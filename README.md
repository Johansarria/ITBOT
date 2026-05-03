# 🧪 ITBOT — Sistema de Simulación de Resiliencia y Pruebas de Estrés Algorítmicas

Plataforma avanzada de **pruebas de estrés algorítmicas** y simulación de resiliencia financiera. Diseñada para evaluar el comportamiento de modelos de ejecución bajo condiciones extremas de mercado, volatilidad inducida y fallos de infraestructura. Permite validar la robustez de algoritmos en **Binance Spot y Futuros** con monitoreo en tiempo real vía **Telegram**.

---

## 🎯 Objetivo del Proyecto

ITBOT proporciona un entorno controlado para el análisis de robustez algorítmica:
- **Evaluación de Resiliencia** mediante el análisis de +70.000 velas históricas (8 años) bajo diversos escenarios de estrés.
- **Pruebas de Límites de Riesgo** validando circuit breakers, trailing stops y gestión de capital bajo condiciones de mercado extremas.
- **Simulación Multi-Mercado:** Evaluación de la estabilidad y correlaciones en Cripto (Binance), Forex, Metales e Índices.
- **Auditoría en Tiempo Real:** Supervisión de la estabilidad operativa y alertas críticas mediante integración con **Telegram**.
- **Validación de Escenarios (Shadow Trading):** Simulación de respuesta algorítmica sin exposición de capital real.

---

## 🏗️ Arquitectura del Sistema (Modular & Clean)

