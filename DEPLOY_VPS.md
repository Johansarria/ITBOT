# ITBOT - Guía de Despliegue en VPS

Esta guía te ayudará a clonar y desplegar ITBOT en tu VPS (154.38.163.39) de manera completa y segura.

## 📋 Requisitos Previos

### Sistema Operativo
- Ubuntu 20.04+ / Debian 11+ / CentOS 8+ recomendado
- Mínimo 2GB RAM, 4GB recomendado
- 10GB de espacio libre en disco
- Acceso root o sudo

### Dependencias del Sistema
- Git
- Docker y Docker Compose
- Python 3.12+ (para despliegue manual)
- PostgreSQL (para despliegue manual)
- Redis (para despliegue manual)

## 🚀 Opción 1: Despliegue Automático (Recomendado)

### Paso 1: Descarga el Script de Instalación

```bash
# Conectarse al VPS
ssh root@154.38.163.39

# Descargar el script de instalación
wget https://raw.githubusercontent.com/Johansarria/ITBOT/main/setup_vps.sh
chmod +x setup_vps.sh

# Ejecutar la instalación automática
./setup_vps.sh
```

### Paso 2: Configurar Variables de Entorno

El script te guiará para configurar las variables necesarias:

```bash
# Editar el archivo .env
nano ITBOT/.env
```

### Paso 3: Iniciar los Servicios

```bash
cd ITBOT
docker compose up -d --build
```

## 🔧 Opción 2: Instalación Manual Paso a Paso

### Paso 1: Preparar el Sistema

```bash
# Actualizar el sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias básicas
sudo apt install -y git curl wget unzip

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Reiniciar la sesión para aplicar cambios de grupo
newgrp docker
```

### Paso 2: Clonar el Repositorio

```bash
# Clonar el repositorio
git clone https://github.com/Johansarria/ITBOT.git
cd ITBOT

# Verificar que tienes todos los archivos
ls -la
```

### Paso 3: Configurar el Entorno

```bash
# Copiar el archivo de ejemplo
cp .env.example .env

# Editar las variables de entorno
nano .env
```

#### Variables Críticas a Configurar:

```env
# PostgreSQL
POSTGRES_DB=itbot_db
POSTGRES_USER=itbot_user
POSTGRES_PASSWORD=tu_password_seguro_aqui

# Telegram
TELEGRAM_BOT_TOKEN=tu_bot_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id_aqui
ADMIN_TELEGRAM_ID=tu_admin_id_aqui

# Binance API (para trading real)
BINANCE_API_KEY=tu_api_key_aqui
BINANCE_SECRET_KEY=tu_secret_key_aqui

# Modo de operación
PRODUCTION_MODE=false  # Cambiar a true solo para trading real

# Web Interface
WEB_PORT=8080
WEB_HOST=0.0.0.0
```

### Paso 4: Configurar Firewall y Seguridad

```bash
# Configurar UFW (Ubuntu Firewall)
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 8080/tcp  # Puerto web del bot
sudo ufw allow 22/tcp    # SSH

# Opcional: Permitir acceso a PostgreSQL solo desde localhost
# sudo ufw allow from 127.0.0.1 to any port 5432
```

### Paso 5: Desplegar con Docker

```bash
# Construir e iniciar todos los servicios
docker compose up -d --build

# Verificar que todos los servicios están corriendo
docker compose ps

# Ver logs de los servicios
docker compose logs -f
```

### Paso 6: Verificar el Despliegue

```bash
# Verificar servicios individuales
docker logs itbot_listener
docker logs itbot_main
docker logs itbot_worker
docker logs itbot_web

# Verificar la web interface
curl http://localhost:8080

# Verificar bases de datos
docker exec -it itbot_postgres_db psql -U itbot_user -d itbot_db -c "SELECT version();"
docker exec -it itbot_redis redis-cli ping
```

## 🌐 Acceso Remoto

### Configurar Acceso Web

El panel web estará disponible en:
- Local: `http://154.38.163.39:8080`
- Si tienes un dominio: `http://tu-dominio.com:8080`

### Configurar Reverse Proxy (Opcional)

Para un acceso más profesional con HTTPS:

