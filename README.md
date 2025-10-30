# BPO Financeiro Simples

O repositório agora inclui um sistema completo para escritórios de contabilidade que desejam oferecer BPO Financeiro aos seus clientes. A solução roda em `localhost`, usa apenas tecnologias gratuitas e foi pensada para ser clara para empresários que não dominam termos contábeis.

## Principais recursos

- **Multiempresa**: cadastre quantas empresas quiser, cada uma com contas bancárias, categorias e usuários próprios.
- **Perfis de acesso separados**: clientes visualizam apenas os dados da própria empresa, enquanto o escritório possui um painel com visão consolidada.
- **Importação de extratos**: suporte a arquivos Excel (`.xlsx`), CSV e OFX com classificação automática por palavras-chave.
- **Relatórios em linguagem simples**: Fluxo de Caixa mensal, resumo de resultado (DRE simplificada), listas de contas a pagar e receber, além de destaques que explicam a situação do negócio.
- **Exportação**: gere relatórios em PDF ou Excel com um clique.
- **Interface responsiva**: painel renovado com seleção de período, gráfico interativo de fluxo de caixa e listas amigáveis de contas a pagar e receber que funcionam bem em computadores e celulares.
- **Centro de configurações**: menu moderno para o escritório administrar empresas, usuários, contas bancárias, categorias, lançamentos e importações em um único lugar.
- **Integração NFSe (ABRASF)**: envie XMLs para os principais serviços SOAP (consulta, cancelamento, geração etc.) direto do painel administrativo.
- **API FastAPI com SQLite**: pronta para receber uma futura migração para PostgreSQL.
- **Containerização**: Dockerfile e Docker Compose para subir o ambiente rapidamente.

## Como executar com Docker

```bash
docker compose up --build
```

O serviço ficará disponível em `http://localhost:8000`. A interface web pode ser acessada em `http://localhost:8000/`.

O sistema utiliza variáveis definidas em um arquivo `.env` na raiz do projeto. Os scripts de instalação criam esse arquivo automaticamente com uma chave secreta e credenciais iniciais geradas na hora. Caso esteja configurando manualmente, crie um arquivo `.env` com, por exemplo:

```
BPO_SECRET_KEY=troque-esta-chave
BPO_ADMIN_EMAIL=admin@bpo.local
BPO_ADMIN_PASSWORD=uma-senha-bem-segura
BPO_ADMIN_NAME=Administrador
# opcional: BPO_DATABASE_URL=sqlite:///./bpo_finance.db
# integração NFSe (preencha se desejar acionar os serviços SOAP)
# BPO_NFSE_WSDL_URL=https://exemplo.prefeitura.gov.br/nfse?wsdl
# BPO_NFSE_SERVICE_URL=https://exemplo.prefeitura.gov.br/nfse.asmx
# BPO_NFSE_TIMEOUT=45
# BPO_NFSE_VERIFY_SSL=true
```

Na primeira inicialização essas informações criam o usuário administrador. Atualize a senha após o primeiro acesso e utilize valores fortes (principalmente para `BPO_SECRET_KEY`) antes de levar o sistema para produção.