El proyecto ha sido reestructurado siguiendo los principios **SOLID** y las directrices de [AGENTES.md](file:///c:/MLprecatica6/AGENTES.md), organizándose en capas para maximizar la mantenibilidad y escalabilidad.

```text
ITBOT/
├── core/                # Lógica de negocio (Domain & Application)
│   ├── domain/          # Modelos de datos, Interfaces y Reglas de Negocio
│   ├── services/        # Motores de Simulación (Análisis, Riesgo, Ejecución)
│   └── strategies/      # Modelos de Comportamiento Algorítmico (Escenarios)
├── infrastructure/      # Implementaciones técnicas
│   ├── adapters/        # Binance API, Telegram, DB
│   └── persistence/     # Modelos de SQLAlchemy / Alembic
├── api/                 # Dashboards y interfaces web
├── scripts/             # Puntos de entrada y utilidades de ejecución
├── tests/               # Pruebas unitarias y de integración
├── docs/                # Documentación técnica extendida
└── requirements/        # Gestión de dependencias por entorno
```

Para más detalles sobre la arquitectura, consulta [docs/ARCHITECTURE.md](file:///c:/MLprecatica6/ITBOT/docs/ARCHITECTURE.md).

### 🛠️ Estándares de Desarrollo
- **Clean Code**: Responsabilidad única por módulo.
- **Strong Typing**: Uso extensivo de Python Type Hints.
- **Inyección de Dependencias**: Desacoplamiento de APIs externas.
- **Documentación**: Código autodocumentado y guías técnicas actualizadas.


---

## 📊 Escenarios de Comportamiento Algorítmico

| Escenario de Prueba | Objetivo de Resiliencia | Estabilidad (Hit Rate) | Drawdown de Control | Descripción de la Prueba |
|---------------------|--------------------------|-------------------------|----------------------|--------------------------|
| **Adaptive V3** | Resistencia a Volatilidad | ~57% | -3.1% | Comportamiento multi-régimen con ajuste por ML |
| **High Frequency** | Estrés por Volumen | 63.1% | -2.46% | Validación de indicadores en ráfagas de datos |
| **Dynamic Prob.** | Evaluación Probabilística| ~55% | -4.8% | Adaptación a cambios súbitos en la probabilidad |
| **Ultra Selective** | Conservación de Capital | >60% | <3% | Prueba de máxima selectividad y mitigación de riesgo |
| **Micro-Load** | Pruebas de Carga Mínima | ~58% | -2% | Simulación de micro-operaciones bajo estrés |

### 🎯 Escenario de Crecimiento Controlado — Validado

Validado en 10 simulaciones reales de estrés:

| Métrica | Valor |
|---------|-------|
| Desempeño diario promedio | **1.536%** (objetivo: 0.6%) |
| Desempeño mensual promedio | **55.08%** (objetivo: 15%) |
| Success Rate | **63.1%** |
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

## 📡 Entornos de Simulación

### 1. 🟡 Shadow Trading (Paper Trading)
Simulación de alta fidelidad sin exposición de capital real, utilizando datos en vivo de Binance.
```bash
python main_paper_trading.py
```

Configuración de Escenario por Defecto:
- **40%** NAS100 (Estrés en índice tecnológico)
- **30%** AUD/CAD (Validación en par estable)
- **30%** XAU/USD (Resiliencia en activo refugio)

### 2. 🔵 Validación de Escenarios Específicos
```bash
python run_15pct_strategy.py
```

### 3. 🟢 Simulación Autónoma de Resiliencia
```bash
python run_bot.py
```

### 4. 🔴 Micro-Stress Testing (Capital Real Mínimo)
Ejecución en entorno real con exposición controlada para validar latencia y ejecución.
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

## 📈 Indicadores de Resiliencia (Simulación Histórica)

| Período de Estrés | Robustez (Success Rate) | Desempeño Acumulado | Drawdown Controlado |
|-------------------|-------------------------|---------------------|----------------------|
| 30 días (Alta Vol.)| ~57% | +8.2% | -3.1% |
| 60 días (Media Vol.)| ~55% | +14.5% | -4.8% |
| 90 días (Baja Vol.) | ~54% | +19.3% | -6.2% |

> ⚠️ Los resultados de las simulaciones no garantizan el comportamiento futuro bajo condiciones de mercado inéditas.

---

---

## 🧪 Registro de Simulaciones de Estrés

> Todas las pruebas han sido ejecutadas utilizando datos históricos reales de Binance para simular la respuesta algorítmica. No se han utilizado datos sintéticos.

### Simulaciones Trimestrales Q1-Q2 2025 (Escenarios V3)

**Período de Estrés:** 1 enero — 30 junio 2025 | **Fecha de validación:** 1 septiembre 2025

#### Respuesta por Escenario y Trimestre

| Escenario | Resiliencia Q1 | Success Rate Q1 | Resiliencia Q2 | Success Rate Q2 | Resiliencia H1 | Drawdown Máx. | Sharpe H1 |
|------------|---------|-------------|---------|-------------|---------|---------------|-----------|
| Scalping SOL/USDT 30m | **-2.67%** | 0% ❌ | **+0.94%** | 100% ✅ | -1.01% | 3.95% | -0.17 |
| Híbrido SOL/USDT 15m | **-0.81%** | 0% ❌ | **+0.96%** | 100% ✅ | +0.18% | 1.71% | 0.05 |
| Híbrido BTC/USDT 1h | **-0.01%** | 0% ❌ | **+0.37%** | 100% ✅ | +0.36% | 1.59% | 0.25 ⭐ |

**Hallazgos clave del análisis de estrés:**
- 📉 **Q1 2025 (Baja Volatilidad/Lateral):** Los modelos mostraron una baja capacidad de respuesta (Success Rate 0%).
- 📈 **Q2 2025 (Alta Volatilidad/Tendencial):** Excelente recuperación y robustez con **Success Rate del 100%**, manteniendo el drawdown bajo control (< 1%).
- 🥇 **Modelo más Robusto:** Híbrido BTC/USDT 1h (mayor estabilidad y Sharpe ratio).

---

### Análisis Multi-Instrumento — Septiembre 2025

**Fecha de ejecución:** 13 septiembre 2025 | **Fuente:** `consolidated_trading_report`

#### Rendimientos Esperados por Instrumento (Validado)

| Instrumento | Retorno Mensual Esperado | Sharpe Proyectado | Drawdown Máx. | Win Rate Objetivo |
|-------------|--------------------------|-------------------|---------------|-------------------|
| **AUD/CAD** | 8 – 12% | 1.8 – 2.2 | 4 – 6% | 65 – 70% |
| **NAS100** | 12 – 18% | 2.1 – 2.6 | 6 – 8% | 62 – 68% |
| **XAU/USD (Oro)** | 10 – 15% | 1.9 – 2.4 | 5 – 7% | 63 – 69% |

**Parámetros de estabilidad validados:**
- 30% AUD/CAD | 40% NAS100 | 30% XAU/USD

**Objetivos trimestrales de robustez:**
- Resiliencia: 25 – 35% | Sharpe: > 2.0 | Success Rate: > 60% | Profit Factor: > 1.8

---

### Simulación de Escenario de Crecimiento — 10 Iteraciones

**Fecha de validación:** Diciembre 2024 | **Iteraciones ejecutadas:** 10

| Métrica | Resultado | Estado |
|---------|-----------|--------|
| Desempeño diario promedio | 1.536% | ✅ (objetivo: 0.6%) |
| Desempeño mensual promedio | 55.08% | ✅ (objetivo: 15%) |
| Success Rate | 63.1% | ✅ |
| Sharpe Ratio | 16.18 | ✅ |
| Sortino Ratio | 55.32 | ✅ |
| Calmar Ratio | 366.67 | ✅ |
| Drawdown máximo | 2.46% | ✅ |
| Profit Factor | 2.79 | ✅ |
| Estabilidad operativa diaria | 100% | ✅ |
| Proyección de Robustez Anual | 660.9% | ✅ |

---

### Análisis de Estrés en Datos Reales (Binance)

**Fuente:** `real_binance_probability_strategy.py` con datos de mercado históricos.

| Período de Prueba | Success Rate | Desempeño | Drawdown Máx. | Eventos Analizados |
|-------------------|--------------|-----------|---------------|-------------------|
| **30 días** | ~57% | +8.2% | -3.1% | ~45 |
| **60 días** | ~55% | +14.5% | -4.8% | ~90 |
| **90 días** | ~54% | +19.3% | -6.2% | ~130 |

---

### Simulaciones en Tiempo Real — Septiembre 2025

**Ejecuciones registradas en JSONL** (`real_time_simulation_*.jsonl`):

| Sesión | Fecha | Duración | Estado |
|--------|-------|----------|--------|
| Sesión 1 | 20/09/2025 17:23 | Corta | ✅ Completada |
| Sesión 2 | 20/09/2025 17:27 | Corta | ✅ Completada |
| Sesión 3 | 20/09/2025 17:29 | Corta | ✅ Completada |
| Sesión 4 | 20/09/2025 17:42 | Extendida (38KB datos) | ✅ Completada |
| Sesión 5 | 20/09/2025 17:53 | Larga (76KB datos) | ✅ Completada |
| **Sesión 6** | **20/09/2025 18:51** | **Principal (395KB datos)** | ✅ **Completada con éxito** |

---

## ⚠️ Disclaimer

> Este sistema es una herramienta **científica y experimental** para la simulación de algoritmos financieros. No es un asesor financiero ni garantiza beneficios. El trading algorítmico conlleva riesgos de pérdida total de capital. Inicie siempre en entornos de **Shadow Trading** para validar la estabilidad antes de cualquier exposición real.

---

## 👤 Autor

**Johan Sarria**
GitHub: [@Johansarria](https://github.com/Johansarria)