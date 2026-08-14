from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

class EvidenceItem(BaseModel):
    id: str
    type: str  # "ast" | "coverage" | "test" | "dependency_graph" | "code_smell" | "file_metric" | "architecture"
    file: str
    symbol: Optional[str] = None
    line_number: Optional[int] = None
    metric: str
    value: Any
    details: str

class ImprovementRecommendation(BaseModel):
    id: str
    category: str  # "CODE_QUALITY" | "TEST_COVERAGE" | "COMPLEXITY" | "UNUSED_IMPORTS" | "LARGE_FUNCTIONS" | "LARGE_FILES" | "MAINTAINABILITY" | "TESTING_GAPS" | "DEPENDENCY_ARCHITECTURE" | "ERROR_HANDLING" | "PYTHON_QUALITY" | "JAVASCRIPT_QUALITY"
    title: str
    severity: str  # "high" | "medium" | "low" | "info"
    confidence: float = 1.0  # Evidence strength (1.0 = direct deterministic verification)
    description: str
    why_it_matters: str
    recommendation: str
    affected_files: List[str] = []
    affected_symbols: List[str] = []
    evidence: List[EvidenceItem] = []
    source: str = "static_analysis"  # "static_analysis" | "tests" | "coverage" | "dependency_graph" | "refactor_analysis" | "ai"
    action: str
    is_verified: bool = True

class ProjectHealthMetrics(BaseModel):
    overall_health_pct: Optional[int] = None
    code_quality_pct: int = 100
    test_health_pct: Optional[int] = None  # None if tests haven't been run yet
    architecture_pct: int = 100
    maintainability_pct: int = 100
    health_summary: str

class AccomplishmentItem(BaseModel):
    id: str
    title: str
    detail: str
    category: str

class ProjectImprovementsResponse(BaseModel):
    project_id: str
    health_metrics: ProjectHealthMetrics
    already_done_well: List[AccomplishmentItem] = []
    recommendations: List[ImprovementRecommendation] = []
    total_recommendations: int = 0
    categories_present: List[str] = []
    evidence_count: int = 0
    is_ai_enhanced: bool = False
    ai_summary: Optional[str] = None
    created_at: str

# Schema for AI Explanation request and response
class ExplainImprovementsRequest(BaseModel):
    focus_category: Optional[str] = None

class AIRecommendationItem(BaseModel):
    title: str
    explanation: str
    why_it_matters: str
    suggested_action: str
    evidence_ids: List[str] = []
    priority: str = "medium"

class AIImprovementResponseModel(BaseModel):
    summary: str
    recommendations: List[AIRecommendationItem] = []
