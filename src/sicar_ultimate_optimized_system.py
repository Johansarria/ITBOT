#!/usr/bin/env python3
"""
Sistema SICAR Ultimate Optimizado
Integración completa de todos los componentes desarrollados
Objetivo: 15% ROI mensual sin apalancamiento
"""

import pandas as pd
import numpy as np
import logging
import time
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Importar todos los componentes desarrollados
from signal_quality_filters import SignalQualityFilters
from advanced_ml_engine import AdvancedMLEngine
from extensive_backtesting_engine import ExtensiveBacktestingEngine
from advanced_risk_management import AdvancedRiskManager
from realtime_monitoring_system import RealtimeMonitoringSystem

# APIs y datos
import yfinance as yf
import talib

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sicar_ultimate_optimized.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SicarUltimateOptimizedSystem:
    def __init__(self, initial_capital=10000):
        """Inicializar sistema SICAR ultimate optimizado"""
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = {}
        self.trades = []
        self.performance_metrics = {}
        
        # Inicializar componentes
        self.signal_filters = SignalQualityFilters()
        self.ml_engine = AdvancedMLEngine()
        self.backtesting_engine = ExtensiveBacktestingEngine()
        self.risk_manager = AdvancedRiskManager(initial_capital=initial_capital)
        self.monitor = RealtimeMonitoringSystem(update_interval=300)  # 5 minutos
        
        # Configuración de trading
        self.symbols = ['BTC-USD', 'ETH-USD', 'ADA-USD', 'SOL-USD', 'XRP-USD']
        self.timeframes = ['1h', '4h', '1d']
        
        # Parámetros optimizados
        self.params = {
            'min_signal_quality': 0.75,  # Calidad mínima de señal
            'ml_confidence_threshold': 0.65,  # Confianza ML mínima
            'max_positions': 3,  # Máximo posiciones simultáneas
            'position_size_base': 0.15,  # 15% del capital por posición base
            'stop_loss_pct': 0.03,  # 3% stop loss
            'take_profit_pct': 0.08,  # 8% take profit
            'trailing_stop_pct': 0.02,  # 2% trailing stop
            'market_score_threshold': 40,  # Score mínimo de mercado
            'volatility_adjustment': True,  # Ajustar por volatilidad
            'correlation_limit': 0.8,  # Límite de correlación entre posiciones
        }
        
        logger.info("Sistema SICAR Ultimate Optimizado inicializado")

    def fetch_market_data(self, symbol, period='3mo', interval='1h'):
        """Obtener datos de mercado con manejo de errores"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                logger.warning(f"No se obtuvieron datos para {symbol}")
                return None
            
            # Limpiar datos
            data = data.dropna()
            
            if len(data) < 50:
                logger.warning(f"Datos insuficientes para {symbol}: {len(data)} registros")
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"Error obteniendo datos para {symbol}: {e}")
            return None

    def calculate_advanced_indicators(self, data):
        """Calcular indicadores técnicos avanzados"""
        try:
            indicators = {}
            
            # Precios básicos
            high = data['High'].values
            low = data['Low'].values
            close = data['Close'].values
            volume = data['Volume'].values
            
            # Indicadores de tendencia
            indicators['sma_20'] = talib.SMA(close, timeperiod=20)
            indicators['sma_50'] = talib.SMA(close, timeperiod=50)
            indicators['ema_12'] = talib.EMA(close, timeperiod=12)
            indicators['ema_26'] = talib.EMA(close, timeperiod=26)
            
            # MACD
            macd, macd_signal, macd_hist = talib.MACD(close)
            indicators['macd'] = macd
            indicators['macd_signal'] = macd_signal
            indicators['macd_histogram'] = macd_hist
            
            # RSI
            indicators['rsi'] = talib.RSI(close, timeperiod=14)
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = talib.BBANDS(close)
            indicators['bb_upper'] = bb_upper
            indicators['bb_middle'] = bb_middle
            indicators['bb_lower'] = bb_lower
            indicators['bb_width'] = (bb_upper - bb_lower) / bb_middle
            
            # Stochastic
            slowk, slowd = talib.STOCH(high, low, close)
            indicators['stoch_k'] = slowk
            indicators['stoch_d'] = slowd
            
            # ADX
            indicators['adx'] = talib.ADX(high, low, close, timeperiod=14)
            
            # Williams %R
            indicators['williams_r'] = talib.WILLR(high, low, close, timeperiod=14)
            
            # CCI
            indicators['cci'] = talib.CCI(high, low, close, timeperiod=14)
            
            # Volume indicators
            indicators['obv'] = talib.OBV(close, volume)
            indicators['ad'] = talib.AD(high, low, close, volume)
            
            # Volatilidad
            indicators['atr'] = talib.ATR(high, low, close, timeperiod=14)
            indicators['volatility'] = pd.Series(close).rolling(20).std()
            
            # Momentum
            indicators['momentum'] = talib.MOM(close, timeperiod=10)
            indicators['roc'] = talib.ROC(close, timeperiod=10)
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculando indicadores: {e}")
            return {}

    def generate_momentum_signals(self, data, indicators):
        """Generar señales de momentum optimizadas"""
        try:
            signals = []
            
            for i in range(50, len(data)):
                signal_score = 0
                signal_strength = 0
                
                # Señales de tendencia
                if indicators['ema_12'][i] > indicators['ema_26'][i]:
                    signal_score += 1
                    if indicators['ema_12'][i-1] <= indicators['ema_26'][i-1]:
                        signal_strength += 2  # Cruce alcista
                
                if indicators['sma_20'][i] > indicators['sma_50'][i]:
                    signal_score += 1
                
                # MACD
                if indicators['macd'][i] > indicators['macd_signal'][i]:
                    signal_score += 1
                    if indicators['macd'][i-1] <= indicators['macd_signal'][i-1]:
                        signal_strength += 2  # Cruce MACD
                
                # RSI
                rsi = indicators['rsi'][i]
                if 30 < rsi < 70:
                    signal_score += 1
                elif rsi < 30:
                    signal_strength += 1  # Sobreventa
                
                # Bollinger Bands
                price = data['Close'].iloc[i]
                bb_position = (price - indicators['bb_lower'][i]) / (indicators['bb_upper'][i] - indicators['bb_lower'][i])
                if 0.2 < bb_position < 0.8:
                    signal_score += 1
                
                # ADX para fuerza de tendencia
                if indicators['adx'][i] > 25:
                    signal_strength += 1
                
                # Volumen
                volume_sma = pd.Series(data['Volume']).rolling(20).mean().iloc[i]
                if data['Volume'].iloc[i] > volume_sma * 1.2:
                    signal_strength += 1
                
                # Determinar señal
                total_score = signal_score + signal_strength
                
                if total_score >= 6:
                    signal_type = 'BUY'
                elif total_score <= 2:
                    signal_type = 'SELL'
                else:
                    signal_type = 'HOLD'
                
                signals.append({
                    'timestamp': data.index[i],
                    'signal': signal_type,
                    'score': total_score,
                    'strength': signal_strength,
                    'price': price
                })
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generando señales de momentum: {e}")
            return []

    def generate_ml_signals(self, data, indicators):
        """Generar señales usando ML avanzado"""
        try:
            # Preparar features para ML
            features_df = pd.DataFrame(index=data.index)
            
            # Agregar indicadores como features
            for name, values in indicators.items():
                if isinstance(values, np.ndarray):
                    features_df[name] = values
                elif hasattr(values, 'values'):
                    features_df[name] = values.values
            
            # Agregar precio y volumen
            features_df['close'] = data['Close'].values
            features_df['volume'] = data['Volume'].values
            features_df['high'] = data['High'].values
            features_df['low'] = data['Low'].values
            
            # Limpiar datos
            features_df = features_df.dropna()
            
            if len(features_df) < 100:
                logger.warning("Datos insuficientes para ML")
                return []
            
            # Generar señales ML
            ml_signals = self.ml_engine.generate_signals(features_df)
            
            return ml_signals
            
        except Exception as e:
            logger.error(f"Error generando señales ML: {e}")
            return []

    def combine_signals(self, momentum_signals, ml_signals, market_conditions):
        """Combinar señales de diferentes fuentes"""
        try:
            combined_signals = []
            
            # Obtener score de mercado
            market_score = market_conditions.get('market_score', 50)
            regime = market_conditions.get('regime', 'normal')
            
            # Ajustar pesos según condiciones de mercado
            if regime == 'crisis':
                momentum_weight = 0.3
                ml_weight = 0.7
            elif regime == 'euphoria':
                momentum_weight = 0.7
                ml_weight = 0.3
            else:
                momentum_weight = 0.5
                ml_weight = 0.5
            
            # Combinar señales por timestamp
            momentum_dict = {s['timestamp']: s for s in momentum_signals}
            ml_dict = {s['timestamp']: s for s in ml_signals}
            
            common_timestamps = set(momentum_dict.keys()) & set(ml_dict.keys())
            
            for timestamp in sorted(common_timestamps):
                momentum_signal = momentum_dict[timestamp]
                ml_signal = ml_dict[timestamp]
                
                # Calcular score combinado
                momentum_score = momentum_signal['score'] / 10  # Normalizar a 0-1
                ml_confidence = ml_signal.get('confidence', 0.5)
                
                combined_score = (momentum_score * momentum_weight + 
                                ml_confidence * ml_weight)
                
                # Ajustar por condiciones de mercado
                if market_score < self.params['market_score_threshold']:
                    combined_score *= 0.7  # Reducir agresividad en mal mercado
                
                # Determinar señal final
                if combined_score > 0.7:
                    final_signal = 'BUY'
                elif combined_score < 0.3:
                    final_signal = 'SELL'
                else:
                    final_signal = 'HOLD'
                
                combined_signals.append({
                    'timestamp': timestamp,
                    'signal': final_signal,
                    'confidence': combined_score,
                    'momentum_score': momentum_score,
                    'ml_confidence': ml_confidence,
                    'market_score': market_score,
                    'price': momentum_signal['price']
                })
            
            return combined_signals
            
        except Exception as e:
            logger.error(f"Error combinando señales: {e}")
            return []

    def filter_high_quality_signals(self, signals, data, indicators):
        """Filtrar señales de alta calidad"""
        try:
            filtered_signals = []
            
            for signal in signals:
                try:
                    # Obtener índice del timestamp
                    signal_idx = data.index.get_loc(signal['timestamp'])
                    
                    # Preparar datos para filtros
                    signal_data = {
                        'price': signal['price'],
                        'volume': data['Volume'].iloc[signal_idx],
                        'rsi': indicators['rsi'][signal_idx],
                        'atr': indicators['atr'][signal_idx],
                        'adx': indicators['adx'][signal_idx],
                        'bb_width': indicators['bb_width'][signal_idx],
                        'macd_histogram': indicators['macd_histogram'][signal_idx]
                    }
                    
                    # Aplicar filtros de calidad
                    quality_score = self.signal_filters.calculate_signal_quality(
                        signal_data, data.iloc[max(0, signal_idx-20):signal_idx+1]
                    )
                    
                    # Filtrar por calidad mínima
                    if quality_score >= self.params['min_signal_quality']:
                        signal['quality_score'] = quality_score
                        filtered_signals.append(signal)
                        
                except Exception as e:
                    logger.warning(f"Error filtrando señal: {e}")
                    continue
            
            logger.info(f"Señales filtradas: {len(filtered_signals)}/{len(signals)}")
            return filtered_signals
            
        except Exception as e:
            logger.error(f"Error en filtrado de señales: {e}")
            return signals

    def calculate_position_size(self, signal, symbol, market_conditions):
        """Calcular tamaño de posición optimizado"""
        try:
            # Tamaño base
            base_size = self.params['position_size_base']
            
            # Ajustar por confianza de señal
            confidence_multiplier = signal.get('confidence', 0.5)
            
            # Ajustar por calidad de señal
            quality_multiplier = signal.get('quality_score', 0.5)
            
            # Ajustar por condiciones de mercado
            market_score = market_conditions.get('market_score', 50)
            market_multiplier = market_score / 100
            
            # Ajustar por volatilidad
            volatility = market_conditions.get('factors', {}).get('volatility_index', 0.02)
            volatility_multiplier = max(0.5, 1 - (volatility * 10))
            
            # Calcular tamaño final
            position_size = (base_size * confidence_multiplier * 
                           quality_multiplier * market_multiplier * 
                           volatility_multiplier)
            
            # Límites
            position_size = max(0.05, min(0.25, position_size))
            
            # Verificar límites de riesgo
            position_value = self.current_capital * position_size
            
            if not self.risk_manager.check_position_limits(symbol, position_value):
                position_size *= 0.5  # Reducir si excede límites
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculando tamaño de posición: {e}")
            return 0.1

    def execute_trade(self, signal, symbol, position_size):
        """Ejecutar operación de trading"""
        try:
            trade_value = self.current_capital * position_size
            price = signal['price']
            
            if signal['signal'] == 'BUY':
                # Verificar si ya tenemos posición
                if symbol in self.positions:
                    logger.info(f"Ya existe posición en {symbol}")
                    return False
                
                # Verificar límites de riesgo
                if not self.risk_manager.check_risk_limits(symbol, trade_value, 'BUY'):
                    logger.warning(f"Operación rechazada por límites de riesgo: {symbol}")
                    return False
                
                # Ejecutar compra
                shares = trade_value / price
                
                self.positions[symbol] = {
                    'type': 'LONG',
                    'shares': shares,
                    'entry_price': price,
                    'entry_time': signal['timestamp'],
                    'stop_loss': price * (1 - self.params['stop_loss_pct']),
                    'take_profit': price * (1 + self.params['take_profit_pct']),
                    'trailing_stop': price * (1 - self.params['trailing_stop_pct']),
                    'signal_confidence': signal.get('confidence', 0.5)
                }
                
                self.current_capital -= trade_value
                
                # Registrar trade
                trade = {
                    'timestamp': signal['timestamp'],
                    'symbol': symbol,
                    'action': 'BUY',
                    'shares': shares,
                    'price': price,
                    'value': trade_value,
                    'confidence': signal.get('confidence', 0.5),
                    'quality': signal.get('quality_score', 0.5)
                }
                
                self.trades.append(trade)
                logger.info(f"Compra ejecutada: {symbol} - {shares:.4f} shares @ ${price:.2f}")
                
                return True
                
            elif signal['signal'] == 'SELL' and symbol in self.positions:
                # Vender posición existente
                position = self.positions[symbol]
                shares = position['shares']
                entry_price = position['entry_price']
                
                # Calcular ganancia/pérdida
                profit_loss = (price - entry_price) * shares
                profit_pct = (price - entry_price) / entry_price
                
                # Actualizar capital
                self.current_capital += price * shares
                
                # Registrar trade de venta
                trade = {
                    'timestamp': signal['timestamp'],
                    'symbol': symbol,
                    'action': 'SELL',
                    'shares': shares,
                    'price': price,
                    'value': price * shares,
                    'profit_loss': profit_loss,
                    'profit_pct': profit_pct,
                    'hold_time': signal['timestamp'] - position['entry_time']
                }
                
                self.trades.append(trade)
                
                # Eliminar posición
                del self.positions[symbol]
                
                logger.info(f"Venta ejecutada: {symbol} - P&L: ${profit_loss:.2f} ({profit_pct:.2%})")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error ejecutando trade: {e}")
            return False

    def check_stop_loss_take_profit(self, current_prices):
        """Verificar stop loss y take profit"""
        try:
            positions_to_close = []
            
            for symbol, position in self.positions.items():
                if symbol not in current_prices:
                    continue
                
                current_price = current_prices[symbol]
                entry_price = position['entry_price']
                
                # Actualizar trailing stop
                if current_price > entry_price * 1.02:  # Si hay ganancia > 2%
                    new_trailing = current_price * (1 - self.params['trailing_stop_pct'])
                    position['trailing_stop'] = max(position['trailing_stop'], new_trailing)
                
                # Verificar condiciones de cierre
                should_close = False
                close_reason = ""
                
                if current_price <= position['stop_loss']:
                    should_close = True
                    close_reason = "Stop Loss"
                elif current_price >= position['take_profit']:
                    should_close = True
                    close_reason = "Take Profit"
                elif current_price <= position['trailing_stop']:
                    should_close = True
                    close_reason = "Trailing Stop"
                
                if should_close:
                    positions_to_close.append((symbol, current_price, close_reason))
            
            # Cerrar posiciones
            for symbol, price, reason in positions_to_close:
                self.close_position(symbol, price, reason)
            
        except Exception as e:
            logger.error(f"Error verificando stop loss/take profit: {e}")

    def close_position(self, symbol, price, reason):
        """Cerrar posición"""
        try:
            if symbol not in self.positions:
                return
            
            position = self.positions[symbol]
            shares = position['shares']
            entry_price = position['entry_price']
            
            # Calcular ganancia/pérdida
            profit_loss = (price - entry_price) * shares
            profit_pct = (price - entry_price) / entry_price
            
            # Actualizar capital
            self.current_capital += price * shares
            
            # Registrar trade
            trade = {
                'timestamp': datetime.now(),
                'symbol': symbol,
                'action': 'SELL',
                'shares': shares,
                'price': price,
                'value': price * shares,
                'profit_loss': profit_loss,
                'profit_pct': profit_pct,
                'close_reason': reason
            }
            
            self.trades.append(trade)
            
            # Eliminar posición
            del self.positions[symbol]
            
            logger.info(f"Posición cerrada: {symbol} - {reason} - P&L: ${profit_loss:.2f} ({profit_pct:.2%})")
            
        except Exception as e:
            logger.error(f"Error cerrando posición: {e}")

    def run_trading_session(self, duration_hours=24):
        """Ejecutar sesión de trading"""
        try:
            logger.info(f"Iniciando sesión de trading por {duration_hours} horas")
            
            # Iniciar monitoreo
            self.monitor.start_monitoring()
            
            start_time = datetime.now()
            end_time = start_time + timedelta(hours=duration_hours)
            
            while datetime.now() < end_time:
                try:
                    # Obtener condiciones de mercado
                    market_conditions = self.monitor.get_market_conditions()
                    
                    # Verificar cada símbolo
                    for symbol in self.symbols:
                        try:
                            # Obtener datos
                            data = self.fetch_market_data(symbol, period='3mo', interval='1h')
                            if data is None:
                                continue
                            
                            # Calcular indicadores
                            indicators = self.calculate_advanced_indicators(data)
                            if not indicators:
                                continue
                            
                            # Generar señales
                            momentum_signals = self.generate_momentum_signals(data, indicators)
                            ml_signals = self.generate_ml_signals(data, indicators)
                            
                            # Combinar señales
                            combined_signals = self.combine_signals(
                                momentum_signals, ml_signals, 
                                market_conditions.get('external_factors', {})
                            )
                            
                            # Filtrar señales de alta calidad
                            quality_signals = self.filter_high_quality_signals(
                                combined_signals, data, indicators
                            )
                            
                            # Procesar señales más recientes
                            if quality_signals:
                                latest_signal = quality_signals[-1]
                                
                                # Verificar si la señal es reciente (última hora)
                                if (datetime.now() - latest_signal['timestamp']).total_seconds() < 3600:
                                    
                                    # Calcular tamaño de posición
                                    position_size = self.calculate_position_size(
                                        latest_signal, symbol, 
                                        market_conditions.get('external_factors', {})
                                    )
                                    
                                    # Ejecutar trade si es apropiado
                                    if position_size > 0.05:
                                        self.execute_trade(latest_signal, symbol, position_size)
                            
                        except Exception as e:
                            logger.error(f"Error procesando {symbol}: {e}")
                            continue
                    
                    # Verificar stop loss/take profit
                    current_prices = {}
                    for symbol in self.positions.keys():
                        try:
                            ticker = yf.Ticker(symbol)
                            current_prices[symbol] = ticker.info.get('regularMarketPrice', 0)
                        except:
                            continue
                    
                    self.check_stop_loss_take_profit(current_prices)
                    
                    # Actualizar métricas de performance
                    self.update_performance_metrics()
                    
                    # Esperar antes de la siguiente iteración
                    time.sleep(300)  # 5 minutos
                    
                except Exception as e:
                    logger.error(f"Error en iteración de trading: {e}")
                    time.sleep(60)
            
            # Detener monitoreo
            self.monitor.stop_monitoring()
            
            # Cerrar todas las posiciones al final
            self.close_all_positions()
            
            logger.info("Sesión de trading completada")
            
        except Exception as e:
            logger.error(f"Error en sesión de trading: {e}")

    def close_all_positions(self):
        """Cerrar todas las posiciones abiertas"""
        try:
            for symbol in list(self.positions.keys()):
                try:
                    ticker = yf.Ticker(symbol)
                    current_price = ticker.info.get('regularMarketPrice', 0)
                    if current_price > 0:
                        self.close_position(symbol, current_price, "End of Session")
                except Exception as e:
                    logger.error(f"Error cerrando posición {symbol}: {e}")
                    
        except Exception as e:
            logger.error(f"Error cerrando todas las posiciones: {e}")

    def update_performance_metrics(self):
        """Actualizar métricas de performance"""
        try:
            if not self.trades:
                return
            
            # Calcular métricas básicas
            total_trades = len([t for t in self.trades if t['action'] == 'SELL'])
            
            if total_trades == 0:
                return
            
            profits = [t.get('profit_loss', 0) for t in self.trades if t['action'] == 'SELL']
            winning_trades = [p for p in profits if p > 0]
            
            # Métricas de performance
            total_return = sum(profits)
            win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
            avg_profit = np.mean(profits) if profits else 0
            
            # ROI
            current_portfolio_value = self.current_capital + sum(
                pos['shares'] * self.get_current_price(symbol) 
                for symbol, pos in self.positions.items()
            )
            
            total_roi = (current_portfolio_value - self.initial_capital) / self.initial_capital
            
            self.performance_metrics = {
                'total_trades': total_trades,
                'win_rate': win_rate,
                'total_return': total_return,
                'total_roi': total_roi,
                'avg_profit': avg_profit,
                'current_capital': self.current_capital,
                'portfolio_value': current_portfolio_value,
                'active_positions': len(self.positions)
            }
            
        except Exception as e:
            logger.error(f"Error actualizando métricas: {e}")

    def get_current_price(self, symbol):
        """Obtener precio actual de un símbolo"""
        try:
            ticker = yf.Ticker(symbol)
            return ticker.info.get('regularMarketPrice', 0)
        except:
            return 0

    def run_backtest(self, start_date='2024-01-01', end_date='2024-12-01'):
        """Ejecutar backtest completo"""
        try:
            logger.info("Iniciando backtest del sistema optimizado...")
            
            # Preparar datos para todos los símbolos
            data_dict = {}
            for symbol in self.symbols:
                data = self.fetch_market_data(symbol, period='1y', interval='1d')
                if data is not None:
                    data_dict[symbol] = data
            
            if not data_dict:
                logger.error("No se pudieron obtener datos para el backtest")
                return {}
            
            # Usar el motor de backtesting extenso
            results = self.backtesting_engine.run_backtest(
                data_dict=data_dict,
                strategy_func=self.generate_backtest_signals,
                start_date=start_date,
                end_date=end_date
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error en backtest: {e}")
            return {}

    def generate_backtest_signals(self, data):
        """Generar señales para backtest"""
        try:
            # Calcular indicadores
            indicators = self.calculate_advanced_indicators(data)
            
            # Generar señales de momentum
            momentum_signals = self.generate_momentum_signals(data, indicators)
            
            # Simular condiciones de mercado (para backtest)
            market_conditions = {'market_score': 60, 'regime': 'normal'}
            
            # Generar señales ML (simplificado para backtest)
            ml_signals = []
            for signal in momentum_signals:
                ml_signals.append({
                    'timestamp': signal['timestamp'],
                    'confidence': 0.6,  # Confianza simulada
                    'signal': signal['signal']
                })
            
            # Combinar señales
            combined_signals = self.combine_signals(momentum_signals, ml_signals, market_conditions)
            
            # Filtrar por calidad (simplificado)
            quality_signals = [s for s in combined_signals if s.get('confidence', 0) > 0.6]
            
            return quality_signals
            
        except Exception as e:
            logger.error(f"Error generando señales para backtest: {e}")
            return []

    def generate_report(self):
        """Generar reporte de performance"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'initial_capital': self.initial_capital,
                'performance_metrics': self.performance_metrics,
                'active_positions': len(self.positions),
                'total_trades': len(self.trades),
                'positions': self.positions,
                'recent_trades': self.trades[-10:] if self.trades else []
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generando reporte: {e}")
            return {}

def main():
    """Función principal de prueba"""
    try:
        # Crear sistema
        system = SicarUltimateOptimizedSystem(initial_capital=10000)
        
        # Ejecutar backtest
        print("Ejecutando backtest...")
        backtest_results = system.run_backtest()
        
        if backtest_results:
            print(f"Resultados del backtest:")
            print(f"ROI Total: {backtest_results.get('total_roi', 0):.2%}")
            print(f"Win Rate: {backtest_results.get('win_rate', 0):.2%}")
            print(f"Total Trades: {backtest_results.get('total_trades', 0)}")
            print(f"Sharpe Ratio: {backtest_results.get('sharpe_ratio', 0):.2f}")
        
        # Generar reporte
        report = system.generate_report()
        print(f"Reporte generado: {len(report)} elementos")
        
        print("Prueba del sistema completada")
        
    except Exception as e:
        print(f"Error en prueba: {e}")

if __name__ == "__main__":
    main()