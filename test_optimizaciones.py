#!/usr/bin/env python3
"""
Test completo del sistema SICAR con todas las optimizaciones implementadas
"""

from src.module_patchtst_integration import PatchTSTIntegration
from src.crypto_data_loader import CryptoDataLoader
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_sistema_completo():
    print('🧪 Iniciando test completo del sistema SICAR optimizado...')
    print('='*60)
    
    # Crear instancias
    model = PatchTSTIntegration('BTC-USD')
    
    # Inicializar modelo
    print('⚙️ Inicializando modelo...')
    model.initialize_model(load_pretrained=True, force_retrain=False)
    
    # Ejecutar análisis completo
    print('📊 Analizando BTC-USD con todas las optimizaciones...')
    result = model.generate_signal()
    
    print('\n📈 RESULTADO DEL ANÁLISIS:')
    print(f'Señal: {result["signal"]}')
    print(f'Confianza: {result["confidence"]:.1%}')
    print(f'Recomendación: {result["recommendation"]}')
    
    if result.get('breakout_validation'):
        print(f'Validación de ruptura: {result["breakout_validation"]["validation"]["status"]}')
        print(f'Score de validación: {result["breakout_validation"]["validation"]["total_score"]}/{result["breakout_validation"]["validation"]["validation_threshold"]}')
    
    if result.get('market_conditions'):
        conditions = result['market_conditions']
        print(f'\n📊 CONDICIONES DE MERCADO:')
        print(f'Sentimiento: {conditions["sentiment_classification"]} ({conditions["sentiment_score"]:.2f})')
        print(f'Volatilidad actual: {conditions.get("current_atr_pct", 0):.2%}')
        print(f'Factor de volatilidad: {conditions.get("volatility_factor", 1):.2f}')
        
    print('\n✅ Test completado exitosamente!')
    
    # Validar que no hayan señales contradictorias
    print('\n🔍 VALIDACIÓN DE CONSISTENCIA:')
    
    # Verificar que no recomiende BUY en mercado bajista extremo
    if result['signal'] == 'BUY' and result['market_conditions']['sentiment_score'] < -0.7:
        print('⚠️  ADVERTENCIA: Señal BUY en mercado extremadamente bajista')
    
    # Verificar que la confianza no sea excesivamente alta en condiciones adversas
    if result['confidence'] > 0.8 and result['market_conditions'].get('volatility_factor', 1) < 0.6:
        print('⚠️  ADVERTENCIA: Alta confianza con alta volatilidad detectada')
    
    # Verificar validación de rupturas
    if result.get('breakout_validation') and result['breakout_validation']['validation']['status'] == 'FAKEOUT':
        print('⚠️  ADVERTENCIA: Ruptura potencialmente falsa detectada')
    
    print('✅ Validación de consistencia completada!')
    
    return result

if __name__ == '__main__':
    test_sistema_completo()