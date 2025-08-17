#!/bin/bash
#
# Script para ejecutar el ciclo de optimización mensual de forma automática.
#

echo "--- Iniciando ciclo de optimización mensual: $(date) ---"

# Ruta absoluta al directorio del proyecto para que el script se pueda ejecutar desde cualquier lugar.
PROJECT_DIR="/home/johan/itbot_linux"
PYTHON_EXEC="$PROJECT_DIR/.venv/bin/python"

# Paso 1: Actualizar la base de datos con los últimos datos históricos.
echo "Paso 1/2: Descargando datos históricos actualizados..."
$PYTHON_EXEC "$PROJECT_DIR/download_historical_data.py"

# Comprobar si la descarga fue exitosa antes de continuar.
if [ $? -ne 0 ]; then
    echo "Error: La descarga de datos falló. Abortando optimización."
    exit 1
fi

# Paso 2: Ejecutar el script de optimización con los datos actualizados.
echo "Paso 2/2: Iniciando la optimización de la estrategia..."
$PYTHON_EXEC "$PROJECT_DIR/optimize_strategy.py"

if [ $? -ne 0 ]; then
    echo "Error: La optimización de la estrategia falló."
    exit 1
fi

echo "--- Ciclo de optimización mensual completado exitosamente: $(date) ---"