## Executando sem Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn bpo_app.main:app --reload
```

## Testes automatizados

```bash
python -m unittest discover
```

Os testes cobrem o fluxo principal: login, cadastro de empresa, importação de extratos e geração de relatórios.

## Scripts de instalação automatizada

Os arquivos estão organizados em `installers/` com numeração sequencial para facilitar o envio direto ao cliente:

1. `installers/01_windows_installer.ps1`
2. `installers/02_linux_installer.sh`

Cada script prepara o ambiente, instala dependências e pode iniciar o servidor imediatamente.

### Windows 11 (PowerShell)

```powershell
Set-ExecutionPolicy -Scope Process Bypass
cd installers
./01_windows_installer.ps1
```

Use `-SkipRun` para instalar sem iniciar o servidor automaticamente ou ajuste host e porta com `-Host` e `-Port`.

O script cria um arquivo `.env` com chave secreta e mostra na tela as credenciais iniciais do administrador.

### Linux ou VPS Contábil (bash)

```bash
cd installers
chmod +x 02_linux_installer.sh
./02_linux_installer.sh
```

No Linux é possível evitar que o script execute o servidor adicionando `--skip-run`. Também é possível definir host e porta com `--host` e `--port`.

Assim como no Windows, o script gera um `.env` com chave secreta e exibe as credenciais iniciais para você guardar.

### Manual visual de instalação e uso

Um guia passo a passo em formato de apresentação está disponível em `docs/manual_canva.md`. Ele pode ser compartilhado diretamente com clientes ou importado em ferramentas como Canva para customização visual.

### Pacote completo para enviar ao cliente

Use o comando abaixo para gerar um arquivo `.zip` com os instaladores, guia rápido, manual visual e arquivos da interface web. O pacote fica disponível em `dist/bpo_instalacao.zip` e pode ser anexado em e-mails ou compartilhado por Drive.

```bash
python tools/create_install_bundle.py
```

Se quiser personalizar o destino ou remover a interface web do pacote, consulte `docs/pacote_instalacao.md`.

### Integração NFSe (ABRASF)

O backend expõe a rota `POST /integrations/nfse/{operacao}` para enviar XMLs aos serviços padronizados pelo layout ABRASF. Informe o nome da operação (por exemplo, `ConsultarNfsePorRps`, `GerarNfse` ou `CancelarNfse`) e envie um JSON com o XML do cabeçalho (`nfse_cabec_msg`) e dos dados (`nfse_dados_msg`). Opcionalmente é possível sobrescrever a URL do WSDL, o endpoint do serviço, timeout e a verificação de certificado.

Exemplo de chamada:

```bash
curl -X POST "http://localhost:8000/integrations/nfse/ConsultarNfsePorRps" \
  -H "Authorization: Bearer <TOKEN_DO_ADMIN>" \
  -H "Content-Type: application/json" \
  -d '{
        "nfse_cabec_msg": "<cabecalho>...</cabecalho>",
        "nfse_dados_msg": "<dados>...</dados>",
        "wsdl_url": "https://exemplo.prefeitura.gov.br/nfse?wsdl",
        "service_url": "https://exemplo.prefeitura.gov.br/nfse.asmx"
      }'
