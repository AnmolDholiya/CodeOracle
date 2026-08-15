import os
import logging
from celery import Celery
from app.core.config import load_backend_environment

load_backend_environment()

logger = logging.getLogger("codeoracle.celery")

# Redis URL from environment (default: redis://localhost:6379/0)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0").strip() or "redis://localhost:6379/0"

# Celery Application instance
celery_app = Celery(
    "codeoracle",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"]
)

# Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_connection_timeout=1.5,
    broker_transport_options={
        "max_retries": 1,
        "visibility_timeout": 3600
    },
    task_track_started=True,
    task_time_limit=900,
    task_soft_time_limit=840
)

logger.info(f"[CELERY] Initialized Celery with broker={REDIS_URL.split('@')[-1] if '@' in REDIS_URL else REDIS_URL}")
