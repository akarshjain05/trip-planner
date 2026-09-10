from celery import Celery
from app.core.config import get_settings

settings = get_settings()
celery_app = Celery(
    "trip_planner",
    broker=settings.CELERY_BROKER_URL or settings.REDIS_URL,
    backend=settings.CELERY_RESULT_BACKEND or settings.REDIS_URL,
    include=["app.workers.tasks"],
)
celery_app.conf.update(
    task_serializer="json", result_serializer="json", accept_content=["json"],
    task_track_started=True, task_acks_late=True,       # redeliver if a worker dies mid-task
    worker_prefetch_multiplier=1,                        # planning tasks are long-running
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
)
