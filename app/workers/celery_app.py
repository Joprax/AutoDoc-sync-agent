"""
Celery app instance. Same broker/backend pattern as pr-review-agent — Redis
doing double duty as message broker and result store.

Run a worker locally with:
    celery -A app.workers.celery_app worker --loglevel=info
"""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "doc_sync_agent",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
