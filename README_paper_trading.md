# Sistema de Paper Trading Algorítmico

Sistema completo de simulación de trading en tiempo real con análisis técnico avanzado y gestión automática de portafolio.

## Características Principales

- **Conexión en tiempo real** a Binance WebSocket
- **Análisis técnico avanzado** con RSI, MACD, Bollinger Bands
- **Diversificación automática** basada en porcentajes recomendados
- **Múltiples estrategias** de trading (momentum, mean reversion, trend following, breakout, probability)
- **Gestión de riesgo** con stop loss y take profit automáticos
- **Reportes en tiempo real** con métricas de performance
- **Logging detallado** por consola sin interfaz gráfica

## Símbolos Soportados

### Criptomonedas (Binance)
- BNBUSDT, ADAUSDT, SOLUSDT, ETHUSDT, LTCUSDT
- BTCUSDT, MATICUSDT, XRPUSDT, LINKUSDT, DOTUSDT

### Forex/Índices/Metales
- EURUSD, AUDCAD, NAS100, XAUUSD

## Instalación

1. **Instalar dependencias:**
```bash
pip install -r requirements_paper_trading.txt
```

2. **Configurar credenciales de Binance:**
   - Crear archivo `.env` en el directorio raíz
   - Agregar tus API keys de Binance:
```
BINANCE_API_KEY=tu_api_key_aqui
BINANCE_SECRET_KEY=tu_secret_key_aqui
```

## Uso

### Ejecución Principal
```bash
python main_paper_trading.py
```

### Configuración de Portafolio
El sistema incluye configuración automática con los siguientes porcentajes recomendados:
- **40%** NAS100 (Índice tecnológico)
- **30%** AUDCAD (Par forex estable)
- **30%** XAUUSD (Oro como refugio)

### Estrategias Disponibles
1. **Momentum**: Sigue tendencias fuertes
2. **Mean Reversion**: Aprovecha reversiones a la media
3. **Trend Following**: Identifica y sigue tendencias
4. **Breakout**: Detecta rupturas de niveles clave
5. **Probability**: Basada en análisis probabilístico

## Estructura del Proyecto

```
ITBOT/
├── main_paper_trading.py          # Archivo principal
├── paper_trading_simulator.py     # Simulador base
├── market_analyzer.py             # Análisis técnico
├── portfolio_manager.py           # Gestión de portafolio
├── trading_signals.py             # Sistema de señales
├── trade_executor.py              # Ejecución de trades
├── performance_reporter.py        # Reportes de performance
├── monitoring_system.py           # Sistema de monitoreo
├── requirements_paper_trading.txt # Dependencias
└── README_paper_trading.md        # Este archivo
```

## Funcionalidades Clave

### Análisis en Tiempo Real
- Indicadores técnicos calculados automáticamente
- Detección de patrones de mercado
- Análisis de volatilidad y momentum

### Gestión de Riesgo
- Stop loss automático (2% por defecto)
- Take profit dinámico (4% por defecto)
- Límites de exposición por símbolo
- Diversificación automática

### Reportes y Métricas
- PnL en tiempo real
- Ratio de Sharpe
- Drawdown máximo
- Win rate por estrategia
- Análisis de performance por símbolo

### Logging y Monitoreo
- Logs detallados por consola
- Alertas de trading importantes
- Seguimiento de señales y ejecuciones
- Métricas de performance actualizadas

## Configuración Avanzada

### Parámetros de Trading
- Capital inicial: $10,000 (configurable)
- Comisiones: 0.1% (Binance estándar)
- Slippage: 0.05% (simulado)
- Timeframe principal: 1 minuto

### Indicadores Técnicos
- RSI: Período 14, niveles 30/70
- MACD: 12, 26, 9
- Bollinger Bands: Período 20, desviación 2

## Notas Importantes

1. **Paper Trading**: Este sistema NO ejecuta trades reales, solo simula operaciones
2. **Datos en tiempo real**: Requiere conexión a internet estable
3. **API Limits**: Respeta los límites de rate de Binance
4. **Backtesting**: Los resultados pasados no garantizan performance futura

## Soporte y Desarrollo

Este sistema está diseñado para trading algorítmico educativo y de investigación. Para uso en producción, se recomienda testing extensivo y validación adicional.

## Licencia

Uso educativo y de investigación. No se proporciona garantía de resultados financieros.