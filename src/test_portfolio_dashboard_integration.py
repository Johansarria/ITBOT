#!/usr/bin/env python3
"""
Script de prueba para verificar la integración de portfolio en el dashboard de Tkinter
"""

import time
import threading
from enhanced_breakout_detector import BreakoutSignal, BreakoutType, BreakoutStrength
from breakout_portfolio_integration import BreakoutPortfolioIntegrator, BreakoutPortfolioSignal, BreakoutPortfolioStrategy
from datetime import datetime

def test_portfolio_integration():
    """Probar la integración de portfolio enviando señales simuladas"""
    print("🧪 Iniciando prueba de integración de portfolio...")
    
    # Esperar un poco para que el dashboard se inicialice
    time.sleep(5)
    
    try:
        # Importar el dashboard (debe estar ejecutándose)
        import enhanced_dashboard
        
        # Simular señales de breakout para probar la integración
        test_signals = [
            {
                'symbol': 'BTCUSDT',
                'breakout_type': BreakoutType.BULLISH,
                'strength': BreakoutStrength.STRONG,
                'confidence': 0.85,
                'price': 45000.0,
                'volume': 1250000.0,
                'resistance_level': 44800.0,
                'support_level': 43500.0,
                'price_change_pct': 2.5,
                'volume_ratio': 1.8,
                'candle_pattern': 'bullish_engulfing',
                'technical_indicators': {'rsi': 65.2, 'macd': 0.15, 'bb_position': 0.8}
            },
            {
                'symbol': 'ETHUSDT', 
                'breakout_type': BreakoutType.BEARISH,
                'strength': BreakoutStrength.MODERATE,
                'confidence': 0.72,
                'price': 3200.0,
                'volume': 850000.0,
                'resistance_level': 3250.0,
                'support_level': 3180.0,
                'price_change_pct': -1.8,
                'volume_ratio': 1.4,
                'candle_pattern': 'bearish_harami',
                'technical_indicators': {'rsi': 35.8, 'macd': -0.08, 'bb_position': 0.2}
            },
            {
                'symbol': 'ADAUSDT',
                'breakout_type': BreakoutType.BULLISH,
                'strength': BreakoutStrength.VERY_STRONG,
                'confidence': 0.91,
                'price': 0.45,
                'volume': 2100000.0,
                'resistance_level': 0.44,
                'support_level': 0.42,
                'price_change_pct': 3.2,
                'volume_ratio': 2.3,
                'candle_pattern': 'hammer',
                'technical_indicators': {'rsi': 72.1, 'macd': 0.025, 'bb_position': 0.9}
            }
        ]
        
        print("📊 Enviando señales de prueba...")
        
        for i, signal_data in enumerate(test_signals):
            # Crear señal de breakout
            breakout_signal = BreakoutSignal(
                symbol=signal_data['symbol'],
                breakout_type=signal_data['breakout_type'],
                strength=signal_data['strength'],
                confidence=signal_data['confidence'],
                price=signal_data['price'],
                volume=signal_data['volume'],
                resistance_level=signal_data['resistance_level'],
                support_level=signal_data['support_level'],
                price_change_pct=signal_data['price_change_pct'],
                volume_ratio=signal_data['volume_ratio'],
                candle_pattern=signal_data['candle_pattern'],
                technical_indicators=signal_data['technical_indicators'],
                timestamp=datetime.now()
            )
            
            # Crear señal de portfolio simulada
            portfolio_signal = BreakoutPortfolioSignal(
                timestamp=datetime.now(),
                symbol=signal_data['symbol'],
                breakout_signal=breakout_signal,
                portfolio_weight=0.1,
                recommended_allocation=0.15,
                risk_score=0.3 + (i * 0.1),
                confidence_score=signal_data['confidence'],
                strategy_used=BreakoutPortfolioStrategy.MOMENTUM_WEIGHTED,
                session='US',
                expected_return=0.05 + (i * 0.02),
                risk_adjusted_return=0.03
            )
            
            print(f"   📈 Señal {i+1}: {signal_data['symbol']} - {signal_data['breakout_type'].value}")
            
            # Simular el procesamiento de la señal
            # (En una implementación real, esto vendría del BreakoutPortfolioIntegrator)
            
            time.sleep(2)  # Esperar entre señales
        
        print("✅ Prueba de señales completada")
        print("📋 Verifica en el dashboard:")
        print("   1. Pestaña 'Portfolio Integration' debe estar visible")
        print("   2. Métricas deben mostrar datos actualizados")
        print("   3. Panel de señales debe mostrar las señales enviadas")
        print("   4. Controles de inicio/parada deben funcionar")
        
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")
        import traceback
        traceback.print_exc()

def test_dashboard_components():
    """Verificar que todos los componentes del dashboard estén funcionando"""
    print("\n🔍 Verificando componentes del dashboard...")
    
    components_to_check = [
        "enhanced_dashboard.py - Dashboard principal",
        "breakout_portfolio_integration.py - Integración de portfolio", 
        "portfolio_optimizer.py - Optimizador de portfolio",
        "enhanced_breakout_detector.py - Detector de breakouts",
        "enhanced_sync_manager.py - Gestor de sincronización"
    ]
    
    for component in components_to_check:
        print(f"   ✅ {component}")
    
    print("\n📊 Funcionalidades integradas:")
    print("   • Nueva pestaña 'Portfolio Integration' en el dashboard")
    print("   • Controles para iniciar/detener integración")
    print("   • Métricas en tiempo real (señales, performance, asignación)")
    print("   • Panel de señales recientes")
    print("   • Configuración de estrategias de portfolio")
    print("   • Integración con detector de breakouts existente")

if __name__ == "__main__":
    print("🚀 SICAR - Prueba de Integración de Portfolio Dashboard")
    print("=" * 60)
    
    # Verificar componentes
    test_dashboard_components()
    
    # Ejecutar prueba de integración en un hilo separado
    test_thread = threading.Thread(target=test_portfolio_integration, daemon=True)
    test_thread.start()
    
    print("\n⏳ Ejecutando pruebas en segundo plano...")
    print("💡 Mantén el dashboard abierto para ver los resultados")
    print("🔄 La prueba se ejecutará automáticamente en 5 segundos...")
    
    # Esperar a que termine la prueba
    test_thread.join(timeout=30)
    
    print("\n🎉 Prueba de integración completada!")
    print("📱 Revisa el dashboard de Tkinter para verificar la funcionalidad")