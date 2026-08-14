import ast
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Set, Tuple
from app.schemas.ast import (
    ASTFileAnalysis,
    PythonFileAnalysis,
    ImportDetail,
    ClassDetail,
    FunctionDetail,
    ParameterDetail,
    ProjectAnalysisResponse
)
from app.schemas.project import ProjectMetadata, FileDetail
from app.services.file_classifier import (
    is_ignored_directory,
    is_binary_extension,
    should_analyze_source_file,
    get_file_language,
    IGNORED_DIRS,
    BINARY_EXTENSIONS,
    LANGUAGE_MAP
)

class CallVisitor(ast.NodeVisitor):
    """AST NodeVisitor to collect function/method calls inside a block."""
    def __init__(self):
        self.calls: Set[str] = set()

    def visit_Call(self, node: ast.Call):
        call_name = self._get_call_name(node.func)
        if call_name:
            self.calls.add(call_name)
        self.generic_visit(node)

    def _get_call_name(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            val = self._get_call_name(node.value)
            if val:
                return f"{val}.{node.attr}"
            return node.attr
        elif isinstance(node, ast.Call):
            return self._get_call_name(node.func)
        return None

def parse_parameters(args_node: ast.arguments) -> List[ParameterDetail]:
    """Extracts function parameter names, annotations, and default values."""
    params: List[ParameterDetail] = []
    
    # Calculate position offset for defaults
    num_args = len(args_node.args)
    num_defaults = len(args_node.defaults)
    default_offset = num_args - num_defaults

    # Positional / standard arguments
    for idx, arg in enumerate(args_node.args):
        annotation_str = ast.unparse(arg.annotation) if arg.annotation else None
        default_str = None
        if idx >= default_offset:
            default_node = args_node.defaults[idx - default_offset]
            default_str = ast.unparse(default_node)
            
        params.append(ParameterDetail(
            name=arg.arg,
            annotation=annotation_str,
            default=default_str
        ))

    # *vararg (*args)
    if args_node.vararg:
        var_annotation = ast.unparse(args_node.vararg.annotation) if args_node.vararg.annotation else None
        params.append(ParameterDetail(
            name=f"*{args_node.vararg.arg}",
            annotation=var_annotation,
            default=None
        ))

    # Keyword-only arguments
    for idx, arg in enumerate(args_node.kwonlyargs):
        annotation_str = ast.unparse(arg.annotation) if arg.annotation else None
        default_str = None
        if idx < len(args_node.kw_defaults) and args_node.kw_defaults[idx] is not None:
            default_str = ast.unparse(args_node.kw_defaults[idx])
        params.append(ParameterDetail(
            name=arg.arg,
            annotation=annotation_str,
            default=default_str
        ))

    # **kwarg (**kwargs)
    if args_node.kwarg:
        kw_annotation = ast.unparse(args_node.kwarg.annotation) if args_node.kwarg.annotation else None
        params.append(ParameterDetail(
            name=f"**{args_node.kwarg.arg}",
            annotation=kw_annotation,
            default=None
        ))

    return params

def extract_function_detail(node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionDetail:
    """Extracts metadata from a function or async function definition."""
    params = parse_parameters(node.args)
    
    # Return type annotation or return statements
    return_annotation = ast.unparse(node.returns) if node.returns else None
    
    # Collect calls inside function body
    visitor = CallVisitor()
    for stmt in node.body:
        visitor.visit(stmt)
    calls = sorted(list(visitor.calls))

    # Extract docstring if present
    docstring = ast.get_docstring(node)

    start_line = node.lineno
    end_line = getattr(node, 'end_lineno', start_line)
    loc = (end_line - start_line + 1)

    return FunctionDetail(
        name=node.name,
        parameters=params,
        returns=return_annotation,
        calls=calls,
        start_line=start_line,
        end_line=end_line,
        docstring=docstring,
        lines_of_code=loc
    )

def extract_class_detail(node: ast.ClassDef) -> ClassDetail:
    """Extracts metadata from a class definition including methods and inheritance."""
    bases = [ast.unparse(b) for b in node.bases]
    docstring = ast.get_docstring(node)
    
    methods: List[FunctionDetail] = []
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(extract_function_detail(item))

    start_line = node.lineno
    end_line = getattr(node, 'end_lineno', start_line)

    return ClassDetail(
        name=node.name,
        bases=bases,
        start_line=start_line,
        end_line=end_line,
        docstring=docstring,
        methods=methods
    )

def analyze_python_file(file_path: str, relative_path: str) -> PythonFileAnalysis:
    """Parses a Python source file into structured AST analysis metadata."""
    lines_of_code = 0
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            lines_of_code = len([l for l in content.splitlines() if l.strip()])
    except Exception as read_err:
        return PythonFileAnalysis(
            relative_path=relative_path,
            absolute_path=file_path,
            lines_of_code=0,
            has_syntax_error=True,
            syntax_error_message=f"Failed to read file: {str(read_err)}"
        )

    # Attempt to parse AST with error handling for malformed Python files
    try:
        tree = ast.parse(content, filename=file_path)
    except Exception as parse_err:
        return PythonFileAnalysis(
            relative_path=relative_path,
            absolute_path=file_path,
            lines_of_code=lines_of_code,
            has_syntax_error=True,
            syntax_error_message=f"Syntax error during AST parsing: {str(parse_err)}"
        )

    imports: List[ImportDetail] = []
    classes: List[ClassDetail] = []
    functions: List[FunctionDetail] = []
    global_calls_set: Set[str] = set()

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
            classes.append(extract_class_detail(node))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(extract_function_detail(node))
        else:
            # Check global scope calls (e.g. if __name__ == '__main__': main())
            visitor = CallVisitor()
            visitor.visit(node)
            global_calls_set.update(visitor.calls)

    return PythonFileAnalysis(
        relative_path=relative_path,
        absolute_path=file_path,
        lines_of_code=lines_of_code,
        has_syntax_error=False,
        syntax_error_message=None,
        imports=imports,
        classes=classes,
        functions=functions,
        global_calls=sorted(list(global_calls_set))
    )

def _analyze_single_file_worker(item: Tuple[str, str, str]) -> Tuple[ASTFileAnalysis, int]:
    """Worker function for concurrent AST parsing."""
    abs_path, rel_path, ext = item
    from app.services.js_ts_ast import analyze_js_ts_file
    
    if ext == ".py":
        analysis = analyze_python_file(abs_path, rel_path)
    else:
        analysis = analyze_js_ts_file(abs_path, rel_path)
        
    try:
        size = os.path.getsize(abs_path)
    except Exception:
        size = 0
        
    return analysis, size

def _count_lines_worker(item: Tuple[str, str, str]) -> Tuple[str, str, str, int, int, str]:
    """Worker function for non-source file line counts."""
    abs_path, rel_path, ext = item
    lang = get_file_language(ext)
    lines_count = 0
    size = 0
    try:
        size = os.path.getsize(abs_path)
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            lines_count = sum(1 for line in f if line.strip())
    except Exception:
        pass
    return rel_path, abs_path, ext, size, lines_count, lang

def scan_and_analyze_workspace(
    project_dir: str,
    project_id: str,
    original_filename: str = "Codebase"
) -> Tuple[ProjectMetadata, ProjectAnalysisResponse]:
    """Unified single-pass scanner and parallel AST analyzer.
    
    Discovers files, computes line counts, and parses Python/JS/TS ASTs concurrently
    with a bounded worker pool without reading files multiple times.
    """
    source_tasks: List[Tuple[str, str, str]] = []
    other_tasks: List[Tuple[str, str, str]] = []
    
    # Single directory walk
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if not is_ignored_directory(d)]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if is_binary_extension(ext):
                continue
            if file in {"status.json", "project_metadata.json", "analysis_ast.json", "dependency_graph.json", "explanation_cache.json", "uploaded_archive.zip"}:
                continue
                
            abs_path = os.path.join(root, file)
            rel_path = os.path.relpath(abs_path, project_dir).replace("\\", "/")
            
            if should_analyze_source_file(file):
                source_tasks.append((abs_path, rel_path, ext))
            else:
                other_tasks.append((abs_path, rel_path, ext))

    # Determine bounded worker pool size based on CPU cores (max 4 to protect Render container memory)
    max_workers = min(4, max(2, (os.cpu_count() or 2)))
    
    file_details: List[FileDetail] = []
    file_analyses: List[ASTFileAnalysis] = []
    languages_found: Set[str] = set()
    
    total_loc = 0
    total_classes = 0
    total_functions = 0
    total_imports = 0
    total_exports = 0
    py_count = 0
    js_count = 0
    ts_count = 0

    # 1. Concurrently parse source files (Python, JS, TS)
    if source_tasks:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(_analyze_single_file_worker, source_tasks))
            
        for (analysis, size), (abs_path, rel_path, ext) in zip(results, source_tasks):
            file_analyses.append(analysis)
            lang = get_file_language(ext)
            if lang != "Plain Text":
                languages_found.add(lang)
                
            file_details.append(FileDetail(
                relative_path=rel_path,
                absolute_path=abs_path,
                extension=ext,
                size_bytes=size,
                lines_of_code=analysis.lines_of_code,
                language=lang
            ))
            
            if ext in (".py", ".pyw"):
                py_count += 1
            elif ext in (".js", ".jsx", ".mjs", ".cjs"):
                js_count += 1
            elif ext in (".ts", ".tsx", ".mts", ".cts"):
                ts_count += 1

            total_loc += analysis.lines_of_code
            total_imports += len(analysis.imports)
            total_exports += len(analysis.exports)
            total_classes += len(analysis.classes)
            total_functions += len(analysis.functions)
            for cls in analysis.classes:
                total_functions += len(cls.methods)

    # 2. Concurrently process remaining config & text files (fast LOC count)
    if other_tasks:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            other_results = list(executor.map(_count_lines_worker, other_tasks))
            
        for rel_path, abs_path, ext, size, loc, lang in other_results:
            if lang != "Plain Text":
                languages_found.add(lang)
            total_loc += loc
            file_details.append(FileDetail(
                relative_path=rel_path,
                absolute_path=abs_path,
                extension=ext,
                size_bytes=size,
                lines_of_code=loc,
                language=lang
            ))

    created_time = time.strftime("%Y-%m-%d %H:%M:%S")

    metadata = ProjectMetadata(
        project_id=project_id,
        original_filename=original_filename,
        extracted_path=project_dir,
        total_files=len(file_details),
        total_lines_of_code=total_loc,
        languages=sorted(list(languages_found)),
        files=file_details,
        created_at=created_time
    )

    ast_analysis = ProjectAnalysisResponse(
        project_id=project_id,
        total_files_analyzed=len(file_analyses),
        total_python_files=py_count,
        total_javascript_files=js_count,
        total_typescript_files=ts_count,
        total_lines_of_code=sum(f.lines_of_code for f in file_analyses),
        total_classes=total_classes,
        total_functions=total_functions,
        total_imports=total_imports,
        total_exports=total_exports,
        files_analyzed=file_analyses,
        created_at=created_time
    )

    return metadata, ast_analysis

