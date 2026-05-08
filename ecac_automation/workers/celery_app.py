from celery import Celery

from ecac_automation.core.config import get_settings

settings = get_settings()

celery_app = Celery("ecac", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "ecac_automation.workers.tasks.login_task": {"queue": "auth"},
        "ecac_automation.workers.tasks.extract_task": {"queue": "extract"},
    },
)
