import os
import sys
import json
import ast
import re
import hashlib
import asyncio
import subprocess
import time
from typing import Optional, Dict, Any, List

from app.ai import get_ai_provider
from app.schemas.testing import (
    UnitTestGenResponse,
    GeneratedUnitTestModel,
    TestExecutionResult,
    CoverageResult,
    FileCoverageDetail
)
from app.services.extractor import get_project_directory
from app.services.python_ast import analyze_project_workspace
from app.services.js_ts_ast import analyze_js_ts_file
from app.services.file_classifier import get_file_type
from app.services.js_ts_test_service import (
    inspect_package_json,
    build_js_test_prompt,
    generate_js_static_fallback,
    validate_js_syntax,
    run_js_unit_tests,
    get_js_test_coverage
)

# In-flight lock for test generation
_IN_FLIGHT_TEST_REQUESTS: Dict[str, asyncio.Task] = {}

def _compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

def _read_cache(project_dir: str) -> Dict[str, Any]:
    cache_path = os.path.join(project_dir, "explanation_cache.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _write_cache(project_dir: str, cache_data: Dict[str, Any]):
    cache_path = os.path.join(project_dir, "explanation_cache.json")
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
    except Exception:
        pass

def _ensure_safe_path(project_dir: str, file_path: str) -> str:
    """Security Guard: Prevents path traversal outside project workspace."""
    abs_project = os.path.abspath(project_dir)
    target_path = os.path.abspath(os.path.join(project_dir, file_path))
    if not target_path.startswith(abs_project):
        raise ValueError(f"Security Alert: Path traversal attempt detected outside workspace: '{file_path}'")
    return target_path

def _extract_source_snippet(file_path: str, start_line: int, end_line: int) -> str:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            sliced = lines[max(0, start_line - 1): min(len(lines), end_line)]
            return "".join(sliced)
    except Exception:
        return f"# Unable to read snippet from {file_path}"

def _build_unit_test_prompt(
    file_path: str,
    function_name: Optional[str],
    source_code: str,
    ast_info: Optional[Dict[str, Any]]
) -> str:
    """Builds a compact prompt for Groq unit test generation."""
    target_desc = f"function '{function_name}'" if function_name else f"file '{file_path}'"
    module_name = os.path.splitext(os.path.basename(file_path))[0]
    
    return (
        f"You are an expert Python test engineer. Write a complete, syntactically valid pytest test suite for the {target_desc} in '{file_path}'.\n\n"
        f"TARGET SOURCE CODE:\n"
        f"```python\n{source_code[:1500]}\n```\n\n"
        f"AST METADATA:\n"
        f"{json.dumps(ast_info or {}, indent=2)[:500]}\n\n"
        f"INSTRUCTIONS:\n"
        f"1. Import pytest and target functions from {module_name} if needed.\n"
        f"2. Generate real, executable Python pytest functions (e.g. test_normal(), test_edge_case()).\n"
        f"3. Do NOT include markdown blocks inside the test_code property string.\n"
        f"4. Output strictly JSON with 'test_code' and 'summary'."
    )

def _generate_static_fallback_test_code(clean_rel: str, function_name: Optional[str], source_code: str) -> str:
    """Generates a valid static pytest fallback test file if AI is unavailable or produces invalid syntax."""
    module_name = os.path.splitext(os.path.basename(clean_rel))[0]
    
    if function_name:
        return (
            f"import pytest\n"
            f"from {module_name} import {function_name}\n\n"
            f"def test_{function_name}_execution():\n"
            f"    # Basic execution test for {function_name}\n"
            f"    assert callable({function_name})\n"
        )
    else:
        return (
            f"import pytest\n\n"
            f"def test_{module_name}_structure():\n"
            f"    # Basic structure assertion for {module_name}\n"
            f"    assert '{clean_rel}'.endswith('.py')\n"
        )

async def generate_unit_tests(
    project_id: str,
    relative_path: str,
    function_name: Optional[str] = None,
    force_refresh: bool = False
) -> UnitTestGenResponse:
    """Generates unit tests using GroqProvider on-demand, validates syntax with ast.parse, and saves to workspace."""
    project_dir = get_project_directory(project_id)
    clean_rel = relative_path.replace("\\", "/")
    abs_src_path = _ensure_safe_path(project_dir, clean_rel)

    if not os.path.exists(abs_src_path):
        raise FileNotFoundError(f"Source file '{relative_path}' not found in project workspace.")

    file_type = get_file_type(clean_rel)
    if file_type not in ("python", "javascript", "typescript"):
        raise ValueError(f"Unit test generation is supported for Python, JavaScript, and TypeScript files (got '{file_type}').")

    with open(abs_src_path, "r", encoding="utf-8", errors="ignore") as f:
        source_code = f.read()

    # JS / TS Test Generation Pathway
    if file_type in ("javascript", "typescript"):
        pkg_info = inspect_package_json(project_dir)
        framework = pkg_info["framework"]
        ast_info = None
        try:
            ast_analysis = analyze_js_ts_file(abs_src_path, clean_rel)
            ast_info = ast_analysis.model_dump()
        except Exception:
            ast_info = {}

        src_hash = _compute_hash(source_code)
        fn_suffix = f":{function_name}" if function_name else ""
        cache_key = f"test:{project_id}:{clean_rel}{fn_suffix}:{src_hash}"
        cache = _read_cache(project_dir)

        base_name = os.path.splitext(os.path.basename(clean_rel))[0]
        ext = os.path.splitext(clean_rel)[1]
        rel_gen_test_path = f"tests/generated/{base_name}.test{ext}"
        abs_gen_test_path = _ensure_safe_path(project_dir, rel_gen_test_path)

        if not force_refresh and cache_key in cache and os.path.exists(abs_gen_test_path):
            print(f"AI Provider: groq | Request type: test_gen | Target: {clean_rel} | Cache: HIT")
            cached_data = cache[cache_key]
            return UnitTestGenResponse(
                file_path=clean_rel,
                function_name=function_name,
                test_file_path=rel_gen_test_path,
                test_code=cached_data.get("test_code", ""),
                summary=cached_data.get("summary", "Cached JS/TS unit tests retrieved."),
                status="generated",
                is_cached=True,
                is_fallback=cached_data.get("is_fallback", False),
                language=file_type,
                framework=framework
            )

        if cache_key in _IN_FLIGHT_TEST_REQUESTS:
            return await _IN_FLIGHT_TEST_REQUESTS[cache_key]

        async def _execute_js_gen():
            provider = get_ai_provider()
            prompt = build_js_test_prompt(clean_rel, function_name, source_code, ast_info or {}, pkg_info)
            is_fallback = False
            summary_text = f"Unit tests generated for {file_type.title()} using Groq AI."

            if provider.is_configured:
                try:
                    res = await provider.generate_structured(
                        prompt=prompt,
                        schema_class=GeneratedUnitTestModel,
                        max_tokens=int(os.getenv("GROQ_MAX_OUTPUT_TOKENS", os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "400")))
                    )
                    test_code = res.test_code
                    summary_text = res.summary
                except Exception as exc:
                    print(f"[JS Test Gen AI Notice]: {exc}. Using static fallback.")
                    test_code = generate_js_static_fallback(clean_rel, function_name, source_code, pkg_info)
                    summary_text = f"Static test template generated ({str(exc)[:80]})."
                    is_fallback = True
            else:
                test_code = generate_js_static_fallback(clean_rel, function_name, source_code, pkg_info)
                summary_text = "Static test template generated (AI Provider unconfigured)."
                is_fallback = True

            cleaned_code = test_code.strip()
            if "```" in cleaned_code:
                blocks = cleaned_code.split("```")
                for block in blocks:
                    b_sub = block.strip()
                    if b_sub.startswith(("javascript", "typescript", "js", "ts", "jsx", "tsx")):
                        b_sub = re.sub(r"^(javascript|typescript|js|ts|jsx|tsx)\n?", "", b_sub).strip()
                    if "import " in b_sub or "require(" in b_sub or "describe(" in b_sub or "test(" in b_sub or "it(" in b_sub:
                        cleaned_code = b_sub
                        break

            if not validate_js_syntax(cleaned_code):
                print(f"[JS Test Syntax Error]: Invalid syntax detected. Reverting to static fallback code.")
                final_test_code = generate_js_static_fallback(clean_rel, function_name, source_code, pkg_info)
                summary_text = "Generated test contained invalid syntax; safe static fallback used."
                is_fallback = True
            else:
                final_test_code = cleaned_code

            os.makedirs(os.path.dirname(abs_gen_test_path), exist_ok=True)
            with open(abs_gen_test_path, "w", encoding="utf-8") as f:
                f.write(final_test_code)

            response_obj = UnitTestGenResponse(
                file_path=clean_rel,
                function_name=function_name,
                test_file_path=rel_gen_test_path,
                test_code=final_test_code,
                summary=summary_text,
                status="generated",
                is_cached=False,
                is_fallback=is_fallback,
                language=file_type,
                framework=framework
            )

            cache[cache_key] = response_obj.model_dump()
            _write_cache(project_dir, cache)
            return response_obj

        task = asyncio.create_task(_execute_js_gen())
        _IN_FLIGHT_TEST_REQUESTS[cache_key] = task
        try:
            return await task
        finally:
            _IN_FLIGHT_TEST_REQUESTS.pop(cache_key, None)

    # Python Test Generation Pathway
    target_code = source_code
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
    cache_key = f"test:{project_id}:{clean_rel}{fn_suffix}:{src_hash}"
    cache = _read_cache(project_dir)

    base_name = os.path.splitext(os.path.basename(clean_rel))[0]
    fn_name_clean = f"_{function_name}" if function_name else ""
    rel_gen_test_path = f"tests/generated/test_{base_name}{fn_name_clean}.py"
    abs_gen_test_path = _ensure_safe_path(project_dir, rel_gen_test_path)

    # 1. Check Cache
    if not force_refresh and cache_key in cache and os.path.exists(abs_gen_test_path):
        print(f"AI Provider: groq | Model: Groq | Request type: test_gen | Target: {clean_rel} | Cache: HIT")
        cached_data = cache[cache_key]
        return UnitTestGenResponse(
            file_path=clean_rel,
            function_name=function_name,
            test_file_path=rel_gen_test_path,
            test_code=cached_data.get("test_code", ""),
            summary=cached_data.get("summary", "Cached unit tests retrieved."),
            status="generated",
            is_cached=True,
            is_fallback=cached_data.get("is_fallback", False),
            language="python",
            framework="pytest"
        )

    # 2. In-Flight Request Deduplication Guard
    if cache_key in _IN_FLIGHT_TEST_REQUESTS:
        print(f"AI Provider: groq | Deduplicated test generation request joined.")
        return await _IN_FLIGHT_TEST_REQUESTS[cache_key]

    async def _execute_test_gen():
        provider = get_ai_provider()
        prompt = _build_unit_test_prompt(clean_rel, function_name, target_code, ast_info)
        is_fallback = False
        summary_text = "Unit tests generated using Groq AI."

        if provider.is_configured:
            try:
                res = await provider.generate_structured(
                    prompt=prompt,
                    schema_class=GeneratedUnitTestModel,
                    max_tokens=int(os.getenv("GROQ_MAX_OUTPUT_TOKENS", os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "300")))
                )
                test_code = res.test_code
                summary_text = res.summary
            except Exception as exc:
                print(f"[Unit Test Gen AI Notice]: {exc}. Using static fallback test generator.")
                test_code = _generate_static_fallback_test_code(clean_rel, function_name, target_code)
                summary_text = f"Static test template generated ({str(exc)[:80]})."
                is_fallback = True
        else:
            test_code = _generate_static_fallback_test_code(clean_rel, function_name, target_code)
            summary_text = "Static test template generated (AI Provider unconfigured)."
            is_fallback = True

        # Defensive cleanup of markdown tags if Groq wrapped test_code string
        cleaned_code = test_code.strip()
        if "```" in cleaned_code:
            blocks = cleaned_code.split("```")
            for block in blocks:
                b_sub = block.strip()
                if b_sub.startswith("python"):
                    b_sub = b_sub[6:].strip()
                if b_sub.startswith("import ") or b_sub.startswith("def test_"):
                    cleaned_code = b_sub
                    break

        # 3. Validate Python Syntax using ast.parse()
        try:
            ast.parse(cleaned_code)
            final_test_code = cleaned_code
        except SyntaxError as syn_err:
            print(f"[Unit Test Syntax Error]: {syn_err}. Reverting to static fallback code.")
            final_test_code = _generate_static_fallback_test_code(clean_rel, function_name, target_code)
            summary_text = "Generated test contained invalid syntax; safe static fallback used."
            is_fallback = True

        # 4. Save Test File Safely inside workspace
        os.makedirs(os.path.dirname(abs_gen_test_path), exist_ok=True)
        with open(abs_gen_test_path, "w", encoding="utf-8") as f:
            f.write(final_test_code)

        response_obj = UnitTestGenResponse(
            file_path=clean_rel,
            function_name=function_name,
            test_file_path=rel_gen_test_path,
            test_code=final_test_code,
            summary=summary_text,
            status="generated",
            is_cached=False,
            is_fallback=is_fallback,
            language="python",
            framework="pytest"
        )

        cache[cache_key] = response_obj.model_dump()
        _write_cache(project_dir, cache)
        return response_obj

    task = asyncio.create_task(_execute_test_gen())
    _IN_FLIGHT_TEST_REQUESTS[cache_key] = task
    try:
        return await task
    finally:
        _IN_FLIGHT_TEST_REQUESTS.pop(cache_key, None)

