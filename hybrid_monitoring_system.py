#!/usr/bin/env python3
"""
Sistema de Monitoreo Híbrido para Micro-Pruebas
- Mantiene posiciones legacy con monitoreo especial
- Aplica límites estrictos a nuevas operaciones
- Monitoreo continuo dual
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from binance import Client
from binance.exceptions import BinanceAPIException
import os
from typing import Dict, List, Optional
import traceback

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HybridMicroTestingMonitor:
    def __init__(self):
        self.client = Client(
            api_key=os.getenv('BINANCE_API_KEY'),
            api_secret=os.getenv('BINANCE_SECRET_KEY')
        )
        
        # Configuración híbrida
        self.MICRO_TRADE_MAX_USDT = 0.75
        self.MAX_DAILY_LOSS_PCT = 10  # 10% máximo diario
        self.MONITORING_INTERVAL = 30  # segundos
        
        # Posiciones legacy (existentes antes de micro-pruebas)
        self.legacy_positions = set()
        
        # Control de pérdidas diarias
        self.daily_start_balance = 0
        self.daily_loss_limit = 0
        self.daily_losses = 0
        
        logger.info("🚀 Sistema de Monitoreo Híbrido iniciado")
        
    async def initialize_daily_tracking(self):
        """Inicializar seguimiento diario"""
        try:
            account_info = self.client.futures_account()
            current_balance = float(account_info['totalWalletBalance'])
            
            self.daily_start_balance = current_balance
            self.daily_loss_limit = current_balance * (self.MAX_DAILY_LOSS_PCT / 100)
            
            logger.info(f"💰 Balance inicial del día: ${current_balance:.2f}")
            logger.info(f"🛡️ Límite pérdida diaria: ${self.daily_loss_limit:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando seguimiento: {e}")
            
    async def get_account_status(self) -> Dict:
        """Obtener estado actual de la cuenta"""
        try:
            account_info = self.client.futures_account()
            
            total_balance = float(account_info['totalWalletBalance'])
            available_balance = float(account_info['availableBalance'])
            total_unrealized_pnl = float(account_info['totalUnrealizedProfit'])
            margin_ratio = float(account_info.get('totalMaintMargin', 0)) / total_balance * 100 if total_balance > 0 else 0
            
            return {
                'total_balance': total_balance,
                'available_balance': available_balance,
                'unrealized_pnl': total_unrealized_pnl,
                'margin_ratio': margin_ratio,
                'timestamp': datetime.now()
            }
            
        except BinanceAPIException as e:
            logger.error(f"❌ Error API Binance: {e}")
            return {}
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado: {e}")
            return {}
    
    async def get_open_positions(self) -> List[Dict]:
        """Obtener posiciones abiertas"""
        try:
            positions = self.client.futures_position_information()
            
            open_positions = []
            for pos in positions:
                position_amt = float(pos['positionAmt'])
                if position_amt != 0:
                    entry_price = float(pos['entryPrice'])
                    mark_price = float(pos['markPrice'])
                    unrealized_pnl = float(pos['unRealizedProfit'])
                    
                    # Calcular valor de la posición
                    position_value = abs(position_amt) * mark_price
                    
                    position_data = {
                        'symbol': pos['symbol'],
                        'side': 'LONG' if position_amt > 0 else 'SHORT',
                        'size': abs(position_amt),
                        'entry_price': entry_price,
                        'mark_price': mark_price,
                        'unrealized_pnl': unrealized_pnl,
                        'position_value': position_value,
                        'percentage': (mark_price - entry_price) / entry_price * 100 if position_amt > 0 else (entry_price - mark_price) / entry_price * 100
                    }
                    open_positions.append(position_data)
            
            return open_positions
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo posiciones: {e}")
            return []
    
    async def identify_legacy_positions(self):
        """Identificar posiciones legacy (existentes antes de micro-pruebas)"""
        positions = await self.get_open_positions()
        
        for pos in positions:
            # Cualquier posición > límite micro se considera legacy
            if pos['position_value'] > self.MICRO_TRADE_MAX_USDT:
                self.legacy_positions.add(pos['symbol'])
                logger.info(f"📊 Posición legacy identificada: {pos['symbol']} (${pos['position_value']:.2f})")
    
    async def check_micro_compliance(self, positions: List[Dict]) -> Dict:
        """Verificar cumplimiento de límites micro-pruebas"""
        compliance = {
            'compliant_positions': [],
            'violating_positions': [],
            'legacy_positions': [],
            'new_micro_positions': []
        }
        
        for pos in positions:
            symbol = pos['symbol']
            value = pos['position_value']
            
            if symbol in self.legacy_positions:
                # Posición legacy - monitoreo especial
                compliance['legacy_positions'].append({
                    'symbol': symbol,
                    'value': value,
                    'status': 'LEGACY_MONITORING',
                    'pnl': pos['unrealized_pnl'],
                    'percentage': pos['percentage']
                })
            elif value <= self.MICRO_TRADE_MAX_USDT:
                # Nueva posición que cumple límites
                compliance['compliant_positions'].append({
                    'symbol': symbol,
                    'value': value,
                    'status': 'MICRO_COMPLIANT',
                    'pnl': pos['unrealized_pnl']
                })
                compliance['new_micro_positions'].append(pos)
            else:
                # Nueva posición que viola límites
                compliance['violating_positions'].append({
                    'symbol': symbol,
                    'value': value,
                    'limit': self.MICRO_TRADE_MAX_USDT,
                    'excess': value - self.MICRO_TRADE_MAX_USDT,
                    'status': 'VIOLATION',
                    'pnl': pos['unrealized_pnl']
                })
        
        return compliance
    
    async def check_daily_loss_limit(self, current_balance: float) -> Dict:
        """Verificar límite de pérdida diaria"""
        if self.daily_start_balance == 0:
            await self.initialize_daily_tracking()
        
        daily_pnl = current_balance - self.daily_start_balance
        loss_percentage = abs(daily_pnl) / self.daily_start_balance * 100 if daily_pnl < 0 else 0
        
        return {
            'daily_pnl': daily_pnl,
            'loss_percentage': loss_percentage,
            'limit_exceeded': loss_percentage > self.MAX_DAILY_LOSS_PCT,
            'remaining_loss_allowance': self.daily_loss_limit - abs(daily_pnl) if daily_pnl < 0 else self.daily_loss_limit
        }
    
    async def generate_monitoring_report(self) -> Dict:
        """Generar reporte completo de monitoreo"""
        try:
            # Obtener datos actuales
            account_status = await self.get_account_status()
            positions = await self.get_open_positions()
            compliance = await self.check_micro_compliance(positions)
            daily_check = await self.check_daily_loss_limit(account_status.get('total_balance', 0))
            
            report = {
                'timestamp': datetime.now().strftime("%H:%M:%S"),
                'account': account_status,
                'compliance': compliance,
                'daily_limits': daily_check,
                'summary': {
                    'total_positions': len(positions),
                    'legacy_positions': len(compliance['legacy_positions']),
                    'micro_positions': len(compliance['new_micro_positions']),
                    'violations': len(compliance['violating_positions']),
                    'daily_loss_ok': not daily_check['limit_exceeded']
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte: {e}")
            return {}
    
    def print_monitoring_report(self, report: Dict):
        """Mostrar reporte de monitoreo en consola"""
        print("\n" + "="*60)
        print("🔄 MONITOREO HÍBRIDO MICRO-PRUEBAS")
        print("="*60)
        print(f"⏰ {report['timestamp']}")
        
        # Estado de cuenta
        account = report.get('account', {})
        print(f"\n📊 ESTADO CUENTA:")
        print(f"   Balance total: ${account.get('total_balance', 0):.2f}")
        print(f"   Balance disponible: ${account.get('available_balance', 0):.2f}")
        print(f"   PnL no realizado: ${account.get('unrealized_pnl', 0):.2f}")
        
        # Límites diarios
        daily = report.get('daily_limits', {})
        status_icon = "✅" if daily.get('daily_loss_ok', True) else "🚨"
        print(f"\n{status_icon} LÍMITES DIARIOS:")
        print(f"   PnL diario: ${daily.get('daily_pnl', 0):.2f}")
        print(f"   Pérdida %: {daily.get('loss_percentage', 0):.2f}%")
        print(f"   Margen restante: ${daily.get('remaining_loss_allowance', 0):.2f}")
        
        # Posiciones legacy
        compliance = report.get('compliance', {})
        legacy_positions = compliance.get('legacy_positions', [])
        if legacy_positions:
            print(f"\n📊 POSICIONES LEGACY ({len(legacy_positions)}):")
            for pos in legacy_positions:
                pnl_icon = "📈" if pos['pnl'] > 0 else "📉"
                print(f"   {pnl_icon} {pos['symbol']}: ${pos['value']:.2f} | PnL: ${pos['pnl']:.2f} ({pos['percentage']:.2f}%)")
        
        # Posiciones micro
        micro_positions = compliance.get('new_micro_positions', [])
        if micro_positions:
            print(f"\n🧪 POSICIONES MICRO-PRUEBAS ({len(micro_positions)}):")
            for pos in micro_positions:
                pnl_icon = "📈" if pos['unrealized_pnl'] > 0 else "📉"
                print(f"   {pnl_icon} {pos['symbol']}: ${pos['position_value']:.2f} | PnL: ${pos['unrealized_pnl']:.2f}")
        
        # Violaciones
        violations = compliance.get('violating_positions', [])
        if violations:
            print(f"\n🚨 VIOLACIONES DETECTADAS ({len(violations)}):")
            for viol in violations:
                print(f"   ❌ {viol['symbol']}: ${viol['value']:.2f} (límite: ${viol['limit']:.2f})")
        
        # Resumen
        summary = report.get('summary', {})
        print(f"\n📋 RESUMEN:")
        print(f"   Total posiciones: {summary.get('total_positions', 0)}")
        print(f"   Legacy: {summary.get('legacy_positions', 0)} | Micro: {summary.get('micro_positions', 0)}")
        print(f"   Violaciones: {summary.get('violations', 0)}")
        print(f"   Estado diario: {'✅ OK' if summary.get('daily_loss_ok', True) else '🚨 LÍMITE EXCEDIDO'}")
    
    async def continuous_monitoring(self):
        """Monitoreo continuo del sistema híbrido"""
        logger.info("🔄 Iniciando monitoreo continuo híbrido...")
        
        # Identificar posiciones legacy al inicio
        await self.identify_legacy_positions()
        await self.initialize_daily_tracking()
        
        cycle = 0
        while True:
            try:
                cycle += 1
                print(f"\n🔄 CICLO DE MONITOREO #{cycle}")
                
                # Generar y mostrar reporte
                report = await self.generate_monitoring_report()
                if report:
                    self.print_monitoring_report(report)
                    
                    # Verificar alertas críticas
                    daily_limits = report.get('daily_limits', {})
                    violations = report.get('compliance', {}).get('violating_positions', [])
                    
                    if daily_limits.get('limit_exceeded', False):
                        print("\n🚨 ALERTA CRÍTICA: LÍMITE DIARIO EXCEDIDO")
                        print("🛑 Se recomienda detener nuevas operaciones")
                    
                    if violations:
                        print(f"\n⚠️ ALERTA: {len(violations)} violaciones detectadas")
                        print("📊 Revisar posiciones que exceden límites micro")
                
                # Esperar siguiente ciclo
                print(f"\n⏳ Próximo ciclo en {self.MONITORING_INTERVAL} segundos...")
                await asyncio.sleep(self.MONITORING_INTERVAL)
                
            except KeyboardInterrupt:
                print("\n🛑 Monitoreo detenido por usuario")
                break
            except Exception as e:
                logger.error(f"❌ Error en ciclo de monitoreo: {e}")
                print(f"❌ Error: {e}")
                await asyncio.sleep(5)  # Esperar antes de reintentar

async def main():
    """Función principal"""
    print("🚀 INICIANDO SISTEMA DE MONITOREO HÍBRIDO")
    print("="*50)
    print("🎯 Modo: Posiciones legacy + Micro-pruebas")
    print("💰 Límite por operación: $0.75")
    print("🛡️ Límite pérdida diaria: 10%")
    print("⏰ Intervalo monitoreo: 30s")
    print("="*50)
    
    monitor = HybridMicroTestingMonitor()
    await monitor.continuous_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
