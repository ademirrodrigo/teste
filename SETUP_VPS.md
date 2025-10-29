# Guia de Instalação na VPS - Monitor eCAC

Este guia irá ajudá-lo a configurar o sistema de monitoramento eCAC na sua VPS.

## Pré-requisitos

- VPS com Ubuntu 20.04+ ou Debian 11+
- Acesso root ou sudo
- Python 3.9 ou superior
- Pelo menos 1GB de RAM
- 10GB de espaço em disco

## Passo 1: Preparação do Servidor

### 1.1 Atualizar o sistema

```bash
sudo apt update && sudo apt upgrade -y
```

### 1.2 Instalar dependências

```bash
sudo apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx
```

### 1.3 Criar usuário para a aplicação (recomendado)

```bash
sudo adduser --system --group --home /opt/ecac ecac
sudo mkdir -p /opt/ecac
sudo chown ecac:ecac /opt/ecac
```

## Passo 2: Instalação da Aplicação

### 2.1 Clonar ou copiar o projeto

Se você já tem os arquivos:
```bash
sudo cp -r /caminho/do/projeto/* /opt/ecac/
```

Ou via git:
```bash
cd /opt/ecac
sudo -u ecac git clone <seu-repositorio> .
```

### 2.2 Criar ambiente virtual

```bash
cd /opt/ecac
sudo -u ecac python3 -m venv venv
sudo -u ecac ./venv/bin/pip install --upgrade pip
sudo -u ecac ./venv/bin/pip install -r requirements.txt
```

## Passo 3: Configuração

### 3.1 Configurar a API

```bash
cd /opt/ecac
sudo -u ecac cp api_config.example.json api_config.json
sudo -u ecac nano api_config.json
```

Edite os seguintes campos:
- `contador_document`: Seu CPF/CNPJ
- `default_procuracao_token`: Token do eCAC
- `admin_token`: **TROQUE por um token forte** (use: `openssl rand -hex 32`)

### 3.2 Configurar o Monitor

```bash
sudo -u ecac cp monitor_config.example.json monitor_config.json
sudo -u ecac nano monitor_config.json
```

Ajuste:
- `api_base_url`: `http://localhost:5000`
- `contador_document`: Mesmo valor do api_config.json
- `procuracao_token`: Mesmo token padrão
- `webhook_url`: URL do seu sistema de alertas (opcional)

### 3.3 Criar diretórios de dados

```bash
sudo mkdir -p /opt/ecac/data/certificates
sudo mkdir -p /opt/ecac/logs
sudo chown -R ecac:ecac /opt/ecac/data /opt/ecac/logs
sudo chmod 700 /opt/ecac/data/certificates
```

## Passo 4: Configurar Serviços Systemd

### 4.1 Serviço da API

```bash
sudo nano /etc/systemd/system/ecac-api.service
```

Cole o conteúdo:
```ini
[Unit]
Description=eCAC Monitor API Server
After=network.target

[Service]
Type=simple
User=ecac
Group=ecac
WorkingDirectory=/opt/ecac
Environment="API_CONFIG=/opt/ecac/api_config.json"
Environment="API_DATABASE=/opt/ecac/data/api_data.db"
ExecStart=/opt/ecac/venv/bin/python /opt/ecac/api_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 4.2 Serviço do Monitor

```bash
sudo nano /etc/systemd/system/ecac-monitor.service
```

Cole o conteúdo:
```ini
[Unit]
Description=eCAC Monitor Background Service
After=network.target ecac-api.service
Requires=ecac-api.service

[Service]
Type=simple
User=ecac
Group=ecac
WorkingDirectory=/opt/ecac
ExecStart=/opt/ecac/venv/bin/python /opt/ecac/main.py run --database /opt/ecac/data/monitor.db --config /opt/ecac/monitor_config.json
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 4.3 Serviço da WebApp

```bash
sudo nano /etc/systemd/system/ecac-webapp.service
```

