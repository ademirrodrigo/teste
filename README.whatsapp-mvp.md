# WhatsApp Expiration Tracking MVP

MVP simples para cadastro e alerta de vencimento de produtos via WhatsApp.

## Stack
- Node.js + Express
- SQLite local (`mvp.sqlite`)
- Baileys para integração com WhatsApp Web
- node-cron para alertas diários

## Funcionalidades
- Cadastro de usuário por telefone (automaticamente quando envia mensagem)
- Cadastro de produtos com data de vencimento
- Consulta por WhatsApp:
  - `menu`
  - `add,<name>,<YYYY-MM-DD>`
  - `list`
  - `expiring`
  - `expired`
- Fluxo guiado para usuários low-tech:
  - enviar `1` (cadastrar)
  - responder nome
  - responder data
- Sistema de ativação por validade de acesso:
  - campo `expiration_access_date` controla até quando o usuário pode usar
  - quando a data expira, o usuário é automaticamente bloqueado (`active = 0`)
  - comando `status` mostra situação atual do acesso
  - comando `pay` (simulação MVP) ativa por +30 dias
- Cron diário às 08:00:
  - alerta faltando 5 dias
  - alerta faltando 3 dias
  - alerta no dia do vencimento

## Rodar localmente
```bash
npm install
node index.js
```

## Fluxo de uso
1. Inicie o sistema.
2. Escaneie o QR Code no terminal para conectar o WhatsApp.
3. Envie `menu` no chat do número conectado.
4. Para cadastro simples, envie `1` e siga as perguntas.
5. Para checar o acesso, envie `status`.

## Observações do MVP
- O banco é local (arquivo `mvp.sqlite`).
- A pasta `auth_info` será criada automaticamente pelo Baileys para armazenar sessão do WhatsApp.
- Lógica de pagamento Pix está em modo simulação para facilitar teste local.
