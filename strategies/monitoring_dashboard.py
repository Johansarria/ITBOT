#!/usr/bin/env python3
"""
DASHBOARD DE MONITOREO SIMPLE
Para monitorear el rendimiento de las estrategias autónomas
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List

class AutonomousMonitoringDashboard:
    """
    Dashboard simple para monitorear estrategias autónomas
    """
    
    def __init__(self):
        self.metrics_file = '/home/johan/itbot_linux/strategies/performance_metrics.json'
        self.trades_file = '/home/johan/itbot_linux/strategies/trades_log.json'
        
    def log_trade(self, trade_data: Dict):
        """
        Registrar un trade ejecutado
        """
        trade_entry = {
            'timestamp': datetime.now().isoformat(),
            'pair': trade_data.get('pair'),
            'direction': trade_data.get('direction'),
            'entry_price': trade_data.get('entry_price'),
            'position_size': trade_data.get('position_size'),
            'strategy': trade_data.get('strategy'),
            'confidence': trade_data.get('confidence'),
            'status': 'OPEN'
        }
        
        # Cargar trades existentes
        trades = self.load_trades()
        trades.append(trade_entry)
        
        # Guardar trades
        with open(self.trades_file, 'w') as f:
            json.dump(trades, f, indent=2)
            
    def load_trades(self) -> List[Dict]:
        """
        Cargar historial de trades
        """
        if os.path.exists(self.trades_file):
            with open(self.trades_file, 'r') as f:
                return json.load(f)
        return []
    
    def calculate_daily_performance(self) -> Dict:
        """
        Calcular rendimiento diario
        """
        trades = self.load_trades()
        today = datetime.now().date()
        
        today_trades = [
            t for t in trades 
            if datetime.fromisoformat(t['timestamp']).date() == today
        ]
        
        total_trades = len(today_trades)
        if total_trades == 0:
            return {'trades': 0, 'pnl': 0, 'win_rate': 0}
        
        # Simular PnL (en producción usar datos reales)
        winning_trades = 0
        total_pnl = 0
        
        for trade in today_trades:
            # Simular PnL basado en confianza
            simulated_pnl = trade['confidence'] * 0.01 * 1000 if trade.get('confidence') else 10
            total_pnl += simulated_pnl
            if simulated_pnl > 0:
                winning_trades += 1
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        return {
            'trades': total_trades,
            'pnl': total_pnl,
            'win_rate': win_rate,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades
        }
    
    def generate_report(self) -> str:
        """
        Generar reporte de rendimiento
        """
        daily_perf = self.calculate_daily_performance()
        trades = self.load_trades()
        
        # Estadísticas por estrategia
        strategy_stats = {}
        for trade in trades:
            strategy = trade.get('strategy', 'unknown')
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {'count': 0, 'total_confidence': 0}
            
            strategy_stats[strategy]['count'] += 1
            strategy_stats[strategy]['total_confidence'] += trade.get('confidence', 0)
        
        # Generar reporte
        report = f"""
🤖 REPORTE DE ESTRATEGIAS AUTÓNOMAS
=======================================
📅 Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

📊 RENDIMIENTO DIARIO:
   💰 PnL: ${daily_perf['pnl']:,.2f}
   📈 Trades ejecutados: {daily_perf['trades']}
   🎯 Win Rate: {daily_perf['win_rate']:.1%}
   ✅ Trades ganadores: {daily_perf.get('winning_trades', 0)}
   ❌ Trades perdedores: {daily_perf.get('losing_trades', 0)}

📊 ESTADÍSTICAS POR ESTRATEGIA:
"""
        
        for strategy, stats in strategy_stats.items():
            avg_confidence = stats['total_confidence'] / stats['count'] if stats['count'] > 0 else 0
            report += f"   {strategy}: {stats['count']} trades (Confianza promedio: {avg_confidence:.1%})\n"
        
        report += f"""
📋 RESUMEN TOTAL:
   📊 Total trades históricos: {len(trades)}
   🕐 Último trade: {trades[-1]['timestamp'] if trades else 'N/A'}
   
💡 RECOMENDACIONES:
"""
        
        if daily_perf['win_rate'] < 0.6:
            report += "   ⚠️  Win rate bajo - considerar ajustar parámetros de confianza\n"
        if daily_perf['trades'] < 5:
            report += "   ⚠️  Pocos trades - considerar ampliar criterios de entrada\n"
        if daily_perf['win_rate'] > 0.8:
            report += "   🎯 Excelente rendimiento - mantener configuración actual\n"
            
        return report
    
    def show_live_dashboard(self):
        """
        Mostrar dashboard en tiempo real
        """
        os.system('clear')  # Limpiar pantalla
        
        report = self.generate_report()
        print(report)
        
        # Mostrar últimos 5 trades
        trades = self.load_trades()
        recent_trades = trades[-5:] if len(trades) >= 5 else trades
        
        if recent_trades:
            print("\n📝 ÚLTIMOS TRADES:")
            for trade in reversed(recent_trades):
                timestamp = datetime.fromisoformat(trade['timestamp']).strftime("%H:%M:%S")
                print(f"   {timestamp} - {trade['strategy']} - {trade['pair']} {trade['direction']} @ {trade['entry_price']}")

def main():
    """
    Función principal del dashboard
    """
    dashboard = AutonomousMonitoringDashboard()
    
    try:
        dashboard.show_live_dashboard()
        
        print("\n" + "=" * 50)
        print("🔄 Para actualizar en tiempo real, ejecuta:")
        print("   watch -n 10 'python3 strategies/monitoring_dashboard.py'")
        print("\n💡 Para logging automático, integra con tu bot:")
        print("   dashboard.log_trade(signal_data)")
        
    except KeyboardInterrupt:
        print("\n👋 Dashboard cerrado")

if __name__ == "__main__":
    main()