Cole o conteúdo:
```ini
[Unit]
Description=eCAC Monitor Web Interface
After=network.target ecac-api.service
Requires=ecac-api.service

[Service]
Type=simple
User=ecac
Group=ecac
WorkingDirectory=/opt/ecac
Environment="MONITOR_DATABASE=/opt/ecac/data/monitor.db"
Environment="MONITOR_CONFIG=/opt/ecac/monitor_config.json"
Environment="FLASK_SECRET_KEY=GERE_UMA_CHAVE_ALEATORIA_AQUI"
ExecStart=/opt/ecac/venv/bin/python /opt/ecac/webapp.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**IMPORTANTE**: Gere uma chave secreta:
```bash
openssl rand -hex 32
```
E substitua `GERE_UMA_CHAVE_ALEATORIA_AQUI` pelo resultado.

## Passo 5: Configurar Nginx (Reverse Proxy)

```bash
sudo nano /etc/nginx/sites-available/ecac
```

Cole:
```nginx
server {
    listen 80;
    server_name seu-dominio.com;  # Troque pelo seu domínio ou IP

    # API Server
    location /api/ {
        proxy_pass http://localhost:5000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Web Interface
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Increase timeouts for long-running requests
    proxy_connect_timeout 300;
    proxy_send_timeout 300;
    proxy_read_timeout 300;
    send_timeout 300;
}
```

Ativar o site:
```bash
sudo ln -s /etc/nginx/sites-available/ecac /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Passo 6: Configurar SSL/HTTPS (Recomendado)

```bash
sudo certbot --nginx -d seu-dominio.com
```

Siga as instruções do Certbot para configurar HTTPS automaticamente.

## Passo 7: Iniciar os Serviços

```bash
# Recarregar systemd
sudo systemctl daemon-reload

# Habilitar serviços para iniciar no boot
sudo systemctl enable ecac-api
sudo systemctl enable ecac-monitor
sudo systemctl enable ecac-webapp

# Iniciar os serviços
sudo systemctl start ecac-api
sleep 5  # Aguardar API iniciar
sudo systemctl start ecac-monitor
sudo systemctl start ecac-webapp
```

## Passo 8: Verificar Status

```bash
# Verificar se os serviços estão rodando
sudo systemctl status ecac-api
sudo systemctl status ecac-monitor
sudo systemctl status ecac-webapp

# Ver logs em tempo real
sudo journalctl -u ecac-api -f
sudo journalctl -u ecac-monitor -f
sudo journalctl -u ecac-webapp -f
```

## Passo 9: Cadastrar Primeiro Cliente

### Via CLI:

```bash
sudo -u ecac /opt/ecac/venv/bin/python /opt/ecac/main.py add-client \
  --database /opt/ecac/data/monitor.db \
  12345678000190 "Empresa Exemplo Ltda" PJ \
  --auth-mode procuracao \
  --procuracao-token "token-opcional"
```

### Via API:

```bash
curl -X POST http://localhost:5000/admin/clients \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: SEU_TOKEN_ADMIN" \
  -d '{
    "document": "12345678000190",
    "name": "Empresa Exemplo Ltda",
    "client_type": "PJ",
    "procuracao_token": "token-opcional"
  }'
```

### Via Interface Web:

Acesse `http://seu-dominio.com` e use os formulários de cadastro.

## Gerenciamento

### Parar todos os serviços:
```bash
sudo systemctl stop ecac-webapp ecac-monitor ecac-api
```

### Reiniciar todos os serviços:
```bash
sudo systemctl restart ecac-api && \
sudo systemctl restart ecac-monitor && \
sudo systemctl restart ecac-webapp
```

### Ver logs:
```bash
# Últimas 100 linhas
sudo journalctl -u ecac-api -n 100
sudo journalctl -u ecac-monitor -n 100
sudo journalctl -u ecac-webapp -n 100
```

### Backup dos dados:
```bash
# Criar backup
sudo tar -czf /root/ecac-backup-$(date +%Y%m%d).tar.gz \
  /opt/ecac/data/ \
  /opt/ecac/api_config.json \
  /opt/ecac/monitor_config.json

# Restaurar backup
sudo tar -xzf /root/ecac-backup-YYYYMMDD.tar.gz -C /
sudo chown -R ecac:ecac /opt/ecac/data
```

## Firewall (Opcional)

Se estiver usando UFW:

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

## Troubleshooting

### Serviço não inicia:
```bash
sudo journalctl -u ecac-api -xe
```

### Permissões incorretas:
```bash
sudo chown -R ecac:ecac /opt/ecac
```

### Banco de dados corrompido:
```bash
sudo -u ecac sqlite3 /opt/ecac/data/monitor.db ".backup /opt/ecac/data/monitor.db.bak"
```

### Atualizar o código:
```bash
cd /opt/ecac
sudo -u ecac git pull
sudo systemctl restart ecac-api ecac-monitor ecac-webapp
```

## Monitoramento de Recursos

### Verificar uso de CPU/RAM:
```bash
ps aux | grep python
top -u ecac
```

### Verificar espaço em disco:
```bash
du -sh /opt/ecac/data/
df -h
```

## Segurança

1. **Nunca exponha a porta 5000 diretamente** - sempre use Nginx como proxy
2. **Use HTTPS em produção** - Configure SSL com Certbot
3. **Mantenha tokens seguros** - Use `chmod 600` nos arquivos de configuração
4. **Backup regular** - Automatize backups dos bancos de dados
5. **Atualizações** - Mantenha o sistema e dependências atualizados

## Portas Utilizadas

- **5000**: API Server (interno apenas)
- **8000**: WebApp (interno apenas)
- **80**: HTTP (Nginx)
- **443**: HTTPS (Nginx)

## Próximos Passos

1. Configure certificados digitais em `/opt/ecac/data/certificates/` para clientes que usarão esse modo
2. Configure o webhook_url para receber alertas
3. Ajuste o `poll_interval` conforme necessário (padrão: 900 segundos = 15 minutos)
4. Configure monitoramento externo (uptime, logs, métricas)

## Suporte

Para dúvidas ou problemas, consulte os logs e a documentação do projeto no README.md.
