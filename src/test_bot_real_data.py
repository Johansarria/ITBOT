#!/usr/bin/env python3
"""
Test del Bot SICAR completo con datos reales de Binance
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import pandas as pd

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main_bot import TradingBot
import config

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_bot_real_data.log')
    ]
)

logger = logging.getLogger(__name__)

def test_bot_initialization():
    """Prueba la inicialización del bot."""
    logger.info("=== PRUEBA DE INICIALIZACIÓN DEL BOT ===")
    
    try:
        # Crear instancia del bot (usa configuración por defecto desde variables de entorno)
        bot = TradingBot()
        logger.info(f"Configuración cargada: {bot.config['symbol']}")
        logger.info("Bot creado exitosamente")
        
        # Verificar inicialización de modelos
        if bot.initialize_models():
            logger.info("✅ Modelos inicializados correctamente")
            return bot
        else:
            logger.error("❌ Error inicializando modelos")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error en inicialización: {str(e)}")
        return None

def test_binance_connection(bot):
    """Prueba la conexión con Binance."""
    logger.info("=== PRUEBA DE CONEXIÓN CON BINANCE ===")
    
    try:
        # Probar obtención de datos de mercado
        market_data = bot.get_binance_data()
        
        if not market_data.empty:
            logger.info(f"✅ Datos de Binance obtenidos: {len(market_data)} registros")
            logger.info(f"Rango de fechas: {market_data.index[0]} a {market_data.index[-1]}")
            logger.info(f"Precio actual: ${market_data['close'].iloc[-1]:.2f}")
            logger.info(f"Volatilidad promedio: {market_data['volatility'].mean():.4f}")
            return True
        else:
            logger.error("❌ No se pudieron obtener datos de Binance")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error conectando con Binance: {str(e)}")
        return False

def test_market_analysis(bot):
    """Prueba el análisis completo de mercado."""
    logger.info("=== PRUEBA DE ANÁLISIS DE MERCADO ===")
    
    try:
        # Obtener datos de mercado
        market_data = bot.get_market_data()
        
        if market_data.empty:
            logger.error("❌ No se pudieron obtener datos para análisis")
            return False
        
        # Ejecutar análisis completo
        analysis_results = bot.analyze_market(market_data)
        
        if analysis_results:
            logger.info("✅ Análisis de mercado completado")
            
            # Mostrar resultados del análisis causal
            if 'causal_analysis' in analysis_results:
                causal = analysis_results['causal_analysis']
                logger.info(f"Análisis Causal - Sentimiento: {causal.get('sentiment', 0):.3f}")
            
            # Mostrar resultados del análisis de régimen
            if 'regime_analysis' in analysis_results:
                regime = analysis_results['regime_analysis']
                logger.info(f"Régimen de Mercado: {regime.get('regime_name', 'N/A')} (confianza: {regime.get('confidence', 0):.3f})")
            
            # Mostrar decisión de estrategia
            if 'strategy_decision' in analysis_results:
                strategy = analysis_results['strategy_decision']
                logger.info(f"Estrategia: {strategy.get('strategy', 'N/A')} (señal: {strategy.get('signal', 0):.3f})")
            
            # Mostrar reporte XAI
            if 'xai_report' in analysis_results and analysis_results['xai_report']:
                logger.info("✅ Reporte cognitivo XAI generado")
            
            return True
        else:
            logger.error("❌ Error en análisis de mercado")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en análisis: {str(e)}")
        return False

def test_trading_decision(bot):
    """Prueba la toma de decisiones de trading."""
    logger.info("=== PRUEBA DE DECISIONES DE TRADING ===")
    
    try:
        # Obtener datos y análisis
        market_data = bot.get_market_data()
        analysis_results = bot.analyze_market(market_data)
        
        if not analysis_results:
            logger.error("❌ No se pudo realizar análisis para decisión")
            return False
        
        # Ejecutar decisión de trading
        decision = bot.execute_trading_decision(analysis_results, market_data)
        
        if decision:
            logger.info(f"✅ Decisión de trading: {decision.get('action', 'N/A')}")
            logger.info(f"Razón: {decision.get('reason', 'N/A')}")
            
            if decision.get('action') != 'hold':
                logger.info(f"Tamaño de posición: {decision.get('position_size', 0):.4f}")
                logger.info(f"Precio objetivo: ${decision.get('target_price', 0):.2f}")
            
            return True
        else:
            logger.error("❌ No se pudo tomar decisión de trading")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en decisión de trading: {str(e)}")
        return False

def test_complete_cycle(bot):
    """Prueba un ciclo completo del bot."""
    logger.info("=== PRUEBA DE CICLO COMPLETO ===")
    
    try:
        # Simular una iteración completa del bot
        logger.info("Ejecutando ciclo completo...")
        
        # 1. Obtener datos
        market_data = bot.get_market_data()
        if market_data.empty:
            logger.error("❌ No se pudieron obtener datos")
            return False
        
        # 2. Analizar mercado
        analysis = bot.analyze_market(market_data)
        if not analysis:
            logger.error("❌ Error en análisis")
            return False
        
        # 3. Tomar decisión
        decision = bot.execute_trading_decision(analysis, market_data)
        if not decision:
            logger.error("❌ Error en decisión")
            return False
        
        # 4. Guardar logs
        bot.save_logs()
        
        # 5. Mostrar estadísticas
        stats = bot.get_performance_stats()
        logger.info(f"✅ Ciclo completo exitoso")
        logger.info(f"Estadísticas: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en ciclo completo: {str(e)}")
        return False

def main():
    """Función principal de pruebas."""
    logger.info("🚀 INICIANDO PRUEBAS DEL BOT SICAR CON DATOS REALES")
    
    # Contadores de pruebas
    tests_passed = 0
    total_tests = 5
    
    # 1. Prueba de inicialización
    bot = test_bot_initialization()
    if bot:
        tests_passed += 1
    else:
        logger.error("❌ Prueba de inicialización falló - abortando")
        return
    
    # 2. Prueba de conexión Binance
    if test_binance_connection(bot):
        tests_passed += 1
    
    # 3. Prueba de análisis de mercado
    if test_market_analysis(bot):
        tests_passed += 1
    
    # 4. Prueba de decisiones de trading
    if test_trading_decision(bot):
        tests_passed += 1
    
    # 5. Prueba de ciclo completo
    if test_complete_cycle(bot):
        tests_passed += 1
    
    # Resumen final
    logger.info("=" * 50)
    logger.info(f"RESUMEN DE PRUEBAS: {tests_passed}/{total_tests} exitosas")
    
    if tests_passed == total_tests:
        logger.info("🎉 ¡TODAS LAS PRUEBAS PASARON! El bot está listo para operar.")
    else:
        logger.warning(f"⚠️  {total_tests - tests_passed} pruebas fallaron. Revisar logs.")
    
    logger.info("=" * 50)

if __name__ == "__main__":
    main()