import os
import json
import hashlib
import asyncio
import time
from typing import Optional, Dict, Any

from app.ai import get_ai_provider
from app.ai.schemas import (
    ProjectExplanation,
    ModuleExplanation,
    ClassExplanation,
    FunctionExplanation,
    ParameterExplanation
)
from app.ai.prompts import (
    build_project_explanation_prompt,
    build_module_explanation_prompt,
    build_markdown_explanation_prompt,
    build_json_config_explanation_prompt,
    build_js_ts_explanation_prompt,
    build_generic_text_explanation_prompt,
    build_class_explanation_prompt,
    build_function_explanation_prompt
)
from app.services.extractor import get_project_directory
from app.services.python_ast import analyze_project_workspace
from app.services.dependency_graph import generate_dependency_graph
from app.services.file_classifier import get_file_type, is_binary_file

# Global Development Request Counter
_AI_REQUEST_COUNTER = 0
# Global In-Flight Request Lock Guard
_IN_FLIGHT_REQUESTS: Dict[str, asyncio.Task] = {}

def _log_ai_request(req_type: str, target: str, cache_hit: bool):
    """Development-only request counter logger for Groq / AI provider."""
    global _AI_REQUEST_COUNTER
    provider = get_ai_provider()
    p_name = provider.__class__.__name__.replace("Provider", "").lower()
    if not cache_hit:
        _AI_REQUEST_COUNTER += 1
    cache_str = "HIT" if cache_hit else "MISS"
    print(f"AI Provider: {p_name}")
    print(f"Model: {provider.model}")
    print(f"Request type: {req_type} | Target: {target} | Cache: {cache_str}")

def reset_ai_request_counter():
    """Resets counter for test suites."""
    global _AI_REQUEST_COUNTER
    _AI_REQUEST_COUNTER = 0

def _get_cache_file_path(project_dir: str) -> str:
    return os.path.join(project_dir, "explanation_cache.json")

def _read_cache(project_dir: str) -> Dict[str, Any]:
    cache_path = _get_cache_file_path(project_dir)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _write_cache(project_dir: str, cache_data: Dict[str, Any]):
    cache_path = _get_cache_file_path(project_dir)
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
    except Exception:
        pass

def _compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

