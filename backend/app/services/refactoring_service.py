import os
import sys
import json
import ast
import hashlib
import difflib
import asyncio
import time
from typing import Optional, Dict, Any, List, Tuple

from app.ai import get_ai_provider
from app.schemas.refactoring import (
    AIRefactorResponseModel,
    RefactorResultResponse,
    ValidationMetrics,
    CodeIssue,
    CodeImprovement,
    SaveRefactorResponse
)
from app.services.extractor import get_project_directory
from app.services.python_ast import analyze_project_workspace
from app.services.file_classifier import get_file_type
from app.services.code_smell_service import analyze_code_smells
from app.services.unit_testing_service import (
    run_unit_tests,
    get_test_coverage,
    _ensure_safe_path,
    _read_cache,
    _write_cache,
    _compute_hash,
    _extract_source_snippet
)

# In-flight request deduplication lock for refactoring
_IN_FLIGHT_REFACTOR_REQUESTS: Dict[str, asyncio.Task] = {}

# Python Standard Library module names for new dependency detection
STD_LIB_MODULES = {
    "abc", "argparse", "array", "ast", "asyncio", "base64", "bisect", "builtins",
    "collections", "concurrent", "copy", "csv", "dataclasses", "datetime", "decimal",
    "difflib", "enum", "functools", "glob", "hashlib", "http", "io", "itertools",
    "json", "logging", "math", "os", "pathlib", "pickle", "random", "re", "select",
    "shutil", "signal", "socket", "sqlite3", "ssl", "string", "sys", "tempfile",
    "threading", "time", "typing", "unittest", "urllib", "uuid", "weakref", "xml", "zipfile"
}

def _clean_code_fences(code_str: str) -> str:
    """Strips markdown code blocks safely from raw AI text output."""
    cleaned = code_str.strip()
    if "```" in cleaned:
        parts = cleaned.split("```")
        for part in parts:
            p = part.strip()
            if p.startswith("python"):
                p = p[6:].strip()
            if any(p.startswith(kw) for kw in ["def ", "class ", "import ", "from ", "#", "if ", "try:", "with ", "return "]):
                return p
        for part in parts:
            p = part.strip()
            if p.startswith("python"):
                p = p[6:].strip()
            if p and not p.startswith("json"):
                return p
    return cleaned

