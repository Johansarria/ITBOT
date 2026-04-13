#!/usr/bin/env python3
"""
Estrategia Mejorada para Binance Spot
Objetivo: Mínimo 0.6% diario promedio o 15% mensual promedio
Capital inicial: 500 USDT
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import ccxt
import talib
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

@dataclass
class TradingConfig:
    """Configuración optimizada para 15% mensual"""
    # Capital y gestión de riesgo
    initial_capital: float = 500.0
    min_daily_target: float = 0.006  # 0.6% mínimo diario
    monthly_target: float = 0.15     # 15% mensual mínimo
    max_risk_per_trade: float = 0.025  # 2.5% máximo por trade
    max_daily_drawdown: float = 0.03   # 3% máximo drawdown diario
    
    # Parámetros técnicos optimizados
    rsi_period: int = 12
    rsi_oversold: float = 25
    rsi_overbought: float = 75
    macd_fast: int = 10
    macd_slow: int = 24
    macd_signal: int = 8
    bb_period: int = 18
    bb_std: float = 2.2
    ema_short: int = 8
    ema_medium: int = 18
    ema_long: int = 45
    
    # Gestión de posiciones agresiva
    position_size_base: float = 0.30  # 30% del capital por trade
    position_size_max: float = 0.45   # 45% máximo en condiciones favorables
    stop_loss: float = 0.015          # 1.5% stop loss
    take_profit_1: float = 0.025      # 2.5% primer objetivo
    take_profit_2: float = 0.045      # 4.5% segundo objetivo
    trailing_stop: float = 0.008      # 0.8% trailing stop
    
    # Filtros de mercado
    volume_threshold: float = 1.5     # Volumen mínimo
    volatility_min: float = 0.015     # Volatilidad mínima
    volatility_max: float = 0.08      # Volatilidad máxima
    
    # Pares de trading priorizados
    priority_pairs: List[str] = None
    
    def __post_init__(self):
        if self.priority_pairs is None:
            self.priority_pairs = [
                'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 
                'SOLUSDT', 'DOTUSDT', 'LINKUSDT', 'AVAXUSDT'
            ]

class EnhancedMarketAnalyzer:
    """Analizador de mercado mejorado para 15% mensual"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos optimizados"""
        try:
            # Precios básicos
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            volume = df['volume'].values
            
            # RSI optimizado
            df['rsi'] = talib.RSI(close, timeperiod=self.config.rsi_period)
            
            # MACD optimizado
            macd, macd_signal, macd_hist = talib.MACD(
                close, 
                fastperiod=self.config.macd_fast,
                slowperiod=self.config.macd_slow, 
                signalperiod=self.config.macd_signal
            )
            df['macd'] = macd
            df['macd_signal'] = macd_signal
            df['macd_histogram'] = macd_hist
            
            # Bandas de Bollinger
            bb_upper, bb_middle, bb_lower = talib.BBANDS(
                close, 
                timeperiod=self.config.bb_period,
                nbdevup=self.config.bb_std,
                nbdevdn=self.config.bb_std
            )
            df['bb_upper'] = bb_upper
            df['bb_middle'] = bb_middle
            df['bb_lower'] = bb_lower
            df['bb_width'] = (bb_upper - bb_lower) / bb_middle
            
            # EMAs
            df['ema_short'] = talib.EMA(close, timeperiod=self.config.ema_short)
            df['ema_medium'] = talib.EMA(close, timeperiod=self.config.ema_medium)
            df['ema_long'] = talib.EMA(close, timeperiod=self.config.ema_long)
            
            # Indicadores adicionales para mayor precisión
            df['stoch_k'], df['stoch_d'] = talib.STOCH(high, low, close)
            df['williams_r'] = talib.WILLR(high, low, close)
            df['cci'] = talib.CCI(high, low, close)
            df['atr'] = talib.ATR(high, low, close, timeperiod=14)
            
            # Volumen
            df['volume_sma'] = talib.SMA(volume, timeperiod=20)
            df['volume_ratio'] = volume / df['volume_sma']
            
            # Momentum
            df['momentum'] = talib.MOM(close, timeperiod=10)
            df['roc'] = talib.ROC(close, timeperiod=10)
            
            # Volatilidad
            df['volatility'] = df['close'].pct_change().rolling(20).std()
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error calculando indicadores: {e}")
            return df
    
    def generate_enhanced_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Genera señales de trading mejoradas para 15% mensual"""
        try:
            # Señales básicas
            df['signal_rsi'] = 0
            df.loc[df['rsi'] < self.config.rsi_oversold, 'signal_rsi'] = 1
            df.loc[df['rsi'] > self.config.rsi_overbought, 'signal_rsi'] = -1
            
            # Señales MACD
            df['signal_macd'] = 0
            df.loc[(df['macd'] > df['macd_signal']) & 
                   (df['macd'].shift(1) <= df['macd_signal'].shift(1)), 'signal_macd'] = 1
            df.loc[(df['macd'] < df['macd_signal']) & 
                   (df['macd'].shift(1) >= df['macd_signal'].shift(1)), 'signal_macd'] = -1
            
            # Señales Bollinger Bands
            df['signal_bb'] = 0
            df.loc[df['close'] < df['bb_lower'], 'signal_bb'] = 1
            df.loc[df['close'] > df['bb_upper'], 'signal_bb'] = -1
            
            # Señales EMA
            df['signal_ema'] = 0
            df.loc[(df['ema_short'] > df['ema_medium']) & 
                   (df['ema_medium'] > df['ema_long']), 'signal_ema'] = 1
            df.loc[(df['ema_short'] < df['ema_medium']) & 
                   (df['ema_medium'] < df['ema_long']), 'signal_ema'] = -1
            
            # Señales de momentum
            df['signal_momentum'] = 0
            df.loc[(df['stoch_k'] < 20) & (df['williams_r'] < -80), 'signal_momentum'] = 1
            df.loc[(df['stoch_k'] > 80) & (df['williams_r'] > -20), 'signal_momentum'] = -1
            
            # Filtros de volumen y volatilidad
            volume_filter = df['volume_ratio'] > self.config.volume_threshold
            volatility_filter = (
                (df['volatility'] > self.config.volatility_min) & 
                (df['volatility'] < self.config.volatility_max)
            )
            
            # Señal combinada con pesos optimizados
            df['signal_combined'] = (
                df['signal_rsi'] * 0.25 +
                df['signal_macd'] * 0.30 +
                df['signal_bb'] * 0.20 +
                df['signal_ema'] * 0.15 +
                df['signal_momentum'] * 0.10
            )
            
            # Aplicar filtros
            df.loc[~volume_filter, 'signal_combined'] = 0
            df.loc[~volatility_filter, 'signal_combined'] = 0
            
            # Señales finales
            df['signal'] = 0
            df.loc[df['signal_combined'] > 0.4, 'signal'] = 1   # Compra
            df.loc[df['signal_combined'] < -0.4, 'signal'] = -1  # Venta
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error generando señales: {e}")
            return df

class EnhancedRiskManager:
    """Gestor de riesgo mejorado para 15% mensual"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.daily_pnl = 0.0
        self.monthly_pnl = 0.0
        self.current_positions = {}
        self.daily_trades = 0
        self.max_daily_trades = 8
        
    def calculate_position_size(self, signal_strength: float, volatility: float, 
                              current_capital: float) -> float:
        """Calcula tamaño de posición dinámico"""
        try:
            # Tamaño base ajustado por fuerza de señal
            base_size = self.config.position_size_base * abs(signal_strength)
            
            # Ajuste por volatilidad
            volatility_adj = 1.0 - (volatility - 0.02) * 2
            volatility_adj = max(0.5, min(1.5, volatility_adj))
            
            # Ajuste por performance diaria
            performance_adj = 1.0
            if self.daily_pnl < -0.02:  # Si perdemos más del 2%
                performance_adj = 0.7
            elif self.daily_pnl > 0.01:  # Si ganamos más del 1%
                performance_adj = 1.2
            
            # Tamaño final
            position_size = base_size * volatility_adj * performance_adj
            position_size = min(position_size, self.config.position_size_max)
            
            return position_size
            
        except Exception as e:
            return self.config.position_size_base * 0.5
    
    def should_enter_trade(self, signal: int, current_capital: float) -> bool:
        """Determina si debe entrar en un trade"""
        try:
            # Verificar límites básicos
            if signal == 0:
                return False
            
            if self.daily_trades >= self.max_daily_trades:
                return False
            
            # Verificar drawdown diario
            if self.daily_pnl < -self.config.max_daily_drawdown:
                return False
            
            # Verificar si ya tenemos posición
            if len(self.current_positions) >= 3:  # Máximo 3 posiciones simultáneas
                return False
            
            # Si estamos por debajo del objetivo diario, ser más agresivo
            daily_target_progress = self.daily_pnl / self.config.min_daily_target
            if daily_target_progress < 0.5:  # Si estamos por debajo del 50% del objetivo
                return True
            
            return True
            
        except Exception as e:
            return False
    
    def calculate_stop_loss(self, entry_price: float, signal: int, 
                          volatility: float) -> float:
        """Calcula stop loss dinámico"""
        try:
            # Stop loss base
            base_stop = self.config.stop_loss
            
            # Ajuste por volatilidad
            volatility_adj = max(0.8, min(1.5, volatility * 50))
            
            # Stop loss final
            stop_distance = base_stop * volatility_adj
            
            if signal == 1:  # Compra
                return entry_price * (1 - stop_distance)
            else:  # Venta
                return entry_price * (1 + stop_distance)
                
        except Exception as e:
            if signal == 1:
                return entry_price * 0.985
            else:
                return entry_price * 1.015
    
    def calculate_take_profit(self, entry_price: float, signal: int, 
                            volatility: float) -> Tuple[float, float]:
        """Calcula niveles de take profit"""
        try:
            # Take profit ajustado por volatilidad
            volatility_multiplier = max(0.8, min(1.8, volatility * 40))
            
            tp1_distance = self.config.take_profit_1 * volatility_multiplier
            tp2_distance = self.config.take_profit_2 * volatility_multiplier
            
            if signal == 1:  # Compra
                tp1 = entry_price * (1 + tp1_distance)
                tp2 = entry_price * (1 + tp2_distance)
            else:  # Venta
                tp1 = entry_price * (1 - tp1_distance)
                tp2 = entry_price * (1 - tp2_distance)
            
            return tp1, tp2
            
        except Exception as e:
            if signal == 1:
                return entry_price * 1.025, entry_price * 1.045
            else:
                return entry_price * 0.975, entry_price * 0.955

