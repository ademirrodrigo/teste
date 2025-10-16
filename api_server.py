"""API proprietária para integrar o monitoramento do eCAC."""
from __future__ import annotations

import json
import os
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Flask, abort, jsonify, request

ISO_FORMAT = "%Y-%m-%dT%H:%M:%S"


@dataclass
class APIConfig:
    """Configurações principais da API."""

    contador_document: str
    default_procuracao_token: str
    access_token_ttl: int = 60  # minutos
    admin_token: Optional[str] = None

    @classmethod
    def load(cls, path: Path) -> "APIConfig":
        with path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        missing = [field for field in ("contador_document", "default_procuracao_token") if field not in data]
        if missing:
            raise ValueError(
                "Configuração inválida da API, campos obrigatórios ausentes: " + ", ".join(missing)
            )
        return cls(
            contador_document=data["contador_document"],
            default_procuracao_token=data["default_procuracao_token"],
            access_token_ttl=int(data.get("access_token_ttl", 60)),
            admin_token=data.get("admin_token"),
        )


class APIDatabase:
    """Gerencia o armazenamento de clientes, notificações e tokens."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS clients (
                    document TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    client_type TEXT NOT NULL CHECK (client_type IN ('PJ', 'PF')),
                    procuracao_token TEXT,
                    certificate_identifier TEXT
                );

                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_document TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (client_document) REFERENCES clients(document) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS obligations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_document TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT,
                    due_date TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (client_document) REFERENCES clients(document) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS access_tokens (
                    token TEXT PRIMARY KEY,
                    client_document TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (client_document) REFERENCES clients(document) ON DELETE CASCADE
                );
                """
            )

    # ------------------------------------------------------------------
    # Clientes
    # ------------------------------------------------------------------
    def upsert_client(
        self,
        document: str,
        name: str,
        client_type: str,
        procuracao_token: Optional[str] = None,
        certificate_identifier: Optional[str] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO clients (document, name, client_type, procuracao_token, certificate_identifier)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(document) DO UPDATE SET
                    name=excluded.name,
                    client_type=excluded.client_type,
                    procuracao_token=excluded.procuracao_token,
                    certificate_identifier=excluded.certificate_identifier
                """,
                (document, name, client_type, procuracao_token, certificate_identifier),
            )

    def get_client(self, document: str) -> Optional[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute("SELECT * FROM clients WHERE document = ?", (document,)).fetchone()

    # ------------------------------------------------------------------
    # Tokens de acesso
    # ------------------------------------------------------------------
    def create_access_token(self, document: str, ttl_minutes: int) -> str:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO access_tokens (token, client_document, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    token,
                    document,
                    expires_at.strftime(ISO_FORMAT),
                    datetime.utcnow().strftime(ISO_FORMAT),
                ),
            )
        return token

    def validate_token(self, token: str) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT client_document, expires_at FROM access_tokens WHERE token = ?",
                (token,),
            ).fetchone()
        if not row:
            return None
        expires_at = datetime.strptime(row["expires_at"], ISO_FORMAT)
        if expires_at < datetime.utcnow():
            self.delete_token(token)
            return None
        return row["client_document"]

    def delete_token(self, token: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM access_tokens WHERE token = ?", (token,))

    # ------------------------------------------------------------------
    # Notificações e obrigações
    # ------------------------------------------------------------------
    def list_notifications(self, document: str) -> list[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload, created_at FROM notifications WHERE client_document = ? ORDER BY id DESC",
                (document,),
            ).fetchall()
        notifications = []
        for row in rows:
            payload = json.loads(row["payload"])
            payload.setdefault("created_at", row["created_at"])
            notifications.append(payload)
        return notifications

    def append_notification(self, document: str, payload: Dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO notifications (client_document, payload, created_at)
                VALUES (?, ?, ?)
                """,
                (document, json.dumps(payload, ensure_ascii=False), datetime.utcnow().strftime(ISO_FORMAT)),
            )

    def list_obligations(self, document: str) -> list[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload, status, due_date, created_at
                FROM obligations
                WHERE client_document = ?
                ORDER BY id DESC
                """,
                (document,),
            ).fetchall()
        obligations: list[Dict[str, Any]] = []
        for row in rows:
            payload = json.loads(row["payload"])
            if row["status"]:
                payload.setdefault("status", row["status"])
            if row["due_date"]:
                payload.setdefault("due_date", row["due_date"])
            payload.setdefault("updated_at", row["created_at"])
            obligations.append(payload)
        return obligations

    def replace_obligations(self, document: str, obligations: list[Dict[str, Any]]) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM obligations WHERE client_document = ?", (document,))
            now = datetime.utcnow().strftime(ISO_FORMAT)
            for item in obligations:
                conn.execute(
                    """
                    INSERT INTO obligations (client_document, payload, status, due_date, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        document,
                        json.dumps(item, ensure_ascii=False),
                        item.get("status"),
                        item.get("due_date"),
                        now,
                    ),
                )


