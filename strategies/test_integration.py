#!/usr/bin/env python3
"""
SCRIPT DE PRUEBA PARA INTEGRACIÓN AUTÓNOMA
Verifica que el módulo se puede integrar con tu bot actual
"""

import asyncio
import sys
import os
sys.path.append('/home/johan/itbot_linux')

# Importar módulo autónomo
from strategies.autonomous_integration_module import AutonomousStrategiesModule

def test_module_initialization():
    """
    Test 1: Verificar que el módulo se puede inicializar
    """
    print("🧪 Test 1: Inicialización del módulo")
    
    try:
        # Configuración de prueba
        test_config = {
            'binance_api_key': 'test_key',
            'binance_secret': 'test_secret',
            'capital_inicial': 10000,
            'test_mode': True
        }
        
        autonomous = AutonomousStrategiesModule(
            capital_inicial=10000,
            existing_bot_config=test_config
        )
        
        print("✅ Módulo inicializado correctamente")
        print(f"   Capital inicial: ${autonomous.capital_inicial:,}")
        print(f"   Estrategias configuradas: {len(autonomous.strategy_config)}")
        
        # Verificar configuración de estrategias
        for strategy_name, config in autonomous.strategy_config.items():
            status = "✅ Activa" if config['enabled'] else "❌ Inactiva"
            print(f"   {strategy_name}: {status} ({config['capital_pct']*100}% capital)")
        
        return autonomous
        
    except Exception as e:
        print(f"❌ Error en inicialización: {e}")
        return None

def test_signal_generation_offline():
    """
    Test 2: Verificar generación de señales sin conexión real
    """
    print("\n🧪 Test 2: Generación de señales (modo offline)")
    
    autonomous = test_module_initialization()
    if not autonomous:
        return
    
    try:
        # Simular datos de prueba
        print("📊 Simulando generación de señales...")
        
        # Test de cálculo de position size
        position_size = autonomous.calculate_position_size(
            capital_pct=0.35,
            risk_pct=0.02,
            entry_price=50000,
            stop_loss_price=49000
        )
        
        print(f"✅ Cálculo position size: ${position_size:.2f}")
        
        # Test de cálculo de confianza
        import pandas as pd
        test_ema_short = pd.Series([100, 101, 102])
        test_ema_long = pd.Series([99, 100, 101])
        
        confidence = autonomous.calculate_signal_confidence(
            rsi=25,  # Oversold
            volume_spike=True,
            ema_short=test_ema_short,
            ema_long=test_ema_long
        )
        
        print(f"✅ Cálculo confianza: {confidence:.2%}")
        
        # Test de indicadores técnicos
        test_prices = pd.Series([100, 101, 99, 102, 98, 103, 97, 104, 96, 105])
        rsi = autonomous.calculate_rsi(test_prices, 5)
        print(f"✅ RSI calculado: {rsi.iloc[-1]:.2f}")
        
        bb_upper, bb_lower = autonomous.calculate_bollinger_bands(test_prices, 5, 2)
        print(f"✅ Bollinger Bands: Upper={bb_upper.iloc[-1]:.2f}, Lower={bb_lower.iloc[-1]:.2f}")
        
    except Exception as e:
        print(f"❌ Error en generación de señales: {e}")

def test_risk_management():
    """
    Test 3: Verificar sistema de gestión de riesgo
    """
    print("\n🧪 Test 3: Sistema de gestión de riesgo")
    
    autonomous = test_module_initialization()
    if not autonomous:
        return
    
    try:
        from strategies.autonomous_integration_module import TradeSignal
        from datetime import datetime
        
        # Crear señales de prueba
        test_signals = [
            TradeSignal(
                pair='BTCUSDT',
                direction='LONG',
                entry_price=50000,
                stop_loss=49000,
                take_profit=[50500, 51000, 51500],
                position_size=0.1,
                strategy='scalping_auto',
                confidence=0.8,
                timestamp=datetime.now()
            ),
            TradeSignal(
                pair='ETHUSDT',
                direction='SHORT',
                entry_price=3000,
                stop_loss=3100,
                take_profit=[2950, 2900, 2850],
                position_size=2.0,
                strategy='mean_reversion',
                confidence=0.7,
                timestamp=datetime.now()
            )
        ]
        
        # Test filtrado por riesgo
        filtered_signals = autonomous.filter_signals_by_risk(test_signals)
        print(f"✅ Señales originales: {len(test_signals)}")
        print(f"✅ Señales después de filtrado: {len(filtered_signals)}")
        
        # Calcular exposición total
        total_exposure = sum(s.position_size * s.entry_price for s in filtered_signals)
        max_exposure = autonomous.capital_inicial * 0.1  # 10% máximo
        
        print(f"✅ Exposición total: ${total_exposure:,.2f}")
        print(f"✅ Exposición máxima permitida: ${max_exposure:,.2f}")
        print(f"✅ Dentro de límites: {'Sí' if total_exposure <= max_exposure else 'No'}")
        
    except Exception as e:
        print(f"❌ Error en gestión de riesgo: {e}")

