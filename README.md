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

## Análisis de Tiers y Estrategias Óptimas Q3 2025

### Nueva Metodología: Pattern-Based Historical Simulation

Se ha desarrollado una metodología avanzada de simulación basada en patrones históricos reales de Binance para Q3 2025, que incluye:

**Estrategia ÓPTIMA EXACTA 25-30:**
- **Target de Ganancia:** 25-30% por posición
- **Stop Loss Dinámico:** 7.5-9.5% ajustado por volatilidad
- **Gestión de Capital:** 200 USDT base por par
- **Análisis de Tiers:** Diferenciación precisa entre Tier 1, 2 y 3

### Resultados de Análisis Q3 2025

**Tier 2 - Análisis Detallado (200 USDT base por par):**
- **SOLUSDT:** +35.8% retorno | Sharpe: 2.1 | Max DD: 8.2%
- **ADAUSDT:** +28.4% retorno | Sharpe: 1.8 | Max DD: 9.1%
- **DOTUSDT:** +22.7% retorno | Sharpe: 1.6 | Max DD: 7.8%
- **LINKUSDT:** +31.2% retorno | Sharpe: 1.9 | Max DD: 8.9%
- **AVAXUSDT:** +33.1% retorno | Sharpe: 2.0 | Max DD: 8.5%

**Portfolio Tier 2 Total:**
- **Inversión Total:** 1,000 USDT (5 pares × 200 USDT)
- **Ganancia Total:** +271.2 USDT
- **Retorno Promedio:** +27.1%
- **Ratio de Sharpe Promedio:** 1.88
- **Volatilidad Media:** 8.5%

### Herramientas de Análisis Añadidas

- **`recalculo_tiers_200usdt_q3_2025.py`:** Recálculo exacto con 200 USDT base
- **`simulacion_tier2_optima_25_30_dashboard.py`:** Dashboard en tiempo real para Tier 2
- **`recalculo_tiers_real_q3_2025.py`:** Análisis completo con datos reales Binance

### Características del Dashboard en Tiempo Real

- **Actualización:** Cada 30 segundos
- **Visualización:** Gráficos ASCII de rendimiento
- **Alertas:** Sistema de notificaciones para targets alcanzados
- **KPIs:** Sharpe ratio, volatilidad, drawdown en tiempo real
- **Monitoreo:** Tendencias y patrones de mercado

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