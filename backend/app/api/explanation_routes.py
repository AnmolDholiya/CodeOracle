from fastapi import APIRouter, HTTPException, Query, status
from app.ai.schemas import (
    ProjectExplanation,
    ModuleExplanation,
    ClassExplanation,
    FunctionExplanation,
    ModuleExplanationRequest,
    ClassExplanationRequest,
    FunctionExplanationRequest
)
from app.ai.exceptions import (
    AIConfigurationError,
    AIAuthenticationError,
    AIRateLimitError,
    AITimeoutError,
    AIInsufficientCreditsError,
    AIProviderError,
    AIValidationError
)
from app.services.explanation_service import (
    explain_project,
    explain_module,
    explain_class,
    explain_function
)

router = APIRouter(prefix="/api/projects", tags=["Explanations"])

@router.get("/{project_id}/explanations/project", response_model=ProjectExplanation)
async def get_project_explanation(
    project_id: str,
    force_refresh: bool = Query(default=False)
):
    """Retrieves high-level project architectural overview (AI or Static Fallback)."""
    try:
        return await explain_project(project_id, force_refresh=force_refresh)
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Project explanation error: {str(exc)}")

@router.post("/{project_id}/explanations/module", response_model=ModuleExplanation)
async def get_module_explanation(
    project_id: str, 
    request: ModuleExplanationRequest,
    force_refresh: bool = Query(default=False)
):
    """Retrieves module/file explanation (AI or Static Fallback)."""
    try:
        return await explain_module(project_id, request.file_path, force_refresh=force_refresh)
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Module explanation error: {str(exc)}")

@router.post("/{project_id}/explanations/class", response_model=ClassExplanation)
async def get_class_explanation(
    project_id: str, 
    request: ClassExplanationRequest,
    force_refresh: bool = Query(default=False)
):
    """Retrieves class-level explanation (AI or Static Fallback)."""
    try:
        return await explain_class(project_id, request.file_path, request.class_name, force_refresh=force_refresh)
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Class explanation error: {str(exc)}")

@router.post("/{project_id}/explanations/function", response_model=FunctionExplanation)
async def get_function_explanation(
    project_id: str, 
    request: FunctionExplanationRequest,
    force_refresh: bool = Query(default=False)
):
    """Retrieves function/method level explanation (AI or Static Fallback)."""
    try:
        return await explain_function(project_id, request.file_path, request.function_name, force_refresh=force_refresh)
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Function explanation error: {str(exc)}")
