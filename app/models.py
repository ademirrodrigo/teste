"""Modelos de dados utilizados pelo Coletor Fiscal."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .config import settings
from .utils.cnpj import sanitize_cnpj
from .database import Base


class Empresa(Base):
    """Representa uma empresa cadastrada com certificado digital."""

    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    cnpj: Mapped[str] = mapped_column(String(14), unique=True, index=True, nullable=False)
    uf: Mapped[str] = mapped_column(String(2), nullable=False, default="GO")
    certificado: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    certificado_senha: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documentos: Mapped[list["Documento"]] = relationship("Documento", back_populates="empresa")

    def certificado_path(self) -> Path:
        """Retorna o caminho absoluto do certificado A1 da empresa."""
        if not self.certificado:
            return settings.certs_dir / f"{sanitize_cnpj(self.cnpj)}.pfx"
        return settings.certs_dir / self.certificado


class Documento(Base):
    """Armazena metadados dos documentos coletados."""

    __tablename__ = "documentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)  # NFE / NFCE
    chave: Mapped[str] = mapped_column(String(44), unique=True, index=True, nullable=False)
    arquivo: Mapped[str] = mapped_column(Text, nullable=False)
    resumo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    empresa: Mapped[Empresa] = relationship("Empresa", back_populates="documentos")
