#!/usr/bin/env python3
"""
Script de prueba para verificar la integración del análisis de sentimiento
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.market_sentiment import MarketSentimentAnalyzer
from src.module_patchtst_integration import PatchTSTIntegration

def test_sentiment_integration():
    """Probar la integración de sentimiento con PatchTST"""
    
    print("=== PRUEBA DE INTEGRACIÓN DE SENTIMIENTO ===")
    
    # 1. Probar analizador de sentimiento standalone
    print("\n1. Probando MarketSentimentAnalyzer...")
    analyzer = MarketSentimentAnalyzer()
    
    # Fear & Greed
    fg = analyzer.get_fear_greed_index()
    if fg:
        print(f"   ✓ Fear & Greed actual: {fg['current_value']} ({fg['current_classification']})")
        print(f"   ✓ Miedo extremo: {fg['extreme_fear']}")
    else:
        print("   ✗ Error obteniendo Fear & Greed")
    
    # Funding rates para BTC
    funding = analyzer.get_funding_rates("BTCUSDT")
    if funding:
        print(f"   ✓ Funding Rate BTC: {funding['current_rate']:.2f}% anualizado")
    else:
        print("   ✗ Error obteniendo funding rates")
    
    # Sentimiento combinado
    combined = analyzer.get_combined_sentiment("BTCUSDT")
    print(f"   ✓ Sentimiento combinado: {combined['sentiment_classification']} (score: {combined['sentiment_score']:.3f})")
    print(f"   ✓ Señales: {combined['signals']}")
    
    # 2. Probar integración con PatchTST
    print("\n2. Probando integración con PatchTST...")
    
    try:
        patchtst = PatchTSTIntegration("BTC-USD")
        
        # Inicializar modelo
        print("   Inicializando modelo...")
        success = patchtst.initialize_model(load_pretrained=True, force_retrain=False)
        
        if success:
            print("   ✓ Modelo PatchTST inicializado correctamente")
            
            # Generar señal de prueba
            print("   Generando señal con análisis de sentimiento...")
            signal_result = patchtst.generate_trading_signal()
            
            if 'error' not in signal_result:
                print(f"   ✓ Señal generada: {signal_result['signal']}")
                print(f"   ✓ Confianza: {signal_result['confidence']:.2%}")
                
                # Verificar que el análisis de sentimiento esté incluido
                if 'sentiment_data' in signal_result.get('model_info', {}):
                    sentiment_data = signal_result['model_info']['sentiment_data']
                    print(f"   ✓ Sentimiento incluido: {sentiment_data['sentiment_classification']}")
                    print(f"   ✓ Score de sentimiento: {sentiment_data['sentiment_score']:.3f}")
                    
                    # Verificar recomendación
                    recommendation = signal_result.get('recommendation', '')
                    if 'MIEDO EXTREMO' in recommendation:
                        print(f"   ⚠️  ADVERTENCIA DE MIEDO EXTREMO DETECTADA")
                    
                    print(f"   ✓ Recomendación: {recommendation}")
                    
                else:
                    print("   ✗ Análisis de sentimiento no encontrado en resultado")
                    
            else:
                print(f"   ✗ Error generando señal: {signal_result['error']}")
        else:
            print("   ✗ Error inicializando modelo")
            
    except Exception as e:
        print(f"   ✗ Error en integración: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sentiment_integration()