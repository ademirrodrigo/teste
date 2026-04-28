"""Rotina diária de envio automático de cobrança via WhatsApp."""

from __future__ import annotations

import os
from datetime import date, datetime

from database import atualizar_ultimo_envio, init_db, listar_pendentes
from messaging import WhatsAppConfig, enviar_mensagem, montar_mensagem


def tipo_mensagem_para_data(data_vencimento_str: str, hoje: date) -> str | None:
    data_vencimento = datetime.strptime(data_vencimento_str, "%Y-%m-%d").date()
    diferenca = (data_vencimento - hoje).days

    if diferenca == 1:
        return "lembrete"
    if diferenca == 0:
        return "no_dia"
    if diferenca < 0:
        return "atrasado"
    return None


def executar_rotina_diaria() -> None:
    init_db()

    config = WhatsAppConfig(
        api_url=os.getenv("WHATSAPP_API_URL", "https://api.exemplo.com/send"),
        token=os.getenv("WHATSAPP_TOKEN", "seu_token_aqui"),
        instance_id=os.getenv("WHATSAPP_INSTANCE_ID"),
    )

    hoje = date.today()
    pendentes = listar_pendentes()

    for cliente in pendentes:
        tipo = tipo_mensagem_para_data(cliente["data_vencimento"], hoje)
        if not tipo:
            continue

        mensagem = montar_mensagem(tipo, cliente["nome"], cliente["valor"])
        enviado = enviar_mensagem(config, cliente["telefone"], mensagem)

        if enviado:
            atualizar_ultimo_envio(cliente["id"])
            print(f"Mensagem enviada para {cliente['nome']} ({tipo}).")
        else:
            print(f"Falha ao enviar para {cliente['nome']}.")


if __name__ == "__main__":
    executar_rotina_diaria()
