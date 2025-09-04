#!/bin/bash
"""
Script para ejecutar bot autónomo en background de forma persistente
"""

echo "🚀 Iniciando Bot Autónomo de Micro-Trading..."
echo "="*50

# Detener cualquier instancia previa
pkill -f "autonomous_micro_trading_bot.py" 2>/dev/null

# Ejecutar bot en background
python autonomous_micro_trading_bot.py > bot_output.log 2>&1 &
BOT_PID=$!

echo "✅ Bot iniciado con PID: $BOT_PID"
echo "📝 Logs en: bot_output.log"
echo "🛑 Para detener: kill $BOT_PID"

# Mostrar primeros logs
sleep 3
echo ""
echo "📊 PRIMEROS LOGS:"
echo "="*30
head -20 bot_output.log
echo "="*30
echo "⏳ Bot ejecutándose en background..."
echo "💡 Usar 'tail -f bot_output.log' para ver logs en tiempo real"
