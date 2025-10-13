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

## Configuração da API

1. Copie o arquivo de exemplo `monitor_config.example.json` para `monitor_config.json` e edite os valores:
   - `api_base_url`: URL base da API proprietária (sem barra no final).
   - `contador_document`: CPF/CNPJ do contador com procuração.
   - `procuracao_token`: token padrão usado na autorização.
   - Opcional: `poll_interval`, `verify_ssl`, `timeout`, `webhook_url`.
2. Garanta que os certificados `.pem` dos clientes que utilizarem o modo por certificado estejam acessíveis no servidor onde o monitor rodará. Para clientes configurados apenas com procuração, assegure que o token padrão ou individual esteja válido.

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

1. Configure as variáveis de ambiente:
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
   histórico de eventos e executar ciclos sob demanda (globais ou por cliente).

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
