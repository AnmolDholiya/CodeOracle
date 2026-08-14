import ast
import os
import json
import hashlib
import asyncio
import time
from typing import Optional, Dict, Any, List, Set, Tuple

from app.ai import get_ai_provider
from app.schemas.ast import FunctionDetail, ClassDetail, ImportDetail, ParameterDetail
from app.schemas.breaking_change import (
    BreakingChangeItem,
    BreakingChangeAnalysisResponse,
    BreakingChangeExplanationModel,
    BreakingChangeExplanationResponse
)
from app.services.extractor import get_project_directory
from app.services.python_ast import (
    analyze_python_file,
    analyze_project_workspace,
    parse_parameters,
    CallVisitor
)
from app.services.file_classifier import get_file_type
from app.services.unit_testing_service import (
    _ensure_safe_path,
    _read_cache,
    _write_cache,
    _compute_hash
)

# In-flight request lock for breaking change explanations
_IN_FLIGHT_BREAKING_REQUESTS: Dict[str, asyncio.Task] = {}

def _extract_ast_nodes_from_code(source_code: str, file_path: Optional[str] = None) -> Tuple[Dict[str, FunctionDetail], Dict[str, ClassDetail], List[ImportDetail], Any]:
    """Parses Python or JS/TS source code into AST and extracts dictionaries of functions, classes, and imports."""
    try:
        tree = ast.parse(source_code)
        functions: Dict[str, FunctionDetail] = {}
        classes: Dict[str, ClassDetail] = {}
        imports: List[ImportDetail] = []

        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(ImportDetail(
                        module=alias.name,
                        name=None,
                        alias=alias.asname,
                        line_number=node.lineno
                    ))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.append(ImportDetail(
                        module=node.module,
                        name=alias.name,
                        alias=alias.asname,
                        line_number=node.lineno
                    ))
            elif isinstance(node, ast.ClassDef):
                bases = [ast.unparse(b) for b in node.bases]
                methods = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        m_params = parse_parameters(item.args)
                        m_ret = ast.unparse(item.returns) if item.returns else None
                        m_start = item.lineno
                        m_end = getattr(item, 'end_lineno', m_start)
                        methods.append(FunctionDetail(
                            name=item.name,
                            parameters=m_params,
                            returns=m_ret,
                            calls=[],
                            start_line=m_start,
                            end_line=m_end,
                            lines_of_code=(m_end - m_start + 1)
                        ))
                classes[node.name] = ClassDetail(
                    name=node.name,
                    bases=bases,
                    start_line=node.lineno,
                    end_line=getattr(node, 'end_lineno', node.lineno),
                    methods=methods
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn_params = parse_parameters(node.args)
                fn_ret = ast.unparse(node.returns) if node.returns else None
                fn_start = node.lineno
                fn_end = getattr(node, 'end_lineno', fn_start)
                functions[node.name] = FunctionDetail(
                    name=node.name,
                    parameters=fn_params,
                    returns=fn_ret,
                    calls=[],
                    start_line=fn_start,
                    end_line=fn_end,
                    lines_of_code=(fn_end - fn_start + 1)
                )

        return functions, classes, imports, tree
    except SyntaxError:
        # Fallback parsing for JavaScript & TypeScript
        import tempfile
        from app.services.js_ts_ast import analyze_js_ts_file
        ext = ".js"
        if file_path:
            ext = os.path.splitext(file_path)[1] or ".js"
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=ext, encoding="utf-8") as tmp:
            tmp.write(source_code)
            tmp_path = tmp.name

        try:
            js_ast = analyze_js_ts_file(tmp_path, file_path or "temp_file.js")
            functions = {f.name: f for f in js_ast.functions}
            classes = {c.name: c for c in js_ast.classes}
            imports = js_ast.imports
            return functions, classes, imports, None
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

