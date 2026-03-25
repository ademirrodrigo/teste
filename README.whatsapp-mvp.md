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

## Observações do MVP
- O banco é local (arquivo `mvp.sqlite`).
- A pasta `auth_info` será criada automaticamente pelo Baileys para armazenar sessão do WhatsApp.
- Lógica de pagamento Pix está como placeholder em `bot.js` (`processPixActivation`).
