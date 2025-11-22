# /src/test_dynamic_xai.py

import os
import sys
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar módulos SICAR
from module_1_causal import CausalCartographer
from module_2_regime import RegimeClassifier
from module_3_metacontroller import MetaController, create_labels
from module_xai import generate_dynamic_cognitive_report
from config import *

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_test_data(days=100):
    """Genera datos de prueba para el XAI dinámico."""
    points_per_day = 6  # 4 horas
    total_points = days * points_per_day
    
    start_date = datetime.now() - timedelta(days=days)
    dates = pd.date_range(start=start_date, periods=total_points, freq='4H')
    
    np.random.seed(42)
    initial_price = 45000.0
    
    # Generar datos más realistas
    trend = np.cumsum(np.random.normal(0, 0.0001, total_points))
    volatility = 0.005 + 0.002 * np.sin(np.arange(total_points) * 2 * np.pi / (30 * points_per_day))
    daily_returns = np.random.normal(trend, volatility)
    daily_returns = np.clip(daily_returns, -0.05, 0.05)
    
    cumulative_returns = np.cumsum(daily_returns)
    prices = initial_price * (1 + cumulative_returns)
    
    # Generar volumen
    base_volume = 1000000
    volume_noise = np.random.normal(1, 0.3, total_points)
    volume = base_volume * np.abs(volume_noise)
    
    # Generar OHLC
    price_noise = np.random.normal(0, 0.002, total_points)
    open_prices = prices * (1 + price_noise * 0.5)
    high_prices = prices * (1 + np.abs(price_noise))
    low_prices = prices * (1 - np.abs(price_noise))
    close_prices = prices
    
    data = pd.DataFrame({
        'Open': open_prices.astype(np.float64),
        'High': high_prices.astype(np.float64),
        'Low': low_prices.astype(np.float64),
        'Close': close_prices.astype(np.float64),
        'Volume': volume.astype(np.float64)
    }, index=dates)
    
    # Asegurar consistencia OHLC
    data['High'] = np.maximum(data['High'], np.maximum(data['Open'], data['Close']))
    data['Low'] = np.minimum(data['Low'], np.minimum(data['Open'], data['Close']))
    
    return data

def test_dynamic_xai():
    """Prueba el módulo XAI dinámico con datos reales de todos los módulos."""
    try:
        logger.info("🧠 PROBANDO MÓDULO XAI DINÁMICO")
        logger.info("="*50)
        
        # 1. Generar datos de prueba
        market_data = generate_test_data(days=100)
        logger.info(f"Datos generados: {len(market_data)} puntos")
        
        # 2. Inicializar módulos SICAR
        logger.info("Inicializando módulos SICAR...")
        
        # Módulo 1 - Causal Cartographer
        causal_cartographer = CausalCartographer()
        
        # Módulo 2 - Regime Classifier
        regime_classifier = RegimeClassifier()
        # Convertir nombres de columnas a minúsculas para compatibilidad
        market_data_lower = market_data.copy()
        market_data_lower.columns = market_data_lower.columns.str.lower()
        regime_results = regime_classifier.classify_regimes(market_data_lower)
        
        # Módulo 3 - Metacontroller
        metacontroller = MetaController()
        
        # Entrenar metacontroller
        features = metacontroller.prepare_features(market_data_lower)
        if not features.empty:
            labels = create_labels(market_data_lower)
            # Alinear datos
            aligned_data = pd.concat([features, labels.rename('label')], axis=1).dropna()
            if len(aligned_data) > 10:
                features_aligned = aligned_data.drop(columns=['label'])
                labels_aligned = aligned_data['label']
                metacontroller.train_metacontroller(features_aligned, labels_aligned)
                logger.info("✅ Metacontroller entrenado correctamente")
        
        # 3. Simular una decisión de trading
        logger.info("Simulando decisión de trading...")
        
        # Obtener estrategia del metacontroller
        recent_features = metacontroller.prepare_features(market_data_lower.tail(50))
        if not recent_features.empty:
            strategy, confidence = metacontroller.predict_strategy(recent_features)
            signal = metacontroller.execute_strategy(strategy, market_data_lower.tail(20))
            
            # Determinar decisión basada en señal
            if signal > 0.5:
                decision = "BUY"
            elif signal < -0.5:
                decision = "SELL"
            else:
                decision = "HOLD"
        else:
            strategy = "momentum"
            confidence = 0.75
            decision = "BUY"
        
        logger.info(f"Decisión: {decision}, Estrategia: {strategy}, Confianza: {confidence:.2f}")
        
        # 4. Generar reporte cognitivo dinámico
        logger.info("Generando reporte cognitivo dinámico...")
        
        dynamic_report = generate_dynamic_cognitive_report(
            metacontroller=metacontroller,
            regime_classifier=regime_classifier,
            causal_cartographer=causal_cartographer,
            market_data=market_data_lower,
            decision=decision,
            strategy=strategy,
            confidence=confidence,
            additional_context={
                'test_mode': 'True',
                'data_source': 'Simulado'
            }
        )
        
        # 5. Mostrar resultados
        logger.info("="*50)
        logger.info("📋 REPORTE COGNITIVO DINÁMICO GENERADO")
        logger.info("="*50)
        print("\n" + dynamic_report)
        logger.info("="*50)
        
        # 6. Guardar reporte
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"../reports/reporte_dinamico_{timestamp}.txt"
        
        try:
            os.makedirs("../reports", exist_ok=True)
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(f"REPORTE COGNITIVO DINÁMICO SICAR\n")
                f.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Decisión: {decision}\n")
                f.write(f"Estrategia: {strategy}\n")
                f.write(f"Confianza: {confidence:.2f}\n")
                f.write("="*50 + "\n\n")
                f.write(dynamic_report)
            
            logger.info(f"✅ Reporte guardado en: {report_filename}")
        except Exception as e:
            logger.warning(f"No se pudo guardar el reporte: {str(e)}")
        
        logger.info("✅ MÓDULO XAI DINÁMICO FUNCIONANDO CORRECTAMENTE")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en prueba XAI dinámico: {str(e)}")
        return False

if __name__ == '__main__':
    success = test_dynamic_xai()
    if success:
        print("\n🎉 ¡MÓDULO XAI DINÁMICO FUNCIONANDO PERFECTAMENTE!")
    else:
        print("\n❌ Error en el módulo XAI dinámico. Revisa los logs.")