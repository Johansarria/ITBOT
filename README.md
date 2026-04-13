# 🤖 ITBOT — Sistema de Trading Algorítmico Autónomo con IA

Bot de trading autónomo multi-estrategia para **Binance Spot y Futuros** con Machine Learning integrado, gestión de riesgo dinámica, dashboard web en tiempo real y control total vía **Telegram**. Diseñado para operar en mercados cripto 24/7 de forma autónoma.

---

## 🎯 Objetivo del Proyecto

ITBOT es un sistema de trading algorítmico de nivel institucional que combina:
- **Señales ML** (modelos entrenados con +70.000 velas históricas de Binance)
- **Análisis técnico multi-indicador** (RSI, MACD, ADX, Bollinger Bands, ATR)
- **Gestión de riesgo dinámica** con circuit breakers, trailing stops y break-even automático
- **Control por Telegram** para operar, monitorear y pausar el bot desde tu teléfono
- **Paper Trading / Simulación** completa antes de operar con capital real

---

## 🗂️ Arquitectura del Sistema

```
ITBOT/
│
├── 🧠 Core del Bot
│   ├── config.py                     # Configuración central (Pydantic Settings)
│   ├── run_bot.py                    # Punto de entrada principal
│   ├── listener_bot.py               # Listener de comandos Telegram
│   ├── main_trading_bot.py           # Motor principal de trading
│   └── trade_executor.py             # Ejecutor de órdenes en Binance
│
├── 📊 Estrategias de Trading
│   ├── adaptive_trading_strategies.py    # Estrategias adaptativas multi-régimen
│   ├── dynamic_risk_manager.py           # Gestor de riesgo dinámico
│   ├── risk_management.py                # Lógica SL/TP/Trailing
│   ├── trading_signals.py                # Motor de señales técnicas
│   ├── market_analyzer.py                # Análisis de mercado en tiempo real
│   └── strategies/                       # Módulo de estrategias adicionales
│
├── 🤖 Módulo de IA/ML
│   ├── ai_module/                        # Módulo de predicción ML
│   ├── ml_model_trainer.py               # Entrenamiento de modelos
│   ├── build_feature_store.py            # Feature engineering
│   └── train_pipeline.py                 # Pipeline de entrenamiento
│
├── 🌐 Dashboard Web
│   ├── dashboard_web.py                  # API Flask + Dashboard
│   ├── web/app.py                        # Aplicación web principal
│   └── assets/                           # Archivos estáticos del dashboard
│
├── 📡 Backtesting & Simulación
│   ├── advanced_backtester.py            # Backtester avanzado con métricas
│   ├── binance_backtester_v4_ultra.py    # Backtester V4 con datos reales
│   ├── paper_trading_realtime.py         # Paper trading en tiempo real
│   ├── final_simulation.py               # Simulación completa del sistema
│   └── real_time_trading_simulator.py    # Simulador de trading en vivo
│
├── 🗄️ Base de Datos & Auditoría
│   ├── database/                         # Modelos y gestión de DB
│   ├── alembic/                          # Migraciones de database
│   ├── utils/audit_db.py                 # DB de auditoría de operaciones
│   └── json_logger.py                    # Logger estructurado en JSON/JSONL
│
├── 📈 Análisis Específicos por Mercado
│   ├── eurusd_strategy_system.py         # Sistema EUR/USD
│   ├── audcad_strategy_system.py         # Sistema AUD/CAD
│   ├── nas100_strategy_system.py         # Sistema NAS100
│   ├── xauusd_strategy_system.py         # Sistema XAU/USD (Oro)
│   └── integrate_nas100.py               # Integración con datos NAS100
│
├── 🔧 Infraestructura
│   ├── docker-compose.yml                # Orquestación Docker
│   ├── Dockerfile                        # Imagen Docker del bot
│   ├── monitoring_system.py              # Sistema de monitoreo y alertas
│   └── backup_logs_system.py             # Respaldo automático de logs
│
└── 📋 Documentación
    ├── README.md                         # Este archivo
    ├── GUIA_IMPLEMENTACION_PRODUCCION.md # Guía de despliegue en producción
    ├── strategy_documentation.md         # Documentación de estrategias
    └── ANALISIS_COMPLETO_PROYECTO.md     # Análisis técnico del sistema
```

---

## 🧠 Modelos de IA y Estrategias

### Estrategias Implementadas

