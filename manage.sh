#!/bin/bash
# Script de Gerenciamento - Monitor eCAC
# Facilita operações comuns de manutenção

INSTALL_DIR="/opt/ecac"
APP_USER="ecac"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Verificar se está rodando como root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}ERRO: Este script precisa ser executado como root (use sudo)${NC}"
        exit 1
    fi
}

# Mostrar menu
show_menu() {
    clear
    echo -e "${BLUE}=========================================="
    echo "Monitor eCAC - Menu de Gerenciamento"
    echo -e "==========================================${NC}"
    echo ""
    echo "1)  Ver status de todos os serviços"
    echo "2)  Iniciar todos os serviços"
    echo "3)  Parar todos os serviços"
    echo "4)  Reiniciar todos os serviços"
    echo ""
    echo "5)  Ver logs da API (tempo real)"
    echo "6)  Ver logs do Monitor (tempo real)"
    echo "7)  Ver logs da WebApp (tempo real)"
    echo ""
    echo "8)  Listar clientes cadastrados"
    echo "9)  Adicionar novo cliente"
    echo "10) Remover cliente"
    echo ""
    echo "11) Fazer backup dos dados"
    echo "12) Restaurar backup"
    echo ""
    echo "13) Atualizar código (git pull)"
    echo "14) Verificar espaço em disco"
    echo "15) Verificar uso de recursos"
    echo ""
    echo "16) Abrir configuração da API"
    echo "17) Abrir configuração do Monitor"
    echo ""
    echo "18) Testar conectividade dos serviços"
    echo "19) Limpar logs antigos"
    echo ""
    echo "0)  Sair"
    echo ""
    echo -n "Escolha uma opção: "
}

# Status dos serviços
service_status() {
    echo -e "${BLUE}=== Status dos Serviços ===${NC}"
    echo ""
    systemctl status ecac-api --no-pager -l | head -10
    echo ""
    systemctl status ecac-monitor --no-pager -l | head -10
    echo ""
    systemctl status ecac-webapp --no-pager -l | head -10
    echo ""
    read -p "Pressione ENTER para continuar..."
}

# Iniciar serviços
start_services() {
    echo -e "${GREEN}Iniciando serviços...${NC}"
    systemctl start ecac-api
    sleep 3
    systemctl start ecac-monitor
    systemctl start ecac-webapp
    echo -e "${GREEN}Serviços iniciados!${NC}"
    sleep 2
}

# Parar serviços
stop_services() {
    echo -e "${YELLOW}Parando serviços...${NC}"
    systemctl stop ecac-webapp
    systemctl stop ecac-monitor
    systemctl stop ecac-api
    echo -e "${GREEN}Serviços parados!${NC}"
    sleep 2
}

# Reiniciar serviços
restart_services() {
    echo -e "${YELLOW}Reiniciando serviços...${NC}"
    systemctl restart ecac-api
    sleep 3
    systemctl restart ecac-monitor
    systemctl restart ecac-webapp
    echo -e "${GREEN}Serviços reiniciados!${NC}"
    sleep 2
}

# Ver logs
view_logs() {
    local service=$1
    echo -e "${BLUE}Logs do serviço $service (Ctrl+C para sair)${NC}"
    echo ""
    sleep 2
    journalctl -u "$service" -f
}

# Listar clientes
list_clients() {
    echo -e "${BLUE}=== Clientes Cadastrados ===${NC}"
    echo ""
    sudo -u "$APP_USER" "$INSTALL_DIR/venv/bin/python" "$INSTALL_DIR/main.py" \
        list-clients --database "$INSTALL_DIR/data/monitor.db"
    echo ""
    read -p "Pressione ENTER para continuar..."
}

