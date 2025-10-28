# Coletor Fiscal v3.2 SaaS-Ready

Sistema completo para coleta automatizada de documentos fiscais eletrônicos (NF-e e NFC-e), preparado para execução em ambientes Windows ou Linux.

## Visão Geral
- **Backend:** Python + SQLAlchemy + SQLite
- **Painel:** Streamlit rodando na porta 8501
- **Coletas:**
  - NF-e via WebService `NFeDistribuicaoDFe` utilizando certificado A1 (arquivo `.pfx`)
  - NFC-e via raspagem pública no portal da SEFAZ-GO
- **Estrutura de pastas:**
  - `app/`: código backend e serviços
  - `web/`: painel Streamlit
  - `certs/`: certificados digitais A1 (`CNPJ.pfx`)
  - `data/xmls`: armazenamento dos XMLs coletados
  - `data/html`: armazenamento dos HTMLs da NFC-e
  - `logs/`: registros de execução

> ⚠️ **Importante:** As chamadas reais para os serviços da SEFAZ estão comentadas. Para ativá-las basta remover os comentários indicados nos módulos `app/collectors/nfe_dfe.py` e `app/collectors/nfce_html.py`.

## Pré-requisitos
- Python 3.11+ (com Python 3.13 no Windows utilize o `lxml 5.3.x` incluído no `requirements.txt`, que já possui wheels oficiais)
- Certificados A1 no formato `.pfx` de cada empresa cadastrada
- Dependências listadas em `requirements.txt`

## Configuração Inicial
1. Copie `.env.example` para `.env` e ajuste as variáveis conforme necessário.
2. Instale as dependências utilizando um ambiente virtual:
   ```bash
   python -m venv .venv
   source .venv/bin/activate          # Linux/macOS
   .\.venv\Scripts\Activate.ps1      # Windows (PowerShell)
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```
   > 💡 **Windows 11:** Com Python 3.13 certifique-se de atualizar o `pip` (`python -m pip install --upgrade pip`) para baixar o wheel oficial do `lxml 5.3.x`. Caso utilize versões mais antigas do `lxml`, será necessário instalar o [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).
3. Execute o painel Streamlit:
   ```bash
   python -m streamlit run web/app.py --server.port 8501
   ```
   - Para alterar a porta, defina a variável de ambiente antes de executar o comando e use a sintaxe correta do seu shell:
     - **PowerShell:** ` $env:PORTA=8502 ; python -m streamlit run web/app.py --server.port $env:PORTA`
     - **Prompt (cmd.exe):** `set PORTA=8502 && python -m streamlit run web/app.py --server.port %PORTA%`
   - Ao informar a porta diretamente, utilize apenas o número (`8501`) sem o prefixo `$`.
4. Acesse `http://localhost:8501` (ou a porta configurada) e faça login com as credenciais definidas nas variáveis `WEB_USER` e `WEB_PASS`.

### Scripts rápidos para Windows
- `install.bat`: instalação padrão (cria/atualiza `.venv` e dependências).
- `force_install.bat`: reinstalação completa, removendo e recriando o ambiente virtual.
- `start.bat`: inicialização do painel Streamlit utilizando o ambiente configurado.
- `verify.bat`: verificação rápida do ambiente (versão do Python, `pip check` e compilação das pastas `app/` e `web/`).


## Cadastro de Empresas
- Utilize o painel para cadastrar cada empresa informando **Nome**, **CNPJ**, **UF** e **Senha do certificado**.
- Salve o arquivo `.pfx` correspondente na pasta `certs/` com o nome `CNPJ.pfx` (somente números).

## Coleta de Documentos
1. Selecione a empresa desejada no painel.
2. Informe opcionalmente as chaves de NFC-e (uma por linha) para raspagem pública.
3. Clique em **🔄 Coletar Agora** para executar as rotinas de coleta.
4. Os documentos são salvos nas pastas `data/xmls/<CNPJ>/` e `data/html/<CNPJ>/` e registrados no banco SQLite.

## Execução com Systemd
O script `install.sh` configura o ambiente em servidores Linux (Ubuntu) criando um serviço systemd para o painel Streamlit. Revise o arquivo antes de executar para ajustar caminhos ou usuário do serviço.

## Proxy Reverso com Nginx
O arquivo `nginx.conf` contém um exemplo de configuração para expor o painel com HTTPS usando um certificado gerenciado pelo Let's Encrypt no domínio `fiscal.goianiacontabil.com`.

## Atualização e Remoção
- `update.sh`: atualiza o código via Git e reinicia o serviço.
- `uninstall.sh`: remove o serviço systemd e opcionalmente o ambiente virtual.

## Ativando a Integração Real
- **NF-e:** Remova os comentários na função `coletar_nfe_distribuicao` para habilitar o uso do `requests_pkcs12`/`zeep` e configure o endpoint apropriado da SEFAZ.
- **NFC-e:** Habilite a requisição HTTP no módulo `coletar_nfce_publica` ajustando a URL da consulta pública.

Certifique-se de que os certificados e permissões estão válidos e que a rede do servidor possui acesso aos domínios da SEFAZ.
