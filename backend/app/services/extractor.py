import os
import shutil
import zipfile
import uuid
import time
import json
import logging
import tempfile
from typing import Dict, List, Tuple, Optional
from app.schemas.project import ProjectMetadata, FileDetail, ProjectStatusResponse

# Base directory for temporary uploads
BASE_TEMP_DIR = os.path.join(tempfile.gettempdir(), "codeoracle_projects")
os.makedirs(BASE_TEMP_DIR, exist_ok=True)

logger = logging.getLogger("codeoracle.extractor")

# Language extension mapping
LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".html": "HTML",
    ".css": "CSS",
    ".json": "JSON",
    ".md": "Markdown",
}

# Directories to skip during scanning
IGNORED_DIRS = {
    "__pycache__", ".git", "node_modules", ".venv", "venv", 
    "env", ".pytest_cache", ".idea", ".vscode", "dist", "build"
}

def is_safe_path(base_dir: str, target_path: str) -> bool:
    """Path traversal prevention check (Zip Slip vulnerability guard)."""
    resolved_base = os.path.abspath(base_dir)
    resolved_target = os.path.abspath(target_path)
    try:
        common = os.path.commonpath([resolved_base, resolved_target])
        return common == resolved_base
    except ValueError:
        return False

def update_project_status(
    project_dir: str, 
    status: str, 
    stage: str, 
    progress: int, 
    message: str, 
    error: Optional[str] = None
):
    """Writes status.json inside the project workspace directory."""
    status_file = os.path.join(project_dir, "status.json")
    status_data = {
        "project_id": os.path.basename(project_dir),
        "status": status,
        "stage": stage,
        "progress": progress,
        "message": message,
        "error": error,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2)
        logger.info(f"[STATUS] project={os.path.basename(project_dir)} stage={stage} progress={progress}% status={status}")
    except Exception:
        pass

def get_project_status(project_id: str) -> ProjectStatusResponse:
    """Retrieves current processing status for a project workspace."""
    project_dir = get_project_directory(project_id)
    status_file = os.path.join(project_dir, "status.json")
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return ProjectStatusResponse(**data)
        except Exception:
            pass
    # Default fallback if status.json is missing
    return ProjectStatusResponse(
        project_id=project_id,
        status="completed",
        stage="completed",
        progress=100,
        message="Project processing ready."
    )

def create_project_workspace(file_bytes: bytes, original_filename: str) -> Tuple[str, str]:
    """Saves uploaded ZIP file to temp workspace and returns (project_id, project_dir)."""
    project_id = str(uuid.uuid4())[:8]
    project_dir = os.path.join(BASE_TEMP_DIR, project_id)
    os.makedirs(project_dir, exist_ok=True)

    zip_path = os.path.join(project_dir, "uploaded_archive.zip")
    with open(zip_path, "wb") as f:
        f.write(file_bytes)

    # Initialize status file
    update_project_status(
        project_dir=project_dir,
        status="queued",
        stage="queued",
        progress=5,
        message="ZIP archive uploaded. Queued for processing..."
    )

    return project_id, project_dir

def create_empty_project_workspace(original_filename: str) -> Tuple[str, str]:
    """Creates temp workspace for async background operations and returns (project_id, project_dir)."""
    project_id = str(uuid.uuid4())[:8]
    project_dir = os.path.join(BASE_TEMP_DIR, project_id)
    os.makedirs(project_dir, exist_ok=True)

    update_project_status(
        project_dir=project_dir,
        status="queued",
        stage="queued",
        progress=5,
        message=f"Repository '{original_filename}' queued. Waiting to fetch from GitHub..."
    )
    return project_id, project_dir