# Adicionar cliente
add_client() {
    clear
    echo -e "${BLUE}=== Adicionar Novo Cliente ===${NC}"
    echo ""

    read -p "Documento (CPF/CNPJ sem pontos): " DOCUMENT
    read -p "Nome do cliente: " NAME
    read -p "Tipo (PF/PJ): " TYPE

    echo ""
    echo "Modo de autenticação:"
    echo "1) Procuração (apenas token)"
    echo "2) Certificado digital"
    read -p "Escolha (1 ou 2): " AUTH_MODE

    if [ "$AUTH_MODE" == "1" ]; then
        read -p "Token da procuração (opcional, ENTER para usar padrão): " TOKEN

        CMD="sudo -u $APP_USER $INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py add-client \
            --database $INSTALL_DIR/data/monitor.db \
            $DOCUMENT \"$NAME\" $TYPE \
            --auth-mode procuracao"

        if [ ! -z "$TOKEN" ]; then
            CMD="$CMD --procuracao-token \"$TOKEN\""
        fi

        echo ""
        echo -e "${YELLOW}Executando: $CMD${NC}"
        eval $CMD

    elif [ "$AUTH_MODE" == "2" ]; then
        read -p "Caminho do certificado (.pem): " CERT_PATH
        read -p "Caminho da chave (.pem): " KEY_PATH
        read -p "Senha do certificado (opcional): " CERT_PASSWORD

        CMD="sudo -u $APP_USER $INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py add-client \
            --database $INSTALL_DIR/data/monitor.db \
            $DOCUMENT \"$NAME\" $TYPE \
            \"$CERT_PATH\" \"$KEY_PATH\""

        if [ ! -z "$CERT_PASSWORD" ]; then
            CMD="$CMD --certificate-password \"$CERT_PASSWORD\""
        fi

        echo ""
        echo -e "${YELLOW}Executando: $CMD${NC}"
        eval $CMD
    else
        echo -e "${RED}Opção inválida!${NC}"
    fi

    echo ""
    read -p "Pressione ENTER para continuar..."
}

# Remover cliente
remove_client() {
    clear
    echo -e "${RED}=== Remover Cliente ===${NC}"
    echo ""
    list_clients
    echo ""
    read -p "Digite o documento do cliente para remover: " DOCUMENT
    read -p "Tem certeza? (sim/não): " CONFIRM

    if [ "$CONFIRM" == "sim" ]; then
        sudo -u "$APP_USER" "$INSTALL_DIR/venv/bin/python" "$INSTALL_DIR/main.py" \
            delete-client --database "$INSTALL_DIR/data/monitor.db" "$DOCUMENT"
        echo -e "${GREEN}Cliente removido!${NC}"
    else
        echo -e "${YELLOW}Operação cancelada.${NC}"
    fi

    echo ""
    read -p "Pressione ENTER para continuar..."
}

# Fazer backup
backup_data() {
    echo -e "${BLUE}=== Backup dos Dados ===${NC}"
    echo ""

    BACKUP_DIR="/root/ecac-backups"
    mkdir -p "$BACKUP_DIR"

    BACKUP_FILE="$BACKUP_DIR/ecac-backup-$(date +%Y%m%d-%H%M%S).tar.gz"

    echo "Criando backup em: $BACKUP_FILE"
    tar -czf "$BACKUP_FILE" \
        "$INSTALL_DIR/data/" \
        "$INSTALL_DIR/api_config.json" \
        "$INSTALL_DIR/monitor_config.json"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Backup criado com sucesso!${NC}"
        echo "Arquivo: $BACKUP_FILE"
        echo "Tamanho: $(du -h $BACKUP_FILE | cut -f1)"
    else
        echo -e "${RED}Erro ao criar backup!${NC}"
    fi

    echo ""
    read -p "Pressione ENTER para continuar..."
}

