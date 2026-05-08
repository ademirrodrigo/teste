from celery.utils.log import get_task_logger

from ecac_automation.browser.playwright_client import EcacBrowserClient
from ecac_automation.browser.session_store import SessionStore
from ecac_automation.core.config import get_settings
from ecac_automation.services.cache import SmartCache
from ecac_automation.services.ecac_service import EcacService
from ecac_automation.workers.celery_app import celery_app

logger = get_task_logger(__name__)
settings = get_settings()


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def login_task(self, tenant_id: str, cert_path: str, cert_password: str):
    service = EcacService(
        browser=EcacBrowserClient(headless=settings.playwright_headless),
        sessions=SessionStore(settings.redis_url, settings.session_ttl_seconds),
        cache=SmartCache(settings.redis_url),
    )
    service.login(tenant_id, cert_path, cert_password)
    logger.info("login_task_ok", tenant_id=tenant_id)


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def extract_task(self, tenant_id: str, html: str):
    service = EcacService(
        browser=EcacBrowserClient(headless=settings.playwright_headless),
        sessions=SessionStore(settings.redis_url, settings.session_ttl_seconds),
        cache=SmartCache(settings.redis_url),
    )
    return service.extract_structured(tenant_id, html)
