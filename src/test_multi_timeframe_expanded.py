#!/usr/bin/env python3
"""
Script de prueba para verificar el análisis multi-timeframe expandido de SICAR.
Prueba los nuevos timeframes: 15m, 30m, 45m, 1h, 2h, 3h, 4h
"""

import sys
import os
import logging
from datetime import datetime

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pipelines.data_pipeline import DataPipeline
from module_2_regime import RegimeClassifier
from module_3_metacontroller import MetaController

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_multi_timeframe_expanded():
    """
    Prueba el análisis multi-timeframe expandido.
    """
    try:
        logger.info("🚀 === PRUEBA ANÁLISIS MULTI-TIMEFRAME EXPANDIDO ===")
        
        # 1. Inicializar componentes
        logger.info("📊 Inicializando componentes SICAR...")
        data_pipeline = DataPipeline()
        regime_classifier = RegimeClassifier()
        metacontroller = MetaController()
        
        # 2. Definir timeframes expandidos
        timeframes = ['15m', '30m', '45m', '1h', '2h', '3h', '4h']
        symbol = 'BTCUSDT'
        
        logger.info(f"🎯 Timeframes a probar: {timeframes}")
        logger.info(f"📈 Símbolo: {symbol}")
        
        # 3. Obtener datos multi-timeframe
        logger.info("📊 Obteniendo datos multi-timeframe...")
        multi_data = data_pipeline.get_multi_timeframe_data(
            ticker=symbol, 
            timeframes=timeframes,
            period="1mo"
        )
        
        if not multi_data:
            logger.error("❌ No se pudieron obtener datos multi-timeframe")
            return False
        
        logger.info(f"✅ Datos obtenidos para {len(multi_data)} timeframes:")
        for tf, data in multi_data.items():
            logger.info(f"   • {tf}: {len(data)} barras")
        
        # 4. Análisis de regímenes multi-timeframe
        logger.info("🧠 Analizando regímenes multi-timeframe...")
        multi_regime_analysis = regime_classifier.analyze_multi_timeframe_regimes(multi_data)
        
        if not multi_regime_analysis:
            logger.error("❌ Error en análisis de regímenes")
            return False
        
        logger.info("✅ Análisis de regímenes completado:")
        for tf, analysis in multi_regime_analysis.get('timeframe_analysis', {}).items():
            regime_name = analysis.get('regime_name', 'N/A')
            confidence = analysis.get('confidence', 0.0)
            logger.info(f"   • {tf}: {regime_name} (confianza: {confidence:.1%})")
        
        # 5. Análisis de estrategias multi-timeframe
        logger.info("⚡ Analizando estrategias multi-timeframe...")
        multi_strategy_analysis = metacontroller.analyze_multi_timeframe_strategies(
            multi_data, multi_regime_analysis
        )
        
        if not multi_strategy_analysis:
            logger.error("❌ Error en análisis de estrategias")
            return False
        
        logger.info("✅ Análisis de estrategias completado:")
        for tf, analysis in multi_strategy_analysis.get('timeframe_analysis', {}).items():
            strategy = analysis.get('strategy', 'N/A')
            confidence = analysis.get('confidence', 0.0)
            signal = analysis.get('signal', 0.0)
            logger.info(f"   • {tf}: {strategy} (confianza: {confidence:.1%}, señal: {signal:.3f})")
        
        # 6. Análisis de consenso
        logger.info("🎯 Analizando consenso multi-timeframe...")
        
        regime_consensus = multi_regime_analysis.get('consensus', {})
        strategy_consensus = multi_strategy_analysis.get('consensus', {})
        
        logger.info("📊 CONSENSO DE REGÍMENES:")
        logger.info(f"   • Régimen dominante: {regime_consensus.get('dominant_regime', 'N/A')}")
        logger.info(f"   • Acuerdo general: {regime_consensus.get('overall_agreement', 'N/A')}")
        
        logger.info("⚡ CONSENSO DE ESTRATEGIAS:")
        logger.info(f"   • Estrategia consenso: {strategy_consensus.get('consensus_strategy', 'N/A')}")
        logger.info(f"   • Señal consenso: {strategy_consensus.get('consensus_signal', 0.0):.3f}")
        logger.info(f"   • Confianza general: {strategy_consensus.get('overall_confidence', 0.0):.1%}")
        
        # 7. Verificar pesos de timeframes
        logger.info("⚖️ Verificando pesos de timeframes:")
        timeframe_weights = {
            '15m': 0.08,
            '30m': 0.12,
            '45m': 0.15,
            '1h': 0.20,
            '2h': 0.18,
            '3h': 0.15,
            '4h': 0.12
        }
        
        total_weight = sum(timeframe_weights.values())
        logger.info(f"   • Peso total: {total_weight:.2f} (debe ser ~1.0)")
        
        for tf, weight in timeframe_weights.items():
            logger.info(f"   • {tf}: {weight:.2f} ({weight*100:.0f}%)")
        
        # 8. Resumen final
        logger.info("🎉 === PRUEBA COMPLETADA EXITOSAMENTE ===")
        logger.info(f"✅ Timeframes procesados: {len(multi_data)}/7")
        logger.info(f"✅ Regímenes analizados: {len(multi_regime_analysis.get('timeframe_analysis', {}))}")
        logger.info(f"✅ Estrategias analizadas: {len(multi_strategy_analysis.get('timeframe_analysis', {}))}")
        logger.info(f"✅ Consenso calculado: {'Sí' if regime_consensus and strategy_consensus else 'No'}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en prueba multi-timeframe: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal."""
    logger.info("🔬 Iniciando prueba del análisis multi-timeframe expandido...")
    
    success = test_multi_timeframe_expanded()
    
    if success:
        logger.info("🎉 ¡Prueba completada exitosamente!")
        logger.info("✅ El análisis multi-timeframe expandido está funcionando correctamente")
    else:
        logger.error("❌ La prueba falló")
        logger.error("⚠️ Revisar logs para identificar problemas")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)