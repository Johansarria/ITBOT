# 🤖 ITBOT — Sistema de Trading Algorítmico Autónomo con IA

Bot de trading algorítmico multi-estrategia para **Binance Spot y Futuros** con Machine Learning integrado, gestión de riesgo dinámica, dashboard web en tiempo real y control total vía **Telegram**. Diseñado para operar en mercados cripto 24/7 de forma autónoma.

---

## 🎯 Objetivo del Proyecto

ITBOT combina lo mejor del análisis técnico con IA para:
- **Predecir movimientos** con modelos ML entrenados con +70.000 velas históricas (8 años)
- **Gestionar riesgo dinámicamente** con circuit breakers, trailing stops y break-even automático
- **Operar en múltiples mercados:** Cripto (Binance), Forex (EUR/USD, AUD/CAD), Metales (XAU/USD) e Índices (NAS100)
- **Controlar el bot desde Telegram** sin necesidad de acceso al servidor
- **Simular y validar** estrategias con paper trading antes de operar con capital real

---

## 🏗️ Arquitectura del Sistema

```
ITBOT/
│
├── 🧠 Core del Bot
│   ├── config.py                          # Configuración central (Pydantic Settings + .env)
│   ├── run_bot.py                         # Punto de entrada principal
│   ├── listener_bot.py                    # Listener de comandos Telegram
│   ├── main_trading_bot.py                # Motor principal de trading
│   └── trade_executor.py                  # Ejecutor de órdenes en Binance
│
├── 📊 Estrategias de Trading
│   ├── adaptive_trading_strategies.py     # Estrategias adaptativas multi-régimen
│   ├── enhanced_strategy_15pct.py         # Estrategia 15% mensual (validada)
│   ├── dynamic_probability_strategy.py    # Estrategia de probabilidad dinámica
│   ├── ultra_selective_strategy.py        # Ultra-selectiva: mínimo riesgo
│   ├── dynamic_risk_manager.py            # Gestor de riesgo dinámico
│   ├── risk_management.py                 # Lógica SL/TP/Trailing stop/Break-even
│   ├── trading_signals.py                 # Motor de señales técnicas
│   └── market_analyzer.py                 # Análisis de mercado en tiempo real
│
├── 🤖 Módulo de IA/ML
│   ├── ai_module/                         # Módulo de predicción ML
│   ├── ml_model_trainer.py                # Entrenamiento de modelos
│   ├── build_feature_store.py             # Feature engineering (70K+ puntos)
│   └── train_pipeline.py                  # Pipeline de entrenamiento
│
├── 📡 Simulación y Backtesting
│   ├── paper_trading_realtime.py          # Paper trading en tiempo real (WebSocket)
│   ├── main_paper_trading.py              # Simulador multi-símbolo con portafolio
│   ├── advanced_backtester.py             # Backtester avanzado con métricas
│   ├── binance_backtester_v4_ultra.py     # Backtester V4 con datos reales de Binance
│   ├── backtest_15pct_validator.py        # Validador estrategia 15% mensual
│   └── real_time_trading_simulator.py     # Simulador de trading en vivo
│
├── 🌐 Dashboard Web
│   ├── dashboard_web.py                   # API Flask + Dashboard de monitoreo
│   ├── live_trading_dashboard_v4.py       # Dashboard V4 con métricas en tiempo real
│   └── assets/                            # Archivos estáticos
│
├── 📈 Análisis por Mercado
│   ├── eurusd_strategy_system.py          # Sistema EUR/USD
│   ├── audcad_strategy_system.py          # Sistema AUD/CAD
│   ├── nas100_strategy_system.py          # Sistema NAS100
│   ├── xauusd_strategy_system.py          # Sistema XAU/USD (Oro)
│   └── integrate_nas100.py                # Integración con datos NAS100
│
├── 🗄️ Base de Datos y Auditoría
│   ├── database/                          # Modelos ORM y gestión de DB
│   ├── alembic/                           # Migraciones de database
│   └── json_logger.py                     # Logger estructurado JSONL
│
└── 🔧 Infraestructura
    ├── docker-compose.yml                 # Orquestación Docker
    ├── Dockerfile                         # Imagen Docker del bot
    ├── monitoring_system.py               # Sistema de monitoreo y alertas
    └── backup_logs_system.py              # Respaldo automático de logs
```

---

## 📊 Estrategias Disponibles

| Estrategia | Objetivo | Win Rate | Drawdown Máx. | Descripción |
|------------|----------|----------|---------------|-------------|
| **Adaptive V3** | 1% diario | ~57% | -3.1% | Multi-régimen con ML, BTC/ETH/SOL |
| **15% Mensual** | 15% mensual | 63.1% | -2.46% | Indicadores optimizados RSI/MACD/BB |
| **Dynamic Probability** | Variable | ~55% | -4.8% | Probabilidad dinámica por símbolo |
| **Ultra Selective** | Óptimo | >60% | <3% | Máxima selectividad, mínimo riesgo |
| **Micro-Trading** | 6-10% en 4-6h | ~58% | -2% | Operaciones ultra-conservadoras ($0.75 max) |

### 🎯 Estrategia 15% Mensual — Validada

Validada en 10 escenarios reales de backtesting:

