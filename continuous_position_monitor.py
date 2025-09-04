#!/usr/bin/env python3
"""
MONITOREO CONTINUO DE POSICIONES
Sistema de supervisión cada 5 minutos para protección de capital
"""

import sys
import os
sys.path.append('/app')

from utils.binance_client import get_um_futures_client
from datetime import datetime, timedelta
import time
import json

class PositionMonitor:
    def __init__(self):
        self.client = get_um_futures_client()
        self.alerts_sent = set()
        self.last_prices = {}
        self.monitoring_start = datetime.now()
        
        # Umbrales críticos
        self.CRITICAL_SL_BUFFER = 1.0  # 1% del SL = crítico
        self.WARNING_SL_BUFFER = 2.0   # 2% del SL = advertencia
        self.BALANCE_WARNING = 0.5     # $0.5 balance = advertencia
        self.BALANCE_CRITICAL = 0.2    # $0.2 balance = crítico
    
    def get_current_status(self):
        """Obtener estado actual completo"""
        try:
            # Balance
            account = self.client.futures_account()
            total_balance = float(account['totalWalletBalance'])
            available_balance = float(account['availableBalance'])
            
            # Posiciones
            positions = self.client.futures_position_information()
            active_positions = []
            
            for pos in positions:
                if float(pos['positionAmt']) != 0:
                    active_positions.append({
                        'symbol': pos['symbol'],
                        'size': float(pos['positionAmt']),
                        'entry_price': float(pos['entryPrice']),
                        'notional': float(pos['notional'])
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
            
            # Precios actuales
            current_prices = {}
            for pos in active_positions:
                symbol = pos['symbol']
                ticker = self.client.futures_symbol_ticker(symbol=symbol)
                current_prices[symbol] = float(ticker['price'])
            
            return {
                'timestamp': datetime.now(),
                'balance': {
                    'total': total_balance,
                    'available': available_balance
                },
                'positions': active_positions,
                'sl_orders': sl_orders,
                'tp_orders': tp_orders,
                'current_prices': current_prices
            }
            
        except Exception as e:
            print(f"❌ Error obteniendo estado: {e}")
            return None
    
    def analyze_risks(self, status):
        """Analizar riesgos actuales"""
        risks = []
        
        # Análisis de balance
        available = status['balance']['available']
        if available <= self.BALANCE_CRITICAL:
            risks.append({
                'level': 'CRÍTICO',
                'type': 'BALANCE',
                'message': f'Balance disponible crítico: ${available:.2f}',
                'action': 'Considerar cierre inmediato de posición perdedora'
            })
        elif available <= self.BALANCE_WARNING:
            risks.append({
                'level': 'ADVERTENCIA',
                'type': 'BALANCE', 
                'message': f'Balance disponible bajo: ${available:.2f}',
                'action': 'Preparar para posible cierre de posiciones'
            })
        
        # Análisis de distancia a Stop Loss
        for pos in status['positions']:
            symbol = pos['symbol']
            current_price = status['current_prices'][symbol]
            
            if symbol in status['sl_orders']:
                sl_price = status['sl_orders'][symbol]
                
                # Para posición LONG
                if pos['size'] > 0:
                    distance_pct = ((current_price - sl_price) / current_price) * 100
                    
                    if distance_pct <= self.CRITICAL_SL_BUFFER:
                        risks.append({
                            'level': 'CRÍTICO',
                            'type': 'STOP_LOSS',
                            'message': f'{symbol} MUY CERCA del SL: {distance_pct:.1f}%',
                            'action': f'Monitoreo cada minuto - Precio: ${current_price:.2f} | SL: ${sl_price:.2f}'
                        })
                    elif distance_pct <= self.WARNING_SL_BUFFER:
                        risks.append({
                            'level': 'ADVERTENCIA', 
                            'type': 'STOP_LOSS',
                            'message': f'{symbol} cerca del SL: {distance_pct:.1f}%',
                            'action': f'Supervisión activa - Precio: ${current_price:.2f} | SL: ${sl_price:.2f}'
                        })
        
        return risks
    
    def check_opportunities(self, status):
        """Verificar oportunidades de mejora"""
        opportunities = []
        
        for pos in status['positions']:
            symbol = pos['symbol']
            entry_price = pos['entry_price']
            current_price = status['current_prices'][symbol]
            
            # Para posición LONG
            if pos['size'] > 0:
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
                
                # Oportunidad de mover SL a break-even
                if pnl_pct >= 1.0:  # 1% de ganancia
                    opportunities.append({
                        'type': 'BREAK_EVEN',
                        'symbol': symbol,
                        'message': f'{symbol} en +{pnl_pct:.1f}% - Oportunidad de mover SL a break-even',
                        'action': f'Mover SL de ${status["sl_orders"].get(symbol, "N/A")} → ${entry_price:.2f}'
                    })
                
                # Oportunidad de trailing stop
                elif pnl_pct >= 2.0:  # 2% de ganancia
                    opportunities.append({
                        'type': 'TRAILING',
                        'symbol': symbol,
                        'message': f'{symbol} en +{pnl_pct:.1f}% - Considerar trailing stop',
                        'action': f'SL trailing a ${current_price * 0.995:.2f} (0.5% trailing)'
                    })
        
        return opportunities
    
    def print_status_report(self, status, risks, opportunities):
        """Imprimir reporte de estado"""
        timestamp = status['timestamp'].strftime('%H:%M:%S')
        
        print(f"\n🔍 MONITOREO CONTINUO - {timestamp}")
        print("=" * 60)
        
        # Balance
        total = status['balance']['total']
        available = status['balance']['available']
        print(f"💰 Balance: ${total:.2f} total | ${available:.2f} disponible")
        
        # Posiciones
        print(f"\n📊 POSICIONES ACTIVAS:")
        for pos in status['positions']:
            symbol = pos['symbol']
            size = pos['size']
            entry = pos['entry_price']
            current = status['current_prices'][symbol]
            notional = abs(pos['notional'])
            
            pnl_pct = ((current - entry) / entry) * 100
            pnl_usd = (current - entry) * size
            
            sl_price = status['sl_orders'].get(symbol, 'N/A')
            tp_price = status['tp_orders'].get(symbol, 'N/A')
            
            print(f"   📈 {symbol}: {size} @ ${entry:.2f}")
            print(f"      Current: ${current:.2f} | PnL: {pnl_pct:+.1f}% (${pnl_usd:+.2f})")
            print(f"      SL: ${sl_price} | TP: ${tp_price}")
            print(f"      Notional: ${notional:.2f}")
        
        # Riesgos
        if risks:
            print(f"\n🚨 RIESGOS DETECTADOS:")
            for risk in risks:
                emoji = "🚨" if risk['level'] == 'CRÍTICO' else "⚠️"
                print(f"   {emoji} [{risk['level']}] {risk['message']}")
                print(f"      💡 Acción: {risk['action']}")
        else:
            print(f"\n✅ Sin riesgos críticos detectados")
        
        # Oportunidades
        if opportunities:
            print(f"\n🎯 OPORTUNIDADES:")
            for opp in opportunities:
                print(f"   💡 {opp['message']}")
                print(f"      🎯 Acción sugerida: {opp['action']}")
        
        print(f"\n⏰ Próxima revisión en 5 minutos...")
    
    def run_continuous_monitoring(self):
        """Ejecutar monitoreo continuo"""
        print("🎯 INICIANDO MONITOREO CONTINUO DE POSICIONES")
        print("=" * 60)
        print(f"🕐 Intervalo: 5 minutos")
        print(f"🎯 Inicio: {self.monitoring_start.strftime('%H:%M:%S')}")
        print(f"🛡️ Protección de capital activada")
        
        cycle_count = 0
        
        try:
            while True:
                cycle_count += 1
                
                print(f"\n" + "="*60)
                print(f"📊 CICLO {cycle_count} - REVISIÓN DE ESTADO")
                
                # Obtener estado actual
                status = self.get_current_status()
                if not status:
                    print("❌ Error obteniendo datos - Reintentando en 1 minuto...")
                    time.sleep(60)
                    continue
                
                # Analizar riesgos y oportunidades
                risks = self.analyze_risks(status)
                opportunities = self.check_opportunities(status)
                
                # Mostrar reporte
                self.print_status_report(status, risks, opportunities)
                
                # Detectar cambios críticos
                critical_risks = [r for r in risks if r['level'] == 'CRÍTICO']
                if critical_risks:
                    print(f"\n🚨 ¡ALERTA CRÍTICA! Revisando cada minuto...")
                    time.sleep(60)  # Revisión cada minuto si hay riesgo crítico
                else:
                    # Esperar 5 minutos para próxima revisión
                    time.sleep(300)
                
        except KeyboardInterrupt:
            print(f"\n\n⏹️ MONITOREO DETENIDO POR USUARIO")
            runtime = datetime.now() - self.monitoring_start
            print(f"🕐 Tiempo de monitoreo: {runtime}")
            print(f"📊 Ciclos completados: {cycle_count}")
        
        except Exception as e:
            print(f"\n❌ Error en monitoreo: {e}")

if __name__ == "__main__":
    monitor = PositionMonitor()
    monitor.run_continuous_monitoring()