def _scan_workspace_call_sites(project_dir: str, target_symbol: str, req_param_count: int) -> List[Tuple[str, int, str]]:
    """
    Scans project workspace AST for calls to target_symbol.
    Returns list of (relative_file_path, line_number, call_snippet) that violate required parameter count.
    """
    call_sites = []
    ignored_dirs = {"__pycache__", ".git", "node_modules", ".venv", "venv", "env", ".pytest_cache", "scratch"}

    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for file in files:
            if file.endswith(".py"):
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, project_dir).replace("\\", "/")
                
                try:
                    with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                        code = f.read()
                    file_tree = ast.parse(code)
                except Exception:
                    continue

                class CallFinder(ast.NodeVisitor):
                    def visit_Call(self, node: ast.Call):
                        # Match function name
                        func_name = None
                        if isinstance(node.func, ast.Name):
                            func_name = node.func.id
                        elif isinstance(node.func, ast.Attribute):
                            func_name = node.func.attr

                        if func_name == target_symbol:
                            arg_count = len(node.args)
                            kw_count = len(node.keywords)
                            total_provided = arg_count + kw_count
                            if total_provided < req_param_count:
                                snippet = ast.unparse(node)
                                call_sites.append((rel_path, node.lineno, snippet))
                        self.generic_visit(node)

                finder = CallFinder()
                finder.visit(file_tree)

    return call_sites

def _find_dependent_files(project_dir: str, target_rel_path: str) -> List[str]:
    """Finds project workspace files that import or reference the target file."""
    dependent_files = set()
    module_base = os.path.splitext(os.path.basename(target_rel_path))[0]
    ignored_dirs = {"__pycache__", ".git", "node_modules", ".venv", "venv", "env", ".pytest_cache", "scratch"}

    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for file in files:
            if file.endswith(".py"):
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, project_dir).replace("\\", "/")
                if rel_path == target_rel_path:
                    continue
                try:
                    with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    if module_base in content:
                        dependent_files.add(rel_path)
                except Exception:
                    pass

    return sorted(list(dependent_files))