def run_unit_tests(
    project_id: str,
    relative_path: str,
    timeout_seconds: int = 30
) -> TestExecutionResult:
    """Executes generated unit tests inside project workspace (pytest for Python, Vitest/Jest for JS/TS)."""
    project_dir = get_project_directory(project_id)
    clean_rel = relative_path.replace("\\", "/")
    file_type = get_file_type(clean_rel)

    if file_type in ("javascript", "typescript"):
        return run_js_unit_tests(project_dir, clean_rel, timeout_seconds)

    # Locate test file for Python
    base_name = os.path.splitext(os.path.basename(clean_rel))[0]
    gen_dir = os.path.join(project_dir, "tests", "generated")
    
    test_files = []
    if os.path.exists(gen_dir):
        for f in os.listdir(gen_dir):
            if f.endswith(".py"):
                test_files.append(os.path.join("tests", "generated", f))

    if not test_files:
        return TestExecutionResult(
            status="error",
            stdout="",
            stderr="No generated test files found for this module. Please generate unit tests first.",
            duration_seconds=0.0,
            language="python",
            framework="pytest"
        )

    # Use backend Python executable for deterministic test runner
    python_exe = sys.executable
    cmd = [python_exe, "-m", "pytest"] + test_files + ["-v", "--tb=short"]

    start_time = time.time()
    try:
        res = subprocess.run(
            cmd,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=timeout_seconds
        )
        duration = round(time.time() - start_time, 2)
        stdout = res.stdout or ""
        stderr = res.stderr or ""

        # Parse pytest execution output for counts using regex
        passed = 0
        failed = 0
        skipped = 0
        errors = 0

        passed_match = re.search(r"(\d+)\s+passed", stdout)
        if passed_match: passed = int(passed_match.group(1))

        failed_match = re.search(r"(\d+)\s+failed", stdout)
        if failed_match: failed = int(failed_match.group(1))

        skipped_match = re.search(r"(\d+)\s+skipped", stdout)
        if skipped_match: skipped = int(skipped_match.group(1))

        error_match = re.search(r"(\d+)\s+error", stdout)
        if error_match: errors = int(error_match.group(1))

        total = passed + failed + skipped + errors
        exec_status = "passed" if res.returncode == 0 and failed == 0 and errors == 0 else "failed"

        return TestExecutionResult(
            status=exec_status,
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration_seconds=duration,
            stdout=stdout[:4000],
            stderr=stderr[:2000],
            language="python",
            framework="pytest"
        )

    except subprocess.TimeoutExpired:
        duration = round(time.time() - start_time, 2)
        return TestExecutionResult(
            status="timeout",
            duration_seconds=duration,
            stdout="",
            stderr=f"Generated test execution timed out after {timeout_seconds} seconds.",
            language="python",
            framework="pytest"
        )
    except Exception as exc:
        duration = round(time.time() - start_time, 2)
        return TestExecutionResult(
            status="error",
            duration_seconds=duration,
            stdout="",
            stderr=f"Test runner error: {str(exc)}",
            language="python",
            framework="pytest"
        )

