# Arquitetura Profissional de Automação e-CAC (Receita Federal)

Base inicial para automação resiliente do e-CAC com **Python + Playwright + certificado A1 (.pfx)**, preparada para operação multi-tenant, processamento assíncrono e escalabilidade horizontal.

## Stack
- FastAPI (API de orquestração)
- Playwright (automação web, sem Selenium)
- Celery + Redis (filas, retries, isolamento de workers)
- PostgreSQL (persistência relacional)
- Cache inteligente em Redis
- Logging estruturado (JSON via structlog)
- Docker Compose (ambiente local e base para produção)

## Estrutura solicitada

```text
ecac_automation/
  auth/
  browser/
  parser/
  services/
  workers/
  database/
  api/
  observability/
  core/
```

## Fluxo detalhado
1. **API recebe requisição** de login/extrator com `tenant_id`.
2. **Task assíncrona** é enfileirada no Celery (`auth` ou `extract`).
3. Worker de autenticação executa Playwright:
   - abre gov.br/e-CAC,
   - tenta login via certificado digital,
   - detecta sinais de CAPTCHA,
   - persiste `storage_state` no Redis para reutilização.
4. Worker de extração reutiliza sessão persistida e processa HTML.
5. Parser desacoplado transforma HTML em payload estruturado.
6. Cache inteligente evita parse repetido (hash por conteúdo + tenant).
7. Eventos e erros são registrados com logs estruturados.

## Módulos principais
- `auth/certificate_loader.py`: carregamento de certificado `.pfx` por tenant.
- `browser/playwright_client.py`: automação Playwright e fluxo de login.
- `browser/session_store.py`: sessão persistente no Redis com TTL.
- `parser/base.py` + `parser/fiscal_parser.py`: parser desacoplado.
- `services/ecac_service.py`: orquestra login, sessão e extração.
- `workers/tasks.py`: retries automáticos com backoff.
- `api/routes.py`: endpoints para enfileirar jobs.
- `observability/logging.py`: logging JSON padronizado.

## Multi-tenant
- Todo fluxo utiliza `tenant_id`.
- Sessões e cache são namespaced por tenant no Redis.
- Certificados separados por arquivo (`/app/certs/<tenant_id>.pfx`).
- Banco preparado para particionar dados por tenant.

## Execução com Docker
```bash
docker compose up --build
```

Serviços:
- `api` (FastAPI)
- `worker-auth` (fila de autenticação)
- `worker-extract` (fila de extração)
- `redis`
- `db` (PostgreSQL)

## Pontos críticos (produção)
1. **Login com certificado no navegador**: em vários ambientes o seletor de certificado é mediado pelo SO; é necessário hardening por ambiente (Linux headful, navegador persistente, container com suporte apropriado).
2. **CAPTCHA / anti-bot**: implementar estratégia híbrida (human-in-the-loop, solver externo opcional, fallback manual).
3. **Mudanças no gov.br/e-CAC**: usar Page Objects, seletores resilientes, feature flags e monitoramento de falhas por etapa.
4. **Segurança de segredo**: senha de certificado em cofre (Vault/Secrets Manager), nunca em texto puro.
5. **Observabilidade**: métricas (Prometheus), tracing (OpenTelemetry) e alertas por taxa de erro/retry.
6. **Compliance**: LGPD, trilha de auditoria, segregação de dados por tenant e criptografia em repouso/trânsito.

## Próximos passos recomendados
- Adicionar Alembic para migrations.
- Implementar persistência de sessão também no PostgreSQL (backup do Redis).
- Adotar circuit breaker e timeout budget por etapa.
- Criar suíte de testes com mocking de Playwright + contract tests de parser.
- Adicionar endpoint de health/readiness/liveness.