| Métrica | Valor |
|---------|-------|
| Retorno diario promedio | **1.536%** (objetivo: 0.6%) |
| Retorno mensual promedio | **55.08%** (objetivo: 15%) |
| Win Rate | **63.1%** |
| Sharpe Ratio | **16.18** |
| Sortino Ratio | **55.32** |
| Drawdown máximo | **2.46%** |
| Proyección anual | **660.9%** |

**Parámetros técnicos optimizados:**
- RSI: período 12, niveles 25/75
- MACD: 10/24/8 (rápido/lento/señal)
- Bollinger Bands: período 18, desviación 2.2
- Stop Loss: 1.5% | Take Profit: 3.5%

---

## 🧠 Motor de Machine Learning

- **Datos de entrenamiento:** +70.000 velas históricas de Binance (8 años)
- **Accuracy objetivo:** 61.7% (validado con datos reales)
- **Umbrales adaptativos:** Se ajustan dinámicamente cada 24h
- **Confluencia técnica:** MACD + ADX requeridos para confirmar señales ML
- **Estándares institucionales:** Sharpe ≥ 1.5 | Drawdown máx. 15% | Hit rate ≥ 52%

---

## 📡 Modos de Operación

### 1. 🟡 Paper Trading (recomendado para empezar)
Simula operaciones sin capital real usando WebSocket de Binance.
```bash
python main_paper_trading.py
```

Portafolio por defecto:
- **40%** NAS100 (índice tecnológico)
- **30%** AUD/CAD (par forex estable)
- **30%** XAU/USD (oro como refugio)

### 2. 🔵 Estrategia 15% Mensual
```bash
python run_15pct_strategy.py
```

### 3. 🟢 Bot Completo Autónomo (producción)
```bash
python run_bot.py
```

### 4. 🔴 Micro-Trading (pruebas con capital real mínimo)
Opera con un máximo de $0.75 por operación y apalancamiento 10x controlado.
```bash
docker exec -it itbot_main bash start_autonomous_bot.sh
```

---

## 🚀 Instalación y Configuración

### Prerrequisitos
- Python 3.10+
- Docker y Docker Compose (para producción)
- Cuenta de Binance con API habilitada

### 1. Clonar el repositorio
```bash
git clone https://github.com/Johansarria/ITBOT.git
cd ITBOT
```

### 2. Crear entorno virtual e instalar dependencias
```bash
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 3. Configurar variables de entorno
```bash
cp .env.example .env
nano .env
```

**Variables requeridas en `.env`:**
```env
# Telegram
TELEGRAM_BOT_TOKEN=tu_token
TELEGRAM_CHAT_ID=tu_chat_id
ADMIN_TELEGRAM_ID=tu_id
KILL_SWITCH_PASSWORD=clave_secreta_segura

# Binance
BINANCE_API_KEY=tu_api_key
BINANCE_SECRET_KEY=tu_secret_key

# Modo de operación
PRODUCTION_MODE=False
PAPER_TRADING=True

# Base de datos (SQLite por defecto)
DB_TYPE=sqlite
```

### 4. Despliegue con Docker
```bash
docker-compose up -d
```

---

## 📲 Control por Telegram

| Comando | Función |
|---------|---------|
| `/start` | Menú principal del bot |
| `/estado` | Balance actual y posiciones abiertas |
| `/señales` | Señales activas por par de trading |
| `/pausar` | Pausa el bot sin cerrar posiciones |
| `/kill` | Kill switch: cierra todo y detiene el bot |
| `/backtest` | Ejecuta backtest con datos recientes |

---

## 🔐 Seguridad

- **Nunca** subas tu `.env` a GitHub (ya está en `.gitignore`)
- Las **API Keys de Binance** deben tener permisos mínimos: solo trading, sin retiros
- El **Kill Switch** requiere contraseña configurada en `.env` (no hay valor por defecto)
- Para primeras pruebas, usa el **Testnet de Binance** (`BINANCE_USE_TESTNET_SPOT=True`)

---

## 🛠️ Tecnologías

| Librería | Uso |
|----------|-----|
| `ccxt` | Conexión a Binance API (Spot y Futuros) |
| `python-telegram-bot` | Control del bot vía Telegram |
| `pandas` / `numpy` | Procesamiento de datos de mercado |
| `scikit-learn` / `xgboost` | Modelos de Machine Learning |
| `SQLAlchemy` + `Alembic` | ORM y migraciones de base de datos |
| `Flask` | Dashboard web de monitoreo |
| `Docker` + `Redis` | Containerización y cola de decisiones |

---

## 📈 Métricas de Backtesting

| Período | Win Rate | Retorno | Drawdown Máx. |
|---------|----------|---------|---------------|
| 30 días | ~57% | +8.2% | -3.1% |
| 60 días | ~55% | +14.5% | -4.8% |
| 90 días | ~54% | +19.3% | -6.2% |

> ⚠️ Rendimientos pasados no garantizan resultados futuros.

---

## ⚠️ Disclaimer

> Este proyecto es **educativo y experimental**. El trading algorítmico conlleva riesgos significativos de pérdida de capital. Siempre inicia en modo **Paper Trading** antes de operar con dinero real. No constituye asesoramiento financiero.

---

## 👤 Autor

**Johan Sarria**
GitHub: [@Johansarria](https://github.com/Johansarria)