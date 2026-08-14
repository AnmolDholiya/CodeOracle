import os
import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas.improvements import (
    ProjectImprovementsResponse,
    ExplainImprovementsRequest
)
from app.services.improvements_service import (
    compute_deterministic_improvements,
    explain_improvements_with_ai
)

logger = logging.getLogger("codeoracle.improvements")
router = APIRouter(prefix="/api/projects", tags=["Project Improvements"])

@router.get("/{project_id}/improvements", response_model=ProjectImprovementsResponse)
async def get_project_improvements(project_id: str):
    """
    Fetches deterministic evidence-backed project improvements & recommendations.
    Uses only static analysis, AST metrics, dependency graphs, and test data.
    Zero Groq AI calls during initial retrieval.
    """
    if not project_id or not project_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PROJECT_ID", "message": "Project ID is required."}
        )

    logger.info(f"[IMPROVEMENTS] Requesting recommendations for project_id={project_id}")
    try:
        res = compute_deterministic_improvements(project_id)
        logger.info(f"[IMPROVEMENTS] Success: project_id={project_id}, recommendations={res.total_recommendations}")
        return res
    except FileNotFoundError as err:
        logger.warning(f"[IMPROVEMENTS] Project not found: project_id={project_id}, error={err}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": str(err)}
        )
    except Exception as exc:
        logger.error(f"[IMPROVEMENTS] Error for project_id={project_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "ANALYSIS_ERROR", "message": f"Failed to calculate project improvements: {str(exc)}"}
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
    if not project_id or not project_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PROJECT_ID", "message": "Project ID is required."}
        )

    logger.info(f"[IMPROVEMENTS_AI] Generating explanation for project_id={project_id}")
    try:
        res = await explain_improvements_with_ai(
            project_id=project_id,
            focus_category=request.focus_category
        )
        return res
    except FileNotFoundError as err:
        logger.warning(f"[IMPROVEMENTS_AI] Project not found: project_id={project_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": str(err)}
        )
    except Exception as exc:
        logger.error(f"[IMPROVEMENTS_AI] AI explanation error for project_id={project_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "ANALYSIS_ERROR", "message": f"Failed to generate AI improvement explanations: {str(exc)}"}
        )
