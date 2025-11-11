from __future__ import annotations

import io
import logging
import os
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import database
from .auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    require_role,
    set_secret_key,
    verify_password,
)
from .classifier import classify_transaction, ensure_default_categories
from .database import get_db
from .importers import parse_upload
from .models import (
    BankAccount,
    Category,
    ChecklistTask,
    Company,
    FinancialGoal,
    TaskStatus,
    Transaction,
    TransactionType,
    UploadLog,
    User,
    UserRole,
)
from .nfse_client import (
    NFSeClient,
    NFSeClientConfig,
    NFSeConfigurationError,
    NFSeOperationError,
    NFSeServiceError,
)
from .nfse_goiania import build_goiania_payload
from .schemas import (
    BankAccountCreate,
    BankAccountRead,
    BankAccountUpdate,
    CashFlowEntry,
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    ChecklistTaskCreate,
    ChecklistTaskRead,
    ChecklistTaskUpdate,
    CompanyCreate,
    CompanyRead,
    CompanyUpdate,
    CurrentUser,
    DRESummary,
    DashboardHighlight,
    FinancialGoalCreate,
    FinancialGoalProgress,
    FinancialGoalRead,
    FinancialGoalUpdate,
    FinancialGoalSummary,
    FinancialHealthReport,
    GoalStatus,
    LoginRequest,
    GoianiaNfseEmissionRequest,
    NFSeCallRequest,
    NFSeCallResponse,
    OutstandingEntry,
    SimpleMessage,
    TokenResponse,
    TransactionCreate,
    TransactionRead,
    TransactionUpdate,
    UploadSummary,
    UserCreate,
    UserRead,
    UserUpdate,
    TaskSummary,
)
from .settings import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()
_nfse_client: Optional[NFSeClient] = None
_nfse_config: Optional[NFSeClientConfig] = None


def _build_nfse_config(payload: NFSeCallRequest) -> Optional[NFSeClientConfig]:
    wsdl_url = payload.wsdl_url or settings.nfse_wsdl_url
    if not wsdl_url:
        return None
    timeout = payload.timeout or settings.nfse_timeout
    verify_ssl = payload.verify_ssl if payload.verify_ssl is not None else settings.nfse_verify_ssl
    return NFSeClientConfig(
        wsdl_url=wsdl_url,
        service_url=payload.service_url or settings.nfse_service_url,
        timeout=timeout,
        verify_ssl=verify_ssl,
    )


def resolve_nfse_client(config: NFSeClientConfig, use_cache: bool = True) -> NFSeClient:
    global _nfse_client, _nfse_config
    if not use_cache:
        return NFSeClient(config)
    if _nfse_client is None or _nfse_config != config:
        _nfse_client = NFSeClient(config)
        _nfse_config = config
    return _nfse_client


def format_brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def resolve_company_id(company_id: Optional[int], current_user: CurrentUser) -> int:
    if current_user.role == UserRole.CLIENT:
        if not current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seu usuário não está vinculado a nenhuma empresa.",
            )
        if company_id and company_id != current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você só pode acessar dados da sua empresa.",
            )
        return current_user.company_id
    if company_id is None:
        raise HTTPException(status_code=400, detail="Informe a empresa desejada.")
    return company_id


def ensure_company_exists(db: Session, company_id: int) -> Company:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return company


def ensure_company_access(company_id: int, current_user: CurrentUser) -> None:
    if current_user.role == UserRole.CLIENT and current_user.company_id != company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ação permitida apenas para a sua empresa.",
        )


