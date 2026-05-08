from fastapi import FastAPI

from ecac_automation.api.routes import router
from ecac_automation.observability.logging import configure_logging

configure_logging()
app = FastAPI(title="e-CAC Automation")
app.include_router(router)
