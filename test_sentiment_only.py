#!/usr/bin/env python3
"""
Script de prueba para verificar el análisis de sentimiento standalone
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Agregar el directorio src al path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

try:
    from src.market_sentiment import MarketSentimentAnalyzer
    
    print("=== PRUEBA DE ANÁLISIS DE SENTIMIENTO ===")
    
    # Probar analizador de sentimiento standalone
    print("\n1. Probando MarketSentimentAnalyzer...")
    analyzer = MarketSentimentAnalyzer()
    
    # Fear & Greed
    print("   Obteniendo Fear & Greed Index...")
    fg = analyzer.get_fear_greed_index()
    if fg:
        print(f"   ✓ Fear & Greed actual: {fg['current_value']} ({fg['current_classification']})")
        print(f"   ✓ Miedo extremo: {fg['extreme_fear']}")
        print(f"   ✓ Tendencia: {fg['trend']}")
    else:
        print("   ✗ Error obteniendo Fear & Greed")
    
    # Funding rates para BTC
    print("\n   Obteniendo Funding Rates para BTC...")
    funding = analyzer.get_funding_rates("BTCUSDT")
    if funding:
        print(f"   ✓ Funding Rate BTC: {funding['current_rate']:.2f}% anualizado")
        print(f"   ✓ Funding alto: {funding['high_funding']}")
        print(f"   ✓ Tendencia funding: {funding['trend']}")
    else:
        print("   ✗ Error obteniendo funding rates")
    
    # Sentimiento combinado
    print("\n   Obteniendo sentimiento combinado...")
    combined = analyzer.get_combined_sentiment("BTCUSDT")
    print(f"   ✓ Sentimiento combinado: {combined['sentiment_classification']}")
    print(f"   ✓ Score de sentimiento: {combined['sentiment_score']:.3f}")
    print(f"   ✓ Señales: {combined['signals']}")
    
    # Análisis detallado
    if combined['fear_greed']:
        print(f"\n   📊 DETALLES FEAR & GREED:")
        print(f"   - Valor actual: {combined['fear_greed']['current_value']}")
        print(f"   - Media móvil 7 días: {combined['fear_greed']['ma_7_value']:.1f}")
        print(f"   - Clasificación: {combined['fear_greed']['current_classification']}")
    
    if combined['funding_rates']:
        print(f"\n   💰 DETALLES FUNDING:")
        print(f"   - Rate actual: {combined['funding_rates']['current_rate']:.3f}%")
        print(f"   - Rate promedio: {combined['funding_rates']['average_rate']:.3f}%")
    
    print(f"\n   🎯 RESUMEN DE SENTIMIENTO:")
    if combined['sentiment_score'] < -0.3:
        print("   🔴 SENTIMIENTO BAJISTA - Precaución con señales BUY")
    elif combined['sentiment_score'] > 0.3:
        print("   🟢 SENTIMIENTO ALCISTA - Precaución con señales SELL")
    else:
        print("   ⚪ SENTIMIENTO NEUTRO - Señales según análisis técnico")
    
    if 'EXTREME_FEAR' in combined['signals']:
        print("   🚨 EXTREME FEAR DETECTADO - Se reducirá confianza en señales BUY")
    
    print("\n✅ Análisis de sentimiento funcionando correctamente!")
    
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    print("Asegúrate de que el archivo market_sentiment.py esté en el directorio src/")
    
except Exception as e:
    print(f"❌ Error ejecutando prueba: {e}")
    import traceback
    traceback.print_exc()