def calculate_goal_progress(db: Session, goal: FinancialGoal) -> FinancialGoalProgress:
    total = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.company_id == goal.company_id,
            Transaction.transaction_type == goal.direction,
            Transaction.date >= goal.period_start,
            Transaction.date <= goal.period_end,
        )
        .scalar()
    )
    actual_amount = float(total or 0)
    target_amount = float(goal.target_amount or 0)
    remaining_amount = max(target_amount - actual_amount, 0.0)
    today = date.today()

    if goal.direction == TransactionType.INFLOW:
        achieved = actual_amount >= target_amount and target_amount > 0
        status = GoalStatus.ACHIEVED if achieved else GoalStatus.IN_PROGRESS
        if today > goal.period_end and not achieved:
            status = GoalStatus.MISSED
        progress_percentage = (
            min(100.0, (actual_amount / target_amount) * 100) if target_amount else 0.0
        )
        if status == GoalStatus.ACHIEVED:
            message = "Meta atingida! Continue acompanhando o período."
        elif status == GoalStatus.MISSED:
            message = "O período encerrou antes de atingir a meta. Revise os próximos passos."
        else:
            message = f"Faltam {format_brl(remaining_amount)} para chegar ao objetivo."
    else:
        consumed_percentage = (
            min(100.0, (actual_amount / target_amount) * 100) if target_amount else 0.0
        )
        status = GoalStatus.IN_PROGRESS
        if actual_amount > target_amount and target_amount > 0:
            status = GoalStatus.MISSED
        if today > goal.period_end:
            status = GoalStatus.ACHIEVED if actual_amount <= target_amount else GoalStatus.MISSED
        progress_percentage = consumed_percentage
        remaining_amount = (
            max(target_amount - actual_amount, 0.0) if actual_amount <= target_amount else 0.0
        )
        if status == GoalStatus.MISSED:
            message = "Os gastos passaram do limite planejado. Ajuste o próximo período."
        elif status == GoalStatus.ACHIEVED:
            message = "Período encerrado com gastos dentro do limite esperado."
        else:
            message = f"Limite disponível de {format_brl(remaining_amount)} até o fim do período."

    return FinancialGoalProgress(
        goal=FinancialGoalRead.model_validate(goal),
        actual_amount=actual_amount,
        remaining_amount=remaining_amount,
        progress_percentage=round(progress_percentage, 2),
        status=status,
        message=message,
    )


def serialize_task(task: ChecklistTask) -> ChecklistTaskRead:
    return ChecklistTaskRead.model_validate(task)


