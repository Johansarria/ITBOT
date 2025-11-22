#!/usr/bin/env python3
"""
Test de Integración - Análisis de OrderBook Híbrido
==================================================

Script para verificar que la integración del análisis de orderbook
funciona correctamente con el sistema híbrido inteligente existente.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List
import requests

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_orderbook_analyzer():
    """Test del analizador de orderbook independiente"""
    try:
        from orderbook_analyzer import OrderBookAnalyzer
        
        logger.info("🔍 Probando OrderBook Analyzer...")
        
        # Crear instancia del analizador
        analyzer = OrderBookAnalyzer()
        
        # Obtener datos reales de Binance
        symbol = "BTCUSDT"
        depth_url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit=20"
        response = requests.get(depth_url, timeout=10)
        depth_data = response.json()
        
        # Analizar datos
        metrics = analyzer.analyze_depth_data(symbol, depth_data)
        
        if metrics:
            logger.info(f"✅ Análisis exitoso para {symbol}")
            logger.info(f"   📊 Spread: {metrics.spread_percentage:.3f}%")
            logger.info(f"   💧 Liquidez: {metrics.liquidity_score:.1f}")
            logger.info(f"   ⚖️ Imbalance: {metrics.volume_imbalance:.3f}")
            logger.info(f"   🎯 Calidad: {metrics.depth_quality:.1f}")
            return True
        else:
            logger.error("❌ No se pudieron obtener métricas")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en test de OrderBook Analyzer: {e}")
        return False

def test_logging_integration():
    """Test de integración con el sistema de logging avanzado"""
    try:
        from advanced_logging_system import AdvancedLoggingSystem, MarketConditions
        
        logger.info("📊 Probando integración con sistema de logging...")
        
        # Crear sistema de logging
        logging_system = AdvancedLoggingSystem()
        
        # Obtener datos reales
        symbol = "ETHUSDT"
        depth_url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit=20"
        ticker_url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
        
        depth_response = requests.get(depth_url, timeout=10)
        ticker_response = requests.get(ticker_url, timeout=10)
        
        depth_data = depth_response.json()
        ticker_data = ticker_response.json()
        
        # Crear condiciones de mercado
        conditions = MarketConditions(
            timestamp=datetime.now(timezone.utc),
            symbol=symbol,
            price=float(ticker_data['lastPrice']),
            volume=float(ticker_data['volume']),
            volatility=float(ticker_data['priceChangePercent']),
            trend_direction="neutral",
            market_session="active",
            spread=0.01
        )
        
        # Log con datos de orderbook
        logging_system.log_market_conditions(conditions, "TestIntegration", depth_data)
        
        logger.info(f"✅ Integración exitosa con logging para {symbol}")
        logger.info(f"   📈 Precio: ${conditions.price:.2f}")
        
        if conditions.order_book_depth:
            logger.info(f"   📊 OrderBook procesado: {len(conditions.order_book_depth)} métricas")
            spread = conditions.order_book_depth.get('spread_pct', 0)
            liquidity = conditions.order_book_depth.get('liquidity_score', 0)
            logger.info(f"   💹 Spread: {spread:.3f}% | Liquidez: {liquidity:.1f}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en test de integración con logging: {e}")
        return False

def test_market_preparation_integration():
    """Test de integración con preparación de activación de mercado"""
    try:
        from preparacion_activacion_mercado import MarketActivationPreparation
        
        logger.info("🚀 Probando integración con preparación de mercado...")
        
        # Crear instancia de preparación
        preparation = MarketActivationPreparation()
        
        # Obtener datos de mercado (incluye análisis de orderbook)
        market_data = preparation.get_comprehensive_market_data()
        
        if market_data:
            logger.info(f"✅ Datos de mercado obtenidos para {len(market_data)} símbolos")
            
            for symbol, data in market_data.items():
                if 'orderbook_metrics' in data and data['orderbook_metrics']:
                    metrics = data['orderbook_metrics']
                    spread = metrics.get('spread_pct', 0)
                    liquidity = metrics.get('liquidity_score', 0)
                    logger.info(f"   📊 {symbol}: Spread={spread:.3f}% | Liquidez={liquidity:.1f}")
                else:
                    logger.info(f"   📊 {symbol}: Sin análisis de orderbook")
            
            return True
        else:
            logger.error("❌ No se pudieron obtener datos de mercado")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en test de preparación de mercado: {e}")
        return False

def test_integration_function():
    """Test de la función de integración directa"""
    try:
        from orderbook_analyzer import integrate_with_market_conditions
        
        logger.info("🔗 Probando función de integración directa...")
        
        # Obtener datos reales
        symbol = "ADAUSDT"
        depth_url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit=20"
        response = requests.get(depth_url, timeout=10)
        depth_data = response.json()
        
        # Usar función de integración
        metrics = integrate_with_market_conditions(depth_data, symbol)
        
        if metrics:
            logger.info(f"✅ Función de integración exitosa para {symbol}")
            logger.info(f"   📊 Métricas obtenidas: {len(metrics)} campos")
            
            for key, value in metrics.items():
                if isinstance(value, float):
                    logger.info(f"   🔹 {key}: {value:.4f}")
                else:
                    logger.info(f"   🔹 {key}: {value}")
            
            return True
        else:
            logger.error("❌ No se pudieron obtener métricas de integración")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en test de función de integración: {e}")
        return False

def run_comprehensive_test():
    """Ejecutar test completo de integración"""
    logger.info("🚀 Iniciando test completo de integración de OrderBook Híbrido")
    logger.info("=" * 60)
    
    tests = [
        ("OrderBook Analyzer", test_orderbook_analyzer),
        ("Integración con Logging", test_logging_integration),
        ("Preparación de Mercado", test_market_preparation_integration),
        ("Función de Integración", test_integration_function)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Ejecutando: {test_name}")
        logger.info("-" * 40)
        
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                logger.info(f"✅ {test_name}: EXITOSO")
            else:
                logger.error(f"❌ {test_name}: FALLIDO")
                
        except Exception as e:
            logger.error(f"💥 {test_name}: ERROR - {e}")
            results.append((test_name, False))
        
        time.sleep(1)  # Pausa entre tests
    
    # Resumen final
    logger.info("\n" + "=" * 60)
    logger.info("📋 RESUMEN DE TESTS")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ EXITOSO" if result else "❌ FALLIDO"
        logger.info(f"   {test_name}: {status}")
    
    logger.info(f"\n🎯 Resultado final: {passed}/{total} tests exitosos")
    
    if passed == total:
        logger.info("🎉 ¡INTEGRACIÓN COMPLETA EXITOSA!")
        logger.info("🔥 El análisis de OrderBook híbrido está funcionando correctamente")
    else:
        logger.warning("⚠️ Algunos tests fallaron - revisar logs para detalles")
    
    return passed == total

if __name__ == "__main__":
    success = run_comprehensive_test()
    exit(0 if success else 1)