def get_test_coverage(project_id: str, relative_path: str) -> CoverageResult:
    """Measures coverage (coverage.py for Python, Vitest for JS/TS)."""
    project_dir = get_project_directory(project_id)
    clean_rel = relative_path.replace("\\", "/")
    file_type = get_file_type(clean_rel)

    if file_type in ("javascript", "typescript"):
        return get_js_test_coverage(project_dir, clean_rel)

    abs_src_path = _ensure_safe_path(project_dir, clean_rel)

    gen_dir = os.path.join(project_dir, "tests", "generated")
    
    test_files = []
    if os.path.exists(gen_dir):
        for f in os.listdir(gen_dir):
            if f.endswith(".py"):
                test_files.append(os.path.join("tests", "generated", f))

    if not test_files or not os.path.exists(abs_src_path):
        return CoverageResult(overall_coverage=0.0, total_statements=0, total_missed=0, files=[], language="python", framework="coverage.py")

    python_exe = sys.executable
    cov_json_path = os.path.join(project_dir, "coverage.json")

    # Step 1: Run coverage run -m pytest
    run_cmd = [python_exe, "-m", "coverage", "run", "-m", "pytest"] + test_files
    try:
        subprocess.run(run_cmd, cwd=project_dir, capture_output=True, text=True, timeout=30)
    except Exception:
        pass

    # Step 2: Run coverage json -o coverage.json
    json_cmd = [python_exe, "-m", "coverage", "json", "-o", cov_json_path]
    try:
        subprocess.run(json_cmd, cwd=project_dir, capture_output=True, text=True, timeout=15)
    except Exception:
        pass

    if not os.path.exists(cov_json_path):
        return CoverageResult(
            overall_coverage=0.0,
            total_statements=0,
            total_missed=0,
            files=[FileCoverageDetail(file_path=clean_rel, coverage_percentage=0.0)],
            language="python",
            framework="coverage.py"
        )

    try:
        with open(cov_json_path, "r", encoding="utf-8") as f:
            cov_data = json.load(f)

        files_map = cov_data.get("files", {})
        file_details: List[FileCoverageDetail] = []
        overall_stmts = 0
        overall_missed = 0

        for file_key, metrics in files_map.items():
            try:
                rel_file = os.path.relpath(file_key, project_dir).replace("\\", "/")
            except ValueError:
                rel_file = os.path.basename(file_key)

            summary = metrics.get("summary", {})
            stmts = summary.get("num_statements", 0)
            missed = summary.get("missing_lines", 0)
            pct = round(summary.get("percent_covered", 0.0), 1)

            missing_line_nums = [str(l) for l in metrics.get("missing_lines", [])]

            file_details.append(FileCoverageDetail(
                file_path=rel_file,
                coverage_percentage=pct,
                statements=stmts,
                missed=missed,
                missing_lines=missing_line_nums[:15]
            ))

            overall_stmts += stmts
            overall_missed += missed

        totals = cov_data.get("totals", {})
        overall_pct = round(totals.get("percent_covered", 0.0), 1)

        return CoverageResult(
            overall_coverage=overall_pct,
            total_statements=overall_stmts,
            total_missed=overall_missed,
            files=file_details,
            language="python",
            framework="coverage.py"
        )
    except Exception as exc:
        print(f"[Coverage Parse Notice]: {exc}")
        return CoverageResult(overall_coverage=0.0, total_statements=0, total_missed=0, files=[], language="python", framework="coverage.py")
