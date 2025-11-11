from datetime import date, datetime
from enum import Enum
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, FieldValidationInfo, field_validator

from .models import TaskStatus, TransactionType, UserRole
from .nfse_goiania import (
    GoianiaNfseEmission,
    GoianiaPrestador,
    GoianiaServico,
    GoianiaServicoValores,
    GoianiaTomador,
    GoianiaTomadorEndereco,
)


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


class GoalStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    MISSED = "missed"


class FinancialGoalBase(BaseModel):
    name: str = Field(..., min_length=2)
    description: Optional[str] = Field(None, max_length=2000)
    target_amount: float = Field(..., gt=0)
    direction: TransactionType
    period_start: date
    period_end: date
    archived: bool = False

    @field_validator("period_end")
    @classmethod
    def validate_period(cls, value: date, info: FieldValidationInfo) -> date:
        start = info.data.get("period_start")
        if isinstance(start, date) and value < start:
            raise ValueError("A data final deve ser posterior ou igual à data inicial da meta.")
        return value


class FinancialGoalCreate(FinancialGoalBase):
    company_id: int


class FinancialGoalUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2)
    description: Optional[str] = Field(None, max_length=2000)
    target_amount: Optional[float] = Field(None, gt=0)
    direction: Optional[TransactionType] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    archived: Optional[bool] = None

    @field_validator("period_end")
    @classmethod
    def validate_period_end(cls, value: Optional[date], info: FieldValidationInfo) -> Optional[date]:
        start = info.data.get("period_start")
        if isinstance(start, date) and value is not None and value < start:
            raise ValueError("A data final deve ser posterior ou igual à data inicial da meta.")
        return value


class FinancialGoalRead(FinancialGoalBase):
    id: int
    company_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinancialGoalProgress(BaseModel):
    goal: FinancialGoalRead
    actual_amount: float
    remaining_amount: float
    progress_percentage: float
    status: GoalStatus
    message: str


class FinancialGoalSummary(BaseModel):
    total: int = 0
    archived: int = 0
    achieved: int = 0
    in_progress: int = 0
    missed: int = 0
    upcoming: list[FinancialGoalProgress] = Field(default_factory=list)
    next_deadline: Optional[date] = None


class TaskUserSummary(BaseModel):
    id: int
    full_name: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class ChecklistTaskBase(BaseModel):
    title: str = Field(..., min_length=2)
    description: Optional[str] = Field(None, max_length=4000)
    due_date: Optional[date] = None
    status: TaskStatus = TaskStatus.OPEN
    assigned_to_id: Optional[int] = None


class ChecklistTaskCreate(ChecklistTaskBase):
    company_id: int


class ChecklistTaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2)
    description: Optional[str] = Field(None, max_length=4000)
    due_date: Optional[date] = None
    status: Optional[TaskStatus] = None
    assigned_to_id: Optional[int] = Field(default=None)


class ChecklistTaskRead(ChecklistTaskBase):
    id: int
    company_id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    assigned_to: Optional[TaskUserSummary] = None
    created_by: Optional[TaskUserSummary] = None

    model_config = ConfigDict(from_attributes=True)


class TaskSummary(BaseModel):
    total: int = 0
    open: int = 0
    in_progress: int = 0
    done: int = 0
    overdue: int = 0
    due_today: int = 0
    due_soon: int = 0
    unassigned: int = 0
    spotlight: list[ChecklistTaskRead] = Field(default_factory=list)


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
    email: str = Field(..., min_length=3, description="Endereço de e-mail do usuário")
    password: str = Field(..., min_length=1, description="Senha de acesso")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Informe o e-mail do usuário.")
        return cleaned.lower()


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


