from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import structlog

logger = structlog.get_logger(__name__)


class EcacBrowserClient:
    def __init__(self, headless: bool = True):
        self.headless = headless

    def login_with_certificate(self, cert_path: str, cert_password: str, saved_state: dict | None = None) -> dict:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(storage_state=saved_state)
            page = context.new_page()
            try:
                page.goto("https://cav.receita.fazenda.gov.br/autenticacao/login", wait_until="domcontentloaded")
                page.get_by_role("button", name="Entrar com gov.br").click(timeout=15000)
                page.get_by_text("Seu certificado digital").click(timeout=15000)
                # Placeholder: integração real depende da seleção do certificado no SO.
                logger.info("cert_prompt_expected", cert_path=cert_path)
                page.wait_for_timeout(3000)
                if "captcha" in page.content().lower():
                    raise RuntimeError("CAPTCHA detectado. Encaminhar para fluxo manual/solver.")
                page.wait_for_url("**/ecac/**", timeout=30000)
                return context.storage_state()
            except PlaywrightTimeoutError as exc:
                logger.error("playwright_timeout", error=str(exc))
                raise
            finally:
                browser.close()