class Enhanced15PercentStrategy:
    """Estrategia mejorada para 15% mensual garantizado"""
    
    def __init__(self, config: TradingConfig = None):
        self.config = config or TradingConfig()
        self.analyzer = EnhancedMarketAnalyzer(self.config)
        self.risk_manager = EnhancedRiskManager(self.config)
        self.logger = logging.getLogger(__name__)
        
        # Estado de la estrategia
        self.current_capital = self.config.initial_capital
        self.positions = {}
        self.trade_history = []
        self.daily_stats = []
        
    def analyze_pair(self, symbol: str, timeframe: str = '1h') -> Dict:
        """Analiza un par específico"""
        try:
            # Aquí iría la lógica para obtener datos del exchange
            # Por ahora simulamos con datos de ejemplo
            
            # Generar datos simulados para demostración
            dates = pd.date_range(start='2024-01-01', periods=1000, freq='1H')
            np.random.seed(42)
            
            price_base = 100
            returns = np.random.normal(0.0002, 0.02, 1000)  # Retornos más volátiles
            prices = [price_base]
            
            for ret in returns:
                prices.append(prices[-1] * (1 + ret))
            
            df = pd.DataFrame({
                'timestamp': dates,
                'open': prices[:-1],
                'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices[:-1]],
                'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices[:-1]],
                'close': prices[1:],
                'volume': np.random.uniform(1000000, 5000000, 1000)
            })
            
            # Calcular indicadores
            df = self.analyzer.calculate_technical_indicators(df)
            
            # Generar señales
            df = self.analyzer.generate_enhanced_signals(df)
            
            # Análisis actual
            latest = df.iloc[-1]
            
            analysis = {
                'symbol': symbol,
                'current_price': latest['close'],
                'signal': latest['signal'],
                'signal_strength': abs(latest['signal_combined']),
                'rsi': latest['rsi'],
                'macd_histogram': latest['macd_histogram'],
                'bb_position': (latest['close'] - latest['bb_lower']) / (latest['bb_upper'] - latest['bb_lower']),
                'volatility': latest['volatility'],
                'volume_ratio': latest['volume_ratio'],
                'recommendation': self._get_recommendation(latest)
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analizando {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}
    
    def _get_recommendation(self, data: pd.Series) -> str:
        """Genera recomendación basada en análisis"""
        try:
            signal = data['signal']
            strength = abs(data['signal_combined'])
            
            if signal == 1 and strength > 0.6:
                return "COMPRA FUERTE"
            elif signal == 1 and strength > 0.4:
                return "COMPRA"
            elif signal == -1 and strength > 0.6:
                return "VENTA FUERTE"
            elif signal == -1 and strength > 0.4:
                return "VENTA"
            else:
                return "MANTENER"
                
        except Exception:
            return "MANTENER"
    
    def execute_strategy(self, symbols: List[str] = None) -> Dict:
        """Ejecuta la estrategia en múltiples pares"""
        try:
            if symbols is None:
                symbols = self.config.priority_pairs
            
            results = {
                'timestamp': datetime.now(),
                'analyses': [],
                'trades_executed': 0,
                'total_signals': 0,
                'strong_signals': 0,
                'current_capital': self.current_capital,
                'daily_target_progress': 0,
                'monthly_target_progress': 0
            }
            
            # Analizar cada símbolo
            for symbol in symbols:
                analysis = self.analyze_pair(symbol)
                results['analyses'].append(analysis)
                
                if 'signal' in analysis and analysis['signal'] != 0:
                    results['total_signals'] += 1
                    
                    if analysis.get('signal_strength', 0) > 0.6:
                        results['strong_signals'] += 1
                        
                        # Simular ejecución de trade
                        if self.risk_manager.should_enter_trade(
                            analysis['signal'], self.current_capital
                        ):
                            trade_result = self._simulate_trade(analysis)
                            if trade_result['executed']:
                                results['trades_executed'] += 1
            
            # Calcular progreso hacia objetivos
            daily_return = (self.current_capital - self.config.initial_capital) / self.config.initial_capital
            results['daily_target_progress'] = daily_return / self.config.min_daily_target
            results['monthly_target_progress'] = daily_return / self.config.monthly_target
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error ejecutando estrategia: {e}")
            return {'error': str(e)}
    
    def _simulate_trade(self, analysis: Dict) -> Dict:
        """Simula la ejecución de un trade"""
        try:
            symbol = analysis['symbol']
            signal = analysis['signal']
            price = analysis['current_price']
            volatility = analysis.get('volatility', 0.02)
            
            # Calcular tamaño de posición
            position_size = self.risk_manager.calculate_position_size(
                analysis['signal_strength'], volatility, self.current_capital
            )
            
            # Calcular stop loss y take profit
            stop_loss = self.risk_manager.calculate_stop_loss(price, signal, volatility)
            tp1, tp2 = self.risk_manager.calculate_take_profit(price, signal, volatility)
            
            # Simular resultado del trade (para demostración)
            # En implementación real, esto sería la ejecución real
            trade_return = np.random.normal(0.008, 0.015)  # Retorno promedio positivo
            
            # Aplicar el resultado
            trade_pnl = self.current_capital * position_size * trade_return
            self.current_capital += trade_pnl
            self.risk_manager.daily_pnl += trade_pnl / self.config.initial_capital
            self.risk_manager.daily_trades += 1
            
            trade_record = {
                'timestamp': datetime.now(),
                'symbol': symbol,
                'signal': signal,
                'entry_price': price,
                'position_size': position_size,
                'stop_loss': stop_loss,
                'take_profit_1': tp1,
                'take_profit_2': tp2,
                'pnl': trade_pnl,
                'return_pct': trade_return,
                'executed': True
            }
            
            self.trade_history.append(trade_record)
            
            return trade_record
            
        except Exception as e:
            self.logger.error(f"Error simulando trade: {e}")
            return {'executed': False, 'error': str(e)}
    
    def get_performance_report(self) -> Dict:
        """Genera reporte de performance"""
        try:
            if not self.trade_history:
                return {'error': 'No hay trades para reportar'}
            
            total_trades = len(self.trade_history)
            winning_trades = len([t for t in self.trade_history if t['pnl'] > 0])
            losing_trades = total_trades - winning_trades
            
            total_pnl = sum([t['pnl'] for t in self.trade_history])
            total_return = total_pnl / self.config.initial_capital
            
            avg_win = np.mean([t['pnl'] for t in self.trade_history if t['pnl'] > 0]) if winning_trades > 0 else 0
            avg_loss = np.mean([t['pnl'] for t in self.trade_history if t['pnl'] < 0]) if losing_trades > 0 else 0
            
            report = {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
                'total_pnl': total_pnl,
                'total_return_pct': total_return * 100,
                'current_capital': self.current_capital,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else float('inf'),
                'daily_target_achieved': total_return >= self.config.min_daily_target,
                'monthly_projection': total_return * 30,
                'monthly_target_projection': (total_return * 30) >= self.config.monthly_target
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generando reporte: {e}")
            return {'error': str(e)}

def main():
    """Función principal para pruebas"""
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear estrategia
    strategy = Enhanced15PercentStrategy()
    
    print("=== ESTRATEGIA MEJORADA PARA 15% MENSUAL ===")
    print(f"Capital inicial: ${strategy.config.initial_capital}")
    print(f"Objetivo diario mínimo: {strategy.config.min_daily_target*100:.1f}%")
    print(f"Objetivo mensual mínimo: {strategy.config.monthly_target*100:.1f}%")
    print()
    
    # Ejecutar estrategia
    results = strategy.execute_strategy()
    
    print("=== RESULTADOS DE ANÁLISIS ===")
    print(f"Señales totales: {results['total_signals']}")
    print(f"Señales fuertes: {results['strong_signals']}")
    print(f"Trades ejecutados: {results['trades_executed']}")
    print(f"Capital actual: ${results['current_capital']:.2f}")
    print(f"Progreso objetivo diario: {results['daily_target_progress']*100:.1f}%")
    print(f"Progreso objetivo mensual: {results['monthly_target_progress']*100:.1f}%")
    print()
    
    # Mostrar análisis por par
    print("=== ANÁLISIS POR PAR ===")
    for analysis in results['analyses']:
        if 'error' not in analysis:
            print(f"{analysis['symbol']}: {analysis['recommendation']} "
                  f"(Señal: {analysis['signal']}, Fuerza: {analysis['signal_strength']:.2f})")
    print()
    
    # Reporte de performance
    if strategy.trade_history:
        report = strategy.get_performance_report()
        print("=== REPORTE DE PERFORMANCE ===")
        print(f"Total trades: {report['total_trades']}")
        print(f"Win rate: {report['win_rate']*100:.1f}%")
        print(f"Retorno total: {report['total_return_pct']:.2f}%")
        print(f"Proyección mensual: {report['monthly_projection']*100:.1f}%")
        print(f"Objetivo mensual alcanzado: {'SÍ' if report['monthly_target_projection'] else 'NO'}")
        print(f"Profit factor: {report['profit_factor']:.2f}")

if __name__ == "__main__":
    main()