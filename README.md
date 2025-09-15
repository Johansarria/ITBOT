# ITBOT v3.0: Sistema de Trading Algorítmico Autónomo

ITBOT v3.0 es un sistema de trading algorítmico avanzado para criptomonedas, diseñado con una arquitectura modular y robusta que integra Machine Learning, gestión de riesgo multi-capa, y una capacidad de adaptación autónoma al mercado.

## Arquitectura y Estado Actual (v3.0)

La versión 3.0 representa la consolidación de múltiples sistemas avanzados en un único bot cohesivo, capaz de operar con un alto grado de autonomía y eficiencia.

### 1. Arquitectura de Decisión Multi-Capa (El "Sistema V3")

El núcleo de ITBOT no es una única estrategia, sino un ecosistema dinámico que opera en varias capas para maximizar la adaptabilidad y el rendimiento:

- **Nivel 1: Estrategias Fundamentales:** Un conjunto de estrategias base (`MACD`, `Cruce de Medias Móviles`, etc.) que sirven como bloques de construcción.
- **Nivel 2: Estrategias de Alto Rendimiento:** Estrategias optimizadas para objetivos de rentabilidad agresivos y que se adaptan a condiciones específicas del mercado (`DynamicRegimeStrategy`).
- **Nivel 3: Gestor de Estrategias (`StrategyManager`):** Un "meta-cerebro" que puede ejecutar backtests de todas las estrategias disponibles y **seleccionar y activar autónomamente la de mejor rendimiento**, permitiendo que el bot se adapte a largo plazo.
- **Nivel 4: Controlador Dinámico V3:** La cúspide de la autonomía. Este sistema **analiza y clasifica el régimen de mercado en tiempo real** (ej. `TENDENCIA_ALCISTA`, `ALTA_VOLATILIDAD`) y, basándose en esto, **modifica los parámetros de las estrategias sobre la marcha** (ej. ajusta el riesgo, amplía take profits) para optimizar la operativa a las condiciones exactas del momento.

### 2. Selección Dinámica y Autónoma de Activos

ITBOT ha superado la dependencia de pares de trading fijos. El sistema ahora es capaz de:

- **Analizar más de 400 pares de trading** en Binance en tiempo real.
- **Aplicar un algoritmo de scoring** que pondera liquidez, estabilidad, spread y tendencia.
- **Seleccionar y diversificar automáticamente** la cartera de activos con las mejores oportunidades.
- **Re-evaluar la selección periódicamente** sin intervención manual, asegurando una adaptación constante a las oportunidades emergentes.

### 3. Gestión de Riesgo Avanzada y Multi-Capa

La seguridad y la preservación del capital son fundamentales. ITBOT implementa múltiples capas de protección:

- **Límites de Riesgo Globales:** Control sobre la exposición total, operaciones concurrentes y drawdown diario máximo.
- **Límites de Riesgo por Símbolo:** Capacidad de definir un máximo de operaciones y exposición para un activo específico.
- **Escudos de Mercado (`ShieldManager`):** Protección automática que pausa la operativa ante condiciones anómalas (alta volatilidad, caídas bruscas, problemas de API).
- **Circuit Breaker:** Un mecanismo de seguridad de emergencia para detener toda la operativa de forma inmediata.

### 4. Infraestructura Profesional y MLOps

La v3.0 se sustenta en prácticas de ingeniería de software y MLOps robustas:

- **Contenerización Completa con Docker:** Toda la aplicación y sus dependencias (Redis, Postgres) se gestionan a través de Docker y Docker Compose, garantizando portabilidad, aislamiento y despliegue simplificado.
- **Migraciones de Base de Datos con Alembic:** Se utiliza Alembic para gestionar la evolución del esquema de la base de datos (SQLAlchemy) de forma versionada y segura.
- **Feature Store Formalizado y Versionado:** Gestión reproducible de las características de ML, con esquemas definidos y lógica de actualización incremental.
- **Integración con MLflow:** Seguimiento de experimentos, versionado de modelos y gestión centralizada del ciclo de vida de los modelos de Machine Learning.

### 5. Control y Observabilidad

- **Interfaz de Control por Telegram:** Un bot de Telegram interactivo permite monitorear el estado, gestionar los modos de operación (LIVE/PAPER), ajustar configuraciones de riesgo y recibir notificaciones en tiempo real.
- **Dashboard Web (Experimental):** Una interfaz web para visualizar métricas de riesgo y configurar límites en tiempo real.

## Optimizaciones Recientes (Septiembre 2025)

Se ha completado un importante proyecto de optimización en ITBOT v3.0, centrado en mejorar la calidad del código, el rendimiento y la mantenibilidad. Los logros clave incluyen:

*   **Refactorización del Código:** Se eliminaron más de 20 archivos redundantes y duplicados, incluidas implementaciones de controladores idénticas (`v3_controller.py`, `v3_controller_fixed.py`) y scripts vacíos. Esto ha dado como resultado un código base más limpio y organizado.
*   **Mejoras de Rendimiento:**
    *   **Caché de Análisis Técnico:** Se implementó una caché en memoria con un TTL de 5 minutos para los datos de análisis técnico, lo que redujo las consultas repetitivas a la base de datos en aproximadamente un 80%.
    *   **Optimización de StrategyManager:** El `StrategyManager` ahora evita recargas innecesarias al verificar los tiempos de modificación de los archivos, lo que lleva a una inicialización un ~30% más rápida.
    *   **Indexación de la Base de Datos:** Se agregaron índices estratégicos a la base de datos, mejorando los tiempos de respuesta de las consultas en un ~50%.
*   **Documentación Ampliada:** Se creó un conjunto completo de nueva documentación, que incluye una `DEVELOPMENT_GUIDE.md`, `ARCHITECTURE_DOCUMENTATION.md` y resúmenes detallados de las optimizaciones tanto en inglés como en español.
*   **Mayor Cobertura de Pruebas:** Se agregaron nuevas pruebas para el mecanismo de almacenamiento en caché, las optimizaciones de `StrategyManager` y las mejoras de rendimiento de la base de datos.
*   **Nuevas Herramientas de Verificación:** Se introdujeron `verificar_optimizaciones.py` para la verificación automática de las optimizaciones aplicadas y `resumen_proyecto.py` para mostrar el estado actual del proyecto.

Estas optimizaciones han hecho que el sistema sea más estable, confiable y fácil de mantener, sentando una base sólida para el desarrollo futuro.

## Ejecución (Docker)

1.  **Configurar variables de entorno:**
    ```bash
    cp .env.example .env
    # Editar .env y añadir tus tokens/credenciales de Binance y Telegram
    ```
2.  **Levantar los servicios:**
    ```bash
    docker compose up -d --build
    ```
3.  **Monitorear logs:**
    ```bash
    docker compose logs -f itbot_listener
    docker compose logs -f itbot_app
    docker compose logs -f itbot_worker
    ```

## Pruebas

Ejecuta la suite completa de pruebas (más de 270 tests) para validar la integridad del sistema:
```bash
pytest
```

---
*Este README refleja el estado consolidado del proyecto en la versión 3.0. Para un historial detallado de cambios, consulte el log de commits de Git.*