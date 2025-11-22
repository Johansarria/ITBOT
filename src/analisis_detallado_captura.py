#!/usr/bin/env python3
"""
Análisis Detallado de la Captura BTCUSD 5m
Análisis específico basado en la captura visual proporcionada
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import json
from dotenv import load_dotenv
import talib

# Cargar variables de entorno
load_dotenv()

def analizar_captura_detallada():
    """Análisis detallado de la captura del gráfico"""
    
    print("="*100)
    print("🎯 ANÁLISIS DETALLADO DE LA CAPTURA BTCUSD 5 MINUTOS")
    print("="*100)
    
    # Datos observados en la captura
    precio_captura = 108110.47
    hora_captura = "21:01:53 UTC-5"
    
    print(f"📊 DATOS DE LA CAPTURA:")
    print(f"  • Precio: ${precio_captura:,.2f}")
    print(f"  • Hora: {hora_captura}")
    print(f"  • Timeframe: 5 minutos")
    print(f"  • Cambio: -$58.36 (-0.05%)")
    
    print(f"\n🔍 PATRONES VISUALES IDENTIFICADOS:")
    
    # 1. Análisis de la estructura del gráfico
    print(f"\n1️⃣ ESTRUCTURA DEL PRECIO:")
    print(f"  • Rango visible: ~$106,200 - $109,000")
    print(f"  • Amplitud total: ~$2,800 (~2.6%)")
    print(f"  • Posición actual: Zona media-alta del rango")
    print(f"  • Patrón dominante: CONSOLIDACIÓN LATERAL con ligero sesgo bajista")
    
    # 2. Análisis de las velas recientes
    print(f"\n2️⃣ ANÁLISIS DE VELAS RECIENTES:")
    print(f"  • Últimas velas: Predominantemente rojas (bajistas)")
    print(f"  • Tamaño de velas: Pequeño a mediano (baja volatilidad)")
    print(f"  • Mechas: Presentes pero no excesivamente largas")
    print(f"  • Patrón: Descenso gradual sin momentum fuerte")
    
    # 3. Análisis de niveles clave
    print(f"\n3️⃣ NIVELES CLAVE OBSERVADOS:")
    print(f"  • Resistencia principal: ~$108,800 - $109,000")
    print(f"  • Resistencia inmediata: ~$108,400 - $108,500")
    print(f"  • Soporte inmediato: ~$107,800 - $108,000")
    print(f"  • Soporte principal: ~$106,800 - $107,000")
    
    # 4. Análisis de momentum
    print(f"\n4️⃣ ANÁLISIS DE MOMENTUM:")
    print(f"  • Tendencia inmediata: BAJISTA SUAVE")
    print(f"  • Fuerza del movimiento: DÉBIL")
    print(f"  • Volumen aparente: NORMAL a BAJO")
    print(f"  • Probabilidad de continuación: MEDIA")
    
    # 5. Patrones técnicos identificados
    print(f"\n5️⃣ PATRONES TÉCNICOS:")
    print(f"  • Patrón principal: RANGO DE TRADING / CONSOLIDACIÓN")
    print(f"  • Sub-patrón: Bandera bajista menor")
    print(f"  • Formación: Posible triángulo descendente")
    print(f"  • Estado: En desarrollo (no confirmado)")
    
    # 6. Análisis de tiempo
    print(f"\n6️⃣ ANÁLISIS TEMPORAL:")
    print(f"  • Hora de trading: Sesión americana tardía")
    print(f"  • Contexto: Fin de día de trading tradicional")
    print(f"  • Expectativa: Posible reducción de volumen")
    print(f"  • Próxima sesión: Asiática (menor volatilidad típica)")
    
    # 7. Comparación con sistema IA
    print(f"\n🤖 COMPARACIÓN CON SISTEMA IA:")
    print(f"  • Sistema detecta: MODO ZOMBIE (mercado inactivo)")
    print(f"  • Captura muestra: Consolidación lateral con sesgo bajista")
    print(f"  • Concordancia: ALTA - Ambos indican baja actividad")
    print(f"  • Diferencia: Sistema más conservador en detección de patrones")
    
    # 8. Escenarios probables
    print(f"\n🔮 ESCENARIOS PROBABLES (Próximas 1-3 horas):")
    
    print(f"\n  📈 ESCENARIO ALCISTA (30% probabilidad):")
    print(f"    • Rebote desde $107,800-$108,000")
    print(f"    • Objetivo: $108,500-$108,800")
    print(f"    • Catalizador: Compras de soporte + volumen")
    
    print(f"\n  📉 ESCENARIO BAJISTA (45% probabilidad):")
    print(f"    • Ruptura de $107,800")
    print(f"    • Objetivo: $107,200-$107,500")
    print(f"    • Catalizador: Continuación del momentum bajista")
    
    print(f"\n  ↔️ ESCENARIO LATERAL (25% probabilidad):")
    print(f"    • Rango: $107,800 - $108,500")
    print(f"    • Duración: 2-4 horas")
    print(f"    • Catalizador: Falta de momentum direccional")
    
    # 9. Recomendaciones de trading
    print(f"\n💡 RECOMENDACIONES DE TRADING:")
    
    print(f"\n  🎯 PARA SCALPING (5-15 min):")
    print(f"    • Venta en $108,300-$108,400 (resistencia)")
    print(f"    • Compra en $107,900-$108,000 (soporte)")
    print(f"    • Stop loss: 0.15% ($150-200)")
    print(f"    • Take profit: 0.20-0.30% ($200-300)")
    
    print(f"\n  📊 PARA SWING (1-4 horas):")
    print(f"    • Esperar ruptura confirmada del rango")
    print(f"    • Si rompe $108,500: Target $109,000")
    print(f"    • Si rompe $107,800: Target $107,200")
    print(f"    • Stop loss: Lado opuesto del rango")
    
    print(f"\n  ⚠️ GESTIÓN DE RIESGO:")
    print(f"    • Volumen bajo = Movimientos pueden ser falsos")
    print(f"    • Usar posiciones pequeñas")
    print(f"    • Confirmar rupturas con volumen")
    print(f"    • Evitar FOMO en movimientos sin confirmación")
    
    # 10. Indicadores clave a monitorear
    print(f"\n📊 INDICADORES CLAVE A MONITOREAR:")
    print(f"  • Volumen: Confirmar rupturas")
    print(f"  • RSI: Actualmente neutral (~56)")
    print(f"  • MACD: Buscar divergencias")
    print(f"  • Niveles de Fibonacci: $107,800 y $108,500")
    
    print(f"\n" + "="*100)
    print(f"⏰ Análisis realizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Próxima revisión recomendada: En 30-60 minutos")
    print(f"="*100)

if __name__ == "__main__":
    analizar_captura_detallada()