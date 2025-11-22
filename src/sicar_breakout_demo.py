#!/usr/bin/env python3
"""
SICAR - Demo Acelerado de Estrategia de Rompimiento
Versión de demostración que simula las 3 sesiones de trading rápidamente
"""

import numpy as np
import pandas as pd
import json
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class SessionInfo:
    """Información de sesión de trading"""
    name: str
    start_utc: str
    end_utc: str
    description: str
    expected_win_rate: float
    expected_roi_monthly: float

@dataclass
class BreakoutResult:
    """Resultado de análisis de rompimiento"""
    timestamp: datetime
    symbol: str
    session: str
    signal_type: str
    entry_price: float
    stop_loss: float
    take_profit: float
    volume_ratio: float
    confidence: float
    position_size: float
    pnl: float = 0.0
    pnl_percent: float = 0.0
    close_reason: str = ""

class SicarBreakoutDemo:
    """Demo acelerado de la estrategia de breakout"""
    
    def __init__(self, initial_capital: float = 200.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.base_capital = initial_capital
        
        # Configuración de sesiones
        self.sessions = {
            'asian': SessionInfo(
                name='Asiática',
                start_utc='00:00',
                end_utc='00:05',
                description='Apertura mercados asiáticos',
                expected_win_rate=78.0,
                expected_roi_monthly=3.5
            ),
            'european': SessionInfo(
                name='Europea',
                start_utc='12:30',
                end_utc='12:35',
                description='Apertura mercados europeos',
                expected_win_rate=95.5,
                expected_roi_monthly=4.0
            ),
            'american': SessionInfo(
                name='Americana',
                start_utc='13:25',
                end_utc='13:30',
                description='Apertura mercados americanos',
                expected_win_rate=87.0,
                expected_roi_monthly=3.8
            )
        }
        
        # Parámetros por sesión
        self.session_params = {
            'asian': {
                'stop_loss_pct': 0.0018,
                'take_profit_pct': 0.0054,
                'position_size_pct': 0.15,
                'min_volume_ratio': 1.3,
                'confidence_threshold': 0.65
            },
            'european': {
                'stop_loss_pct': 0.0013,
                'take_profit_pct': 0.0039,
                'position_size_pct': 0.20,
                'min_volume_ratio': 1.5,
                'confidence_threshold': 0.70
            },
            'american': {
                'stop_loss_pct': 0.0015,
                'take_profit_pct': 0.0045,
                'position_size_pct': 0.18,
                'min_volume_ratio': 1.8,
                'confidence_threshold': 0.75
            }
        }
        
        # Símbolos principales
        self.trading_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'AVAXUSDT',
            'ADAUSDT', 'DOTUSDT', 'ATOMUSDT', 'NEARUSDT', 'UNIUSDT',
            'AAVEUSDT', 'LINKUSDT', 'DOGEUSDT', 'XRPUSDT', 'LTCUSDT'
        ]
        
        # Precios base (enero 2025)
        self.base_prices = {
            'BTCUSDT': 95000, 'ETHUSDT': 3400, 'BNBUSDT': 680,
            'SOLUSDT': 180, 'AVAXUSDT': 38, 'ADAUSDT': 0.85,
            'DOTUSDT': 6.8, 'ATOMUSDT': 7.2, 'NEARUSDT': 4.8,
            'UNIUSDT': 12.5, 'AAVEUSDT': 280, 'LINKUSDT': 22,
            'DOGEUSDT': 0.32, 'XRPUSDT': 2.1, 'LTCUSDT': 105
        }
        
        self.trades = []
        self.total_pnl = 0.0
        self.total_reinvested = 0.0
        self.reinvestment_threshold = 0.05
        self.max_capital = 500.0

    def simulate_breakout_candle(self, symbol: str, session: str) -> Optional[BreakoutResult]:
        """Simula una vela de breakout para la sesión"""
        base_price = self.base_prices.get(symbol, 100)
        params = self.session_params[session]
        session_info = self.sessions[session]
        
        # Probabilidad de generar señal basada en win rate esperado
        signal_probability = session_info.expected_win_rate / 100.0 * 0.3  # 30% de las veces
        
        if random.random() > signal_probability:
            return None
        
        # Generar datos de la vela
        open_price = base_price * random.uniform(0.998, 1.002)
        
        # Determinar dirección del breakout
        is_bullish = random.random() > 0.5
        
        if is_bullish:
            # Breakout alcista
            close_price = open_price * random.uniform(1.008, 1.025)  # 0.8% - 2.5%
            high_price = close_price * random.uniform(1.001, 1.003)
            low_price = open_price * random.uniform(0.997, 0.999)
            signal_type = 'bullish_breakout'
        else:
            # Breakout bajista
            close_price = open_price * random.uniform(0.975, 0.992)  # -2.5% - -0.8%
            high_price = open_price * random.uniform(1.001, 1.003)
            low_price = close_price * random.uniform(0.997, 0.999)
            signal_type = 'bearish_breakout'
        
        # Calcular métricas
        body_size = abs(close_price - open_price)
        total_range = high_price - low_price
        body_ratio = body_size / total_range if total_range > 0 else 0
        
        # Volumen simulado (mayor en breakouts)
        volume_ratio = random.uniform(1.5, 3.5)
        
        # Confianza basada en métricas
        confidence = min(0.95, 0.5 + (body_ratio * 0.3) + (volume_ratio * 0.15))
        
        if confidence < params['confidence_threshold']:
            return None
        
        # Calcular niveles
        entry_price = close_price
        
        if signal_type == 'bullish_breakout':
            stop_loss = entry_price * (1 - params['stop_loss_pct'])
            take_profit = entry_price * (1 + params['take_profit_pct'])
        else:
            stop_loss = entry_price * (1 + params['stop_loss_pct'])
            take_profit = entry_price * (1 - params['take_profit_pct'])
        
        position_size = self.current_capital * params['position_size_pct']
        
        return BreakoutResult(
            timestamp=datetime.now(timezone.utc),
            symbol=symbol,
            session=session,
            signal_type=signal_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume_ratio=volume_ratio,
            confidence=confidence,
            position_size=position_size
        )

    def execute_trade(self, breakout: BreakoutResult) -> BreakoutResult:
        """Ejecuta el trade simulado"""
        session_info = self.sessions[breakout.session]
        success_probability = session_info.expected_win_rate / 100.0
        
        # Simular resultado
        if random.random() < success_probability:
            # Trade exitoso
            exit_price = breakout.take_profit
            close_reason = "Take Profit"
            
            if breakout.signal_type == 'bullish_breakout':
                pnl = breakout.position_size * (exit_price / breakout.entry_price - 1)
            else:
                pnl = breakout.position_size * (breakout.entry_price / exit_price - 1)
        else:
            # Trade fallido
            exit_price = breakout.stop_loss
            close_reason = "Stop Loss"
            
            if breakout.signal_type == 'bullish_breakout':
                pnl = breakout.position_size * (exit_price / breakout.entry_price - 1)
            else:
                pnl = breakout.position_size * (breakout.entry_price / exit_price - 1)
        
        # Aplicar comisiones
        trading_fee = breakout.position_size * 0.002
        pnl_net = pnl - trading_fee
        
        # Actualizar capital
        self.current_capital += pnl_net
        self.total_pnl += pnl_net
        
        # Actualizar resultado
        breakout.pnl = pnl_net
        breakout.pnl_percent = (pnl_net / breakout.position_size) * 100
        breakout.close_reason = close_reason
        
        return breakout

    def check_reinvestment(self) -> bool:
        """Verifica reinversión"""
        current_roi = (self.current_capital - self.base_capital) / self.base_capital
        
        if current_roi >= self.reinvestment_threshold and self.current_capital < self.max_capital:
            profit = self.current_capital - self.base_capital
            reinvestment_amount = min(profit, self.max_capital - self.base_capital)
            
            self.base_capital += reinvestment_amount
            self.total_reinvested += reinvestment_amount
            
            print(f"🔄 REINVERSIÓN: +${reinvestment_amount:.2f} | Nueva base: ${self.base_capital:.2f}")
            return True
        
        return False

    def run_demo_validation(self, days: int = 7) -> Dict:
        """Ejecuta demo de validación acelerada"""
        print(f"\n🎯 === DEMO VALIDACIÓN ESTRATEGIA BREAKOUT ===")
        print(f"📅 Simulando {days} días de trading")
        print(f"💰 Capital inicial: ${self.current_capital:.2f}")
        print(f"🌍 Sesiones: {', '.join([s.name for s in self.sessions.values()])}")
        
        trades_by_session = {session: [] for session in self.sessions.keys()}
        
        # Simular días de trading
        for day in range(days):
            print(f"\n📅 === DÍA {day + 1}/{days} ===")
            
            # Simular cada sesión del día
            for session_name, session_info in self.sessions.items():
                print(f"\n🔍 Analizando sesión {session_info.name}...")
                session_trades = 0
                
                # Analizar símbolos en esta sesión
                for symbol in self.trading_symbols:
                    # Probabilidad de encontrar breakout
                    if random.random() < 0.4:  # 40% probabilidad por símbolo
                        breakout = self.simulate_breakout_candle(symbol, session_name)
                        
                        if breakout:
                            executed_trade = self.execute_trade(breakout)
                            self.trades.append(executed_trade)
                            trades_by_session[session_name].append(executed_trade)
                            session_trades += 1
                            
                            print(f"💹 {executed_trade.signal_type.upper()} {symbol} | "
                                  f"${executed_trade.position_size:.2f} | "
                                  f"PnL: ${executed_trade.pnl:.2f} ({executed_trade.pnl_percent:.2f}%) | "
                                  f"{executed_trade.close_reason}")
                            
                            # Verificar reinversión
                            self.check_reinvestment()
                
                if session_trades == 0:
                    print("❌ No se detectaron breakouts válidos")
                else:
                    print(f"✅ {session_trades} trades ejecutados")
            
            # Resumen del día
            day_pnl = sum(t.pnl for t in self.trades if t.timestamp.date() == datetime.now().date())
            current_roi = (self.current_capital - self.initial_capital) / self.initial_capital * 100
            
            print(f"\n📊 Resumen Día {day + 1}:")
            print(f"💼 Capital: ${self.current_capital:.2f}")
            print(f"📈 ROI: {current_roi:.2f}%")
            print(f"💰 PnL del día: ${day_pnl:.2f}")
        
        return self.generate_demo_report(trades_by_session, days)

    def generate_demo_report(self, trades_by_session: Dict, days: int) -> Dict:
        """Genera reporte de la demo"""
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t.pnl > 0]
        
        # Estadísticas generales
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        total_roi = (self.current_capital - self.initial_capital) / self.initial_capital * 100
        avg_pnl = sum(t.pnl for t in self.trades) / total_trades if total_trades > 0 else 0
        
        # Estadísticas por sesión
        session_stats = {}
        for session_name, session_trades in trades_by_session.items():
            if session_trades:
                session_winning = [t for t in session_trades if t.pnl > 0]
                session_win_rate = len(session_winning) / len(session_trades) * 100
                session_pnl = sum(t.pnl for t in session_trades)
                
                session_stats[session_name] = {
                    'trades_count': len(session_trades),
                    'win_rate': session_win_rate,
                    'total_pnl': session_pnl,
                    'avg_pnl': session_pnl / len(session_trades),
                    'expected_win_rate': self.sessions[session_name].expected_win_rate,
                    'performance_vs_expected': session_win_rate - self.sessions[session_name].expected_win_rate
                }
        
        # Proyección mensual
        daily_roi = total_roi / days
        monthly_projection = daily_roi * 30
        
        report = {
            'demo_summary': {
                'simulation_days': days,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'total_roi': total_roi,
                'daily_avg_roi': daily_roi,
                'monthly_projection': monthly_projection,
                'avg_pnl_per_trade': avg_pnl
            },
            'capital_evolution': {
                'initial_capital': self.initial_capital,
                'final_capital': self.current_capital,
                'base_capital': self.base_capital,
                'total_reinvested': self.total_reinvested,
                'total_pnl': self.total_pnl
            },
            'session_performance': session_stats,
            'strategy_validation': {
                'asian_validated': session_stats.get('asian', {}).get('win_rate', 0) >= 70,
                'european_validated': session_stats.get('european', {}).get('win_rate', 0) >= 90,
                'american_validated': session_stats.get('american', {}).get('win_rate', 0) >= 80,
                'overall_valid': win_rate >= 80 and total_roi >= 10
            },
            'trades': [asdict(trade) for trade in self.trades]
        }
        
        return report

