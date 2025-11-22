#!/usr/bin/env python3
"""
Script de prueba para verificar el análisis ATR dinámico
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.crypto_data_loader import CryptoDataLoader
    
    print("=== PRUEBA DE ANÁLISIS ATR DINÁMICO ===")
    
    # Crear loader de prueba
    loader = CryptoDataLoader("BTC-USD", "1h")
    
    # Obtener datos de prueba
    print("\n1. Obteniendo datos de prueba...")
    data = loader.get_binance_data(limit=1000)
    print(f"   ✓ Datos obtenidos: {len(data)} registros")
    
    # Calcular indicadores técnicos (incluyendo ATR)
    print("\n2. Calculando indicadores técnicos...")
    enriched_data = loader.calculate_technical_indicators(data)
    print(f"   ✓ Indicadores calculados: {len(enriched_data.columns)} columnas")
    
    # Verificar que ATR se calculó
    if 'atr' in enriched_data.columns:
        print(f"   ✓ ATR calculado: último valor = {enriched_data['atr'].iloc[-1]:.4f}")
        print(f"   ✓ ATR %: último valor = {enriched_data['atr_percent'].iloc[-1]:.2f}%")
    else:
        print("   ✗ ATR no encontrado")
    
    # Obtener análisis ATR completo
    print("\n3. Obteniendo análisis ATR completo...")
    atr_analysis = loader.get_atr_analysis(enriched_data)
    
    if atr_analysis:
        print(f"   ✓ Volatilidad actual: {atr_analysis['volatility_level']} ({atr_analysis['current_atr_percent']:.2f}%)")
        print(f"   ✓ Factor de volatilidad: {atr_analysis['volatility_factor']}")
        print(f"   ✓ Tendencia volatilidad: {atr_analysis['volatility_trend']}")
        print(f"   ✓ Ratio ATR: {atr_analysis['atr_ratio']:.2f}")
        
        # Percentiles
        percentiles = atr_analysis['atr_percentiles']
        print(f"   ✓ Percentiles ATR: P25={percentiles['p25']:.2f}%, P50={percentiles['p50']:.2f}%, P75={percentiles['p75']:.2f}%")
        
        # Rangos dinámicos
        ranges = atr_analysis['dynamic_ranges']
        current_price = enriched_data['close'].iloc[-1]
        print(f"   ✓ Precio actual: ${current_price:.2f}")
        print(f"   ✓ Soporte 2ATR: ${ranges['support_2atr']:.2f}")
        print(f"   ✓ Resistencia 2ATR: ${ranges['resistance_2atr']:.2f}")
        
        # Señales de breakout
        breakouts = atr_analysis['breakout_signals']
        print(f"   ✓ Breakout alcista: {breakouts['high_breakout']}")
        print(f"   ✓ Breakout bajista: {breakouts['low_breakout']}")
        
        print(f"\n   📊 ANÁLISIS COMPLETO:")
        
        # Análisis de volatilidad actual
        if atr_analysis['volatility_level'] == "HIGH":
            print("   🔴 ALTA VOLATILIDAD - El modelo reducirá confianza en señales")
        elif atr_analysis['volatility_level'] == "LOW":
            print("   🟢 BAJA VOLATILIDAD - El modelo aumentará confianza en señales")
        else:
            print("   ⚪ VOLATILIDAD NORMAL - Confianza estándar")
        
        # Análisis de tendencia
        if atr_analysis['volatility_trend'] == "INCREASING":
            print("   📈 Volatilidad CRECIENDO - Mayor riesgo en operaciones")
        elif atr_analysis['volatility_trend'] == "DECREASING":
            print("   📉 Volatilidad DECRECIENDO - Menor riesgo en operaciones")
        
        print("\n✅ Análisis ATR dinámico funcionando correctamente!")
        
    else:
        print("   ✗ Error obteniendo análisis ATR")
    
except Exception as e:
    print(f"❌ Error en prueba: {e}")
    import traceback
    traceback.print_exc()