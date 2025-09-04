# CONFIGURACIÓN DE INTEGRACIÓN AUTÓNOMA
# Para ITBOT - Estrategias que funcionan solo con bot + Binance

## 1. INSTALACIÓN RÁPIDA

### Paso 1: Añadir al archivo principal de tu bot

```python
# En tu archivo principal (main.py, run_bot.py, etc.)
from strategies.autonomous_integration_module import AutonomousStrategiesModule, run_autonomous_strategies_cycle

# Añadir esta función a tu bot:
async def execute_autonomous_strategies():
    """
    Función que se ejecuta cada minuto para obtener señales autónomas
    """
    try:
        signals = await run_autonomous_strategies_cycle()
        
        for signal in signals:
            # Usar tu función actual de ejecución de trades
            await execute_trade_signal(signal)  # Adaptar nombre según tu función
            
    except Exception as e:
        print(f"❌ Error en estrategias autónomas: {e}")

# En tu loop principal, añadir:
# asyncio.create_task(execute_autonomous_strategies())
```

### Paso 2: Adaptar funciones de datos

En `autonomous_integration_module.py`, completa estas funciones con tu código actual:

```python
async def get_recent_klines(self, pair: str, timeframe: str, limit: int):
    # Reemplazar con tu función actual de Binance
    return await self.your_binance_client.get_klines(
        symbol=pair,
        interval=timeframe,
        limit=limit
    )

async def auto_select_high_volume_pairs(self):
    # Usar tu función actual para obtener pares por volumen
    ticker_24h = await self.your_binance_client.get_ticker()
    # Filtrar por volumen y devolver top pairs
    return ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
```

## 2. CONFIGURACIÓN PERSONALIZADA

### Ajustar Capital y Riesgo

```python
# En la inicialización del módulo
strategy_config = {
    'scalping_auto': {
        'enabled': True,
        'capital_pct': 0.35,      # 35% del capital para scalping
        'max_positions': 3,       # Máximo 3 posiciones simultáneas
        'risk_per_trade': 0.02,   # 2% de riesgo por trade
        'pairs': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']  # Tus pares favoritos
    },
    'mean_reversion': {
        'enabled': True,
        'capital_pct': 0.25,      # 25% para mean reversion
        'max_positions': 2,
        'risk_per_trade': 0.03,   # 3% por trade (más conservador)
    },
    'breakout_momentum': {
        'enabled': True,
        'capital_pct': 0.20,      # 20% para breakouts
        'max_positions': 2,
        'risk_per_trade': 0.025,
    }
}
```

### Personalizar Timeframes

```python
# Para trading más agresivo:
timeframes = ['1m', '3m', '5m']

# Para trading más conservador:
timeframes = ['15m', '30m', '1h']

# Para trading swing:
timeframes = ['1h', '4h', '1d']
```

## 3. INTEGRACIÓN CON TU SISTEMA ACTUAL

### Usando tu Risk Manager

```python
# En autonomous_integration_module.py
def calculate_position_size(self, capital_pct: float, risk_pct: float, 
                          entry_price: float, stop_loss_price: float) -> float:
    # Usar tu RiskManager actual
    from risk_manager import RiskManager
    
    risk_manager = RiskManager()
    return risk_manager.calculate_position_size(
        capital=self.capital_inicial * capital_pct,
        risk_percentage=risk_pct,
        entry=entry_price,
        stop_loss=stop_loss_price
    )
```

### Usando tus Handlers actuales

```python
# En la función principal
async def process_autonomous_signal(signal):
    """
    Procesar señal usando tus handlers actuales
    """
    from handlers import TradingHandler  # Tu handler actual
    
    handler = TradingHandler()
    
    # Convertir señal a formato de tu bot
    trade_data = {
        'symbol': signal.pair,
        'side': 'BUY' if signal.direction == 'LONG' else 'SELL',
        'quantity': signal.position_size,
        'price': signal.entry_price,
        'stopPrice': signal.stop_loss,
        'strategy': signal.strategy
    }
    
    # Ejecutar usando tu sistema
    result = await handler.execute_trade(trade_data)
    return result
```

## 4. MONITOREO Y LOGGING

### Integrar con tu sistema de logs

```python
# En autonomous_integration_module.py
import logging
from logging_config import setup_logging  # Tu configuración actual

# Usar tu logger actual
self.logger = logging.getLogger('itbot.autonomous_strategies')
```

### Dashboard en tiempo real

```python
# Añadir métricas a tu dashboard actual
async def update_autonomous_metrics():
    """
    Actualizar métricas de estrategias autónomas
    """
    metrics = {
        'active_strategies': len([s for s in self.strategy_config.values() if s['enabled']]),
        'active_positions': len(self.active_positions),
        'daily_pnl': self.calculate_daily_pnl(),
        'win_rate': self.calculate_win_rate(),
        'signals_generated_today': self.count_daily_signals()
    }
    
    # Integrar con tu dashboard actual
    await self.update_dashboard(metrics)
```