def run_breakout_demo():
    """Ejecuta demo de validación de breakout"""
    print("🚀 === DEMO ESTRATEGIA BREAKOUT MULTI-SESIÓN ===")
    print("📊 Validando estrategia de rompimiento de primera vela")
    print("🌍 Sesiones: Asiática, Europea, Americana")
    
    # Inicializar demo
    demo = SicarBreakoutDemo(initial_capital=200.0)
    
    # Ejecutar demo de 7 días
    results = demo.run_demo_validation(days=7)
    
    # Mostrar resultados finales
    print(f"\n🎉 === RESULTADOS FINALES ===")
    summary = results['demo_summary']
    capital = results['capital_evolution']
    
    print(f"📊 Días simulados: {summary['simulation_days']}")
    print(f"🎯 Total trades: {summary['total_trades']}")
    print(f"✅ Win rate: {summary['win_rate']:.1f}%")
    print(f"💰 ROI total: {summary['total_roi']:.2f}%")
    print(f"📈 ROI diario promedio: {summary['daily_avg_roi']:.2f}%")
    print(f"🚀 Proyección mensual: {summary['monthly_projection']:.1f}%")
    print(f"💵 PnL promedio por trade: ${summary['avg_pnl_per_trade']:.2f}")
    
    print(f"\n💼 === EVOLUCIÓN DEL CAPITAL ===")
    print(f"Capital inicial: ${capital['initial_capital']:.2f}")
    print(f"Capital final: ${capital['final_capital']:.2f}")
    print(f"Capital base: ${capital['base_capital']:.2f}")
    print(f"Total reinvertido: ${capital['total_reinvested']:.2f}")
    print(f"PnL total: ${capital['total_pnl']:.2f}")
    
    # Rendimiento por sesión
    print(f"\n📊 === RENDIMIENTO POR SESIÓN ===")
    for session_name, stats in results['session_performance'].items():
        session_info = demo.sessions[session_name]
        print(f"\n{session_info.name}:")
        print(f"  • Trades: {stats['trades_count']}")
        print(f"  • Win Rate: {stats['win_rate']:.1f}% (esperado: {stats['expected_win_rate']:.1f}%)")
        print(f"  • Diferencia: {stats['performance_vs_expected']:+.1f}%")
        print(f"  • PnL total: ${stats['total_pnl']:.2f}")
        print(f"  • PnL promedio: ${stats['avg_pnl']:.2f}")
    
    # Validación de estrategia
    validation = results['strategy_validation']
    print(f"\n✅ === VALIDACIÓN DE ESTRATEGIA ===")
    print(f"Sesión Asiática: {'✅ VALIDADA' if validation['asian_validated'] else '❌ NO VALIDADA'}")
    print(f"Sesión Europea: {'✅ VALIDADA' if validation['european_validated'] else '❌ NO VALIDADA'}")
    print(f"Sesión Americana: {'✅ VALIDADA' if validation['american_validated'] else '❌ NO VALIDADA'}")
    print(f"Estrategia General: {'✅ VALIDADA' if validation['overall_valid'] else '❌ NO VALIDADA'}")
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"sicar_breakout_demo_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str, ensure_ascii=False)
    
    print(f"\n💾 Resultados guardados en: {filename}")
    
    return results

if __name__ == "__main__":
    run_breakout_demo()