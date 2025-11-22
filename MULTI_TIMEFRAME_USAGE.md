# SICAR - Sistema Multi-Timeframe Paper Trading

## 📋 Resumen

Se ha implementado exitosamente el análisis multi-timeframe en el sistema de paper trading de SICAR, integrando modelos de ML entrenados con datos recientes de las IAs Grok y OpenAI.

## 🎯 Características Implementadas

### ✅ Análisis Multi-Timeframe
- **Timeframes soportados**: 1m, 5m, 15m, 1h
- **Símbolos**: BTCUSDT, ETHUSDT, ADAUSDT, DOTUSDT, LINKUSDT
- **Indicadores técnicos**: RSI, MACD, Bollinger Bands, Stochastic, Williams %R, Volume, Momentum, ATR, SMA, EMA

### ✅ Modelos de ML Entrenados
- **Datos de entrenamiento**: 277,200 muestras con 9 características
- **Modelos**: Random Forest, Gradient Boosting, Logistic Regression
- **Mejor modelo**: Gradient Boosting (Accuracy: 61.35%)
- **Fuente de datos**: Análisis recientes de Grok xAI y OpenAI

### ✅ Integración Completa
- **Sistema integrado**: Combina análisis técnico + ML + paper trading
- **Preservación de IAs**: Las conexiones existentes no se ven afectadas
- **Gestión de riesgo**: Stop-loss y take-profit automáticos

## 🚀 Cómo Usar el Sistema

### Opción 1: Ejecutar Sistema Integrado
```bash
cd src
python run_multi_timeframe_paper_trading.py
```

### Opción 2: Con Capital Personalizado
```bash
python run_multi_timeframe_paper_trading.py 5000.0
```

### Opción 3: Solo Análisis Multi-Timeframe
```bash
python multi_timeframe_paper_trading.py
```

### Opción 4: Entrenar Nuevos Modelos
```bash
python ml_training_recent_data.py
```

## 📊 Archivos Creados

### Módulos Principales
- `multi_timeframe_paper_trading.py` - Análisis multi-timeframe base
- `integrated_multi_timeframe_paper_trading.py` - Sistema integrado con ML
- `ml_training_recent_data.py` - Entrenamiento de modelos ML
- `run_multi_timeframe_paper_trading.py` - Script de ejecución principal

### Modelos Entrenados
- `models/multi_timeframe_random_forest.joblib`
- `models/multi_timeframe_gradient_boosting.joblib`
- `models/multi_timeframe_logistic_regression.joblib`
- `models/multi_timeframe_model_metadata.json`

### Logs y Resultados
- `ml_training_recent_data.log` - Log de entrenamiento
- `multi_timeframe_paper_trading.log` - Log de ejecución
- `test_results_simplified.json` - Resultados de tests

## 🔧 Configuración

### Parámetros Principales
```python
INITIAL_CAPITAL = 1000.0  # Capital inicial
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']  # Símbolos a analizar
TIMEFRAMES = ['1m', '5m', '15m', '1h']  # Timeframes
RISK_PERCENTAGE = 0.02  # 2% de riesgo por operación
```

### Configuración de ML
```python
ML_FEATURES = [
    'rsi', 'macd_signal', 'bb_position', 'stoch_k', 'williams_r',
    'volume_ratio', 'momentum', 'atr_normalized', 'price_sma_ratio'
]
```

## 📈 Funcionamiento

### 1. Análisis Multi-Timeframe
El sistema analiza cada símbolo en múltiples timeframes:
- Obtiene datos históricos de Binance
- Calcula indicadores técnicos
- Genera señales por timeframe
- Combina señales en consenso

### 2. Predicciones ML
- Extrae características de los datos de mercado
- Aplica modelos entrenados
- Genera predicciones con confianza
- Combina con análisis técnico

### 3. Ejecución de Trades
- Evalúa señales combinadas
- Calcula niveles de riesgo
- Ejecuta órdenes en paper trading
- Aplica stop-loss y take-profit

### 4. Monitoreo Continuo
- Bucle de análisis cada minuto
- Actualización de posiciones
- Logging detallado
- Preservación de conexiones IA

## 🛡️ Verificaciones de Seguridad

### ✅ Tests Pasados (6/6)
- **ml_models_exist**: Modelos ML disponibles
- **training_data_extraction**: Datos de entrenamiento válidos
- **paper_trading_components**: Componentes de paper trading funcionales
- **ai_connections_active**: Conexiones IA activas y funcionando
- **multi_timeframe_implementation**: Implementación completa
- **training_logs**: Logs de entrenamiento disponibles

### 🔒 Preservación de IAs
- Las conexiones a Grok xAI y OpenAI **NO se ven afectadas**
- Los procesos de análisis continuo siguen funcionando
- Los archivos de patrones se siguen actualizando
- No hay interferencia con sistemas existentes

## 📝 Logs y Monitoreo

### Archivos de Log
- `multi_timeframe_paper_trading.log` - Actividad del sistema
- `ml_training_recent_data.log` - Entrenamiento de modelos
- `SICAR - ANÁLISIS CONTINUO DE PATRONES...txt` - Análisis de IAs

### Métricas Monitoreadas
- Capital total y disponible
- Posiciones abiertas
- Señales generadas
- Predicciones ML
- Performance de modelos

## 🚨 Solución de Problemas

### Error: Módulos no encontrados
```bash
# Verificar que estás en el directorio correcto
cd C:\Users\johan\OneDrive\Escritorio\SICAR\sicar_project\src

# Ejecutar en modo compatibilidad
python run_multi_timeframe_paper_trading.py
```

### Error: Modelos ML no disponibles
```bash
# Re-entrenar modelos
python ml_training_recent_data.py
```

### Error: Conexión a Binance
- El sistema funciona en modo simulado
- No requiere conexión real a Binance para paper trading
- Los datos se obtienen de cache cuando es posible

## 📞 Soporte

Para problemas o mejoras:
1. Revisar logs en `src/`
2. Ejecutar tests: `python test_integrated_system.py`
3. Verificar que las IAs siguen funcionando
4. Consultar documentación en `docs/`

---

**Fecha de implementación**: 2025-01-21  
**Versión**: 1.0  
**Estado**: ✅ Completamente funcional