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

### v2.1: Refactorización E2E y Arquitectura Multi-Activo

Se ha completado una refactorización masiva que introduce mejoras críticas en la arquitectura y la fiabilidad del bot:

*   **Arquitectura Multi-Activo:** Se refactoriza `run_bot.py` para soportar el **análisis concurrente de múltiples pares de trading**, reemplazando el antiguo modelo mono-activo y permitiendo una mayor escalabilidad.
*   **Pipeline de Features Robusto:** Se consolida el uso del `FeaturePipeline` y el formato Parquet, eliminando la dependencia de archivos CSV intermedios y mejorando el rendimiento.
*   **Entrenamiento ML Avanzado:** Se integra una versión refactorizada de `ml_model_trainer.py`, que incluye funciones modulares, versionado del código de features y logging avanzado con MLflow para una mejor trazabilidad.
*   **Prueba End-to-End (E2E):** Se establece una prueba de integración completa que valida todo el flujo de la aplicación, desde la decisión en `run_bot` hasta la ejecución en `execution_worker` y la persistencia en la base de datos, garantizando la fiabilidad del sistema.
*   **Mejoras en KPIs y Pruebas:** Se actualizan los cálculos de KPIs para ser más precisos y se expande la cobertura de pruebas para el `listener_bot`.

### Infraestructura y MLOps

*   **Dockerización Completa:** La aplicación ha sido completamente dockerizada, lo que garantiza portabilidad, aislamiento y un despliegue simplificado.
*   **Integración de MLflow:** Se ha integrado MLflow para una gestión robusta de los experimentos de Machine Learning, permitiendo el seguimiento de experimentos, la reproducibilidad y la gestión centralizada de modelos.

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

*   Para una operación completa, `run_bot.py` y `execution_worker.py` deben ejecutarse en paralelo (idealmente en procesos separados o en segundo plano).
*   Para operar el bot (orquestador): `python3 run_bot.py`
*   Para el worker de ejecución: `python3 execution_worker.py`
*   Para entrenar modelos ML: `python3 ml_model_trainer.py`

## Pruebas

*   Ejecuta los tests con:
    ```bash
    pytest --cov=.
    ```

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