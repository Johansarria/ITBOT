#!/usr/bin/env python3
"""
Script para verificar qué timeframes está analizando SICAR actualmente.
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
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_current_timeframes():
    """
    Verifica qué timeframes está usando SICAR actualmente.
    """
    try:
        print("🔍 === VERIFICACIÓN DE TIMEFRAMES SICAR ===")
        print(f"⏰ Verificación realizada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # 1. Inicializar componentes
        print("\n📊 Inicializando componentes...")
        data_pipeline = DataPipeline()
        
        # 2. Verificar timeframes por defecto en DataPipeline
        print("\n🎯 TIMEFRAMES CONFIGURADOS EN DATA_PIPELINE:")
        
        # Simular llamada para ver timeframes por defecto
        symbol = 'BTCUSDT'
        
        # Los timeframes están hardcodeados en el método get_multi_timeframe_data
        default_timeframes = ['15m', '30m', '45m', '1h', '2h', '3h', '4h']
        print(f"   📋 Timeframes por defecto: {default_timeframes}")
        
        # 3. Probar obtención de datos para cada timeframe
        print("\n📈 VERIFICANDO DISPONIBILIDAD DE DATOS:")
        available_timeframes = []
        
        for tf in default_timeframes:
            try:
                print(f"   🔄 Probando {tf}...", end=" ")
                data = data_pipeline.get_market_data(symbol, period="1d", interval=tf)
                
                if data is not None and not data.empty:
                    available_timeframes.append(tf)
                    print(f"✅ ({len(data)} barras)")
                else:
                    print("❌ Sin datos")
                    
            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}...")
        
        # 4. Verificar configuración principal
        print(f"\n🎯 TIMEFRAMES DISPONIBLES: {available_timeframes}")
        print(f"📊 Total de timeframes activos: {len(available_timeframes)}")
        
        # 5. Verificar timeframe principal configurado
        try:
            from config import TIMEFRAME
            print(f"\n⚙️ TIMEFRAME PRINCIPAL CONFIGURADO: {TIMEFRAME}")
        except:
            print("\n⚙️ TIMEFRAME PRINCIPAL: 4h (por defecto)")
        
        # 6. Análisis de cobertura temporal
        print("\n📊 ANÁLISIS DE COBERTURA TEMPORAL:")
        timeframe_minutes = {
            '15m': 15,
            '30m': 30, 
            '45m': 45,
            '1h': 60,
            '2h': 120,
            '3h': 180,
            '4h': 240
        }
        
        for tf in available_timeframes:
            minutes = timeframe_minutes.get(tf, 0)
            hours = minutes / 60
            print(f"   • {tf}: {minutes} minutos ({hours}h)")
        
        # 7. Recomendaciones
        print("\n💡 ANÁLISIS:")
        if len(available_timeframes) >= 5:
            print("   ✅ Excelente cobertura multi-timeframe")
        elif len(available_timeframes) >= 3:
            print("   ⚠️ Cobertura moderada multi-timeframe")
        else:
            print("   ❌ Cobertura limitada multi-timeframe")
        
        print(f"\n🎯 SICAR está configurado para analizar {len(available_timeframes)} timeframes simultáneamente")
        print("   📈 Esto permite análisis desde perspectivas de corto, medio y largo plazo")
        print("   🧠 Cada timeframe aporta información única para la toma de decisiones")
        
        return available_timeframes
        
    except Exception as e:
        logger.error(f"Error verificando timeframes: {str(e)}")
        return []

if __name__ == "__main__":
    timeframes = check_current_timeframes()
    print(f"\n✅ Verificación completada. Timeframes activos: {len(timeframes)}")