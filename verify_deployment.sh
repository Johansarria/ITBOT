#!/bin/bash

#
# ITBOT VPS Deployment Verification Script
# Verifica que el despliegue de ITBOT en VPS esté funcionando correctamente
#

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funciones de utilidad
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Verificar Docker
check_docker() {
    log "Verificando Docker..."
    if ! command -v docker &> /dev/null; then
        error "Docker no está instalado"
    fi
    
    if ! docker --version; then
        error "Docker no funciona correctamente"
    fi
    
    log "Docker OK: $(docker --version)"
}

# Verificar Docker Compose
check_docker_compose() {
    log "Verificando Docker Compose..."
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose no está instalado"
    fi
    
    if ! docker-compose --version; then
        error "Docker Compose no funciona correctamente"
    fi
    
    log "Docker Compose OK: $(docker-compose --version)"
}

# Verificar archivos de configuración
check_config_files() {
    log "Verificando archivos de configuración..."
    
    if [[ ! -f "docker-compose.yml" ]]; then
        error "Archivo docker-compose.yml no encontrado"
    fi
    
    if [[ ! -f ".env" ]]; then
        error "Archivo .env no encontrado. Copia desde .env.example"
    fi
    
    if [[ ! -f "Dockerfile" ]]; then
        error "Dockerfile no encontrado"
    fi
    
    log "Archivos de configuración OK"
}

# Verificar servicios de Docker
check_docker_services() {
    log "Verificando servicios de Docker..."
    
    # Verificar que los servicios están corriendo
    if ! docker-compose ps | grep -q "Up"; then
        warn "Algunos servicios no están corriendo. Iniciando servicios..."
        docker-compose up -d --build
        sleep 10
    fi
    
    # Verificar servicios individuales
    services=("itbot_redis" "itbot_postgres_db" "itbot_listener" "itbot_main" "itbot_worker" "itbot_web")
    
    for service in "${services[@]}"; do
        if docker ps | grep -q "$service"; then
            log "Servicio $service está corriendo"
        else
            warn "Servicio $service no está corriendo"
        fi
    done
}

# Verificar conectividad de red
check_network_connectivity() {
    log "Verificando conectividad de red..."
    
    # Verificar Redis
    if docker exec itbot_redis redis-cli ping | grep -q "PONG"; then
        log "Redis responde correctamente"
    else
        error "Redis no responde"
    fi
    
    # Verificar PostgreSQL
    if docker exec itbot_postgres_db pg_isready -q; then
        log "PostgreSQL responde correctamente"
    else
        error "PostgreSQL no responde"
    fi
    
    # Verificar web interface
    if curl -s http://localhost:8080 > /dev/null; then
        log "Web interface responde correctamente"
    else
        warn "Web interface no responde en puerto 8080"
    fi
}

# Verificar logs de servicios
check_service_logs() {
    log "Verificando logs de servicios..."
    
    # Verificar que no hay errores críticos en los logs recientes
    if docker-compose logs --tail=20 | grep -i "error\|failed\|exception" | grep -v "INFO\|DEBUG"; then
        warn "Se encontraron errores en los logs. Revisa con: docker-compose logs"
    else
        log "No se encontraron errores críticos en logs recientes"
    fi
}

# Verificar variables de entorno
check_environment_variables() {
    log "Verificando variables de entorno..."
    
    # Verificar variables críticas
    if grep -q "your_telegram_bot_token_here" .env; then
        warn "TELEGRAM_BOT_TOKEN no está configurado"
    fi
    
    if grep -q "your_telegram_chat_id_here" .env; then
        warn "TELEGRAM_CHAT_ID no está configurado"
    fi
    
    if grep -q "changeme" .env; then
        warn "POSTGRES_PASSWORD usa el valor por defecto"
    fi
    
    log "Verificación de variables de entorno completada"
}

# Función principal
main() {
    log "=================================================="
    log "     VERIFICACIÓN DE DESPLIEGUE ITBOT VPS"
    log "=================================================="
    
    # Verificar que estamos en el directorio correcto
    if [[ ! -f "docker-compose.yml" ]]; then
        error "No estás en el directorio de ITBOT. Ejecuta desde el directorio raíz del proyecto."
    fi
    
    # Ejecutar verificaciones
    check_docker
    check_docker_compose
    check_config_files
    check_docker_services
    check_network_connectivity
    check_service_logs
    check_environment_variables
    
    log "=================================================="
    log "         VERIFICACIÓN COMPLETADA"
    log "=================================================="
    
    info "ESTADO DEL SISTEMA:"
    docker-compose ps
    
    echo ""
    info "COMANDOS ÚTILES:"
    echo "  Ver logs en tiempo real: docker-compose logs -f"
    echo "  Reiniciar servicios:     docker-compose restart"
    echo "  Parar servicios:         docker-compose down"
    echo "  Estado de servicios:     docker-compose ps"
    echo ""
    info "ACCESO:"
    echo "  Web Interface: http://localhost:8080"
    echo "  Para acceso externo: http://[IP_DEL_VPS]:8080"
    echo ""
    info "Para más información, consulta DEPLOY_VPS.md"
}

# Verificar si se está ejecutando como script principal
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi