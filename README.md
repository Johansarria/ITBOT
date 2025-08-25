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