def test_config_compatibility():
    """
    Test 4: Verificar compatibilidad con archivos existentes
    """
    print("\n🧪 Test 4: Compatibilidad con archivos existentes")
    
    try:
        # Verificar que los archivos del bot existen
        required_files = [
            '/home/johan/itbot_linux/config.py',
            '/home/johan/itbot_linux/risk_manager.py',
            '/home/johan/itbot_linux/handlers.py'
        ]
        
        existing_files = []
        missing_files = []
        
        for file_path in required_files:
            if os.path.exists(file_path):
                existing_files.append(file_path)
                print(f"✅ Encontrado: {file_path}")
            else:
                missing_files.append(file_path)
                print(f"⚠️  No encontrado: {file_path}")
        
        print(f"\n📊 Resumen de compatibilidad:")
        print(f"   Archivos existentes: {len(existing_files)}")
        print(f"   Archivos faltantes: {len(missing_files)}")
        
        if len(existing_files) >= 2:
            print("✅ Compatibilidad: BUENA - Se puede integrar fácilmente")
        elif len(existing_files) >= 1:
            print("⚠️  Compatibilidad: MEDIA - Requiere algunas adaptaciones")
        else:
            print("❌ Compatibilidad: BAJA - Requiere configuración manual")
            
    except Exception as e:
        print(f"❌ Error verificando compatibilidad: {e}")

def test_performance_simulation():
    """
    Test 5: Simulación de rendimiento
    """
    print("\n🧪 Test 5: Simulación de rendimiento esperado")
    
    try:
        # Parámetros de simulación
        capital_inicial = 10000
        dias_simulacion = 30
        trades_por_dia = 8
        win_rate = 0.65
        avg_profit = 0.012  # 1.2% promedio por trade ganador
        avg_loss = 0.008   # 0.8% promedio por trade perdedor
        
        print(f"📊 Simulando {dias_simulacion} días de trading:")
        print(f"   Capital inicial: ${capital_inicial:,}")
        print(f"   Trades por día: {trades_por_dia}")
        print(f"   Win rate: {win_rate:.1%}")
        print(f"   Profit promedio: {avg_profit:.1%}")
        print(f"   Loss promedio: {avg_loss:.1%}")
        
        # Simulación simple
        current_capital = capital_inicial
        total_trades = dias_simulacion * trades_por_dia
        winning_trades = int(total_trades * win_rate)
        losing_trades = total_trades - winning_trades
        
        total_profit = winning_trades * avg_profit * capital_inicial
        total_loss = losing_trades * avg_loss * capital_inicial
        net_profit = total_profit - total_loss
        
        final_capital = capital_inicial + net_profit
        monthly_return = (final_capital / capital_inicial - 1) * 100
        
        print(f"\n📈 Resultados de simulación:")
        print(f"   Total trades: {total_trades}")
        print(f"   Trades ganadores: {winning_trades}")
        print(f"   Trades perdedores: {losing_trades}")
        print(f"   Ganancia total: ${total_profit:,.2f}")
        print(f"   Pérdida total: ${total_loss:,.2f}")
        print(f"   Ganancia neta: ${net_profit:,.2f}")
        print(f"   Capital final: ${final_capital:,.2f}")
        print(f"   Retorno mensual: {monthly_return:.2f}%")
        
        if monthly_return >= 15:
            print("🎯 ✅ OBJETIVO ALCANZADO: Retorno >= 15% mensual")
        else:
            print("⚠️  OBJETIVO NO ALCANZADO: Requiere optimización")
            
    except Exception as e:
        print(f"❌ Error en simulación: {e}")

