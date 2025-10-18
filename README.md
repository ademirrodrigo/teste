# Monitoramento do eCAC

Este repositório contém uma ferramenta CLI em Python para monitorar periodicamente o eCAC para escritórios de contabilidade. Ela autentica usando o certificado digital de cada contribuinte (empresa ou pessoa física) ou, opcionalmente, apenas a procuração eletrônica do contador, consulta uma API proprietária e registra novos eventos em um banco SQLite, disparando alertas via webhook.

> 📘 Precisa de um roteiro completo? Consulte o [Manual Operacional Passo a Passo](MANUAL_OPERACIONAL.md) para executar um ambiente real utilizando o CPF do contador (ex.: `97121215187`) e/ou certificados das empresas.
>
> 🎨 Quer transformar a documentação em uma apresentação estilo Canva? Utilize o [Guia Visual Canva-Style](MANUAL_CANVA.md) com páginas prontas para instalação e uso.
>
> 📦 Precisa baixar tudo em ordem? Consulte a [sequência sugerida de arquivos](sequencia_arquivos.txt) antes da implantação.

## Instalação automatizada (Windows local e VPS Linux)

Execute o instalador único incluído no repositório para preparar o ambiente em
ambas as plataformas:

```bash
python install.py
```

Também estão disponíveis scripts dedicados para cada plataforma que encapsulam
o comando acima:

- **Windows 11 (PowerShell):** `./scripts/install_windows.ps1`
- **Linux/VPS:** `bash scripts/install_linux.sh`

O script cria um ambiente virtual em `.venv`, instala todas as dependências e
gera automaticamente `monitor_config.json` e `api_config.json` a partir dos
modelos. Ao final, ele exibe os comandos corretos para ativar o ambiente e
iniciar a API (`api_server.py`), o painel web (`webapp.py`) e o monitor CLI
(`main.py`).

Caso precise repetir a instalação em um servidor novo, basta copiar o repositório
e rodar novamente `python install.py`. Se já existir um ambiente virtual ou
arquivos de configuração personalizados, eles são preservados.

## Requisitos

- Python 3.9 ou superior
- Bibliotecas [`requests`](https://pypi.org/project/requests/) e [`Flask`](https://flask.palletsprojects.com/)
- Certificados digitais (`.pem`) dos clientes que usarão o modo por certificado e procuração eletrônica ativa para o contador
- API própria do escritório capaz de autenticar e consultar notificações/obrigações do eCAC

### Preparando o certificado do contador com procurações

Caso utilize o certificado digital do contador para acessar o eCAC em nome dos clientes que lhe concederam procurações, converta
 o arquivo `.pfx` ou `.p12` para o par `.pem` esperado pelo monitor e mantenha-o em local seguro:

```bash
openssl pkcs12 -in certificado-contador.pfx -out contador.pem -clcerts -nodes
openssl pkcs12 -in certificado-contador.pfx -out contador-key.pem -nocerts -nodes
chmod 600 contador.pem contador-key.pem
```

Armazene os caminhos resultantes para informar no cadastro do cliente que usará o modo `certificate`. Caso o fluxo seja via pro
curação (sem certificado individual), basta garantir que o campo `procuracao_token` em `monitor_config.json` contenha o token pa
drão obtido no eCAC para o CPF `97121215187` (ou o documento do seu contador).

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

5. Atualize `monitor_config.json` (copiado de `monitor_config.example.json`) apontando `api_base_url` para `http://localhost:5000`, definindo o mesmo `contador_document` e o token padrão desejado no campo `procuracao_token`. Opcionalmente ajuste `poll_interval`, `verify_ssl`, `timeout` e `webhook_url`.

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
4. Se o navegador não conectar, confirme se o processo `python webapp.py` segue ativo, se não houve erros no terminal e se a
   porta `8000` está liberada no firewall local.

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
