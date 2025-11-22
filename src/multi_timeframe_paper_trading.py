# /src/multi_timeframe_paper_trading.py
"""
Sistema de Análisis Multi-Timeframe para Paper Trading SICAR
Integra análisis de múltiples timeframes sin afectar las conexiones de IA existentes.
Entrena modelos ML con datos recientes desde la implementación de Grok y OpenAI.
"""

import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import threading
import time
from dataclasses import dataclass, asdict

# Importaciones del sistema SICAR existente
from paper_trading_system import PaperTradingEngine, OrderType, PositionSide
from binance_data_provider import BinanceDataProvider
from advanced_ml_engine import AdvancedMLEngine
from data_pipeline import DataPipeline

# Importaciones de ML
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, classification_report
import talib

logger = logging.getLogger(__name__)

@dataclass
class MultiTimeframeSignal:
    """Señal de trading multi-timeframe."""
    symbol: str
    timestamp: datetime
    timeframes: Dict[str, Dict]  # Análisis por timeframe
    consensus_signal: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float
    strength: float
    ml_prediction: Dict
    risk_level: str

class MultiTimeframePaperTrading:
    """
    Sistema de Paper Trading con análisis multi-timeframe integrado.
    
    Características:
    - Análisis simultáneo de múltiples timeframes (1m, 5m, 15m, 1h)
    - Modelos ML entrenados con datos recientes
    - Integración con sistema de IA existente (Grok + OpenAI)
    - No afecta conexiones de IA actuales
    """
    
    def __init__(self, 
                 initial_capital: float = 250.0,
                 timeframes: List[str] = None,
                 symbols: List[str] = None):
        """
        Inicializa el sistema multi-timeframe.
        
        Args:
            initial_capital: Capital inicial para paper trading
            timeframes: Lista de timeframes a analizar
            symbols: Lista de símbolos a monitorear
        """
        self.initial_capital = initial_capital
        self.timeframes = timeframes or ['1m', '5m', '15m', '1h']
        self.symbols = symbols or ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        
        # Componentes principales
        self.paper_engine = PaperTradingEngine(
            initial_capital=initial_capital,
            commission_rate=0.001
        )
        self.data_provider = BinanceDataProvider()
        self.data_pipeline = DataPipeline(symbols=self.symbols)
        
        # Motor ML avanzado
        self.ml_engine = AdvancedMLEngine()
        
        # Modelos ML por timeframe
        self.ml_models = {}
        self.scalers = {}
        self.models_trained = False
        
        # Cache de datos multi-timeframe
        self.multi_data_cache = {}
        self.last_cache_update = {}
        
        # Configuración de trading
        self.trading_config = {
            'min_confidence': 0.65,
            'min_consensus': 0.7,  # 70% de timeframes deben estar de acuerdo
            'position_size_pct': 0.1,  # 10% del capital por trade
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.04,
            'max_positions': 2
        }
        
        # Estado del sistema
        self.is_running = False
        self.analysis_thread = None
        self.last_analysis = {}
        
        # Métricas de performance
        self.performance_metrics = {
            'total_signals': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0,
            'avg_confidence': 0.0
        }
        
        logger.info(f"🚀 Multi-Timeframe Paper Trading inicializado")
        logger.info(f"   💰 Capital: ${initial_capital}")
        logger.info(f"   ⏰ Timeframes: {self.timeframes}")
        logger.info(f"   📊 Símbolos: {self.symbols}")
    
    def get_multi_timeframe_data(self, symbol: str, limit: int = 100) -> Dict[str, pd.DataFrame]:
        """
        Obtiene datos de múltiples timeframes para un símbolo.
        
        Args:
            symbol: Símbolo a analizar
            limit: Número de barras por timeframe
            
        Returns:
            Diccionario con DataFrames por timeframe
        """
        try:
            multi_data = {}
            
            for timeframe in self.timeframes:
                # Verificar cache
                cache_key = f"{symbol}_{timeframe}"
                now = datetime.now()
                
                if (cache_key in self.multi_data_cache and 
                    cache_key in self.last_cache_update and
                    (now - self.last_cache_update[cache_key]).seconds < 60):
                    multi_data[timeframe] = self.multi_data_cache[cache_key]
                    continue
                
                # Obtener datos frescos
                try:
                    df = self.data_provider.get_klines(
                        symbol=symbol,
                        interval=timeframe,
                        limit=limit
                    )
                    
                    if df is not None and len(df) > 0:
                        # Agregar indicadores técnicos
                        df = self._add_technical_indicators(df)
                        multi_data[timeframe] = df
                        
                        # Actualizar cache
                        self.multi_data_cache[cache_key] = df
                        self.last_cache_update[cache_key] = now
                        
                except Exception as e:
                    logger.warning(f"Error obteniendo datos {timeframe} para {symbol}: {e}")
                    continue
            
            return multi_data
            
        except Exception as e:
            logger.error(f"Error en get_multi_timeframe_data: {e}")
            return {}
    
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Agrega indicadores técnicos al DataFrame.
        
        Args:
            df: DataFrame con datos OHLCV
            
        Returns:
            DataFrame con indicadores técnicos
        """
        try:
            # RSI
            df['rsi'] = talib.RSI(df['close'], timeperiod=14)
            df['rsi_7'] = talib.RSI(df['close'], timeperiod=7)
            df['rsi_21'] = talib.RSI(df['close'], timeperiod=21)
            
            # MACD
            macd, macd_signal, macd_hist = talib.MACD(df['close'])
            df['macd'] = macd
            df['macd_signal'] = macd_signal
            df['macd_hist'] = macd_hist
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = talib.BBANDS(df['close'])
            df['bb_upper'] = bb_upper
            df['bb_middle'] = bb_middle
            df['bb_lower'] = bb_lower
            df['bb_position'] = (df['close'] - bb_lower) / (bb_upper - bb_lower)
            
            # Stochastic
            slowk, slowd = talib.STOCH(df['high'], df['low'], df['close'])
            df['stoch_k'] = slowk
            df['stoch_d'] = slowd
            
            # Williams %R
            df['williams_r'] = talib.WILLR(df['high'], df['low'], df['close'])
            
            # Volume indicators
            df['volume_sma'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # Momentum
            df['momentum'] = talib.MOM(df['close'], timeperiod=10)
            df['roc'] = talib.ROC(df['close'], timeperiod=10)
            
            # ATR
            df['atr'] = talib.ATR(df['high'], df['low'], df['close'])
            df['atr_pct'] = df['atr'] / df['close'] * 100
            
            # Trend indicators
            df['sma_20'] = talib.SMA(df['close'], timeperiod=20)
            df['sma_50'] = talib.SMA(df['close'], timeperiod=50)
            df['ema_12'] = talib.EMA(df['close'], timeperiod=12)
            df['ema_26'] = talib.EMA(df['close'], timeperiod=26)
            
            return df
            
        except Exception as e:
            logger.error(f"Error agregando indicadores técnicos: {e}")
            return df
    
    def analyze_timeframe(self, symbol: str, timeframe: str, df: pd.DataFrame) -> Dict:
        """
        Analiza un timeframe específico.
        
        Args:
            symbol: Símbolo
            timeframe: Timeframe
            df: DataFrame con datos
            
        Returns:
            Diccionario con análisis del timeframe
        """
        try:
            if len(df) < 20:
                return {'signal': 'HOLD', 'confidence': 0.0, 'strength': 0.0}
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # Análisis técnico básico
            signals = []
            confidences = []
            
            # RSI
            if latest['rsi'] < 30:
                signals.append('BUY')
                confidences.append(0.7)
            elif latest['rsi'] > 70:
                signals.append('SELL')
                confidences.append(0.7)
            else:
                signals.append('HOLD')
                confidences.append(0.3)
            
            # MACD
            if latest['macd'] > latest['macd_signal'] and prev['macd'] <= prev['macd_signal']:
                signals.append('BUY')
                confidences.append(0.8)
            elif latest['macd'] < latest['macd_signal'] and prev['macd'] >= prev['macd_signal']:
                signals.append('SELL')
                confidences.append(0.8)
            else:
                signals.append('HOLD')
                confidences.append(0.4)
            
            # Bollinger Bands
            if latest['bb_position'] < 0.2:
                signals.append('BUY')
                confidences.append(0.6)
            elif latest['bb_position'] > 0.8:
                signals.append('SELL')
                confidences.append(0.6)
            else:
                signals.append('HOLD')
                confidences.append(0.3)
            
            # Stochastic
            if latest['stoch_k'] < 20 and latest['stoch_k'] > latest['stoch_d']:
                signals.append('BUY')
                confidences.append(0.6)
            elif latest['stoch_k'] > 80 and latest['stoch_k'] < latest['stoch_d']:
                signals.append('SELL')
                confidences.append(0.6)
            else:
                signals.append('HOLD')
                confidences.append(0.3)
            
            # Consenso de señales
            buy_count = signals.count('BUY')
            sell_count = signals.count('SELL')
            hold_count = signals.count('HOLD')
            
            if buy_count > sell_count and buy_count > hold_count:
                consensus_signal = 'BUY'
                confidence = np.mean([c for i, c in enumerate(confidences) if signals[i] == 'BUY'])
            elif sell_count > buy_count and sell_count > hold_count:
                consensus_signal = 'SELL'
                confidence = np.mean([c for i, c in enumerate(confidences) if signals[i] == 'SELL'])
            else:
                consensus_signal = 'HOLD'
                confidence = np.mean(confidences)
            
            # Calcular fuerza de la señal
            strength = abs(buy_count - sell_count) / len(signals)
            
            # Análisis ML si está disponible
            ml_prediction = self._get_ml_prediction(symbol, timeframe, df)
            
            return {
                'signal': consensus_signal,
                'confidence': confidence,
                'strength': strength,
                'ml_prediction': ml_prediction,
                'indicators': {
                    'rsi': latest['rsi'],
                    'macd': latest['macd'],
                    'bb_position': latest['bb_position'],
                    'stoch_k': latest['stoch_k'],
                    'volume_ratio': latest['volume_ratio']
                },
                'signals_breakdown': {
                    'buy': buy_count,
                    'sell': sell_count,
                    'hold': hold_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error analizando timeframe {timeframe}: {e}")
            return {'signal': 'HOLD', 'confidence': 0.0, 'strength': 0.0}
    
    def _get_ml_prediction(self, symbol: str, timeframe: str, df: pd.DataFrame) -> Dict:
        """
        Obtiene predicción ML para un timeframe específico.
        
        Args:
            symbol: Símbolo
            timeframe: Timeframe
            df: DataFrame con datos
            
        Returns:
            Diccionario con predicción ML
        """
        try:
            model_key = f"{symbol}_{timeframe}"
            
            if model_key not in self.ml_models or not self.models_trained:
                return {'prediction': 'HOLD', 'confidence': 0.0, 'available': False}
            
            # Preparar features
            features = self._prepare_ml_features(df)
            if features is None or len(features) == 0:
                return {'prediction': 'HOLD', 'confidence': 0.0, 'available': False}
            
            # Escalar features
            scaler = self.scalers.get(model_key)
            if scaler is None:
                return {'prediction': 'HOLD', 'confidence': 0.0, 'available': False}
            
            features_scaled = scaler.transform([features])
            
            # Predicción
            model = self.ml_models[model_key]
            prediction = model.predict(features_scaled)[0]
            probabilities = model.predict_proba(features_scaled)[0]
            
            # Convertir predicción numérica a señal
            if prediction == 0:
                signal = 'SELL'
            elif prediction == 2:
                signal = 'BUY'
            else:
                signal = 'HOLD'
            
            confidence = np.max(probabilities)
            
            return {
                'prediction': signal,
                'confidence': confidence,
                'probabilities': probabilities.tolist(),
                'available': True
            }
            
        except Exception as e:
            logger.error(f"Error en predicción ML: {e}")
            return {'prediction': 'HOLD', 'confidence': 0.0, 'available': False}
    
    def _prepare_ml_features(self, df: pd.DataFrame) -> Optional[List[float]]:
        """
        Prepara features para ML.
        
        Args:
            df: DataFrame con datos
            
        Returns:
            Lista de features o None si hay error
        """
        try:
            if len(df) < 2:
                return None
            
            latest = df.iloc[-1]
            
            features = [
                latest['rsi'],
                latest['rsi_7'],
                latest['rsi_21'],
                latest['macd'],
                latest['macd_signal'],
                latest['macd_hist'],
                latest['bb_position'],
                latest['stoch_k'],
                latest['stoch_d'],
                latest['williams_r'],
                latest['volume_ratio'],
                latest['momentum'],
                latest['roc'],
                latest['atr_pct']
            ]
            
            # Verificar que no hay NaN
            if any(pd.isna(features)):
                return None
            
            return features
            
        except Exception as e:
            logger.error(f"Error preparando features ML: {e}")
            return None
    
    def generate_multi_timeframe_signal(self, symbol: str) -> Optional[MultiTimeframeSignal]:
        """
        Genera señal de trading basada en análisis multi-timeframe.
        
        Args:
            symbol: Símbolo a analizar
            
        Returns:
            Señal multi-timeframe o None si hay error
        """
        try:
            # Obtener datos multi-timeframe
            multi_data = self.get_multi_timeframe_data(symbol)
            
            if not multi_data:
                logger.warning(f"No se pudieron obtener datos para {symbol}")
                return None
            
            # Analizar cada timeframe
            timeframe_analyses = {}
            
            for timeframe, df in multi_data.items():
                analysis = self.analyze_timeframe(symbol, timeframe, df)
                timeframe_analyses[timeframe] = analysis
            
            # Calcular consenso
            signals = [analysis['signal'] for analysis in timeframe_analyses.values()]
            confidences = [analysis['confidence'] for analysis in timeframe_analyses.values()]
            strengths = [analysis['strength'] for analysis in timeframe_analyses.values()]
            
            # Consenso por votación ponderada
            buy_weight = sum(conf * strength for signal, conf, strength in zip(signals, confidences, strengths) if signal == 'BUY')
            sell_weight = sum(conf * strength for signal, conf, strength in zip(signals, confidences, strengths) if signal == 'SELL')
            hold_weight = sum(conf * strength for signal, conf, strength in zip(signals, confidences, strengths) if signal == 'HOLD')
            
            total_weight = buy_weight + sell_weight + hold_weight
            
            if total_weight == 0:
                consensus_signal = 'HOLD'
                consensus_confidence = 0.0
            else:
                if buy_weight > sell_weight and buy_weight > hold_weight:
                    consensus_signal = 'BUY'
                    consensus_confidence = buy_weight / total_weight
                elif sell_weight > buy_weight and sell_weight > hold_weight:
                    consensus_signal = 'SELL'
                    consensus_confidence = sell_weight / total_weight
                else:
                    consensus_signal = 'HOLD'
                    consensus_confidence = hold_weight / total_weight
            
            # Calcular fuerza general
            overall_strength = np.mean(strengths)
            
            # Combinar predicciones ML
            ml_predictions = [analysis.get('ml_prediction', {}) for analysis in timeframe_analyses.values()]
            ml_available = any(pred.get('available', False) for pred in ml_predictions)
            
            combined_ml = {
                'available': ml_available,
                'predictions': ml_predictions
            }
            
            # Determinar nivel de riesgo
            risk_level = self._calculate_risk_level(consensus_confidence, overall_strength, timeframe_analyses)
            
            signal = MultiTimeframeSignal(
                symbol=symbol,
                timestamp=datetime.now(),
                timeframes=timeframe_analyses,
                consensus_signal=consensus_signal,
                confidence=consensus_confidence,
                strength=overall_strength,
                ml_prediction=combined_ml,
                risk_level=risk_level
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generando señal multi-timeframe: {e}")
            return None
    
    def _calculate_risk_level(self, confidence: float, strength: float, analyses: Dict) -> str:
        """
        Calcula el nivel de riesgo de la señal.
        
        Args:
            confidence: Confianza del consenso
            strength: Fuerza de la señal
            analyses: Análisis por timeframe
            
        Returns:
            Nivel de riesgo: 'LOW', 'MEDIUM', 'HIGH'
        """
        try:
            # Factores de riesgo
            risk_score = 0
            
            # Confianza baja = mayor riesgo
            if confidence < 0.5:
                risk_score += 2
            elif confidence < 0.7:
                risk_score += 1
            
            # Fuerza baja = mayor riesgo
            if strength < 0.3:
                risk_score += 2
            elif strength < 0.6:
                risk_score += 1
            
            # Divergencia entre timeframes = mayor riesgo
            signals = [analysis['signal'] for analysis in analyses.values()]
            unique_signals = len(set(signals))
            if unique_signals > 2:
                risk_score += 2
            elif unique_signals > 1:
                risk_score += 1
            
            # Clasificar riesgo
            if risk_score <= 1:
                return 'LOW'
            elif risk_score <= 3:
                return 'MEDIUM'
            else:
                return 'HIGH'
                
        except Exception as e:
            logger.error(f"Error calculando nivel de riesgo: {e}")
            return 'HIGH'
    
    def should_execute_trade(self, signal: MultiTimeframeSignal) -> bool:
        """
        Determina si se debe ejecutar un trade basado en la señal.
        
        Args:
            signal: Señal multi-timeframe
            
        Returns:
            True si se debe ejecutar el trade
        """
        try:
            # Verificar condiciones básicas
            if signal.consensus_signal == 'HOLD':
                return False
            
            if signal.confidence < self.trading_config['min_confidence']:
                logger.info(f"Señal rechazada por baja confianza: {signal.confidence:.3f} < {self.trading_config['min_confidence']}")
                return False
            
            if signal.risk_level == 'HIGH':
                logger.info(f"Señal rechazada por alto riesgo: {signal.risk_level}")
                return False
            
            # Verificar consenso mínimo
            total_timeframes = len(signal.timeframes)
            matching_signals = sum(1 for analysis in signal.timeframes.values() 
                                 if analysis['signal'] == signal.consensus_signal)
            
            consensus_ratio = matching_signals / total_timeframes
            if consensus_ratio < self.trading_config['min_consensus']:
                logger.info(f"Señal rechazada por bajo consenso: {consensus_ratio:.3f} < {self.trading_config['min_consensus']}")
                return False
            
            # Verificar límite de posiciones
            portfolio_summary = self.paper_engine.get_portfolio_summary()
            current_positions = len(portfolio_summary.get('positions', {}))
            
            if current_positions >= self.trading_config['max_positions']:
                logger.info(f"Señal rechazada por límite de posiciones: {current_positions} >= {self.trading_config['max_positions']}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error evaluando si ejecutar trade: {e}")
            return False
    
    def execute_paper_trade(self, signal: MultiTimeframeSignal) -> bool:
        """
        Ejecuta un trade en paper trading basado en la señal.
        
        Args:
            signal: Señal multi-timeframe
            
        Returns:
            True si el trade se ejecutó exitosamente
        """
        try:
            if not self.should_execute_trade(signal):
                return False
            
            # Obtener precio actual
            current_price = self.data_provider.get_current_price(signal.symbol)
            if current_price is None:
                logger.error(f"No se pudo obtener precio actual para {signal.symbol}")
                return False
            
            # Calcular tamaño de posición
            portfolio_summary = self.paper_engine.get_portfolio_summary()
            available_capital = portfolio_summary['current_capital']
            
            position_value = available_capital * self.trading_config['position_size_pct']
            quantity = position_value / current_price
            
            # Determinar dirección
            if signal.consensus_signal == 'BUY':
                side = 'buy'
                position_side = PositionSide.LONG
            else:  # SELL
                side = 'sell'
                position_side = PositionSide.SHORT
            
            # Calcular stop loss y take profit
            if signal.consensus_signal == 'BUY':
                stop_loss = current_price * (1 - self.trading_config['stop_loss_pct'])
                take_profit = current_price * (1 + self.trading_config['take_profit_pct'])
            else:
                stop_loss = current_price * (1 + self.trading_config['stop_loss_pct'])
                take_profit = current_price * (1 - self.trading_config['take_profit_pct'])
            
            # Ejecutar orden
            order_id = self.paper_engine.place_order(
                symbol=signal.symbol,
                side=side,
                order_type=OrderType.MARKET,
                quantity=quantity,
                price=current_price
            )
            
            if order_id:
                # Configurar stop loss y take profit
                if signal.consensus_signal == 'BUY':
                    self.paper_engine.place_order(
                        symbol=signal.symbol,
                        side='sell',
                        order_type=OrderType.STOP_LOSS,
                        quantity=quantity,
                        price=stop_loss,
                        stop_price=stop_loss
                    )
                    
                    self.paper_engine.place_order(
                        symbol=signal.symbol,
                        side='sell',
                        order_type=OrderType.TAKE_PROFIT,
                        quantity=quantity,
                        price=take_profit
                    )
                else:
                    self.paper_engine.place_order(
                        symbol=signal.symbol,
                        side='buy',
                        order_type=OrderType.STOP_LOSS,
                        quantity=quantity,
                        price=stop_loss,
                        stop_price=stop_loss
                    )
                    
                    self.paper_engine.place_order(
                        symbol=signal.symbol,
                        side='buy',
                        order_type=OrderType.TAKE_PROFIT,
                        quantity=quantity,
                        price=take_profit
                    )
                
                # Actualizar métricas
                self.performance_metrics['total_signals'] += 1
                
                logger.info(f"✅ Trade ejecutado: {signal.consensus_signal} {signal.symbol}")
                logger.info(f"   💰 Cantidad: {quantity:.6f}")
                logger.info(f"   💲 Precio: ${current_price:.4f}")
                logger.info(f"   🎯 Confianza: {signal.confidence:.1%}")
                logger.info(f"   🛡️ Stop Loss: ${stop_loss:.4f}")
                logger.info(f"   🎯 Take Profit: ${take_profit:.4f}")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error ejecutando paper trade: {e}")
            return False
    
    def start_monitoring(self):
        """Inicia el monitoreo multi-timeframe."""
        try:
            if self.is_running:
                logger.warning("El sistema ya está ejecutándose")
                return
            
            self.is_running = True
            self.analysis_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.analysis_thread.start()
            
            logger.info("🚀 Monitoreo multi-timeframe iniciado")
            
        except Exception as e:
            logger.error(f"Error iniciando monitoreo: {e}")
            self.is_running = False
    
    def stop_monitoring(self):
        """Detiene el monitoreo multi-timeframe."""
        try:
            self.is_running = False
            
            if self.analysis_thread and self.analysis_thread.is_alive():
                self.analysis_thread.join(timeout=5)
            
            logger.info("🛑 Monitoreo multi-timeframe detenido")
            
        except Exception as e:
            logger.error(f"Error deteniendo monitoreo: {e}")
    
    def _monitoring_loop(self):
        """Loop principal de monitoreo."""
        try:
            while self.is_running:
                try:
                    # Analizar cada símbolo
                    for symbol in self.symbols:
                        if not self.is_running:
                            break
                        
                        # Generar señal multi-timeframe
                        signal = self.generate_multi_timeframe_signal(symbol)
                        
                        if signal:
                            # Guardar análisis
                            self.last_analysis[symbol] = signal
                            
                            # Ejecutar trade si es apropiado
                            if signal.consensus_signal != 'HOLD':
                                self.execute_paper_trade(signal)
                        
                        # Pausa entre símbolos
                        time.sleep(2)
                    
                    # Pausa entre ciclos de análisis
                    time.sleep(30)  # Análisis cada 30 segundos
                    
                except Exception as e:
                    logger.error(f"Error en loop de monitoreo: {e}")
                    time.sleep(10)
            
        except Exception as e:
            logger.error(f"Error crítico en monitoreo: {e}")
        finally:
            self.is_running = False
    
    def get_status_report(self) -> Dict:
        """
        Obtiene reporte de estado del sistema.
        
        Returns:
            Diccionario con estado del sistema
        """
        try:
            portfolio_summary = self.paper_engine.get_portfolio_summary()
            
            return {
                'system_status': {
                    'running': self.is_running,
                    'models_trained': self.models_trained,
                    'timeframes': self.timeframes,
                    'symbols': self.symbols
                },
                'portfolio': portfolio_summary,
                'performance': self.performance_metrics,
                'last_analysis': {
                    symbol: {
                        'timestamp': analysis.timestamp.isoformat(),
                        'signal': analysis.consensus_signal,
                        'confidence': analysis.confidence,
                        'risk_level': analysis.risk_level
                    } for symbol, analysis in self.last_analysis.items()
                },
                'trading_config': self.trading_config
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo reporte de estado: {e}")
            return {'error': str(e)}

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Crear sistema multi-timeframe
    mt_system = MultiTimeframePaperTrading(
        initial_capital=250.0,
        timeframes=['1m', '5m', '15m', '1h'],
        symbols=['BTCUSDT', 'ETHUSDT']
    )
    
    print("🚀 Sistema Multi-Timeframe Paper Trading creado!")
    print(f"📊 Estado: {mt_system.get_status_report()}")