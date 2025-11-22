# ITBOT NAS100 Optimized - NinjaTrader Indicator

## Descripción
Este es el indicador **ITBOT NAS100 Optimized** convertido desde Pine Script a **NinjaScript (C#)** para NinjaTrader 8. El indicador está especializado para el trading de índices, particularmente el NAS100 (NASDAQ 100).

## Lenguaje de Programación
**NinjaTrader utiliza C# 8 con .NET Framework 4.8** para su lenguaje de programación NinjaScript.

## Características Principales

### Indicadores Técnicos
- **EMA Rápida (5 períodos)** y **EMA Lenta (20 períodos)**
- **RSI (14 períodos)** con niveles optimizados para índices
- **Momentum (8 períodos)**
- **ATR (14 períodos)** para filtro de volatilidad
- **SMA de Volumen (20 períodos)**

### Señales de Trading
- **Señales de Compra**: Triángulos verdes hacia arriba con texto "BUY"
- **Señales de Venta**: Triángulos rojos hacia abajo con texto "SELL"
- **Señales Básicas**: Puntos más pequeños para cruces simples de EMA

### Filtros Avanzados
- **Filtro de RSI**: Sobrecomprado (75) / Sobrevendido (25)
- **Filtro de Volumen**: Confirmación con multiplicador 1.8x
- **Filtro de Momentum**: Confirmación direccional
- **Filtro de Spread**: Máximo 2.0 puntos
- **Filtro de Volatilidad**: ATR mínimo del 80% del promedio
- **Filtro de Sesión**: Horarios de mercado activo

## Instalación en NinjaTrader

### Paso 1: Copiar el Archivo
1. Copia el archivo `ITBOT_NAS100_Optimized.cs`
2. Navega a la carpeta de NinjaTrader: `Documents\NinjaTrader 8\bin\Custom\Indicators\`
3. Pega el archivo en esta carpeta

### Paso 2: Compilar en NinjaTrader
1. Abre NinjaTrader 8
2. Ve a **Tools > Edit NinjaScript > Indicator**
3. Busca `ITBOT_NAS100_Optimized` en la lista
4. Haz clic derecho y selecciona **Compile**
5. Verifica que no haya errores de compilación

### Paso 3: Aplicar al Gráfico
1. Abre un gráfico del NAS100 (o cualquier índice)
2. Haz clic derecho en el gráfico
3. Selecciona **Indicators**
4. Busca `ITBOT NAS100 Optimized` en la lista
5. Haz doble clic para agregarlo al gráfico

## Configuración de Parámetros

### Parámetros Principales
- **Fast MA Length**: 5 (EMA rápida)
- **Slow MA Length**: 20 (EMA lenta)
- **Trend Threshold %**: 0.08 (8% de diferencia para confirmar tendencia)

### Filtros
- **RSI Length**: 14
- **RSI Overbought**: 75
- **RSI Oversold**: 25
- **Volume Multiplier**: 1.8
- **Momentum Length**: 8
- **Use Advanced Filters**: true/false

### Visualización
- **Show Signals**: Mostrar/ocultar señales
- **Show Trend Background**: Mostrar/ocultar fondo de tendencia
- **Colores personalizables** para EMAs y señales

## Uso Recomendado

### Timeframes Óptimos
- **M5 (5 minutos)**: Para scalping
- **M15 (15 minutos)**: Para trading intradiario
- **H1 (1 hora)**: Para swing trading

### Instrumentos Recomendados
- **NAS100** (NASDAQ 100)
- **SPX500** (S&P 500)
- **US30** (Dow Jones)
- **Otros índices principales**

### Estrategia de Trading
1. **Señal de Compra**: Triángulo verde + confirmación de filtros
2. **Señal de Venta**: Triángulo rojo + confirmación de filtros
3. **Stop Loss**: Usar ATR para calcular niveles dinámicos
4. **Take Profit**: 1:2 o 1:3 risk/reward ratio

## Diferencias con Pine Script

### Ventajas del NinjaScript
- **Mejor rendimiento**: C# compilado vs Pine Script interpretado
- **Más flexibilidad**: Acceso completo a .NET Framework
- **Integración nativa**: Con todas las funciones de NinjaTrader
- **Alertas avanzadas**: Sistema de notificaciones más robusto

### Funcionalidades Equivalentes
- **Cálculos de EMA**: Idénticos al Pine Script original
- **Filtros**: Todos los filtros del Pine Script implementados
- **Señales**: Misma lógica de generación de señales
- **Visualización**: Colores y formas similares

## Troubleshooting

### Errores Comunes
1. **Error de compilación**: Verificar que todas las referencias estén correctas
2. **Indicador no aparece**: Reiniciar NinjaTrader después de la compilación
3. **Señales no se muestran**: Verificar configuración de parámetros

### Soporte
- **Documentación oficial**: [NinjaTrader Help Guide](https://ninjatrader.com/support/helpGuides/nt8/)
- **Foros**: [NinjaTrader Community](https://ninjatrader.com/support/forum/)
- **Tutoriales**: [NinjaScript Programming](https://ninjatrader.com/support/helpGuides/nt8/?ninjascript.htm)

## Versión y Compatibilidad
- **NinjaTrader**: 8.0 o superior
- **Framework**: .NET 4.8
- **Lenguaje**: C# 8
- **Versión del Indicador**: 1.0

## Notas Importantes
- Este indicador es una conversión directa del Pine Script original
- Mantiene la misma lógica y parámetros optimizados para índices
- Se recomienda hacer backtesting antes del uso en vivo
- Los resultados pasados no garantizan resultados futuros

---

**Desarrollado por**: ITBOT Team  
**Convertido a NinjaScript**: 2025  
**Licencia**: Para uso personal y educativo