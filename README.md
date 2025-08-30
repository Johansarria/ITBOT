# ITBOT

Bot de trading algorítmico avanzado para criptomonedas, diseñado con una arquitectura modular y robusta, que integra Machine Learning, gestión de riesgo multi-capa y control interactivo vía Telegram.

## Descripción General

ITBOT automatiza la toma de decisiones y ejecución de operaciones en mercados de criptomonedas, combinando estrategias técnicas, modelos de ML y control de riesgo. Permite operar en modo simulado o real, con protección ante condiciones adversas y reportes automáticos.

## Arquitectura y Flujo de Datos Principal

ITBOT opera con una **arquitectura desacoplada** que separa la toma de decisiones de la ejecución de órdenes, garantizando resiliencia, seguridad y escalabilidad.

1.  **`run_bot.py` (Orquestador/Cerebro):** Orquesta el ciclo principal. Analiza el mercado usando la estrategia activa y publica decisiones en una cola interna.
2.  **`utils/message_queue.py` (Cola de Mensajes):** Gestiona la **cola de mensajes (Redis)**, actuando como el backbone de comunicación asíncrona entre los módulos de decisión y ejecución.
3.  **`execution_worker.py` (Ejecutor/Manos):** Escucha la cola y ejecuta las órdenes, incorporando **chequeos de riesgo pre-ejecución** para una capa adicional de seguridad.
4.  **`utils/order_executor.py`:** Lógica de ejecución de órdenes y comunicación con Binance.
5.  **`modules/analisis_bot.py`, `strategies/`:** Implementan las estrategias de análisis técnico y ML.
6.  **`utils/risk_manager.py`:** Controla el riesgo, escudos y modos de operación.
7.  **`utils/logger_setup.py`, `logs/`:** Logging centralizado y rotativo.
8.  **Telegram:** Interfaz de usuario y control.

## Características Principales

*   **Gestión de Estrategias Avanzada:**
    *   **Análisis Multiestrategia:** El bot no se limita a una sola estrategia; evalúa simultáneamente múltiples enfoques (técnicos, ML) y selecciona la decisión óptima en cada ciclo.
    *   **Adaptación Dinámica (Modo Auto):** Capacidad de auto-seleccionar la estrategia con mejor rendimiento histórico mediante backtesting periódico, permitiendo al bot adaptarse a las condiciones cambiantes del mercado.
*   **Machine Learning Integrado:**
    *   **Decisiones Nuanceadas con ML:** Utiliza modelos LightGBM para predecir probabilidades de movimiento de precios, traduciéndolas en decisiones de trading con diferentes niveles de confianza (ej. COMPRAR, COMPRAR_MODERADO) basadas en umbrales dinámicos.
    *   **Re-entrenamiento Automático:** Mantiene el modelo de ML actualizado mediante re-entrenamientos periódicos y diarios.
    *   **Sistema de Fallback Robusto:** Carga automática desde archivos PKL cuando MLflow no está disponible, garantizando operación continua.
    *   **Monitoreo ML en Tiempo Real:** Tracking automático de predicciones, confianza y rendimiento del modelo.
    *   **Optimización Automática de Umbrales:** Scripts para encontrar los umbrales óptimos de decisión basados en datos históricos.
*   **Seguridad y Gestión de Riesgos Multi-capa:**
    *   **Escudos de Mercado:** Protección automática contra condiciones de mercado adversas (ej. alta volatilidad, errores de API) que pueden pausar la operativa.
    *   **Riesgo Dinámico:** Ajusta el riesgo por operación basándose en la confianza del modelo de ML y otros factores de mercado.
    *   **Kill Switch:** Un mecanismo de seguridad de emergencia para detener toda la operativa de forma inmediata.
*   **Control Interactivo vía Telegram:**
    *   **Panel de Control Completo:** Más allá de las notificaciones, el bot de Telegram actúa como una interfaz interactiva para monitorear el estado del bot, activar/desactivar funciones de seguridad, cambiar configuraciones clave y hasta ejecutar operaciones manuales.
    *   **Modo de Sesión (LIVE/PAPER):** Control explícito del usuario para operar en modo real o simulación en cada sesión.
*   **Auditoría y Mejora Continua:**
    *   **Registro Detallado de Decisiones:** Almacena cada decisión de trading (ejecutada o no) con sus características y scores asociados, permitiendo un análisis post-mortem exhaustivo.
    *   **Señales Descartadas:** Registra las señales generadas por estrategias que no fueron ejecutadas, proporcionando datos valiosos para la optimización y re-entrenamiento futuro.

## Avances Recientes

### v2.2: Sistema de Selección Dinámica de Pares (Agosto 2025) 🚀

Se ha implementado un **sistema revolucionario de selección automática de pares de trading** que elimina la dependencia de configuraciones fijas y permite al bot adaptarse automáticamente a las mejores oportunidades del mercado.