| Estrategia | Objetivo Diario | Instrumentos | Descripción |
|------------|-----------------|--------------|-------------|
| Adaptive V3 | 1% diario | BTC, ETH, SOL | Estrategia adaptativa multi-régimen con ML |
| Conservative 15% | 15% mensual | Top cripto | Baja frecuencia, alta selectividad |
| Aggressive 15% | 15% mensual | Top cripto | Mayor frecuencia, umbrales dinámicos |
| Dynamic Probability | Variable | Binance Spot | Probabilidad dinámica de éxito |
| Ultra Selective | Óptimo | Multi-símbolo | Máxima selectividad, mínimo riesgo |

### Motor de ML

- **Datos de entrenamiento:** +70.000 velas históricas de Binance (8 años)
- **Accuracy objetivo:** 61.7% (validado en datos reales)
- **Umbrales adaptativos:** Se ajustan dinámicamente cada 24h
- **Confluencia técnica:**  MACD + ADX requeridos para confirmar señales ML

---

## 🚀 Instalación y Uso

### Prerrequisitos
- Python 3.10+
- Docker y Docker Compose (recomendado para producción)
- Cuenta de Binance con API habilitada

### 1. Clonar el repositorio
```bash
git clone https://github.com/Johansarria/ITBOT.git
cd ITBOT
```

### 2. Crear entorno virtual e instalar dependencias
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# o: venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 3. Configurar variables de entorno
```bash
cp .env.example .env
nano .env  # Editar con tus credenciales reales
```

Variables requeridas en `.env`:
```env
# Telegram
TELEGRAM_BOT_TOKEN=tu_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id
ADMIN_TELEGRAM_ID=tu_admin_id
KILL_SWITCH_PASSWORD=clave_secreta_segura

# Binance
BINANCE_API_KEY=tu_api_key
BINANCE_SECRET_KEY=tu_secret_key

# Modo (empieza en paper trading)
PRODUCTION_MODE=False
PAPER_TRADING=True
```

### 4. Iniciar en modo Paper Trading (recomendado)
```bash
python run_bot.py
```

### 5. Producción con Docker
```bash
docker-compose up -d
```

---

## 📊 Panel de Control (Telegram)

Una vez iniciado, el bot responde a estos comandos desde Telegram:

| Comando | Función |
|---------|---------|
| `/start` | Menú principal del bot |
| `/estado` | Estado actual: balance, posiciones abiertas |
| `/señales` | Señales activas de todos los pares |
| `/pausar` | Pausa el bot (no cierra posiciones) |
| `/kill` | Kill switch: cierra todo y detiene el bot |
| `/backtest` | Ejecuta backtest con datos recientes |

---

## 🔐 Seguridad

- **Nunca** subas tu archivo `.env` a GitHub (ya está en `.gitignore`)
- Las **API Keys de Binance** deben tener permisos mínimos (solo lectura + trading, sin retiros)
- El **Kill Switch** requiere contraseña configurada en `.env`
- Para producción, usa el **Testnet de Binance** primero (`BINANCE_USE_TESTNET_SPOT=True`)

---

## 📈 Métricas de Backtesting (Resultados Históricos)

| Período | Win Rate | Retorno | Max Drawdown |
|---------|----------|---------|--------------|
| 30 días | ~57% | +8.2% | -3.1% |
| 60 días | ~55% | +14.5% | -4.8% |
| 90 días | ~54% | +19.3% | -6.2% |

> ⚠️ Rendimientos pasados no garantizan resultados futuros.

---

## 🛠️ Tecnologías

| Librería | Uso |
|----------|-----|
| `ccxt` | Conexión a Binance API |
| `python-telegram-bot` | Interface de control vía Telegram |
| `pandas` / `numpy` | Procesamiento de datos de mercado |
| `scikit-learn` / `xgboost` | Modelos de Machine Learning |
| `SQLAlchemy` + `Alembic` | ORM y migraciones de base de datos |
| `Flask` | Dashboard web de monitoreo |
| `Docker` | Containerización y despliegue |
| `Redis` | Cola de decisiones de trading |

---

## ⚠️ Disclaimer

> Este proyecto es **educativo y experimental**. El trading algorítmico conlleva riesgos significativos de pérdida de capital. Comienza siempre en modo **Paper Trading** antes de operar con dinero real. No constituye asesoramiento financiero.

---

## 👤 Autor

**Johan Sarria**  
GitHub: [@Johansarria](https://github.com/Johansarria)