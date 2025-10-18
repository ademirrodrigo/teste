# Manual Operacional Passo a Passo

Este manual descreve, de ponta a ponta, como preparar um ambiente real do monitoramento de eCAC usando o certificado digital do contador (CPF 97121215187 ou outro de sua titularidade) e, quando necessário, os certificados individuais das empresas ou pessoas físicas atendidas.

## 1. Preparação do ambiente

1. **Sistema operacional**: utilize um servidor Linux atualizado (Ubuntu 22.04+ ou equivalente). As instruções também funcionam em macOS e Windows com WSL.
2. **Pacotes básicos**:
   ```bash
   sudo apt update && sudo apt install -y build-essential libssl-dev libffi-dev python3 python3-venv python3-pip sqlite3 git
   ```
3. **Usuário dedicado (opcional, recomendado)**:
   ```bash
   sudo adduser --system --group monitor-ecac
   sudo mkdir -p /opt/monitor-ecac
   sudo chown monitor-ecac:monitor-ecac /opt/monitor-ecac
   ```
4. **Clonar o repositório** (use a pasta desejada):
   ```bash
   cd /opt/monitor-ecac
   git clone https://seu-servidor/git/monitor-ecac.git .
   ```

## 2. Execução do instalador unificado (Windows e Linux)

1. Com o repositório clonado, execute o instalador incluso:
   ```bash
   python install.py
   ```
   - Em Windows, rode o comando em um Prompt/Powershell com Python 3.9+ (ou use o atalho `./scripts/install_windows.ps1`).
   - Em Linux (ou VPS), utilize o Python do sistema (`python3 install.py`) ou o atalho `bash scripts/install_linux.sh`.
2. O script cria automaticamente o ambiente virtual `.venv`, instala as
   dependências listadas em `requirements.txt` e gera `monitor_config.json` e
   `api_config.json` a partir dos modelos.
3. Ao finalizar, o instalador informa o comando correto para ativar o ambiente
   virtual e os próximos passos (iniciar a API, painel web e monitor CLI).
4. Caso precise ajustar algo manualmente, ainda é possível ativar o ambiente
   com `source .venv/bin/activate` (Linux) ou `.venv\Scripts\activate` (Windows)
   e reinstalar dependências com `pip install -r requirements.txt`.

## 3. Configuração inicial dos arquivos

1. Copie o arquivo de configuração do monitor:
   ```bash
   cp monitor_config.example.json monitor_config.json
   ```
2. Edite `monitor_config.json` definindo:
   - `api_base_url`: `http://localhost:5000` (ou o host onde a API ficará).
   - `contador_document`: `97121215187` (ou o CPF/CNPJ do contador responsável).
   - `procuracao_token`: token padrão emitido no eCAC para o contador.
   - Ajuste `poll_interval`, `timeout`, `verify_ssl` e `webhook_url` conforme sua operação.
3. Crie um diretório seguro para certificados e chaves das empresas que utilizarão autenticação por certificado.

### 3.1 Preparar o certificado do contador com procurações

1. Localize o arquivo do certificado do contador (`.pfx` ou `.p12`) emitido pela autoridade certificadora.
2. Converta-o para os formatos `.pem` esperados pelo monitor:
   ```bash
   openssl pkcs12 -in certificado-contador.pfx -out contador.pem -clcerts -nodes
   openssl pkcs12 -in certificado-contador.pfx -out contador-key.pem -nocerts -nodes
   chmod 600 contador.pem contador-key.pem
   ```
3. Registre os caminhos resultantes; eles serão informados no cadastro dos clientes que utilizam o modo `certificate`.
4. Mantenha os arquivos em diretório com permissões restritas (ex.: `chmod 700 /opt/monitor-ecac/certificados`).

## 4. Configuração da API própria (`api_server.py`)

1. Copie e personalize o arquivo de configuração da API:
   ```bash
   cp api_config.example.json api_config.json
   ```
