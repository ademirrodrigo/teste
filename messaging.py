"""Envio de mensagens via API REST (UltraMsg/Z-API-like)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import requests


@dataclass
class WhatsAppConfig:
    api_url: str
    token: str
    instance_id: str | None = None


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
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.token}",
    }
    payload = {
        "to": telefone,
        "body": mensagem,
    }

    # Para APIs que exigem instance_id no path.
    url = config.api_url
    if config.instance_id:
        url = f"{config.api_url.rstrip('/')}/instances/{config.instance_id}/messages/chat"

    response = requests.post(url, json=payload, headers=headers, timeout=20)
    return response.ok
