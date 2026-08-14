from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, Any, List, Union

class AITestRequest(BaseModel):
    code: str = Field(default="def add(a, b): return a + b", description="Python code snippet to test AI explanation")

class AITestResponse(BaseModel):
    success: bool
    response: str
    model_used: str
    is_mock: bool = False

class AIStatusResponse(BaseModel):
    configured: bool
    provider: str = "Groq"
    model: str
    base_url: str

class AIResponse(BaseModel):
    text: str
    model_used: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None

# Helper validator to normalize list of items where LLM might return dicts or single strings
def _normalize_string_list(v: Any) -> List[str]:
    if isinstance(v, str):
        return [v.strip()]
    if isinstance(v, list):
        result = []
        for item in v:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                vals = [str(val) for val in item.values()]
                result.append(" - ".join(vals))
            else:
                result.append(str(item))
        return result
    return []

# ----------------------------------------------------
# Phase 6 Explanation Data Schemas
# ----------------------------------------------------

class ProjectExplanation(BaseModel):
    purpose: str = ""
    project_purpose: Optional[str] = None
    architecture: str = ""
    major_modules: List[str] = []
    important_dependencies: List[str] = []
    execution_flow: List[str] = []
    maintenance_concerns: List[str] = []
    technologies: List[str] = []
    main_components: List[str] = []
    main_workflow: List[str] = []
    key_dependencies: List[str] = []
    is_static_fallback: bool = False
    fallback_reason: Optional[str] = None

    @field_validator("major_modules", "important_dependencies", "execution_flow", "maintenance_concerns", "technologies", "main_components", "main_workflow", "key_dependencies", mode="before")
    @classmethod
    def normalize_lists(cls, v):
        return _normalize_string_list(v)

    @model_validator(mode="after")
    def sync_fields(self):
        if not self.purpose and self.project_purpose:
            self.purpose = self.project_purpose
        elif not self.project_purpose and self.purpose:
            self.project_purpose = self.purpose
        if not self.main_components and self.major_modules:
            self.main_components = self.major_modules
        elif not self.major_modules and self.main_components:
            self.major_modules = self.main_components
        if not self.main_workflow and self.execution_flow:
            self.main_workflow = self.execution_flow
        elif not self.execution_flow and self.main_workflow:
            self.execution_flow = self.main_workflow
        if not self.key_dependencies and self.important_dependencies:
            self.key_dependencies = self.important_dependencies
        elif not self.important_dependencies and self.key_dependencies:
            self.important_dependencies = self.key_dependencies
        return self

class ModuleExplanation(BaseModel):
    file_path: str = ""
    purpose: str = ""
    summary: str = ""
    responsibilities: List[str] = []
    dependencies: List[str] = []
    classes: List[str] = []
    functions: List[str] = []
    key_elements: List[str] = []
    potential_issues: List[str] = []
    file_type: Optional[str] = "python"
    is_binary: Optional[bool] = False
    is_static_fallback: bool = False
    fallback_reason: Optional[str] = None

    @field_validator("responsibilities", "dependencies", "classes", "functions", "key_elements", "potential_issues", mode="before")
    @classmethod
    def normalize_lists(cls, v):
        return _normalize_string_list(v)

    @model_validator(mode="after")
    def sync_elements(self):
        if not self.key_elements:
            self.key_elements = (self.classes or []) + (self.functions or [])
        return self

class ClassExplanation(BaseModel):
    class_name: str = ""
    purpose: str = ""
    responsibilities: List[str] = []
    constructor_summary: Optional[str] = None
    important_methods: List[str] = []
    inheritance: List[str] = []
    dependencies: List[str] = []
    potential_issues: List[str] = []
    is_static_fallback: bool = False
    fallback_reason: Optional[str] = None

    @field_validator("responsibilities", "important_methods", "inheritance", "dependencies", "potential_issues", mode="before")
    @classmethod
    def normalize_lists(cls, v):
        return _normalize_string_list(v)

class ParameterExplanation(BaseModel):
    name: str
    explanation: str

    @field_validator("name", "explanation", mode="before")
    @classmethod
    def normalize_str(cls, v):
        return str(v) if v is not None else ""

class FunctionExplanation(BaseModel):
    function_name: str = ""
    purpose: str = ""
    parameters_explained: List[ParameterExplanation] = []
    parameters: Optional[List[str]] = None
    return_value_explained: str = ""
    return_value: Optional[str] = None
    step_by_step_logic: List[str] = []
    logic: Optional[List[str]] = None
    calls: List[str] = []
    dependencies: List[str] = []
    side_effects: List[str] = []
    edge_cases: List[str] = []
    potential_issues: List[str] = []
    is_static_fallback: bool = False
    fallback_reason: Optional[str] = None

    @field_validator("step_by_step_logic", "calls", "dependencies", "side_effects", "edge_cases", "potential_issues", mode="before")
    @classmethod
    def normalize_lists(cls, v):
        return _normalize_string_list(v)

    @field_validator("parameters_explained", mode="before")
    @classmethod
    def normalize_params(cls, v):
        if isinstance(v, list):
            res = []
            for item in v:
                if isinstance(item, dict):
                    res.append(item)
                elif isinstance(item, str):
                    res.append({"name": item, "explanation": item})
            return res
        return []

    @model_validator(mode="after")
    def sync_function_fields(self):
        if not self.step_by_step_logic and self.logic:
            self.step_by_step_logic = self.logic
        elif not self.logic and self.step_by_step_logic:
            self.logic = self.step_by_step_logic
        if not self.return_value_explained and self.return_value:
            self.return_value_explained = self.return_value
        elif not self.return_value and self.return_value_explained:
            self.return_value = self.return_value_explained
        if not self.parameters_explained and self.parameters:
            self.parameters_explained = [
                ParameterExplanation(name=p, explanation=f"Parameter {p}") for p in self.parameters
            ]
        return self

# Request payloads
class ModuleExplanationRequest(BaseModel):
    file_path: str

class ClassExplanationRequest(BaseModel):
    file_path: str
    class_name: str

class FunctionExplanationRequest(BaseModel):
    file_path: str
    function_name: str
