#!/bin/bash

# Script para iniciar todos los componentes del ITBot

echo "============================================="
echo "         INICIANDO ENTORNO ITBOT"
echo "============================================="

# 1. Iniciar Redis
echo "[1/5] Iniciando Redis Server..."
redis-server --daemonize yes
# La opción --daemonize yes lo inicia en segundo plano automáticamente.

# 2. Verificar PostgreSQL
echo "[2/5] Verificando que PostgreSQL se esté ejecutando..."
# El script ya no inicia PostgreSQL, asume que está activo como un servicio del sistema.
# Puedes verificar su estado con: sudo systemctl status postgresql
if ! pg_isready -q; then
    echo "ERROR: No se pudo conectar a PostgreSQL. Asegúrate de que el servicio esté activo." 
    exit 1
fi
echo "PostgreSQL está listo."


# 3. Esperar a que los servicios estén listos
echo "[3/5] Esperando 5 segundos para que los servicios se estabilicen..."
sleep 5

# 4. Activar el entorno virtual de Python
echo "[4/5] Activando el entorno virtual de Python..."
source .venv/bin/activate

# 5. Iniciar los componentes del bot en segundo plano
echo "[5/5] Iniciando los componentes del Bot en segundo plano..."

echo "  -> Iniciando Listener Bot (Telegram)..."
python listener_bot.py &
LISTENER_PID=$!

echo "  -> Iniciando Execution Worker..."
python execution_worker.py &
WORKER_PID=$!

echo "  -> Iniciando Run Bot (Ciclo de Análisis)..."
python run_bot.py &
RUN_BOT_PID=$!

echo "============================================="
echo "✅ ENTORNO ITBOT INICIADO"
echo "============================================="
echo "Procesos iniciados en segundo plano:"
echo "  - Listener (Telegram): PID $LISTENER_PID"
echo "  - Worker (Ejecución):  PID $WORKER_PID"
echo "  - Run Bot (Análisis):  PID $RUN_BOT_PID"
echo ""
echo "Puedes ver los logs de cada uno en sus respectivos archivos en la carpeta /logs."
echo "Para detener todos los procesos de python, puedes usar el comando: pkill -f python"
