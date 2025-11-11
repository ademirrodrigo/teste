from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import List

import pandas as pd
from fastapi import HTTPException, UploadFile, status
from ofxparse import OfxParser

from .models import TransactionType

EXPECTED_COLUMNS = {"data", "descricao", "valor", "tipo"}


def normalize_record(record: dict) -> dict:
    description = str(record.get("descricao") or record.get("description") or "").strip()
    amount_raw = record.get("valor") or record.get("amount") or 0
    txn_type_raw = str(record.get("tipo") or record.get("type") or "").lower()
    date_raw = record.get("data") or record.get("date")

    if isinstance(date_raw, datetime):
        date_value = date_raw.date()
    elif isinstance(date_raw, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
            try:
                date_value = datetime.strptime(date_raw.strip(), fmt).date()
                break
            except ValueError:
                continue
        else:
            raise HTTPException(status_code=400, detail=f"Data inválida: {date_raw}")
    else:
        raise HTTPException(status_code=400, detail="Coluna de data ausente")

    if isinstance(amount_raw, str):
        cleaned = amount_raw.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
        try:
            amount = float(cleaned)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Valor inválido: {amount_raw}") from exc
    else:
        amount = float(amount_raw)
    if txn_type_raw in {"entrada", "receita", "credito", "in"}:
        txn_type = TransactionType.INFLOW
    elif txn_type_raw in {"saida", "despesa", "debito", "out"}:
        txn_type = TransactionType.OUTFLOW
    else:
        txn_type = TransactionType.INFLOW if amount >= 0 else TransactionType.OUTFLOW

    return {
        "date": date_value,
        "description": description,
        "amount": abs(amount),
        "transaction_type": txn_type,
    }


def read_csv(file_bytes: bytes) -> List[dict]:
    text_stream = io.StringIO(file_bytes.decode("utf-8-sig"))
    sample = text_stream.read(2048)
    text_stream.seek(0)
    try:
        dialect = csv.Sniffer().sniff(sample)
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(text_stream, dialect=dialect)
    records = [normalize_record(row) for row in reader]
    return records


def read_excel(file_bytes: bytes) -> List[dict]:
    stream = io.BytesIO(file_bytes)
    df = pd.read_excel(stream)
    df.columns = [col.strip().lower() for col in df.columns]
    if not EXPECTED_COLUMNS.issubset(set(df.columns)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Planilha deve conter colunas: data, descricao, valor, tipo",
        )
    records = [normalize_record(row) for row in df.to_dict(orient="records")]
    return records


def read_ofx(file_bytes: bytes) -> List[dict]:
    stream = io.BytesIO(file_bytes)
    ofx = OfxParser.parse(stream)
    records: List[dict] = []
    for account in ofx.accounts:
        for transaction in account.statement.transactions:
            txn_type = (
                TransactionType.INFLOW
                if transaction.amount >= 0
                else TransactionType.OUTFLOW
            )
            records.append(
                {
                    "date": transaction.date.date(),
                    "description": transaction.memo or transaction.payee or "OFX",
                    "amount": abs(transaction.amount),
                    "transaction_type": txn_type,
                }
            )
    return records


def parse_upload(file: UploadFile) -> List[dict]:
    content = file.file.read()
    filename = file.filename or "arquivo"
    suffix = filename.split(".")[-1].lower()

    if suffix in {"csv"}:
        return read_csv(content)
    if suffix in {"xls", "xlsx"}:
        return read_excel(content)
    if suffix == "ofx":
        return read_ofx(content)

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato não suportado")
