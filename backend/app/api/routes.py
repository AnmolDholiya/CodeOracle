import os
import json
import re
import logging
import zipfile
import urllib.request
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Body, status
from app.schemas.project import ProjectMetadata, CleanupResponse, ProjectStatusResponse, UploadResponse, GitHubRepoRequest
from app.schemas.ast import ProjectAnalysisResponse
from app.schemas.dependency import DependencyGraphResponse
from app.services.extractor import (
    create_project_workspace,
    create_empty_project_workspace,
    init_project_workspace,
    process_project_background,
    process_github_project_background,
    get_project_status,
    cleanup_project,
    get_project_directory,
    scan_project_directory,
    MAX_UPLOAD_SIZE,
    UPLOAD_CHUNK_SIZE,
)
from app.services.python_ast import analyze_project_workspace
from app.services.dependency_graph import generate_dependency_graph

from app.tasks import (
    dispatch_project_processing,
    dispatch_github_processing
)

router = APIRouter(prefix="/api/projects", tags=["Projects"])
logger = logging.getLogger("codeoracle.routes")

@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_project_zip(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Uploads a legacy codebase ZIP archive via streaming, creates workspace, and enqueues Celery background task."""
    logger.info(f"[UPLOAD_RECEIVED] filename={file.filename}")
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only .zip codebase archives are supported."
        )
    
    # Create workspace and get the target ZIP path
    project_id, project_dir, zip_path = init_project_workspace(file.filename)
    logger.info(f"[PROJECT_CREATED] project_id={project_id}, dir={project_dir}")
    
    try:
        # Stream file to disk in chunks — avoids loading 130+ MB into RAM
        total_written = 0
        logger.info(f"[UPLOAD] Streaming ZIP to disk: filename={file.filename}, project_id={project_id}")
        
        with open(zip_path, "wb") as f:
            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                total_written += len(chunk)
                if total_written > MAX_UPLOAD_SIZE:
                    # Clean up partial file and workspace
                    f.close()
                    cleanup_project(project_id)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"ZIP archive exceeds the {MAX_UPLOAD_SIZE // (1024*1024)} MB upload limit."
                    )
                f.write(chunk)
        
        if total_written == 0:
            cleanup_project(project_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty."
            )
        
        # Validate the saved file is actually a valid ZIP
        if not zipfile.is_zipfile(zip_path):
            cleanup_project(project_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ZIP archive. The uploaded file is not a valid ZIP."
            )
        
        logger.info(f"[UPLOAD] Streamed {total_written} bytes to disk for project_id={project_id}")
        
        # Enqueue Celery background processing task (with fallback if Redis is offline)
        dispatch_project_processing(project_id, file.filename, background_tasks=background_tasks)
        logger.info(f"[CELERY_TASK_QUEUED] project_id={project_id}, returning HTTP 202")
        
        return UploadResponse(
            project_id=project_id,
            status="queued",
            message="Project uploaded successfully. Processing started."
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as exc:
        logger.error(f"[UPLOAD] Failed: {exc}")
        cleanup_project(project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process zip file: {str(exc)}"
        )

@router.post("/upload_github", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_github_repository(
    background_tasks: BackgroundTasks,
    request: GitHubRepoRequest = Body(...)
):
    """Fetches a public GitHub repository ZIP archive, creates workspace, and enqueues Celery background task."""
    url_clean = request.repo_url.strip()
    match = re.search(r"github\.com/([^/]+)/([^/\?#]+?)(?:\.git)?(?:/|$)", url_clean, re.IGNORECASE)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GitHub URL format. Expected: https://github.com/owner/repository"
        )
    
    owner = match.group(1)
    repo = match.group(2)
    if repo.lower().endswith(".git"):
        repo = repo[:-4]
        
    try:
        logger.info(f"[GITHUB_RECEIVED] repo={owner}/{repo}")
        project_id, project_dir = create_empty_project_workspace(f"{repo}.zip")
        logger.info(f"[PROJECT_CREATED] project_id={project_id}")
        dispatch_github_processing(project_id, owner, repo, background_tasks=background_tasks)
        logger.info(f"[CELERY_TASK_QUEUED] project_id={project_id}, returning HTTP 202")
        return UploadResponse(
            project_id=project_id,
            status="queued",
            message=f"GitHub repository '{owner}/{repo}' queued successfully. Processing started."
        )
    except Exception as exc:
        logger.error(f"[GITHUB] Failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process GitHub repository workspace: {str(exc)}"
        )

@router.get("/{project_id}/status", response_model=ProjectStatusResponse)
async def check_project_status(project_id: str):
    """Retrieves processing stage and progress for an uploaded project."""
    try:
        return get_project_status(project_id)
    except FileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err)
        )

@router.post("/{project_id}/analyze", response_model=ProjectAnalysisResponse)
async def analyze_project(project_id: str):
    """Scans Python source files in the project workspace and extracts AST metadata."""
    try:
        project_dir = get_project_directory(project_id)
        analysis_result = analyze_project_workspace(project_dir, project_id)
        
        # Cache AST analysis JSON inside temporary workspace
        cache_path = os.path.join(project_dir, "analysis_ast.json")
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(analysis_result.model_dump_json(indent=2))
            
        return analysis_result
    except FileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AST Analysis failed: {str(exc)}"
        )

@router.get("/{project_id}/analyze", response_model=ProjectAnalysisResponse)
async def get_project_analysis(project_id: str):
    """Retrieves cached Python AST analysis for a project."""
    try:
        project_dir = get_project_directory(project_id)
        cache_path = os.path.join(project_dir, "analysis_ast.json")
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return ProjectAnalysisResponse(**data)
        
        # If cache missing, run fresh analysis
        analysis_result = analyze_project_workspace(project_dir, project_id)
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(analysis_result.model_dump_json(indent=2))
        return analysis_result
    except FileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err)
        )

@router.get("/{project_id}/dependencies", response_model=DependencyGraphResponse)
async def get_project_dependencies(project_id: str):
    """Generates import dependency graph nodes and edges for the project workspace."""
    try:
        project_dir = get_project_directory(project_id)
        
        # Check cached AST analysis or run AST scan if not available
        cache_ast_path = os.path.join(project_dir, "analysis_ast.json")
        if os.path.exists(cache_ast_path):
            with open(cache_ast_path, "r", encoding="utf-8") as f:
                ast_data = json.load(f)
                ast_analysis = ProjectAnalysisResponse(**ast_data)
        else:
            ast_analysis = analyze_project_workspace(project_dir, project_id)
            with open(cache_ast_path, "w", encoding="utf-8") as f:
                f.write(ast_analysis.model_dump_json(indent=2))

        # Generate dependency graph using cached AST data
        graph = generate_dependency_graph(ast_analysis)
        
        # Cache dependency graph JSON inside temporary workspace
        cache_graph_path = os.path.join(project_dir, "dependency_graph.json")
        with open(cache_graph_path, "w", encoding="utf-8") as f:
            f.write(graph.model_dump_json(indent=2))

        return graph
    except FileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dependency Graph generation failed: {str(exc)}"
        )

@router.delete("/{project_id}", response_model=CleanupResponse)
async def delete_project(project_id: str):
    """Deletes temporary project workspace files."""
    success = cleanup_project(project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found or already cleaned up."
        )
    return CleanupResponse(
        status="success",
        message="Temporary project workspace cleaned up successfully.",
        project_id=project_id
    )

@router.get("/{project_id}", response_model=ProjectMetadata)
async def get_project_info(project_id: str):
    """Retrieves active project metadata."""
    try:
        project_dir = get_project_directory(project_id)
        meta_cache_path = os.path.join(project_dir, "project_metadata.json")
        if os.path.exists(meta_cache_path):
            with open(meta_cache_path, "r", encoding="utf-8") as f:
                return ProjectMetadata(**json.load(f))

        files_metadata, languages, total_loc = scan_project_directory(project_dir)
        return ProjectMetadata(
            project_id=project_id,
            original_filename="Active Workspace",
            extracted_path=project_dir,
            total_files=len(files_metadata),
            total_lines_of_code=total_loc,
            languages=languages,
            files=files_metadata,
            created_at=""
        )
    except FileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err)
        )
