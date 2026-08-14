from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List, Literal

class BreakingChangeItem(BaseModel):
    type: str = Field(..., description="Category of breaking change, e.g. FUNCTION_REMOVED, PARAMETER_ADDED, BREAKING_CALL_SITE")
    severity: str = Field(default="HIGH", description="Severity level: HIGH, MEDIUM, LOW, or INFO")
    file: str = Field(..., description="Relative file path where change occurred")
    symbol: str = Field(..., description="Affected symbol name (function, class, method, parameter)")
    line_before: Optional[int] = Field(default=None, description="Original line number")
    line_after: Optional[int] = Field(default=None, description="Modified line number")
    description: str = Field(default="", description="Detailed human-readable summary of the detected breaking change")
    affected_files: List[str] = Field(default=[], description="List of workspace files impacted by this breaking change")
    affected_symbols: List[str] = Field(default=[], description="List of calling symbols or dependent elements impacted")
    confidence: float = Field(default=1.0, description="Confidence score from 0.0 to 1.0 based on AST evidence")
    before_snippet: Optional[str] = Field(default=None, description="Original code or signature snippet")
    after_snippet: Optional[str] = Field(default=None, description="Modified code or signature snippet")

    @field_validator("severity", mode="before")
    @classmethod
    def validate_severity(cls, v):
        val = str(v).upper().strip()
        if val in ["HIGH", "MEDIUM", "LOW", "INFO"]:
            return val
        return "HIGH"

class BreakingChangeAnalysisRequest(BaseModel):
    file_path: str
    modified_code: str
    force_refresh: bool = False

class BreakingChangeAnalysisResponse(BaseModel):
    has_breaking_changes: bool = False
    summary: str = "No breaking changes detected."
    total_changes: int = 0
    high_severity_count: int = 0
    medium_severity_count: int = 0
    low_severity_count: int = 0
    changes: List[BreakingChangeItem] = []
    is_cached: bool = False

class BreakingChangeExplanationModel(BaseModel):
    explanation: str = Field(default="High-level architectural breaking change analysis.", description="Clear technical explanation of breaking changes")
    why_it_breaks: List[str] = Field(default=[], description="Step-by-step reasons why existing callers or dependencies will fail")
    affected_components: List[str] = Field(default=[], description="List of project components or downstream consumers affected")
    recommended_fixes: List[str] = Field(default=[], description="Actionable migration steps to update callers")
    backward_compatible_alternatives: List[str] = Field(default=[], description="Proposed refactorings to preserve API backward compatibility")

    @field_validator("why_it_breaks", "affected_components", "recommended_fixes", "backward_compatible_alternatives", mode="before")
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

class BreakingChangeExplanationRequest(BaseModel):
    file_path: str
    changes: List[BreakingChangeItem]
    force_refresh: bool = False

class BreakingChangeExplanationResponse(BaseModel):
    explanation: str
    why_it_breaks: List[str] = []
    affected_components: List[str] = []
    recommended_fixes: List[str] = []
    backward_compatible_alternatives: List[str] = []
    is_cached: bool = False
    is_fallback: bool = False
