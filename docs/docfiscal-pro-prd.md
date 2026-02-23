# DocFiscal Pro — Portal Inteligente para Escritórios Contábeis

## 1. Visão Geral
O **DocFiscal Pro** é um sistema **SaaS web + mobile responsivo** para um único escritório contábil, com foco em:

- centralizar o envio e recebimento de documentos entre contador e clientes;
- controlar vencimentos fiscais cadastrados manualmente;
- reduzir atrasos por meio de notificações automáticas por e-mail e WhatsApp;
- integrar processos com o Nibo.

## 2. Objetivo do Produto
Criar um portal único para comunicação operacional entre contador e cliente, com trilha de auditoria e automação de lembretes de vencimentos fiscais.

## 3. Público-alvo
- **Administrador (escritório contábil)**
- **Clientes do escritório (empresas atendidas)**

## 4. Stack e Plataforma
Implementação prevista em **Bubble.io** com:

- Database nativo Bubble
- Backend Workflows
- API Connector
- Plugin Stripe
- Twilio (WhatsApp API)
- SendGrid (e-mail transacional)

## 5. Estrutura de Telas
- Login / Cadastro
- Dashboard do Contador
- Dashboard do Cliente
- Gestão de Clientes
- Upload de Documentos
- Vencimentos
- Histórico
- Configurações
- Assinatura / Plano

## 6. Diretrizes de UI/UX
- Visual profissional minimalista
- Paleta: azul escuro + verde fiscal
- Sidebar fixa
- Dark mode opcional
- Mobile-first responsivo

## 7. Modelo de Dados (Bubble)

### 7.1 Users
- `id`
- `nome`
- `email`
- `senha`
- `tipo` (`contador` | `cliente`)
- `cliente_relacionado`
- `plano`
- `ativo`
- `telefone_whatsapp`

### 7.2 Clientes
- `id`
- `nome_empresa`
- `cnpj`
- `email_responsavel`
- `telefone`
- `ativo`
- `limite_documentos`

### 7.3 Documentos
- `id`
- `titulo`
- `arquivo`
- `tipo`
- `enviado_por`
- `cliente_relacionado`
- `data_upload`
- `status` (`pendente` | `aprovado` | `rejeitado`)

### 7.4 Vencimentos
- `id`
- `cliente_relacionado`
- `descricao`
- `valor`
- `data_vencimento`
- `status` (`pendente` | `pago` | `vencido`)
- `alerta_enviado_7`
- `alerta_enviado_1`

### 7.5 Assinatura
- `plano`
- `limite_clientes`
- `status`
- `stripe_customer_id`

### 7.6 Índices recomendados
- `cliente_relacionado`
- `data_vencimento`
- `status`

## 8. Fluxos Essenciais

### Fluxo 1 — Cadastro de Cliente
1. Contador cria cliente.
2. Sistema envia convite por e-mail.
3. Cliente define senha e ativa acesso.

### Fluxo 2 — Upload de Documento
1. Cliente envia documento.
2. Contador recebe notificação.
3. Contador aprova ou rejeita.

### Fluxo 3 — Cadastro de Vencimento
1. Contador cria vencimento.
2. Sistema agenda alertas automáticos.

### Fluxo 4 — Notificações Automáticas
- **7 dias antes:** e-mail + WhatsApp
- **1 dia antes:** e-mail + WhatsApp
- **Após vencimento:** alerta de atraso

## 9. Regras de Automação

### Backend Workflow diário
- Consultar vencimentos próximos e vencidos.
- Disparar notificação quando:
  - `data_vencimento - 7 dias`
  - `data_vencimento - 1 dia`
  - `data_vencimento < hoje`

### Mensageria
- **WhatsApp:** Twilio API com template aprovado.
- **E-mail:** SendGrid com template dinâmico.

### Integração com Nibo
- Via API Connector.
- Sincronização manual de clientes.
- Atualização de status financeiro.

## 10. Segurança e Governança
- Login obrigatório
- Permissões por tipo de usuário
- Cliente visualiza apenas seus próprios documentos
- SSL obrigatório
- Rate limit de login
- Logs de auditoria

## 11. Recursos de IA
- Classificação automática de documentos
- Sugestão de categoria fiscal
- Alerta inteligente de risco de inadimplência
- Assistente interno para o contador

## 12. Customizações
- Dark mode
- Personalização com logo do escritório
- Nome do sistema customizável
- Templates de e-mail editáveis

## 13. Monetização
Planos por número de clientes:
- até 20 clientes;
- até 50 clientes;
- ilimitado.

Regras:
- cobrança mensal via Stripe;
- bloqueio automático ao exceder limite do plano.

## 14. Deploy e Testes

### Checklist funcional
- [ ] Teste de upload
- [ ] Teste de notificação
- [ ] Teste de integração API
- [ ] Teste de permissão de usuário
- [ ] Teste de limite por plano
- [ ] Teste mobile

### Otimizações
- Lazy loading
- Compressão de arquivos
- Cache de consultas
