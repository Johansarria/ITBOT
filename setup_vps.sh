#!/bin/bash

#
# ITBOT VPS Setup Script
# Automatiza la instalación completa de ITBOT en un VPS
# Compatible con Ubuntu 20.04+, Debian 11+, CentOS 8+
#

set -e  # Exit on any error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables globales
VPS_IP="154.38.163.39"
REPO_URL="https://github.com/Johansarria/ITBOT.git"
INSTALL_DIR="ITBOT"
LOG_FILE="itbot_install.log"

# Funciones de utilidad
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}" | tee -a "$LOG_FILE"
}

# Función para detectar el sistema operativo
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$NAME
        VERSION=$VERSION_ID
    else
        error "No se pudo detectar el sistema operativo"
    fi
    
    log "Sistema detectado: $OS $VERSION"
}

# Función para verificar si el usuario tiene permisos sudo
check_sudo() {
    if ! sudo -n true 2>/dev/null; then
        error "Este script requiere permisos sudo. Ejecuta como: sudo $0"
    fi
    log "Permisos sudo verificados"
}

# Función para actualizar el sistema
update_system() {
    log "Actualizando el sistema..."
    
    if [[ $OS == *"Ubuntu"* ]] || [[ $OS == *"Debian"* ]]; then
        sudo apt update && sudo apt upgrade -y
        sudo apt install -y curl wget git unzip software-properties-common apt-transport-https ca-certificates gnupg lsb-release
    elif [[ $OS == *"CentOS"* ]] || [[ $OS == *"Red Hat"* ]]; then
        sudo yum update -y
        sudo yum install -y curl wget git unzip
    else
        warn "Sistema operativo no reconocido completamente, continuando..."
    fi
    
    log "Sistema actualizado"
}

# Función para instalar Docker
install_docker() {
    if command -v docker &> /dev/null; then
        log "Docker ya está instalado: $(docker --version)"
        return 0
    fi
    
    log "Instalando Docker..."
    
    # Descargar e instalar Docker
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    
    # Agregar usuario actual al grupo docker
    sudo usermod -aG docker $USER
    
    # Habilitar e iniciar Docker
    sudo systemctl enable docker
    sudo systemctl start docker
    
    # Verificar instalación
    if ! sudo docker --version; then
        error "Falló la instalación de Docker"
    fi
    
    log "Docker instalado correctamente"
    rm -f get-docker.sh
}

# Función para instalar Docker Compose
install_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        log "Docker Compose ya está instalado: $(docker-compose --version)"
        return 0
    fi
    
    log "Instalando Docker Compose..."
    
    # Descargar la última versión de Docker Compose
    DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
    sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    
    # Dar permisos de ejecución
    sudo chmod +x /usr/local/bin/docker-compose
    
    # Crear enlace simbólico
    sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    # Verificar instalación
    if ! docker-compose --version; then
        error "Falló la instalación de Docker Compose"
    fi
    
    log "Docker Compose instalado correctamente"
}

# Función para configurar el firewall
setup_firewall() {
    log "Configurando firewall..."
    
    if command -v ufw &> /dev/null; then
        # Ubuntu/Debian UFW
        sudo ufw --force enable
        sudo ufw allow ssh
        sudo ufw allow 8080/tcp  # Puerto web del bot
        sudo ufw allow 22/tcp    # SSH
        log "UFW configurado"
    elif command -v firewall-cmd &> /dev/null; then
        # CentOS/RHEL firewalld
        sudo systemctl enable firewalld
        sudo systemctl start firewalld
        sudo firewall-cmd --permanent --add-service=ssh
        sudo firewall-cmd --permanent --add-port=8080/tcp
        sudo firewall-cmd --reload
        log "Firewalld configurado"
    else
        warn "No se detectó firewall. Configura manualmente los puertos 22 y 8080"
    fi
}

# Función para clonar el repositorio
clone_repository() {
    log "Clonando repositorio ITBOT..."
    
    if [[ -d "$INSTALL_DIR" ]]; then
        warn "El directorio $INSTALL_DIR ya existe. Actualizando..."
        cd "$INSTALL_DIR"
        git pull origin main
        cd ..
    else
        git clone "$REPO_URL" "$INSTALL_DIR"
    fi
    
    if [[ ! -d "$INSTALL_DIR" ]]; then
        error "Falló la clonación del repositorio"
    fi
    
    log "Repositorio clonado exitosamente"
}

# Función para configurar variables de entorno
setup_environment() {
    log "Configurando variables de entorno..."
    
    cd "$INSTALL_DIR"
    
    if [[ ! -f ".env" ]]; then
        cp .env.example .env
        log "Archivo .env creado desde .env.example"
    else
        log "Archivo .env ya existe, conservando configuración actual"
    fi
    
    # Configuraciones específicas para VPS
    cat >> .env << EOF

# Configuraciones específicas para VPS
WEB_HOST=0.0.0.0
WEB_PORT=8080
PRODUCTION_MODE=false
DYNAMIC_PAIR_SELECTION_ENABLED=true

# Configuración de red para VPS
REDIS_HOST=redis
POSTGRES_HOST=db

EOF
    
    info "Configuración de .env actualizada. IMPORTANTE:"
    info "Edita el archivo .env para configurar:"
    info "- TELEGRAM_BOT_TOKEN"
    info "- TELEGRAM_CHAT_ID" 
    info "- ADMIN_TELEGRAM_ID"
    info "- BINANCE_API_KEY y BINANCE_SECRET_KEY (para trading real)"
    info "- POSTGRES_PASSWORD (usar una contraseña segura)"
    
    cd ..
}

