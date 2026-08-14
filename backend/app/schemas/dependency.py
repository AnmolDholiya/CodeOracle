from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class DependencyNode(BaseModel):
    id: str
    label: str
    type: str = "file"
    relative_path: str
    lines_of_code: int = 0
    classes_count: int = 0
    functions_count: int = 0
    has_syntax_error: bool = False
    project_dependencies: List[str] = []
    external_libraries: List[str] = []
    unresolved_imports: List[str] = []

class DependencyEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship: str = "imports"

class ExternalLibraryDetail(BaseModel):
    name: str
    top_module: str
    type: str  # "third_party" or "standard_library"
    imports: List[str] = []

class DependencyGraphResponse(BaseModel):
    project_id: str
    total_nodes: int
    total_edges: int
    nodes: List[DependencyNode]
    edges: List[DependencyEdge]
    external_libraries: List[ExternalLibraryDetail] = []
    unresolved_imports: List[str] = []
    external_imports: List[str] = []
    created_at: str
