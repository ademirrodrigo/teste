# Coletor Fiscal v3.2 SaaS-Ready

Plataforma para coleta automatizada de documentos fiscais eletrônicos (NF-e e NFC-e) com backend Python, banco SQLite e painel Streamlit. A versão v3.2 foi reconstruída para operar de forma consistente em contêineres Docker, mantendo scripts auxiliares para instalações tradicionais.

## Visão Geral
- **Backend:** Python + SQLAlchemy + SQLite
- **Painel:** Streamlit executando na porta 8501
- **Coletas:**
  - NF-e via WebService `NFeDistribuicaoDFe` (integração real pronta e comentada)
  - NFC-e via raspagem pública no portal da SEFAZ-GO (requisições comentadas por padrão)
- **Estrutura de pastas:**
  - `app/`: serviços, models e utilitários
  - `web/`: aplicativo Streamlit com login, cadastro de empresas e orquestração da coleta
  - `certs/`: certificados digitais A1 (`CNPJ.pfx`)
  - `data/xmls` e `data/html`: armazenamento dos documentos coletados
  - `logs/`: registros de execução

> ⚠️ **Integrações reais**: Toda chamada direta à SEFAZ permanece comentada. Basta remover os comentários sinalizados nos módulos de coleta para ativar os fluxos produtivos.

## Requisitos
- Docker 24+ e Docker Compose Plugin (recomendado)
- Certificados A1 (arquivo `.pfx`) para cada empresa cadastrada
- Para instalação manual: Python 3.11+ com `pip`

## Configuração do Ambiente
1. Duplique `.env.example` para `.env` e ajuste as variáveis desejadas.
2. Garanta que as pastas `certs/`, `data/xmls`, `data/html` e `logs/` estejam criadas (o sistema fará isso automaticamente ao iniciar).

Variáveis principais disponíveis no `.env`:

| Variável | Descrição |
| --- | --- |
| `PORTA` | Porta exposta do Streamlit (default `8501`) |
| `STREAMLIT_ADDRESS` | Endereço de bind do servidor (default `0.0.0.0`) |
| `WEB_USER` / `WEB_PASS` | Credenciais básicas do painel |
| `DATABASE_URL` | URL alternativa para o banco (caso não queira o SQLite padrão) |

## Execução com Docker (recomendado)
```bash
docker compose up -d --build
```

O serviço ficará disponível em `http://localhost:8501` (ou na porta configurada em `PORTA`). Os volumes montados garantem persistência local dos certificados, XMLs/HTML e logs.

Para interromper:
```bash
docker compose down
```

### Atualização no Docker
```bash
docker compose pull
docker compose up -d --build
```

## Instalação Manual (Linux)
Os scripts originais continuam disponíveis para quem preferir instalações tradicionais.

```bash
./install.sh        # cria .venv, instala dependências e configura systemd
./update.sh         # atualiza o código e reinicia o serviço
./uninstall.sh      # remove o serviço e opcionalmente o ambiente virtual
```

> Antes de rodar `install.sh`, certifique-se de definir as variáveis necessárias em `.env`.

## Instalação Manual (Windows)
Scripts `.bat` mantidos para conveniência:

- `install.bat`: configuração padrão com ambiente virtual
- `force_install.bat`: reinstalação completa do ambiente virtual
- `start.bat`: inicializa o painel Streamlit (modo manual)
- `verify.bat`: valida versões de Python, dependências e compilação do código

## Operação do Painel
1. Acesse o painel e faça login com `WEB_USER`/`WEB_PASS`.
2. Cadastre as empresas informando **Nome**, **CNPJ**, **UF** e **Senha do certificado**.
3. Posicione o certificado em `certs/<CNPJ>.pfx`.
4. Informe, se desejar, chaves de NFC-e (uma por linha).
5. Clique em **🔄 Coletar Agora**.
6. Os documentos ficam registrados no SQLite e armazenados nas pastas `data/xmls/<CNPJ>/` e `data/html/<CNPJ>/`.

## Ativando Integrações Reais
- **NF-e (WebService):** Habilite o trecho comentado em `app/collectors/nfe_dfe.py` para usar `requests_pkcs12` + `zeep` contra o endpoint oficial da SEFAZ. Ajuste o `tpAmb`, `cUFAutor` e endpoints conforme o ambiente.
- **NFC-e (Scraping):** Ative o bloco comentado em `app/collectors/nfce_html.py` que realiza o GET na consulta pública da SEFAZ-GO e persiste o HTML retornado.

Certifique-se de que os certificados, permissões de rede e configurações de proxy estejam corretos antes de rodar em produção.

## Estrutura do Código
- `app/models.py`: modelos `Empresa` e `Documento` com SQLAlchemy
- `app/services/coleta.py`: orquestra as rotinas de coleta
- `app/utils/`: utilitários para certificados, CNPJ e logging
- `web/app.py`: painel Streamlit com autenticação, seleção de empresa e gatilho de coleta

## Testes Rápidos
Para garantir que o código está sintaticamente correto:
```bash
python -m compileall app web
```

No Docker o comando pode ser executado via `docker compose run --rm coletor python -m compileall app web`.

---
Sistema pronto para operação segura em VPS Ubuntu, Windows 11 ou ambientes Docker orquestrados.
