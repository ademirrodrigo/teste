"""Camada de dados SQLite para o MVP de cobrança via WhatsApp."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Dict, List

DB_PATH = Path("cobrancas.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(get_connection()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT NOT NULL,
                valor REAL NOT NULL,
                data_vencimento TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('pendente', 'pago')),
                ultimo_envio TEXT
            )
            """
        )
        conn.commit()


def listar_pendentes() -> List[Dict]:
    with closing(get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT id, nome, telefone, valor, data_vencimento, status, ultimo_envio
            FROM clientes
            WHERE status = 'pendente'
            """
        ).fetchall()
        return [dict(r) for r in rows]


def atualizar_ultimo_envio(cliente_id: int) -> None:
    agora = datetime.now().isoformat(timespec="seconds")
    with closing(get_connection()) as conn:
        conn.execute(
            "UPDATE clientes SET ultimo_envio = ? WHERE id = ?",
            (agora, cliente_id),
        )
        conn.commit()


def inserir_cliente(
    nome: str,
    telefone: str,
    valor: float,
    data_vencimento: str,
    status: str = "pendente",
) -> int:
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO clientes (nome, telefone, valor, data_vencimento, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (nome, telefone, valor, data_vencimento, status),
        )
        conn.commit()
        return int(cursor.lastrowid)
