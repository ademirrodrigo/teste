"""Aplicação web para operar o monitoramento do eCAC."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from flask import (
    Flask,
    Response,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from main import (
    AlertDispatcher,
    Client,
    DashboardMetrics,
    DatabaseManager,
    EcacAPIClient,
    EcacMonitor,
    MonitorConfig,
)


def _load_config() -> MonitorConfig:
    config_path = Path(os.environ.get("MONITOR_CONFIG", "monitor_config.json"))
    if not config_path.exists():
        raise FileNotFoundError(
            "Arquivo de configuração do monitor não encontrado. "
            "Defina MONITOR_CONFIG com o caminho correto."
        )
    return MonitorConfig.load(config_path)


def _load_database() -> DatabaseManager:
    db_path = Path(os.environ.get("MONITOR_DATABASE", "monitor.db"))
    return DatabaseManager(db_path)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "change-me")

    db = _load_database()

    def _build_monitor() -> EcacMonitor:
        config = _load_config()
        api_client = EcacAPIClient(config)
        dispatcher = AlertDispatcher(config.webhook_url, config.verify_ssl, config.timeout)
        return EcacMonitor(db, api_client, dispatcher, config.poll_interval, config.verify_ssl)

    @app.context_processor
    def inject_globals() -> Dict[str, Any]:
        config_env = os.environ.get("MONITOR_CONFIG")
        available = bool(config_env and Path(config_env).exists())
        return {"config_available": available}

    def _prepare_status(client: Client) -> Optional[Dict[str, Any]]:
        if not client.last_status:
            return None
        try:
            return json.loads(client.last_status)
        except json.JSONDecodeError:
            return {"raw": client.last_status}

    def _format_event(event) -> Dict[str, Any]:
        payload = event.payload
        summary = None
        description = None
        category = None
        reference = None
        if isinstance(payload, dict):
            for key in ("title", "titulo", "subject", "assunto"):
                if payload.get(key):
                    summary = str(payload[key])
                    break
            description = (
                payload.get("description")
                or payload.get("mensagem")
                or payload.get("message")
            )
            category = payload.get("category") or payload.get("categoria")
            reference = (
                payload.get("reference")
                or payload.get("protocolo")
                or payload.get("id")
            )
        if summary is None:
            if isinstance(payload, (str, int, float)):
                summary = str(payload)
            else:
                summary = json.dumps(payload, ensure_ascii=False)
        return {
            "id": event.id,
            "client_document": event.client_document,
            "client_name": getattr(event, "client_name", None),
            "received_at": event.received_at,
            "summary": summary,
            "description": description,
            "category": category,
            "reference": reference,
            "payload": payload,
        }

    @app.get("/")
    def index() -> str:
        clients = db.list_clients()
        metrics: DashboardMetrics = db.get_dashboard_metrics()
        enriched = []
        for client in clients:
            status = _prepare_status(client)
            notifications = 0
            obligations = 0
            if isinstance(status, dict):
                notifications_field = status.get("notifications") or status.get("avisos")
                if isinstance(notifications_field, list):
                    notifications = len(notifications_field)
                obligations_field = (
                    status.get("obligations")
                    or status.get("obrigacoes")
                    or status.get("obrigações")
                )
                if isinstance(obligations_field, list):
                    obligations = len(obligations_field)
            enriched.append(
                {
                    "client": client,
                    "status": status,
                    "notifications": notifications,
                    "obligations": obligations,
                }
            )

        stale_threshold = datetime.utcnow() - timedelta(hours=24)
        stale_clients = [
            entry
            for entry in enriched
            if not entry["client"].last_checked
            or entry["client"].last_checked < stale_threshold
        ]
        recent_events = [_format_event(event) for event in db.list_events(limit=6)]

        return render_template(
            "index.html",
            clients=enriched,
            metrics=metrics,
            stale_clients=stale_clients,
            recent_events=recent_events,
        )

    @app.get("/clients/new")
    def new_client() -> str:
        return render_template("add_client.html")

    @app.post("/clients")
    def create_client() -> Response:
        form = request.form
        required = ["document", "name", "client_type", "certificate", "key"]
        missing = [field for field in required if not form.get(field)]
        if missing:
            flash(f"Campos obrigatórios ausentes: {', '.join(missing)}", "error")
            return redirect(url_for("new_client"))

        try:
            db.add_client(
                document=form["document"].strip(),
                name=form["name"].strip(),
                client_type=form["client_type"],
                certificate_path=Path(form["certificate"]).expanduser(),
                key_path=Path(form["key"]).expanduser(),
                certificate_password=form.get("certificate_password") or None,
                procuracao_token=form.get("procuracao_token") or None,
            )
        except Exception as exc:  # noqa: BLE001
            flash(f"Erro ao cadastrar cliente: {exc}", "error")
            return redirect(url_for("new_client"))

        flash("Cliente cadastrado com sucesso", "success")
        return redirect(url_for("index"))

    @app.get("/clients/<document>")
    def client_detail(document: str) -> str:
        client = db.get_client(document)
        if not client:
            flash("Cliente não encontrado", "error")
            return redirect(url_for("index"))
        status = _prepare_status(client)
        notifications = []
        obligations = []
        metadata: Dict[str, Any] = {}
        if isinstance(status, dict):
            raw_notifications = status.get("notifications") or status.get("avisos")
            if isinstance(raw_notifications, list):
                notifications = raw_notifications
            raw_obligations = (
                status.get("obligations")
                or status.get("obrigacoes")
                or status.get("obrigações")
            )
            if isinstance(raw_obligations, list):
                obligations = raw_obligations
            meta_candidate = status.get("metadata") or status.get("metadados")
            if isinstance(meta_candidate, dict):
                metadata = meta_candidate
        recent_events = [
            _format_event(event) for event in db.list_events(document, limit=5)
        ]
        return render_template(
            "client_detail.html",
            client=client,
            status=status,
            notifications=notifications,
            obligations=obligations,
            metadata=metadata,
            recent_events=recent_events,
        )

    @app.post("/run-cycle")
    def run_cycle() -> Response:
        try:
            monitor = _build_monitor()
            monitor.run_cycle()
        except FileNotFoundError as exc:
            flash(str(exc), "error")
            return redirect(url_for("index"))
        except Exception as exc:  # noqa: BLE001
            flash(f"Erro ao executar ciclo: {exc}", "error")
            return redirect(url_for("index"))

        flash("Ciclo executado com sucesso", "success")
        return redirect(url_for("index"))

    @app.post("/clients/<document>/run")
    def run_cycle_for_client(document: str) -> Response:
        try:
            monitor = _build_monitor()
            monitor.run_for_client(document)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("index"))
        except FileNotFoundError as exc:
            flash(str(exc), "error")
            return redirect(url_for("client_detail", document=document))
        except Exception as exc:  # noqa: BLE001
            flash(f"Erro ao executar ciclo: {exc}", "error")
            return redirect(url_for("client_detail", document=document))
        flash("Ciclo executado com sucesso", "success")
        return redirect(url_for("client_detail", document=document))

    @app.get("/clients/<document>/events")
    def client_events(document: str) -> str:
        client = db.get_client(document)
        if not client:
            flash("Cliente não encontrado", "error")
            return redirect(url_for("index"))
        try:
            limit = max(1, min(500, int(request.args.get("limit", 50))))
            offset = max(0, int(request.args.get("offset", 0)))
        except ValueError:
            flash("Parâmetros de paginação inválidos", "error")
            return redirect(url_for("client_events", document=document))
        events = db.list_events(document, limit=limit, offset=offset)
        formatted_events = [_format_event(event) for event in events]
        return render_template(
            "client_events.html",
            client=client,
            events=formatted_events,
            limit=limit,
            offset=offset,
            next_offset=offset + limit if len(events) == limit else None,
            prev_offset=offset - limit if offset - limit >= 0 else None,
        )

    @app.get("/clients/<document>/edit")
    def edit_client(document: str) -> str:
        client = db.get_client(document)
        if not client:
            flash("Cliente não encontrado", "error")
            return redirect(url_for("index"))
        return render_template("edit_client.html", client=client)

    @app.post("/clients/<document>")
    def update_client(document: str) -> Response:
        client = db.get_client(document)
        if not client:
            flash("Cliente não encontrado", "error")
            return redirect(url_for("index"))
        form = request.form
        fields: Dict[str, Any] = {}
        if form.get("name"):
            fields["name"] = form["name"].strip()
        if form.get("client_type"):
            fields["client_type"] = form["client_type"]
        if form.get("certificate"):
            fields["certificate_path"] = Path(form["certificate"]).expanduser()
        if form.get("key"):
            fields["key_path"] = Path(form["key"]).expanduser()
        if form.get("certificate_password") is not None:
            fields["certificate_password"] = form.get("certificate_password") or None
        if form.get("procuracao_token") is not None:
            fields["procuracao_token"] = form.get("procuracao_token") or None
        if not fields:
            flash("Nenhuma alteração informada", "warning")
            return redirect(url_for("edit_client", document=document))
        try:
            db.update_client(document, **fields)
        except Exception as exc:  # noqa: BLE001
            flash(f"Erro ao atualizar cliente: {exc}", "error")
            return redirect(url_for("edit_client", document=document))
        flash("Cliente atualizado com sucesso", "success")
        return redirect(url_for("client_detail", document=document))

    @app.post("/clients/<document>/delete")
    def delete_client(document: str) -> Response:
        try:
            db.delete_client(document)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("index"))
        flash("Cliente removido", "success")
        return redirect(url_for("index"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=False)