```

Se nenhum valor for enviado para `wsdl_url` ou `service_url`, o sistema utiliza as configurações definidas no `.env`. Apenas administradores ou membros da equipe interna (perfil `staff`) podem acionar essa integração.

## Estrutura de pastas relevante

- `bpo_app/main.py`: aplicação FastAPI com autenticação por token, rotas de cadastro, importação de extratos e relatórios.
- `bpo_app/models.py`: modelos do SQLAlchemy prontos para uso com SQLite ou PostgreSQL.
- `bpo_app/frontend/`: arquivos HTML, CSS e JavaScript da interface amigável para o cliente.
- `docker-compose.yml` e `Dockerfile`: containerização pronta para desenvolvimento.

> A aplicação legado de monitoramento do eCAC continua disponível abaixo para referência.

# Monitoramento do eCAC

Este repositório contém uma ferramenta CLI em Python para monitorar periodicamente o eCAC para escritórios de contabilidade. Ela autentica usando o certificado digital de cada contribuinte (empresa ou pessoa física) ou, opcionalmente, apenas a procuração eletrônica do contador, consulta uma API proprietária e registra novos eventos em um banco SQLite, disparando alertas via webhook.

## Requisitos

- Python 3.9 ou superior
- Bibliotecas [`requests`](https://pypi.org/project/requests/) e [`Flask`](https://flask.palletsprojects.com/)
- Certificados digitais (`.pem`) dos clientes que usarão o modo por certificado e procuração eletrônica ativa para o contador
- API própria do escritório capaz de autenticar e consultar notificações/obrigações do eCAC

Instale a dependência:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configuração da API proprietária incluída

O repositório agora acompanha uma API real (`api_server.py`) que atende aos mesmos contratos esperados pelo monitor. Ela armazena clientes, notificações e obrigações em SQLite e valida o acesso por certificado ou pela procuração do contador.

1. Copie `api_config.example.json` para `api_config.json` e defina seus valores reais:
   - `contador_document`: informe o CPF/CNPJ do contador que assina as procurações (por exemplo, `97121215187`).
   - `default_procuracao_token`: token padrão emitido no eCAC para o contador.
   - `access_token_ttl`: tempo de vida (em minutos) dos tokens de acesso emitidos pela API.
   - `admin_token`: segredo usado para autenticar as rotas administrativas (troque por um valor robusto).
2. Inicie a API:

   ```bash
   export API_CONFIG=api_config.json
   export API_DATABASE=api_data.db
   python api_server.py
   ```

3. Cadastre cada cliente autorizado (PJ ou PF). Exemplo usando apenas a procuração do contador:

   ```bash
   curl -X POST http://localhost:5000/admin/clients \
     -H "Content-Type: application/json" \
     -H "X-Admin-Token: SEU_TOKEN_ADMIN" \
     -d '{
       "document": "12345678000190",
       "name": "Empresa Exemplo Ltda",
       "client_type": "PJ",
       "procuracao_token": "token-especifico-opcional"
     }'
   ```

4. Alimente a API com notificações e obrigações sempre que houver novos dados do eCAC (por integração automática ou operação manual). Exemplos:

   ```bash
   curl -X POST http://localhost:5000/admin/clients/12345678000190/notifications \
     -H "Content-Type: application/json" \
     -H "X-Admin-Token: SEU_TOKEN_ADMIN" \
     -d '{
       "notification": {
         "title": "Mensagem do eCAC",
         "category": "Avisos",
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

5. Atualize `monitor_config.json` (copiado de `monitor_config.example.json`) apontando `api_base_url` para `http://localhost:5000`, definindo o mesmo `contador_document` e o token padrão desejado. Opcionalmente ajuste `poll_interval`, `verify_ssl`, `timeout` e `webhook_url`.

6. Garanta que os certificados `.pem` dos clientes que utilizarem o modo por certificado estejam acessíveis no servidor. Para cadastros que operarão somente com a procuração do contador, basta configurar o token padrão ou individual conforme os passos anteriores.

## Banco de dados

O monitor cria automaticamente o arquivo SQLite definido por `--database` (padrão `monitor.db`) com as tabelas `clients` e `events`. Faça backup periódico desse arquivo se precisar de histórico.

## Cadastro de clientes

Utilize o comando `add-client` para registrar cada contribuinte, escolhendo o modo de autenticação mais adequado ao cenário.

### Exemplo com certificado do contribuinte

```bash
python main.py add-client \
  --database monitor.db \
  12345678000190 "Empresa Exemplo Ltda" PJ \
  /caminho/certificados/empresa.pem \
  /caminho/certificados/empresa-key.pem \
  --certificate-password "senhaOpcional" \
  --procuracao-token "tokenOpcional"
```

### Exemplo usando apenas a procuração do contador

```bash
python main.py add-client \
  --database monitor.db \
  98765432100 "Contribuinte via Procuração" PF \
  --auth-mode procuracao \
  --procuracao-token "tokenEspecificoOpcional"
```

No modo `procuracao`, os campos de certificado e chave são opcionais e podem ser omitidos. Se nenhum token específico for informado, o sistema utilizará o valor padrão configurado em `monitor_config.json`.

Para listar os clientes cadastrados:

```bash
python main.py list-clients --database monitor.db
```

### Atualização, remoção e status de clientes

- Atualize informações (nome, tipo, caminhos de arquivos ou credenciais específicas):

  ```bash
  python main.py update-client \
    --database monitor.db \
    12345678000190 \
    --name "Empresa Nova" \
    --certificate /novo/caminho/cert.pem \
    --key /novo/caminho/key.pem
  ```

  Para alternar o modo de autenticação para o uso exclusivo da procuração, execute:

  ```bash
  python main.py update-client \
    --database monitor.db \
    12345678000190 \
    --auth-mode procuracao
  ```

- Remova um cliente (os eventos associados também são excluídos):

  ```bash
  python main.py delete-client --database monitor.db 12345678000190
  ```

- Consulte o último status consolidado retornado pela API:

  ```bash
  python main.py show-status --database monitor.db 12345678000190
  ```

- Liste eventos registrados, com suporte a filtros e paginação simples:

  ```bash
  python main.py list-events --database monitor.db --document 12345678000190 --limit 20
  ```

## Execução do monitoramento

### Execução contínua

Para rodar continuamente (modo daemon simples), use:

```bash
python main.py run --database monitor.db --config monitor_config.json
```

O processo fica em loop consultando a API a cada `poll_interval` segundos, atualizando o banco e enviando alertas para o webhook (quando configurado).

### Execução de ciclo único

Se quiser executar apenas um ciclo (por exemplo, em uma pipeline agendada ou cron job), adicione `--once`:

```bash
python main.py run --database monitor.db --config monitor_config.json --once
```

Para executar o ciclo apenas para um cliente específico (útil em fluxos manuais ou integrações), informe `--client`:

```bash
python main.py run --database monitor.db --config monitor_config.json --client 12345678000190
```

## Interface web

Além da CLI, o repositório inclui um painel web completo (`webapp.py`) para cadastrar clientes, visualizar métricas consolidadas e disparar ciclos manuais do monitor.

1. Configure as variáveis de ambiente (use o mesmo banco e configuração apontados pelo monitor):
   ```bash
   export MONITOR_DATABASE=monitor.db
   export MONITOR_CONFIG=/caminho/para/monitor_config.json
   export FLASK_SECRET_KEY="uma-string-aleatoria"
   ```
2. Inicie o servidor:
   ```bash
   python webapp.py
   ```
3. Acesse `http://localhost:8000` para visualizar clientes, cadastrar novos, editar registros, remover cadastros, examinar o
   histórico de eventos e executar ciclos sob demanda (globais ou por cliente). Caso a página inicial informe que a configuração
   não foi encontrada, verifique se `MONITOR_CONFIG` aponta para o arquivo correto e que ele está acessível.

### Recursos disponíveis no painel

- **Dashboard operacional** com contadores de clientes, eventos, últimos ciclos e destaque para clientes que precisam de nova verificação.
- **Linha do tempo dos eventos** com visualização amigável, filtros de paginação, destaque de categorias/referências e exibição do payload bruto por evento.
- **Páginas de detalhe** para cada cliente exibindo notificações mais recentes, obrigações, metadados retornados pela API e ações rápidas (rodar ciclo, editar, remover).
- **Formulários estruturados** para cadastro e edição, incluindo seleção do modo de autenticação e dicas operacionais ao lado dos campos obrigatórios.
- **Estilo responsivo** baseado em Bulma com personalizações próprias (`static/css/app.css`) para cards, timeline e blocos de informação.

O painel reutiliza o mesmo banco SQLite e respeita as configurações do arquivo JSON. Certifique-se de que o processo tenha acesso
aos certificados dos clientes que utilizarem esse modo e aos tokens de procuração necessários.

## Logs e observabilidade

Os logs são enviados para `stdout` com nível `INFO` por padrão. Para aumentar a verbosidade, ajuste a variável de ambiente `PYTHONLOGLEVEL` ou modifique `logging.basicConfig` em `main.py`.

## Deploy sugerido

- Configure um serviço do sistema (ex.: `systemd`) para iniciar o comando contínuo após o boot.
- Armazene os certificados (quando aplicável) em diretório protegido e mantenha os tokens de procuração em local seguro, com permissões restritas ao usuário que executa o monitor.
- Utilize `venv` dedicado para isolar as dependências Python.

## Suporte

Em caso de dúvidas, entre em contato com o time responsável pela API proprietária ou adapte o código para atender às particularidades do seu escritório.