def analyze_breaking_changes(
    project_id: str,
    relative_path: str,
    modified_code: str,
    force_refresh: bool = False
) -> BreakingChangeAnalysisResponse:
    """
    Performs fast local AST static comparison between original code and modified code.
    Detects signature shifts, parameter additions/removals/renames, class/method removals,
    broken imports, call site violations, and dependency impact.
    """
    project_dir = get_project_directory(project_id)
    clean_rel = relative_path.replace("\\", "/")
    abs_src_path = _ensure_safe_path(project_dir, clean_rel)

    if not os.path.exists(abs_src_path):
        raise FileNotFoundError(f"Source file '{relative_path}' not found in project workspace.")

    with open(abs_src_path, "r", encoding="utf-8", errors="ignore") as f:
        orig_code = f.read()

    orig_hash = _compute_hash(orig_code)
    mod_hash = _compute_hash(modified_code)
    cache_key = f"breaking:{project_id}:{clean_rel}:{orig_hash}:{mod_hash}"
    cache = _read_cache(project_dir)

    if not force_refresh and cache_key in cache:
        cached_data = cache[cache_key]
        cached_data["is_cached"] = True
        return BreakingChangeAnalysisResponse.model_validate(cached_data)

    changes: List[BreakingChangeItem] = []

    # Parse AST for original and modified code
    try:
        orig_fns, orig_cls, orig_imp, orig_tree = _extract_ast_nodes_from_code(orig_code)
    except SyntaxError as err:
        return BreakingChangeAnalysisResponse(
            has_breaking_changes=True,
            summary=f"Original source code contains syntax error: {str(err)}",
            total_changes=1,
            high_severity_count=1,
            changes=[BreakingChangeItem(
                type="SYNTAX_ERROR",
                severity="HIGH",
                file=clean_rel,
                symbol="file",
                description=f"Original file failed AST parsing: {str(err)}"
            )]
        )

    try:
        mod_fns, mod_cls, mod_imp, mod_tree = _extract_ast_nodes_from_code(modified_code)
    except SyntaxError as err:
        return BreakingChangeAnalysisResponse(
            has_breaking_changes=True,
            summary=f"Modified refactored code contains invalid Python syntax.",
            total_changes=1,
            high_severity_count=1,
            changes=[BreakingChangeItem(
                type="SYNTAX_ERROR",
                severity="HIGH",
                file=clean_rel,
                symbol="file",
                description=f"Modified code contains invalid Python syntax: {str(err)}"
            )]
        )

    dependent_files = _find_dependent_files(project_dir, clean_rel)

    # 1. FUNCTION REMOVAL & RENAMING DETECTION
    removed_fn_names = set(orig_fns.keys()) - set(mod_fns.keys())
    added_fn_names = set(mod_fns.keys()) - set(orig_fns.keys())

    for fn_name in list(removed_fn_names):
        orig_fn = orig_fns[fn_name]
        is_private = fn_name.startswith("_") and not fn_name.startswith("__")
        
        # Check potential rename
        potential_rename = None
        for add_name in added_fn_names:
            add_fn = mod_fns[add_name]
            # If parameter count and names match closely
            orig_p_names = [p.name for p in orig_fn.parameters]
            add_p_names = [p.name for p in add_fn.parameters]
            if orig_p_names == add_p_names:
                potential_rename = add_name
                break

        if potential_rename:
            changes.append(BreakingChangeItem(
                type="FUNCTION_RENAMED",
                severity="HIGH" if not is_private else "MEDIUM",
                file=clean_rel,
                symbol=fn_name,
                line_before=orig_fn.start_line,
                description=f"Function '{fn_name}' renamed to '{potential_rename}'. Callers referencing '{fn_name}' will fail.",
                affected_files=dependent_files,
                affected_symbols=[fn_name],
                confidence=0.8,
                before_snippet=f"def {fn_name}(...)",
                after_snippet=f"def {potential_rename}(...)"
            ))
            added_fn_names.discard(potential_rename)
        else:
            changes.append(BreakingChangeItem(
                type="FUNCTION_REMOVED",
                severity="HIGH" if not is_private else "LOW",
                file=clean_rel,
                symbol=fn_name,
                line_before=orig_fn.start_line,
                description=f"Function '{fn_name}' was removed. Callers depending on this symbol will raise NameError/AttributeError.",
                affected_files=dependent_files,
                affected_symbols=[fn_name],
                confidence=1.0 if not is_private else 0.6,
                before_snippet=f"def {fn_name}(...)"
            ))

    # 2. FUNCTION SIGNATURE & PARAMETER DIFFERENCE DETECTION
    common_fns = set(orig_fns.keys()) & set(mod_fns.keys())
    for fn_name in common_fns:
        o_fn = orig_fns[fn_name]
        m_fn = mod_fns[fn_name]

        o_params = o_fn.parameters
        m_params = m_fn.parameters

        o_req_count = len([p for p in o_params if p.default is None and not p.name.startswith("*")])
        m_req_count = len([p for p in m_params if p.default is None and not p.name.startswith("*")])

        o_names = [p.name for p in o_params if not p.name.startswith("*")]
        m_names = [p.name for p in m_params if not p.name.startswith("*")]

        # Case A: Parameter Renamed (Same parameter count, different parameter names at same position)
        is_rename_only = False
        if len(o_names) == len(m_names) and o_names != m_names:
            renamed_pairs = []
            for idx, (on, mn) in enumerate(zip(o_names, m_names)):
                if on != mn:
                    renamed_pairs.append((on, mn))
                    changes.append(BreakingChangeItem(
                        type="PARAMETER_RENAMED",
                        severity="MEDIUM",
                        file=clean_rel,
                        symbol=f"{fn_name}({mn})",
                        line_before=o_fn.start_line,
                        line_after=m_fn.start_line,
                        description=f"Parameter '{on}' renamed to '{mn}' in function '{fn_name}'. Keyword calls '{fn_name}({on}=...)' will fail.",
                        affected_files=dependent_files,
                        affected_symbols=[fn_name],
                        confidence=0.9,
                        before_snippet=f"{fn_name}({on}=...)",
                        after_snippet=f"{fn_name}({mn}=...)"
                    ))
            if renamed_pairs:
                is_rename_only = True

        if not is_rename_only:
            # Case B: Parameter Removed
            removed_params = set(o_names) - set(m_names)
            if removed_params:
                changes.append(BreakingChangeItem(
                    type="PARAMETER_REMOVED",
                    severity="HIGH",
                    file=clean_rel,
                    symbol=f"{fn_name}()",
                    line_before=o_fn.start_line,
                    line_after=m_fn.start_line,
                    description=f"Function '{fn_name}' removed parameter(s): {', '.join(sorted(removed_params))}. Callers passing these arguments will break.",
                    affected_files=dependent_files,
                    affected_symbols=[fn_name],
                    confidence=1.0,
                    before_snippet=f"def {fn_name}({', '.join(o_names)})",
                    after_snippet=f"def {fn_name}({', '.join(m_names)})"
                ))

            # Case C: Parameter Added
            added_params = [p for p in m_params if p.name not in set(o_names) and not p.name.startswith("*")]
            for p in added_params:
                if p.default is None:
                    # Required parameter added
                    changes.append(BreakingChangeItem(
                        type="PARAMETER_ADDED",
                        severity="HIGH",
                        file=clean_rel,
                        symbol=f"{fn_name}({p.name})",
                        line_before=o_fn.start_line,
                        line_after=m_fn.start_line,
                        description=f"Function '{fn_name}' added a required parameter '{p.name}' with no default value. Existing call sites will fail missing positional argument.",
                        affected_files=dependent_files,
                        affected_symbols=[fn_name],
                        confidence=1.0,
                        before_snippet=f"def {fn_name}({', '.join(o_names)})",
                        after_snippet=f"def {fn_name}({', '.join(m_names)})"
                    ))

                    # Scan Call-Sites across workspace for this function
                    call_sites = _scan_workspace_call_sites(project_dir, fn_name, m_req_count)
                    for cs_file, cs_line, cs_snippet in call_sites:
                        changes.append(BreakingChangeItem(
                            type="BREAKING_CALL_SITE",
                            severity="HIGH",
                            file=cs_file,
                            symbol=fn_name,
                            line_before=cs_line,
                            description=f"Call site '{cs_snippet}' in '{cs_file}:L{cs_line}' fails new required parameter count ({m_req_count} required).",
                            affected_files=[cs_file],
                            affected_symbols=[fn_name],
                            confidence=1.0,
                            before_snippet=cs_snippet
                        ))

                else:
                    # Optional parameter added with default
                    changes.append(BreakingChangeItem(
                        type="PARAMETER_ADDED",
                        severity="LOW",
                        file=clean_rel,
                        symbol=f"{fn_name}({p.name}={p.default})",
                        line_before=o_fn.start_line,
                        line_after=m_fn.start_line,
                        description=f"Function '{fn_name}' added an optional parameter '{p.name}' with default value ({p.default}). Non-breaking API addition.",
                        affected_files=[],
                        affected_symbols=[fn_name],
                        confidence=1.0,
                        before_snippet=f"def {fn_name}({', '.join(o_names)})",
                        after_snippet=f"def {fn_name}({', '.join(m_names)})"
                    ))

        # Case D: Default Value Changed
        for op, mp in zip(o_params, m_params):
            if op.name == mp.name and op.default != mp.default:
                if op.default is not None and mp.default is not None:
                    changes.append(BreakingChangeItem(
                        type="DEFAULT_VALUE_CHANGED",
                        severity="MEDIUM",
                        file=clean_rel,
                        symbol=f"{fn_name}({mp.name})",
                        line_before=o_fn.start_line,
                        line_after=m_fn.start_line,
                        description=f"Default value for parameter '{mp.name}' changed from '{op.default}' to '{mp.default}' in '{fn_name}'. Potential behavior shift.",
                        affected_files=dependent_files,
                        affected_symbols=[fn_name],
                        confidence=0.85,
                        before_snippet=f"{mp.name}={op.default}",
                        after_snippet=f"{mp.name}={mp.default}"
                    ))

    # 3. CLASS & METHOD REMOVAL & INHERITANCE DETECTION
    removed_classes = set(orig_cls.keys()) - set(mod_cls.keys())
    for cls_name in removed_classes:
        o_cls = orig_cls[cls_name]
        changes.append(BreakingChangeItem(
            type="CLASS_REMOVED",
            severity="HIGH",
            file=clean_rel,
            symbol=cls_name,
            line_before=o_cls.start_line,
            description=f"Class '{cls_name}' was removed. Callers instantiating or inheriting from this class will raise NameError.",
            affected_files=dependent_files,
            affected_symbols=[cls_name],
            confidence=1.0,
            before_snippet=f"class {cls_name}:"
        ))

    common_classes = set(orig_cls.keys()) & set(mod_cls.keys())
    for cls_name in common_classes:
        o_c = orig_cls[cls_name]
        m_c = mod_cls[cls_name]

        # Base class changes
        if o_c.bases != m_c.bases:
            changes.append(BreakingChangeItem(
                type="BASE_CLASS_CHANGED",
                severity="MEDIUM",
                file=clean_rel,
                symbol=cls_name,
                line_before=o_c.start_line,
                line_after=m_c.start_line,
                description=f"Base class inheritance of '{cls_name}' changed from ({', '.join(o_c.bases)}) to ({', '.join(m_c.bases)}).",
                affected_files=dependent_files,
                affected_symbols=[cls_name],
                confidence=0.85,
                before_snippet=f"class {cls_name}({', '.join(o_c.bases)}):",
                after_snippet=f"class {cls_name}({', '.join(m_c.bases)}):"
            ))

        # Method removal
        o_methods = {m.name: m for m in o_c.methods}
        m_methods = {m.name: m for m in m_c.methods}

        removed_methods = set(o_methods.keys()) - set(m_methods.keys())
        for m_name in removed_methods:
            is_priv = m_name.startswith("_") and not m_name.startswith("__")
            changes.append(BreakingChangeItem(
                type="METHOD_REMOVED",
                severity="HIGH" if not is_priv else "LOW",
                file=clean_rel,
                symbol=f"{cls_name}.{m_name}",
                line_before=o_methods[m_name].start_line,
                description=f"Method '{m_name}' removed from class '{cls_name}'. Callers invoking '{cls_name}.{m_name}()' will fail with AttributeError.",
                affected_files=dependent_files,
                affected_symbols=[f"{cls_name}.{m_name}"],
                confidence=1.0 if not is_priv else 0.6,
                before_snippet=f"def {m_name}(self, ...)"
            ))

    # 4. IMPORT REMOVAL & BROKEN IMPORT DETECTION
    orig_imp_symbols = {imp.alias or imp.name or imp.module for imp in orig_imp if (imp.alias or imp.name or imp.module)}
    mod_imp_symbols = {imp.alias or imp.name or imp.module for imp in mod_imp if (imp.alias or imp.name or imp.module)}

    removed_import_symbols = orig_imp_symbols - mod_imp_symbols
    for sym in removed_import_symbols:
        # Check if sym is referenced in modified code body
        if sym and sym in modified_code:
            changes.append(BreakingChangeItem(
                type="BROKEN_IMPORT",
                severity="HIGH",
                file=clean_rel,
                symbol=sym,
                description=f"Import '{sym}' was removed, but symbol is still referenced in code body.",
                affected_files=[clean_rel],
                affected_symbols=[sym],
                confidence=1.0,
                before_snippet=f"from ... import {sym}"
            ))

    # Summarize & Classify Severity Counts
    high_count = sum(1 for c in changes if c.severity == "HIGH")
    med_count = sum(1 for c in changes if c.severity == "MEDIUM")
    low_count = sum(1 for c in changes if c.severity in ["LOW", "INFO"])

    has_breaking = high_count > 0 or med_count > 0
    summary_text = (
        f"Detected {len(changes)} change(s) ({high_count} HIGH, {med_count} MEDIUM, {low_count} LOW/INFO)."
        if changes else "No breaking changes detected."
    )

    response_obj = BreakingChangeAnalysisResponse(
        has_breaking_changes=has_breaking,
        summary=summary_text,
        total_changes=len(changes),
        high_severity_count=high_count,
        medium_severity_count=med_count,
        low_severity_count=low_count,
        changes=changes,
        is_cached=False
    )

    cache[cache_key] = response_obj.model_dump()
    _write_cache(project_dir, cache)

    return response_obj

