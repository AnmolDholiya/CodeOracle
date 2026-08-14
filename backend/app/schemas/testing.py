from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class UnitTestGenRequest(BaseModel):
    file_path: str = Field(..., description="Relative path of target Python file")
    function_name: Optional[str] = Field(None, description="Optional target function name")
    force_refresh: bool = Field(False, description="Force re-generation bypassing cache")

class GeneratedUnitTestModel(BaseModel):
    test_code: str = Field(..., description="Valid executable Python pytest code containing unit test functions.")
    summary: str = Field(..., description="Short explanation of tests generated and cases covered.")

class UnitTestGenResponse(BaseModel):
    file_path: str
    function_name: Optional[str] = None
    test_file_path: str
    test_code: str
    summary: Optional[str] = "Unit tests generated successfully."
    status: str = "generated"
    is_cached: bool = False
    is_fallback: bool = False
    language: str = "python"
    framework: str = "pytest"

class TestExecutionRequest(BaseModel):
    file_path: str = Field(..., description="Target file path")
    test_file_path: Optional[str] = Field(None, description="Specific generated test file relative path")
    timeout_seconds: Optional[int] = Field(30, description="Execution timeout limit")

class TestExecutionResult(BaseModel):
    status: str  # "passed", "failed", "error", "timeout"
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    stdout: str = ""
    stderr: str = ""
    language: str = "python"
    framework: str = "pytest"
    missing_dependencies: List[str] = []

class FileCoverageDetail(BaseModel):
    file_path: str
    coverage_percentage: float = 0.0
    statements: int = 0
    missed: int = 0
    missing_lines: List[str] = []

class CoverageResult(BaseModel):
    overall_coverage: float = 0.0
    total_statements: int = 0
    total_missed: int = 0
    files: List[FileCoverageDetail] = []
    language: str = "python"
    framework: str = "coverage.py"