```bash
# Instalar Nginx
sudo apt install -y nginx

# Configurar Nginx
sudo nano /etc/nginx/sites-available/itbot
```

```nginx
server {
    listen 80;
    server_name 154.38.163.39;  # o tu dominio

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Activar la configuración
sudo ln -s /etc/nginx/sites-available/itbot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 📊 Monitoreo y Mantenimiento

### Comandos Útiles

```bash
# Ver estado de todos los servicios
docker compose ps

# Reiniciar un servicio específico
docker compose restart listener

# Ver logs en tiempo real
docker compose logs -f

# Actualizar el código
git pull origin main
docker compose up -d --build

# Hacer backup de la base de datos
docker exec itbot_postgres_db pg_dump -U itbot_user itbot_db > backup_$(date +%Y%m%d).sql

# Restaurar backup
cat backup_20240101.sql | docker exec -i itbot_postgres_db psql -U itbot_user -d itbot_db
```

### Automatizar Backups

```bash
# Crear script de backup
cat > backup_script.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/backup/itbot"
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)

# Backup PostgreSQL
docker exec itbot_postgres_db pg_dump -U itbot_user itbot_db > $BACKUP_DIR/db_backup_$DATE.sql

# Backup volúmenes importantes
docker run --rm -v itbot_data-volume:/data -v $BACKUP_DIR:/backup ubuntu tar czf /backup/data_backup_$DATE.tar.gz -C /data .

# Limpiar backups antiguos (más de 7 días)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
EOF

chmod +x backup_script.sh

# Configurar cron para backups automáticos
(crontab -l 2>/dev/null; echo "0 2 * * * /path/to/backup_script.sh") | crontab -
```

## 🔒 Seguridad

### Recomendaciones de Seguridad

1. **Cambiar puertos por defecto**: Modificar el puerto SSH desde 22
2. **Usar claves SSH**: Deshabilitar autenticación por contraseña
3. **Actualizar regularmente**: Mantener el sistema y Docker actualizados
4. **Monitorear logs**: Revisar logs regularmente para detectar anomalías
5. **Backup regular**: Configurar backups automáticos
6. **Firewall**: Mantener solo los puertos necesarios abiertos

### Configuración SSH Segura

```bash
# Editar configuración SSH
sudo nano /etc/ssh/sshd_config

# Cambios recomendados:
# Port 2222  # Cambiar puerto por defecto
# PasswordAuthentication no  # Solo claves SSH
# PermitRootLogin no  # Deshabilitar login root directo

sudo systemctl restart ssh
```

## 🆘 Resolución de Problemas

### Problemas Comunes

**1. Error de permisos Docker:**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

**2. Puerto ya en uso:**
```bash
# Verificar qué proceso usa el puerto
sudo netstat -tulpn | grep :8080
# Terminar proceso si es necesario
sudo kill -9 PID
```

**3. Servicios no inician:**
```bash
# Verificar logs específicos
docker logs itbot_listener
docker logs itbot_postgres_db
docker logs itbot_redis
```

**4. Error de conexión a base de datos:**
```bash
# Verificar variables de entorno
docker compose config

# Reiniciar base de datos
docker compose restart db
```

**5. Bot de Telegram no responde:**
```bash
# Verificar token y configuración
docker logs itbot_listener | grep -i error
# Verificar que el bot está agregado al chat correcto
```

### Logs y Diagnóstico

```bash
# Ver logs de todos los servicios
docker compose logs

# Ver logs de un servicio específico
docker compose logs listener

# Ver logs en tiempo real
docker compose logs -f

# Ver logs del sistema
sudo journalctl -u docker.service

# Verificar uso de recursos
docker stats
```

## 📞 Soporte

Si encuentras problemas durante el despliegue:

1. Revisar los logs detallados
2. Verificar la configuración de .env
3. Consultar la documentación del proyecto
4. Revisar issues en GitHub

## 🔄 Actualizaciones

Para actualizar ITBOT a una nueva versión:

```bash
cd ITBOT
git pull origin main
docker compose down
docker compose up -d --build
```

---

**¡Importante!** Este bot maneja operaciones financieras. Siempre prueba en modo PAPER antes de usar dinero real.