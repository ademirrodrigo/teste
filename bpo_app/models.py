from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SQLAlchemyEnum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    trade_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    document: Mapped[Optional[str]] = mapped_column(String(32), unique=True, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    users: Mapped[list["User"]] = relationship("User", back_populates="company")
    bank_accounts: Mapped[list["BankAccount"]] = relationship(
        "BankAccount", back_populates="company", cascade="all, delete-orphan"
    )
    categories: Mapped[list["Category"]] = relationship(
        "Category", back_populates="company", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="company", cascade="all, delete-orphan"
    )


class UserRole(str, PyEnum):
    ADMIN = "admin"
    STAFF = "staff"
    CLIENT = "client"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SQLAlchemyEnum(UserRole), nullable=False)
    company_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("companies.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped[Optional[Company]] = relationship("Company", back_populates="users")


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    bank_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    account_number: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    initial_balance: Mapped[float] = mapped_column(Float, default=0.0)

    company: Mapped[Company] = relationship("Company", back_populates="bank_accounts")
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="bank_account"
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    keywords: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    company: Mapped[Company] = relationship("Company", back_populates="categories")
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="category"
    )


class TransactionType(str, PyEnum):
    INFLOW = "inflow"
    OUTFLOW = "outflow"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), index=True)
    bank_account_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("bank_accounts.id"), nullable=True
    )
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(
        SQLAlchemyEnum(TransactionType), nullable=False
    )
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id"))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    auto_classified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped[Company] = relationship("Company", back_populates="transactions")
    bank_account: Mapped[Optional[BankAccount]] = relationship(
        "BankAccount", back_populates="transactions"
    )
    category: Mapped[Optional[Category]] = relationship(
        "Category", back_populates="transactions"
    )


class UploadLog(Base):
    __tablename__ = "upload_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"))
    filename: Mapped[str] = mapped_column(String(200), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    company: Mapped[Company] = relationship("Company")
