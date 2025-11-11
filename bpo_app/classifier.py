from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Session

from .models import Category, Transaction


def classify_transaction(db: Session, transaction: Transaction) -> None:
    if transaction.category_id:
        return

    categories: Iterable[Category] = (
        db.query(Category)
        .filter(Category.company_id == transaction.company_id)
        .order_by(Category.name.asc())
        .all()
    )
    description = (transaction.description or "").lower()
    for category in categories:
        if not category.keywords:
            continue
        keywords = [keyword.strip().lower() for keyword in category.keywords.split(",") if keyword.strip()]
        if any(keyword in description for keyword in keywords):
            transaction.category_id = category.id
            transaction.auto_classified = True
            break


def ensure_default_categories(db: Session, company_id: int) -> None:
    existing = db.query(Category).filter(Category.company_id == company_id).count()
    if existing:
        return

    defaults = [
        ("Vendas", "recebimento, pix, venda, deposito"),
        ("Serviços", "mensalidade, honorário"),
        ("Folha de Pagamento", "salario, holerite, folha"),
        ("Impostos", "taxa, imposto, guiapgto, darf"),
        ("Custos Fixos", "aluguel, energia, telefone, internet"),
        ("Custos Variáveis", "fornecedor, compra, estoque"),
        ("Outros", "transferencia, ajuste"),
    ]
    for name, keywords in defaults:
        category = Category(company_id=company_id, name=name, keywords=keywords)
        db.add(category)
    db.commit()