def _build_breaking_explanation_prompt(
    file_path: str,
    changes: List[Dict[str, Any]]
) -> str:
    return (
        f"You are an expert Python software architect and API compatibility engineer. "
        f"Analyze the following static breaking changes detected between original and refactored versions of '{file_path}'.\n\n"
        f"DETECTED BREAKING CHANGES:\n"
        f"{json.dumps(changes, indent=2)}\n\n"
        f"INSTRUCTIONS:\n"
        f"1. Explain clearly why these API signature/symbol changes will break existing downstream callers.\n"
        f"2. List affected project components.\n"
        f"3. Provide actionable developer migration fixes.\n"
        f"4. Propose backward-compatible alternative refactorings (e.g. deprecation aliases, optional default parameters).\n"
        f"Respond ONLY with valid JSON strictly matching the Pydantic schema with keys: 'explanation', 'why_it_breaks', 'affected_components', 'recommended_fixes', 'backward_compatible_alternatives'."
    )

async def explain_breaking_changes(
    project_id: str,
    file_path: str,
    changes: List[BreakingChangeItem],
    force_refresh: bool = False
) -> BreakingChangeExplanationResponse:
    """
    Queries Groq AI on-demand to generate human-readable technical explanations,
    impact assessments, migration steps, and backward-compatible alternatives.
    """
    project_dir = get_project_directory(project_id)
    clean_rel = file_path.replace("\\", "/")

    changes_dicts = [c.model_dump() for c in changes]
    changes_hash = _compute_hash(json.dumps(changes_dicts, sort_keys=True))
    cache_key = f"breaking_exp:{project_id}:{clean_rel}:{changes_hash}"
    cache = _read_cache(project_dir)

    # 1. Check Cache
    if not force_refresh and cache_key in cache:
        print(f"AI Provider: groq | Model: Groq | Request type: breaking_exp | Target: {clean_rel} | Cache: HIT")
        cached_data = cache[cache_key]
        cached_data["is_cached"] = True
        return BreakingChangeExplanationResponse.model_validate(cached_data)

    # 2. In-Flight Request Deduplication Guard
    if cache_key in _IN_FLIGHT_BREAKING_REQUESTS:
        print(f"AI Provider: groq | Deduplicated breaking change explanation request joined.")
        return await _IN_FLIGHT_BREAKING_REQUESTS[cache_key]

    async def _execute_explanation():
        provider = get_ai_provider()
        is_fallback = False

        if provider.is_configured:
            try:
                prompt = _build_breaking_explanation_prompt(clean_rel, changes_dicts)
                res: BreakingChangeExplanationModel = await provider.generate_structured(
                    prompt=prompt,
                    schema_class=BreakingChangeExplanationModel,
                    max_tokens=int(os.getenv("GROQ_MAX_OUTPUT_TOKENS", os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "1000")))
                )
                explanation_text = res.explanation
                why_breaks = res.why_it_breaks
                aff_comps = res.affected_components
                rec_fixes = res.recommended_fixes
                compat_alts = res.backward_compatible_alternatives
            except Exception as exc:
                print(f"[Breaking Change Explanation AI Notice]: {exc}. Using static fallback explanation.")
                explanation_text = f"Static analysis explanation fallback ({str(exc)[:80]})."
                why_breaks = [f"Change '{c.symbol}' ({c.type}): {c.description}" for c in changes if c.severity == "HIGH"]
                aff_comps = sorted(list(set(sum([c.affected_files for c in changes], []))))
                rec_fixes = ["Update existing caller invocations to pass all required arguments.", "Revert removed symbols or add deprecation wrappers."]
                compat_alts = ["Provide default parameter values (e.g. `param=None`) to maintain caller compatibility."]
                is_fallback = True
        else:
            explanation_text = "Static analysis explanation (AI Provider unconfigured)."
            why_breaks = [f"Change '{c.symbol}' ({c.type}): {c.description}" for c in changes if c.severity == "HIGH"]
            aff_comps = sorted(list(set(sum([c.affected_files for c in changes], []))))
            rec_fixes = ["Update existing caller invocations to pass all required arguments."]
            compat_alts = ["Provide default parameter values to preserve backward compatibility."]
            is_fallback = True

        response_obj = BreakingChangeExplanationResponse(
            explanation=explanation_text,
            why_it_breaks=why_breaks,
            affected_components=aff_comps,
            recommended_fixes=rec_fixes,
            backward_compatible_alternatives=compat_alts,
            is_cached=False,
            is_fallback=is_fallback
        )

        cache[cache_key] = response_obj.model_dump()
        _write_cache(project_dir, cache)

        return response_obj

    task = asyncio.create_task(_execute_explanation())
    _IN_FLIGHT_BREAKING_REQUESTS[cache_key] = task
    try:
        return await task
    finally:
        _IN_FLIGHT_BREAKING_REQUESTS.pop(cache_key, None)
