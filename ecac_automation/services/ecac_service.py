import hashlib
import structlog

from ecac_automation.browser.playwright_client import EcacBrowserClient
from ecac_automation.browser.session_store import SessionStore
from ecac_automation.parser.fiscal_parser import FiscalSummaryParser
from ecac_automation.services.cache import SmartCache

logger = structlog.get_logger(__name__)


class EcacService:
    def __init__(self, browser: EcacBrowserClient, sessions: SessionStore, cache: SmartCache):
        self.browser = browser
        self.sessions = sessions
        self.cache = cache
        self.parser = FiscalSummaryParser()

    def login(self, tenant_id: str, cert_path: str, cert_password: str) -> None:
        current_state = self.sessions.get(tenant_id)
        new_state = self.browser.login_with_certificate(cert_path, cert_password, current_state)
        self.sessions.set(tenant_id, new_state)
        logger.info("session_refreshed", tenant_id=tenant_id)

    def extract_structured(self, tenant_id: str, page_html: str) -> dict:
        cache_key = f"ecac:parsed:{tenant_id}:{hashlib.md5(page_html.encode()).hexdigest()}"
        cached = self.cache.get_json(cache_key)
        if cached:
            logger.info("cache_hit", tenant_id=tenant_id)
            return cached
        parsed = self.parser.parse(page_html)
        self.cache.set_json(cache_key, parsed, ttl=900)
        return parsed
