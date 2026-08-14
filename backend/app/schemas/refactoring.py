from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List, Literal

class CodeIssue(BaseModel):
    type: str = Field(default="maintainability", description="Type of issue, e.g. complexity, readability, poor_naming, long_function")
    description: str = Field(default="", description="Detailed description of the issue")
    severity: str = Field(default="medium", description="Severity level: low, medium, or high")

    @field_validator("severity", mode="before")
    @classmethod
    def validate_severity(cls, v):
        val = str(v).lower().strip()
        if val in ["low", "medium", "high"]:
            return val
        return "medium"

class CodeImprovement(BaseModel):
    type: str = Field(default="readability", description="Type of improvement made")
    description: str = Field(default="", description="Description of the improvement")

class AIRefactorResponseModel(BaseModel):
    summary: str = Field(default="Code refactored for improved readability and maintainability.", description="High-level summary of refactoring")
    issues_found: List[CodeIssue] = Field(default=[], description="List of code smells or quality issues identified")
    improvements: List[CodeImprovement] = Field(default=[], description="List of modernizing improvements applied")
    refactored_code: str = Field(default="", description="Clean refactored Python source code")
    explanation: List[str] = Field(default=[], description="Step-by-step breakdown of refactoring decisions")
    potential_risks: List[str] = Field(default=[], description="Potential risks or behavior caveats to consider")
    new_dependencies: List[str] = Field(default=[], description="New import packages or libraries introduced")

    @field_validator("explanation", "potential_risks", "new_dependencies", mode="before")
    @classmethod
    def normalize_str_list(cls, v):
        if isinstance(v, str):
            return [v.strip()]
        if isinstance(v, list):
            res = []
            for item in v:
                if isinstance(item, str):
                    res.append(item)
                elif isinstance(item, dict):
                    vals = [str(val) for val in item.values()]
                    res.append(" - ".join(vals))
                else:
                    res.append(str(item))
            return res
        return []

class ValidationMetrics(BaseModel):
    syntax_valid: bool = True
    tests_passed: bool = True
    coverage: float = 0.0
    before_tests: Dict[str, Any] = Field(default_factory=dict)
    after_tests: Dict[str, Any] = Field(default_factory=dict)

class RefactorResultResponse(BaseModel):
    status: str = "success"
    file_path: str
    function_name: Optional[str] = None
    summary: str
    issues_found: List[CodeIssue] = []
    improvements: List[CodeImprovement] = []
    original_code: str
    refactored_code: str
    explanation: List[str] = []
    potential_risks: List[str] = []
    new_dependencies: List[str] = []
    validation: ValidationMetrics
    diff: str
    is_cached: bool = False
    is_fallback: bool = False

class FileRefactorRequest(BaseModel):
    file_path: str
    force_refresh: bool = False

class FunctionRefactorRequest(BaseModel):
    file_path: str
    function_name: str
    force_refresh: bool = False

class SaveRefactorRequest(BaseModel):
    file_path: str
    refactored_code: str

class SaveRefactorResponse(BaseModel):
    status: str = "success"
    file_path: str
    message: str = "Refactored code saved successfully."
