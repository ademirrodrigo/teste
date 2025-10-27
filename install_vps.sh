#!/bin/bash
# Script de Instalação Automatizada - Monitor eCAC
# Este script configura o ambiente completo na VPS

set -e  # Para na primeira falha

echo "=========================================="
echo "Instalação do Monitor eCAC na VPS"
echo "=========================================="
echo ""

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then
    echo "ERRO: Este script precisa ser executado como root (use sudo)"
    exit 1
fi

# Variáveis configuráveis
INSTALL_DIR="/opt/ecac"
APP_USER="ecac"
APP_GROUP="ecac"

echo "📦 Passo 1: Atualizando sistema..."
apt update
apt upgrade -y

echo ""
echo "📦 Passo 2: Instalando dependências..."
apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx sqlite3

echo ""
echo "👤 Passo 3: Criando usuário da aplicação..."
if ! id "$APP_USER" &>/dev/null; then
    adduser --system --group --home "$INSTALL_DIR" "$APP_USER"
    echo "Usuário $APP_USER criado."
else
    echo "Usuário $APP_USER já existe."
fi

echo ""
echo "📁 Passo 4: Criando estrutura de diretórios..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/data/certificates"
mkdir -p "$INSTALL_DIR/logs"

# Copiar arquivos do projeto
echo ""
echo "📋 Passo 5: Copiando arquivos do projeto..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
    echo "Copiando de $SCRIPT_DIR para $INSTALL_DIR"
    cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/" 2>/dev/null || true
    # Não copiar .git se existir para evitar problemas
    rm -rf "$INSTALL_DIR/.git" 2>/dev/null || true
fi

echo ""
echo "🐍 Passo 6: Criando ambiente virtual Python..."
cd "$INSTALL_DIR"
sudo -u "$APP_USER" python3 -m venv venv
sudo -u "$APP_USER" ./venv/bin/pip install --upgrade pip
sudo -u "$APP_USER" ./venv/bin/pip install -r requirements.txt

echo ""
echo "⚙️  Passo 7: Configurando arquivos de configuração..."

# Configurar API
if [ ! -f "$INSTALL_DIR/api_config.json" ]; then
    cp "$INSTALL_DIR/api_config.example.json" "$INSTALL_DIR/api_config.json"

    # Gerar token admin aleatório
    ADMIN_TOKEN=$(openssl rand -hex 32)
    sed -i "s/troque-este-token-admin/$ADMIN_TOKEN/" "$INSTALL_DIR/api_config.json"

    echo ""
    echo "⚠️  IMPORTANTE: Token admin gerado automaticamente:"
    echo "   $ADMIN_TOKEN"
    echo "   Guarde este token em local seguro!"
    echo "   Arquivo: $INSTALL_DIR/api_config.json"
    echo ""
    read -p "Pressione ENTER para continuar..."
fi

# Configurar Monitor
if [ ! -f "$INSTALL_DIR/monitor_config.json" ]; then
    cp "$INSTALL_DIR/monitor_config.example.json" "$INSTALL_DIR/monitor_config.json"
    echo "Arquivo monitor_config.json criado. Edite conforme necessário."
fi

# Ajustar permissões
chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR"
chmod 700 "$INSTALL_DIR/data/certificates"
chmod 600 "$INSTALL_DIR/api_config.json"
chmod 600 "$INSTALL_DIR/monitor_config.json"

echo ""
echo "🔧 Passo 8: Criando serviços systemd..."

# Serviço da API
cat > /etc/systemd/system/ecac-api.service << EOF
[Unit]
Description=eCAC Monitor API Server
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$INSTALL_DIR
Environment="API_CONFIG=$INSTALL_DIR/api_config.json"
Environment="API_DATABASE=$INSTALL_DIR/data/api_data.db"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/api_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Serviço do Monitor
cat > /etc/systemd/system/ecac-monitor.service << EOF
[Unit]
Description=eCAC Monitor Background Service
After=network.target ecac-api.service
Requires=ecac-api.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py run --database $INSTALL_DIR/data/monitor.db --config $INSTALL_DIR/monitor_config.json
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Gerar chave secreta para Flask
FLASK_SECRET=$(openssl rand -hex 32)

