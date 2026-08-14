import os
from fastapi import APIRouter, HTTPException, status
from app.schemas.improvements import (
    ProjectImprovementsResponse,
    ExplainImprovementsRequest
)
from app.services.improvements_service import (
    compute_deterministic_improvements,
    explain_improvements_with_ai
)

router = APIRouter(prefix="/api/projects", tags=["Project Improvements"])

@router.get("/{project_id}/improvements", response_model=ProjectImprovementsResponse)
async def get_project_improvements(project_id: str):
    """
    Fetches deterministic evidence-backed project improvements & recommendations.
    Uses only static analysis, AST metrics, dependency graphs, and test data.
    Zero Groq AI calls during initial retrieval.
    """
    try:
        return compute_deterministic_improvements(project_id)
    except FileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate project improvements: {str(exc)}"
        )

@router.post("/{project_id}/improvements/explain", response_model=ProjectImprovementsResponse)
async def explain_improvements(
    project_id: str,
    request: ExplainImprovementsRequest = ExplainImprovementsRequest()
):
    """
    On-Demand Groq AI Prioritization & Refactoring Action Explainer.
    Operates strictly on Layer 1 structured evidence without hallucination.
    """
    try:
        return await explain_improvements_with_ai(
            project_id=project_id,
            focus_category=request.focus_category
        )
    except FileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI improvement explanations: {str(exc)}"
        )
