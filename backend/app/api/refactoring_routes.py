from fastapi import APIRouter, HTTPException, status
from app.schemas.refactoring import (
    FileRefactorRequest,
    FunctionRefactorRequest,
    SaveRefactorRequest,
    RefactorResultResponse,
    SaveRefactorResponse
)
from app.services.refactoring_service import (
    refactor_target,
    save_refactored_code
)

router = APIRouter(prefix="/api/projects", tags=["AI Code Refactoring"])

@router.post("/{project_id}/refactor/file", response_model=RefactorResultResponse)
async def refactor_file_endpoint(
    project_id: str,
    request: FileRefactorRequest
):
    """Generates AI-powered refactored code and quality metrics for a target Python file."""
    try:
        return await refactor_target(
            project_id=project_id,
            relative_path=request.file_path,
            function_name=None,
            force_refresh=request.force_refresh
        )
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File refactoring failed: {str(exc)}"
        )

@router.post("/{project_id}/refactor/function", response_model=RefactorResultResponse)
async def refactor_function_endpoint(
    project_id: str,
    request: FunctionRefactorRequest
):
    """Generates AI-powered refactored code and quality metrics for a target Python function."""
    try:
        return await refactor_target(
            project_id=project_id,
            relative_path=request.file_path,
            function_name=request.function_name,
            force_refresh=request.force_refresh
        )
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Function refactoring failed: {str(exc)}"
        )

@router.post("/{project_id}/refactor/save", response_model=SaveRefactorResponse)
async def save_refactored_code_endpoint(
    project_id: str,
    request: SaveRefactorRequest
):
    """Saves user-approved refactored Python code to project workspace."""
    try:
        return save_refactored_code(
            project_id=project_id,
            relative_path=request.file_path,
            refactored_code=request.refactored_code
        )
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Save refactored code failed: {str(exc)}"
        )
