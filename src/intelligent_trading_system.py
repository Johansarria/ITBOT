# /src/intelligent_trading_system.py
"""
Sistema de Trading Inteligente - Objetivo: 15% ROI mensual con menor frecuencia
Enfoque en calidad sobre cantidad de operaciones.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
import sys
import os

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from robust_data_fetcher import RobustDataFetcher
from multi_symbol_portfolio import MultiSymbolPortfolio

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('intelligent_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IntelligentTradingSystem:
    """Sistema de trading inteligente con enfoque en calidad sobre cantidad."""
    
    def __init__(self, initial_capital: float = 500.0):
        """
        Inicializa el sistema de trading inteligente.
        
        Args:
            initial_capital: Capital inicial
        """
        self.initial_capital = initial_capital
        self.symbols = ['BTCUSDT', 'ETHUSDT']
        
        # Fees de Binance
        self.maker_fee = 0.001  # 0.1%
        self.taker_fee = 0.001  # 0.1%
        
        # Configuración inteligente
        self.min_signal_strength = 0.7  # Señales muy fuertes solamente
        self.min_confidence = 0.8  # Alta confianza requerida
        self.max_daily_trades = 2  # Máximo 2 operaciones por día
        self.min_trade_interval_hours = 6  # Mínimo 6 horas entre operaciones
        self.position_size_pct = 0.4  # 40% del capital por posición
        
        # Gestión de riesgo
        self.stop_loss_pct = 0.03  # 3% stop loss
        self.take_profit_pct = 0.08  # 8% take profit
        self.trailing_stop_pct = 0.02  # 2% trailing stop
        
        # Métricas
        self.total_fees_paid = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.last_trade_times = {}
        self.daily_trade_count = {}
        
    def calculate_premium_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula indicadores técnicos premium para señales de alta calidad.
        
        Args:
            data: DataFrame con datos OHLCV
            
        Returns:
            DataFrame con indicadores premium
        """
        df = data.copy()
        
        try:
            # Ichimoku Cloud
            high_9 = df['High'].rolling(9).max()
            low_9 = df['Low'].rolling(9).min()
            df['Tenkan'] = (high_9 + low_9) / 2
            
            high_26 = df['High'].rolling(26).max()
            low_26 = df['Low'].rolling(26).min()
            df['Kijun'] = (high_26 + low_26) / 2
            
            df['Senkou_A'] = ((df['Tenkan'] + df['Kijun']) / 2).shift(26)
            
            high_52 = df['High'].rolling(52).max()
            low_52 = df['Low'].rolling(52).min()
            df['Senkou_B'] = ((high_52 + low_52) / 2).shift(26)
            
            df['Chikou'] = df['Close'].shift(-26)
            
            # Posición respecto a la nube
            df['Above_Cloud'] = (df['Close'] > df['Senkou_A']) & (df['Close'] > df['Senkou_B'])
            df['Below_Cloud'] = (df['Close'] < df['Senkou_A']) & (df['Close'] < df['Senkou_B'])
            df['In_Cloud'] = ~df['Above_Cloud'] & ~df['Below_Cloud']
            
            # RSI Divergence
            df['RSI'] = self._calculate_rsi(df['Close'], 14)
            df['RSI_MA'] = df['RSI'].rolling(5).mean()
            
            # MACD con histograma
            ema_12 = df['Close'].ewm(span=12).mean()
            ema_26 = df['Close'].ewm(span=26).mean()
            df['MACD'] = ema_12 - ema_26
            df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
            df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
            
            # Volume Profile
            df['Volume_MA'] = df['Volume'].rolling(20).mean()
            df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
            
            # Volatility Squeeze
            bb_std = df['Close'].rolling(20).std()
            keltner_atr = self._calculate_atr(df, 20)
            df['Squeeze'] = bb_std < (keltner_atr * 1.5)
            
            # Support/Resistance
            df['Pivot'] = (df['High'] + df['Low'] + df['Close']) / 3
            df['R1'] = 2 * df['Pivot'] - df['Low']
            df['S1'] = 2 * df['Pivot'] - df['High']
            
            # Trend Strength
            df['ADX'] = self._calculate_adx(df, 14)
            
            # Price Action
            df['Doji'] = abs(df['Open'] - df['Close']) < (df['High'] - df['Low']) * 0.1
            df['Hammer'] = (df['Close'] > df['Open']) & ((df['Close'] - df['Open']) < (df['High'] - df['Low']) * 0.3)
            df['Shooting_Star'] = (df['Open'] > df['Close']) & ((df['Open'] - df['Close']) < (df['High'] - df['Low']) * 0.3)
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculando indicadores premium: {e}")
            return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula RSI."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcula Average True Range."""
        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift())
        low_close = np.abs(data['Low'] - data['Close'].shift())
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        return true_range.rolling(period).mean()
    
    def _calculate_adx(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcula Average Directional Index."""
        high_diff = data['High'].diff()
        low_diff = data['Low'].diff()
        
        plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
        minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)
        
        atr = self._calculate_atr(data, period)
        plus_di = 100 * pd.Series(plus_dm).rolling(period).mean() / atr
        minus_di = 100 * pd.Series(minus_dm).rolling(period).mean() / atr
        
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        return dx.rolling(period).mean()
    
    def generate_intelligent_signal(self, data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Genera señales inteligentes de alta calidad.
        
        Args:
            data: DataFrame con datos e indicadores
            symbol: Símbolo del activo
            
        Returns:
            Diccionario con información de la señal
        """
        try:
            if len(data) < 100:
                return self._empty_signal(data)
            
            latest = data.iloc[-1]
            prev = data.iloc[-2]
            
            # Verificar restricciones de tiempo
            current_time = data.index[-1]
            if not self._can_trade(symbol, current_time):
                return self._empty_signal(data)
            
            # Análisis de múltiples factores
            factors = self._analyze_trading_factors(data, latest, prev)
            
            # Calcular señal compuesta
            signal_strength = self._calculate_composite_signal(factors)
            confidence = self._calculate_signal_confidence(factors, data)
            
            # Filtros de calidad
            if abs(signal_strength) < self.min_signal_strength or confidence < self.min_confidence:
                return self._empty_signal(data)
            
            # Verificar condiciones del mercado
            market_condition = self._assess_market_condition(factors)
            if market_condition == 'unfavorable':
                return self._empty_signal(data)
            
            return {
                'signal': signal_strength,
                'confidence': confidence,
                'factors': factors,
                'market_condition': market_condition,
                'price': latest['Close'],
                'timestamp': current_time,
                'quality_score': confidence * abs(signal_strength)
            }
            
        except Exception as e:
            logger.error(f"Error generando señal inteligente para {symbol}: {e}")
            return self._empty_signal(data)
    
    def _can_trade(self, symbol: str, current_time: datetime) -> bool:
        """Verifica si se puede realizar una operación."""
        # Verificar límite diario
        date_key = current_time.date()
        if self.daily_trade_count.get(date_key, 0) >= self.max_daily_trades:
            return False
        
        # Verificar intervalo mínimo
        if symbol in self.last_trade_times:
            time_diff = current_time - self.last_trade_times[symbol]
            if time_diff < timedelta(hours=self.min_trade_interval_hours):
                return False
        
        return True
    
    def _analyze_trading_factors(self, data: pd.DataFrame, latest: pd.Series, prev: pd.Series) -> Dict[str, float]:
        """Analiza múltiples factores de trading."""
        factors = {}
        
        try:
            # Factor Ichimoku
            if latest.get('Above_Cloud', False):
                factors['ichimoku'] = 0.8
            elif latest.get('Below_Cloud', False):
                factors['ichimoku'] = -0.8
            else:
                factors['ichimoku'] = 0.0
            
            # Factor RSI con divergencia
            rsi = latest.get('RSI', 50)
            if rsi < 25:
                factors['rsi'] = 0.9
            elif rsi > 75:
                factors['rsi'] = -0.9
            elif rsi < 35:
                factors['rsi'] = 0.6
            elif rsi > 65:
                factors['rsi'] = -0.6
            else:
                factors['rsi'] = 0.0
            
            # Factor MACD
            macd = latest.get('MACD', 0)
            macd_signal = latest.get('MACD_Signal', 0)
            macd_hist = latest.get('MACD_Histogram', 0)
            prev_macd_hist = prev.get('MACD_Histogram', 0)
            
            if macd > macd_signal and macd_hist > prev_macd_hist:
                factors['macd'] = 0.7
            elif macd < macd_signal and macd_hist < prev_macd_hist:
                factors['macd'] = -0.7
            else:
                factors['macd'] = 0.0
            
            # Factor volumen
            volume_ratio = latest.get('Volume_Ratio', 1)
            if volume_ratio > 1.5:
                factors['volume'] = 0.5
            elif volume_ratio < 0.7:
                factors['volume'] = -0.3
            else:
                factors['volume'] = 0.0
            
            # Factor ADX (fuerza de tendencia)
            adx = latest.get('ADX', 20)
            if adx > 40:
                factors['trend_strength'] = 0.6
            elif adx < 20:
                factors['trend_strength'] = -0.4
            else:
                factors['trend_strength'] = 0.0
            
            # Factor squeeze
            if latest.get('Squeeze', False):
                factors['squeeze'] = 0.4  # Preparación para movimiento
            else:
                factors['squeeze'] = 0.0
            
            # Factor soporte/resistencia
            price = latest['Close']
            pivot = latest.get('Pivot', price)
            r1 = latest.get('R1', price * 1.01)
            s1 = latest.get('S1', price * 0.99)
            
            if price > r1:
                factors['support_resistance'] = -0.5  # Cerca de resistencia
            elif price < s1:
                factors['support_resistance'] = 0.5  # Cerca de soporte
            else:
                factors['support_resistance'] = 0.0
            
            return factors
            
        except Exception as e:
            logger.error(f"Error analizando factores: {e}")
            return {}
    
    def _calculate_composite_signal(self, factors: Dict[str, float]) -> float:
        """Calcula señal compuesta con pesos."""
        if not factors:
            return 0.0
        
        weights = {
            'ichimoku': 0.25,
            'rsi': 0.20,
            'macd': 0.20,
            'volume': 0.15,
            'trend_strength': 0.10,
            'squeeze': 0.05,
            'support_resistance': 0.05
        }
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for factor, value in factors.items():
            if factor in weights:
                weighted_sum += value * weights[factor]
                total_weight += weights[factor]
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _calculate_signal_confidence(self, factors: Dict[str, float], data: pd.DataFrame) -> float:
        """Calcula la confianza de la señal."""
        if not factors:
            return 0.0
        
        # Confianza basada en consenso de factores
        positive_factors = sum(1 for v in factors.values() if v > 0.3)
        negative_factors = sum(1 for v in factors.values() if v < -0.3)
        total_factors = len(factors)
        
        # Consenso direccional
        if positive_factors > negative_factors:
            consensus = positive_factors / total_factors
        elif negative_factors > positive_factors:
            consensus = negative_factors / total_factors
        else:
            consensus = 0.0
        
        # Ajuste por volatilidad
        recent_volatility = data['Close'].pct_change().tail(20).std()
        volatility_adjustment = min(1.0, 0.02 / recent_volatility) if recent_volatility > 0 else 0.5
        
        return min(0.95, consensus * volatility_adjustment)
    
    def _assess_market_condition(self, factors: Dict[str, float]) -> str:
        """Evalúa las condiciones del mercado."""
        strong_signals = sum(1 for v in factors.values() if abs(v) > 0.6)
        total_signals = len(factors)
        
        if strong_signals >= total_signals * 0.6:
            return 'favorable'
        elif strong_signals >= total_signals * 0.3:
            return 'neutral'
        else:
            return 'unfavorable'
    
    def _empty_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Retorna una señal vacía."""
        return {
            'signal': 0.0,
            'confidence': 0.0,
            'factors': {},
            'market_condition': 'unfavorable',
            'price': data['Close'].iloc[-1] if not data.empty else 0.0,
            'timestamp': data.index[-1] if not data.empty else datetime.now(),
            'quality_score': 0.0
        }
    
    def calculate_intelligent_position_size(self, signal_data: Dict, available_capital: float) -> float:
        """
        Calcula el tamaño de posición inteligente.
        
        Args:
            signal_data: Datos de la señal
            available_capital: Capital disponible
            
        Returns:
            Tamaño de posición
        """
        # Tamaño base
        base_size = available_capital * self.position_size_pct
        
        # Ajuste por calidad de señal
        quality_multiplier = signal_data['quality_score']
        
        # Tamaño final
        position_value = base_size * quality_multiplier
        
        # Convertir a cantidad
        price = signal_data['price']
        quantity = position_value / price
        
        return quantity
    
    def run_intelligent_backtest(self) -> pd.DataFrame:
        """
        Ejecuta el backtesting inteligente.
        
        Returns:
            DataFrame con resultados
        """
        try:
            logger.info("Iniciando backtesting inteligente (objetivo: 15% mensual)")
            
            # Inicializar componentes
            fetcher = RobustDataFetcher()
            
            # Obtener datos (4 horas para swing trading)
            all_data = {}
            for symbol in self.symbols:
                logger.info(f"Obteniendo datos para {symbol}")
                data = fetcher.get_market_data(symbol, interval='4h', limit=500)
                if data is not None and not data.empty:
                    data_with_indicators = self.calculate_premium_indicators(data)
                    all_data[symbol] = data_with_indicators
                    logger.info(f"{symbol}: {len(data)} periodos obtenidos")
                else:
                    logger.error(f"No se pudieron obtener datos para {symbol}")
                    return pd.DataFrame()
            
            if not all_data:
                logger.error("No se pudieron obtener datos")
                return pd.DataFrame()
            
            # Inicializar portfolio
            portfolio = MultiSymbolPortfolio(
                symbols=list(all_data.keys()),
                capital_allocation={'BTCUSDT': 0.5, 'ETHUSDT': 0.5}
            )
            
            results = []
            min_length = min(len(data) for data in all_data.values())
            
            logger.info(f"Ejecutando backtest en {min_length} periodos")
            
            for i in range(100, min_length):
                period_results = []
                
                for symbol in all_data.keys():
                    try:
                        historical_data = all_data[symbol].iloc[:i+1]
                        
                        # Generar señal inteligente
                        signal_data = self.generate_intelligent_signal(historical_data, symbol)
                        
                        # Ejecutar operación si cumple criterios
                        if abs(signal_data['signal']) >= self.min_signal_strength and signal_data['confidence'] >= self.min_confidence:
                            
                            available_capital = portfolio.positions[symbol].available_capital
                            position_size = self.calculate_intelligent_position_size(signal_data, available_capital)
                            
                            trade_value = position_size * signal_data['price']
                            
                            if signal_data['signal'] > 0:
                                # Operación LONG
                                fees = self.calculate_fees(trade_value)
                                self.total_fees_paid += fees
                                
                                portfolio.open_position(
                                    symbol=symbol,
                                    size=position_size,
                                    entry_price=signal_data['price']
                                )
                                
                                self.total_trades += 1
                                self._update_trade_tracking(symbol, signal_data['timestamp'])
                                
                                logger.info(f"{symbol}: LONG ${trade_value:.2f} @ ${signal_data['price']:.2f} (Calidad: {signal_data['quality_score']:.2f}, Fee: ${fees:.2f})")
                                
                            else:
                                # Operación SHORT
                                fees = self.calculate_fees(trade_value)
                                self.total_fees_paid += fees
                                
                                portfolio.open_position(
                                    symbol=symbol,
                                    size=-position_size,
                                    entry_price=signal_data['price']
                                )
                                
                                self.total_trades += 1
                                self._update_trade_tracking(symbol, signal_data['timestamp'])
                                
                                logger.info(f"{symbol}: SHORT ${trade_value:.2f} @ ${signal_data['price']:.2f} (Calidad: {signal_data['quality_score']:.2f}, Fee: ${fees:.2f})")
                        
                        # Gestión inteligente de posiciones
                        if portfolio.is_position_open(symbol):
                            self._manage_existing_position(portfolio, symbol, signal_data)
                        
                        # Actualizar precios
                        portfolio.update_prices({symbol: signal_data['price']})
                        
                        # Guardar resultados
                        portfolio_summary = portfolio.get_portfolio_summary()
                        
                        position_status = 'none'
                        position_size_current = 0
                        if portfolio.is_position_open(symbol):
                            pos = portfolio.positions[symbol]
                            if hasattr(pos, 'size'):
                                position_status = 'long' if pos.size > 0 else 'short'
                                position_size_current = abs(pos.size)
                        
                        period_result = {
                            'timestamp': signal_data['timestamp'],
                            'symbol': symbol,
                            'price': signal_data['price'],
                            'signal': signal_data['signal'],
                            'confidence': signal_data['confidence'],
                            'quality_score': signal_data['quality_score'],
                            'market_condition': signal_data['market_condition'],
                            'portfolio_value': portfolio_summary['total_value'],
                            'total_pnl': portfolio_summary['total_pnl'],
                            'return_pct': portfolio_summary['total_return'],
                            'position': position_status,
                            'position_size': position_size_current,
                            'fees_paid': self.total_fees_paid,
                            'total_trades': self.total_trades
                        }
                        
                        period_results.append(period_result)
                        
                    except Exception as e:
                        logger.error(f"❌ Error procesando {symbol} en periodo {i}: {e}")
                        continue
                
                results.extend(period_results)
                
                # Log progreso
                if i % 25 == 0:
                    portfolio_summary = portfolio.get_portfolio_summary()
                    logger.info(f"Periodo {i}/{min_length} - Valor: ${portfolio_summary['total_value']:.2f} - Operaciones: {self.total_trades}")
            
            # Crear DataFrame de resultados
            results_df = pd.DataFrame(results)
            
            if not results_df.empty:
                # Guardar resultados
                results_df.to_csv('intelligent_trading_results.csv', index=False)
                
                # Calcular métricas finales
                final_summary = portfolio.get_portfolio_summary()
                net_pnl = final_summary['total_pnl'] - self.total_fees_paid
                net_return = net_pnl / self.initial_capital
                
                # Calcular ROI mensual
                duration_days = (results_df['timestamp'].max() - results_df['timestamp'].min()).days
                duration_months = duration_days / 30.44
                monthly_roi = (((final_summary['total_value'] - self.total_fees_paid) / self.initial_capital) ** (1/duration_months) - 1) if duration_months > 0 else 0
                
                # Calcular win rate
                trades_with_pnl = results_df[results_df['total_trades'] > results_df['total_trades'].shift(1)]
                if not trades_with_pnl.empty:
                    profitable_trades = len(trades_with_pnl[trades_with_pnl['total_pnl'] > trades_with_pnl['total_pnl'].shift(1)])
                    win_rate = profitable_trades / len(trades_with_pnl) if len(trades_with_pnl) > 0 else 0
                else:
                    win_rate = 0
                
                logger.info("=" * 70)
                logger.info("RESUMEN FINAL - TRADING INTELIGENTE")
                logger.info("=" * 70)
                logger.info(f"Capital inicial: ${self.initial_capital:.2f}")
                logger.info(f"Valor final: ${final_summary['total_value']:.2f}")
                logger.info(f"PnL bruto: ${final_summary['total_pnl']:.2f}")
                logger.info(f"Fees totales: ${self.total_fees_paid:.2f}")
                logger.info(f"PnL neto: ${net_pnl:.2f}")
                logger.info(f"Retorno neto: {net_return*100:.2f}%")
                logger.info(f"ROI mensual: {monthly_roi*100:.2f}%")
                logger.info(f"Total operaciones: {self.total_trades}")
                logger.info(f"Win rate: {win_rate*100:.1f}%")
                logger.info(f"Drawdown maximo: {final_summary['max_drawdown']:.2f}%")
                
                # Verificar objetivo
                target_roi = 0.15  # 15% mensual
                if monthly_roi >= target_roi:
                    logger.info(f"OBJETIVO ALCANZADO! ROI mensual: {monthly_roi*100:.2f}% >= {target_roi*100:.0f}%")
                else:
                    gap = target_roi - monthly_roi
                    logger.info(f"Objetivo no alcanzado. Gap: {gap*100:.2f}% para llegar al {target_roi*100:.0f}%")
                    
                    # Sugerencias de mejora
                    logger.info("SUGERENCIAS DE MEJORA:")
                    if self.total_trades < 10:
                        logger.info("   - Considerar reducir umbrales para más operaciones")
                    if win_rate < 0.6:
                        logger.info("   - Mejorar filtros de calidad de señales")
                    if final_summary['total_pnl'] != 0 and self.total_fees_paid / abs(final_summary['total_pnl']) > 0.3:
                        logger.info("   - Optimizar frecuencia de trading para reducir fees")
                
            return results_df
            
        except Exception as e:
            logger.error(f"❌ Error en backtesting inteligente: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def _update_trade_tracking(self, symbol: str, timestamp: datetime):
        """Actualiza el seguimiento de operaciones."""
        self.last_trade_times[symbol] = timestamp
        date_key = timestamp.date()
        self.daily_trade_count[date_key] = self.daily_trade_count.get(date_key, 0) + 1
    
    def _manage_existing_position(self, portfolio, symbol: str, signal_data: Dict):
        """Gestiona posiciones existentes con stop-loss y take-profit dinámicos."""
        try:
            position = portfolio.positions[symbol]
            if not hasattr(position, 'size') or not hasattr(position, 'entry_price'):
                return
            
            current_price = signal_data['price']
            entry_price = position.entry_price
            
            if position.size > 0:  # Posición LONG
                pnl_pct = (current_price - entry_price) / entry_price
                
                # Take profit
                if pnl_pct >= self.take_profit_pct:
                    self._close_position(portfolio, symbol, current_price, "Take Profit")
                # Stop loss
                elif pnl_pct <= -self.stop_loss_pct:
                    self._close_position(portfolio, symbol, current_price, "Stop Loss")
                # Trailing stop
                elif pnl_pct > 0.02 and signal_data['signal'] < -0.5:
                    self._close_position(portfolio, symbol, current_price, "Trailing Stop")
                    
            else:  # Posición SHORT
                pnl_pct = (entry_price - current_price) / entry_price
                
                # Take profit
                if pnl_pct >= self.take_profit_pct:
                    self._close_position(portfolio, symbol, current_price, "Take Profit")
                # Stop loss
                elif pnl_pct <= -self.stop_loss_pct:
                    self._close_position(portfolio, symbol, current_price, "Stop Loss")
                # Trailing stop
                elif pnl_pct > 0.02 and signal_data['signal'] > 0.5:
                    self._close_position(portfolio, symbol, current_price, "Trailing Stop")
                    
        except Exception as e:
            logger.error(f"Error gestionando posición {symbol}: {e}")
    
    def _close_position(self, portfolio, symbol: str, price: float, reason: str):
        """Cierra una posición."""
        try:
            position = portfolio.positions[symbol]
            close_value = abs(position.size) * price
            fees = self.calculate_fees(close_value)
            self.total_fees_paid += fees
            
            portfolio.close_position(symbol, price)
            logger.info(f"{symbol}: Cerrando posicion @ ${price:.2f} ({reason}) - Fee: ${fees:.2f}")
            
        except Exception as e:
            logger.error(f"Error cerrando posición {symbol}: {e}")
    
    def calculate_fees(self, trade_value: float, is_maker: bool = False) -> float:
        """Calcula los fees de una operación."""
        fee_rate = self.maker_fee if is_maker else self.taker_fee
        return trade_value * fee_rate

def main():
    """Función principal."""
    system = IntelligentTradingSystem(initial_capital=500.0)
    results = system.run_intelligent_backtest()
    
    if not results.empty:
        print(f"\nBacktesting inteligente completado!")
        print(f"Resultados guardados en: intelligent_trading_results.csv")
        print(f"Log guardado en: intelligent_trading.log")
    else:
        print("Error en el backtesting inteligente")

if __name__ == "__main__":
    main()