def analyze_project_workspace(project_dir: str, project_id: str) -> ProjectAnalysisResponse:
    """Scans project directory and performs parallel AST analysis on all Python, JavaScript, and TypeScript files."""
    source_tasks: List[Tuple[str, str, str]] = []
    
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if not is_ignored_directory(d)]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if should_analyze_source_file(file):
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, project_dir).replace("\\", "/")
                source_tasks.append((abs_path, rel_path, ext))

    max_workers = min(4, max(2, (os.cpu_count() or 2)))
    file_analyses: List[ASTFileAnalysis] = []
    total_loc = 0
    total_classes = 0
    total_functions = 0
    total_imports = 0
    total_exports = 0
    py_count = 0
    js_count = 0
    ts_count = 0

    if source_tasks:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(_analyze_single_file_worker, source_tasks))
            
        for (analysis, _), (_, _, ext) in zip(results, source_tasks):
            file_analyses.append(analysis)
            if ext in (".py", ".pyw"):
                py_count += 1
            elif ext in (".js", ".jsx", ".mjs", ".cjs"):
                js_count += 1
            elif ext in (".ts", ".tsx", ".mts", ".cts"):
                ts_count += 1

            total_loc += analysis.lines_of_code
            total_imports += len(analysis.imports)
            total_exports += len(analysis.exports)
            total_classes += len(analysis.classes)
            total_functions += len(analysis.functions)
            for cls in analysis.classes:
                total_functions += len(cls.methods)

    return ProjectAnalysisResponse(
        project_id=project_id,
        total_files_analyzed=len(file_analyses),
        total_python_files=py_count,
        total_javascript_files=js_count,
        total_typescript_files=ts_count,
        total_lines_of_code=total_loc,
        total_classes=total_classes,
        total_functions=total_functions,
        total_imports=total_imports,
        total_exports=total_exports,
        files_analyzed=file_analyses,
        created_at=time.strftime("%Y-%m-%d %H:%M:%S")
    )
