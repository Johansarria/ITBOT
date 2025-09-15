#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulación Terminal 2 - ADAUSDT
Capital Base: $1000.0
"""

import json
import time
import random
from datetime import datetime, timedelta
import os

class TradingSimulator:
    def __init__(self, symbol, capital, config):
        self.symbol = symbol
        self.capital = capital
        self.initial_capital = capital
        self.config = config
        self.trades = []
        self.session_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.log_file = f"logs_simulacion/{self.session_id}.jsonl"
        
    def log_event(self, event_type: str, data: dict):
        """Registra eventos en formato JSON Lines"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "symbol": self.symbol,
            "event_type": event_type,
            "data": data
        }
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')
    
    def simulate_trade(self) -> dict:
        """Simula una operación de trading"""
        # Determinar si es ganadora basado en win_rate
        is_winner = random.random() < self.config['win_rate']
        
        # Calcular retorno basado en volatilidad
        base_return = self.config['weekly_return'] / 35  # Retorno diario promedio
        volatility_factor = random.uniform(-self.config['volatility'], self.config['volatility'])
        
        if is_winner:
            return_pct = abs(base_return + volatility_factor)
        else:
            return_pct = -(abs(base_return) * random.uniform(0.3, 0.8))
        
        # Calcular monto de la operación (2-5% del capital)
        trade_amount = self.capital * random.uniform(0.02, 0.05)
        profit_loss = trade_amount * (return_pct / 100)
        
        trade = {
            "trade_id": len(self.trades) + 1,
            "timestamp": datetime.now().isoformat(),
            "type": "BUY" if is_winner else "SELL",
            "amount": round(trade_amount, 2),
            "return_pct": round(return_pct, 4),
            "profit_loss": round(profit_loss, 2),
            "is_winner": is_winner
        }
        
        self.capital += profit_loss
        self.trades.append(trade)
        
        return trade
    
    def run_simulation(self, duration_hours: int = 24):
        """Ejecuta la simulación por el tiempo especificado"""
        print(f"\n=== INICIANDO SIMULACIÓN {self.symbol} ===")
        print(f"Terminal: 2")
        print(f"Capital Inicial: ${self.initial_capital:,.2f}")
        print(f"Duración: {duration_hours} horas")
        print(f"Archivo de logs: {self.log_file}")
        print("=" * 50)
        
        # Log de inicio de sesión
        self.log_event("session_start", {
            "initial_capital": self.initial_capital,
            "symbol": self.symbol,
            "duration_hours": duration_hours,
            "config": self.config
        })
        
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=duration_hours)
        trade_count = 0
        
        try:
            while datetime.now() < end_time:
                # Simular operación cada 15-45 minutos
                wait_time = random.uniform(900, 2700)  # 15-45 minutos en segundos
                
                # Para demo, reducir tiempo de espera
                demo_wait = min(wait_time / 60, 10)  # Máximo 10 segundos para demo
                time.sleep(demo_wait)
                
                # Ejecutar trade
                trade = self.simulate_trade()
                trade_count += 1
                
                # Log del trade
                self.log_event("trade_executed", trade)
                
                # Mostrar progreso
                current_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100
                print(f"Trade #{trade_count} | {self.symbol} | "
                      f"P&L: ${trade['profit_loss']:+.2f} | "
                      f"Capital: ${self.capital:,.2f} | "
                      f"Retorno: {current_return:+.2f}%")
                
                # Log de performance cada 10 trades
                if trade_count % 10 == 0:
                    self.log_performance_update()
                
                # Simular condición de parada por pérdidas excesivas
                if self.capital < self.initial_capital * 0.7:  # Stop loss al 30%
                    print(f"\n⚠️  STOP LOSS ACTIVADO - Capital: ${self.capital:,.2f}")
                    self.log_event("stop_loss_triggered", {
                        "remaining_capital": self.capital,
                        "loss_pct": ((self.initial_capital - self.capital) / self.initial_capital) * 100
                    })
                    break
        
        except KeyboardInterrupt:
            print(f"\n⏹️  Simulación interrumpida por el usuario")
            self.log_event("simulation_interrupted", {"reason": "user_interrupt"})
        
        # Resumen final
        self.generate_final_report()
    
    def log_performance_update(self):
        """Registra actualización de performance"""
        total_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100
        winning_trades = sum(1 for t in self.trades if t['is_winner'])
        win_rate = (winning_trades / len(self.trades)) * 100 if self.trades else 0
        
        performance = {
            "total_trades": len(self.trades),
            "current_capital": self.capital,
            "total_return_pct": round(total_return, 2),
            "win_rate_pct": round(win_rate, 2),
            "winning_trades": winning_trades,
            "losing_trades": len(self.trades) - winning_trades
        }
        
        self.log_event("performance_update", performance)
    
    def generate_final_report(self):
        """Genera reporte final de la simulación"""
        final_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100
        winning_trades = sum(1 for t in self.trades if t['is_winner'])
        total_profit = sum(t['profit_loss'] for t in self.trades if t['profit_loss'] > 0)
        total_loss = sum(t['profit_loss'] for t in self.trades if t['profit_loss'] < 0)
        
        report = {
            "session_summary": {
                "symbol": self.symbol,
                "initial_capital": self.initial_capital,
                "final_capital": self.capital,
                "total_return_pct": round(final_return, 2),
                "total_trades": len(self.trades),
                "winning_trades": winning_trades,
                "win_rate_pct": round((winning_trades / len(self.trades)) * 100, 2) if self.trades else 0,
                "total_profit": round(total_profit, 2),
                "total_loss": round(total_loss, 2),
                "net_profit": round(self.capital - self.initial_capital, 2)
            }
        }
        
        # Log del reporte final
        self.log_event("session_end", report)
        
        # Mostrar resumen en consola
        print(f"\n{'='*60}")
        print(f"RESUMEN FINAL - {self.symbol} (Terminal 2)")
        print(f"{'='*60}")
        print(f"Capital Inicial: ${self.initial_capital:,.2f}")
        print(f"Capital Final: ${self.capital:,.2f}")
        print(f"Retorno Total: {final_return:+.2f}%")
        print(f"Operaciones: {len(self.trades)}")
        print(f"Operaciones Ganadoras: {winning_trades}")
        print(f"Tasa de Éxito: {(winning_trades / len(self.trades)) * 100:.1f}%" if self.trades else "N/A")
        print(f"Ganancia Bruta: ${total_profit:,.2f}")
        print(f"Pérdida Bruta: ${total_loss:,.2f}")
        print(f"Ganancia Neta: ${self.capital - self.initial_capital:+,.2f}")
        print(f"Archivo de logs: {self.log_file}")
        print(f"{'='*60}")
        
        # Guardar reporte en JSON
        report_file = f"logs_simulacion/report_{self.session_id}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Reporte guardado en: {report_file}")

if __name__ == "__main__":
    # Configuración del símbolo
    symbol = "ADAUSDT"
    config = {
            "monthly_return": 27.17,
            "weekly_return": 6.32,
            "volatility": 0.18,
            "win_rate": 0.65
}
    
    # Crear simulador
    simulator = TradingSimulator(symbol, 1000.0, config)
    
    # Ejecutar simulación (24 horas simuladas en ~5 minutos reales)
    simulator.run_simulation(duration_hours=24)