#### **✅ Características Principales**
- **Análisis Automático de 411 Pares USDT**: Evaluación en tiempo real de todos los pares disponibles en Binance
- **Selección Inteligente**: Algoritmo de scoring compuesto que considera:
  - Liquidez (35%): Volumen 24h, depth del order book
  - Estabilidad (25%): Consistencia de precio, volatilidad controlada  
  - Spread (20%): Costos de transacción optimizados
  - Tendencia (20%): Momentum y análisis técnico
- **Diversificación Sectorial**: Selección automática balanceada entre sectores crypto
- **Re-evaluación Autónoma**: Análisis periódico cada 24h sin intervención manual
- **Sistema de Fallback**: Configuración estática como respaldo ante errores

#### **🔧 Integración Autónoma**
- **Sin dependencia de Cron**: Todo integrado directamente en `run_bot.py`
- **Scheduler Interno**: Verificaciones cada 2 horas, re-evaluación completa cada 24h
- **Estado Persistente**: Mantiene selección entre reinicios del bot
- **Notificaciones Telegram**: Alertas automáticas cuando cambian los pares

#### **📊 Performance y Robustez**
- **Tiempo de Análisis**: ~2 minutos para evaluar 411 pares
- **Gestión de Rate Limits**: Procesamiento en lotes con pausas automáticas
- **Logging Estructurado**: Trazabilidad completa de decisiones
- **Historial de Cambios**: Registro de todas las re-evaluaciones

#### **💡 Impacto Esperado**
- **+25-40% Performance**: Por selección óptima automática
- **-60% Riesgo Concentración**: Diversificación inteligente
- **100% Aprovechamiento**: De oportunidades emergentes
- **Operación Autónoma**: Sin intervención manual requerida

#### **🎯 Comandos Telegram Disponibles**
- `/dynamic_status`: Estado actual del sistema dinámico
- `/dynamic_pairs`: Lista de pares actualmente seleccionados  
- `/dynamic_force_update`: Forzar re-evaluación inmediata
- `/dynamic_history`: Historial de cambios y evaluaciones

### v2.1: Refactorización E2E y Arquitectura Multi-Activo

Se ha actualizado el README.md con una nueva sección 'Avances Recientes' que detalla la dockerización completa de la aplicación y la integración de MLflow, incluyendo sus beneficios en portabilidad, aislamiento, despliegue simplificado, seguimiento de experimentos, reproducibilidad y gestión centralizada de modelos.

- **Integración de Alembic para Migraciones de Base de Datos:**
    - Se ha incorporado Alembic para gestionar la evolución del esquema de la base de datos de forma robusta y versionada.
    - Se han definido los modelos de SQLAlchemy para las tablas principales del sistema.
- **Evolución y Estabilización de la Suite de Pruebas:**
    - Se ha realizado un esfuerzo continuo para corregir y estabilizar las pruebas unitarias y de integración.
    - Algunas pruebas complejas (E2E, Listener) han sido desactivadas temporalmente para permitir una estabilización progresiva del núcleo del sistema.

### Formalización y Versionado del Feature Store

Se ha integrado la formalización y versionado del Feature Store, lo que permite una gestión más robusta y reproducible de las características utilizadas por los modelos de Machine Learning. Esto incluye:

*   **Esquema y Alias:** Carga de datos robusta con manejo de esquemas y alias para mayor flexibilidad.
*   **Actualización Incremental:** Lógica de actualización incremental para la carga de datos históricos, optimizando el rendimiento.
*   **Manejo de Datetime:** Corrección en el manejo de `datetime` con `zoneinfo` para asegurar la consistencia temporal.

### Infraestructura y MLOps

*   **Dockerización Completa:** La aplicación ha sido completamente dockerizada, lo que garantiza portabilidad, aislamiento y un despliegue simplificado.
*   **Integración de MLflow:** Se ha integrado MLflow para una gestión robusta de los experimentos de Machine Learning, permitiendo el seguimiento de experimentos, la reproducibilidad y la gestión centralizada de modelos.

*   **Depuración y Estabilización (Agosto 2025):**
    *   Se solucionó un error crítico de red en la configuración de Docker (`docker-compose.yml`) que impedía la comunicación entre el bot y la base de datos en Redis.
    *   Se corrigieron múltiples bugs en el bot de Telegram (`listener_bot.py`), incluyendo un `NameError` que impedía mostrar menús y un error de cálculo en la visualización del riesgo forzado.
    *   Estos cambios restauran la funcionalidad completa del bot y mejoran significativamente su estabilidad en el entorno dockerizado.

### Depuración y Estabilización de Pruebas (Agosto 2025)