class NFSeOverrides(BaseModel):
    wsdl_url: Optional[str] = Field(
        None,
        description="URL completa do WSDL para sobrescrever a configuração padrão (opcional)",
    )
    service_url: Optional[str] = Field(
        None,
        description="Endpoint completo do serviço SOAP quando diferente do WSDL (opcional)",
    )
    timeout: Optional[int] = Field(
        None,
        ge=1,
        le=600,
        description="Tempo máximo de espera pela resposta do serviço, em segundos (opcional)",
    )
    verify_ssl: Optional[bool] = Field(
        None,
        description="Define se a verificação de certificado SSL deve ser forçada ou não (opcional)",
    )

    @field_validator("wsdl_url", "service_url")
    @classmethod
    def normalize_optional_urls(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    def has_overrides(self) -> bool:
        return any(value is not None for value in (self.wsdl_url, self.service_url, self.timeout, self.verify_ssl))


class NFSeCallRequest(NFSeOverrides):
    nfse_cabec_msg: str = Field(..., min_length=1, description="XML do cabeçalho da requisição NFSe")
    nfse_dados_msg: str = Field(..., min_length=1, description="XML com os dados da requisição NFSe")

    @field_validator("nfse_cabec_msg", "nfse_dados_msg")
    @classmethod
    def ensure_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Informe o conteúdo XML da mensagem NFSe.")
        return cleaned


class NFSeCallResponse(BaseModel):
    output_xml: str = Field(..., description="XML devolvido pelo serviço NFSe")


class GoianiaNfsePrestador(BaseModel):
    cnpj: str = Field(..., min_length=1, description="CNPJ do prestador")
    inscricao_municipal: str = Field(..., min_length=1, description="Inscrição municipal do prestador")

    @field_validator("cnpj", "inscricao_municipal")
    @classmethod
    def remove_spaces(cls, value: str) -> str:
        return value.strip()


class GoianiaNfseEndereco(BaseModel):
    logradouro: str
    numero: str
    bairro: str
    codigo_municipio: str = Field("5208707", description="Código IBGE do município")
    uf: str = Field("GO", min_length=2, max_length=2)
    cep: Optional[str] = None
    complemento: Optional[str] = None

    @field_validator("logradouro", "numero", "bairro", "codigo_municipio", "uf")
    @classmethod
    def ensure_not_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Informe o endereço completo do tomador.")
        return cleaned


class GoianiaNfseTomador(BaseModel):
    razao_social: str
    cpf_cnpj: str
    inscricao_municipal: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    endereco: GoianiaNfseEndereco

    @field_validator("razao_social", "cpf_cnpj")
    @classmethod
    def sanitize_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Informe os dados do tomador.")
        return cleaned


class GoianiaNfseServicoValoresModel(BaseModel):
    valor_servicos: Decimal = Field(..., description="Valor bruto dos serviços")
    valor_deducoes: Decimal = Decimal("0")
    valor_pis: Decimal = Decimal("0")
    valor_cofins: Decimal = Decimal("0")
    valor_inss: Decimal = Decimal("0")
    valor_ir: Decimal = Decimal("0")
    valor_csll: Decimal = Decimal("0")
    outros_retencoes: Decimal = Decimal("0")
    iss_retido: int = Field(2, ge=1, le=2)
    valor_iss: Optional[Decimal] = None
    valor_iss_retido: Optional[Decimal] = None
    aliquota: Optional[Decimal] = None
    desconto_condicionado: Optional[Decimal] = None
    desconto_incondicionado: Optional[Decimal] = None


class GoianiaNfseServicoModel(BaseModel):
    item_lista_servico: str
    codigo_tributacao_municipio: str
    discriminacao: str
    codigo_municipio: str = Field("5208707", description="Código do município da prestação")
    valores: GoianiaNfseServicoValoresModel

    @field_validator("item_lista_servico", "codigo_tributacao_municipio", "discriminacao")
    @classmethod
    def ensure_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Informe os dados do serviço.")
        return cleaned


class GoianiaNfseEmissionRequest(NFSeOverrides):
    numero_lote: str = Field(..., description="Número do lote a ser enviado")
    numero_rps: str = Field(..., description="Número do RPS")
    serie_rps: str = Field(..., description="Série do RPS")
    tipo_rps: int = Field(1, ge=1, le=3)
    data_emissao: datetime = Field(..., description="Data e hora da emissão do RPS")
    natureza_operacao: int = Field(1, ge=1, le=6)
    regime_especial_tributacao: Optional[int] = Field(None, ge=1, le=6)
    optante_simples: int = Field(1, ge=1, le=2)
    incentivador_cultural: int = Field(2, ge=1, le=2)
    status_rps: int = Field(1, ge=1, le=2)
    prestador: GoianiaNfsePrestador
    servico: GoianiaNfseServicoModel
    tomador: GoianiaNfseTomador

    @field_validator("numero_lote", "numero_rps", "serie_rps")
    @classmethod
    def ensure_identifiers(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Informe os identificadores do RPS.")
        return cleaned

    def to_domain(self) -> GoianiaNfseEmission:
        valores = GoianiaServicoValores(**self.servico.valores.model_dump())
        servico = GoianiaServico(
            valores=valores,
            item_lista_servico=self.servico.item_lista_servico,
            codigo_tributacao_municipio=self.servico.codigo_tributacao_municipio,
            discriminacao=self.servico.discriminacao,
            codigo_municipio=self.servico.codigo_municipio,
        )
        prestador = GoianiaPrestador(**self.prestador.model_dump())
        endereco = GoianiaTomadorEndereco(**self.tomador.endereco.model_dump())
        tomador = GoianiaTomador(
            razao_social=self.tomador.razao_social,
            cpf_cnpj=self.tomador.cpf_cnpj,
            inscricao_municipal=self.tomador.inscricao_municipal,
            email=self.tomador.email,
            telefone=self.tomador.telefone,
            endereco=endereco,
        )
        return GoianiaNfseEmission(
            numero_lote=self.numero_lote,
            numero_rps=self.numero_rps,
            serie_rps=self.serie_rps,
            tipo_rps=self.tipo_rps,
            data_emissao=self.data_emissao,
            natureza_operacao=self.natureza_operacao,
            regime_especial_tributacao=self.regime_especial_tributacao,
            optante_simples=self.optante_simples,
            incentivador_cultural=self.incentivador_cultural,
            status_rps=self.status_rps,
            prestador=prestador,
            servico=servico,
            tomador=tomador,
        )

    def to_call_request(self, cabecalho: str, dados: str) -> NFSeCallRequest:
        return NFSeCallRequest(
            nfse_cabec_msg=cabecalho,
            nfse_dados_msg=dados,
            wsdl_url=self.wsdl_url,
            service_url=self.service_url,
            timeout=self.timeout,
            verify_ssl=self.verify_ssl,
        )
