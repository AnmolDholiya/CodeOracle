from fastapi import APIRouter, HTTPException, status
from app.schemas.breaking_change import (
    BreakingChangeAnalysisRequest,
    BreakingChangeAnalysisResponse,
    BreakingChangeExplanationRequest,
    BreakingChangeExplanationResponse
)
from app.services.breaking_change_service import (
    analyze_breaking_changes,
    explain_breaking_changes
)

router = APIRouter(prefix="/api/projects", tags=["Breaking-Change Detection"])

@router.post("/{project_id}/breaking-changes/analyze", response_model=BreakingChangeAnalysisResponse)
async def analyze_breaking_changes_endpoint(
    project_id: str,
    request: BreakingChangeAnalysisRequest
):
    """Performs local AST static analysis to detect breaking API changes, parameter shifts, and call-site violations."""
    try:
        return analyze_breaking_changes(
            project_id=project_id,
            relative_path=request.file_path,
            modified_code=request.modified_code,
            force_refresh=request.force_refresh
        )
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Breaking change analysis failed: {str(exc)}"
        )

@router.post("/{project_id}/breaking-changes/explain", response_model=BreakingChangeExplanationResponse)
async def explain_breaking_changes_endpoint(
    project_id: str,
    request: BreakingChangeExplanationRequest
):
    """Queries Groq AI on-demand for technical explanation, root cause analysis, and backward-compatible alternatives."""
    try:
        return await explain_breaking_changes(
            project_id=project_id,
            file_path=request.file_path,
            changes=request.changes,
            force_refresh=request.force_refresh
        )
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Breaking change explanation failed: {str(exc)}"
        )
