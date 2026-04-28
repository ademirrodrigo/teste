"""Rotina diária de envio automático de cobrança via WhatsApp."""

from __future__ import annotations

import os
import time
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


def ja_enviado_hoje(ultimo_envio: str | None, hoje: date) -> bool:
    if not ultimo_envio:
        return False

    try:
        data_ultimo_envio = datetime.fromisoformat(ultimo_envio).date()
    except ValueError:
        return False
    return data_ultimo_envio == hoje


def executar_rotina_diaria() -> None:
    init_db()

    provider = os.getenv("WHATSAPP_PROVIDER", "rest").lower()
    api_url = os.getenv("WHATSAPP_API_URL")
    token = os.getenv("WHATSAPP_TOKEN", "")
    if not api_url:
        raise RuntimeError("Defina a variável WHATSAPP_API_URL antes de executar.")

    if provider == "rest" and not token:
        raise RuntimeError(
            "Para provider REST, defina WHATSAPP_TOKEN além de WHATSAPP_API_URL."
        )

    config = WhatsAppConfig(
        api_url=api_url,
        token=token,
        instance_id=os.getenv("WHATSAPP_INSTANCE_ID"),
        provider=provider,
    )

    hoje = date.today()
    pendentes = listar_pendentes()

    for cliente in pendentes:
        if ja_enviado_hoje(cliente["ultimo_envio"], hoje):
            continue

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


def executar_loop_diario() -> None:
    while True:
        print(f"Iniciando ciclo de envio em {datetime.utcnow().isoformat(timespec='seconds')}Z")
        executar_rotina_diaria()
        print("Ciclo finalizado. Aguardando 24 horas para o próximo envio.")
        time.sleep(60 * 60 * 24)


if __name__ == "__main__":
    if os.getenv("RUN_DAILY_LOOP", "0") == "1":
        executar_loop_diario()
    else:
        executar_rotina_diaria()
