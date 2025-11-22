# 📚 Documentación Técnica - SICAR Trading Bot

## 🏗️ Arquitectura del Sistema

### Visión General

SICAR (Sistema Inteligente de Clasificación y Análisis de Regímenes) es un bot de trading que utiliza un enfoque multi-módulo para el análisis de mercados financieros:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Módulo 1      │    │   Módulo 2      │    │   Módulo 3      │
│   Causal        │───▶│   Regímenes     │───▶│ Metacontrolador │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Módulo XAI                                   │
│              (Explicabilidad Artificial)                       │
└─────────────────────────────────────────────────────────────────┘
```

## 📊 Módulos del Sistema

### 1. Módulo Causal (`module_1_causal.py`)

**Propósito**: Análisis de noticias y eventos de mercado para identificar relaciones causales.

**Tecnologías**:
- spaCy para procesamiento de lenguaje natural
- NetworkX para construcción de grafos causales
- VADER para análisis de sentimientos

**Funcionalidades**:
```python
class CausalCartographer:
    def analyze_news_corpus(self, news_data)
    def extract_financial_entities(self, text)
    def build_causal_graph(self, entities, relationships)
    def calculate_sentiment_impact(self, text)
```

**Características extraídas**:
- Entidades financieras (empresas, monedas, índices)
- Relaciones causales entre eventos
- Sentimiento de mercado
- Impacto temporal de noticias

### 2. Clasificador de Regímenes (`module_2_regime.py`)

**Propósito**: Identificación automática del estado actual del mercado.

**Algoritmos**:
- K-Means clustering para clasificación
- PCA para reducción de dimensionalidad
- Análisis técnico avanzado

**Regímenes identificados**:
1. **Tendencia Alcista**: Momentum positivo sostenido
2. **Tendencia Bajista**: Momentum negativo sostenido  
3. **Mercado Lateral**: Baja volatilidad, sin tendencia clara
4. **Alta Volatilidad**: Movimientos erráticos, incertidumbre

**Características técnicas calculadas**:
```python
# Volatilidad
volatility_5d, volatility_20d, volatility_50d

# Momentum
momentum_5d, momentum_20d, rsi, macd

# Tendencia
sma_20, sma_50, bollinger_upper, bollinger_lower

# Volumen
volume_sma, volume_ratio

# Patrones de velas
body_size, upper_shadow, lower_shadow

# Gaps y rangos
gap_up, gap_down, daily_range
```

### 3. Metacontrolador (`module_3_metacontroller.py`)

**Propósito**: Toma de decisiones inteligente basada en múltiples señales.

**Algoritmo**: Random Forest Classifier

**Entradas**:
- Señales del módulo causal
- Clasificación de régimen actual
- Indicadores técnicos
- Métricas de riesgo

**Salidas**:
- Decisión de trading (BUY/SELL/HOLD)
- Nivel de confianza (0-1)
- Tamaño de posición recomendado

### 4. Módulo XAI (`module_xai.py`)

**Propósito**: Explicabilidad de las decisiones del sistema.

**Funcionalidades**:
- Generación de reportes cognitivos
- Explicación de decisiones en lenguaje natural
- Análisis de importancia de características
- Integración con APIs de LLM (OpenAI, Anthropic)

## 🔄 Pipeline de Datos (`data_pipeline.py`)

### Fuentes de Datos

1. **Datos de Mercado**:
   - Yahoo Finance (yfinance)
   - Datos OHLCV históricos
   - Fallback a datos simulados

2. **Datos de Noticias**:
   - APIs de noticias financieras
   - Scraping de sitios web
   - Análisis de redes sociales

### Procesamiento

```python
class DataPipeline:
    def get_market_data(self, ticker, period="1mo", interval="1h")
    def _add_technical_indicators(self, data)
    def _generate_demo_data(self, ticker, period, interval)
    def get_news_data(self, query="financial news")
```

**Indicadores técnicos agregados**:
- Medias móviles (SMA 20, 50)
- RSI (14 períodos)
- MACD
- Bandas de Bollinger
- Volumen promedio

## 🤖 Bot Principal (`main_bot.py`)

### Clase TradingBot

**Configuración por defecto**:
```python
default_config = {
    'symbol': 'AAPL',
    'timeframe': '4h',
    'initial_capital': 100000.0,
    'risk_per_trade': 0.02,        # 2% por trade
    'stop_loss': 0.02,             # 2% stop loss
    'take_profit': 0.04,           # 4% take profit
    'max_positions': 3,            # Máximo 3 posiciones
    'min_confidence': 0.6,         # Confianza mínima 60%
    'analysis_interval': 3600      # Análisis cada hora
}
```

### Flujo de Ejecución

1. **Inicialización**:
   ```python
   bot = TradingBot()
   bot._load_config()
   bot._initialize_binance_client()
   bot.initialize_models()
   ```

2. **Loop Principal**:
   ```python
   while True:
       market_data = bot._get_market_data()
       analysis_result = bot.analyze_market(market_data)
       decision = bot.execute_trade_decision(analysis_result)
       time.sleep(bot.config['analysis_interval'])
   ```

3. **Análisis de Mercado**:
   ```python
   def analyze_market(self, market_data):
       # 1. Análisis causal (simulado)
       causal_signals = self.causal_cartographer.analyze_market_context()
       
       # 2. Clasificación de régimen
       regime_result = self.regime_classifier.classify_regimes(market_data)
       
       # 3. Metacontrolador
       decision = self.metacontroller.make_decision(features)
       
       return decision
   ```

## 🔌 Integración con Binance

### Configuración

```python
def _initialize_binance_client(self):
    if self.config.get('use_binance_testnet', False):
        api_key = os.getenv('BINANCE_API_KEY')
        secret_key = os.getenv('BINANCE_SECRET_KEY')
        
        self.binance_client = Client(
            api_key, secret_key,
            testnet=True  # Usar Testnet
        )