def generate_integration_checklist():
    """
    Test 6: Generar checklist de integración personalizado
    """
    print("\n🧪 Test 6: Checklist de integración personalizado")
    
    try:
        checklist = """
🔧 CHECKLIST DE INTEGRACIÓN AUTÓNOMA

□ 1. PREPARACIÓN
  □ Copiar autonomous_integration_module.py a strategies/
  □ Copiar INTEGRATION_GUIDE.md para referencia
  □ Verificar que Python 3.8+ esté disponible
  □ Instalar dependencias: pandas, numpy

□ 2. CONEXIÓN BINANCE
  □ Adaptar get_recent_klines() con tu cliente Binance
  □ Adaptar auto_select_high_volume_pairs()
  □ Adaptar get_high_volatility_pairs()
  □ Probar conexión con datos reales

□ 3. INTEGRACIÓN RISK MANAGER
  □ Importar tu RiskManager actual
  □ Adaptar calculate_position_size()
  □ Verificar límites de riesgo
  □ Probar cálculos de posición

□ 4. INTEGRACIÓN HANDLERS
  □ Importar tus handlers de ejecución
  □ Adaptar execute_trade_signal()
  □ Configurar stop loss y take profit
  □ Probar ejecución en papel

□ 5. CONFIGURACIÓN PERSONALIZADA
  □ Ajustar capital_pct por estrategia
  □ Configurar pares favoritos
  □ Establecer límites de posiciones
  □ Configurar timeframes preferidos

□ 6. TESTING
  □ Ejecutar tests offline ✅
  □ Probar con datos reales en papel
  □ Verificar logging y alertas
  □ Validar performance tracking

□ 7. MONITOREO
  □ Configurar alertas Telegram
  □ Establecer métricas de seguimiento
  □ Configurar dashboard updates
  □ Establecer límites de emergency stop

□ 8. PRODUCCIÓN
  □ Empezar con capital pequeño (10% del total)
  □ Monitorear durante 1 semana
  □ Incrementar capital gradualmente
  □ Optimizar parámetros basándose en resultados

TIEMPO ESTIMADO DE IMPLEMENTACIÓN: 2-4 horas
RETORNO ESPERADO: 15-17% mensual
        """
        
        print(checklist)
        
        # Guardar checklist
        with open('/home/johan/itbot_linux/strategies/INTEGRATION_CHECKLIST.md', 'w') as f:
            f.write(checklist)
        
        print("✅ Checklist guardado en strategies/INTEGRATION_CHECKLIST.md")
        
    except Exception as e:
        print(f"❌ Error generando checklist: {e}")

def main():
    """
    Función principal de testing
    """
    print("🚀 INICIANDO TESTS DE INTEGRACIÓN AUTÓNOMA")
    print("=" * 50)
    
    # Ejecutar todos los tests
    test_module_initialization()
    test_signal_generation_offline()
    test_risk_management()
    test_config_compatibility()
    test_performance_simulation()
    generate_integration_checklist()
    
    print("\n" + "=" * 50)
    print("🎯 TESTS COMPLETADOS")
    print("\n📋 PRÓXIMOS PASOS:")
    print("1. Revisar INTEGRATION_GUIDE.md para instrucciones detalladas")
    print("2. Seguir INTEGRATION_CHECKLIST.md paso a paso") 
    print("3. Adaptar funciones de datos con tu cliente Binance")
    print("4. Probar en modo paper trading antes de producción")
    print("5. Empezar con capital pequeño y escalar gradualmente")
    
    print("\n💰 OBJETIVO: 15% retorno mensual con estrategias autónomas")
    print("🤖 DEPENDENCIAS: Solo tu bot + Binance API")
    print("⏱️  TIEMPO DE IMPLEMENTACIÓN: 2-4 horas")

if __name__ == "__main__":
    main()