2. Edite `api_config.json` com os campos reais:
   - `contador_document`: `97121215187`.
   - `default_procuracao_token`: token padrão configurado no eCAC.
   - `admin_token`: defina um segredo forte (ex.: resultado de `openssl rand -hex 32`).
   - `access_token_ttl`: tempo de vida dos tokens (padrão 120 minutos).
3. Defina as variáveis de ambiente e inicie a API:
   ```bash
   export API_CONFIG=$(pwd)/api_config.json
   export API_DATABASE=$(pwd)/api_data.db
   source .venv/bin/activate
   python api_server.py
   ```
4. Confirme que a API está acessível acessando `http://localhost:5000/healthz` (deve retornar `{"status":"ok"}`).

## 5. Cadastro e alimentação de clientes na API

1. **Cadastrar clientes**:
   ```bash
   curl -X POST http://localhost:5000/admin/clients \
     -H "Content-Type: application/json" \
     -H "X-Admin-Token: SEU_TOKEN_ADMIN" \
     -d '{
       "document": "12345678000190",
       "name": "Empresa Exemplo Ltda",
       "client_type": "PJ",
       "auth_mode": "procuracao",
       "procuracao_token": "token-especifico-opcional"
     }'
   ```
   - Para clientes que usarão certificado, informe `"auth_mode": "certificate"` e mantenha `procuracao_token` vazio ou com token complementar.
2. **Carregar notificações e obrigações** quando houver novidades:
   ```bash
   curl -X POST http://localhost:5000/admin/clients/12345678000190/notifications \
     -H "Content-Type: application/json" \
     -H "X-Admin-Token: SEU_TOKEN_ADMIN" \
     -d '{
       "notification": {
         "title": "Aviso do eCAC",
         "category": "Mensagens",
         "protocol": "2024-0001"
       }
     }'

   curl -X POST http://localhost:5000/admin/clients/12345678000190/obligations \
     -H "Content-Type: application/json" \
     -H "X-Admin-Token: SEU_TOKEN_ADMIN" \
     -d '{
       "obligations": [
         {"description": "Entrega DCTF", "due_date": "2024-06-30", "status": "pending"}
       ]
     }'
   ```
3. Consulte a lista de clientes para validar:
   ```bash
   curl -H "X-Admin-Token: SEU_TOKEN_ADMIN" http://localhost:5000/admin/clients
   ```
4. **Coleta no eCAC com o certificado do contador**:
   - Autentique-se no portal eCAC usando o certificado convertido do contador (ex.: CPF `97121215187`).
   - Verifique as notificações e obrigações dos clientes outorgantes das procurações.
   - Transcreva ou exporte os dados relevantes e envie-os para a API utilizando os endpoints administrativos acima.
   - Registre protocolos, vencimentos e status exatamente como exibidos para manter o histórico consistente.

## 6. Preparação do banco do monitor

1. O banco SQLite será criado automaticamente quando o monitor ou o painel web forem executados. Defina o caminho desejado (ex.: `/opt/monitor-ecac/monitor.db`).
2. Opcionalmente inicialize o arquivo com permissões restritas:
   ```bash
   touch monitor.db
   chmod 600 monitor.db
   ```

## 7. Cadastro de clientes no monitor (CLI)

1. Execute o comando `add-client` para cada contribuinte:
   ```bash
   source .venv/bin/activate
   python main.py add-client \
     --database monitor.db \
     12345678000190 "Empresa Exemplo Ltda" PJ \
     /caminho/certificados/empresa.pem \
     /caminho/certificados/empresa-key.pem \
     --certificate-password "senhaOpcional"
   ```
2. Para clientes que usarão apenas a procuração do contador:
   ```bash
   python main.py add-client \
     --database monitor.db \
     98765432100 "Contribuinte Procuração" PF \
     --auth-mode procuracao \
     --procuracao-token "token-especifico-opcional"
   ```
3. Confira os registros:
   ```bash
   python main.py list-clients --database monitor.db
   ```

## 8. Execução do monitoramento