```

### Trading Real vs Simulación

**Modo Real** (con credenciales):
```python
def _enter_new_position(self, signal, confidence, current_price):
    if self.binance_client:
        # Trading real con Binance API
        order = self.binance_client.order_market_buy(
            symbol=self.config['symbol'],
            quantity=quantity
        )
    else:
        # Simulación local
        self._simulate_position_entry(signal, confidence, current_price)
```

## 📈 Sistema de Backtesting (`backtester.py`)

### Funcionalidades

- Simulación histórica completa
- Métricas de rendimiento
- Análisis de drawdown
- Optimización de parámetros

### Métricas Calculadas

```python
def calculate_performance_metrics(self):
    return {
        'total_return': self.calculate_total_return(),
        'sharpe_ratio': self.calculate_sharpe_ratio(),
        'max_drawdown': self.calculate_max_drawdown(),
        'win_rate': self.calculate_win_rate(),
        'profit_factor': self.calculate_profit_factor(),
        'avg_trade_duration': self.calculate_avg_duration()
    }
```

## 🔧 Configuración Avanzada

### Variables de Entorno

```env
# Trading
SYMBOL=AAPL
TIMEFRAME=4h
INITIAL_CAPITAL=100000
RISK_PER_TRADE=0.02

# Binance
BINANCE_API_KEY=your_api_key
BINANCE_SECRET_KEY=your_secret_key
USE_BINANCE_TESTNET=true

# AI APIs
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Análisis
MIN_CONFIDENCE=0.6
MAX_POSITIONS=3
ANALYSIS_INTERVAL=3600
```

### Personalización de Estrategias

**Modificar parámetros de riesgo**:
```python
# En main_bot.py
def _calculate_position_size(self, signal_strength, confidence):
    base_risk = self.config['risk_per_trade']
    adjusted_risk = base_risk * confidence * signal_strength
    return min(adjusted_risk, 0.05)  # Máximo 5%
```

**Agregar nuevos indicadores**:
```python
# En data_pipeline.py
def _add_technical_indicators(self, data):
    # Indicadores existentes...
    
    # Nuevo indicador personalizado
    data['custom_indicator'] = your_custom_function(data)
    return data
```

## 🛡️ Gestión de Riesgo

### Controles Implementados

1. **Stop Loss dinámico**: Basado en volatilidad
2. **Take Profit adaptativo**: Según régimen de mercado
3. **Límite de posiciones**: Máximo número de trades simultáneos
4. **Confianza mínima**: Umbral para ejecutar trades
5. **Tamaño de posición**: Basado en Kelly Criterion modificado

### Kill Switch

```python
def check_kill_switch(self):
    current_drawdown = self.calculate_current_drawdown()
    if current_drawdown > self.config.get('max_drawdown', 0.15):
        self.emergency_stop()
        logger.critical("KILL SWITCH ACTIVADO - Drawdown excesivo")
```

## 📊 Logging y Monitoreo

### Sistema de Logs

```python
# Configuración en utils/logger.py
LOGGING_CONFIG = {
    'version': 1,
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'logs/sicar_bot.log',
            'formatter': 'detailed'
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        }
    }
}
```

### Métricas Monitoreadas

- Rendimiento en tiempo real
- Drawdown actual
- Win rate
- Número de posiciones activas
- Confianza promedio de decisiones
- Tiempo de ejecución de análisis

## 🔄 Flujo de Desarrollo

### Testing

```bash
# Test individual de módulos
python src/modules/module_1_causal.py
python src/modules/module_2_regime.py
python src/modules/module_3_metacontroller.py

# Test del pipeline completo
python src/pipelines/data_pipeline.py

# Test del bot principal
python src/main_bot.py
```

### Deployment

1. **Preparación**:
   ```bash
   python install_dependencies.py
   cp .env.example .env
   # Configurar variables de entorno
   ```

2. **Validación**:
   ```bash
   python src/main_bot.py --validate-only
   ```

3. **Ejecución**:
   ```bash
   python src/main_bot.py
   ```

## 🚀 Optimización y Escalabilidad

### Mejoras de Rendimiento

1. **Caching**: Resultados de análisis técnico
2. **Paralelización**: Análisis de múltiples símbolos
3. **Optimización de memoria**: Gestión eficiente de datos históricos
4. **Base de datos**: Almacenamiento persistente de resultados

### Escalabilidad

- **Multi-símbolo**: Análisis simultáneo de múltiples activos
- **Multi-timeframe**: Análisis en diferentes marcos temporales
- **Distributed computing**: Procesamiento distribuido para análisis complejos

---

**📝 Nota**: Esta documentación está en constante evolución. Para la versión más actualizada, consulta el código fuente y los comentarios inline.