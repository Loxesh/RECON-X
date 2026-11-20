
"""Celery application for RECON X background jobs."""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "recon_x",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks.ingest_task"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.tasks.ingest_task.process_ingestion": {
            "queue": "ingestion",
        },
    },
)