def _extract_source_snippet(file_path: str, start_line: int, end_line: int) -> str:
    """Extracts exact lines of source code for a function or class."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            sliced = lines[max(0, start_line - 1): min(len(lines), end_line)]
            return "".join(sliced)
    except Exception:
        return f"# Unable to read source snippet for {file_path}"

async def explain_project(project_id: str, force_refresh: bool = False) -> ProjectExplanation:
    """Generates or retrieves cached project-level architectural overview (On-Demand only)."""
    project_dir = get_project_directory(project_id)
    ast_analysis = analyze_project_workspace(project_dir, project_id)
    dep_graph = generate_dependency_graph(ast_analysis)

    project_hash = _compute_hash(f"{ast_analysis.total_python_files}:{ast_analysis.total_lines_of_code}:{ast_analysis.total_classes}:{ast_analysis.total_functions}")
    cache_key = f"project:{project_id}:{project_hash}"
    cache = _read_cache(project_dir)

    # 1. Check Cache
    if not force_refresh and cache_key in cache:
        _log_ai_request("project", "Project Overview", cache_hit=True)
        return ProjectExplanation(**cache[cache_key])

    # 2. Rich Static Fallback Object
    static_fallback = ProjectExplanation(
        purpose=f"Python codebase with {ast_analysis.total_python_files} files and {ast_analysis.total_lines_of_code} lines of code.",
        architecture=f"Modular Python architecture ({ast_analysis.total_classes} classes, {ast_analysis.total_functions} functions).",
        major_modules=[f.relative_path for f in ast_analysis.files_analyzed[:5]],
        main_components=[f.relative_path for f in ast_analysis.files_analyzed[:5]],
        technologies=["Python"] + [lib.name for lib in dep_graph.external_libraries],
        important_dependencies=[lib.name for lib in dep_graph.external_libraries],
        key_dependencies=[lib.name for lib in dep_graph.external_libraries],
        execution_flow=["Main application entrypoints and module definitions extracted via AST."],
        main_workflow=["Main application entrypoints and module definitions extracted via AST."],
        maintenance_concerns=["Verify unhandled exceptions and maintain clear dependency boundaries."],
        is_static_fallback=True,
        fallback_reason="AI explanation temporarily unavailable. Showing static analysis."
    )

    provider = get_ai_provider()
    if not provider.is_configured:
        cache[cache_key] = static_fallback.model_dump()
        _write_cache(project_dir, cache)
        return static_fallback

    # 3. In-Flight Lock / Deduplication Guard
    if cache_key in _IN_FLIGHT_REQUESTS:
        return await _IN_FLIGHT_REQUESTS[cache_key]

    async def _execute_request():
        _log_ai_request("project", "Project Overview", cache_hit=False)
        prompt = build_project_explanation_prompt(
            total_files=ast_analysis.total_python_files,
            total_loc=ast_analysis.total_lines_of_code,
            file_list=[f.relative_path for f in ast_analysis.files_analyzed],
            ast_summary={
                "classes": ast_analysis.total_classes,
                "functions": ast_analysis.total_functions,
                "imports": ast_analysis.total_imports
            },
            dep_summary={"edges": [e.id for e in dep_graph.edges]},
            ext_libs=[{"name": lib.name} for lib in dep_graph.external_libraries]
        )

        try:
            explanation = await provider.generate_structured(
                prompt=prompt,
                schema_class=ProjectExplanation,
                max_tokens=int(os.getenv("GROQ_MAX_OUTPUT_TOKENS", os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "250")))
            )
            explanation.is_static_fallback = False
            explanation.main_components = explanation.main_components or explanation.major_modules
            explanation.main_workflow = explanation.main_workflow or explanation.execution_flow
            explanation.key_dependencies = explanation.key_dependencies or explanation.important_dependencies
        except Exception as exc:
            print(f"[Project Explanation AI Notice]: {exc}. Returning static fallback.")
            explanation = static_fallback
            explanation.fallback_reason = str(exc)

        cache[cache_key] = explanation.model_dump()
        _write_cache(project_dir, cache)
        return explanation

    task = asyncio.create_task(_execute_request())
    _IN_FLIGHT_REQUESTS[cache_key] = task
    try:
        return await task
    finally:
        _IN_FLIGHT_REQUESTS.pop(cache_key, None)

async def explain_module(project_id: str, relative_path: str, force_refresh: bool = False) -> ModuleExplanation:
    """Generates or retrieves cached module/file level explanation (On-Demand only)."""
    project_dir = get_project_directory(project_id)
    clean_rel = relative_path.replace("\\", "/")
    abs_path = os.path.join(project_dir, clean_rel)

    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"File '{relative_path}' not found in project workspace.")

    file_type = get_file_type(clean_rel)
    is_bin = is_binary_file(abs_path)

    # Binary guard
    if is_bin or file_type == "binary":
        size_kb = os.path.getsize(abs_path) / 1024.0 if os.path.exists(abs_path) else 0.0
        return ModuleExplanation(
            file_path=clean_rel,
            purpose=f"Binary/Database asset file ({os.path.basename(clean_rel)}).",
            summary=f"Binary data asset file ({size_kb:.1f} KB).",
            responsibilities=[f"Binary data asset ({size_kb:.1f} KB)."],
            dependencies=[],
            classes=[],
            functions=[],
            key_elements=[],
            potential_issues=["Direct text analysis not available for binary files."],
            file_type=file_type,
            is_binary=True,
            is_static_fallback=True
        )

    with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
        source_code = f.read()

    if not source_code.strip():
        return ModuleExplanation(
            file_path=clean_rel,
            purpose=f"Empty file '{clean_rel}'.",
            summary="Empty file containing no content lines.",
            responsibilities=["Contains no code or text lines."],
            file_type=file_type,
            is_static_fallback=True
        )

    file_hash = _compute_hash(source_code)
    cache_key = f"file:{project_id}:{clean_rel}:{file_hash}"
    cache = _read_cache(project_dir)

    # 1. Check Cache
    if not force_refresh and cache_key in cache:
        _log_ai_request("file", clean_rel, cache_hit=True)
        return ModuleExplanation(**cache[cache_key])

    # Fetch AST info for static fallback construction
    file_ast_info = None
    if file_type == "python":
        try:
            ast_analysis = analyze_project_workspace(project_dir, project_id)
            for f in ast_analysis.files_analyzed:
                if f.relative_path.replace("\\", "/") == clean_rel:
                    file_ast_info = f
                    break
        except Exception:
            file_ast_info = None

    if file_ast_info:
        cls_names = [c.name for c in file_ast_info.classes]
        fn_names = [fn.name for fn in file_ast_info.functions]
        imp_names = [i.module or i.name for i in file_ast_info.imports if i.module or i.name]
        static_fallback = ModuleExplanation(
            file_path=clean_rel,
            purpose=f"Python source module containing {len(fn_names)} functions and {len(cls_names)} classes ({file_ast_info.lines_of_code} LOC).",
            summary=f"Defines {len(cls_names)} classes and {len(fn_names)} functions.",
            responsibilities=[
                f"Class definitions: {', '.join(cls_names) or 'None'}.",
                f"Standalone functions: {', '.join(fn_names) or 'None'}."
            ],
            dependencies=imp_names,
            classes=cls_names,
            functions=fn_names,
            key_elements=cls_names + fn_names,
            potential_issues=["Ensure error handling and boundary scenarios are tested."],
            file_type=file_type,
            is_binary=False,
            is_static_fallback=True,
            fallback_reason="AI explanation temporarily unavailable. Showing static analysis."
        )
    else:
        static_fallback = ModuleExplanation(
            file_path=clean_rel,
            purpose=f"{file_type.capitalize()} file '{clean_rel}'.",
            summary=f"Provides {file_type} configuration or documentation contents.",
            responsibilities=[f"Provides {file_type} documentation or configuration data."],
            dependencies=[],
            classes=[],
            functions=[],
            key_elements=[],
            potential_issues=[],
            file_type=file_type,
            is_binary=False,
            is_static_fallback=True,
            fallback_reason="AI explanation temporarily unavailable. Showing static analysis."
        )

    provider = get_ai_provider()
    if not provider.is_configured:
        cache[cache_key] = static_fallback.model_dump()
        _write_cache(project_dir, cache)
        return static_fallback

    # 2. In-Flight Lock / Deduplication Guard
    if cache_key in _IN_FLIGHT_REQUESTS:
        return await _IN_FLIGHT_REQUESTS[cache_key]

    async def _execute_request():
        _log_ai_request("file", clean_rel, cache_hit=False)
        if file_type == "python" and file_ast_info:
            prompt = build_module_explanation_prompt(
                file_path=clean_rel,
                source_code=source_code[:1000],
                file_ast_info=file_ast_info.model_dump(),
                file_dep_info={"project_dependencies": []}
            )
        elif file_type == "markdown":
            prompt = build_markdown_explanation_prompt(clean_rel, source_code[:1000])
        elif file_type in ["json", "config"]:
            prompt = build_json_config_explanation_prompt(clean_rel, source_code[:1000], file_type)
        elif file_type in ["javascript", "typescript"]:
            prompt = build_js_ts_explanation_prompt(clean_rel, source_code[:1000], file_type)
        else:
            prompt = build_generic_text_explanation_prompt(clean_rel, source_code[:1000], file_type)

        try:
            explanation = await provider.generate_structured(
                prompt=prompt,
                schema_class=ModuleExplanation,
                max_tokens=int(os.getenv("GROQ_MAX_OUTPUT_TOKENS", os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "250")))
            )
            explanation.file_type = file_type
            explanation.is_binary = False
            explanation.is_static_fallback = False
            if file_ast_info:
                if not explanation.classes and file_ast_info.classes:
                    explanation.classes = [c.name for c in file_ast_info.classes]
                if not explanation.functions and file_ast_info.functions:
                    explanation.functions = [fn.name for fn in file_ast_info.functions]
                explanation.key_elements = explanation.key_elements or (explanation.classes + explanation.functions)
        except Exception as exc:
            print(f"[Module Explanation AI Notice for {clean_rel}]: {exc}. Returning static fallback.")
            explanation = static_fallback
            explanation.fallback_reason = str(exc)

        cache[cache_key] = explanation.model_dump()
        _write_cache(project_dir, cache)
        return explanation

    task = asyncio.create_task(_execute_request())
    _IN_FLIGHT_REQUESTS[cache_key] = task
    try:
        return await task
    finally:
        _IN_FLIGHT_REQUESTS.pop(cache_key, None)

async def explain_class(project_id: str, relative_path: str, class_name: str, force_refresh: bool = False) -> ClassExplanation:
    """Generates or retrieves cached class-level explanation (On-Demand only)."""
    project_dir = get_project_directory(project_id)
    clean_rel = relative_path.replace("\\", "/")
    abs_path = os.path.join(project_dir, clean_rel)

    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"File '{relative_path}' not found in project workspace.")

    ast_analysis = analyze_project_workspace(project_dir, project_id)
    target_cls = None
    for f in ast_analysis.files_analyzed:
        if f.relative_path.replace("\\", "/") == clean_rel:
            for cls in f.classes:
                if cls.name == class_name:
                    target_cls = cls
                    break

    if not target_cls:
        raise FileNotFoundError(f"Class '{class_name}' not found in '{relative_path}'.")

    class_source = _extract_source_snippet(abs_path, target_cls.start_line, target_cls.end_line)
    cls_hash = _compute_hash(class_source)
    cache_key = f"class:{project_id}:{clean_rel}:{class_name}:{cls_hash}"
    cache = _read_cache(project_dir)

    if not force_refresh and cache_key in cache:
        _log_ai_request("class", f"{clean_rel}:{class_name}", cache_hit=True)
        return ClassExplanation(**cache[cache_key])

    static_fallback = ClassExplanation(
        class_name=class_name,
        purpose=f"Defines class '{class_name}' inheriting from {target_cls.bases or 'object'}.",
        responsibilities=[f"Encapsulates {len(target_cls.methods)} methods."],
        constructor_summary="Initializes instance attributes." if any(m.name == "__init__" for m in target_cls.methods) else None,
        important_methods=[m.name for m in target_cls.methods],
        inheritance=target_cls.bases,
        dependencies=[],
        potential_issues=[],
        is_static_fallback=True,
        fallback_reason="AI explanation temporarily unavailable. Showing static analysis."
    )

    provider = get_ai_provider()
    if not provider.is_configured:
        cache[cache_key] = static_fallback.model_dump()
        _write_cache(project_dir, cache)
        return static_fallback

    if cache_key in _IN_FLIGHT_REQUESTS:
        return await _IN_FLIGHT_REQUESTS[cache_key]

    async def _execute_request():
        _log_ai_request("class", f"{clean_rel}:{class_name}", cache_hit=False)
        prompt = build_class_explanation_prompt(
            file_path=clean_rel,
            class_name=class_name,
            class_source=class_source,
            class_ast_info=target_cls.model_dump()
        )

        try:
            explanation = await provider.generate_structured(
                prompt=prompt,
                schema_class=ClassExplanation,
                max_tokens=int(os.getenv("GROQ_MAX_OUTPUT_TOKENS", os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "250")))
            )
            explanation.is_static_fallback = False
        except Exception as exc:
            explanation = static_fallback
            explanation.fallback_reason = str(exc)

        cache[cache_key] = explanation.model_dump()
        _write_cache(project_dir, cache)
        return explanation

    task = asyncio.create_task(_execute_request())
    _IN_FLIGHT_REQUESTS[cache_key] = task
    try:
        return await task
    finally:
        _IN_FLIGHT_REQUESTS.pop(cache_key, None)

async def explain_function(project_id: str, relative_path: str, function_name: str, force_refresh: bool = False) -> FunctionExplanation:
    """Generates or retrieves cached function-level explanation (Explicit On-Demand only)."""
    project_dir = get_project_directory(project_id)
    clean_rel = relative_path.replace("\\", "/")
    abs_path = os.path.join(project_dir, clean_rel)

    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"File '{relative_path}' not found in project workspace.")

    ast_analysis = analyze_project_workspace(project_dir, project_id)
    target_fn = None
    for f in ast_analysis.files_analyzed:
        if f.relative_path.replace("\\", "/") == clean_rel:
            for fn in f.functions:
                if fn.name == function_name:
                    target_fn = fn
                    break
            if not target_fn:
                for cls in f.classes:
                    for m in cls.methods:
                        if m.name == function_name:
                            target_fn = m
                            break

    if not target_fn:
        raise FileNotFoundError(f"Function/Method '{function_name}' not found in '{relative_path}'.")

    fn_source = _extract_source_snippet(abs_path, target_fn.start_line, target_fn.end_line)
    fn_hash = _compute_hash(fn_source)
    cache_key = f"function:{project_id}:{clean_rel}:{function_name}:{fn_hash}"
    cache = _read_cache(project_dir)

    # 1. Check Cache
    if not force_refresh and cache_key in cache:
        _log_ai_request("function", f"{clean_rel}:{function_name}", cache_hit=True)
        return FunctionExplanation(**cache[cache_key])

    param_exps = [
        ParameterExplanation(name=p.name, explanation=f"Parameter '{p.name}' (type: {p.annotation or 'any'}, default: {p.default or 'none'})")
        for p in target_fn.parameters
    ]
    static_fallback = FunctionExplanation(
        function_name=function_name,
        purpose=f"Executes Python function '{function_name}'.",
        parameters_explained=param_exps,
        return_value_explained=f"Returns {target_fn.returns or 'computed result'}.",
        step_by_step_logic=[f"Evaluates function body from line {target_fn.start_line} to {target_fn.end_line}."],
        calls=target_fn.calls,
        dependencies=[],
        side_effects=[],
        edge_cases=["Empty or invalid parameter types."],
        potential_issues=[],
        is_static_fallback=True,
        fallback_reason="AI explanation temporarily unavailable. Showing static analysis."
    )

    provider = get_ai_provider()
    if not provider.is_configured:
        cache[cache_key] = static_fallback.model_dump()
        _write_cache(project_dir, cache)
        return static_fallback

    # 2. In-Flight Lock / Deduplication Guard
    if cache_key in _IN_FLIGHT_REQUESTS:
        return await _IN_FLIGHT_REQUESTS[cache_key]

    async def _execute_request():
        _log_ai_request("function", f"{clean_rel}:{function_name}", cache_hit=False)
        prompt = build_function_explanation_prompt(
            file_path=clean_rel,
            function_name=function_name,
            function_source=fn_source,
            function_ast_info=target_fn.model_dump()
        )

        try:
            explanation = await provider.generate_structured(
                prompt=prompt,
                schema_class=FunctionExplanation,
                max_tokens=int(os.getenv("GROQ_MAX_OUTPUT_TOKENS", os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "250")))
            )
            explanation.is_static_fallback = False
        except Exception as exc:
            explanation = static_fallback
            explanation.fallback_reason = str(exc)

        cache[cache_key] = explanation.model_dump()
        _write_cache(project_dir, cache)
        return explanation

    task = asyncio.create_task(_execute_request())
    _IN_FLIGHT_REQUESTS[cache_key] = task
    try:
        return await task
    finally:
        _IN_FLIGHT_REQUESTS.pop(cache_key, None)