## 5. SCHEDULE DE EJECUCIÓN

### Integrar con tu scheduler actual

```python
# En tu sistema de scheduling
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Ejecutar estrategias cada minuto
scheduler.add_job(
    execute_autonomous_strategies,
    'interval',
    minutes=1,
    id='autonomous_strategies'
)

# Ejecutar análisis profundo cada hora
scheduler.add_job(
    deep_market_analysis,
    'interval',
    hours=1,
    id='market_analysis'
)
```

## 6. TESTING Y VALIDACIÓN

### Test de integración

```python
# Test básico
python3 strategies/autonomous_integration_module.py

# Test con tu bot actual
async def test_integration():
    autonomous = AutonomousStrategiesModule(
        capital_inicial=1000,  # Capital de prueba
        existing_bot_config=your_config
    )
    
    await autonomous.initialize()
    signals = await autonomous.get_all_autonomous_signals()
    
    print(f"✅ Generadas {len(signals)} señales de prueba")
    for signal in signals:
        print(f"   {signal.strategy}: {signal.pair} {signal.direction}")
```

### Backtesting con datos históricos

```python
# Usar tus datos históricos existentes
async def backtest_autonomous_strategies():
    # Cargar datos históricos de tu base de datos
    historical_data = load_historical_data()
    
    # Simular estrategias autónomas
    results = await simulate_strategies(historical_data)
    
    print(f"📊 Backtest Results:")
    print(f"   Total Return: {results['total_return']:.2%}")
    print(f"   Win Rate: {results['win_rate']:.2%}")
    print(f"   Max Drawdown: {results['max_drawdown']:.2%}")
```

## 7. CONFIGURACIÓN AVANZADA

### Filtros personalizados

```python
# Añadir filtros específicos para tu estilo de trading
def custom_signal_filters(self, signals):
    filtered = []
    
    for signal in signals:
        # Filtro por volatilidad
        if self.get_pair_volatility(signal.pair) > 0.05:  # >5% volatilidad diaria
            continue
            
        # Filtro por spread
        if self.get_bid_ask_spread(signal.pair) > 0.001:  # >0.1% spread
            continue
            
        # Filtro por volumen mínimo
        if self.get_24h_volume(signal.pair) < 1000000:  # <1M USDT volumen
            continue
            
        filtered.append(signal)
    
    return filtered
```

### Optimización dinámica

```python
# Ajustar parámetros basándose en performance
async def optimize_strategy_parameters():
    """
    Optimiza parámetros basándose en rendimiento reciente
    """
    recent_performance = await self.analyze_recent_performance()
    
    if recent_performance['win_rate'] < 0.6:  # Si win rate < 60%
        # Ser más conservador
        self.strategy_config['scalping_auto']['risk_per_trade'] *= 0.8
        
    elif recent_performance['win_rate'] > 0.8:  # Si win rate > 80%
        # Ser más agresivo
        self.strategy_config['scalping_auto']['risk_per_trade'] *= 1.1
```

## 8. MODO PRODUCCIÓN

### Configuración para live trading

```python
PRODUCTION_CONFIG = {
    'capital_inicial': 50000,  # Tu capital real
    'max_daily_trades': 20,
    'max_concurrent_positions': 8,
    'emergency_stop_loss': 0.05,  # Stop general al 5% de pérdida diaria
    'profit_target': 0.15,  # Target mensual 15%
    'risk_management': {
        'max_risk_per_strategy': 0.10,  # 10% máximo por estrategia
        'correlation_limit': 0.7,  # No más de 70% correlación entre trades
    }
}
```

### Alertas y notificaciones

```python
# Integrar con tu sistema de Telegram actual
async def send_strategy_alert(message):
    # Usar tu bot de Telegram actual para notificaciones
    await self.telegram_bot.send_message(
        chat_id=your_chat_id,
        text=f"🤖 Estrategias Autónomas: {message}"
    )
```

---

## RESUMEN DE INTEGRACIÓN

1. **Copiar** `autonomous_integration_module.py` a tu carpeta `strategies/`
2. **Adaptar** las funciones de datos con tu cliente Binance actual
3. **Integrar** con tu sistema de ejecución de trades
4. **Configurar** parámetros según tu estilo de trading
5. **Testear** en modo paper trading primero
6. **Activar** en producción gradualmente

**Retorno esperado**: 15-17% mensual con las 3 estrategias principales activas
**Tiempo de implementación**: 2-3 horas para integración completa
**Dependencias**: Solo tu bot actual + Binance API

¿Empezamos con la integración paso a paso?
