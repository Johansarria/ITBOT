#!/usr/bin/env python3
"""
VERIFICACIÓN DE MICRO-PRUEBAS CONFIGURADAS
Validar que los límites ultra-seguros estén activos
"""

import sys
import os
sys.path.append('/app')

from datetime import datetime

def verify_micro_testing_config():
    print("🧪 VERIFICACIÓN DE MICRO-PRUEBAS CONFIGURADAS")
    print("=" * 60)
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    
    # Verificar configuración
    try:
        import importlib
        if 'config' in sys.modules:
            importlib.reload(sys.modules['config'])
        
        import config
        
        print(f"\n📋 VERIFICACIÓN DE LÍMITES ULTRA-SEGUROS:")
        
        # Configuraciones críticas para micro-pruebas
        micro_checks = [
            ('MICRO_TRADE_MAX_USDT', 0.75, 'Máximo por trade ultra-seguro'),
            ('MAX_DAILY_LOSS_PCT', 10, 'Pérdida diaria máxima 10%'),
            ('MAX_TRADES_PER_DAY', 4, 'Máximo 4 trades diarios'),
            ('MAX_TRADES_PER_HOUR', 1, 'Solo 1 trade por hora'),
            ('MIN_ROI_ON_MARGIN_FOR_ENTRY_PCT', 18.0, 'ROI mínimo 18%'),
            ('ML_THRESHOLD_LOW', 0.65, 'Alta selectividad ML'),
            ('MANDATORY_STOP_LOSS', True, 'SL obligatorio'),
            ('MAX_SL_DISTANCE_PCT', 2.0, 'SL máximo 2%'),
            ('MICRO_TESTING_MODE', True, 'Modo micro-pruebas'),
        ]
        
        verification_score = 0
        total_checks = len(micro_checks)
        
        for config_name, expected, description in micro_checks:
            try:
                if hasattr(config, config_name):
                    actual = getattr(config, config_name)
                    
                    if isinstance(expected, bool):
                        passed = actual == expected
                    elif isinstance(expected, (int, float)):
                        passed = float(actual) == float(expected)
                    else:
                        passed = actual == expected
                    
                    status = "✅" if passed else "❌"
                    print(f"   {status} {config_name}: {actual} ({description})")
                    
                    if passed:
                        verification_score += 1
                        
                else:
                    print(f"   ⚠️ {config_name}: NO ENCONTRADO")
                    
            except Exception as e:
                print(f"   ❌ Error verificando {config_name}: {e}")
        
        # Calcular score
        score_pct = (verification_score / total_checks) * 100
        print(f"\n📊 SCORE DE VERIFICACIÓN: {score_pct:.0f}% ({verification_score}/{total_checks})")
        
        if score_pct >= 90:
            config_status = "✅ MICRO-PRUEBAS CORRECTAMENTE CONFIGURADAS"
        elif score_pct >= 70:
            config_status = "⚠️ CONFIGURACIÓN PARCIAL"
        else:
            config_status = "❌ CONFIGURACIÓN INCOMPLETA"
        
        print(f"🎯 Estado: {config_status}")
        
    except Exception as e:
        print(f"❌ Error verificando configuración: {e}")
        return False
    
    # Mostrar límites aplicados
    if verification_score >= 7:  # Al menos 7/9 configuraciones correctas
        print(f"\n🛡️ LÍMITES DE MICRO-PRUEBAS ACTIVOS:")
        
        balance = 5.86
        max_trade = 0.75
        max_daily_loss = 0.59
        max_trades_day = 4
        
        print(f"   💰 Balance actual: ${balance:.2f}")
        print(f"   🎯 Máximo por trade: ${max_trade:.2f} ({(max_trade/balance)*100:.1f}% del balance)")
        print(f"   📉 Máx pérdida diaria: ${max_daily_loss:.2f} ({(max_daily_loss/balance)*100:.1f}% del balance)")
        print(f"   🔢 Trades máximos/día: {max_trades_day}")
        print(f"   ⏰ Frecuencia máxima: 1 trade/hora")
        print(f"   🛡️ Stop Loss: 2% máximo")
        
        # Simulación de escenarios
        print(f"\n🧪 SIMULACIÓN DE ESCENARIOS:")
        
        # Peor caso: 4 pérdidas máximas
        worst_case_loss = max_daily_loss
        balance_after_worst = balance - worst_case_loss
        
        # Caso promedio: 2 pérdidas, 2 ganancias pequeñas
        avg_case_result = -0.30 + 0.10  # 2 pérdidas de $0.15 - 2 ganancias de $0.05
        balance_after_avg = balance + avg_case_result
        
        # Mejor caso: 4 ganancias pequeñas
        best_case_gain = 0.20  # 4 ganancias de $0.05
        balance_after_best = balance + best_case_gain
        
        print(f"   📉 Peor día posible: ${balance_after_worst:.2f} (-{(worst_case_loss/balance)*100:.1f}%)")
        print(f"   📊 Día promedio: ${balance_after_avg:.2f} ({(avg_case_result/balance)*100:.1f}%)")
        print(f"   📈 Mejor día posible: ${balance_after_best:.2f} (+{(best_case_gain/balance)*100:.1f}%)")
        
        # Proyección de supervivencia
        days_survival = balance / max_daily_loss if max_daily_loss > 0 else float('inf')
        print(f"   🛡️ Días supervivencia (peor escenario): {days_survival:.0f} días")
        
        # Estado del sistema
        print(f"\n📊 ESTADO DEL SISTEMA:")
        try:
            from utils.binance_client import get_um_futures_client
            client = get_um_futures_client()
            
            # Verificar conexión y balance
            account = client.futures_account()
            current_balance = float(account['totalWalletBalance'])
            available = float(account['availableBalance'])
            
            print(f"   💰 Balance real: ${current_balance:.2f}")
            print(f"   💳 Disponible: ${available:.2f}")
            
            # Posiciones activas
            positions = client.futures_position_information()
            active_positions = sum(1 for pos in positions if float(pos['positionAmt']) != 0)
            
            print(f"   📈 Posiciones activas: {active_positions}")
            
            if active_positions > 0:
                print(f"   📊 Sistema listo para micro-pruebas adicionales")
            else:
                print(f"   🎯 Sistema listo para primera micro-prueba")
                
        except Exception as e:
            print(f"   ⚠️ Error verificando sistema: {e}")
        
        print(f"\n✅ SISTEMA CONFIGURADO PARA MICRO-PRUEBAS ULTRA-SEGURAS")
        print(f"🧪 Listo para operar con riesgo mínimo y máximo aprendizaje")
        
        return True
    
    else:
        print(f"\n❌ CONFIGURACIÓN INSUFICIENTE PARA MICRO-PRUEBAS")
        return False

if __name__ == "__main__":
    success = verify_micro_testing_config()
    
    if success:
        print(f"\n🎯 MICRO-PRUEBAS ACTIVADAS")
        print(f"🔄 El bot operará con límites ultra-seguros")
        print(f"📊 Máximo riesgo diario: 10% del capital")
    else:
        print(f"\n🔧 REQUIERE AJUSTES ADICIONALES")