def process_github_project_background(project_id: str, owner: str, repo: str):
    """Background task fetching GitHub repository archive, creating workspace, and processing indexing."""
    try:
        import urllib.request
        project_dir = get_project_directory(project_id)
        update_project_status(project_dir, "processing", "downloading_github", 15, f"Downloading public repository '{owner}/{repo}' from GitHub...")
        
        zip_urls = [
            f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/main",
            f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/master",
            f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/dev",
            f"https://github.com/{owner}/{repo}/archive/HEAD.zip"
        ]
        
        zip_bytes = None
        last_err = None
        for z_url in zip_urls:
            try:
                req = urllib.request.Request(z_url, headers={"User-Agent": "CodeOracle-Bot"})
                with urllib.request.urlopen(req, timeout=25) as resp:
                    if resp.status == 200:
                        zip_bytes = resp.read()
                        break
            except Exception as exc:
                last_err = str(exc)
                
        if not zip_bytes:
            raise ValueError(f"Failed to download repository '{owner}/{repo}' from GitHub. Ensure repository is public. Error: {last_err}")
            
        zip_path = os.path.join(project_dir, "uploaded_archive.zip")
        with open(zip_path, "wb") as f:
            f.write(zip_bytes)
            
        process_project_background(project_id, f"{repo}.zip")
    except Exception as exc:
        project_dir = os.path.join(BASE_TEMP_DIR, project_id)
        update_project_status(
            project_dir=project_dir,
            status="failed",
            stage="failed",
            progress=0,
            message=f"GitHub repository processing failed: {str(exc)}",
            error=str(exc)
        )

def process_project_background(project_id: str, original_filename: str):
    """Background task performing ZIP extraction, file scanning, AST analysis, and dependency graph generation."""
    try:
        project_dir = get_project_directory(project_id)
        zip_path = os.path.join(project_dir, "uploaded_archive.zip")
        logger.info(f"[WORKER] Starting background processing: project_id={project_id}, filename={original_filename}")

        # Stage 1: Extraction
        update_project_status(project_dir, "processing", "extracting", 15, "Extracting ZIP archive safely...")
        if os.path.exists(zip_path):
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    for member in zip_ref.infolist():
                        target_path = os.path.join(project_dir, member.filename)
                        if not is_safe_path(project_dir, target_path):
                            raise ValueError(f"Security Alert: Malformed path detected in zip: {member.filename}")
                        zip_ref.extract(member, project_dir)
            except zipfile.BadZipFile:
                raise ValueError("Invalid or corrupted ZIP archive file.")
            finally:
                if os.path.exists(zip_path):
                    os.remove(zip_path)

        # Stage 2: File Scanning
        update_project_status(project_dir, "processing", "discovering_files", 35, "Discovering codebase files & calculating line counts...")
        files_metadata, languages, total_loc = scan_project_directory(project_dir)
        logger.info(f"[WORKER] project_id={project_id} discovered {len(files_metadata)} files, {total_loc} LOC, languages={languages}")

        metadata = ProjectMetadata(
            project_id=project_id,
            original_filename=original_filename,
            extracted_path=project_dir,
            total_files=len(files_metadata),
            total_lines_of_code=total_loc,
            languages=languages,
            files=files_metadata,
            created_at=time.strftime("%Y-%m-%d %H:%M:%S")
        )

        # Cache metadata JSON
        meta_cache_path = os.path.join(project_dir, "project_metadata.json")
        with open(meta_cache_path, "w", encoding="utf-8") as f:
            f.write(metadata.model_dump_json(indent=2))

        # Stage 3: Python AST Analysis
        update_project_status(project_dir, "processing", "analyzing_python", 55, "Scanning Python AST symbols and imports...")
        from app.services.python_ast import analyze_project_workspace
        ast_analysis = analyze_project_workspace(project_dir, project_id)
        ast_cache_path = os.path.join(project_dir, "analysis_ast.json")
        with open(ast_cache_path, "w", encoding="utf-8") as f:
            f.write(ast_analysis.model_dump_json(indent=2))

        # Stage 4: JavaScript/TypeScript indexing (lightweight — files are analyzed on-demand)
        update_project_status(project_dir, "processing", "analyzing_javascript", 75, "Indexing JavaScript/TypeScript source files...")
        # JS/TS AST analysis is performed on-demand per-file via the explanation/testing endpoints.
        # This stage confirms JS/TS files are discovered and indexed in metadata.
        js_ts_count = sum(1 for f in files_metadata if f.extension in ('.js', '.jsx', '.ts', '.tsx'))
        logger.info(f"[WORKER] project_id={project_id} JS/TS files indexed: {js_ts_count}")

        # Stage 5: Dependency Graph
        update_project_status(project_dir, "processing", "building_dependencies", 90, "Building import dependency graph...")
        from app.services.dependency_graph import generate_dependency_graph
        graph = generate_dependency_graph(ast_analysis)
        dep_cache_path = os.path.join(project_dir, "dependency_graph.json")
        with open(dep_cache_path, "w", encoding="utf-8") as f:
            f.write(graph.model_dump_json(indent=2))

        # Stage 6: Completed
        update_project_status(project_dir, "completed", "completed", 100, "Project processing completed successfully!")
        logger.info(f"[WORKER] Completed: project_id={project_id}")

    except Exception as exc:
        logger.error(f"[WORKER] Failed: project_id={project_id}, error={exc}")
        project_dir = os.path.join(BASE_TEMP_DIR, project_id)
        update_project_status(
            project_dir=project_dir,
            status="failed",
            stage="failed",
            progress=0,
            message=f"Project processing failed: {str(exc)}",
            error=str(exc)
        )

