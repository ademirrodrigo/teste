"""Ferramenta de monitoramento contínuo do eCAC para escritórios de contabilidade.

Este módulo fornece uma linha de comando para registrar clientes (empresas ou pessoas
físicas) e acompanhar notificações do eCAC por meio de uma API própria do escritório.
As requisições podem ser autenticadas com o certificado digital do contribuinte ou
apenas com a procuração eletrônica do contador, permitindo flexibilidade para cada
cadastro.

O código foi escrito para ser direto e pronto para uso em produção, sem mocks
ou simulações. Ajuste apenas as configurações de acesso (endereços da API,
caminhos dos certificados, tokens de procuração e URLs de alerta) antes de
colocá-lo em operação.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

try:
    import requests
except ImportError as exc:  # pragma: no cover - dependência obrigatória em produção
    raise SystemExit(
        "Dependência 'requests' não encontrada. Instale-a com 'pip install requests'."
    ) from exc

LOGGER = logging.getLogger("ecac_monitor")

AUTH_MODES = {"certificate", "procuracao"}


@dataclass
class MonitorConfig:
    """Representa a configuração principal do monitor."""

    api_base_url: str
    contador_document: str
    procuracao_token: str
    poll_interval: int = 900
    verify_ssl: bool = True
    timeout: int = 60
    webhook_url: Optional[str] = None

    @classmethod
    def load(cls, path: Path) -> "MonitorConfig":
        with path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        required = {"api_base_url", "contador_document", "procuracao_token"}
        missing = [field for field in required if field not in data]
        if missing:
            raise ValueError(
                f"Configuração inválida: campos obrigatórios ausentes {', '.join(missing)}"
            )
        return cls(
            api_base_url=data["api_base_url"].rstrip("/"),
            contador_document=data["contador_document"],
            procuracao_token=data["procuracao_token"],
            poll_interval=int(data.get("poll_interval", 900)),
            verify_ssl=bool(data.get("verify_ssl", True)),
            timeout=int(data.get("timeout", 60)),
            webhook_url=data.get("webhook_url"),
        )


@dataclass
class Client:
    document: str
    name: str
    client_type: str  # PJ ou PF
    auth_mode: str  # certificate ou procuracao
    certificate_path: Optional[Path]
    key_path: Optional[Path]
    certificate_password: Optional[str]
    procuracao_token: Optional[str]
    last_status: Optional[str]
    last_checked: Optional[datetime]


@dataclass
class EventRecord:
    id: int
    client_document: str
    payload: Dict[str, Any]
    received_at: datetime
    client_name: Optional[str] = None


@dataclass
class DashboardMetrics:
    """Representa indicadores consolidados para o painel web."""

    total_clients: int
    pj_clients: int
    pf_clients: int
    total_events: int
    clients_with_alerts: int
    last_check: Optional[datetime]
    last_event: Optional[datetime]


class DatabaseManager:
    """Responsável por persistir dados locais do monitor."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
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
                    auth_mode TEXT NOT NULL DEFAULT 'certificate'
                        CHECK (auth_mode IN ('certificate', 'procuracao')),
                    certificate_path TEXT,
                    key_path TEXT,
                    certificate_password TEXT,
                    procuracao_token TEXT,
                    last_status TEXT,
                    last_checked TEXT
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_document TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    FOREIGN KEY (client_document) REFERENCES clients(document)
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_events_document_hash
                    ON events(client_document, event_hash);
                """
            )
            self._migrate_clients_table(conn)

    def _migrate_clients_table(self, conn: sqlite3.Connection) -> None:
        info = conn.execute("PRAGMA table_info(clients)").fetchall()
        if not info:
            return

        columns = {row[1]: row for row in info}
        auth_present = "auth_mode" in columns
        certificate_nullable = not columns["certificate_path"][3]
        key_nullable = not columns["key_path"][3]

        if auth_present and certificate_nullable and key_nullable:
            return

        auth_select = "auth_mode" if auth_present else "'certificate'"
        conn.executescript(
            f"""
            CREATE TABLE clients_new (
                document TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                client_type TEXT NOT NULL CHECK (client_type IN ('PJ', 'PF')),
                auth_mode TEXT NOT NULL DEFAULT 'certificate'
                    CHECK (auth_mode IN ('certificate', 'procuracao')),
                certificate_path TEXT,
                key_path TEXT,
                certificate_password TEXT,
                procuracao_token TEXT,
                last_status TEXT,
                last_checked TEXT
            );

            INSERT INTO clients_new (
                document, name, client_type, auth_mode,
                certificate_path, key_path, certificate_password,
                procuracao_token, last_status, last_checked
            )
            SELECT
                document,
                name,
                client_type,
                COALESCE({auth_select}, 'certificate') AS auth_mode,
                certificate_path,
                key_path,
                certificate_password,
                procuracao_token,
                last_status,
                last_checked
            FROM clients;

            DROP TABLE clients;
            ALTER TABLE clients_new RENAME TO clients;

            CREATE UNIQUE INDEX IF NOT EXISTS idx_events_document_hash
                ON events(client_document, event_hash);
            """
        )

    # Métodos públicos -------------------------------------------------
    def add_client(
        self,
        document: str,
        name: str,
        client_type: str,
        auth_mode: str,
        certificate_path: Optional[Path],
        key_path: Optional[Path],
        certificate_password: Optional[str],
        procuracao_token: Optional[str],
    ) -> None:
        if auth_mode not in AUTH_MODES:
            raise ValueError(f"Modo de autenticação inválido: {auth_mode}")
        if auth_mode == "certificate" and (not certificate_path or not key_path):
            raise ValueError(
                "Certificado e chave são obrigatórios quando o modo é 'certificate'"
            )
        if auth_mode == "procuracao":
            certificate_path = None
            key_path = None
            certificate_password = None
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO clients (
                    document, name, client_type, auth_mode,
                    certificate_path, key_path,
                    certificate_password, procuracao_token
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document,
                    name,
                    client_type,
                    auth_mode,
                    str(certificate_path) if certificate_path else None,
                    str(key_path) if key_path else None,
                    certificate_password,
                    procuracao_token,
                ),
            )

    def list_clients(self) -> List[Client]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT document, name, client_type, auth_mode, certificate_path, key_path, "
                "certificate_password, procuracao_token, last_status, last_checked FROM clients"
            ).fetchall()
        clients: List[Client] = []
        for row in rows:
            last_checked = (
                datetime.fromisoformat(row["last_checked"]) if row["last_checked"] else None
            )
            clients.append(
                Client(
                    document=row["document"],
                    name=row["name"],
                    client_type=row["client_type"],
                    auth_mode=row["auth_mode"],
                    certificate_path=Path(row["certificate_path"])
                    if row["certificate_path"]
                    else None,
                    key_path=Path(row["key_path"]) if row["key_path"] else None,
                    certificate_password=row["certificate_password"],
                    procuracao_token=row["procuracao_token"],
                    last_status=row["last_status"],
                    last_checked=last_checked,
                )
            )
        return clients

    def get_client(self, document: str) -> Optional[Client]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT document, name, client_type, auth_mode, certificate_path, key_path, "
                "certificate_password, procuracao_token, last_status, last_checked "
                "FROM clients WHERE document = ?",
                (document,),
            ).fetchone()
        if row is None:
            return None
        last_checked = datetime.fromisoformat(row["last_checked"]) if row["last_checked"] else None
        return Client(
            document=row["document"],
            name=row["name"],
            client_type=row["client_type"],
            auth_mode=row["auth_mode"],
            certificate_path=Path(row["certificate_path"]) if row["certificate_path"] else None,
            key_path=Path(row["key_path"]) if row["key_path"] else None,
            certificate_password=row["certificate_password"],
            procuracao_token=row["procuracao_token"],
            last_status=row["last_status"],
            last_checked=last_checked,
        )

    def update_status(self, document: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE clients SET last_status = ?, last_checked = ? WHERE document = ?",
                (status, datetime.utcnow().isoformat(), document),
            )

    def register_events(self, document: str, events: Sequence[Dict]) -> List[Dict]:
        """Registra eventos inéditos e retorna apenas os novos."""

        if not events:
            return []

        created: List[Dict] = []
        with self._connect() as conn:
            for event in events:
                normalized = json.dumps(event, sort_keys=True, ensure_ascii=False)
                event_hash = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
                try:
                    conn.execute(
                        """
                        INSERT INTO events (client_document, event_hash, payload, received_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            document,
                            event_hash,
                            normalized,
                            datetime.utcnow().isoformat(),
                        ),
                    )
                except sqlite3.IntegrityError:
                    continue
                created.append(event)
        return created

    def list_events(
        self,
        document: Optional[str] = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> List[EventRecord]:
        query = (
            "SELECT e.id, e.client_document, e.payload, e.received_at, c.name as client_name "
            "FROM events e "
            "LEFT JOIN clients c ON c.document = e.client_document "
            + ("WHERE e.client_document = ? " if document else "")
            + "ORDER BY datetime(e.received_at) DESC, e.id DESC LIMIT ? OFFSET ?"
        )
        params: List[Any]
        if document:
            params = [document, limit, offset]
        else:
            params = [limit, offset]
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        events: List[EventRecord] = []
        for row in rows:
            try:
                payload = json.loads(row["payload"])
            except json.JSONDecodeError:
                payload = {"raw": row["payload"]}
            events.append(
                EventRecord(
                    id=row["id"],
                    client_document=row["client_document"],
                    payload=payload,
                    received_at=datetime.fromisoformat(row["received_at"]),
                    client_name=row["client_name"],
                )
            )
        return events

    def get_dashboard_metrics(self) -> DashboardMetrics:
        with self._connect() as conn:
            total_clients = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
            type_counts = {
                row["client_type"]: row["count"]
                for row in conn.execute(
                    "SELECT client_type, COUNT(*) as count FROM clients GROUP BY client_type"
                ).fetchall()
            }
            last_check_raw = conn.execute("SELECT MAX(last_checked) FROM clients").fetchone()[0]
            total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            clients_with_alerts = conn.execute(
                "SELECT COUNT(DISTINCT client_document) FROM events"
            ).fetchone()[0]
            last_event_raw = conn.execute("SELECT MAX(received_at) FROM events").fetchone()[0]

        last_check = (
            datetime.fromisoformat(last_check_raw) if last_check_raw else None
        )
        last_event = (
            datetime.fromisoformat(last_event_raw) if last_event_raw else None
        )
        return DashboardMetrics(
            total_clients=total_clients,
            pj_clients=type_counts.get("PJ", 0),
            pf_clients=type_counts.get("PF", 0),
            total_events=total_events,
            clients_with_alerts=clients_with_alerts,
            last_check=last_check,
            last_event=last_event,
        )

    def delete_client(self, document: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM events WHERE client_document = ?", (document,))
            deleted = conn.execute("DELETE FROM clients WHERE document = ?", (document,)).rowcount
        if not deleted:
            raise ValueError(f"Cliente {document} não encontrado")

    def update_client(self, document: str, **fields: Any) -> None:
        current = self.get_client(document)
        if not current:
            raise ValueError(f"Cliente {document} não encontrado")

        new_auth_mode = fields.get("auth_mode", current.auth_mode)
        if new_auth_mode not in AUTH_MODES:
            raise ValueError(f"Modo de autenticação inválido: {new_auth_mode}")

        new_certificate = fields.get("certificate_path", current.certificate_path)
        new_key = fields.get("key_path", current.key_path)

        if new_auth_mode == "certificate" and (not new_certificate or not new_key):
            raise ValueError(
                "Certificado e chave são obrigatórios quando o modo é 'certificate'"
            )
        if new_auth_mode == "procuracao":
            fields.setdefault("certificate_path", None)
            fields.setdefault("key_path", None)
            fields.setdefault("certificate_password", None)

        allowed = {
            "name": "name",
            "client_type": "client_type",
            "auth_mode": "auth_mode",
            "certificate_path": "certificate_path",
            "key_path": "key_path",
            "certificate_password": "certificate_password",
            "procuracao_token": "procuracao_token",
        }
        assignments: List[str] = []
        values: List[Any] = []
        for key, column in allowed.items():
            if key not in fields:
                continue
            assignments.append(f"{column} = ?")
            value = fields[key]
            if isinstance(value, Path):
                value = str(value)
            values.append(value)
        if not assignments:
            return
        values.append(document)
        with self._connect() as conn:
            updated = conn.execute(
                f"UPDATE clients SET {', '.join(assignments)} WHERE document = ?",
                values,
            ).rowcount
        if not updated:
            raise ValueError(f"Cliente {document} não encontrado")


class EcacAPIClient:
    """Cliente HTTP que interage com a API proprietária."""

    def __init__(self, config: MonitorConfig) -> None:
        self.config = config

    def _prepare_session(
        self, client: Client, verify_ssl: bool
    ) -> requests.Session:
        session = requests.Session()
        session.verify = verify_ssl
        if client.auth_mode == "certificate" and client.certificate_path and client.key_path:
            session.cert = (str(client.certificate_path), str(client.key_path))
            if client.certificate_password:
                session.headers["X-Certificate-Pin"] = client.certificate_password
        session.headers.update({
            "User-Agent": "ecac-monitor/1.0",
            "X-Contador-Documento": self.config.contador_document,
            "X-Procuracao-Token": client.procuracao_token or self.config.procuracao_token,
        })
        return session

    def authenticate(self, session: requests.Session, client: Client) -> str:
        if client.auth_mode == "procuracao":
            endpoint = f"{self.config.api_base_url}/auth/procuracao"
            payload = {
                "document": client.document,
                "client_type": client.client_type,
                "contador_document": self.config.contador_document,
            }
            if client.procuracao_token:
                payload["procuracao_token"] = client.procuracao_token
        else:
            endpoint = f"{self.config.api_base_url}/auth/certificate"
            payload = {
                "document": client.document,
                "client_type": client.client_type,
            }
        response = session.post(
            endpoint,
            timeout=self.config.timeout,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError("Resposta da API sem access_token")
        return token

    def fetch_notifications(
        self, session: requests.Session, token: str, document: str
    ) -> List[Dict]:
        response = session.get(
            f"{self.config.api_base_url}/ecac/{document}/notifications",
            timeout=self.config.timeout,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        payload = response.json()
        notifications = payload.get("notifications")
        if notifications is None:
            raise RuntimeError("Resposta inesperada da API: campo 'notifications' ausente")
        if not isinstance(notifications, list):
            raise RuntimeError("Campo 'notifications' deve ser uma lista")
        return notifications

    def fetch_obligations(
        self, session: requests.Session, token: str, document: str
    ) -> List[Dict]:
        response = session.get(
            f"{self.config.api_base_url}/ecac/{document}/obligations",
            timeout=self.config.timeout,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        payload = response.json()
        obligations = payload.get("obligations", [])
        if not isinstance(obligations, list):
            raise RuntimeError("Campo 'obligations' deve ser uma lista")
        return obligations


class AlertDispatcher:
    def __init__(self, webhook_url: Optional[str], verify_ssl: bool, timeout: int) -> None:
        self.webhook_url = webhook_url
        self.verify_ssl = verify_ssl
        self.timeout = timeout

    def dispatch(self, payload: Dict) -> None:
        if not self.webhook_url:
            return
        response = requests.post(
            self.webhook_url,
            json=payload,
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError:
            LOGGER.exception("Falha ao enviar alerta para %s", self.webhook_url)
            raise


class EcacMonitor:
    def __init__(
        self,
        db: DatabaseManager,
        api_client: EcacAPIClient,
        dispatcher: AlertDispatcher,
        poll_interval: int,
        verify_ssl: bool,
    ) -> None:
        self.db = db
        self.api_client = api_client
        self.dispatcher = dispatcher
        self.poll_interval = poll_interval
        self.verify_ssl = verify_ssl

    def run_forever(self) -> None:
        LOGGER.info("Monitoramento iniciado")
        while True:
            start = time.monotonic()
            self.run_cycle()
            elapsed = time.monotonic() - start
            sleep_time = max(self.poll_interval - elapsed, 5)
            LOGGER.debug("Aguardando %.1f segundos até o próximo ciclo", sleep_time)
            time.sleep(sleep_time)

    def run_cycle(self) -> None:
        for client in self.db.list_clients():
            self._process_client(client)

    def run_for_client(self, document: str) -> None:
        client = self.db.get_client(document)
        if not client:
            raise ValueError(f"Cliente {document} não encontrado")
        self._process_client(client)

    def _process_client(self, client: Client) -> None:
        LOGGER.info("Verificando %s (%s)", client.name, client.document)
        session = self.api_client._prepare_session(client, self.verify_ssl)
        try:
            token = self.api_client.authenticate(session, client)
            notifications = self.api_client.fetch_notifications(session, token, client.document)
            obligations = self.api_client.fetch_obligations(session, token, client.document)
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Falha ao comunicar com a API do eCAC: %s", exc)
            return

        new_events = self.db.register_events(client.document, notifications)
        status_payload = {
            "notifications": notifications,
            "obligations": obligations,
            "updated_at": datetime.utcnow().isoformat(),
        }
        self.db.update_status(client.document, json.dumps(status_payload, ensure_ascii=False))

        if new_events:
            LOGGER.info("%s novos eventos encontrados para %s", len(new_events), client.document)
            self._emit_alert(client, new_events, obligations)
        else:
            LOGGER.info("Nenhum evento novo para %s", client.document)

    def _emit_alert(
        self,
        client: Client,
        new_events: Iterable[Dict],
        obligations: Sequence[Dict],
    ) -> None:
        payload = {
            "client": {
                "document": client.document,
                "name": client.name,
                "type": client.client_type,
            },
            "new_notifications": list(new_events),
            "open_obligations": obligations,
            "generated_at": datetime.utcnow().isoformat(),
        }
        try:
            self.dispatcher.dispatch(payload)
        except Exception:  # noqa: BLE001
            LOGGER.exception("Erro ao enviar alerta do cliente %s", client.document)


# ---------------------------------------------------------------------------
# Linha de comando
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Monitoramento contínuo do eCAC")
    parser.add_argument(
        "--database",
        default="monitor.db",
        help="Caminho do arquivo SQLite (padrão: monitor.db)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_client_cmd = subparsers.add_parser("add-client", help="Cadastra um novo cliente")
    add_client_cmd.add_argument("document", help="CPF ou CNPJ do contribuinte")
    add_client_cmd.add_argument("name", help="Nome ou razão social")
    add_client_cmd.add_argument("client_type", choices=["PJ", "PF"], help="Tipo do cliente")
    add_client_cmd.add_argument(
        "certificate",
        nargs="?",
        default=None,
        help="Arquivo PEM do certificado da empresa (obrigatório para auth_mode=certificate)",
    )
    add_client_cmd.add_argument(
        "key",
        nargs="?",
        default=None,
        help="Arquivo PEM da chave privada correspondente",
    )
    add_client_cmd.add_argument(
        "--auth-mode",
        choices=sorted(AUTH_MODES),
        default="certificate",
        help="Define se o acesso usa certificado ou procuração (padrão: certificate)",
    )
    add_client_cmd.add_argument(
        "--certificate-password",
        dest="certificate_password",
        help="Senha do certificado (se aplicável)",
    )
    add_client_cmd.add_argument(
        "--procuracao-token",
        dest="procuracao_token",
        help="Token de procuração específico do cliente (opcional)",
    )

    subparsers.add_parser("list-clients", help="Lista clientes cadastrados")

    update_client_cmd = subparsers.add_parser(
        "update-client", help="Atualiza informações de um cliente"
    )
    update_client_cmd.add_argument("document", help="CPF ou CNPJ do contribuinte")
    update_client_cmd.add_argument("--name", help="Novo nome ou razão social")
    update_client_cmd.add_argument(
        "--client-type",
        choices=["PJ", "PF"],
        dest="client_type",
        help="Atualiza o tipo do cliente",
    )
    update_client_cmd.add_argument(
        "--auth-mode",
        choices=sorted(AUTH_MODES),
        dest="auth_mode",
        help="Altera o modo de autenticação do cliente",
    )
    update_client_cmd.add_argument("--certificate", help="Novo caminho do certificado")
    update_client_cmd.add_argument("--key", help="Novo caminho da chave privada")
    update_client_cmd.add_argument(
        "--certificate-password",
        dest="certificate_password",
        help="Atualiza a senha do certificado",
    )
    update_client_cmd.add_argument(
        "--procuracao-token",
        dest="procuracao_token",
        help="Atualiza o token de procuração",
    )
    update_client_cmd.add_argument(
        "--clear-certificate-password",
        action="store_true",
        help="Remove a senha do certificado armazenada",
    )
    update_client_cmd.add_argument(
        "--clear-procuracao-token",
        action="store_true",
        help="Remove o token de procuração armazenado",
    )

    delete_client_cmd = subparsers.add_parser(
        "delete-client", help="Remove um cliente e seu histórico"
    )
    delete_client_cmd.add_argument("document", help="CPF ou CNPJ do contribuinte")

    events_cmd = subparsers.add_parser(
        "list-events", help="Lista eventos registrados no banco"
    )
    events_cmd.add_argument(
        "--document",
        help="Filtra eventos por documento do cliente",
    )
    events_cmd.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Quantidade máxima de eventos (padrão: 50)",
    )
    events_cmd.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Deslocamento para paginação (padrão: 0)",
    )

    status_cmd = subparsers.add_parser(
        "show-status", help="Mostra o último status consolidado de um cliente"
    )
    status_cmd.add_argument("document", help="CPF ou CNPJ do contribuinte")

    run_cmd = subparsers.add_parser("run", help="Executa o monitoramento contínuo")
    run_cmd.add_argument(
        "--config",
        required=True,
        help="Arquivo JSON com configuração do monitor",
    )
    run_cmd.add_argument(
        "--once",
        action="store_true",
        help="Executa apenas um ciclo de consulta (útil para integrações)",
    )
    run_cmd.add_argument(
        "--client",
        help="Documento de um cliente específico para executar o ciclo",
    )

    return parser


def handle_add_client(args: argparse.Namespace, db: DatabaseManager) -> None:
    certificate_path = Path(args.certificate).expanduser() if args.certificate else None
    key_path = Path(args.key).expanduser() if args.key else None
    db.add_client(
        document=args.document,
        name=args.name,
        client_type=args.client_type,
        auth_mode=args.auth_mode,
        certificate_path=certificate_path,
        key_path=key_path,
        certificate_password=args.certificate_password,
        procuracao_token=args.procuracao_token,
    )
    LOGGER.info("Cliente %s cadastrado com sucesso", args.document)


def handle_list_clients(db: DatabaseManager) -> None:
    clients = db.list_clients()
    if not clients:
        print("Nenhum cliente cadastrado.")
        return
    for client in clients:
        last_checked = client.last_checked.isoformat() if client.last_checked else "nunca"
        print(
            f"{client.document} | {client.name} | {client.client_type} | "
            f"última verificação: {last_checked}"
        )


def handle_update_client(args: argparse.Namespace, db: DatabaseManager) -> None:
    fields: Dict[str, Any] = {}
    if args.name:
        fields["name"] = args.name
    if args.client_type:
        fields["client_type"] = args.client_type
    if args.auth_mode:
        fields["auth_mode"] = args.auth_mode
    if args.certificate:
        fields["certificate_path"] = Path(args.certificate).expanduser()
    if args.key:
        fields["key_path"] = Path(args.key).expanduser()
    if args.certificate_password is not None:
        fields["certificate_password"] = args.certificate_password
    if args.procuracao_token is not None:
        fields["procuracao_token"] = args.procuracao_token
    if args.clear_certificate_password:
        fields["certificate_password"] = None
    if args.clear_procuracao_token:
        fields["procuracao_token"] = None
    if not fields:
        LOGGER.info("Nenhum campo informado para atualização")
        return
    db.update_client(args.document, **fields)
    LOGGER.info("Cliente %s atualizado com sucesso", args.document)


def handle_delete_client(args: argparse.Namespace, db: DatabaseManager) -> None:
    db.delete_client(args.document)
    LOGGER.info("Cliente %s removido", args.document)


def handle_list_events(args: argparse.Namespace, db: DatabaseManager) -> None:
    events = db.list_events(args.document, limit=args.limit, offset=args.offset)
    if not events:
        print("Nenhum evento encontrado.")
        return
    for event in events:
        print(
            f"[{event.received_at.isoformat()}] {event.client_document} - "
            f"payload: {json.dumps(event.payload, ensure_ascii=False)}"
        )


def handle_show_status(args: argparse.Namespace, db: DatabaseManager) -> None:
    client = db.get_client(args.document)
    if not client:
        print(f"Cliente {args.document} não encontrado.")
        return
    if not client.last_status:
        print("Nenhum status registrado. Execute um ciclo de monitoramento.")
        return
    try:
        status = json.loads(client.last_status)
    except json.JSONDecodeError:
        print(client.last_status)
        return
    print(json.dumps(status, indent=2, ensure_ascii=False))


def handle_run(args: argparse.Namespace, db: DatabaseManager) -> None:
    config = MonitorConfig.load(Path(args.config))
    api_client = EcacAPIClient(config)
    dispatcher = AlertDispatcher(config.webhook_url, config.verify_ssl, config.timeout)
    monitor = EcacMonitor(db, api_client, dispatcher, config.poll_interval, config.verify_ssl)
    if args.client:
        monitor.run_for_client(args.client)
        return
    if args.once:
        monitor.run_cycle()
    else:
        monitor.run_forever()


def main(argv: Optional[Sequence[str]] = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    parser = build_parser()
    args = parser.parse_args(argv)
    db = DatabaseManager(Path(args.database))

    if args.command == "add-client":
        handle_add_client(args, db)
        return 0
    if args.command == "list-clients":
        handle_list_clients(db)
        return 0
    if args.command == "update-client":
        handle_update_client(args, db)
        return 0
    if args.command == "delete-client":
        handle_delete_client(args, db)
        return 0
    if args.command == "list-events":
        handle_list_events(args, db)
        return 0
    if args.command == "show-status":
        handle_show_status(args, db)
        return 0
    if args.command == "run":
        handle_run(args, db)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