# Serviço da WebApp
cat > /etc/systemd/system/ecac-webapp.service << EOF
[Unit]
Description=eCAC Monitor Web Interface
After=network.target ecac-api.service
Requires=ecac-api.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$INSTALL_DIR
Environment="MONITOR_DATABASE=$INSTALL_DIR/data/monitor.db"
Environment="MONITOR_CONFIG=$INSTALL_DIR/monitor_config.json"
Environment="FLASK_SECRET_KEY=$FLASK_SECRET"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/webapp.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "Serviços systemd criados."

echo ""
echo "🌐 Passo 9: Configurando Nginx..."

# Pedir domínio ou IP
read -p "Digite seu domínio ou IP público (ex: monitor.exemplo.com ou 123.45.67.89): " SERVER_NAME

if [ -z "$SERVER_NAME" ]; then
    SERVER_NAME="_"
    echo "Usando configuração padrão (qualquer host)."
fi

cat > /etc/nginx/sites-available/ecac << EOF
server {
    listen 80;
    server_name $SERVER_NAME;

    client_max_body_size 10M;

    # API Server
    location /api/ {
        proxy_pass http://localhost:5000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }

    # Web Interface
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }
}
EOF

# Ativar site
ln -sf /etc/nginx/sites-available/ecac /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Testar configuração
nginx -t

if [ $? -eq 0 ]; then
    systemctl restart nginx
    echo "Nginx configurado e reiniciado."
else
    echo "ERRO: Configuração do Nginx inválida!"
    exit 1
fi

echo ""
echo "🚀 Passo 10: Iniciando serviços..."

systemctl daemon-reload
systemctl enable ecac-api ecac-monitor ecac-webapp

systemctl start ecac-api
sleep 5  # Aguardar API iniciar

systemctl start ecac-monitor
systemctl start ecac-webapp

echo ""
echo "✅ Verificando status dos serviços..."
systemctl status ecac-api --no-pager -l | head -15
systemctl status ecac-monitor --no-pager -l | head -15
systemctl status ecac-webapp --no-pager -l | head -15

echo ""
echo "=========================================="
echo "✅ Instalação concluída!"
echo "=========================================="
echo ""
echo "📍 Informações importantes:"
echo ""
echo "   Diretório de instalação: $INSTALL_DIR"
echo "   Usuário da aplicação: $APP_USER"
echo "   Banco de dados: $INSTALL_DIR/data/"
echo ""
echo "🌐 Acesso:"
if [ "$SERVER_NAME" != "_" ]; then
    echo "   Interface Web: http://$SERVER_NAME"
    echo "   API: http://$SERVER_NAME/api"
else
    echo "   Interface Web: http://SEU_IP"
    echo "   API: http://SEU_IP/api"
fi
echo ""
echo "📝 Próximos passos:"
echo ""
echo "   1. Edite as configurações:"
echo "      sudo nano $INSTALL_DIR/api_config.json"
echo "      sudo nano $INSTALL_DIR/monitor_config.json"
echo ""
echo "   2. Configure SSL/HTTPS (recomendado):"
echo "      sudo certbot --nginx -d $SERVER_NAME"
echo ""
echo "   3. Cadastre seu primeiro cliente via web ou CLI:"
echo "      sudo -u $APP_USER $INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py add-client --help"
echo ""
echo "   4. Veja os logs:"
echo "      sudo journalctl -u ecac-api -f"
echo ""
echo "   5. Use o script de gerenciamento:"
echo "      sudo $INSTALL_DIR/manage.sh"
echo ""
echo "⚠️  Lembre-se de guardar o token admin gerado!"
echo ""
echo "📖 Documentação completa: $INSTALL_DIR/SETUP_VPS.md"
echo ""
