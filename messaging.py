"""Envio de mensagens via API REST (UltraMsg/Z-API-like ou wwebjs bridge)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import requests
from requests import RequestException


@dataclass
class WhatsAppConfig:
    api_url: str
    token: str
    instance_id: str | None = None
    provider: str = "rest"


def montar_mensagem(tipo: str, nome: str, valor: float) -> str:
    templates: Dict[str, str] = {
        "lembrete": "Olá, {nome}. Passando para lembrar que seu boleto de R$ {valor:.2f} vence amanhã.",
        "no_dia": "Olá, {nome}. Sua cobrança de R$ {valor:.2f} vence hoje. Evite atrasos.",
        "atrasado": "Olá, {nome}. Identificamos atraso na cobrança de R$ {valor:.2f}. Favor regularizar o quanto antes.",
    }
    template = templates.get(tipo)
    if not template:
        raise ValueError(f"Tipo de mensagem inválido: {tipo}")
    return template.format(nome=nome, valor=valor)


def enviar_mensagem(config: WhatsAppConfig, telefone: str, mensagem: str) -> bool:
    """
    Estrutura genérica de envio (ajuste payload conforme API escolhida).

    Exemplo de endpoint (UltraMsg):
    POST {api_url}/instances/{instance_id}/messages/chat
    """
    if config.provider == "wwebjs":
        return enviar_mensagem_wwebjs(config, telefone, mensagem)
    return enviar_mensagem_rest(config, telefone, mensagem)


def enviar_mensagem_rest(config: WhatsAppConfig, telefone: str, mensagem: str) -> bool:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.token}",
    }
    payload = {"to": telefone, "body": mensagem}

    url = config.api_url
    if config.instance_id:
        url = f"{config.api_url.rstrip('/')}/instances/{config.instance_id}/messages/chat"

    return _post_json(url, payload, headers, telefone)


def enviar_mensagem_wwebjs(config: WhatsAppConfig, telefone: str, mensagem: str) -> bool:
    """
    Espera um bridge local Node.js com whatsapp-web.js.
    Endpoint padrão: POST http://localhost:3000/send-message
    """
    headers = {"Content-Type": "application/json"}
    if config.token:
        headers["Authorization"] = f"Bearer {config.token}"
    payload = {"phone": telefone, "message": mensagem}
    return _post_json(config.api_url.rstrip("/"), payload, headers, telefone)


def _post_json(url: str, payload: Dict[str, str], headers: Dict[str, str], telefone: str) -> bool:
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20)
    except RequestException as exc:
        print(f"Erro de conexão ao enviar para {telefone}: {exc}")
        return False

    if not response.ok:
        print(
            f"API retornou erro para {telefone}: "
            f"status={response.status_code}, body={response.text[:200]}"
        )
        return False
    return True
