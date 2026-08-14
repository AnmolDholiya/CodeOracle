from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class FileDetail(BaseModel):
    relative_path: str
    absolute_path: str
    extension: str
    size_bytes: int
    lines_of_code: int
    language: str

class ProjectMetadata(BaseModel):
    project_id: str
    original_filename: str
    extracted_path: str
    total_files: int
    total_lines_of_code: int
    languages: List[str]
    files: List[FileDetail]
    created_at: str

class CleanupResponse(BaseModel):
    status: str
    message: str
    project_id: str

class ProjectStatusResponse(BaseModel):
    project_id: str
    status: str  # processing | completed | failed
    stage: str   # uploading | extracting | discovering_files | analyzing_python | building_dependencies | completed | failed
    progress: int # 0 - 100
    message: str
    error: Optional[str] = None

class UploadResponse(BaseModel):
    project_id: str
    status: str
    message: str

class GitHubRepoRequest(BaseModel):
    repo_url: str = Field(..., example="https://github.com/AnmolDholiya/student-portfolio.git")
