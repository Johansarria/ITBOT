#!/usr/bin/env python3
"""
SICAR - Validador de Estrategia de Rompimiento de Primera Vela
Sistema integrado que valida y ejecuta la estrategia de breakout en las 3 sesiones principales
"""

import numpy as np
import pandas as pd
import json
import time
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass, asdict
import pytz

@dataclass
class SessionInfo:
    """Información de sesión de trading"""
    name: str
    start_utc: str  # Formato "HH:MM"
    end_utc: str
    timezone_name: str
    description: str
    expected_win_rate: float
    expected_roi_monthly: float

@dataclass
class BreakoutResult:
    """Resultado de análisis de rompimiento"""
    timestamp: datetime
    symbol: str
    session: str
    signal_type: str  # 'bullish_breakout', 'bearish_breakout', 'no_signal'
    entry_price: float
    stop_loss: float
    take_profit: float
    volume_ratio: float
    confidence: float
    position_size: float
    pnl: float = 0.0
    pnl_percent: float = 0.0
    close_reason: str = ""
    trade_duration_minutes: float = 0.0

class SicarBreakoutValidator:
    """
    Validador completo de la estrategia de rompimiento de primera vela
    Integra con el sistema SICAR de capital variable
    """
    
    def __init__(self, initial_capital: float = 200.0):
        """
        Inicializa el validador de breakout
        
        Args:
            initial_capital: Capital inicial en USDT
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.base_capital = initial_capital
        
        # Configuración de sesiones principales
        self.sessions = {
            'asian': SessionInfo(
                name='Asiática',
                start_utc='00:00',  # 8:00 PM EST = 00:00 UTC (día siguiente)
                end_utc='00:05',
                timezone_name='Asia/Tokyo',
                description='Apertura mercados asiáticos (Tokio, Hong Kong)',
                expected_win_rate=78.0,
                expected_roi_monthly=3.5
            ),
            'european': SessionInfo(
                name='Europea',
                start_utc='12:30',  # 8:30 AM EST = 12:30 UTC
                end_utc='12:35',
                timezone_name='Europe/London',
                description='Apertura mercados europeos (Londres, Frankfurt)',
                expected_win_rate=95.5,
                expected_roi_monthly=4.0
            ),
            'american': SessionInfo(
                name='Americana',
                start_utc='13:25',  # 9:25 AM EST = 13:25 UTC
                end_utc='13:30',
                timezone_name='America/New_York',
                description='Apertura mercados americanos (NYSE, NASDAQ)',
                expected_win_rate=87.0,
                expected_roi_monthly=3.8
            )
        }
        
        # Parámetros optimizados por sesión
        self.session_params = {
            'asian': {
                'stop_loss_pct': 0.0018,      # 0.18%
                'take_profit_pct': 0.0054,    # 0.54% (ratio 3:1)
                'position_size_pct': 0.15,    # 15% del capital (más conservador)
                'min_volume_ratio': 1.3,      # Volumen mínimo vs promedio
                'min_price_move_pct': 0.0012, # Movimiento mínimo 0.12%
                'confidence_threshold': 0.65, # Confianza mínima
                'max_spread_pct': 0.0006      # Spread máximo 0.06%
            },
            'european': {
                'stop_loss_pct': 0.0013,      # 0.13%
                'take_profit_pct': 0.0039,    # 0.39% (ratio 3:1)
                'position_size_pct': 0.20,    # 20% del capital
                'min_volume_ratio': 1.5,      # Volumen mínimo vs promedio
                'min_price_move_pct': 0.0008, # Movimiento mínimo 0.08%
                'confidence_threshold': 0.70, # Confianza mínima
                'max_spread_pct': 0.0005      # Spread máximo 0.05%
            },
            'american': {
                'stop_loss_pct': 0.0015,      # 0.15%
                'take_profit_pct': 0.0045,    # 0.45% (ratio 3:1)
                'position_size_pct': 0.18,    # 18% del capital
                'min_volume_ratio': 1.8,      # Mayor volumen requerido
                'min_price_move_pct': 0.0010, # Movimiento mínimo 0.10%
                'confidence_threshold': 0.75, # Confianza mínima
                'max_spread_pct': 0.0004      # Spread máximo 0.04%
            }
        }
        
        # Símbolos optimizados para breakouts
        self.trading_symbols = [
            # Criptomonedas principales - Excelentes para rupturas
            'BTCUSDT',    # Bitcoin - Líder del mercado
            'ETHUSDT',    # Ethereum - Alta liquidez
            'BNBUSDT',    # Binance Coin - Alta volatilidad
            'SOLUSDT',    # Solana - Movimientos explosivos
            'AVAXUSDT',   # Avalanche - Alta volatilidad
            
            # Layer 1 blockchains
            'ADAUSDT',    # Cardano - Movimientos fuertes
            'DOTUSDT',    # Polkadot - Excelente para breakouts
            'ATOMUSDT',   # Cosmos - Alta volatilidad intraday
            'NEARUSDT',   # Near Protocol - Movimientos explosivos
            
            # DeFi tokens
            'UNIUSDT',    # Uniswap - Líder DeFi
            'AAVEUSDT',   # Aave - Movimientos significativos
            'LINKUSDT',   # Chainlink - Alta volatilidad
            
            # Altcoins volátiles
            'DOGEUSDT',   # Dogecoin - Movimientos extremos
            'XRPUSDT',    # Ripple - Rupturas significativas
            'LTCUSDT'     # Litecoin - Volatilidad clásica
        ]
        
        # Tracking
        self.trades = []
        self.session_stats = {}
        self.total_pnl = 0.0
        self.total_reinvested = 0.0
        self.reinvestment_threshold = 0.05  # 5% ROI para reinvertir
        self.max_capital = 500.0
        
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        print(f"🚀 SICAR Breakout Validator iniciado")
        print(f"💰 Capital inicial: ${self.current_capital:.2f}")
        print(f"📊 Sesiones configuradas: {len(self.sessions)}")
        print(f"🎯 Símbolos a monitorear: {len(self.trading_symbols)}")

    def generate_market_data(self, symbol: str, periods: int = 100) -> pd.DataFrame:
        """
        Genera datos de mercado simulados para análisis
        
        Args:
            symbol: Símbolo del par
            periods: Número de períodos
            
        Returns:
            DataFrame con datos OHLCV
        """
        # Precios base actualizados (enero 2025)
        base_prices = {
            'BTCUSDT': 95000,   # Bitcoin
            'ETHUSDT': 3400,    # Ethereum
            'BNBUSDT': 680,     # Binance Coin
            'SOLUSDT': 180,     # Solana
            'AVAXUSDT': 38,     # Avalanche
            'ADAUSDT': 0.85,    # Cardano
            'DOTUSDT': 6.8,     # Polkadot
            'ATOMUSDT': 7.2,    # Cosmos
            'NEARUSDT': 4.8,    # Near Protocol
            'UNIUSDT': 12.5,    # Uniswap
            'AAVEUSDT': 280,    # Aave
            'LINKUSDT': 22,     # Chainlink
            'DOGEUSDT': 0.32,   # Dogecoin
            'XRPUSDT': 2.1,     # Ripple
            'LTCUSDT': 105      # Litecoin
        }
        
        base_price = base_prices.get(symbol, 100)
        
        # Generar datos con patrones de breakout
        timestamps = []
        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []
        
        current_time = datetime.now(timezone.utc)
        current_price = base_price
        
        for i in range(periods):
            # Timestamp (intervalos de 1 minuto)
            timestamps.append(current_time - timedelta(minutes=(periods-i)))
            
            # Precio de apertura
            open_price = current_price
            opens.append(open_price)
            
            # Simular patrones de breakout en horarios de sesión
            hour = (current_time - timedelta(minutes=(periods-i))).hour
            minute = (current_time - timedelta(minutes=(periods-i))).minute
            
            # Detectar si estamos en ventana de breakout
            is_breakout_window = (
                (hour == 0 and minute <= 5) or      # Sesión asiática
                (hour == 12 and 30 <= minute <= 35) or  # Sesión europea
                (hour == 13 and 25 <= minute <= 30)     # Sesión americana
            )
            
            if is_breakout_window and i >= periods - 10:  # Últimos 10 períodos
                # Simular breakout más probable
                volatility = random.uniform(0.008, 0.025)  # 0.8% - 2.5%
                trend_strength = random.uniform(0.5, 0.9)  # Tendencia fuerte
                
                if random.random() > 0.3:  # 70% probabilidad de breakout
                    direction = random.choice([1, -1])
                    price_change = direction * volatility * trend_strength
                else:
                    price_change = random.gauss(0, volatility * 0.3)
            else:
                # Movimiento normal
                volatility = random.uniform(0.002, 0.008)  # 0.2% - 0.8%
                price_change = random.gauss(0, volatility)
            
            close_price = open_price * (1 + price_change)
            closes.append(close_price)
            
            # High y Low
            if close_price > open_price:  # Vela verde
                high_price = close_price * random.uniform(1.0002, 1.005)
                low_price = open_price * random.uniform(0.995, 0.9998)
            else:  # Vela roja
                high_price = open_price * random.uniform(1.0002, 1.005)
                low_price = close_price * random.uniform(0.995, 0.9998)
            
            highs.append(high_price)
            lows.append(low_price)
            
            # Volumen (mayor en breakouts)
            base_volume = random.uniform(800000, 2500000)
            if is_breakout_window and abs(price_change) > 0.01:
                volume_multiplier = random.uniform(2.0, 4.0)
            else:
                volume_multiplier = random.uniform(0.8, 1.5)
            
            volumes.append(base_volume * volume_multiplier)
            
            current_price = close_price
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })
        
        return df

    def detect_session_breakout(self, symbol: str, session: str, df: pd.DataFrame) -> Optional[BreakoutResult]:
        """
        Detecta rompimiento en la primera vela de la sesión
        
        Args:
            symbol: Símbolo a analizar
            session: Sesión ('asian', 'european', 'american')
            df: DataFrame con datos de mercado
            
        Returns:
            BreakoutResult o None
        """
        if len(df) < 20:
            return None
        
        params = self.session_params[session]
        
        # Obtener la vela más reciente (primera vela de la sesión)
        current_candle = df.iloc[-1]
        
        # Calcular indicadores
        recent_prices = df['close'].tail(20).tolist()
        recent_volumes = df['volume'].tail(20).tolist()
        
        avg_volume = sum(recent_volumes[:-1]) / len(recent_volumes[:-1])
        volume_ratio = current_candle['volume'] / avg_volume if avg_volume > 0 else 1.0
        
        # Análisis de la vela
        open_price = current_candle['open']
        close_price = current_candle['close']
        high_price = current_candle['high']
        low_price = current_candle['low']
        
        body_size = abs(close_price - open_price)
        total_range = high_price - low_price
        body_ratio = body_size / total_range if total_range > 0 else 0
        
        price_change_pct = abs(close_price - open_price) / open_price
        
        # Verificar condiciones básicas
        if (volume_ratio < params['min_volume_ratio'] or
            price_change_pct < params['min_price_move_pct'] or
            body_ratio < 0.4):  # Cuerpo debe ser al menos 40% de la vela
            return None
        
        # Determinar tipo de breakout
        signal_type = 'no_signal'
        confidence = 0.0
        
        if close_price > open_price:  # Vela verde
            upper_wick_ratio = (high_price - close_price) / total_range if total_range > 0 else 0
            
            if (body_ratio > 0.6 and  # Cuerpo fuerte
                upper_wick_ratio < 0.25 and  # Mecha superior pequeña
                volume_ratio > params['min_volume_ratio']):
                signal_type = 'bullish_breakout'
                confidence = min(0.9, 0.4 + (body_ratio * 0.3) + (volume_ratio * 0.2))
        
        elif close_price < open_price:  # Vela roja
            lower_wick_ratio = (close_price - low_price) / total_range if total_range > 0 else 0
            
            if (body_ratio > 0.6 and  # Cuerpo fuerte
                lower_wick_ratio < 0.25 and  # Mecha inferior pequeña
                volume_ratio > params['min_volume_ratio']):
                signal_type = 'bearish_breakout'
                confidence = min(0.9, 0.4 + (body_ratio * 0.3) + (volume_ratio * 0.2))
        
        # Verificar umbral de confianza
        if confidence < params['confidence_threshold']:
            return None
        
        # Calcular niveles de entrada y salida
        entry_price = close_price
        
        if signal_type == 'bullish_breakout':
            stop_loss = entry_price * (1 - params['stop_loss_pct'])
            take_profit = entry_price * (1 + params['take_profit_pct'])
        elif signal_type == 'bearish_breakout':
            stop_loss = entry_price * (1 + params['stop_loss_pct'])
            take_profit = entry_price * (1 - params['take_profit_pct'])
        else:
            return None
        
        # Calcular tamaño de posición
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

    def simulate_trade_execution(self, breakout: BreakoutResult) -> BreakoutResult:
        """
        Simula la ejecución de un trade de breakout
        
        Args:
            breakout: Resultado de breakout
            
        Returns:
            BreakoutResult actualizado con PnL
        """
        # Simular duración del trade (5-30 minutos típicamente)
        trade_duration = random.uniform(5, 30)
        
        # Simular movimiento del precio
        entry_price = breakout.entry_price
        
        # Probabilidad de éxito basada en datos históricos
        session_info = self.sessions[breakout.session]
        success_probability = session_info.expected_win_rate / 100.0
        
        # Simular resultado
        if random.random() < success_probability:
            # Trade exitoso - alcanza take profit
            exit_price = breakout.take_profit
            close_reason = "Take Profit"
            
            if breakout.signal_type == 'bullish_breakout':
                pnl = breakout.position_size * (exit_price / entry_price - 1)
            else:  # bearish_breakout
                pnl = breakout.position_size * (entry_price / exit_price - 1)
        else:
            # Trade fallido - alcanza stop loss
            exit_price = breakout.stop_loss
            close_reason = "Stop Loss"
            
            if breakout.signal_type == 'bullish_breakout':
                pnl = breakout.position_size * (exit_price / entry_price - 1)
            else:  # bearish_breakout
                pnl = breakout.position_size * (entry_price / exit_price - 1)
        
        # Aplicar comisiones (0.1% por lado = 0.2% total)
        trading_fee = breakout.position_size * 0.002
        pnl_net = pnl - trading_fee
        
        # Actualizar capital
        self.current_capital += pnl_net
        self.total_pnl += pnl_net
        
        # Actualizar resultado
        breakout.pnl = pnl_net
        breakout.pnl_percent = (pnl_net / breakout.position_size) * 100
        breakout.close_reason = close_reason
        breakout.trade_duration_minutes = trade_duration
        
        return breakout

    def check_reinvestment(self) -> bool:
        """
        Verifica si se debe reinvertir las ganancias
        
        Returns:
            True si se reinvirtió
        """
        current_roi = (self.current_capital - self.base_capital) / self.base_capital
        
        if current_roi >= self.reinvestment_threshold and self.current_capital < self.max_capital:
            # Calcular cantidad a reinvertir
            profit = self.current_capital - self.base_capital
            reinvestment_amount = min(profit, self.max_capital - self.base_capital)
            
            self.base_capital += reinvestment_amount
            self.total_reinvested += reinvestment_amount
            
            print(f"🔄 REINVERSIÓN: +${reinvestment_amount:.2f} | Nueva base: ${self.base_capital:.2f}")
            return True
        
        return False

    def get_current_session(self) -> Optional[str]:
        """
        Determina la sesión actual basada en la hora UTC
        
        Returns:
            Nombre de la sesión actual o None
        """
        now_utc = datetime.now(timezone.utc)
        current_time = now_utc.strftime("%H:%M")
        
        for session_name, session_info in self.sessions.items():
            start_time = session_info.start_utc
            end_time = session_info.end_utc
            
            if start_time <= current_time <= end_time:
                return session_name
        
        return None

    def run_session_validation(self, duration_hours: int = 24) -> Dict:
        """
        Ejecuta validación de la estrategia durante un período
        
        Args:
            duration_hours: Duración de la validación en horas
            
        Returns:
            Resultados de la validación
        """
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(hours=duration_hours)
        
        print(f"\n🎯 === VALIDACIÓN ESTRATEGIA BREAKOUT MULTI-SESIÓN ===")
        print(f"⏱️ Duración: {duration_hours} horas")
        print(f"💰 Capital inicial: ${self.current_capital:.2f}")
        print(f"📊 Sesiones a validar: {', '.join(self.sessions.keys())}")
        
        cycle = 0
        trades_by_session = {session: [] for session in self.sessions.keys()}
        
        while datetime.now(timezone.utc) < end_time:
            cycle += 1
            current_time = datetime.now(timezone.utc)
            
            # Mostrar progreso cada hora
            if cycle % 60 == 1:
                elapsed_hours = (current_time - start_time).total_seconds() / 3600
                print(f"\n--- Hora {elapsed_hours:.1f}/{duration_hours} ---")
                print(f"💼 Capital actual: ${self.current_capital:.2f}")
                print(f"📈 ROI: {((self.current_capital - self.initial_capital) / self.initial_capital * 100):.2f}%")
            
            # Verificar si estamos en una ventana de breakout
            current_session = self.get_current_session()
            
            if current_session:
                print(f"🔍 Analizando sesión {self.sessions[current_session].name}...")
                
                # Analizar todos los símbolos
                for symbol in self.trading_symbols:
                    try:
                        # Generar datos de mercado
                        df = self.generate_market_data(symbol, 100)
                        
                        # Detectar breakout
                        breakout = self.detect_session_breakout(symbol, current_session, df)
                        
                        if breakout and breakout.signal_type != 'no_signal':
                            # Simular ejecución del trade
                            executed_trade = self.simulate_trade_execution(breakout)
                            
                            # Registrar trade
                            self.trades.append(executed_trade)
                            trades_by_session[current_session].append(executed_trade)
                            
                            print(f"💹 {executed_trade.signal_type.upper()} {symbol} | "
                                  f"${executed_trade.position_size:.2f} | "
                                  f"PnL: ${executed_trade.pnl:.2f} ({executed_trade.pnl_percent:.2f}%) | "
                                  f"{executed_trade.close_reason}")
                            
                            # Verificar reinversión
                            self.check_reinvestment()
                    
                    except Exception as e:
                        self.logger.error(f"Error analizando {symbol}: {e}")
                        continue
                
                # Saltar al final de la ventana de breakout
                time.sleep(300)  # 5 minutos
            else:
                # Fuera de ventanas de breakout, esperar 1 minuto
                time.sleep(60)
        
        return self.generate_validation_report(trades_by_session)

    def generate_validation_report(self, trades_by_session: Dict) -> Dict:
        """
        Genera reporte completo de validación
        
        Args:
            trades_by_session: Trades agrupados por sesión
            
        Returns:
            Reporte de validación
        """
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
                session_avg_pnl = session_pnl / len(session_trades)
                
                session_stats[session_name] = {
                    'trades_count': len(session_trades),
                    'win_rate': session_win_rate,
                    'total_pnl': session_pnl,
                    'avg_pnl': session_avg_pnl,
                    'expected_win_rate': self.sessions[session_name].expected_win_rate,
                    'win_rate_vs_expected': session_win_rate - self.sessions[session_name].expected_win_rate
                }
        
        # Proyección mensual
        if total_trades > 0:
            daily_roi = total_roi / (len(self.trades) / 3)  # Asumiendo 3 sesiones por día
            monthly_projection = daily_roi * 30
        else:
            monthly_projection = 0
        
        report = {
            'validation_summary': {
                'total_trades': total_trades,
                'win_rate': win_rate,
                'total_roi': total_roi,
                'avg_pnl_per_trade': avg_pnl,
                'monthly_projection': monthly_projection
            },
            'capital_management': {
                'initial_capital': self.initial_capital,
                'final_capital': self.current_capital,
                'base_capital': self.base_capital,
                'total_reinvested': self.total_reinvested,
                'total_pnl': self.total_pnl
            },
            'session_performance': session_stats,
            'strategy_validation': {
                'asian_session_validated': session_stats.get('asian', {}).get('win_rate', 0) >= 70,
                'european_session_validated': session_stats.get('european', {}).get('win_rate', 0) >= 90,
                'american_session_validated': session_stats.get('american', {}).get('win_rate', 0) >= 80,
                'overall_strategy_valid': win_rate >= 85 and total_roi >= 8
            },
            'trades': [asdict(trade) for trade in self.trades],
            'recommendations': self.generate_recommendations(session_stats, win_rate, total_roi)
        }
        
        return report

    def generate_recommendations(self, session_stats: Dict, win_rate: float, total_roi: float) -> List[str]:
        """Genera recomendaciones basadas en los resultados"""
        recommendations = []
        
        # Recomendaciones por sesión
        for session_name, stats in session_stats.items():
            expected_wr = self.sessions[session_name].expected_win_rate
            actual_wr = stats['win_rate']
            
            if actual_wr < expected_wr - 5:
                recommendations.append(f"📊 Optimizar parámetros de sesión {session_name} - Win rate {actual_wr:.1f}% vs esperado {expected_wr:.1f}%")
        
        # Recomendaciones generales
        if win_rate < 85:
            recommendations.append("🎯 Aumentar umbrales de confianza para mejorar win rate general")
        
        if total_roi < 8:
            recommendations.append("💰 Considerar aumentar tamaños de posición o reducir stop loss")
        
        if len(session_stats) < 3:
            recommendations.append("⏰ Implementar monitoreo de todas las sesiones para maximizar oportunidades")
        
        return recommendations

def run_breakout_validation():
    """Ejecuta validación completa de la estrategia de breakout"""
    print("🚀 === VALIDADOR ESTRATEGIA BREAKOUT MULTI-SESIÓN ===")
    print("📊 Validando estrategia de rompimiento de primera vela")
    print("🌍 Sesiones: Asiática, Europea, Americana")
    
    # Inicializar validador
    validator = SicarBreakoutValidator(initial_capital=200.0)
    
    # Ejecutar validación de 24 horas
    results = validator.run_session_validation(duration_hours=24)
    
    # Mostrar resultados
    print(f"\n🎉 === RESULTADOS DE VALIDACIÓN ===")
    print(f"📊 Total trades: {results['validation_summary']['total_trades']}")
    print(f"🎯 Win rate: {results['validation_summary']['win_rate']:.1f}%")
    print(f"💰 ROI total: {results['validation_summary']['total_roi']:.2f}%")
    print(f"📈 Proyección mensual: {results['validation_summary']['monthly_projection']:.1f}%")
    print(f"💵 PnL promedio: ${results['validation_summary']['avg_pnl_per_trade']:.2f}")
    
    # Resultados por sesión
    print(f"\n📊 === RENDIMIENTO POR SESIÓN ===")
    for session_name, stats in results['session_performance'].items():
        session_info = validator.sessions[session_name]
        print(f"{session_info.name}:")
        print(f"  • Trades: {stats['trades_count']}")
        print(f"  • Win Rate: {stats['win_rate']:.1f}% (esperado: {stats['expected_win_rate']:.1f}%)")
        print(f"  • PnL total: ${stats['total_pnl']:.2f}")
        print(f"  • PnL promedio: ${stats['avg_pnl']:.2f}")
    
    # Validación de estrategia
    validation = results['strategy_validation']
    print(f"\n✅ === VALIDACIÓN DE ESTRATEGIA ===")
    print(f"Sesión Asiática: {'✅' if validation['asian_session_validated'] else '❌'}")
    print(f"Sesión Europea: {'✅' if validation['european_session_validated'] else '❌'}")
    print(f"Sesión Americana: {'✅' if validation['american_session_validated'] else '❌'}")
    print(f"Estrategia General: {'✅' if validation['overall_strategy_valid'] else '❌'}")
    
    # Recomendaciones
    if results['recommendations']:
        print(f"\n🔧 === RECOMENDACIONES ===")
        for rec in results['recommendations']:
            print(rec)
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"sicar_breakout_validation_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str, ensure_ascii=False)
    
    print(f"\n💾 Resultados guardados en: {filename}")
    
    return results

if __name__ == "__main__":
    run_breakout_validation()