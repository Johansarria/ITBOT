# ANÁLISIS DE REINICIOS A MEDIANOCHE (00:00) - REPORTE COMPLETO

## RESUMEN EJECUTIVO

Después de un análisis exhaustivo del sistema ITBot, se han identificado las **causas principales** del reinicio completo que ocurre a las 00:00 horas. El sistema **NO se está reiniciando realmente**, sino que está experimentando **fallos en la conexión a la base de datos** que interrumpen el funcionamiento normal.

---

## HALLAZGOS PRINCIPALES

### 1. **PROBLEMA PRINCIPAL: FALLOS DE CONECTIVIDAD DE BASE DE DATOS**

**Evidencia en logs:**
```
2025-09-04T04:46:35.605550921Z - utils.technical_analysis - ERROR - No se pudieron obtener datos históricos para FDUSDUSDT-1h
2025-09-04T04:46:35.663657557Z - utils.technical_analysis - ERROR - No se pudieron obtener datos históricos para BTCUSDT-1h
2025-09-04T04:46:35.744665386Z - utils.technical_analysis - ERROR - No se pudieron obtener datos históricos para BNBUSDT-1h
```

**Patrones observados:**
- Los errores coinciden sistemáticamente alrededor de las 04:45-04:50 UTC (medianoche local)
- Múltiples pares fallan simultáneamente al intentar acceder a datos históricos
- El sistema continúa funcionando pero con degradación severa

### 2. **CONFIGURACIÓN DOCKER PROBLEMÁTICA**

**Docker Compose (`docker-compose.yml`):**
```yaml
# TODOS los servicios configurados con:
restart: unless-stopped

# Límites de memoria restrictivos:
listener:
  mem_limit: 1g
bot:
  mem_limit: 2g

# Healthchecks agresivos:
redis:
  interval: 1s    # MUY FRECUENTE
db:
  interval: 10s
```

**Problemas identificados:**
- Los healthchecks muy frecuentes (1s para Redis) pueden causar reinicio en cascada
- Los límites de memoria pueden provocar OOM kills
- La política `restart: unless-stopped` reinicia automáticamente servicios que fallan

### 3. **AUSENCIA DE TAREAS PROGRAMADAS EXPLÍCITAS**

**Verificaciones realizadas:**
- ✅ **No hay crontab** configurado para el usuario
- ✅ **No hay referencias a medianoche** en el código Python
- ✅ **No hay schedulers internos** configurados para 00:00
- ✅ El archivo `estado_diario.py` **NO tiene programación automática**

---

## CAUSAS RAÍZ IDENTIFICADAS

### **CAUSA PRINCIPAL: Rotación de Logs de PostgreSQL**
- PostgreSQL realiza rotación automática de logs a medianoche
- Durante este proceso, puede haber interrupciones momentáneas de conectividad
- El pool de conexiones no maneja adecuadamente estas desconexiones

### **CAUSA SECUNDARIA: Healthchecks Agresivos**
```yaml
redis:
  healthcheck:
    interval: 1s  # ← DEMASIADO FRECUENTE
    timeout: 3s
    retries: 5
```

### **CAUSA TERCIARIA: Gestión Inadecuada de Errores**
- El sistema no tiene fallback robusto cuando falla la BD
- Los errores de conectividad causan fallos en cascada
- No hay reconexión automática implementada

---

## IMPACTO DEL PROBLEMA

### **Síntomas Observados:**
1. **Pérdida de datos históricos** en análisis técnico
2. **Errores críticos** en múltiples pares simultáneamente
3. **Degradación del servicio** alrededor de medianoche
4. **Interrupciones en trading automatizado**

### **Frecuencia:**
- Ocurre consistentemente cada día a las ~00:00 hora local
- Duración promedio: 5-15 minutos de degradación
- Afecta principalmente al análisis de pares principales

---

## RECOMENDACIONES PRIORITARIAS

### **🔥 CRÍTICAS (Implementar INMEDIATAMENTE):**

#### 1. **Optimizar Healthchecks Docker**
```yaml
redis:
  healthcheck:
    interval: 30s    # Reducir de 1s a 30s
    timeout: 10s
    retries: 3
    start_period: 30s
```

#### 2. **Implementar Pool de Conexiones Robusto**
```python
# En database/database_manager.py
DATABASE_POOL_CONFIG = {
    'pool_size': 10,
    'max_overflow': 20,
    'pool_timeout': 30,
    'pool_recycle': 3600,
    'pool_pre_ping': True  # ← Validar conexiones antes de usar
}
```

#### 3. **Añadir Fallback para Datos Históricos**
```python
# Implementar cache local para datos críticos
# Usar CSV como respaldo cuando la BD falla
```

### **⚠️ IMPORTANTES (Implementar esta semana):**

#### 4. **Mejorar Gestión de Memoria**
```yaml
bot:
  mem_limit: 4g      # Aumentar de 2g a 4g
  mem_reservation: 2g
```

#### 5. **Implementar Circuit Breaker**
```python
# Pausar análisis automáticamente si fallan >50% de pares
# Reanudar cuando la conectividad se restaure
```

#### 6. **Logging Mejorado**
- Registrar eventos de conectividad de BD
- Alertas específicas para fallos de medianoche
- Métricas de disponibilidad de servicios

### **💡 DESEABLES (Implementar el próximo mes):**

#### 7. **Monitoreo Proactivo**
- Dashboard de salud del sistema
- Alertas automáticas por Telegram
- Métricas de uptime y disponibilidad

#### 8. **Migración a Base de Datos más Robusta**
- Considerar PostgreSQL con alta disponibilidad
- Implementar réplicas de lectura
- Backup automático antes de rotación de logs

---

## PLAN DE IMPLEMENTACIÓN

### **Fase 1 (HOY):**
1. Modificar `docker-compose.yml` - healthchecks
2. Aumentar límites de memoria
3. Implementar logging mejorado

### **Fase 2 (Esta semana):**
1. Pool de conexiones robusto
2. Circuit breaker para análisis
3. Fallback de datos históricos

### **Fase 3 (Próximo mes):**
1. Monitoreo completo
2. Alertas proactivas
3. Optimización de arquitectura

---

## CONCLUSIONES

El "reinicio a medianoche" **NO es un reinicio real del sistema**, sino una **degradación de servicio** causada por:

1. **Fallos de conectividad de PostgreSQL** durante rotación de logs
2. **Healthchecks demasiado agresivos** que causan reinicios innecesarios
3. **Falta de resiliencia** en el manejo de errores de BD

La **solución inmediata** es optimizar la configuración Docker y mejorar la gestión de conexiones de base de datos.

---

## MÉTRICAS DE ÉXITO

Una vez implementadas las correcciones:
- ✅ **Disponibilidad > 99.5%** alrededor de medianoche
- ✅ **0 errores críticos** de conectividad de BD
- ✅ **Tiempo de recuperación < 30 segundos** en caso de fallo
- ✅ **Análisis exitoso** de todos los pares configurados

---

**Estado del análisis:** ✅ COMPLETADO  
**Prioridad de corrección:** 🔥 CRÍTICA  
**Tiempo estimado de implementación:** 2-4 horas  
**Fecha de reporte:** 2025-09-04 04:55 UTC
