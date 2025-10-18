# 📘 Guia Visual Canva-Style do Monitor eCAC

> **Objetivo:** oferecer um material com aparência de apresentação Canva, organizado em "páginas" com blocos visuais, facilitando a instalação e o uso diário do monitor de eCAC com certificado do contador e procurações associadas.

---

## 🟦 Capa
- **Título:** Monitoramento de eCAC – Implantação Completa
- **Subtítulo:** Escritório Contábil • CPF Contador: 971.212.151-87
- **Elementos visuais sugeridos:**
  - Fundo em degradê azul (#1E3A8A → #3B82F6)
  - Ícones de certificado digital, nuvem e checklist
  - Logotipo do escritório no canto inferior direito

---

## 🟩 Sumário (Página 2)
1. Panorama do Projeto
2. Checklist Pré-Instalação
3. Fluxo de Instalação Windows 11 (Localhost)
4. Fluxo de Instalação Linux/VPS
5. Ativação da API Própria
6. Cadastros e Integrações
7. Uso do Painel Web
8. Operação da CLI do Monitor
9. Automação & Rotina
10. Suporte e Manutenção

---

## 🟨 1. Panorama do Projeto (Página 3)
- **Metas:** centralizar obrigações, notificações e alertas do eCAC.
- **Componentes:**
  - API proprietária (`api_server.py`)
  - Monitor CLI (`main.py`)
  - Painel Web (`webapp.py` + templates + `static/css/app.css`)
  - Banco SQLite (`monitor.db` padrão)
  - Certificados do contador e das empresas (quando necessário)
- **Fluxo geral:** Cadastro ➜ Coleta API ➜ Monitoramento ➜ Alertas/Relatórios

---

## 🟧 2. Checklist Pré-Instalação (Página 4)
| Item | Descrição | Status |
|------|-----------|--------|
| ✅ | Certificado do contador em `.pfx/.p12` com procurações ativas | ☐ |
| ✅ | Token de procuração geral (`procuracao_token`) | ☐ |
| ✅ | Servidor ou PC com Python 3.9+ | ☐ |
| ✅ | Acesso administrativo (sudo/Administrador) | ☐ |
| ✅ | Firewall liberado para porta 5000 (API) e 8000 (painel) | ☐ |
| ✅ | Git instalado (opcional, recomendado) | ☐ |

**Observações visuais:** use um quadro com ícones de escudo, certificado e servidor.

---

## 🟦 3. Instalação Windows 11 (Página 5)
**Layout sugerido:** card duplo (passo + comando) com cores lilás/azul.

1. Baixe ou clone o repositório para `C:\monitor-ecac`.
2. Abra o **Windows PowerShell** como Administrador.
3. Execute o script único:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   cd C:\monitor-ecac
   .\scripts\install_windows.ps1
   ```
4. Ao finalizar, anote:
   - Pasta virtualenv: `C:\monitor-ecac\.venv`
   - Arquivos gerados: `monitor_config.json`, `api_config.json`
   - Comando para ativar ambiente: `C:\monitor-ecac\.venv\Scripts\Activate.ps1`
5. Configure firewall Windows para liberar portas 5000 e 8000 se necessário.

---

## 🟥 4. Instalação Linux/VPS (Página 6)
**Layout sugerido:** blocos horizontais com fundo escuro e texto claro.

1. Conecte-se à VPS (Ubuntu/Debian recomendados).
2. Atualize o sistema e pacotes essenciais:
   ```bash
   sudo apt update && sudo apt install -y git python3 python3-venv python3-pip build-essential libssl-dev libffi-dev
   ```
3. Clone ou copie o projeto para `/opt/monitor-ecac`.
4. Execute o instalador único:
   ```bash
   cd /opt/monitor-ecac
   bash scripts/install_linux.sh
   ```
5. Registre os comandos exibidos ao final para ativar o ambiente virtual e iniciar API/Painel/Monitor.
6. Configure firewall/UFW liberando portas 5000 (API) e 8000 (painel).

---

## 🟩 5. Ativação da API Própria (Página 7)
**Design:** timeline vertical com três checkpoints.

1. **Configuração:** revise `api_config.json` (gerado pelos scripts) e ajuste:
   - `contador_document`: `97121215187`
   - `default_procuracao_token`: token geral do contador
   - `admin_token`: segredo forte
2. **Inicialização:**
   ```bash
   source .venv/bin/activate            # Linux
   python api_server.py
   ```
   ```powershell
   .\.venv\Scripts\Activate.ps1        # Windows
   python api_server.py
   ```
3. **Teste rápido:** acesse `http://localhost:5000/healthz` e confirme resposta `{"status":"ok"}`.

---

## 🟨 6. Cadastros e Integrações (Página 8)
- **Cadastro via API (curl/Postman):**
  ```bash
  curl -X POST http://localhost:5000/admin/clients \
    -H "Content-Type: application/json" \
    -H "X-Admin-Token: SEU_TOKEN_ADMIN" \
    -d '{
      "document": "12345678000190",
      "name": "Empresa Exemplo Ltda",
      "client_type": "PJ",
      "auth_mode": "procuracao"
    }'
  ```
- **Carga de notificações/obrigações:** utilizar endpoints `/notifications` e `/obligations` conforme dados coletados no eCAC.
- **Recomendações visuais:** criar cards coloridos "Cliente", "Notificações", "Obrigações" com ícones correspondentes.

---

## 🟧 7. Uso do Painel Web (Página 9)
**Layout:** mockup de dashboard.

1. Ative o ambiente virtual e execute:
   ```bash
   python webapp.py --config monitor_config.json --database monitor.db
   ```
2. Acesse `http://localhost:8000`.
3. Recursos principais do painel:
   - Dashboard com KPIs (clientes ativos, obrigações pendentes, alertas recentes).
   - Lista de clientes com filtros por modo de autenticação.
   - Cadastro/edição/remoção de clientes.
   - Linha do tempo de eventos e gatilhos de monitoramento manual.
4. Utilize badges de cor diferentes para `auth_mode`: azul (procuracao), verde (certificate).

---

## 🟥 8. Operação da CLI (Página 10)
- **Adicionar cliente (certificate):**
  ```bash
  python main.py add-client \
    --database monitor.db \
    --auth-mode certificate \
    --certificate-path /caminho/cert.pem \
    --private-key-path /caminho/key.pem \
    --certificate-password "senhaOpcional" \
    12345678000190 "Empresa Certificada" PJ
  ```
- **Adicionar cliente (procuração):**
  ```bash
  python main.py add-client \
    --database monitor.db \
    --auth-mode procuracao \
    98765432100 "Contribuinte Procuração" PF
  ```
- **Executar ciclo:** `python main.py run-cycle --database monitor.db`
- **Listar eventos:** `python main.py list-events --database monitor.db`
- **Layout:** tabela dark + destaque para comandos em caixas.

---

## 🟦 9. Automação & Rotina (Página 11)
- **Windows Task Scheduler:**
  - Criar tarefa que executa `powershell.exe -File C:\monitor-ecac\scripts\run_cycle.ps1` (arquivo a ser criado com `Activate.ps1; python main.py run-cycle`).
- **Linux cron:**
  ```bash
  */30 * * * * /opt/monitor-ecac/scripts/run_cycle.sh >> /opt/monitor-ecac/logs/monitor.log 2>&1
  ```
- **Checklist diário:**
  1. Verificar dashboard
  2. Validar alertas enviados
  3. Atualizar obrigações cumpridas

---

## 🟨 10. Suporte e Manutenção (Página 12)
- **Backup:** agende cópias de `monitor.db` e `api_data.db`.
- **Atualizações:**
  - `git pull` no repositório
  - Reinstalar dependências: `pip install -r requirements.txt`
- **Logs:** revisar `logs/` (crie a pasta se necessário).
- **Checklist trimestral:**
  - Renovar certificados perto do vencimento
  - Testar credenciais e tokens
  - Revisar regras de firewall

---

## 🟪 Recursos Visuais Complementares (Página 13)
- **Paleta sugerida:** #1E3A8A, #3B82F6, #FBBF24, #F97316, #10B981
- **Fontes sugeridas:**
  - Títulos: Montserrat Bold
  - Corpo: Open Sans Regular
- **Ícones:** pack "Line Awesome" ou "Feather Icons".
- **Dica:** importe este roteiro para o Canva como guia textual e utilize modelos de apresentação 16:9.

---

## ✅ Entregáveis Gerados
- Manual Canva-Style (este arquivo)
- Scripts de instalação dedicados (`scripts/install_windows.ps1`, `scripts/install_linux.sh`)
- Lista sequencial de arquivos (`sequencia_arquivos.txt`)
- Manual operacional completo (`MANUAL_OPERACIONAL.md`)
- Documentação base (`README.md`)

> **Próximo passo:** abra o Canva, selecione um template corporativo e replique as páginas seguindo este roteiro para um material final visual.