def create_app(config: APIConfig, database: APIDatabase) -> Flask:
    app = Flask(__name__)

    def require_admin() -> None:
        if not config.admin_token:
            return
        provided = request.headers.get("X-Admin-Token")
        if provided != config.admin_token:
            abort(401, "Admin token inválido")

    def require_access_token() -> str:
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            abort(401, "Token ausente")
        token = header.split(" ", 1)[1]
        document = database.validate_token(token)
        if not document:
            abort(401, "Token inválido ou expirado")
        return document

    @app.post("/auth/procuracao")
    def auth_procuracao() -> Any:
        payload = request.get_json(force=True)
        for field in ("document", "client_type", "contador_document"):
            if field not in payload:
                abort(400, f"Campo obrigatório ausente: {field}")
        if payload["contador_document"] != config.contador_document:
            abort(401, "Contador não autorizado")
        client = database.get_client(payload["document"])
        if not client:
            abort(404, "Cliente não cadastrado")
        if client["client_type"] != payload["client_type"]:
            abort(400, "Tipo de cliente divergente")
        provided_token = payload.get("procuracao_token") or config.default_procuracao_token
        valid_token = client["procuracao_token"] or config.default_procuracao_token
        if provided_token != valid_token:
            abort(401, "Token de procuração inválido")
        token = database.create_access_token(client["document"], config.access_token_ttl)
        return jsonify({"access_token": token, "expires_in": config.access_token_ttl * 60})

    @app.post("/auth/certificate")
    def auth_certificate() -> Any:
        payload = request.get_json(force=True)
        for field in ("document", "client_type"):
            if field not in payload:
                abort(400, f"Campo obrigatório ausente: {field}")
        client = database.get_client(payload["document"])
        if not client:
            abort(404, "Cliente não cadastrado")
        if client["client_type"] != payload["client_type"]:
            abort(400, "Tipo de cliente divergente")
        identifier = payload.get("certificate_identifier")
        stored_identifier = client["certificate_identifier"]
        if stored_identifier and identifier != stored_identifier:
            abort(401, "Certificado não autorizado")
        token = database.create_access_token(client["document"], config.access_token_ttl)
        return jsonify({"access_token": token, "expires_in": config.access_token_ttl * 60})

    @app.get("/ecac/<document>/notifications")
    def get_notifications(document: str) -> Any:
        token_document = require_access_token()
        if token_document != document:
            abort(403, "Token não corresponde ao cliente consultado")
        data = database.list_notifications(document)
        return jsonify({"notifications": data})

    @app.get("/ecac/<document>/obligations")
    def get_obligations(document: str) -> Any:
        token_document = require_access_token()
        if token_document != document:
            abort(403, "Token não corresponde ao cliente consultado")
        data = database.list_obligations(document)
        return jsonify({"obligations": data})

    # ------------------------------------------------------------------
    # Endpoints administrativos para alimentar a API
    # ------------------------------------------------------------------
    @app.post("/admin/clients")
    def create_or_update_client() -> Any:
        require_admin()
        payload = request.get_json(force=True)
        for field in ("document", "name", "client_type"):
            if field not in payload:
                abort(400, f"Campo obrigatório ausente: {field}")
        database.upsert_client(
            document=payload["document"],
            name=payload["name"],
            client_type=payload["client_type"],
            procuracao_token=payload.get("procuracao_token"),
            certificate_identifier=payload.get("certificate_identifier"),
        )
        return jsonify({"status": "ok"})

    @app.post("/admin/clients/<document>/notifications")
    def append_client_notification(document: str) -> Any:
        require_admin()
        payload = request.get_json(force=True)
        if "notification" in payload:
            entry = payload["notification"]
        else:
            entry = payload
        if not isinstance(entry, dict):
            abort(400, "Notification inválida")
        if not database.get_client(document):
            abort(404, "Cliente não encontrado")
        database.append_notification(document, entry)
        return jsonify({"status": "ok"})

    @app.post("/admin/clients/<document>/obligations")
    def replace_client_obligations(document: str) -> Any:
        require_admin()
        payload = request.get_json(force=True)
        obligations = payload.get("obligations")
        if not isinstance(obligations, list):
            abort(400, "Campo 'obligations' deve ser uma lista")
        if not database.get_client(document):
            abort(404, "Cliente não encontrado")
        database.replace_obligations(document, obligations)
        return jsonify({"status": "ok"})

    return app


def load_app() -> Flask:
    config_path = Path(os.environ.get("API_CONFIG", "api_config.json"))
    if not config_path.exists():
        raise FileNotFoundError(
            "Arquivo de configuração da API não encontrado. Defina API_CONFIG ou crie api_config.json."
        )
    config = APIConfig.load(config_path)
    db_path = Path(os.environ.get("API_DATABASE", "api_data.db"))
    database = APIDatabase(db_path)
    return create_app(config, database)
app = load_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("API_PORT", 5000)), debug=False)