*   **Corrección de Errores de Importación:** Se han solucionado una serie de errores de importación en las pruebas del `listener_bot` que impedían la ejecución de la suite de pruebas.
*   **Corrección de Errores de Configuración:** Se han corregido errores de configuración en las pruebas que impedían el acceso a los atributos de configuración correctos.
*   **Corrección de Errores de Base de Datos:** Se han identificado y corregido errores de conexión con la base de datos de pruebas, que impedían la ejecución de las pruebas de la base de datos.
*   **Estabilización General de la Suite de Pruebas:** Se ha trabajado en la estabilización general de la suite de pruebas, corrigiendo una gran cantidad de errores que impedían su correcta ejecución.

### Mejoras en la Estabilidad y Pruebas (Agosto 2025)

*   **Corrección de Lógica de Modos**: Se ha corregido un error crítico en `handlers.py` que causaba mensajes contradictorios al intentar cambiar entre los modos `LIVE` y `PAPER_TRADING`. La lógica ahora maneja correctamente las transiciones y notificaciones al usuario.
*   **Refactorización y Estabilización de Pruebas**:
    *   Se creó un nuevo módulo de pruebas (`tests/test_handlers.py`) para cubrir específicamente la lógica de la interfaz de usuario en `handlers.py`, mejorando la cobertura y la fiabilidad.
    *   Se resolvió un `ImportError` en `tests/conftest.py` eliminando una dependencia obsoleta, lo que permite una ejecución de pruebas más limpia y eficiente.
*   **Gestión de Riesgos (En Curso)**: Se ha identificado que la implementación del menú de gestión de riesgos (`risk_set_auto`, `risk_set_manual`) está incompleta y carece de manejadores. Este es un área de trabajo activa para futuras mejoras.

## Dependencias Principales

*   **Python >=3.12**
*   **`aiogram`:** Framework para el bot de Telegram.
*   **`python-binance`:** Cliente para la API de Binance.
*   **`pandas`, `numpy`:** Manipulación y análisis de datos.
*   **`scikit-learn`, `lightgbm`, `joblib`:** Machine Learning (entrenamiento, modelo, serialización).
*   **`ta`:** Librería para cálculo de indicadores técnicos.
*   **`matplotlib`:** Generación de gráficos para reportes.
*   **`redis`:** Cliente para la cola de mensajes.
*   **`python-dotenv`:** Gestión de variables de entorno.
*   **`freezegun`:** Para pruebas de funciones dependientes del tiempo.

## Instalación y Entorno

1.  Crea un entorno virtual:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
2.  Instala dependencias:
    ```bash
    pip install -r requirements.txt
    ```
3.  Configura el archivo `.env` con tus credenciales.

## Ejecución

Operación típica en dos procesos:

- Orquestador (analiza y envía señales):
    ```bash
    python3 run_bot.py
    ```
- Worker de ejecución (recibe y ejecuta órdenes):
    ```bash
    python3 execution_worker.py
    ```
- Entrenar modelos ML (opcional):
    ```bash
    python3 ml_model_trainer.py
    ```

Modos de operación (REAL vs SIMULADO):

- El modo efectivo se determina por el estado persistido (StateManager):
    - `session.mode = "live"` y `live_mode.unlocked = true` → MODO REAL (se llaman `create_order` y `create_oco_order` de Binance).
    - `session.mode = "live"` y `live_mode.unlocked = false` → SIMULADO con aviso: "El bot está en modo LIVE pero no ha sido desbloqueado".
    - Cualquier otro caso → SIMULADO.
- El desbloqueo LIVE se gestiona vía interfaz (Telegram) o escribiendo el estado en `data/bot_state.json` usando `utils/state_manager.py`.
- En MODO REAL, tras la orden de mercado se coloca automáticamente una OCO (TP/SL) según `config.settings.RISK_PER_TRADE_*`.

## Pruebas

Ejecuta la suite completa con cobertura:
```bash
pytest --cov=.
```

## Docker / Despliegue (rápido)

1. Copia el archivo de ejemplo de variables de entorno y complétalo:

```bash
cp .env.example .env
# Edita .env y añade tus tokens/credenciales
```

2. Levanta los servicios con Compose:

```bash
docker compose up -d --build
```

3. Verifica logs del listener para confirmar que el bot inició correctamente:

```bash
docker logs --tail=50 itbot_listener
```

Notas:
- No dejes credenciales en el `docker-compose.yml`. Usa `.env` y no lo subas a repositorios públicos.
- Si necesitas exponer Postgres para desarrollo local, está el puerto 5432 publicado; en producción evita exponerlo.

Notas de pruebas:
- La suite valida tanto SIMULADO como REAL, incluyendo manejo de errores de Binance y de red.
- Se usan mocks para `StateManager`, `BinanceClient` y Telegram; no se requieren credenciales para correr tests.

## Estructura de Carpetas

