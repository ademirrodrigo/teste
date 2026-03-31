# 📱 Manual de Instalação e Operação
## WhatsApp Product Expiration Tracker

---

## 📋 Índice

1. [Pré-requisitos](#pré-requisitos)
2. [Instalação](#instalação)
3. [Configuração](#configuração)
4. [Como Usar](#como-usar)
5. [Comandos Disponíveis](#comandos-disponíveis)
6. [Funcionamento do Sistema](#funcionamento-do-sistema)
7. [Pagamento](#pagamento)
8. [Solução de Problemas](#solução-de-problemas)
9. [Manutenção](#manutenção)

---

## 🔧 Pré-requisitos

Antes de começar, certifique-se de ter:

| Item | Versão Mínima | Como Instalar |
|------|---------------|---------------|
| **Node.js** | v16.x ou superior | [nodejs.org](https://nodejs.org/) |
| **npm** | v8.x ou superior | Instalado com Node.js |
| **WhatsApp** | Conta ativa | Aplicativo no celular |
| **Internet** | Conexão estável | - |

### Verificar instalações:

```bash
node --version
npm --version
```

---

## 📥 Instalação

### Passo 1: Baixar o Projeto

```bash
# Navegue até a pasta do projeto
cd whatsapp-expiration-tracker
```

### Passo 2: Instalar Dependências

```bash
npm install
```

**O que será instalado:**
- `express` - Servidor web
- `baileys` - API do WhatsApp
- `better-sqlite3` - Banco de dados
- `node-cron` - Agendador de tarefas
- `qrcode-terminal` - Exibir QR Code no terminal

### Passo 3: Verificar Instalação

```bash
ls -la
# Deve mostrar: node_modules/, package.json, index.js, bot.js, db.js, cron.js
```

---

## ⚙️ Configuração

### Estrutura de Arquivos

```
whatsapp-expiration-tracker/
├── index.js          # Servidor principal
├── bot.js            # Lógica do WhatsApp
├── db.js             # Banco de dados
├── cron.js           # Alertas automáticos
├── package.json      # Dependências
├── expiration.db     # Banco SQLite (criado automaticamente)
└── README.md         # Documentação
```

### Configurações Opcionais

Edite `index.js` para alterar:

```javascript
const PORT = process.env.PORT || 3000;  // Porta do servidor
const ALERT_HOUR = 8;                    // Horário do alerta (24h)
const EXPIRING_DAYS = 5;                 // Dias para alerta
```

---

## 🚀 Como Usar

### Passo 1: Iniciar o Sistema

```bash
node index.js
```

**Saída esperada:**
```
🚀 Servidor rodando na porta 3000
📱 Conectando ao WhatsApp...
📊 Banco de dados inicializado
⏰ Agenda de alertas configurada
```

### Passo 2: Escanear QR Code

1. Um QR Code aparecerá no terminal
2. Abra o WhatsApp no seu celular
3. Vá em **Aparelhos conectados** → **Conectar aparelho**
4. Escaneie o QR Code

**Importante:** Use um número exclusivo para o bot (não use seu número pessoal principal).

### Passo 3: Bot Conectado

Quando conectado, você verá:
```
✅ WhatsApp conectado!
🤖 Bot pronto para receber mensagens
```

---

## 💬 Comandos Disponíveis

### Menu Principal

Envie qualquer uma destas opções:
- `menu`
- `1`

**Resposta:**
```
📦 GERENCIADOR DE VALIDADE

Escolha uma opção:

1️⃣ Adicionar produto
   Formato: add,NOME,AAAA-MM-DD
   Exemplo: add,Leite,2025-04-15

2️⃣ Listar produtos
   Envie: list

3️⃣ Produtos vencendo em breve
   Envie: expiring

4️⃣ Produtos vencidos
   Envie: expired

💡 Dica: Você pode enviar apenas o número da opção!
```

---

### 1️⃣ Adicionar Produto

**Formato:**
```
add,NOME_DO_PRODUTO,DATA_DE_VALIDADE
```

**Exemplos válidos:**
```
add,Leite,2025-04-15
add,Iogurte Natural,2025-03-20
add,Queijo Minas,2025-04-01
```

**Respostas possíveis:**

✅ **Sucesso:**
```
✅ Produto adicionado!

📦 Nome: Leite
📅 Validade: 15/04/2025
⏰ Faltam 30 dias
```

❌ **Erro de formato:**
```
❌ Formato inválido!

Use: add,NOME,AAAA-MM-DD
Exemplo: add,Leite,2025-04-15
```

❌ **Data inválida:**
```
❌ Data inválida!

Use o formato: AAAA-MM-DD
Exemplo: 2025-04-15
```

❌ **Data passada:**
```
⚠️ Atenção: Este produto já está vencido!
```

---

### 2️⃣ Listar Produtos

**Comando:**
```
list
```
ou
```
2
```

**Resposta:**
```
📦 SEUS PRODUTOS (3)

1. Leite
   📅 15/04/2025 (30 dias)
   ✅ Válido

2. Iogurte Natural
   📅 20/03/2025 (5 dias)
   ⚠️ Vence em breve

3. Queijo Minas
   📅 01/04/2025 (16 dias)
   ✅ Válido

─────────────────
Total: 3 produtos
```

**Se não houver produtos:**
```
📦 Nenhum produto cadastrado!

Envie: add,NOME,AAAA-MM-DD
Para adicionar seu primeiro produto.
```

---

### 3️⃣ Produtos Vencendo em Breve

**Comando:**
```
expiring
```
ou
```
3
```

**Resposta:**
```
⚠️ PRODUTOS VENCENDO EM 5 DIAS

1. Iogurte Natural
   📅 20/03/2025
   ⏰ Faltam 5 dias

2. Requeijão
   📅 21/03/2025
   ⏰ Faltam 6 dias

─────────────────
Total: 2 produtos
```

**Se não houver:**
```
✅ Nenhum produto vencendo nos próximos 5 dias!
```

---

### 4️⃣ Produtos Vencidos

**Comando:**
```
expired
```
ou
```
4
```

**Resposta:**
```
❌ PRODUTOS VENCIDOS

1. Manteiga
   📅 10/03/2025
   ⏰ Venceu há 5 dias

─────────────────
Total: 1 produto vencido
```

**Se não houver:**
```
✅ Nenhum produto vencido!
```

---

## 🔄 Funcionamento do Sistema

### Fluxo do Usuário

```
┌─────────────────────────────────────────────────────┐
│  1. Usuário envia mensagem no WhatsApp              │
│     ↓                                                │
│  2. Bot identifica o número do telefone             │
│     ↓                                                │
│  3. Verifica se usuário está ativo no banco         │
│     ↓                                                │
│  4. Processa o comando                              │
│     ↓                                                │
│  5. Retorna resposta via WhatsApp                   │
└─────────────────────────────────────────────────────┘
```

### Alertas Automáticos

**Horário:** Todos os dias às 08:00

**O que acontece:**
1. Sistema verifica todos os produtos
2. Identifica produtos que vencem em:
   - 5 dias
   - 3 dias
   - Já venceram
3. Envia mensagem automática para cada usuário

**Exemplo de alerta:**
```
🔔 LEMBRETE DE VALIDADE

Olá! Aqui estão seus produtos com atenção hoje:

⚠️ Vencendo em 5 dias:
• Iogurte Natural (20/03/2025)

⚠️ Vencendo em 3 dias:
• Leite (18/03/2025)

❌ Vencidos:
• Manteiga (10/03/2025)

Use o comando "list" para ver todos os produtos.
```

---

## 💰 Pagamento

### Sistema de Ativação

O sistema possui controle de acesso por assinatura:

| Status | Descrição |
|--------|-----------|
| `active = 1` | Usuário ativo - acesso liberado |
| `active = 0` | Usuário inativo - acesso bloqueado |

### Mensagem de Bloqueio

Se usuário estiver inativo:
```
⚠️ ACESSO BLOQUEADO

Sua assinatura está vencida.

Para reativar, faça o pagamento via PIX:

Chave PIX: seu-email@exemplo.com
Valor: R$ 9,90/mês

Após o pagamento, envie: ATIVAR
```

### Ativar Usuário (Administrador)

No código, use a função:
```javascript
await activateUser('5511999999999');
```

Ou via banco de dados:
```sql
UPDATE users SET active = 1 WHERE phone = '5511999999999';
```

### Placeholder de Pagamento

A função `processPixPayment()` em `bot.js` está pronta para integração com:
- API de banco
- Gateway de pagamento
- Verificação automática de PIX

---

## 🛠️ Solução de Problemas

### Problema: QR Code não aparece

**Causas possíveis:**
- Baileys não instalou corretamente
- Terminal não suporta caracteres Unicode

**Solução:**
```bash
# Reinstalar dependências
rm -rf node_modules
npm install

# Ou usar outro terminal
```

---

### Problema: "Cannot find module 'baileys'"

**Solução:**
```bash
npm install @whiskeysockets/baileys --save
```

---

### Problema: Banco de dados corrompido

**Solução:**
```bash
# Deletar banco existente
rm expiration.db

# Reiniciar o sistema
node index.js
# Banco será recriado automaticamente
```

---

### Problema: Alertas não estão funcionando

**Verificações:**
1. Cron job está rodando?
   ```bash
   # Verificar logs no console
   ```

2. Horário do sistema está correto?
   ```bash
   date
   ```

3. Usuários têm produtos cadastrados?
   ```bash
   # Verificar no banco
   sqlite3 expiration.db "SELECT * FROM products;"
   ```

---

### Problema: Bot não responde mensagens

**Verificações:**
1. WhatsApp está conectado?
   - Verificar mensagem "✅ WhatsApp conectado!"

2. Número está ativo no banco?
   ```sql
   SELECT * FROM users WHERE phone = '5511999999999';
   ```

3. Usuário está ativo?
   ```sql
   UPDATE users SET active = 1 WHERE phone = '5511999999999';
   ```

---

### Problema: Erro de permissão no banco

**Solução:**
```bash
# Dar permissão de escrita
chmod 666 expiration.db

# Ou rodar como administrador (não recomendado)
sudo node index.js
```

---

## 🔧 Manutenção

### Backup do Banco de Dados

```bash
# Copiar banco de dados
cp expiration.db expiration_backup_$(date +%Y%m%d).db

# Ou compactar
tar -czf backup_$(date +%Y%m%d).tar.gz expiration.db
```

### Restaurar Backup

```bash
# Parar o sistema
Ctrl+C

# Substituir banco
cp expiration_backup_20250101.db expiration.db

# Reiniciar
node index.js
```

---

### Limpar Dados Antigos

```sql
-- Remover produtos vencidos há mais de 30 dias
DELETE FROM products 
WHERE expiration_date < date('now', '-30 days');

-- Remover usuários inativos há mais de 90 dias
DELETE FROM users 
WHERE active = 0 AND last_access < date('now', '-90 days');
```

---

### Atualizar o Sistema

```bash
# Parar o sistema
Ctrl+C

# Puxar atualizações (se usar Git)
git pull

# Reinstalar dependências
npm install

# Reiniciar
node index.js
```

---

### Monitorar Logs

```bash
# Rodar e salvar logs
node index.js > logs.txt 2>&1

# Ou usar tmux/screen para manter rodando
tmux new -s whatsapp-bot
node index.js
# Ctrl+B, D para desanexar
```

---

## 📊 Comandos SQL Úteis

### Ver todos os usuários
```sql
SELECT * FROM users;
```

### Ver produtos de um usuário
```sql
SELECT p.name, p.expiration_date, u.phone
FROM products p
JOIN users u ON p.user_id = u.id
WHERE u.phone = '5511999999999';
```

### Contar produtos por status
```sql
SELECT 
  COUNT(*) as total,
  SUM(CASE WHEN expiration_date > date('now', '+5 days') THEN 1 ELSE 0 END) as validos,
  SUM(CASE WHEN expiration_date BETWEEN date('now') AND date('now', '+5 days') THEN 1 ELSE 0 END) as vencendo,
  SUM(CASE WHEN expiration_date < date('now') THEN 1 ELSE 0 END) as vencidos
FROM products;
```

### Ativar todos os usuários (teste)
```sql
UPDATE users SET active = 1;
```

---

## 📞 Suporte

### Logs de Erro

Sempre verifique o console para erros. Exemplo:
```
[ERRO] Falha ao salvar produto: SQLITE_CONSTRAINT
[INFO] Usuário 5511999999999 solicitado lista
[ALERT] Enviando alerta para 3 usuários
```

### Contato

Para suporte técnico ou dúvidas:
- 📧 Email: suporte@exemplo.com
- 💬 WhatsApp: (11) 99999-9999
- 📖 Documentação: README.md

---

## ✅ Checklist de Implantação

- [ ] Node.js instalado
- [ ] Dependências instaladas (`npm install`)
- [ ] QR Code escaneado
- [ ] Primeiro usuário cadastrado
- [ ] Primeiro produto adicionado
- [ ] Alerta automático testado
- [ ] Backup configurado
- [ ] Sistema de pagamento integrado (opcional)

---

## 🎯 Próximos Passos

1. **Produção:**
   - Hospedar em servidor (Heroku, DigitalOcean, AWS)
   - Configurar variáveis de ambiente
   - Usar banco PostgreSQL (opcional)

2. **Melhorias:**
   - Integrar gateway de pagamento real
   - Adicionar painel web administrativo
   - Criar relatórios por email
   - Suporte a múltiplos idiomas

3. **Escala:**
   - Usar Redis para sessões
   - Implementar filas de mensagens
   - Adicionar balanceamento de carga

---

**Versão do Manual:** 1.0  
**Última Atualização:** Janeiro 2025  
**Desenvolvido por:** Senior Full-Stack Engineer
