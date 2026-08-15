import os
import logging
from app.celery_app import celery_app
from app.services.extractor import (
    process_project_background,
    process_github_project_background,
    get_project_directory,
    get_project_status,
    update_project_status
)

logger = logging.getLogger("codeoracle.tasks")

@celery_app.task(name="app.tasks.process_project_task", max_retries=2)
def process_project_task(project_id: str, original_filename: str):
    """
    Celery background worker task for full ZIP extraction, AST parsing,
    dependency graph generation, and metadata finalization.
    """
    logger.info(f"[TASK_STARTED] Celery worker processing project_id={project_id}, filename={original_filename}")
    try:
        process_project_background(project_id, original_filename)
        st = get_project_status(project_id)
        if st.status == "failed":
            logger.error(f"[TASK_FAILED_EXTRACTOR] project_id={project_id}, error={st.error or st.message}")
            return {"project_id": project_id, "status": "failed", "error": st.error or st.message}
        logger.info(f"[PROJECT_COMPLETED] Celery task successfully finished for project_id={project_id}")
        return {"project_id": project_id, "status": "completed"}
    except ValueError as val_err:
        # Non-retryable validation or security error (e.g. bad zip, zip bomb, path traversal)
        logger.error(f"[TASK_FAILED_NON_RETRYABLE] project_id={project_id}, error={val_err}")
        return {"project_id": project_id, "status": "failed", "error": str(val_err)}
    except Exception as exc:
        logger.error(f"[TASK_FAILED] project_id={project_id}, error={exc}")
        return {"project_id": project_id, "status": "failed", "error": str(exc)}


@celery_app.task(name="app.tasks.process_github_project_task", max_retries=2)
def process_github_project_task(project_id: str, owner: str, repo: str):
    """
    Celery background worker task for downloading public GitHub repository archive,
    extracting workspace, and running static analysis pipeline.
    """
    logger.info(f"[TASK_STARTED] Celery worker downloading and processing GitHub repo '{owner}/{repo}', project_id={project_id}")
    try:
        process_github_project_background(project_id, owner, repo)
        st = get_project_status(project_id)
        if st.status == "failed":
            return {"project_id": project_id, "status": "failed", "error": st.error or st.message}
        logger.info(f"[PROJECT_COMPLETED] GitHub task finished for project_id={project_id}")
        return {"project_id": project_id, "status": "completed"}
    except ValueError as val_err:
        logger.error(f"[TASK_FAILED_NON_RETRYABLE] GitHub project_id={project_id}, error={val_err}")
        return {"project_id": project_id, "status": "failed", "error": str(val_err)}
    except Exception as exc:
        logger.error(f"[TASK_FAILED] GitHub project_id={project_id}, error={exc}")
        return {"project_id": project_id, "status": "failed", "error": str(exc)}


def dispatch_project_processing(project_id: str, original_filename: str, background_tasks=None):
    """
    Unified task dispatcher:
    1. Attempts to enqueue Celery task via Redis broker (non-blocking, fast failover).
    2. Gracefully falls back to FastAPI BackgroundTasks if Redis is offline/unavailable.
    """
    try:
        process_project_task.apply_async(args=[project_id, original_filename], retry=False)
        logger.info(f"[CELERY_TASK_QUEUED] Successfully enqueued Celery task for project_id={project_id}")
    except Exception as celery_err:
        logger.warning(f"[CELERY_FALLBACK] Could not enqueue to Redis broker ({celery_err}). Falling back to FastAPI BackgroundTask.")
        if background_tasks:
            background_tasks.add_task(process_project_background, project_id, original_filename)
        else:
            # Direct execution fallback
            process_project_background(project_id, original_filename)


def dispatch_github_processing(project_id: str, owner: str, repo: str, background_tasks=None):
    """
    Unified GitHub task dispatcher with graceful fallback.
    """
    try:
        process_github_project_task.apply_async(args=[project_id, owner, repo], retry=False)
        logger.info(f"[CELERY_TASK_QUEUED] Successfully enqueued GitHub Celery task for project_id={project_id}")
    except Exception as celery_err:
        logger.warning(f"[CELERY_FALLBACK] Could not enqueue GitHub task to Redis broker ({celery_err}). Falling back to FastAPI BackgroundTask.")
        if background_tasks:
            background_tasks.add_task(process_github_project_background, project_id, owner, repo)
        else:
            process_github_project_background(project_id, owner, repo)
