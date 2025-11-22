"""
SICAR - Test Breakout-Portfolio Integration
Script de prueba para la integración entre breakout y optimización de portafolio
"""

import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

try:
    from breakout_portfolio_integration import (
        BreakoutPortfolioIntegrator,
        BreakoutPortfolioStrategy,
        start_breakout_portfolio_integration,
        stop_breakout_portfolio_integration,
        get_integration_status,
        get_integration_signals
    )
    from first_candle_breakout import FirstCandleBreakoutDetector, BreakoutSignal
    from session_detector import SessionDetector
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    MODULES_AVAILABLE = False

def test_integration_basic():
    """Prueba básica de la integración"""
    print("=== Prueba Básica de Integración ===")
    
    if not MODULES_AVAILABLE:
        print("❌ Módulos no disponibles")
        return False
    
    try:
        # Crear integrador
        integrator = BreakoutPortfolioIntegrator(initial_capital=10000.0)
        
        # Verificar estado inicial
        status = integrator.get_portfolio_status()
        print(f"✅ Estado inicial: {status['is_running']}")
        
        # Iniciar integración
        integrator.start_integration(BreakoutPortfolioStrategy.CONFIDENCE_SCALED)
        
        # Verificar que está ejecutándose
        status = integrator.get_portfolio_status()
        print(f"✅ Integración iniciada: {status['is_running']}")
        print(f"📊 Estrategia: {status['strategy']}")
        
        # Esperar un poco
        print("⏳ Esperando actividad...")
        time.sleep(10)
        
        # Verificar señales
        signals = integrator.get_active_signals()
        print(f"📡 Señales activas: {len(signals)}")
        
        # Mostrar estado del portafolio
        status = integrator.get_portfolio_status()
        weights = status.get('portfolio_weights', {})
        print(f"💼 Posiciones en portafolio: {len(weights)}")
        
        for symbol, weight in weights.items():
            if weight > 0.01:  # Solo mostrar posiciones significativas
                print(f"  {symbol}: {weight:.1%}")
        
        # Detener integración
        integrator.stop_integration()
        print("✅ Integración detenida")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba básica: {e}")
        return False

def test_manual_breakout_signal():
    """Prueba con señal de breakout manual"""
    print("\n=== Prueba con Señal Manual ===")
    
    if not MODULES_AVAILABLE:
        print("❌ Módulos no disponibles")
        return False
    
    try:
        # Crear integrador
        integrator = BreakoutPortfolioIntegrator()
        
        # Crear señal de breakout manual
        manual_signal = BreakoutSignal(
            timestamp=datetime.now(),
            symbol="BTCUSDT",
            session="european",
            signal_type="bullish_breakout",
            entry_price=45000.0,
            stop_loss=44500.0,
            take_profit=46000.0,
            volume_ratio=2.5,
            confidence=0.85,
            candle_data={
                'open': 44800.0,
                'high': 45200.0,
                'low': 44700.0,
                'close': 45000.0,
                'volume': 1500000
            }
        )
        
        print(f"📊 Señal manual creada para {manual_signal.symbol}")
        print(f"  Tipo: {manual_signal.signal_type}")
        print(f"  Confianza: {manual_signal.confidence:.1%}")
        print(f"  Precio entrada: ${manual_signal.entry_price:,.2f}")
        
        # Iniciar integración
        integrator.start_integration(BreakoutPortfolioStrategy.CONFIDENCE_SCALED)
        
        # Simular procesamiento de la señal
        integrator._on_breakout_detected(manual_signal)
        
        # Verificar resultado
        status = integrator.get_portfolio_status()
        weights = status.get('portfolio_weights', {})
        
        print(f"💼 Resultado en portafolio:")
        for symbol, weight in weights.items():
            print(f"  {symbol}: {weight:.1%}")
        
        # Verificar señales activas
        signals = integrator.get_active_signals()
        if signals:
            signal = signals[0]
            print(f"📡 Señal procesada:")
            print(f"  Asignación recomendada: {signal['recommended_allocation']:.1%}")
            print(f"  Score de riesgo: {signal['risk_score']:.2f}")
            print(f"  Retorno esperado: {signal['expected_return']:.1%}")
        
        # Detener
        integrator.stop_integration()
        
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba manual: {e}")
        return False