1. **Ciclo contínuo** (recomendado em produção):
   ```bash
   python main.py run --database monitor.db --config monitor_config.json
   ```
   - O comando roda em loop, consulta a API a cada `poll_interval` e salva eventos.
2. **Ciclo único** (útil para cron ou testes):
   ```bash
   python main.py run --database monitor.db --config monitor_config.json --once
   ```
3. **Ciclo direcionado a um cliente**:
   ```bash
   python main.py run --database monitor.db --config monitor_config.json --client 12345678000190
   ```

## 9. Painel web para operações diárias

1. Configure as variáveis de ambiente:
   ```bash
   export MONITOR_DATABASE=$(pwd)/monitor.db
   export MONITOR_CONFIG=$(pwd)/monitor_config.json
   export FLASK_SECRET_KEY="chave-ultra-secreta"
   ```
2. Inicie o painel:
   ```bash
   python webapp.py
   ```
3. Acesse `http://localhost:8000` para:
   - Visualizar o dashboard com métricas e clientes críticos.
   - Cadastrar, editar e excluir clientes.
   - Visualizar o histórico de eventos e obrigações.
   - Executar ciclos manuais (globais ou por cliente).
4. Se o navegador exibir erro de conexão, confirme:
   - Se o processo `python webapp.py` está em execução e sem erros no terminal.
   - Se a variável `MONITOR_CONFIG` aponta para o caminho correto do arquivo JSON.
   - Se a porta `8000` está liberada no firewall local ou de rede.

## 10. Automação e serviços

1. **Systemd para o monitor** (`/etc/systemd/system/monitor-ecac.service`):
   ```ini
   [Unit]
   Description=Monitoramento eCAC
   After=network.target

   [Service]
   User=monitor-ecac
   WorkingDirectory=/opt/monitor-ecac
   Environment="PYTHONUNBUFFERED=1"
   Environment="API_CONFIG=/opt/monitor-ecac/api_config.json"
   Environment="API_DATABASE=/opt/monitor-ecac/api_data.db"
   ExecStart=/opt/monitor-ecac/.venv/bin/python main.py run --database /opt/monitor-ecac/monitor.db --config /opt/monitor-ecac/monitor_config.json
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
2. **Systemd para a API** (opcional) configurando `ExecStart=/opt/monitor-ecac/.venv/bin/python api_server.py`.
3. **Systemd para o painel web** com `ExecStart=/opt/monitor-ecac/.venv/bin/python webapp.py`.
4. Ative os serviços:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now monitor-ecac.service
   sudo systemctl enable --now monitor-ecac-api.service
   sudo systemctl enable --now monitor-ecac-web.service
   ```

## 11. Boas práticas operacionais

- **Backups**: copie `monitor.db` e `api_data.db` diariamente (ex.: `rsync` ou snapshots do servidor).
- **Segurança**: mantenha certificados e arquivos JSON com permissões restritas (`chmod 600`).
- **Logs**: redirecione `stdout` para arquivos usando `systemd` (`journalctl -u monitor-ecac.service -f`).
- **Atualizações**: antes de atualizar, pare os serviços, faça backup dos bancos e execute `git pull` seguido de `pip install -r requirements.txt`.
- **Testes pontuais**: valide a API com `curl http://localhost:5000/healthz` e o monitor com `python main.py show-status --database monitor.db DOCUMENTO`.

## 12. Checklist rápido (produção)

1. [ ] API ativa (`journalctl -u monitor-ecac-api.service -f`).
2. [ ] Clientes cadastrados na API (`curl /admin/clients`).
3. [ ] `monitor_config.json` com CPF do contador e token padrão corretos.
4. [ ] Clientes cadastrados no monitor (`python main.py list-clients`).
5. [ ] Monitor rodando continuamente (serviço `monitor-ecac.service`).
6. [ ] Painel web acessível para a equipe (`http://servidor:8000`).
7. [ ] Backups agendados dos bancos SQLite.

Seguindo este roteiro, o escritório operará um sistema real de monitoramento do eCAC sem dependência de terceiros, com total controle sobre a API, o monitor e o painel web.