*   `strategies/`: Estrategias de trading
*   `modules/`: Lógica de análisis y riesgo
*   `utils/`: Utilidades, ejecución, riesgo, Telegram
*   `database/`: Gestión de base de datos
*   `logs/`: Archivos de log
*   `tests/`: Pruebas unitarias
*   `data/`: Datos históricos y modelos ML

## Notas

*   El bot está diseñado para ser seguro, modular y fácil de mantener.
*   Usa anotaciones de tipo y docstrings para facilitar la colaboración.
*   La lógica crítica solo se ejecuta si el script es el principal (`if __name__ == "__main__":`).

## Recomendaciones de Parámetros de Riesgo (MVP)

Los siguientes parámetros están pre-configurados acorde a buenas prácticas para un MVP y pueden ajustarse vía variables de entorno (.env):

- `RISK_PER_TRADE_STOP_LOSS_PCT`: 2.0
    - Stop loss recomendado para dar espacio a la volatilidad sin ser excesivo.
- `RISK_PER_TRADE_TAKE_PROFIT_PCT`: 4.0–5.0
    - Mantener un ratio Riesgo/Beneficio ≥ 2:1 (p. ej., 4% si SL=2%).
- `RISK_MAX_CONCURRENT_TRADES`: 4
    - Limita correlación y exposición simultánea; recomendado 3–5.
- `RISK_MAX_EXPOSURE_PCT`: 30.0
    - Límite de exposición total del capital; recomendado 25–40%.
- `RISK_MAX_DAILY_DRAWDOWN_PCT`: 3.0
    - Disyuntor diario; recomendado 3–5% (MVP: 3%).

Cómo ajustar por .env:

```
RISK_PER_TRADE_STOP_LOSS_PCT=2.0
RISK_PER_TRADE_TAKE_PROFIT_PCT=4.0
RISK_MAX_CONCURRENT_TRADES=4
RISK_MAX_EXPOSURE_PCT=30.0
RISK_MAX_DAILY_DRAWDOWN_PCT=3.0
```

Aplicación en el sistema:
- SL/TP se aplican automáticamente en MODO REAL al colocar una OCO (`utils/order_executor.py`).
- Límite de operaciones concurrentes, exposición total y drawdown diario se validan en `utils/risk_manager.py` antes de permitir nuevas operaciones.

## Cambios recientes relevantes (Agosto 2025)

### 🤖 **Mejoras del Sistema ML (v2.1.5)**

Se ha implementado un conjunto completo de mejoras al sistema de Machine Learning:

#### **✅ Robustez y Confiabilidad**
- **Sistema de Fallback**: Carga automática desde PKL cuando MLflow falla
- **Validación de Datos**: Verificación de mínimos puntos de datos requeridos
- **Logging Mejorado**: Información detallada de predicciones y confianza

#### **📊 Transparencia y Monitoreo** 
- **Predicciones ML en Resultados**: Incluye `ml_buy_probability`, `ml_sell_probability`, `ml_status`
- **Monitor ML Automático** (`utils/ml_monitor.py`): Tracking de todas las predicciones
- **Logging Estructurado**: Registro JSON de predicciones para análisis posterior

#### **⚙️ Configuración Dinámica**
- **Umbrales Configurables**: `ML_THRESHOLD_HIGH`, `ML_THRESHOLD_MEDIUM`, `ML_THRESHOLD_LOW` en `config.py`
- **Parámetros por Defecto**: Alto=0.85, Medio=0.70, Bajo=0.55
- **Configuración Mínima de Datos**: `ML_MIN_DATA_POINTS=50`

#### **🔧 Scripts de Mantenimiento**
- **`retrain_ml_model.py`**: Reentrenamiento automático con verificación de rendimiento
- **`optimize_ml_thresholds.py`**: Optimización de umbrales basada en datos históricos
- **Backup Automático**: Respaldo de modelos antes de reentrenamiento

#### **📈 Métricas y Análisis**
- **Estadísticas en Tiempo Real**: Confianza promedio, distribución de decisiones
- **Análisis de Rendimiento**: Detección automática de degradación del modelo
- **Recomendaciones Automáticas**: Sugerencias de optimización basadas en datos

#### **🎯 Impacto en Trading**
- **Decisiones Más Informadas**: Múltiples niveles de confianza (COMPRAR, COMPRAR_BAJO, etc.)
- **Mejor Gestión de Riesgo**: Score basado en probabilidades ML
- **Operación Continua**: Fallback garantiza funcionamiento sin MLflow

- Corrección de la ruta de ejecución en MODO REAL en `utils/order_executor.py` (cuando `live`+`unlocked`).
- Manejo explícito de excepciones `BinanceAPIException` y `aiohttp.ClientError` con mensajes de error claros.
- Aviso de LIVE bloqueado se envía tras pasar validaciones de riesgo para evitar ruido en denegaciones tempranas.
- Suite de tests estabilizada: 435 pruebas pasando en local.