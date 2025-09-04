#!/usr/bin/env python3
"""
MONITOREO CONTINUO DE MICRO-PRUEBAS
Sistema de supervisión constante para micro-pruebas ultra-seguras
"""

import sys
import os
sys.path.append('/app')

from utils.binance_client import get_um_futures_client
from datetime import datetime, timedelta
import time
import json

class MicroTestingMonitor:
    def __init__(self):
        self.client = get_um_futures_client()
        self.start_time = datetime.now()
        
        # Límites de micro-pruebas
        self.MAX_TRADE_SIZE = 0.75
        self.MAX_DAILY_LOSS = 0.59
        self.MAX_TRADES_PER_DAY = 4
        self.MAX_TRADES_PER_HOUR = 1
        self.MAX_SL_DISTANCE = 2.0
        
        # Tracking de actividad
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.last_trade_time = None
        self.alerts_sent = []
        
        print("🧪 MONITOREO DE MICRO-PRUEBAS INICIADO")
        print("=" * 60)
        print(f"⏰ Inicio: {self.start_time.strftime('%H:%M:%S')}")
        print(f"🎯 Modo: Ultra-seguro (10% pérdida diaria máx)")
    
    def get_current_status(self):
        """Obtener estado completo actual"""
        try:
            # Balance
            account = self.client.futures_account()
            total_balance = float(account['totalWalletBalance'])
            available_balance = float(account['availableBalance'])
            
            # Posiciones activas
            positions = self.client.futures_position_information()
            active_positions = []
            total_unrealized_pnl = 0
            
            for pos in positions:
                if float(pos['positionAmt']) != 0:
                    symbol = pos['symbol']
                    size = float(pos['positionAmt'])
                    entry_price = float(pos['entryPrice'])
                    notional = abs(float(pos['notional']))
                    
                    # Precio actual
                    ticker = self.client.futures_symbol_ticker(symbol=symbol)
                    current_price = float(ticker['price'])
                    
                    # PnL
                    unrealized_pnl = (current_price - entry_price) * size
                    total_unrealized_pnl += unrealized_pnl
                    
                    active_positions.append({
                        'symbol': symbol,
                        'size': size,
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'notional': notional,
                        'unrealized_pnl': unrealized_pnl,
                        'pnl_pct': ((current_price - entry_price) / entry_price) * 100
                    })
            
            # Órdenes activas
            orders = self.client.futures_get_open_orders()
            sl_orders = {}
            tp_orders = {}
            
            for order in orders:
                symbol = order['symbol']
                if order['type'] == 'STOP_MARKET':
                    sl_orders[symbol] = float(order['stopPrice'])
                elif order['type'] == 'TAKE_PROFIT_MARKET':
                    tp_orders[symbol] = float(order['stopPrice'])
            
            return {
                'timestamp': datetime.now(),
                'balance': {
                    'total': total_balance,
                    'available': available_balance
                },
                'positions': active_positions,
                'sl_orders': sl_orders,
                'tp_orders': tp_orders,
                'total_unrealized_pnl': total_unrealized_pnl
            }
            
        except Exception as e:
            print(f"❌ Error obteniendo estado: {e}")
            return None
    
    def analyze_micro_testing_compliance(self, status):
        """Analizar cumplimiento de reglas de micro-pruebas"""
        compliance_issues = []
        warnings = []
        
        # 1. Verificar tamaños de posición
        for pos in status['positions']:
            if pos['notional'] > self.MAX_TRADE_SIZE:
                compliance_issues.append({
                    'type': 'POSICION_GRANDE',
                    'symbol': pos['symbol'],
                    'message': f"Posición {pos['symbol']} (${pos['notional']:.2f}) > límite (${self.MAX_TRADE_SIZE:.2f})",
                    'severity': 'CRITICO'
                })
        
        # 2. Verificar distancia de Stop Loss
        for symbol, sl_price in status['sl_orders'].items():
            pos_data = next((p for p in status['positions'] if p['symbol'] == symbol), None)
            if pos_data:
                current_price = pos_data['current_price']
                sl_distance_pct = abs((current_price - sl_price) / current_price) * 100
                
                if sl_distance_pct > self.MAX_SL_DISTANCE:
                    warnings.append({
                        'type': 'SL_LEJANO',
                        'symbol': symbol,
                        'message': f"SL {symbol} a {sl_distance_pct:.1f}% > límite {self.MAX_SL_DISTANCE}%",
                        'severity': 'ADVERTENCIA'
                    })
        
        # 3. Verificar balance disponible
        available_pct = (status['balance']['available'] / status['balance']['total']) * 100
        if available_pct < 20:
            warnings.append({
                'type': 'BALANCE_BAJO',
                'message': f"Balance disponible bajo: {available_pct:.1f}%",
                'severity': 'ADVERTENCIA'
            })
        
        # 4. Verificar PnL diario acumulado (simulado por ahora)
        daily_loss_pct = abs(status['total_unrealized_pnl'] / status['balance']['total']) * 100
        if daily_loss_pct > 8:  # 8% como advertencia antes del 10%
            warnings.append({
                'type': 'PERDIDA_DIARIA_ALTA',
                'message': f"Pérdida no realizada: {daily_loss_pct:.1f}% del balance",
                'severity': 'ADVERTENCIA'
            })
        
        return compliance_issues, warnings
    
    def calculate_micro_testing_metrics(self, status):
        """Calcular métricas específicas de micro-pruebas"""
        total_balance = status['balance']['total']
        
        # Exposición actual
        total_exposure = sum(pos['notional'] for pos in status['positions'])
        exposure_pct = (total_exposure / total_balance) * 100 if total_balance > 0 else 0
        
        # Utilización del límite diario
        daily_utilization = abs(status['total_unrealized_pnl'] / self.MAX_DAILY_LOSS) * 100 if self.MAX_DAILY_LOSS > 0 else 0
        
        # Margen de seguridad restante
        remaining_daily_limit = max(0, self.MAX_DAILY_LOSS + status['total_unrealized_pnl'])
        
        # Posiciones restantes permitidas (basado en tamaño)
        remaining_positions = max(0, 3 - len(status['positions']))  # Max 3 concurrent
        
        return {
            'total_exposure': total_exposure,
            'exposure_pct': exposure_pct,
            'daily_utilization': daily_utilization,
            'remaining_daily_limit': remaining_daily_limit,
            'remaining_positions': remaining_positions,
            'safety_margin': (status['balance']['available'] / total_balance) * 100 if total_balance > 0 else 0
        }
    
    def print_micro_testing_report(self, status, compliance_issues, warnings, metrics):
        """Imprimir reporte de micro-pruebas"""
        timestamp = status['timestamp'].strftime('%H:%M:%S')
        runtime = status['timestamp'] - self.start_time
        
        print(f"\n🧪 MICRO-PRUEBAS - REPORTE {timestamp}")
        print("=" * 60)
        print(f"⏰ Runtime: {runtime}")
        
        # Balance y estado
        total = status['balance']['total']
        available = status['balance']['available']
        pnl = status['total_unrealized_pnl']
        
        print(f"\n💰 ESTADO FINANCIERO:")
        print(f"   Balance Total: ${total:.2f}")
        print(f"   Disponible: ${available:.2f} ({metrics['safety_margin']:.1f}%)")
        print(f"   PnL No Realizado: ${pnl:+.2f}")
        
        # Límites de micro-pruebas
        print(f"\n🧪 LÍMITES DE MICRO-PRUEBAS:")
        print(f"   📊 Exposición actual: ${metrics['total_exposure']:.2f} ({metrics['exposure_pct']:.1f}%)")
        print(f"   📉 Uso límite diario: {metrics['daily_utilization']:.1f}%")
        print(f"   💰 Margen restante hoy: ${metrics['remaining_daily_limit']:.2f}")
        print(f"   📈 Posiciones restantes: {metrics['remaining_positions']}")
        
        # Posiciones activas
        if status['positions']:
            print(f"\n📊 POSICIONES ACTIVAS ({len(status['positions'])}):")
            for pos in status['positions']:
                symbol = pos['symbol']
                size = pos['size']
                entry = pos['entry_price']
                current = pos['current_price']
                pnl_pct = pos['pnl_pct']
                pnl_usd = pos['unrealized_pnl']
                notional = pos['notional']
                
                # Verificar si cumple límites
                size_ok = "✅" if notional <= self.MAX_TRADE_SIZE else "🚨"
                
                print(f"   {size_ok} {symbol}: {size} @ ${entry:.2f} → ${current:.2f}")
                print(f"      PnL: {pnl_pct:+.2f}% (${pnl_usd:+.2f}) | Size: ${notional:.2f}")
                
                # Estado de protección
                sl_price = status['sl_orders'].get(symbol, 'N/A')
                tp_price = status['tp_orders'].get(symbol, 'N/A')
                print(f"      SL: ${sl_price} | TP: ${tp_price}")
        else:
            print(f"\n📊 Sin posiciones activas - Listo para micro-pruebas")
        
        # Cumplimiento de reglas
        if compliance_issues:
            print(f"\n🚨 VIOLACIONES DE LÍMITES:")
            for issue in compliance_issues:
                print(f"   🚨 {issue['message']}")
        
        if warnings:
            print(f"\n⚠️ ADVERTENCIAS:")
            for warning in warnings:
                print(f"   ⚠️ {warning['message']}")
        
        if not compliance_issues and not warnings:
            print(f"\n✅ TODAS LAS REGLAS DE MICRO-PRUEBAS CUMPLIDAS")
        
        # Recomendaciones
        print(f"\n💡 ESTADO ACTUAL:")
        if metrics['remaining_daily_limit'] > 0.20:
            if len(status['positions']) == 0:
                print(f"   🎯 Listo para nueva micro-prueba")
            else:
                print(f"   📊 Posiciones bajo monitoreo")
        else:
            print(f"   ⏸️ Límite diario casi alcanzado - Pausa recomendada")
        
        print(f"   🔄 Próxima revisión en 2 minutos...")
    
    def run_continuous_micro_testing_monitor(self):
        """Ejecutar monitoreo continuo de micro-pruebas"""
        cycle_count = 0
        
        try:
            while True:
                cycle_count += 1
                
                print(f"\n" + "="*60)
                print(f"🔄 CICLO {cycle_count} - MONITOREO MICRO-PRUEBAS")
                
                # Obtener estado
                status = self.get_current_status()
                if not status:
                    print("❌ Error obteniendo datos - Reintentando en 30 segundos...")
                    time.sleep(30)
                    continue
                
                # Analizar cumplimiento
                compliance_issues, warnings = self.analyze_micro_testing_compliance(status)
                
                # Calcular métricas
                metrics = self.calculate_micro_testing_metrics(status)
                
                # Mostrar reporte
                self.print_micro_testing_report(status, compliance_issues, warnings, metrics)
                
                # Verificar si hay violaciones críticas
                if compliance_issues:
                    print(f"\n🚨 VIOLACIONES CRÍTICAS DETECTADAS")
                    print(f"🔧 Revisar configuración o posiciones manualmente")
                    time.sleep(60)  # Revisión más frecuente si hay problemas
                elif warnings:
                    print(f"\n⚠️ Advertencias detectadas - Monitoreo cada minuto")
                    time.sleep(60)
                else:
                    # Monitoreo normal cada 2 minutos
                    time.sleep(120)
                
        except KeyboardInterrupt:
            runtime = datetime.now() - self.start_time
            print(f"\n\n⏹️ MONITOREO DE MICRO-PRUEBAS DETENIDO")
            print(f"⏰ Runtime total: {runtime}")
            print(f"🔄 Ciclos completados: {cycle_count}")
            print(f"🧪 Sesión de micro-pruebas finalizada")
        
        except Exception as e:
            print(f"\n❌ Error en monitoreo: {e}")

if __name__ == "__main__":
    monitor = MicroTestingMonitor()
    monitor.run_continuous_micro_testing_monitor()
