import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import warnings
import talib
from robust_data_fetcher import RobustDataFetcher
import time
import os
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('advanced_multi_pairs_sicar.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AdvancedMultiPairsSicarSystem:
    def __init__(self):
        self.initial_capital = 500
        self.current_capital = self.initial_capital
        self.leverage = 1.0  # Sin apalancamiento para SICAR
        self.max_risk_per_trade = 0.02  # 2% riesgo máximo por operación
        self.target_monthly_roi = 0.15  # 15% mensual
        
        # Múltiples pares de criptomonedas para diversificación
        self.trading_pairs = [
            'BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 
            'LINKUSDT', 'LTCUSDT', 'XRPUSDT', 'SOLUSDT'
        ]
        
        # Configuración de timeframes múltiples
        self.timeframes = ['4h', '1d']  # 4h para señales rápidas, 1d para tendencia
        
        # Parámetros optimizados para cada par
        self.pair_configs = {
            'BTCUSDT': {'volatility_factor': 1.0, 'momentum_threshold': 0.6},
            'ETHUSDT': {'volatility_factor': 1.2, 'momentum_threshold': 0.65},
            'ADAUSDT': {'volatility_factor': 1.5, 'momentum_threshold': 0.7},
            'DOTUSDT': {'volatility_factor': 1.4, 'momentum_threshold': 0.7},
            'LINKUSDT': {'volatility_factor': 1.3, 'momentum_threshold': 0.68},
            'LTCUSDT': {'volatility_factor': 1.1, 'momentum_threshold': 0.62},
            'XRPUSDT': {'volatility_factor': 1.6, 'momentum_threshold': 0.72},
            'SOLUSDT': {'volatility_factor': 1.8, 'momentum_threshold': 0.75}
        }
        
        self.positions = {}
        self.trades_history = []
        self.portfolio_history = []
        self.fees_paid = 0
        self.total_trades = 0
        
        # Métricas de rendimiento
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0
        
        # Configuración SICAR avanzada
        self.sicar_confidence_threshold = 0.4  # Reducido para más operaciones
        self.sicar_quality_threshold = 0.3     # Reducido para más oportunidades
        self.correlation_threshold = 0.7       # Para evitar sobreexposición
        
    def fetch_multi_pair_data(self):
        """Obtiene datos para múltiples pares de criptomonedas"""
        try:
            logger.info("Obteniendo datos para múltiples pares de criptomonedas...")
            fetcher = RobustDataFetcher()
            
            all_data = {}
            
            for pair in self.trading_pairs:
                try:
                    logger.info(f"Obteniendo datos para {pair}...")
                    
                    # Obtener datos para ambos timeframes
                    data_4h = fetcher.get_market_data(pair, '4h', limit=500)
                    data_1d = fetcher.get_market_data(pair, '1d', limit=200)
                    
                    if data_4h is not None and not data_4h.empty and data_1d is not None and not data_1d.empty:
                        # Normalizar nombres de columnas
                        for df in [data_4h, data_1d]:
                            # Convertir columnas a minúsculas
                            df.columns = df.columns.str.lower()
                            
                            # Manejar el índice timestamp
                            if df.index.name == 'timestamp' or 'timestamp' in str(df.index.name).lower():
                                df.reset_index(inplace=True)
                                df.columns = df.columns.str.lower()
                            elif 'timestamp' not in df.columns:
                                df.reset_index(inplace=True)
                                if 'date' in df.columns:
                                    df.rename(columns={'date': 'timestamp'}, inplace=True)
                                elif df.columns[0] in ['index', 'datetime']:
                                    df.rename(columns={df.columns[0]: 'timestamp'}, inplace=True)
                            
                            # Asegurar que tenemos las columnas necesarias
                            if 'volume' not in df.columns:
                                df['volume'] = 1000000  # Volumen dummy
                            if 'open' not in df.columns and 'Open' in df.columns:
                                df['open'] = df['Open']
                            if 'high' not in df.columns and 'High' in df.columns:
                                df['high'] = df['High']
                            if 'low' not in df.columns and 'Low' in df.columns:
                                df['low'] = df['Low']
                            if 'close' not in df.columns and 'Close' in df.columns:
                                df['close'] = df['Close']
                        
                        all_data[pair] = {
                            '4h': data_4h,
                            '1d': data_1d
                        }
                        logger.info(f"✅ Datos obtenidos para {pair}: 4h={len(data_4h)}, 1d={len(data_1d)}")
                    else:
                        logger.warning(f"⚠️ No se pudieron obtener datos para {pair}")
                        
                except Exception as e:
                    logger.error(f"❌ Error obteniendo datos para {pair}: {e}")
                    continue
                    
                # Pequeña pausa para evitar rate limiting
                time.sleep(0.1)
            
            logger.info(f"Total pares con datos: {len(all_data)}/{len(self.trading_pairs)}")
            return all_data
            
        except Exception as e:
            logger.error(f"Error obteniendo datos multi-pares: {e}")
            return {}
    
    def calculate_advanced_indicators(self, df, pair):
        """Calcula indicadores técnicos avanzados específicos por par"""
        try:
            if df is None or df.empty or len(df) < 50:
                return None
            
            df = df.copy()
            
            # Precios básicos
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            volume = df['volume'].values
            
            # Indicadores de tendencia
            df['sma_20'] = talib.SMA(close, timeperiod=20)
            df['sma_50'] = talib.SMA(close, timeperiod=50)
            df['ema_12'] = talib.EMA(close, timeperiod=12)
            df['ema_26'] = talib.EMA(close, timeperiod=26)
            
            # MACD
            df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(close)
            
            # RSI con múltiples períodos
            df['rsi_14'] = talib.RSI(close, timeperiod=14)
            df['rsi_21'] = talib.RSI(close, timeperiod=21)
            
            # Bollinger Bands
            df['bb_upper'], df['bb_middle'], df['bb_lower'] = talib.BBANDS(close)
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
            df['bb_position'] = (close - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            
            # Indicadores de momentum
            df['momentum'] = talib.MOM(close, timeperiod=10)
            df['roc'] = talib.ROC(close, timeperiod=10)
            df['cci'] = talib.CCI(high, low, close, timeperiod=14)
            
            # Indicadores de volatilidad
            df['atr'] = talib.ATR(high, low, close, timeperiod=14)
            df['volatility'] = df['close'].rolling(20).std()
            
            # Indicadores de volumen
            df['obv'] = talib.OBV(close, volume)
            df['ad'] = talib.AD(high, low, close, volume)
            
            # Patrones de velas (algunos seleccionados)
            df['doji'] = talib.CDLDOJI(df['open'], high, low, close)
            df['hammer'] = talib.CDLHAMMER(df['open'], high, low, close)
            df['engulfing'] = talib.CDLENGULFING(df['open'], high, low, close)
            
            # Indicadores personalizados específicos por par
            config = self.pair_configs.get(pair, {'volatility_factor': 1.0, 'momentum_threshold': 0.6})
            
            # Factor de volatilidad ajustado por par
            df['adjusted_volatility'] = df['volatility'] * config['volatility_factor']
            
            # Momentum ajustado
            df['momentum_strength'] = np.where(
                np.abs(df['momentum']) > df['momentum'].rolling(20).std() * config['momentum_threshold'],
                1, 0
            )
            
            # Señal de tendencia multi-timeframe (simulada)
            df['trend_strength'] = np.where(
                (df['sma_20'] > df['sma_50']) & (df['ema_12'] > df['ema_26']), 1,
                np.where((df['sma_20'] < df['sma_50']) & (df['ema_12'] < df['ema_26']), -1, 0)
            )
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculando indicadores para {pair}: {e}")
            return None
    
    def generate_sicar_signals(self, data_4h, data_1d, pair):
        """Genera señales SICAR avanzadas combinando múltiples timeframes"""
        try:
            if data_4h is None or data_1d is None or data_4h.empty or data_1d.empty:
                return 0, 0, 0
            
            # Obtener últimos valores de ambos timeframes
            latest_4h = data_4h.iloc[-1]
            latest_1d = data_1d.iloc[-1]
            
            # Señales de 4h (operaciones rápidas)
            signal_4h = 0
            confidence_4h = 0
            
            # Condiciones alcistas 4h
            bullish_4h = (
                latest_4h['rsi_14'] > 30 and latest_4h['rsi_14'] < 70 and
                latest_4h['macd'] > latest_4h['macd_signal'] and
                latest_4h['close'] > latest_4h['sma_20'] and
                latest_4h['bb_position'] > 0.2 and latest_4h['bb_position'] < 0.8 and
                latest_4h['momentum_strength'] > 0
            )
            
            # Condiciones bajistas 4h
            bearish_4h = (
                latest_4h['rsi_14'] > 30 and latest_4h['rsi_14'] < 70 and
                latest_4h['macd'] < latest_4h['macd_signal'] and
                latest_4h['close'] < latest_4h['sma_20'] and
                latest_4h['bb_position'] > 0.2 and latest_4h['bb_position'] < 0.8 and
                latest_4h['momentum_strength'] > 0
            )
            
            # Señales de 1d (tendencia principal)
            signal_1d = 0
            confidence_1d = 0
            
            # Condiciones alcistas 1d
            bullish_1d = (
                latest_1d['trend_strength'] > 0 and
                latest_1d['rsi_14'] > 40 and latest_1d['rsi_14'] < 80 and
                latest_1d['close'] > latest_1d['sma_50']
            )
            
            # Condiciones bajistas 1d
            bearish_1d = (
                latest_1d['trend_strength'] < 0 and
                latest_1d['rsi_14'] > 20 and latest_1d['rsi_14'] < 60 and
                latest_1d['close'] < latest_1d['sma_50']
            )
            
            # Combinar señales de ambos timeframes
            if bullish_4h and bullish_1d:
                signal_4h = 1
                confidence_4h = 0.8
            elif bullish_4h and latest_1d['trend_strength'] >= 0:
                signal_4h = 1
                confidence_4h = 0.6
            elif bearish_4h and bearish_1d:
                signal_4h = -1
                confidence_4h = 0.8
            elif bearish_4h and latest_1d['trend_strength'] <= 0:
                signal_4h = -1
                confidence_4h = 0.6
            
            # Calcular calidad de la señal
            quality = 0
            if signal_4h != 0:
                # Factores de calidad
                volatility_factor = min(latest_4h['bb_width'], 0.1) / 0.1
                momentum_factor = min(abs(latest_4h['momentum']) / latest_4h['adjusted_volatility'], 2) / 2
                volume_factor = min(latest_4h['volume'] / data_4h['volume'].rolling(20).mean().iloc[-1], 2) / 2
                
                quality = (volatility_factor + momentum_factor + volume_factor) / 3
                quality = max(0, min(1, quality))
            
            # Ajustar por configuración específica del par
            config = self.pair_configs.get(pair, {'momentum_threshold': 0.6})
            if confidence_4h < config['momentum_threshold']:
                signal_4h = 0
                confidence_4h = 0
                quality = 0
            
            return signal_4h, confidence_4h, quality
            
        except Exception as e:
            logger.error(f"Error generando señales SICAR para {pair}: {e}")
            return 0, 0, 0
    
    def calculate_position_size(self, pair, signal_strength, current_price):
        """Calcula el tamaño de posición con gestión de riesgo avanzada"""
        try:
            # Capital disponible
            available_capital = self.current_capital * 0.8  # Usar máximo 80% del capital
            
            # Ajustar por número de pares activos para diversificación
            active_pairs = len([p for p in self.positions.values() if p['size'] != 0])
            max_pairs = min(len(self.trading_pairs), 4)  # Máximo 4 pares simultáneos
            
            if active_pairs >= max_pairs:
                return 0  # No abrir más posiciones
            
            # Tamaño base por par
            base_size = available_capital / max_pairs
            
            # Ajustar por fuerza de la señal
            signal_multiplier = signal_strength
            
            # Ajustar por volatilidad del par
            config = self.pair_configs.get(pair, {'volatility_factor': 1.0})
            volatility_adjustment = 1.0 / config['volatility_factor']
            
            # Calcular tamaño final
            position_value = base_size * signal_multiplier * volatility_adjustment
            
            # Aplicar apalancamiento
            leveraged_value = position_value * self.leverage
            
            # Calcular cantidad de tokens
            position_size = leveraged_value / current_price
            
            # Límite de riesgo por operación
            max_position_value = self.current_capital * self.max_risk_per_trade * 10  # Con apalancamiento
            if leveraged_value > max_position_value:
                position_size = (max_position_value / current_price)
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculando tamaño de posición para {pair}: {e}")
            return 0
    
    def calculate_dynamic_stops(self, pair, entry_price, signal_direction, atr_value):
        """Calcula stop-loss y take-profit dinámicos"""
        try:
            config = self.pair_configs.get(pair, {'volatility_factor': 1.0})
            
            # Stop-loss basado en ATR y volatilidad del par
            atr_multiplier = 1.5 * config['volatility_factor']
            stop_distance = atr_value * atr_multiplier
            
            # Take-profit con ratio 1:2.5 (mejorado)
            tp_ratio = 2.5
            tp_distance = stop_distance * tp_ratio
            
            if signal_direction > 0:  # Long
                stop_loss = entry_price - stop_distance
                take_profit = entry_price + tp_distance
            else:  # Short
                stop_loss = entry_price + stop_distance
                take_profit = entry_price - tp_distance
            
            return stop_loss, take_profit
            
        except Exception as e:
            logger.error(f"Error calculando stops dinámicos para {pair}: {e}")
            return entry_price * 0.95, entry_price * 1.05
    
    def check_correlation_risk(self, new_pair, signal_direction):
        """Verifica riesgo de correlación entre pares"""
        try:
            # Pares altamente correlacionados
            correlations = {
                'BTCUSDT': ['ETHUSDT'],
                'ETHUSDT': ['BTCUSDT'],
                'ADAUSDT': ['DOTUSDT'],
                'DOTUSDT': ['ADAUSDT'],
                'LINKUSDT': ['ETHUSDT'],
                'XRPUSDT': ['ADAUSDT'],
                'SOLUSDT': ['ETHUSDT']
            }
            
            correlated_pairs = correlations.get(new_pair, [])
            
            # Verificar si ya tenemos posiciones en pares correlacionados
            for pair in correlated_pairs:
                if pair in self.positions and self.positions[pair]['size'] != 0:
                    existing_direction = 1 if self.positions[pair]['size'] > 0 else -1
                    if existing_direction == signal_direction:
                        # Reducir exposición si es la misma dirección
                        return 0.5
                    else:
                        # Permitir cobertura si es dirección opuesta
                        return 1.0
            
            return 1.0
            
        except Exception as e:
            logger.error(f"Error verificando correlación para {new_pair}: {e}")
            return 1.0
    
    def execute_trade(self, pair, signal, confidence, quality, current_price, atr_value, timestamp):
        """Ejecuta una operación con gestión de riesgo avanzada"""
        try:
            # Verificar umbrales SICAR
            if abs(signal) == 0 or confidence < self.sicar_confidence_threshold or quality < self.sicar_quality_threshold:
                return False
            
            # Verificar riesgo de correlación
            correlation_factor = self.check_correlation_risk(pair, signal)
            if correlation_factor == 0:
                return False
            
            # Calcular tamaño de posición
            position_size = self.calculate_position_size(pair, confidence * quality, current_price)
            position_size *= correlation_factor  # Ajustar por correlación
            
            if position_size == 0:
                return False
            
            # Calcular stops dinámicos
            stop_loss, take_profit = self.calculate_dynamic_stops(pair, current_price, signal, atr_value)
            
            # Cerrar posición existente si hay una
            if pair in self.positions and self.positions[pair]['size'] != 0:
                self.close_position(pair, current_price, timestamp, 'new_signal')
            
            # Abrir nueva posición
            position_value = position_size * current_price
            fee = position_value * 0.001  # 0.1% fee
            self.fees_paid += fee
            
            # Registrar posición
            self.positions[pair] = {
                'size': position_size * signal,  # Positivo para long, negativo para short
                'entry_price': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'entry_time': timestamp,
                'signal_strength': confidence * quality,
                'leverage': self.leverage
            }
            
            # Registrar trade
            trade = {
                'timestamp': timestamp,
                'pair': pair,
                'action': 'open',
                'side': 'long' if signal > 0 else 'short',
                'size': abs(position_size),
                'price': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'signal_strength': confidence * quality,
                'leverage': self.leverage,
                'fee': fee
            }
            
            self.trades_history.append(trade)
            self.total_trades += 1
            
            logger.info(f"🔄 {pair}: {trade['side'].upper()} - Size: {position_size:.6f} @ ${current_price:.2f} | SL: ${stop_loss:.2f} | TP: ${take_profit:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error ejecutando trade para {pair}: {e}")
            return False
    
    def close_position(self, pair, current_price, timestamp, reason='manual'):
        """Cierra una posición existente"""
        try:
            if pair not in self.positions or self.positions[pair]['size'] == 0:
                return False
            
            position = self.positions[pair]
            position_size = abs(position['size'])
            is_long = position['size'] > 0
            entry_price = position['entry_price']
            
            # Calcular PnL
            if is_long:
                pnl = (current_price - entry_price) * position_size * self.leverage
            else:
                pnl = (entry_price - current_price) * position_size * self.leverage
            
            # Fee de cierre
            position_value = position_size * current_price
            fee = position_value * 0.001
            self.fees_paid += fee
            
            # PnL neto
            net_pnl = pnl - fee
            self.total_pnl += net_pnl
            self.current_capital += net_pnl
            
            # Estadísticas
            if net_pnl > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1
            
            # Registrar trade de cierre
            trade = {
                'timestamp': timestamp,
                'pair': pair,
                'action': 'close',
                'side': 'long' if is_long else 'short',
                'size': position_size,
                'price': current_price,
                'entry_price': entry_price,
                'pnl': net_pnl,
                'fee': fee,
                'reason': reason,
                'leverage': self.leverage
            }
            
            self.trades_history.append(trade)
            
            # Limpiar posición
            self.positions[pair] = {'size': 0}
            
            logger.info(f"🔚 {pair}: CLOSE {trade['side'].upper()} - PnL: ${net_pnl:.2f} | Reason: {reason}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error cerrando posición para {pair}: {e}")
            return False
    
    def check_stop_conditions(self, pair, current_price, timestamp):
        """Verifica condiciones de stop-loss y take-profit"""
        try:
            if pair not in self.positions or self.positions[pair]['size'] == 0:
                return False
            
            position = self.positions[pair]
            is_long = position['size'] > 0
            stop_loss = position['stop_loss']
            take_profit = position['take_profit']
            
            # Verificar stop-loss
            if (is_long and current_price <= stop_loss) or (not is_long and current_price >= stop_loss):
                self.close_position(pair, current_price, timestamp, 'stop_loss')
                return True
            
            # Verificar take-profit
            if (is_long and current_price >= take_profit) or (not is_long and current_price <= take_profit):
                self.close_position(pair, current_price, timestamp, 'take_profit')
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error verificando stops para {pair}: {e}")
            return False
    
    def run_multi_pairs_backtest(self):
        """Ejecuta backtest con múltiples pares de criptomonedas"""
        try:
            logger.info("🚀 INICIANDO SISTEMA AVANZADO MULTI-PARES SICAR")
            logger.info(f"Capital inicial: ${self.initial_capital}")
            logger.info(f"Apalancamiento: {self.leverage}x")
            logger.info(f"Pares a operar: {', '.join(self.trading_pairs)}")
            logger.info(f"Objetivo ROI mensual: {self.target_monthly_roi*100}%")
            
            # Obtener datos para todos los pares
            all_data = self.fetch_multi_pair_data()
            
            if not all_data:
                logger.error("No se pudieron obtener datos para ningún par")
                return None
            
            # Calcular indicadores para todos los pares
            processed_data = {}
            for pair, timeframe_data in all_data.items():
                processed_data[pair] = {}
                for timeframe, df in timeframe_data.items():
                    processed_df = self.calculate_advanced_indicators(df, pair)
                    if processed_df is not None:
                        processed_data[pair][timeframe] = processed_df
                        logger.info(f"✅ Indicadores calculados para {pair} {timeframe}")
            
            # Inicializar posiciones
            for pair in self.trading_pairs:
                self.positions[pair] = {'size': 0}
            
            # Obtener timestamps comunes (usar el par con más datos)
            max_length = 0
            reference_pair = None
            for pair, timeframe_data in processed_data.items():
                if '4h' in timeframe_data:
                    length = len(timeframe_data['4h'])
                    if length > max_length:
                        max_length = length
                        reference_pair = pair
            
            if reference_pair is None:
                logger.error("No se encontró par de referencia")
                return None
            
            timestamps = processed_data[reference_pair]['4h']['timestamp'].values
            
            logger.info(f"Iniciando backtest con {len(timestamps)} períodos...")
            
            # Ejecutar backtest
            for i in range(50, len(timestamps)):  # Empezar después de 50 períodos para indicadores
                current_time = timestamps[i]
                
                # Procesar cada par
                for pair in self.trading_pairs:
                    if pair not in processed_data or '4h' not in processed_data[pair]:
                        continue
                    
                    try:
                        # Obtener datos actuales
                        data_4h = processed_data[pair]['4h'].iloc[:i+1]
                        data_1d = processed_data[pair].get('1d', data_4h).iloc[:i//6+1] if '1d' in processed_data[pair] else data_4h.iloc[:i+1]
                        
                        if len(data_4h) < 20 or len(data_1d) < 10:
                            continue
                        
                        current_price = data_4h['close'].iloc[-1]
                        current_atr = data_4h['atr'].iloc[-1] if 'atr' in data_4h.columns else current_price * 0.02
                        
                        # Verificar stops primero
                        self.check_stop_conditions(pair, current_price, current_time)
                        
                        # Generar señales SICAR
                        signal, confidence, quality = self.generate_sicar_signals(data_4h, data_1d, pair)
                        
                        # Ejecutar trade si hay señal válida
                        if signal != 0:
                            self.execute_trade(pair, signal, confidence, quality, current_price, current_atr, current_time)
                        
                    except Exception as e:
                        logger.error(f"Error procesando {pair} en timestamp {i}: {e}")
                        continue
                
                # Registrar estado del portfolio cada 24 períodos (1 día en 4h)
                if i % 24 == 0:
                    portfolio_value = self.current_capital
                    
                    # Agregar valor de posiciones abiertas
                    for pair in self.trading_pairs:
                        if pair in self.positions and self.positions[pair]['size'] != 0:
                            if pair in processed_data and '4h' in processed_data[pair] and i < len(processed_data[pair]['4h']):
                                current_price = processed_data[pair]['4h']['close'].iloc[i]
                                position = self.positions[pair]
                                position_size = abs(position['size'])
                                is_long = position['size'] > 0
                                entry_price = position['entry_price']
                                
                                if is_long:
                                    unrealized_pnl = (current_price - entry_price) * position_size * self.leverage
                                else:
                                    unrealized_pnl = (entry_price - current_price) * position_size * self.leverage
                                
                                portfolio_value += unrealized_pnl
                    
                    self.portfolio_history.append({
                        'timestamp': current_time,
                        'portfolio_value': portfolio_value,
                        'total_pnl': self.total_pnl,
                        'total_trades': self.total_trades,
                        'fees_paid': self.fees_paid,
                        'active_positions': len([p for p in self.positions.values() if p['size'] != 0])
                    })
            
            # Cerrar todas las posiciones al final
            final_timestamp = timestamps[-1]
            for pair in self.trading_pairs:
                if pair in self.positions and self.positions[pair]['size'] != 0:
                    if pair in processed_data and '4h' in processed_data[pair]:
                        final_price = processed_data[pair]['4h']['close'].iloc[-1]
                        self.close_position(pair, final_price, final_timestamp, 'backtest_end')
            
            # Calcular métricas finales
            final_capital = self.current_capital
            total_return = (final_capital - self.initial_capital) / self.initial_capital
            net_pnl = self.total_pnl - self.fees_paid
            net_return = net_pnl / self.initial_capital
            
            # Calcular duración y ROI mensual
            start_date = pd.to_datetime(timestamps[50])
            end_date = pd.to_datetime(timestamps[-1])
            duration_days = (end_date - start_date).days
            duration_months = duration_days / 30.44
            
            if duration_months > 0:
                monthly_roi = ((final_capital - self.fees_paid) / self.initial_capital) ** (1/duration_months) - 1
            else:
                monthly_roi = 0
            
            # Calcular win rate
            total_closed_trades = self.winning_trades + self.losing_trades
            win_rate = self.winning_trades / total_closed_trades if total_closed_trades > 0 else 0
            
            # Resultados
            results = {
                'capital_inicial': self.initial_capital,
                'capital_final': final_capital,
                'pnl_bruto': self.total_pnl,
                'fees_totales': self.fees_paid,
                'pnl_neto': net_pnl,
                'retorno_total': total_return * 100,
                'retorno_neto': net_return * 100,
                'roi_mensual': monthly_roi * 100,
                'total_operaciones': self.total_trades,
                'operaciones_ganadoras': self.winning_trades,
                'operaciones_perdedoras': self.losing_trades,
                'win_rate': win_rate * 100,
                'duracion_dias': duration_days,
                'duracion_meses': duration_months,
                'apalancamiento': self.leverage,
                'pares_operados': len([p for p in self.trading_pairs if p in processed_data])
            }
            
            # Guardar resultados
            results_df = pd.DataFrame(self.portfolio_history)
            results_df.to_csv('advanced_multi_pairs_sicar_results.csv', index=False)
            
            # Log de resultados
            logger.info("=" * 80)
            logger.info("RESULTADOS SISTEMA AVANZADO MULTI-PARES SICAR")
            logger.info("=" * 80)
            logger.info(f"💰 Capital inicial: ${results['capital_inicial']:.2f}")
            logger.info(f"💰 Capital final: ${results['capital_final']:.2f}")
            logger.info(f"📈 PnL bruto: ${results['pnl_bruto']:.2f}")
            logger.info(f"💸 Fees totales: ${results['fees_totales']:.2f}")
            logger.info(f"💵 PnL neto: ${results['pnl_neto']:.2f}")
            logger.info(f"📊 Retorno neto: {results['retorno_neto']:.2f}%")
            logger.info(f"🎯 ROI mensual: {results['roi_mensual']:.2f}%")
            logger.info(f"🔄 Total operaciones: {results['total_operaciones']}")
            logger.info(f"✅ Operaciones ganadoras: {results['operaciones_ganadoras']}")
            logger.info(f"❌ Operaciones perdedoras: {results['operaciones_perdedoras']}")
            logger.info(f"🏆 Win rate: {results['win_rate']:.1f}%")
            logger.info(f"📅 Duración: {results['duracion_dias']:.0f} días ({results['duracion_meses']:.1f} meses)")
            logger.info(f"⚡ Apalancamiento: {results['apalancamiento']}x")
            logger.info(f"🪙 Pares operados: {results['pares_operados']}")
            
            # Evaluación del objetivo
            target_gap = self.target_monthly_roi * 100 - results['roi_mensual']
            if results['roi_mensual'] >= self.target_monthly_roi * 100:
                logger.info(f"🎉 ¡OBJETIVO ALCANZADO! ROI mensual: {results['roi_mensual']:.2f}% >= {self.target_monthly_roi*100}%")
            else:
                logger.info(f"⚡ Gap al objetivo: {target_gap:.2f}% (Objetivo: {self.target_monthly_roi*100}%)")
            
            logger.info("=" * 80)
            
            return results
            
        except Exception as e:
            logger.error(f"Error en backtest multi-pares: {e}")
            return None

def main():
    """Función principal"""
    print("🚀 Iniciando Sistema Avanzado Multi-Pares SICAR")
    print("=" * 60)
    
    system = AdvancedMultiPairsSicarSystem()
    results = system.run_multi_pairs_backtest()
    
    if results:
        print(f"\n✅ Backtest completado!")
        print(f"📊 ROI mensual: {results['roi_mensual']:.2f}%")
        print(f"🎯 Objetivo: {system.target_monthly_roi*100}%")
        print(f"🔄 Total operaciones: {results['total_operaciones']}")
        print(f"🏆 Win rate: {results['win_rate']:.1f}%")
        print(f"⚡ Apalancamiento: {results['apalancamiento']}x")
        print(f"📁 Resultados guardados en: advanced_multi_pairs_sicar_results.csv")
    else:
        print("❌ Error en el backtest")

if __name__ == "__main__":
    main()