# Restaurar backup
restore_backup() {
    echo -e "${YELLOW}=== Restaurar Backup ===${NC}"
    echo ""

    BACKUP_DIR="/root/ecac-backups"

    if [ ! -d "$BACKUP_DIR" ]; then
        echo -e "${RED}Diretório de backups não encontrado!${NC}"
        read -p "Pressione ENTER para continuar..."
        return
    fi

    echo "Backups disponíveis:"
    ls -lh "$BACKUP_DIR"/*.tar.gz 2>/dev/null

    echo ""
    read -p "Digite o caminho completo do backup: " BACKUP_FILE

    if [ ! -f "$BACKUP_FILE" ]; then
        echo -e "${RED}Arquivo não encontrado!${NC}"
        read -p "Pressione ENTER para continuar..."
        return
    fi

    echo ""
    echo -e "${RED}ATENÇÃO: Esta operação irá sobrescrever os dados atuais!${NC}"
    read -p "Tem certeza? (sim/não): " CONFIRM

    if [ "$CONFIRM" == "sim" ]; then
        stop_services
        tar -xzf "$BACKUP_FILE" -C /
        chown -R "$APP_USER:$APP_USER" "$INSTALL_DIR/data"
        start_services
        echo -e "${GREEN}Backup restaurado com sucesso!${NC}"
    else
        echo -e "${YELLOW}Operação cancelada.${NC}"
    fi

    echo ""
    read -p "Pressione ENTER para continuar..."
}

# Atualizar código
update_code() {
    echo -e "${BLUE}=== Atualizar Código ===${NC}"
    echo ""

    cd "$INSTALL_DIR"

    if [ -d ".git" ]; then
        echo "Atualizando via git..."
        sudo -u "$APP_USER" git pull

        echo ""
        echo "Atualizando dependências..."
        sudo -u "$APP_USER" ./venv/bin/pip install -r requirements.txt

        echo ""
        read -p "Deseja reiniciar os serviços? (s/n): " RESTART

        if [ "$RESTART" == "s" ]; then
            restart_services
        fi
    else
        echo -e "${RED}Repositório git não encontrado!${NC}"
        echo "Para atualizar manualmente, copie os novos arquivos para $INSTALL_DIR"
    fi

    echo ""
    read -p "Pressione ENTER para continuar..."
}

# Verificar espaço em disco
check_disk_space() {
    echo -e "${BLUE}=== Espaço em Disco ===${NC}"
    echo ""
    df -h
    echo ""
    echo "Uso do diretório de dados:"
    du -sh "$INSTALL_DIR/data/"
    echo ""
    echo "Detalhamento:"
    du -sh "$INSTALL_DIR/data/"*
    echo ""
    read -p "Pressione ENTER para continuar..."
}

# Verificar recursos
check_resources() {
    echo -e "${BLUE}=== Uso de Recursos ===${NC}"
    echo ""
    echo "Processos Python:"
    ps aux | grep python | grep -v grep
    echo ""
    echo "Memória:"
    free -h
    echo ""
    echo "CPU:"
    top -bn1 | head -15
    echo ""
    read -p "Pressione ENTER para continuar..."
}

# Abrir configurações
edit_api_config() {
    nano "$INSTALL_DIR/api_config.json"
    read -p "Deseja reiniciar os serviços para aplicar mudanças? (s/n): " RESTART
    if [ "$RESTART" == "s" ]; then
        restart_services
    fi
}

edit_monitor_config() {
    nano "$INSTALL_DIR/monitor_config.json"
    read -p "Deseja reiniciar os serviços para aplicar mudanças? (s/n): " RESTART
    if [ "$RESTART" == "s" ]; then
        restart_services
    fi
}

# Testar conectividade
test_connectivity() {
    echo -e "${BLUE}=== Teste de Conectividade ===${NC}"
    echo ""

    echo "Testando API (porta 5000)..."
    curl -s http://localhost:5000/ | head -5
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ API respondendo${NC}"
    else
        echo -e "${RED}✗ API não responde${NC}"
    fi

    echo ""
    echo "Testando WebApp (porta 8000)..."
    curl -s http://localhost:8000/ | head -5
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ WebApp respondendo${NC}"
    else
        echo -e "${RED}✗ WebApp não responde${NC}"
    fi

    echo ""
    echo "Testando Nginx (porta 80)..."
    curl -s http://localhost/ | head -5
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Nginx respondendo${NC}"
    else
        echo -e "${RED}✗ Nginx não responde${NC}"
    fi

    echo ""
    read -p "Pressione ENTER para continuar..."
}

# Limpar logs antigos
clean_old_logs() {
    echo -e "${BLUE}=== Limpar Logs Antigos ===${NC}"
    echo ""

    echo "Logs atuais:"
    journalctl --disk-usage

    echo ""
    read -p "Deseja limpar logs com mais de 7 dias? (s/n): " CONFIRM

    if [ "$CONFIRM" == "s" ]; then
        journalctl --vacuum-time=7d
        echo -e "${GREEN}Logs antigos removidos!${NC}"
    else
        echo -e "${YELLOW}Operação cancelada.${NC}"
    fi

    echo ""
    read -p "Pressione ENTER para continuar..."
}

# Loop principal
main() {
    check_root

    while true; do
        show_menu
        read option

        case $option in
            1) service_status ;;
            2) start_services ;;
            3) stop_services ;;
            4) restart_services ;;
            5) view_logs "ecac-api" ;;
            6) view_logs "ecac-monitor" ;;
            7) view_logs "ecac-webapp" ;;
            8) list_clients ;;
            9) add_client ;;
            10) remove_client ;;
            11) backup_data ;;
            12) restore_backup ;;
            13) update_code ;;
            14) check_disk_space ;;
            15) check_resources ;;
            16) edit_api_config ;;
            17) edit_monitor_config ;;
            18) test_connectivity ;;
            19) clean_old_logs ;;
            0)
                echo -e "${GREEN}Saindo...${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Opção inválida!${NC}"
                sleep 1
                ;;
        esac
    done
}

# Executar
main