def _extract_imported_packages(source_code: str) -> List[str]:
    """Extracts top-level imported module names from Python source code."""
    imported = set()
    try:
        tree = ast.parse(source_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_name = alias.name.split('.')[0]
                    imported.add(top_name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top_name = node.module.split('.')[0]
                    imported.add(top_name)
    except Exception:
        pass
    return sorted(list(imported))

def _detect_new_dependencies(orig_code: str, refactored_code: str) -> List[str]:
    """Identifies new third-party dependencies introduced in refactored code."""
    orig_imports = set(_extract_imported_packages(orig_code))
    ref_imports = set(_extract_imported_packages(refactored_code))
    
    new_imports = ref_imports - orig_imports
    third_party_new = [pkg for pkg in new_imports if pkg not in STD_LIB_MODULES and not pkg.startswith("_")]
    return sorted(third_party_new)

def _generate_unified_diff(orig_code: str, refactored_code: str) -> str:
    """Generates a clean unified diff string using Python's difflib."""
    orig_lines = orig_code.splitlines(keepends=True)
    ref_lines = refactored_code.splitlines(keepends=True)
    
    diff_generator = difflib.unified_diff(
        orig_lines,
        ref_lines,
        fromfile="Original Code",
        tofile="Refactored Code",
        lineterm=""
    )
    diff_text = "".join(diff_generator)
    return diff_text if diff_text.strip() else "# No structural changes detected."

def _build_refactoring_prompt(
    file_path: str,
    function_name: Optional[str],
    source_code: str,
    ast_info: Optional[Dict[str, Any]],
    code_smells: List[Dict[str, str]]
) -> str:
    target_desc = f"function '{function_name}'" if function_name else f"file '{file_path}'"
    
    return (
        f"You are an expert Python software architect. Refactor the following Python {target_desc} for superior readability, maintainability, performance, and modern Pythonic conventions.\n\n"
        f"CRITICAL CONSTRAINTS:\n"
        f"1. DO NOT change external API behavior, function signatures, or business logic contracts unless essential for error safety.\n"
        f"2. Maintain 100% functional equivalence.\n"
        f"3. Provide actual, complete Python code in the 'refactored_code' property. Do NOT output pseudocode or markdown block fences inside the string.\n\n"
        f"TARGET SOURCE CODE:\n"
        f"```python\n{source_code}\n```\n\n"
        f"STATIC CODE SMELLS IDENTIFIED LOCALLY:\n"
        f"{json.dumps(code_smells, indent=2)}\n\n"
        f"AST METADATA:\n"
        f"{json.dumps(ast_info or {}, indent=2)[:800]}\n\n"
        f"Respond ONLY with valid JSON strictly matching the Pydantic schema with keys: 'summary', 'issues_found', 'improvements', 'refactored_code', 'explanation', 'potential_risks', 'new_dependencies'."
    )

def _generate_static_fallback_refactored_code(source_code: str) -> Tuple[str, List[CodeIssue], List[CodeImprovement]]:
    """Generates clean fallback refactored code when AI is unconfigured or rate limited."""
    # Ensure source code has docstring and clean formatting
    issues = [
        CodeIssue(type="static_fallback", description="AI temporarily unavailable; showing static formatting baseline.", severity="low")
    ]
    improvements = [
        CodeImprovement(type="formatting", description="Preserved clean original source structure as fallback.")
    ]
    return source_code, issues, improvements

async def refactor_target(
    project_id: str,
    relative_path: str,
    function_name: Optional[str] = None,
    force_refresh: bool = False
) -> RefactorResultResponse:
    """
    Refactors a Python file or function using Groq AI and static code analysis.
    Validates syntax via ast.parse(), measures pytest execution & coverage before and after,
    and returns a structured response without mutating original code.
    """
    project_dir = get_project_directory(project_id)
    clean_rel = relative_path.replace("\\", "/")
    abs_src_path = _ensure_safe_path(project_dir, clean_rel)

    if not os.path.exists(abs_src_path):
        raise FileNotFoundError(f"Source file '{relative_path}' not found in project workspace.")

    file_type = get_file_type(clean_rel)
    if file_type not in ("python", "javascript", "typescript"):
        raise ValueError(f"Code refactoring is supported for Python, JavaScript, and TypeScript files (got '{file_type}').")

    with open(abs_src_path, "r", encoding="utf-8", errors="ignore") as f:
        full_source = f.read()

    # Target specific snippet if function_name provided
    target_code = full_source
    ast_info = None
    try:
        ast_analysis = analyze_project_workspace(project_dir, project_id)
        for file_obj in ast_analysis.files_analyzed:
            if file_obj.relative_path.replace("\\", "/") == clean_rel:
                ast_info = file_obj.model_dump()
                if function_name:
                    for fn in file_obj.functions:
                        if fn.name == function_name:
                            target_code = _extract_source_snippet(abs_src_path, fn.start_line, fn.end_line)
                            break
                    for cls in file_obj.classes:
                        for m in cls.methods:
                            if m.name == function_name:
                                target_code = _extract_source_snippet(abs_src_path, m.start_line, m.end_line)
                                break
                break
    except Exception:
        ast_info = None

    src_hash = _compute_hash(target_code)
    fn_suffix = f":{function_name}" if function_name else ""
    cache_key = f"refactor:{project_id}:{clean_rel}{fn_suffix}:{src_hash}"
    cache = _read_cache(project_dir)

    # 1. Check Cache
    if not force_refresh and cache_key in cache:
        print(f"AI Provider: groq | Model: Groq | Request type: refactor | Target: {clean_rel} | Cache: HIT")
        cached_data = cache[cache_key]
        cached_data["is_cached"] = True
        return RefactorResultResponse.model_validate(cached_data)

    # 2. In-Flight Request Deduplication Guard
    if cache_key in _IN_FLIGHT_REFACTOR_REQUESTS:
        print(f"AI Provider: groq | Deduplicated refactoring request joined.")
        return await _IN_FLIGHT_REFACTOR_REQUESTS[cache_key]

    async def _execute_refactoring():
        # Step A: Local AST Static Code Smell Analysis
        code_smells = analyze_code_smells(target_code, function_name)
        
        # Step B: AI Code Generation via GroqProvider
        provider = get_ai_provider()
        is_fallback = False
        summary_text = "Code refactored using Groq AI."

        if provider.is_configured:
            try:
                prompt = _build_refactoring_prompt(clean_rel, function_name, target_code, ast_info, code_smells)
                res: AIRefactorResponseModel = await provider.generate_structured(
                    prompt=prompt,
                    schema_class=AIRefactorResponseModel,
                    max_tokens=int(os.getenv("GROQ_MAX_OUTPUT_TOKENS", os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "750")))
                )
                raw_ref_code = res.refactored_code
                issues_found = res.issues_found
                improvements = res.improvements
                summary_text = res.summary
                explanation = res.explanation
                potential_risks = res.potential_risks
                new_deps = res.new_dependencies
            except Exception as exc:
                print(f"[Refactoring AI Notice]: {exc}. Using static fallback refactoring.")
                raw_ref_code, issues_found, improvements = _generate_static_fallback_refactored_code(target_code)
                summary_text = f"Static analysis fallback refactoring ({str(exc)[:80]})."
                explanation = ["Preserved original code structure due to AI rate limits/unavailability."]
                potential_risks = []
                new_deps = []
                is_fallback = True
        else:
            raw_ref_code, issues_found, improvements = _generate_static_fallback_refactored_code(target_code)
            summary_text = "Static analysis refactoring (AI Provider unconfigured)."
            explanation = ["AI Provider not configured in backend environment."]
            potential_risks = []
            new_deps = []
            is_fallback = True

        cleaned_ref_code = _clean_code_fences(raw_ref_code)

        # Step C: Syntax Validation via ast.parse()
        syntax_valid = True
        try:
            ast.parse(cleaned_ref_code)
            final_refactored_code = cleaned_ref_code
        except SyntaxError as syn_err:
            print(f"[Refactor Syntax Error]: {syn_err}. Attempting single clean regeneration attempt...")
            # Try 1 simple fix attempt or fallback
            syntax_valid = False
            final_refactored_code = target_code  # Safely keep original if syntax invalid
            summary_text = "Generated refactored code contained invalid Python syntax."
            explanation.append("Refactored code failed ast.parse() validation; original code preserved.")

        # Detect any new third party dependencies
        detected_new_deps = _detect_new_dependencies(target_code, final_refactored_code)
        all_new_deps = sorted(list(set(new_deps + detected_new_deps)))

        # Step D: Pre-Refactoring Test Execution & Coverage Baseline
        before_exec = run_unit_tests(project_id, clean_rel, timeout_seconds=15)
        before_cov = get_test_coverage(project_id, clean_rel)

        before_metrics = {
            "passed": before_exec.passed,
            "failed": before_exec.failed,
            "total": before_exec.total,
            "status": before_exec.status,
            "coverage": before_cov.overall_coverage
        }

        # Step E: Post-Refactoring Test Sandboxing
        # Safely test refactored candidate by temporarily swapping file content in workspace
        after_metrics = dict(before_metrics)
        tests_passed = True

        if syntax_valid and final_refactored_code != target_code:
            try:
                # If function refactoring, substitute function snippet inside full source
                if function_name:
                    full_refactored = full_source.replace(target_code, final_refactored_code, 1)
                else:
                    full_refactored = final_refactored_code

                # Overwrite temporarily
                with open(abs_src_path, "w", encoding="utf-8") as f:
                    f.write(full_refactored)

                # Run Pytest & Coverage on workspace
                after_exec = run_unit_tests(project_id, clean_rel, timeout_seconds=15)
                after_cov = get_test_coverage(project_id, clean_rel)

                after_metrics = {
                    "passed": after_exec.passed,
                    "failed": after_exec.failed,
                    "total": after_exec.total,
                    "status": after_exec.status,
                    "coverage": after_cov.overall_coverage
                }

                if after_exec.failed > 0 or after_exec.status == "failed":
                    tests_passed = False
                    summary_text += " (Refactored code failed validation tests)."

            finally:
                # ALWAYS restore original source code file
                with open(abs_src_path, "w", encoding="utf-8") as f:
                    f.write(full_source)

        # Step F: Generate Unified Diff
        diff_text = _generate_unified_diff(target_code, final_refactored_code)

        validation_res = ValidationMetrics(
            syntax_valid=syntax_valid,
            tests_passed=tests_passed,
            coverage=after_metrics["coverage"],
            before_tests=before_metrics,
            after_tests=after_metrics
        )

        response_obj = RefactorResultResponse(
            status="success" if syntax_valid else "error",
            file_path=clean_rel,
            function_name=function_name,
            summary=summary_text,
            issues_found=issues_found,
            improvements=improvements,
            original_code=target_code,
            refactored_code=final_refactored_code,
            explanation=explanation,
            potential_risks=potential_risks,
            new_dependencies=all_new_deps,
            validation=validation_res,
            diff=diff_text,
            is_cached=False,
            is_fallback=is_fallback
        )

        if syntax_valid:
            cache[cache_key] = response_obj.model_dump()
            _write_cache(project_dir, cache)

        return response_obj

    task = asyncio.create_task(_execute_refactoring())
    _IN_FLIGHT_REFACTOR_REQUESTS[cache_key] = task
    try:
        return await task
    finally:
        _IN_FLIGHT_REFACTOR_REQUESTS.pop(cache_key, None)

def save_refactored_code(
    project_id: str,
    relative_path: str,
    refactored_code: str
) -> SaveRefactorResponse:
    """
    Explicitly saves user-approved refactored code to the workspace source file.
    Validates path security and Python syntax before writing to disk.
    """
    project_dir = get_project_directory(project_id)
    clean_rel = relative_path.replace("\\", "/")
    abs_src_path = _ensure_safe_path(project_dir, clean_rel)

    cleaned_code = _clean_code_fences(refactored_code)

    # Validate Python syntax
    try:
        ast.parse(cleaned_code)
    except SyntaxError as syn_err:
        raise ValueError(f"Cannot save refactored code: Invalid Python syntax ({str(syn_err)}).")

    with open(abs_src_path, "w", encoding="utf-8") as f:
        f.write(cleaned_code)

    return SaveRefactorResponse(
        status="success",
        file_path=clean_rel,
        message=f"Refactored code saved successfully to '{clean_rel}'."
    )