def test_multiple_strategies():
    """Prueba con múltiples estrategias"""
    print("\n=== Prueba con Múltiples Estrategias ===")
    
    if not MODULES_AVAILABLE:
        print("❌ Módulos no disponibles")
        return False
    
    strategies = [
        BreakoutPortfolioStrategy.CONFIDENCE_SCALED,
        BreakoutPortfolioStrategy.RISK_ADJUSTED,
        BreakoutPortfolioStrategy.MOMENTUM_WEIGHTED
    ]
    
    results = {}
    
    for strategy in strategies:
        try:
            print(f"\n🔄 Probando estrategia: {strategy.value}")
            
            # Crear integrador
            integrator = BreakoutPortfolioIntegrator()
            
            # Crear señal de prueba
            test_signal = BreakoutSignal(
                timestamp=datetime.now(),
                symbol="ETHUSDT",
                session="american",
                signal_type="bullish_breakout",
                entry_price=2500.0,
                stop_loss=2450.0,
                take_profit=2600.0,
                volume_ratio=1.8,
                confidence=0.75,
                candle_data={
                    'open': 2480.0,
                    'high': 2520.0,
                    'low': 2470.0,
                    'close': 2500.0,
                    'volume': 800000
                }
            )
            
            # Iniciar con estrategia específica
            integrator.start_integration(strategy)
            
            # Procesar señal
            integrator._on_breakout_detected(test_signal)
            
            # Obtener resultado
            signals = integrator.get_active_signals()
            if signals:
                signal = signals[0]
                allocation = signal['recommended_allocation']
                risk_score = signal['risk_score']
                
                results[strategy.value] = {
                    'allocation': allocation,
                    'risk_score': risk_score,
                    'expected_return': signal['expected_return']
                }
                
                print(f"  ✅ Asignación: {allocation:.1%}")
                print(f"  📊 Riesgo: {risk_score:.2f}")
                print(f"  💰 Retorno esperado: {signal['expected_return']:.1%}")
            
            # Detener
            integrator.stop_integration()
            
        except Exception as e:
            print(f"  ❌ Error con {strategy.value}: {e}")
            results[strategy.value] = {'error': str(e)}
    
    # Comparar resultados
    print(f"\n📊 Comparación de Estrategias:")
    for strategy, result in results.items():
        if 'error' not in result:
            print(f"  {strategy}:")
            print(f"    Asignación: {result['allocation']:.1%}")
            print(f"    Riesgo: {result['risk_score']:.2f}")
            print(f"    Retorno: {result['expected_return']:.1%}")
    
    return True

def test_portfolio_rebalancing():
    """Prueba de rebalanceo de portafolio"""
    print("\n=== Prueba de Rebalanceo ===")
    
    if not MODULES_AVAILABLE:
        print("❌ Módulos no disponibles")
        return False
    
    try:
        # Crear integrador con rebalanceo frecuente
        integrator = BreakoutPortfolioIntegrator()
        integrator.rebalance_frequency = timedelta(seconds=5)  # Rebalanceo cada 5 segundos
        
        # Iniciar integración
        integrator.start_integration(BreakoutPortfolioStrategy.DYNAMIC_ALLOCATION)
        
        # Simular múltiples señales
        symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
        
        for i, symbol in enumerate(symbols):
            signal = BreakoutSignal(
                timestamp=datetime.now(),
                symbol=symbol,
                session="european",
                signal_type="bullish_breakout",
                entry_price=1000.0 + i * 100,
                stop_loss=950.0 + i * 100,
                take_profit=1100.0 + i * 100,
                volume_ratio=2.0 + i * 0.5,
                confidence=0.7 + i * 0.05,
                candle_data={
                    'open': 990.0 + i * 100,
                    'high': 1020.0 + i * 100,
                    'low': 980.0 + i * 100,
                    'close': 1000.0 + i * 100,
                    'volume': 500000 + i * 100000
                }
            )
            
            print(f"📡 Procesando señal {i+1}: {symbol}")
            integrator._on_breakout_detected(signal)
            
            # Esperar un poco entre señales
            time.sleep(2)
        
        # Esperar rebalanceo
        print("⏳ Esperando rebalanceo...")
        time.sleep(10)
        
        # Verificar estado final
        status = integrator.get_portfolio_status()
        weights = status.get('portfolio_weights', {})
        
        print(f"💼 Portafolio final:")
        total_weight = 0
        for symbol, weight in weights.items():
            print(f"  {symbol}: {weight:.1%}")
            total_weight += weight
        
        print(f"📊 Peso total: {total_weight:.1%}")
        
        # Verificar normalización
        if abs(total_weight - 1.0) < 0.01:
            print("✅ Portafolio correctamente normalizado")
        else:
            print("⚠️ Portafolio no normalizado correctamente")
        
        # Detener
        integrator.stop_integration()
        
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba de rebalanceo: {e}")
        return False

def main():
    """Función principal de pruebas"""
    print("🚀 SICAR - Test Breakout-Portfolio Integration")
    print("=" * 50)
    
    if not MODULES_AVAILABLE:
        print("❌ No se pueden ejecutar las pruebas - módulos no disponibles")
        return
    
    # Ejecutar pruebas
    tests = [
        ("Integración Básica", test_integration_basic),
        ("Señal Manual", test_manual_breakout_signal),
        ("Múltiples Estrategias", test_multiple_strategies),
        ("Rebalanceo de Portafolio", test_portfolio_rebalancing)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 Ejecutando: {test_name}")
        try:
            success = test_func()
            results[test_name] = "✅ PASS" if success else "❌ FAIL"
        except Exception as e:
            results[test_name] = f"❌ ERROR: {str(e)}"
        
        # Pausa entre pruebas
        time.sleep(2)
    
    # Resumen de resultados
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 50)
    
    for test_name, result in results.items():
        print(f"{test_name}: {result}")
    
    # Estadísticas
    passed = sum(1 for r in results.values() if "PASS" in r)
    total = len(results)
    
    print(f"\n📈 Estadísticas: {passed}/{total} pruebas exitosas ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron exitosamente!")
    else:
        print("⚠️ Algunas pruebas fallaron - revisar logs para detalles")

if __name__ == "__main__":
    main()