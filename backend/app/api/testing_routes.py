from fastapi import APIRouter, HTTPException, Query, status
from app.schemas.testing import (
    UnitTestGenRequest,
    UnitTestGenResponse,
    TestExecutionRequest,
    TestExecutionResult,
    CoverageResult
)
from app.services.unit_testing_service import (
    generate_unit_tests,
    run_unit_tests,
    get_test_coverage
)

router = APIRouter(prefix="/api/projects", tags=["Unit Testing & Coverage"])

@router.post("/{project_id}/tests/generate", response_model=UnitTestGenResponse)
async def generate_tests_endpoint(
    project_id: str,
    request: UnitTestGenRequest
):
    """Generates AI-powered unit tests for a target Python file or function."""
    try:
        return await generate_unit_tests(
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
            detail=f"Test generation failed: {str(exc)}"
        )

@router.post("/{project_id}/tests/run", response_model=TestExecutionResult)
async def run_tests_endpoint(
    project_id: str,
    request: TestExecutionRequest
):
    """Executes generated pytest test suite inside project workspace."""
    try:
        timeout = request.timeout_seconds if request.timeout_seconds and request.timeout_seconds > 0 else 30
        return run_unit_tests(
            project_id=project_id,
            relative_path=request.file_path,
            timeout_seconds=timeout
        )
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test execution error: {str(exc)}"
        )

@router.get("/{project_id}/tests/coverage", response_model=CoverageResult)
async def get_coverage_endpoint(
    project_id: str,
    file_path: str = Query(..., description="Relative path of target Python file")
):
    """Retrieves actual statement & line coverage percentage measured via coverage.py."""
    try:
        return get_test_coverage(project_id, file_path)
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Coverage calculation failed: {str(exc)}"
        )
