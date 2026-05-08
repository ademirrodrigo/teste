from fastapi import APIRouter
from pydantic import BaseModel

from ecac_automation.workers.tasks import login_task, extract_task

router = APIRouter(prefix="/v1")


class LoginPayload(BaseModel):
    tenant_id: str
    cert_path: str
    cert_password: str


@router.post("/auth/login")
def enqueue_login(payload: LoginPayload):
    task = login_task.delay(payload.tenant_id, payload.cert_path, payload.cert_password)
    return {"task_id": task.id, "status": "queued"}


class ParsePayload(BaseModel):
    tenant_id: str
    html: str


@router.post("/extract")
def enqueue_extract(payload: ParsePayload):
    task = extract_task.delay(payload.tenant_id, payload.html)
    return {"task_id": task.id, "status": "queued"}
