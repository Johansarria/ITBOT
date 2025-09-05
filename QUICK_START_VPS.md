# 🚀 Cómo Clonar ITBOT a tu VPS (154.38.163.39) - Guía Rápida

## ⚡ Instalación Súper Rápida (Recomendada)

Ejecuta este único comando en tu VPS:

```bash
ssh root@154.38.163.39
curl -fsSL https://raw.githubusercontent.com/Johansarria/ITBOT/main/setup_vps.sh | bash
```

¡Y listo! El script instalará automáticamente:
- Docker y Docker Compose
- Clonará el repositorio ITBOT
- Configurará el firewall
- Preparará los archivos de configuración

## 📋 Configuración Rápida

Después de la instalación automática:

### 1. Configura las variables de entorno:
```bash
cd ITBOT
nano .env
```

**Variables obligatorias a cambiar:**
```env
# Token del bot de Telegram
TELEGRAM_BOT_TOKEN=tu_token_aqui

# ID del chat donde recibirás notificaciones  
TELEGRAM_CHAT_ID=tu_chat_id_aqui

# Tu ID de Telegram para administración
ADMIN_TELEGRAM_ID=tu_id_aqui

# Contraseña segura para la base de datos
POSTGRES_PASSWORD=una_contraseña_muy_segura

# Para trading real (opcional, déjalo como está para pruebas)
BINANCE_API_KEY=tu_api_key_binance
BINANCE_SECRET_KEY=tu_secret_key_binance
```

### 2. Inicia el bot:
```bash
docker compose up -d --build
```

### 3. Verifica que todo funcione:
```bash
./verify_deployment.sh
```

## 🌐 Acceso

- **Panel Web**: `http://154.38.163.39:8080`
- **Logs**: `docker compose logs -f`
- **Estado**: `docker compose ps`

## 📚 Documentación Completa

Si prefieres instalación manual o necesitas más detalles:
- **[DEPLOY_VPS.md](DEPLOY_VPS.md)** - Guía completa paso a paso
- **[README.md](README.md)** - Documentación del proyecto

## 🆘 Comandos Útiles

```bash
# Ver logs en tiempo real
docker compose logs -f

# Reiniciar el bot
docker compose restart

# Parar todo
docker compose down

# Actualizar el código
git pull origin main && docker compose up -d --build

# Backup de la base de datos
docker exec itbot_postgres_db pg_dump -U itbot_user itbot_db > backup.sql
```

## 🔒 Importante

1. **Nunca** uses contraseñas por defecto en producción
2. Configura las variables de Telegram antes de iniciar
3. Para trading real, cambia `PRODUCTION_MODE=false` a `true` solo cuando estés seguro
4. El bot inicia en modo PAPER (simulado) por seguridad

## ❓ ¿Problemas?

1. Ejecuta: `./verify_deployment.sh`
2. Revisa logs: `docker compose logs`
3. Consulta: `DEPLOY_VPS.md` sección "Resolución de Problemas"

---
**¡Tu bot estará listo en menos de 5 minutos!** 🎉