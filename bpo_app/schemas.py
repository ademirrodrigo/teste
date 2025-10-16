from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import TransactionType, UserRole


class CompanyBase(BaseModel):
    name: str = Field(..., description="Nome da empresa")
    trade_name: Optional[str] = Field(None, description="Nome fantasia")
    document: Optional[str] = Field(None, description="CNPJ ou CPF")
    notes: Optional[str] = Field(None, description="Observações internas")


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    trade_name: Optional[str] = None
    document: Optional[str] = None
    notes: Optional[str] = None


class CompanyRead(CompanyBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    role: UserRole
    company_id: Optional[int] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    company_id: Optional[int] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)


class UserRead(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BankAccountBase(BaseModel):
    name: str
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    initial_balance: float = 0.0


class BankAccountCreate(BankAccountBase):
    company_id: int


class BankAccountUpdate(BaseModel):
    name: Optional[str] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    initial_balance: Optional[float] = None


class BankAccountRead(BankAccountBase):
    id: int
    company_id: int

    model_config = ConfigDict(from_attributes=True)


class CategoryBase(BaseModel):
    name: str
    keywords: Optional[str] = Field(
        None,
        description="Palavras-chave separadas por vírgula para classificação automática",
    )
    color: Optional[str] = Field(None, description="Cor usada na interface (hexadecimal)")


class CategoryCreate(CategoryBase):
    company_id: int


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    keywords: Optional[str] = None
    color: Optional[str] = None


class CategoryRead(CategoryBase):
    id: int
    company_id: int

    model_config = ConfigDict(from_attributes=True)


class TransactionBase(BaseModel):
    company_id: int
    bank_account_id: Optional[int] = None
    date: date
    description: str
    amount: float
    transaction_type: TransactionType
    category_id: Optional[int] = None
    notes: Optional[str] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    bank_account_id: Optional[int] = None
    date: Optional[date] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    transaction_type: Optional[TransactionType] = None
    category_id: Optional[int] = None
    notes: Optional[str] = None


class TransactionRead(TransactionBase):
    id: int
    auto_classified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UploadSummary(BaseModel):
    filename: str
    total_records: int
    imported: int
    skipped: int
    notes: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class DashboardHighlight(BaseModel):
    title: str
    value: str
    description: str


class CashFlowEntry(BaseModel):
    label: str
    inflow: float
    outflow: float
    balance: float


class DRESummary(BaseModel):
    revenue: float
    expenses: float
    result: float
    message: str


class OutstandingEntry(BaseModel):
    description: str
    due_date: date
    amount: float
    status: str


class FinancialHealthReport(BaseModel):
    period: str
    cash_flow: list[CashFlowEntry]
    dre: DRESummary
    payables: list[OutstandingEntry]
    receivables: list[OutstandingEntry]
    highlights: list[DashboardHighlight]


class CurrentUser(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: UserRole
    company_id: Optional[int] = None


class SimpleMessage(BaseModel):
    message: str
