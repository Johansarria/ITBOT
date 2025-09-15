# Rama Micropruebas - Sistema de Trading Autónomo Ultra-Conservador

## 🎯 Descripción
Esta rama contiene la implementación completa del sistema de **micro-trading autónomo** con límites ultra-conservadores para protección total del capital.

## 🚀 Características Principales

### 🤖 Bot Autónomo de Micro-Trading
- **Límite por operación**: $0.75 máximo
- **Apalancamiento**: 10x controlado
- **Stop Loss**: 2% automático 
- **Take Profit**: 3% automático
- **Análisis cada**: 5 minutos
- **Cooldown**: 30 minutos entre trades
- **Máximo diario**: 5 operaciones

### 🛡️ Protección de Capital
- **Pérdida máxima por trade**: $0.15
- **Pérdida diaria máxima**: 10% del balance
- **Gestión de riesgo automática**
- **Monitoreo continuo de cumplimiento**

### 📊 Sistema Híbrido
- **Posiciones legacy**: Supervisión especial
- **Micro-pruebas nuevas**: Límites estrictos
- **Compatibilidad**: Binance Futures USDT-M
- **Precisión automática**: Ajuste a filtros de exchange

## 🔧 Archivos Clave

### Bot Principal
- `autonomous_micro_trading_bot.py` - Bot principal autónomo
- `start_autonomous_bot.sh` - Script de inicio persistente

### Monitoreo y Análisis
- `hybrid_monitoring_system.py` - Monitor híbrido legacy+micro
- `detailed_position_check.py` - Estado detallado de posiciones
- `trading_projection.py` - Proyecciones de rendimiento
- `simple_market_analyzer.py` - Análisis de oportunidades

### Configuración de Seguridad
- `configure_micro_testing.py` - Configuración inicial
- `manage_micro_transition.py` - Gestión de transición
- `verify_micro_testing.py` - Verificación de parámetros

### Utilidades
- `check_symbol_precision.py` - Verificación de precisión Binance
- `micro_testing_monitor.py` - Monitor de cumplimiento

## 🚀 Uso Rápido

### 1. Iniciar Bot Autónomo
```bash
docker exec -it itbot_main bash start_autonomous_bot.sh
```

### 2. Monitorear Logs en Tiempo Real
```bash
docker exec -it itbot_main tail -f bot_output.log
```

### 3. Verificar Estado de Posiciones
```bash
docker exec -it itbot_main python detailed_position_check.py
```

### 4. Ver Proyecciones
```bash
docker exec -it itbot_main python trading_projection.py
```

## 📈 Rendimiento Esperado

### Proyección 4-6 horas:
- **Conservador**: +$0.47 (+10.4% ROI)
- **Moderado**: +$0.38 (+8.3% ROI) 
- **Optimista**: +$0.28 (+6.2% ROI)

### Características de Seguridad:
- ✅ Máximo $0.75 riesgo por trade
- ✅ Ratio R/R favorable (1:1.5)
- ✅ Filtros de calidad estrictos (score >75/100)
- ✅ Operación 24/7 sin intervención

## ⚠️ Consideraciones Importantes

1. **Solo SOLUSDT viable**: BTC/ETH requieren más capital para mínimos notionales
2. **Dependiente de volatilidad**: Mejores resultados con mercado moderadamente volátil
3. **Balance mínimo**: Se recomienda >$5 para operación óptima
4. **Monitoreo recomendado**: Verificar estado cada 2-3 horas

## 🔄 Estado Actual
- Bot funcionando en background (PID disponible en logs)
- Sistema híbrido activo
- Posición SOLUSDT legacy protegida con SL/TP
- Esperando liberación de símbolos para nuevas micro-operaciones

## 📝 Logs y Monitoreo
Todos los logs se almacenan en `bot_output.log` dentro del contenedor principal para facilitar el seguimiento y debugging.

---
**Fecha de creación**: 2025-09-04  
**Estado**: ✅ Funcional y en producción  
**Riesgo**: 🛡️ Ultra-conservador  
**ROI esperado**: 📈 6-10% en 4-6 horas