app = FastAPI(title="BPO Financeiro Simples", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


@app.on_event("startup")
def on_startup() -> None:
    if database.engine is None:
        database.init_engine()

    database.Base.metadata.create_all(bind=database.engine)
    set_secret_key(settings.secret_key)

    if settings.secret_key == "troque-essa-chave":
        logger.warning(
            "BPO_SECRET_KEY não definido. Use um valor forte antes de rodar em produção."
        )

    session_factory = database.get_sessionmaker()
    with session_factory() as db:
        admin_email = (settings.admin_email or "admin@bpo.exemplo.com").strip().lower()
        admin_password = settings.admin_password or "admin123"

        admin = db.query(User).filter(func.lower(User.email) == admin_email).first()
        created_admin = False

        if admin is None:
            admin = User(
                full_name=settings.admin_name or "Administrador",
                email=admin_email,
                password_hash=get_password_hash(admin_password),
                role=UserRole.ADMIN,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            created_admin = True
            logger.info(
                "Administrador padrão criado com o e-mail %s. Atualize a senha após o primeiro login.",
                admin_email,
            )

        updates_performed = False

        if admin.role != UserRole.ADMIN:
            admin.role = UserRole.ADMIN
            updates_performed = True

        if settings.admin_password_from_env and settings.admin_password:
            if not verify_password(settings.admin_password, admin.password_hash):
                admin.password_hash = get_password_hash(settings.admin_password)
                updates_performed = True
                logger.info(
                    "Senha do administrador %s sincronizada com o valor definido em BPO_ADMIN_PASSWORD.",
                    admin_email,
                )

        if updates_performed:
            db.commit()

        if created_admin and admin_password == "admin123":
            logger.warning(
                "BPO_ADMIN_PASSWORD não definido. A senha padrão 'admin123' está em uso.",
            )



@app.get("/", response_class=HTMLResponse)
def root_page() -> str:
    if os.path.isdir(FRONTEND_DIR):
        with open(os.path.join(FRONTEND_DIR, "index.html"), "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>BPO Financeiro Simples</h1><p>Aplicação em execução.</p>"


@app.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = request.email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    token = create_access_token({"sub": user.id, "role": user.role.value})
    return TokenResponse(access_token=token)


@app.get("/auth/me", response_model=UserRead)
def read_current_user(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> UserRead:
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return UserRead.model_validate(user)


@app.post("/companies", response_model=CompanyRead)
def create_company(
    payload: CompanyCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_role(UserRole.ADMIN, UserRole.STAFF)),
) -> CompanyRead:
    company = Company(**payload.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    ensure_default_categories(db, company.id)
    return CompanyRead.model_validate(company)


@app.get("/companies", response_model=list[CompanyRead])
def list_companies(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CompanyRead]:
    query = db.query(Company)
    if current_user.role == UserRole.CLIENT:
        query = query.filter(Company.id == current_user.company_id)
    companies = query.order_by(Company.name.asc()).all()
    return [CompanyRead.model_validate(company) for company in companies]


@app.put("/companies/{company_id}", response_model=CompanyRead)
def update_company(
    company_id: int,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_role(UserRole.ADMIN, UserRole.STAFF)),
) -> CompanyRead:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, key, value)
    db.commit()
    db.refresh(company)
    return CompanyRead.model_validate(company)


@app.delete("/companies/{company_id}", response_model=SimpleMessage)
def delete_company(
    company_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_role(UserRole.ADMIN)),
) -> SimpleMessage:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    db.delete(company)
    db.commit()
    return SimpleMessage(message="Empresa removida com sucesso")


@app.post("/users", response_model=UserRead)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(UserRole.ADMIN, UserRole.STAFF)),
) -> UserRead:
    if payload.role == UserRole.CLIENT and not payload.company_id:
        raise HTTPException(status_code=400, detail="Cliente precisa estar vinculado a uma empresa")
    user = User(
        full_name=payload.full_name,
        email=payload.email.lower(),
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        company_id=payload.company_id,
        is_active=payload.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@app.get("/users", response_model=list[UserRead])
def list_users(
    current_user: CurrentUser = Depends(require_role(UserRole.ADMIN, UserRole.STAFF)),
    db: Session = Depends(get_db),
) -> list[UserRead]:
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [UserRead.model_validate(user) for user in users]


@app.put("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_role(UserRole.ADMIN, UserRole.STAFF)),
) -> UserRead:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    update_data = payload.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        user.password_hash = get_password_hash(update_data.pop("password"))
    for key, value in update_data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@app.post("/bank-accounts", response_model=BankAccountRead)
def create_bank_account(
    payload: BankAccountCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BankAccountRead:
    if current_user.role == UserRole.CLIENT and current_user.company_id != payload.company_id:
        raise HTTPException(status_code=403, detail="Conta bancária deve pertencer à sua empresa")
    account = BankAccount(**payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return BankAccountRead.model_validate(account)


@app.get("/bank-accounts", response_model=list[BankAccountRead])
def list_bank_accounts(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    company_id: Optional[int] = None,
) -> list[BankAccountRead]:
    query = db.query(BankAccount)
    if current_user.role == UserRole.CLIENT:
        query = query.filter(BankAccount.company_id == current_user.company_id)
    elif company_id:
        query = query.filter(BankAccount.company_id == company_id)
    accounts = query.order_by(BankAccount.name.asc()).all()
    return [BankAccountRead.model_validate(account) for account in accounts]


@app.post("/categories", response_model=CategoryRead)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> CategoryRead:
    if current_user.role == UserRole.CLIENT and payload.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Categoria deve pertencer à sua empresa")
    category = Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return CategoryRead.model_validate(category)


@app.get("/categories", response_model=list[CategoryRead])
def list_categories(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    company_id: Optional[int] = None,
) -> list[CategoryRead]:
    query = db.query(Category)
    if current_user.role == UserRole.CLIENT:
        query = query.filter(Category.company_id == current_user.company_id)
    elif company_id:
        query = query.filter(Category.company_id == company_id)
    categories = query.order_by(Category.name.asc()).all()
    return [CategoryRead.model_validate(category) for category in categories]


@app.post("/financial-goals", response_model=FinancialGoalRead)
def create_financial_goal(
    payload: FinancialGoalCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> FinancialGoalRead:
    ensure_company_access(payload.company_id, current_user)
    ensure_company_exists(db, payload.company_id)
    goal = FinancialGoal(**payload.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return FinancialGoalRead.model_validate(goal)


@app.get("/financial-goals", response_model=list[FinancialGoalProgress])
def list_financial_goals(
    company_id: Optional[int] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FinancialGoalProgress]:
    target_company_id = resolve_company_id(company_id, current_user)
    ensure_company_exists(db, target_company_id)
    goals = (
        db.query(FinancialGoal)
        .filter(FinancialGoal.company_id == target_company_id)
        .order_by(FinancialGoal.period_end.asc())
        .all()
    )
    progress_items = [calculate_goal_progress(db, goal) for goal in goals]
    progress_items.sort(
        key=lambda item: (
            item.goal.archived,
            item.status == GoalStatus.ACHIEVED,
            item.goal.period_end,
        )
    )
    return progress_items


@app.get("/financial-goals/summary", response_model=FinancialGoalSummary)
def summarize_financial_goals(
    company_id: Optional[int] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FinancialGoalSummary:
    target_company_id = resolve_company_id(company_id, current_user)
    ensure_company_exists(db, target_company_id)
    goals = (
        db.query(FinancialGoal)
        .filter(FinancialGoal.company_id == target_company_id)
        .order_by(FinancialGoal.period_end.asc())
        .all()
    )
    progress_items = [calculate_goal_progress(db, goal) for goal in goals]
    archived = sum(1 for goal in goals if goal.archived)
    achieved = sum(1 for item in progress_items if item.status == GoalStatus.ACHIEVED)
    in_progress = sum(1 for item in progress_items if item.status == GoalStatus.IN_PROGRESS)
    missed = sum(1 for item in progress_items if item.status == GoalStatus.MISSED)
    upcoming = [item for item in progress_items if not item.goal.archived]
    upcoming.sort(
        key=lambda item: (
            item.status != GoalStatus.MISSED,
            item.status == GoalStatus.ACHIEVED,
            item.goal.period_end,
        )
    )
    upcoming = upcoming[:3]
    today = date.today()
    future_candidates = [
        item
        for item in progress_items
        if not item.goal.archived and item.goal.period_end >= today
    ]
    future_candidates.sort(key=lambda item: item.goal.period_end)
    next_deadline = future_candidates[0].goal.period_end if future_candidates else None
    return FinancialGoalSummary(
        total=len(goals),
        archived=archived,
        achieved=achieved,
        in_progress=in_progress,
        missed=missed,
        upcoming=upcoming,
        next_deadline=next_deadline,
    )


@app.get("/financial-goals/{goal_id}", response_model=FinancialGoalRead)
def get_financial_goal(
    goal_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FinancialGoalRead:
    goal = db.query(FinancialGoal).filter(FinancialGoal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Meta não encontrada")
    ensure_company_access(goal.company_id, current_user)
    return FinancialGoalRead.model_validate(goal)


@app.put("/financial-goals/{goal_id}", response_model=FinancialGoalRead)
def update_financial_goal(
    goal_id: int,
    payload: FinancialGoalUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> FinancialGoalRead:
    goal = db.query(FinancialGoal).filter(FinancialGoal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Meta não encontrada")
    ensure_company_access(goal.company_id, current_user)
    update_data = payload.model_dump(exclude_unset=True)
    new_period_start = update_data.get("period_start", goal.period_start)
    new_period_end = update_data.get("period_end", goal.period_end)
    if new_period_start and new_period_end and new_period_end < new_period_start:
        raise HTTPException(
            status_code=400,
            detail="A data final deve ser posterior ou igual à data inicial da meta.",
        )
    if "target_amount" in update_data and update_data["target_amount"] is not None:
        if update_data["target_amount"] <= 0:
            raise HTTPException(status_code=400, detail="Informe um valor de meta maior que zero.")
    for key, value in update_data.items():
        setattr(goal, key, value)
    db.commit()
    db.refresh(goal)
    return FinancialGoalRead.model_validate(goal)


@app.delete("/financial-goals/{goal_id}", response_model=SimpleMessage)
def delete_financial_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> SimpleMessage:
    goal = db.query(FinancialGoal).filter(FinancialGoal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Meta não encontrada")
    ensure_company_access(goal.company_id, current_user)
    db.delete(goal)
    db.commit()
    return SimpleMessage(message="Meta removida com sucesso")


@app.post("/tasks", response_model=ChecklistTaskRead)
def create_task(
    payload: ChecklistTaskCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ChecklistTaskRead:
    ensure_company_access(payload.company_id, current_user)
    ensure_company_exists(db, payload.company_id)
    task = ChecklistTask(
        company_id=payload.company_id,
        title=payload.title,
        description=payload.description,
        status=payload.status or TaskStatus.OPEN,
        due_date=payload.due_date,
        assigned_to_id=payload.assigned_to_id,
        created_by_id=current_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return serialize_task(task)


@app.get("/tasks", response_model=list[ChecklistTaskRead])
def list_tasks(
    company_id: Optional[int] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ChecklistTaskRead]:
    target_company_id = resolve_company_id(company_id, current_user)
    ensure_company_exists(db, target_company_id)
    tasks = (
        db.query(ChecklistTask)
        .filter(ChecklistTask.company_id == target_company_id)
        .all()
    )
    tasks.sort(
        key=lambda task: (
            task.status == TaskStatus.DONE,
            task.due_date is None,
            task.due_date or date.max,
            task.created_at,
        )
    )
    return [serialize_task(task) for task in tasks]


@app.get("/tasks/summary", response_model=TaskSummary)
def summarize_tasks(
    company_id: Optional[int] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskSummary:
    target_company_id = resolve_company_id(company_id, current_user)
    ensure_company_exists(db, target_company_id)
    tasks = (
        db.query(ChecklistTask)
        .filter(ChecklistTask.company_id == target_company_id)
        .all()
    )
    today = date.today()
    soon_threshold = today + timedelta(days=7)
    open_count = sum(1 for task in tasks if task.status == TaskStatus.OPEN)
    in_progress_count = sum(1 for task in tasks if task.status == TaskStatus.IN_PROGRESS)
    done_count = sum(1 for task in tasks if task.status == TaskStatus.DONE)
    overdue_count = sum(
        1
        for task in tasks
        if task.status != TaskStatus.DONE and task.due_date and task.due_date < today
    )
    due_today_count = sum(
        1
        for task in tasks
        if task.status != TaskStatus.DONE and task.due_date == today
    )
    due_soon_count = sum(
        1
        for task in tasks
        if task.status != TaskStatus.DONE
        and task.due_date
        and today < task.due_date <= soon_threshold
    )
    unassigned_count = sum(1 for task in tasks if task.assigned_to_id is None)
    spotlight_candidates = [task for task in tasks if task.status != TaskStatus.DONE]
    spotlight_candidates.sort(
        key=lambda task: (
            task.due_date is None,
            task.due_date or date.max,
            task.created_at,
        )
    )
    spotlight = [serialize_task(task) for task in spotlight_candidates[:6]]
    return TaskSummary(
        total=len(tasks),
        open=open_count,
        in_progress=in_progress_count,
        done=done_count,
        overdue=overdue_count,
        due_today=due_today_count,
        due_soon=due_soon_count,
        unassigned=unassigned_count,
        spotlight=spotlight,
    )


@app.get("/tasks/{task_id}", response_model=ChecklistTaskRead)
def get_task(
    task_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChecklistTaskRead:
    task = db.query(ChecklistTask).filter(ChecklistTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    ensure_company_access(task.company_id, current_user)
    return serialize_task(task)


@app.put("/tasks/{task_id}", response_model=ChecklistTaskRead)
def update_task(
    task_id: int,
    payload: ChecklistTaskUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ChecklistTaskRead:
    task = db.query(ChecklistTask).filter(ChecklistTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    ensure_company_access(task.company_id, current_user)
    update_data = payload.model_dump(exclude_unset=True)
    for key in ("title", "description", "due_date", "assigned_to_id"):
        if key in update_data:
            setattr(task, key, update_data[key])
    if "status" in update_data and update_data["status"]:
        new_status = update_data["status"]
        task.status = new_status
        if new_status == TaskStatus.DONE:
            task.completed_at = datetime.utcnow()
        else:
            task.completed_at = None
    db.commit()
    db.refresh(task)
    return serialize_task(task)


@app.delete("/tasks/{task_id}", response_model=SimpleMessage)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> SimpleMessage:
    task = db.query(ChecklistTask).filter(ChecklistTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    ensure_company_access(task.company_id, current_user)
    db.delete(task)
    db.commit()
    return SimpleMessage(message="Tarefa removida com sucesso")


@app.post("/transactions", response_model=TransactionRead)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> TransactionRead:
    if current_user.role == UserRole.CLIENT and payload.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Lançamento deve pertencer à sua empresa")
    transaction = Transaction(**payload.model_dump())
    classify_transaction(db, transaction)
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return TransactionRead.model_validate(transaction)


@app.get("/transactions", response_model=list[TransactionRead])
def list_transactions(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    company_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[TransactionRead]:
    query = db.query(Transaction)
    if current_user.role == UserRole.CLIENT:
        query = query.filter(Transaction.company_id == current_user.company_id)
    elif company_id:
        query = query.filter(Transaction.company_id == company_id)
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    transactions = query.order_by(Transaction.date.desc()).all()
    return [TransactionRead.model_validate(transaction) for transaction in transactions]


@app.put("/transactions/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> TransactionRead:
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    if current_user.role == UserRole.CLIENT and transaction.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Você não pode editar este lançamento")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(transaction, key, value)
    transaction.auto_classified = False
    classify_transaction(db, transaction)
    db.commit()
    db.refresh(transaction)
    return TransactionRead.model_validate(transaction)


@app.post("/transactions/import", response_model=UploadSummary)
def import_transactions(
    company_id: int,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UploadSummary:
    if current_user.role == UserRole.CLIENT and company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Importação deve pertencer à sua empresa")

    records = parse_upload(file)
    imported = 0
    for data in records:
        transaction = Transaction(
            company_id=company_id,
            date=data["date"],
            description=data["description"],
            amount=data["amount"],
            transaction_type=data["transaction_type"],
        )
        classify_transaction(db, transaction)
        db.add(transaction)
        imported += 1
    db.commit()

    upload_log = UploadLog(
        company_id=company_id,
        filename=file.filename or "arquivo",
        uploaded_by=current_user.id,
        total_records=len(records),
        notes="Importação concluída",
    )
    db.add(upload_log)
    db.commit()

    return UploadSummary(
        filename=upload_log.filename,
        total_records=upload_log.total_records,
        imported=imported,
        skipped=upload_log.total_records - imported,
        notes=upload_log.notes,
    )


def build_cash_flow(db: Session, company_id: int, start_date: date, end_date: date) -> list[CashFlowEntry]:
    cash_flow: list[CashFlowEntry] = []
    current_month = date(start_date.year, start_date.month, 1)
    balance = 0.0
    while current_month <= end_date:
        if current_month.month == 12:
            next_month = date(current_month.year + 1, 1, 1)
        else:
            next_month = date(current_month.year, current_month.month + 1, 1)
        period_start = max(start_date, current_month)
        period_end = min(end_date, next_month - timedelta(days=1))
        inflow = (
            db.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.company_id == company_id,
                Transaction.transaction_type == TransactionType.INFLOW,
                Transaction.date >= period_start,
                Transaction.date <= period_end,
            )
            .scalar()
        )
        outflow = (
            db.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.company_id == company_id,
                Transaction.transaction_type == TransactionType.OUTFLOW,
                Transaction.date >= period_start,
                Transaction.date <= period_end,
            )
            .scalar()
        )
        balance += float(inflow or 0) - float(outflow or 0)
        cash_flow.append(
            CashFlowEntry(
                label=f"{current_month.month:02d}/{current_month.year}",
                inflow=float(inflow or 0),
                outflow=float(outflow or 0),
                balance=balance,
            )
        )
        current_month = next_month
    return cash_flow


def build_dre(db: Session, company_id: int, start_date: date, end_date: date) -> DRESummary:
    revenue = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.company_id == company_id,
            Transaction.transaction_type == TransactionType.INFLOW,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        .scalar()
    )
    expenses = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.company_id == company_id,
            Transaction.transaction_type == TransactionType.OUTFLOW,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        .scalar()
    )
    revenue_value = float(revenue or 0)
    expenses_value = float(expenses or 0)
    result = revenue_value - expenses_value
    if result > 0:
        message = "A empresa está com saldo positivo no período."
    elif result == 0:
        message = "A empresa fechou o período empatada: o que entrou saiu."
    else:
        message = "Atenção: as saídas superaram as entradas. Revise seus gastos."
    return DRESummary(
        revenue=revenue_value,
        expenses=expenses_value,
        result=result,
        message=message,
    )


def build_outstanding(
    db: Session, company_id: int, start_date: date, end_date: date, txn_type: TransactionType
) -> list[OutstandingEntry]:
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.company_id == company_id,
            Transaction.transaction_type == txn_type,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        .order_by(Transaction.date.asc())
        .all()
    )
    status_label = "a receber" if txn_type == TransactionType.INFLOW else "a pagar"
    return [
        OutstandingEntry(
            description=txn.description,
            due_date=txn.date,
            amount=float(txn.amount),
            status=status_label,
        )
        for txn in transactions
    ]


def compute_financial_health(
    db: Session, company_id: int, start_date: date, end_date: date
) -> FinancialHealthReport:
    cash_flow = build_cash_flow(db, company_id, start_date, end_date)
    dre = build_dre(db, company_id, start_date, end_date)
    payables = build_outstanding(db, company_id, start_date, end_date, TransactionType.OUTFLOW)
    receivables = build_outstanding(db, company_id, start_date, end_date, TransactionType.INFLOW)

    highlights = [
        DashboardHighlight(
            title="Saldo do período",
            value=f"R$ {dre.result:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            description="Mostra se você fechou o período no azul ou no vermelho.",
        ),
        DashboardHighlight(
            title="Entradas",
            value=f"R$ {dre.revenue:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            description="Total de valores que chegaram na conta.",
        ),
        DashboardHighlight(
            title="Saídas",
            value=f"R$ {dre.expenses:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            description="Quanto foi pago no período.",
        ),
    ]

    period_label = f"De {start_date.strftime('%d/%m/%Y')} até {end_date.strftime('%d/%m/%Y')}"

    return FinancialHealthReport(
        period=period_label,
        cash_flow=cash_flow,
        dre=dre,
        payables=payables,
        receivables=receivables,
        highlights=highlights,
    )


@app.get("/reports/financial-health", response_model=FinancialHealthReport)
def financial_health(
    company_id: int,
    start_date: date,
    end_date: date,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FinancialHealthReport:
    if current_user.role == UserRole.CLIENT and company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Relatório restrito à sua empresa")

    return compute_financial_health(db, company_id, start_date, end_date)


@app.get("/reports/export")
def export_report(
    company_id: int,
    start_date: date,
    end_date: date,
    report_type: str = "cashflow",
    export_format: str = "xlsx",
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == UserRole.CLIENT and company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Exportação restrita à sua empresa")

    report = compute_financial_health(db, company_id, start_date, end_date)

    if export_format == "xlsx":
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_cash = pd.DataFrame([entry.model_dump() for entry in report.cash_flow])
            df_cash.to_excel(writer, sheet_name="Fluxo de Caixa", index=False)
            dre_df = pd.DataFrame([
                {
                    "Entradas": report.dre.revenue,
                    "Saídas": report.dre.expenses,
                    "Resultado": report.dre.result,
                    "Mensagem": report.dre.message,
                }
            ])
            dre_df.to_excel(writer, sheet_name="Resumo", index=False)
            pd.DataFrame([entry.model_dump() for entry in report.payables]).to_excel(
                writer, sheet_name="A Pagar", index=False
            )
            pd.DataFrame([entry.model_dump() for entry in report.receivables]).to_excel(
                writer, sheet_name="A Receber", index=False
            )
        output.seek(0)
        filename = f"relatorio_{report_type}_{start_date}_{end_date}.xlsx"
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    if export_format == "pdf":
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table
        except ImportError as exc:  # pragma: no cover - guard if dependency missing
            raise HTTPException(status_code=500, detail="Dependência de PDF ausente") from exc

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph("Relatório Financeiro", styles["Heading1"]))
        story.append(Paragraph(report.period, styles["Normal"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Resumo do período", styles["Heading2"]))
        story.append(
            Table(
                [
                    ["Entradas", f"R$ {report.dre.revenue:,.2f}"],
                    ["Saídas", f"R$ {report.dre.expenses:,.2f}"],
                    ["Resultado", f"R$ {report.dre.result:,.2f}"],
                ]
            )
        )
        story.append(Spacer(1, 12))
        story.append(Paragraph(report.dre.message, styles["Italic"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Principais destaques", styles["Heading2"]))
        for highlight in report.highlights:
            story.append(Paragraph(f"<b>{highlight.title}</b>: {highlight.description} - {highlight.value}", styles["Normal"]))
        doc.build(story)
        buffer.seek(0)
        filename = f"relatorio_{report_type}_{start_date}_{end_date}.pdf"
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    raise HTTPException(status_code=400, detail="Formato de exportação não suportado")


@app.get("/dashboard/overview", response_model=list[DashboardHighlight])
def dashboard_overview(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DashboardHighlight]:
    if current_user.role == UserRole.CLIENT and not current_user.company_id:
        return []

    company_filter = current_user.company_id if current_user.role == UserRole.CLIENT else None

    total_companies = (
        db.query(func.count(Company.id))
        if current_user.role != UserRole.CLIENT
        else db.query(func.count(Company.id)).filter(Company.id == company_filter)
    ).scalar()

    total_users = (
        db.query(func.count(User.id))
        if current_user.role == UserRole.ADMIN
        else db.query(func.count(User.id)).filter(User.company_id == company_filter)
    ).scalar()

    total_transactions = (
        db.query(func.count(Transaction.id))
        if not company_filter
        else db.query(func.count(Transaction.id)).filter(Transaction.company_id == company_filter)
    ).scalar()

    highlights = [
        DashboardHighlight(
            title="Empresas acompanhadas" if current_user.role != UserRole.CLIENT else "Minha empresa",
            value=str(total_companies or 0),
            description="Quantidade de empresas atendidas pelo financeiro.",
        ),
        DashboardHighlight(
            title="Pessoas com acesso",
            value=str(total_users or 0),
            description="Usuários com acesso ao painel.",
        ),
        DashboardHighlight(
            title="Lançamentos registrados",
            value=str(total_transactions or 0),
            description="Soma de entradas e saídas cadastradas.",
        ),
    ]
    return highlights


@app.post("/integrations/nfse/{operation}", response_model=NFSeCallResponse)
async def trigger_nfse_operation(
    operation: str,
    payload: NFSeCallRequest,
    _: CurrentUser = Depends(require_role(UserRole.ADMIN, UserRole.STAFF)),
) -> NFSeCallResponse:
    config = _build_nfse_config(payload)
    if config is None:
        raise HTTPException(status_code=503, detail="Integração NFSe não está configurada.")

    client = resolve_nfse_client(config, use_cache=not payload.has_overrides())

    try:
        output_xml = await client.call_operation(operation, payload.nfse_cabec_msg, payload.nfse_dados_msg)
    except NFSeOperationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NFSeConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except NFSeServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return NFSeCallResponse(output_xml=output_xml)


@app.post("/integrations/nfse/goiania/emissao", response_model=NFSeCallResponse)
async def emitir_nfse_goiania(
    payload: GoianiaNfseEmissionRequest,
    current_user: CurrentUser = Depends(require_role(UserRole.ADMIN, UserRole.STAFF)),
) -> NFSeCallResponse:
    emission = payload.to_domain()
    cabecalho, dados = build_goiania_payload(emission)
    call_request = payload.to_call_request(cabecalho, dados)
    config = _build_nfse_config(call_request)
    if config is None:
        raise HTTPException(status_code=503, detail="Integração NFSe não está configurada.")

    client = resolve_nfse_client(config, use_cache=not call_request.has_overrides())

    try:
        output_xml = await client.call_operation("GerarNfse", call_request.nfse_cabec_msg, call_request.nfse_dados_msg)
    except NFSeOperationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NFSeConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except NFSeServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return NFSeCallResponse(output_xml=output_xml)
