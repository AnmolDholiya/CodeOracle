from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ParameterDetail(BaseModel):
    name: str
    annotation: Optional[str] = None
    default: Optional[str] = None

class FunctionDetail(BaseModel):
    name: str
    parameters: List[ParameterDetail] = []
    returns: Optional[str] = None
    calls: List[str] = []
    start_line: int
    end_line: int
    docstring: Optional[str] = None
    lines_of_code: int
    is_async: bool = False

class ClassDetail(BaseModel):
    name: str
    bases: List[str] = []
    start_line: int
    end_line: int
    docstring: Optional[str] = None
    methods: List[FunctionDetail] = []

class ImportDetail(BaseModel):
    module: Optional[str] = None
    name: Optional[str] = None
    alias: Optional[str] = None
    line_number: int
    import_type: str = "es_module"  # es_module | commonjs

class ExportDetail(BaseModel):
    exported_name: str
    local_name: Optional[str] = None
    is_default: bool = False
    export_type: str = "named"  # default | named | commonjs
    line_number: int

class InterfaceDetail(BaseModel):
    name: str
    properties: List[str] = []
    line_number: int

class TypeDetail(BaseModel):
    name: str
    definition: Optional[str] = None
    line_number: int

class ComponentDetail(BaseModel):
    name: str
    props: List[str] = []
    line_number: int

class ASTFileAnalysis(BaseModel):
    relative_path: str
    absolute_path: str
    lines_of_code: int
    language: str = "Python"  # Python | JavaScript | TypeScript | JSX | TSX
    has_syntax_error: bool = False
    syntax_error_message: Optional[str] = None
    imports: List[ImportDetail] = []
    exports: List[ExportDetail] = []
    classes: List[ClassDetail] = []
    functions: List[FunctionDetail] = []
    global_calls: List[str] = []
    interfaces: List[InterfaceDetail] = []
    types: List[TypeDetail] = []
    components: List[ComponentDetail] = []

# Alias for backwards compatibility
PythonFileAnalysis = ASTFileAnalysis

class ProjectAnalysisResponse(BaseModel):
    project_id: str
    total_files_analyzed: int = 0
    total_python_files: int = 0
    total_javascript_files: int = 0
    total_typescript_files: int = 0
    total_lines_of_code: int = 0
    total_classes: int = 0
    total_functions: int = 0
    total_imports: int = 0
    total_exports: int = 0
    files_analyzed: List[ASTFileAnalysis] = []
    created_at: str