def extract_zip_file(file_bytes: bytes, original_filename: str) -> ProjectMetadata:
    """Synchronous extraction fallback for legacy API compatibility and small files."""
    project_id, project_dir = create_project_workspace(file_bytes, original_filename)
    process_project_background(project_id, original_filename)

    status_data = get_project_status(project_id)
    if status_data.status == "failed":
        raise ValueError(status_data.error or "Failed to process zip file.")

    meta_cache_path = os.path.join(project_dir, "project_metadata.json")
    if os.path.exists(meta_cache_path):
        with open(meta_cache_path, "r", encoding="utf-8") as f:
            return ProjectMetadata(**json.load(f))

    files_metadata, languages, total_loc = scan_project_directory(project_dir)
    return ProjectMetadata(
        project_id=project_id,
        original_filename=original_filename,
        extracted_path=project_dir,
        total_files=len(files_metadata),
        total_lines_of_code=total_loc,
        languages=languages,
        files=files_metadata,
        created_at=time.strftime("%Y-%m-%d %H:%M:%S")
    )

def scan_project_directory(project_dir: str) -> Tuple[List[FileDetail], List[str], int]:
    """Scans project files, computes line counts, and identifies languages."""
    files_list: List[FileDetail] = []
    languages_found = set()
    total_loc = 0

    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            rel_path = os.path.relpath(os.path.join(root, file), project_dir).replace("\\", "/")
            abs_path = os.path.join(root, file)

            # Skip binary, system, or internal workspace cache files
            if ext in [".zip", ".png", ".jpg", ".jpeg", ".ico", ".exe", ".pyc"]:
                continue
            if file in {"status.json", "project_metadata.json", "analysis_ast.json", "dependency_graph.json", "explanation_cache.json", "uploaded_archive.zip"}:
                continue

            lang = LANGUAGE_MAP.get(ext, "Plain Text")
            if lang != "Plain Text":
                languages_found.add(lang)

            loc = count_lines_of_code(abs_path)
            total_loc += loc
            size = os.path.getsize(abs_path)

            files_list.append(FileDetail(
                relative_path=rel_path,
                absolute_path=abs_path,
                extension=ext,
                size_bytes=size,
                lines_of_code=loc,
                language=lang
            ))

    return files_list, sorted(list(languages_found)), total_loc

def count_lines_of_code(file_path: str) -> int:
    """Counts non-empty lines of code in a file."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [line.strip() for line in f if line.strip()]
            return len(lines)
    except Exception:
        return 0

def cleanup_project(project_id: str) -> bool:
    """Safely removes temporary project directory."""
    project_dir = os.path.join(BASE_TEMP_DIR, project_id)
    if os.path.exists(project_dir) and is_safe_path(BASE_TEMP_DIR, project_dir):
        shutil.rmtree(project_dir, ignore_errors=True)
        return True
    return False

def get_project_directory(project_id: str) -> str:
    """Returns project path if valid and exists."""
    project_dir = os.path.join(BASE_TEMP_DIR, project_id)
    if os.path.exists(project_dir) and is_safe_path(BASE_TEMP_DIR, project_dir):
        return project_dir
    raise FileNotFoundError(f"Project workspace '{project_id}' not found or has been cleaned up.")