# Función para configurar directorios de datos
setup_data_directories() {
    log "Configurando directorios de datos..."
    
    cd "$INSTALL_DIR"
    
    # Crear directorios necesarios si no existen
    mkdir -p data/analisis
    mkdir -p data/dynamic_system
    mkdir -p logs
    mkdir -p storage
    mkdir -p assets
    
    # Verificar permisos
    sudo chown -R $USER:$USER .
    chmod -R 755 data logs storage
    
    log "Directorios de datos configurados"
    cd ..
}

# Función para probar la instalación
test_installation() {
    log "Probando la instalación..."
    
    cd "$INSTALL_DIR"
    
    # Verificar que Docker y Docker Compose funcionan
    if ! docker --version; then
        error "Docker no funciona correctamente"
    fi
    
    if ! docker-compose --version; then
        error "Docker Compose no funciona correctamente"
    fi
    
    # Verificar archivos de configuración
    if [[ ! -f "docker-compose.yml" ]]; then
        error "Archivo docker-compose.yml no encontrado"
    fi
    
    if [[ ! -f ".env" ]]; then
        error "Archivo .env no encontrado"
    fi
    
    if [[ ! -f "Dockerfile" ]]; then
        error "Dockerfile no encontrado"
    fi
    
    log "Verificación de instalación completada"
    cd ..
}

# Función para mostrar información post-instalación
show_post_install_info() {
    log "==================================================="
    log "           INSTALACIÓN COMPLETADA"
    log "==================================================="
    echo ""
    info "ITBOT ha sido instalado en: $(pwd)/$INSTALL_DIR"
    echo ""
    info "PASOS SIGUIENTES:"
    echo ""
    info "1. Configurar variables de entorno:"
    echo "   cd $INSTALL_DIR"
    echo "   nano .env"
    echo ""
    info "2. Iniciar los servicios:"
    echo "   docker-compose up -d --build"
    echo ""
    info "3. Verificar que los servicios están corriendo:"
    echo "   docker-compose ps"
    echo ""
    info "4. Ver logs de los servicios:"
    echo "   docker-compose logs -f"
    echo ""
    info "5. Acceder al panel web:"
    echo "   http://$VPS_IP:8080"
    echo ""
    warn "IMPORTANTE: Configura las variables de entorno antes de iniciar!"
    warn "Especialmente TELEGRAM_BOT_TOKEN y credenciales de Binance"
    echo ""
    info "Para más información, consulta: DEPLOY_VPS.md"
    log "==================================================="
}

# Función para mostrar ayuda
show_help() {
    echo "ITBOT VPS Setup Script"
    echo ""
    echo "Uso: $0 [opciones]"
    echo ""
    echo "Opciones:"
    echo "  -h, --help              Mostrar esta ayuda"
    echo "  -v, --verbose           Modo verboso"
    echo "  --skip-docker           Saltar instalación de Docker"
    echo "  --skip-firewall         Saltar configuración de firewall"
    echo "  --skip-update           Saltar actualización del sistema"
    echo ""
    echo "Ejemplo:"
    echo "  $0                      Instalación completa"
    echo "  $0 --skip-docker        Instalación sin Docker"
    echo ""
}

# Función principal
main() {
    local skip_docker=false
    local skip_firewall=false
    local skip_update=false
    local verbose=false
    
    # Procesar argumentos
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                verbose=true
                set -x
                shift
                ;;
            --skip-docker)
                skip_docker=true
                shift
                ;;
            --skip-firewall)
                skip_firewall=true
                shift
                ;;
            --skip-update)
                skip_update=true
                shift
                ;;
            *)
                error "Opción desconocida: $1"
                ;;
        esac
    done
    
    # Inicio del script
    log "==================================================="
    log "      INICIANDO INSTALACIÓN DE ITBOT EN VPS"
    log "==================================================="
    
    # Verificaciones iniciales
    detect_os
    check_sudo
    
    # Actualizar sistema
    if [[ "$skip_update" != true ]]; then
        update_system
    else
        log "Saltando actualización del sistema"
    fi
    
    # Instalar Docker
    if [[ "$skip_docker" != true ]]; then
        install_docker
        install_docker_compose
    else
        log "Saltando instalación de Docker"
    fi
    
    # Configurar firewall
    if [[ "$skip_firewall" != true ]]; then
        setup_firewall
    else
        log "Saltando configuración de firewall"
    fi
    
    # Clonar repositorio
    clone_repository
    
    # Configurar entorno
    setup_environment
    setup_data_directories
    
    # Probar instalación
    test_installation
    
    # Información post-instalación
    show_post_install_info
    
    log "Instalación completada exitosamente!"
}

# Verificar si se está ejecutando como script principal
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi