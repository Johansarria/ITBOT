import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configurar logging sin caracteres especiales
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('final_optimized_roi_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FinalOptimizedROISystem:
    def __init__(self, initial_capital=500):
        self.initial_capital = initial_capital
        self.total_trades = 0
        self.total_fees_paid = 0.0
        self.fee_rate = 0.001  # 0.1% por operación
        
        # Umbrales optimizados para máxima selectividad
        self.signal_threshold = 0.4  # Muy alto para máxima calidad
        self.confidence_threshold = 0.5  # Muy alto para máxima calidad
        self.quality_threshold = 0.3  # Muy alto para máxima calidad
        
        # Gestión de riesgo optimizada para máximo profit factor
        self.position_size_pct = 0.35  # 35% del capital por posición
        self.stop_loss_pct = 0.03  # 3% stop-loss (ajustado)
        self.take_profit_pct = 0.15  # 15% take-profit (ratio 1:5)
        
        # Parámetros de trading optimizados
        self.min_hold_periods = 6  # Mínimo 6 períodos
        self.max_hold_periods = 50  # Máximo 50 períodos
        self.min_bars_between_trades = 5  # Mínimo 5 barras entre operaciones
        
        # Filtros muy selectivos
        self.min_volume_ratio = 1.3  # Volumen mínimo alto
        self.volatility_min = 0.01  # Volatilidad mínima
        self.volatility_max = 0.08  # Volatilidad máxima más restrictiva
        self.trend_strength_min = 0.5  # Tendencia fuerte requerida
        
        # Métricas de rendimiento
        self.winning_trades = 0
        self.losing_trades = 0
        self.max_consecutive_losses = 0
        self.current_consecutive_losses = 0
        self.last_trade_bar = -20
        
        # Control avanzado de capital
        self.max_positions = 2  # Máximo 2 posiciones simultáneas
        self.capital_preservation_mode = False
        self.drawdown_threshold = 0.1  # 10% drawdown máximo
        
    def calculate_advanced_indicators(self, df):
        """Calcula indicadores técnicos avanzados"""
        try:
            # RSI con múltiples períodos
            for period in [14, 21, 28]:
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
                rs = gain / (loss + 0.0001)
                df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
            
            # MACD con múltiples configuraciones
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            df['macd'] = exp1 - exp2
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # MACD largo plazo
            exp1_long = df['close'].ewm(span=24).mean()
            exp2_long = df['close'].ewm(span=52).mean()
            df['macd_long'] = exp1_long - exp2_long
            df['macd_long_signal'] = df['macd_long'].ewm(span=18).mean()
            
            # Bollinger Bands con múltiples desviaciones
            bb_middle = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = bb_middle + (bb_std * 2.5)  # Más amplias
            df['bb_lower'] = bb_middle - (bb_std * 2.5)
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / bb_middle
            
            # Sistema de medias móviles múltiples
            for period in [10, 20, 50, 100, 200]:
                df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
                df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
            
            # Momentum avanzado
            for period in [5, 10, 20, 50]:
                df[f'momentum_{period}'] = df['close'] / df['close'].shift(period) - 1
                df[f'roc_{period}'] = df['close'].pct_change(period)
            
            # Volatilidad y ATR avanzados
            df['volatility_10'] = df['close'].rolling(window=10).std() / df['close'].rolling(window=10).mean()
            df['volatility_20'] = df['close'].rolling(window=20).std() / df['close'].rolling(window=20).mean()
            df['volatility_50'] = df['close'].rolling(window=50).std() / df['close'].rolling(window=50).mean()
            
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['atr_14'] = true_range.rolling(window=14).mean()
            df['atr_21'] = true_range.rolling(window=21).mean()
            df['atr_pct'] = df['atr_14'] / df['close']
            
            # Volumen avanzado
            for period in [10, 20, 50]:
                df[f'volume_ma_{period}'] = df['volume'].rolling(window=period).mean()
            
            df['volume_ratio_10'] = df['volume'] / df['volume_ma_10']
            df['volume_ratio_20'] = df['volume'] / df['volume_ma_20']
            df['volume_trend'] = df['volume_ma_10'] / df['volume_ma_20']
            df['volume_acceleration'] = df['volume_ma_10'] / df['volume_ma_50']
            
            # Indicadores de tendencia avanzados
            df['trend_sma_short'] = np.where(df['sma_10'] > df['sma_20'], 1, -1)
            df['trend_sma_medium'] = np.where(df['sma_20'] > df['sma_50'], 1, -1)
            df['trend_sma_long'] = np.where(df['sma_50'] > df['sma_100'], 1, -1)
            df['trend_ema'] = np.where(df['ema_20'] > df['ema_50'], 1, -1)
            df['trend_macd'] = np.where(df['macd'] > df['macd_signal'], 1, -1)
            df['trend_macd_long'] = np.where(df['macd_long'] > df['macd_long_signal'], 1, -1)
            df['trend_price'] = np.where(df['close'] > df['sma_50'], 1, -1)
            
            # Fuerza de tendencia compuesta
            df['trend_strength'] = (df['trend_sma_short'] + df['trend_sma_medium'] + 
                                  df['trend_sma_long'] + df['trend_ema'] + 
                                  df['trend_macd'] + df['trend_macd_long'] + 
                                  df['trend_price']) / 7
            
            # Indicadores de reversión avanzados
            df['rsi_divergence'] = np.where(
                (df['rsi_14'] > df['rsi_14'].shift(1)) & 
                (df['close'] < df['close'].shift(1)), 1, 
                np.where((df['rsi_14'] < df['rsi_14'].shift(1)) & 
                        (df['close'] > df['close'].shift(1)), -1, 0)
            )
            
            # Squeeze momentum
            df['bb_squeeze'] = np.where(df['bb_width'] < df['bb_width'].rolling(20).quantile(0.2), 1, 0)
            
            # Soporte y resistencia dinámicos
            df['resistance'] = df['high'].rolling(window=20).max()
            df['support'] = df['low'].rolling(window=20).min()
            df['support_resistance_ratio'] = (df['close'] - df['support']) / (df['resistance'] - df['support'])
            
            # Rellenar valores NaN
            df = df.fillna(method='ffill').fillna(0)
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculando indicadores avanzados: {e}")
            return df
    
    def generate_premium_signal(self, df, i):
        """Genera señales premium de máxima calidad"""
        try:
            if i < 200:  # Necesitamos muchos datos para análisis premium
                return 0.0, 0.0, 0.0
            
            current = df.iloc[i]
            prev = df.iloc[i-1]
            prev5 = df.iloc[i-5]
            
            # Verificar frecuencia de operaciones
            if i - self.last_trade_bar < self.min_bars_between_trades:
                return 0.0, 0.0, 0.0
            
            # Verificar modo de preservación de capital
            if self.capital_preservation_mode:
                return 0.0, 0.0, 0.0
            
            signals = []
            confidences = []
            
            # 1. FILTRO DE TENDENCIA OBLIGATORIO (MUY ESTRICTO)
            trend_strength = current['trend_strength']
            if abs(trend_strength) < self.trend_strength_min:
                return 0.0, 0.0, 0.0  # Tendencia insuficiente
            
            # 2. FILTRO DE VOLATILIDAD OBLIGATORIO
            volatility = current['volatility_20']
            if volatility < self.volatility_min or volatility > self.volatility_max:
                return 0.0, 0.0, 0.0
            
            # 3. FILTRO DE VOLUMEN OBLIGATORIO
            volume_ratio = current['volume_ratio_20']
            volume_trend = current['volume_trend']
            volume_acceleration = current['volume_acceleration']
            
            if (volume_ratio < self.min_volume_ratio or 
                volume_trend < 1.05 or 
                volume_acceleration < 1.02):
                return 0.0, 0.0, 0.0
            
            # 4. SEÑAL RSI MULTI-TIMEFRAME
            rsi_14 = current['rsi_14']
            rsi_21 = current['rsi_21']
            rsi_28 = current['rsi_28']
            
            # Convergencia RSI
            rsi_convergence = (rsi_14 + rsi_21 + rsi_28) / 3
            rsi_consistency = 1 - (np.std([rsi_14, rsi_21, rsi_28]) / 100)
            
            if 25 < rsi_convergence < 35 and rsi_consistency > 0.9:
                signals.append(0.8)
                confidences.append(0.9)
            elif 65 < rsi_convergence < 75 and rsi_consistency > 0.9:
                signals.append(-0.8)
                confidences.append(0.9)
            elif 40 < rsi_convergence < 60 and rsi_consistency > 0.95:
                signals.append(0.3)
                confidences.append(0.5)
            else:
                return 0.0, 0.0, 0.0  # RSI no favorable
            
            # 5. SEÑAL MACD DOBLE CONFIRMACIÓN
            macd_signal_strength = 0
            macd_confidence = 0
            
            # MACD corto
            if (current['macd'] > current['macd_signal'] and 
                prev['macd'] <= prev['macd_signal'] and 
                current['macd_histogram'] > prev['macd_histogram']):
                macd_signal_strength += 0.6
                macd_confidence += 0.7
            
            # MACD largo
            if (current['macd_long'] > current['macd_long_signal'] and 
                current['macd_long'] > prev['macd_long']):
                macd_signal_strength += 0.4
                macd_confidence += 0.6
            
            if macd_signal_strength > 0.5:
                signals.append(macd_signal_strength)
                confidences.append(macd_confidence)
            else:
                return 0.0, 0.0, 0.0  # MACD no confirmatorio
            
            # 6. SEÑAL BOLLINGER BANDS PREMIUM
            bb_pos = current['bb_position']
            bb_width = current['bb_width']
            bb_squeeze = current['bb_squeeze']
            
            if bb_squeeze == 1 and bb_pos < 0.3:  # Squeeze + posición baja
                signals.append(0.7)
                confidences.append(0.8)
            elif bb_pos < 0.15 and bb_width > 0.05:  # Límite inferior con expansión
                signals.append(0.6)
                confidences.append(0.7)
            elif 0.3 < bb_pos < 0.7 and bb_width < 0.03:  # Zona media con compresión
                signals.append(0.2)
                confidences.append(0.4)
            else:
                return 0.0, 0.0, 0.0  # BB no favorable
            
            # 7. CONFIRMACIÓN DE MOMENTUM MULTI-PERÍODO
            momentum_5 = current['momentum_5']
            momentum_10 = current['momentum_10']
            momentum_20 = current['momentum_20']
            
            momentum_consistency = np.sign(momentum_5) == np.sign(momentum_10) == np.sign(momentum_20)
            momentum_strength = abs(momentum_10)
            
            if momentum_consistency and momentum_strength > 0.01:
                signals.append(0.5 * np.sign(momentum_10))
                confidences.append(0.6)
            else:
                return 0.0, 0.0, 0.0  # Momentum inconsistente
            
            # 8. FILTRO DE SOPORTE/RESISTENCIA
            sr_ratio = current['support_resistance_ratio']
            if not (0.2 < sr_ratio < 0.8):  # Evitar zonas de S/R fuertes
                return 0.0, 0.0, 0.0
            
            # 9. COMBINACIÓN FINAL (MUY ESTRICTA)
            if len(signals) >= 4:  # Mínimo 4 señales confirmatorias
                final_signal = np.mean(signals)
                final_confidence = np.mean(confidences)
                
                # Boost por volumen excepcional
                volume_boost = min(volume_ratio / self.min_volume_ratio, 1.4)
                final_confidence *= volume_boost
                
                # Boost por tendencia fuerte
                trend_boost = min(abs(trend_strength) / self.trend_strength_min, 1.3)
                final_confidence *= trend_boost
                
                # Boost por consistencia de señales
                signal_std = np.std(signals)
                consistency_factor = max(0.7, 1 - signal_std)
                
                # Calcular calidad premium
                quality_score = (final_confidence * consistency_factor * 
                               (len(signals) / 6) * trend_boost * volume_boost)
                
                # Aplicar umbrales premium
                if (abs(final_signal) >= self.signal_threshold and 
                    final_confidence >= self.confidence_threshold and 
                    quality_score >= self.quality_threshold):
                    
                    return final_signal, final_confidence, quality_score
            
            return 0.0, 0.0, 0.0
            
        except Exception as e:
            logger.error(f"Error generando señal premium: {e}")
            return 0.0, 0.0, 0.0
    
    def calculate_optimal_position_size(self, signal, confidence, quality_score, current_capital, volatility, atr_pct):
        """Calcula tamaño de posición óptimo usando Kelly Criterion modificado"""
        try:
            # Kelly Criterion base
            win_rate = self.winning_trades / max(self.total_trades, 1) if self.total_trades > 0 else 0.6
            avg_win_loss_ratio = 3.0  # Ratio objetivo basado en TP/SL
            
            kelly_fraction = (win_rate * avg_win_loss_ratio - (1 - win_rate)) / avg_win_loss_ratio
            kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Limitar Kelly
            
            # Tamaño base ajustado por Kelly
            base_size = self.position_size_pct * (0.5 + kelly_fraction)
            
            # Ajustar por calidad de señal
            quality_multiplier = min(quality_score / self.quality_threshold, 1.5)
            
            # Ajustar por confianza
            confidence_multiplier = min(confidence / self.confidence_threshold, 1.4)
            
            # Ajustar por volatilidad (crítico)
            volatility_multiplier = 1.0
            if volatility > 0.04:
                volatility_multiplier = 0.6
            elif volatility < 0.02:
                volatility_multiplier = 1.2
            
            # Ajustar por ATR
            atr_multiplier = 1.0
            if atr_pct > 0.03:
                atr_multiplier = 0.8
            elif atr_pct < 0.015:
                atr_multiplier = 1.1
            
            # Ajustar por racha de pérdidas (conservador)
            loss_multiplier = 1.0
            if self.current_consecutive_losses >= 2:
                loss_multiplier = 0.5
            elif self.current_consecutive_losses == 1:
                loss_multiplier = 0.8
            elif self.current_consecutive_losses == 0 and self.winning_trades > 0:
                loss_multiplier = 1.1
            
            # Calcular tamaño final
            position_fraction = (base_size * quality_multiplier * confidence_multiplier * 
                               volatility_multiplier * atr_multiplier * loss_multiplier)
            
            # Limitar al máximo absoluto
            position_fraction = min(position_fraction, 0.4)  # Máximo 40%
            
            # Calcular valor en USD
            position_value = current_capital * position_fraction
            
            return max(position_value, 30)  # Mínimo $30
            
        except Exception as e:
            logger.error(f"Error calculando tamaño óptimo: {e}")
            return 0.0
    
    def calculate_dynamic_risk_levels(self, price, volatility, atr, signal_strength, quality_score):
        """Calcula niveles de riesgo dinámicos optimizados"""
        try:
            # Stop-loss dinámico
            base_stop = self.stop_loss_pct
            
            # Ajustar por volatilidad
            volatility_stop = volatility * 2.0
            
            # Ajustar por ATR
            atr_stop = (atr / price) * 2.2 if atr > 0 else base_stop
            
            # Usar el mayor pero limitado
            stop_loss_pct = max(base_stop, min(volatility_stop, atr_stop, 0.06))
            
            # Take-profit dinámico optimizado
            base_tp = self.take_profit_pct
            
            # Ajustar por fuerza de señal
            signal_multiplier = min(abs(signal_strength) / 0.5, 1.6)
            
            # Ajustar por calidad
            quality_multiplier = min(quality_score / 0.4, 1.4)
            
            take_profit_pct = base_tp * signal_multiplier * quality_multiplier
            
            # Asegurar ratio mínimo 1:4 para máximo profit factor
            min_tp = stop_loss_pct * 4.0
            take_profit_pct = max(take_profit_pct, min_tp)
            
            # Limitar TP máximo
            take_profit_pct = min(take_profit_pct, 0.25)  # Máximo 25%
            
            return stop_loss_pct, take_profit_pct
            
        except Exception as e:
            logger.error(f"Error calculando niveles dinámicos: {e}")
            return self.stop_loss_pct, self.take_profit_pct
    
    def check_capital_preservation(self, current_value):
        """Verifica si activar modo de preservación de capital"""
        try:
            drawdown = (self.initial_capital - current_value) / self.initial_capital
            
            if drawdown > self.drawdown_threshold:
                if not self.capital_preservation_mode:
                    self.capital_preservation_mode = True
                    logger.warning(f"MODO PRESERVACION ACTIVADO - Drawdown: {drawdown*100:.1f}%")
            elif drawdown < self.drawdown_threshold * 0.5:
                if self.capital_preservation_mode:
                    self.capital_preservation_mode = False
                    logger.info(f"MODO PRESERVACION DESACTIVADO - Drawdown: {drawdown*100:.1f}%")
                    
        except Exception as e:
            logger.error(f"Error verificando preservación de capital: {e}")
    
    def run_final_backtest(self):
        """Ejecuta el backtest final optimizado"""
        try:
            logger.info("Iniciando BACKTEST FINAL OPTIMIZADO para ROI 15% mensual")
            
            # Importar y usar el fetcher de datos
            from robust_data_fetcher import RobustDataFetcher
            
            # Crear fetcher
            fetcher = RobustDataFetcher()
            
            # Obtener datos históricos extensos
            logger.info("Obteniendo datos historicos extensos...")
            btc_data = fetcher.get_market_data('BTCUSDT', '4h', 1000)
            eth_data = fetcher.get_market_data('ETHUSDT', '4h', 1000)
            
            if btc_data is None or eth_data is None or btc_data.empty or eth_data.empty:
                logger.error("No se pudieron obtener datos historicos")
                return pd.DataFrame()
            
            # Normalizar nombres de columnas
            btc_data.columns = [col.lower() for col in btc_data.columns]
            eth_data.columns = [col.lower() for col in eth_data.columns]
            
            # Resetear índice
            btc_data = btc_data.reset_index()
            eth_data = eth_data.reset_index()
            
            # Agregar volumen si no existe
            if 'volume' not in btc_data.columns:
                btc_data['volume'] = 1000000
            if 'volume' not in eth_data.columns:
                eth_data['volume'] = 1000000
            
            logger.info(f"Datos BTC: {len(btc_data)} registros")
            logger.info(f"Datos ETH: {len(eth_data)} registros")
            
            # Calcular indicadores avanzados
            btc_data = self.calculate_advanced_indicators(btc_data)
            eth_data = self.calculate_advanced_indicators(eth_data)
            
            # Inicializar portfolio final
            portfolio = FinalPortfolio(self.initial_capital)
            results = []
            
            logger.info(f"Procesando {len(btc_data)} periodos con análisis premium")
            
            for i in range(len(btc_data)):
                if i >= len(eth_data):
                    break
                    
                current_time = btc_data.iloc[i]['timestamp']
                
                # Verificar preservación de capital
                portfolio_summary = portfolio.get_portfolio_summary()
                self.check_capital_preservation(portfolio_summary['total_value'])
                
                # Procesar BTC
                btc_price = btc_data.iloc[i]['close']
                btc_volatility = btc_data.iloc[i]['volatility_20']
                btc_atr = btc_data.iloc[i]['atr_14']
                btc_atr_pct = btc_data.iloc[i]['atr_pct']
                btc_signal, btc_confidence, btc_quality = self.generate_premium_signal(btc_data, i)
                
                # Procesar ETH
                eth_price = eth_data.iloc[i]['close']
                eth_volatility = eth_data.iloc[i]['volatility_20']
                eth_atr = eth_data.iloc[i]['atr_14']
                eth_atr_pct = eth_data.iloc[i]['atr_pct']
                eth_signal, eth_confidence, eth_quality = self.generate_premium_signal(eth_data, i)
                
                # Gestión de riesgo avanzada
                self.manage_advanced_risk(portfolio, btc_price, eth_price, i)
                
                # Verificar límite de posiciones
                active_positions = len(portfolio.positions)
                
                # Evaluar nuevas entradas BTC
                if (btc_signal != 0.0 and btc_confidence != 0.0 and btc_quality != 0.0 and 
                    active_positions < self.max_positions):
                    
                    position_size = self.calculate_optimal_position_size(
                        btc_signal, btc_confidence, btc_quality, portfolio.cash, 
                        btc_volatility, btc_atr_pct
                    )
                    
                    if btc_signal > 0 and position_size > 25 and not portfolio.has_position('BTCUSDT'):
                        stop_loss_pct, take_profit_pct = self.calculate_dynamic_risk_levels(
                            btc_price, btc_volatility, btc_atr, btc_signal, btc_quality
                        )
                        
                        fees = self.execute_premium_trade(portfolio, 'BTCUSDT', btc_price, position_size, 'buy', stop_loss_pct, take_profit_pct, i)
                        self.last_trade_bar = i
                        logger.info(f"BTC PREMIUM LONG @ ${btc_price:.2f} - Size: ${position_size:.2f} - SL: {stop_loss_pct*100:.1f}% - TP: {take_profit_pct*100:.1f}% - Q: {btc_quality:.2f}")
                
                # Evaluar nuevas entradas ETH
                if (eth_signal != 0.0 and eth_confidence != 0.0 and eth_quality != 0.0 and 
                    active_positions < self.max_positions):
                    
                    position_size = self.calculate_optimal_position_size(
                        eth_signal, eth_confidence, eth_quality, portfolio.cash, 
                        eth_volatility, eth_atr_pct
                    )
                    
                    if eth_signal > 0 and position_size > 25 and not portfolio.has_position('ETHUSDT'):
                        stop_loss_pct, take_profit_pct = self.calculate_dynamic_risk_levels(
                            eth_price, eth_volatility, eth_atr, eth_signal, eth_quality
                        )
                        
                        fees = self.execute_premium_trade(portfolio, 'ETHUSDT', eth_price, position_size, 'buy', stop_loss_pct, take_profit_pct, i)
                        self.last_trade_bar = i
                        logger.info(f"ETH PREMIUM LONG @ ${eth_price:.2f} - Size: ${position_size:.2f} - SL: {stop_loss_pct*100:.1f}% - TP: {take_profit_pct*100:.1f}% - Q: {eth_quality:.2f}")
                
                # Guardar estado
                results.append({
                    'timestamp': current_time,
                    'btc_price': btc_price,
                    'btc_signal': btc_signal,
                    'btc_confidence': btc_confidence,
                    'btc_quality': btc_quality,
                    'eth_price': eth_price,
                    'eth_signal': eth_signal,
                    'eth_confidence': eth_confidence,
                    'eth_quality': eth_quality,
                    'portfolio_value': portfolio_summary['total_value'],
                    'total_pnl': portfolio_summary['total_pnl'],
                    'return_pct': portfolio_summary['return_pct'],
                    'total_trades': self.total_trades,
                    'fees_paid': self.total_fees_paid,
                    'active_positions': active_positions,
                    'capital_preservation': self.capital_preservation_mode
                })
                
                # Log progreso
                if i % 150 == 0:
                    win_rate = self.winning_trades / max(self.total_trades, 1) if self.total_trades > 0 else 0
                    logger.info(f"Periodo {i}/{len(btc_data)} - Valor: ${portfolio_summary['total_value']:.2f} - Operaciones: {self.total_trades} - Win Rate: {win_rate*100:.1f}% - Posiciones: {active_positions}")
            
            # Crear DataFrame de resultados
            results_df = pd.DataFrame(results)
            
            if not results_df.empty:
                # Guardar resultados
                results_df.to_csv('final_optimized_roi_results.csv', index=False)
                
                # Calcular métricas finales
                final_summary = portfolio.get_portfolio_summary()
                net_pnl = final_summary['total_pnl'] - self.total_fees_paid
                net_return = net_pnl / self.initial_capital
                
                # Calcular ROI mensual
                duration_days = (results_df['timestamp'].max() - results_df['timestamp'].min()).days
                duration_months = duration_days / 30.44
                monthly_roi = (((final_summary['total_value'] - self.total_fees_paid) / self.initial_capital) ** (1/duration_months) - 1) if duration_months > 0 else 0
                
                # Métricas avanzadas
                win_rate = self.winning_trades / max(self.total_trades, 1) if self.total_trades > 0 else 0
                
                if self.winning_trades > 0 and self.losing_trades > 0:
                    avg_win = (final_summary['total_pnl'] + self.total_fees_paid) / self.winning_trades if self.winning_trades > 0 else 0
                    avg_loss = abs(final_summary['total_pnl'] - self.total_fees_paid) / self.losing_trades if self.losing_trades > 0 else 0
                    profit_factor = avg_win / max(avg_loss, 0.01)
                else:
                    profit_factor = 0
                
                # Drawdown máximo
                portfolio_values = results_df['portfolio_value'].values
                peak = np.maximum.accumulate(portfolio_values)
                drawdown = (peak - portfolio_values) / peak
                max_drawdown = np.max(drawdown)
                
                logger.info("=" * 80)
                logger.info("RESUMEN FINAL - SISTEMA OPTIMIZADO PREMIUM ROI 15%")
                logger.info("=" * 80)
                logger.info(f"Capital inicial: ${self.initial_capital:.2f}")
                logger.info(f"Valor final: ${final_summary['total_value']:.2f}")
                logger.info(f"PnL bruto: ${final_summary['total_pnl']:.2f}")
                logger.info(f"Fees totales: ${self.total_fees_paid:.2f}")
                logger.info(f"PnL neto: ${net_pnl:.2f}")
                logger.info(f"Retorno neto: {net_return*100:.2f}%")
                logger.info(f"ROI mensual: {monthly_roi*100:.2f}%")
                logger.info(f"Total operaciones: {self.total_trades}")
                logger.info(f"Operaciones ganadoras: {self.winning_trades}")
                logger.info(f"Operaciones perdedoras: {self.losing_trades}")
                logger.info(f"Win rate: {win_rate*100:.1f}%")
                logger.info(f"Profit factor: {profit_factor:.2f}")
                logger.info(f"Max drawdown: {max_drawdown*100:.1f}%")
                logger.info(f"Max perdidas consecutivas: {self.max_consecutive_losses}")
                logger.info(f"Duracion: {duration_days} dias ({duration_months:.1f} meses)")
                
                # Verificar objetivo
                target_roi = 0.15  # 15% mensual
                if monthly_roi >= target_roi:
                    logger.info("=" * 80)
                    logger.info(f"🎯 OBJETIVO ALCANZADO! ROI mensual: {monthly_roi*100:.2f}% >= {target_roi*100:.0f}%")
                    logger.info("🏆 SISTEMA OPTIMIZADO EXITOSO!")
                    logger.info("=" * 80)
                else:
                    gap = target_roi - monthly_roi
                    logger.info("=" * 80)
                    logger.info(f"❌ Objetivo no alcanzado. Gap: {gap*100:.2f}% para llegar al {target_roi*100:.0f}%")
                    
                    # Análisis detallado
                    if win_rate < 0.6:
                        logger.info("📊 ANALISIS: Win rate bajo - necesita filtros más estrictos")
                    if profit_factor < 2.0:
                        logger.info("📊 ANALISIS: Profit factor bajo - ajustar ratio TP/SL")
                    if self.total_trades < 3:
                        logger.info("📊 ANALISIS: Muy pocas operaciones - reducir filtros selectivamente")
                    elif self.total_trades > 20:
                        logger.info("📊 ANALISIS: Demasiadas operaciones - aumentar selectividad")
                    if max_drawdown > 0.15:
                        logger.info("📊 ANALISIS: Drawdown alto - mejorar gestión de riesgo")
                    
                    logger.info("=" * 80)
                
                return results_df
            else:
                logger.error("No se generaron resultados")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error en backtest final: {e}")
            return pd.DataFrame()
    
    def execute_premium_trade(self, portfolio, symbol, price, position_size, action, stop_loss_pct, take_profit_pct, entry_bar):
        """Ejecuta una operación premium"""
        try:
            if action == 'buy' and position_size > 0:
                quantity = position_size / price
                fees = position_size * self.fee_rate
                
                stop_loss_price = price * (1 - stop_loss_pct)
                take_profit_price = price * (1 + take_profit_pct)
                
                portfolio.open_position(symbol, price, quantity, stop_loss_price, take_profit_price, entry_bar)
                self.total_trades += 1
                self.total_fees_paid += fees
                return fees
            return 0.0
        except Exception as e:
            logger.error(f"Error ejecutando trade premium: {e}")
            return 0.0
    
    def manage_advanced_risk(self, portfolio, btc_price, eth_price, current_bar):
        """Gestiona el riesgo de forma avanzada"""
        try:
            # Gestionar BTC
            if portfolio.has_position('BTCUSDT'):
                position = portfolio.positions['BTCUSDT']
                entry_price = position['entry_price']
                entry_bar = position['entry_bar']
                current_pnl_pct = (btc_price - entry_price) / entry_price
                hold_periods = current_bar - entry_bar
                
                # Stop-loss
                if btc_price <= position['stop_loss_price']:
                    portfolio.close_position('BTCUSDT', btc_price)
                    self.losing_trades += 1
                    self.current_consecutive_losses += 1
                    self.max_consecutive_losses = max(self.max_consecutive_losses, self.current_consecutive_losses)
                    hold_days = hold_periods * 4 / 24
                    logger.info(f"BTC PREMIUM Stop Loss @ ${btc_price:.2f} - Loss: {current_pnl_pct*100:.2f}% - Hold: {hold_days:.1f}d")
                
                # Take-profit
                elif btc_price >= position['take_profit_price']:
                    portfolio.close_position('BTCUSDT', btc_price)
                    self.winning_trades += 1
                    self.current_consecutive_losses = 0
                    hold_days = hold_periods * 4 / 24
                    logger.info(f"BTC PREMIUM Take Profit @ ${btc_price:.2f} - Profit: {current_pnl_pct*100:.2f}% - Hold: {hold_days:.1f}d")
                
                # Cierre por tiempo máximo
                elif hold_periods >= self.max_hold_periods:
                    portfolio.close_position('BTCUSDT', btc_price)
                    if current_pnl_pct > 0:
                        self.winning_trades += 1
                        self.current_consecutive_losses = 0
                    else:
                        self.losing_trades += 1
                        self.current_consecutive_losses += 1
                    hold_days = hold_periods * 4 / 24
                    logger.info(f"BTC PREMIUM Max Time @ ${btc_price:.2f} - PnL: {current_pnl_pct*100:.2f}% - Hold: {hold_days:.1f}d")
                
                # Trailing stop dinámico (para ganancias > 8%)
                elif current_pnl_pct > 0.08 and hold_periods >= self.min_hold_periods:
                    trailing_stop = btc_price * 0.95  # 5% trailing
                    if trailing_stop > position['stop_loss_price']:
                        portfolio.positions['BTCUSDT']['stop_loss_price'] = trailing_stop
            
            # Gestionar ETH (similar lógica)
            if portfolio.has_position('ETHUSDT'):
                position = portfolio.positions['ETHUSDT']
                entry_price = position['entry_price']
                entry_bar = position['entry_bar']
                current_pnl_pct = (eth_price - entry_price) / entry_price
                hold_periods = current_bar - entry_bar
                
                if eth_price <= position['stop_loss_price']:
                    portfolio.close_position('ETHUSDT', eth_price)
                    self.losing_trades += 1
                    self.current_consecutive_losses += 1
                    self.max_consecutive_losses = max(self.max_consecutive_losses, self.current_consecutive_losses)
                    hold_days = hold_periods * 4 / 24
                    logger.info(f"ETH PREMIUM Stop Loss @ ${eth_price:.2f} - Loss: {current_pnl_pct*100:.2f}% - Hold: {hold_days:.1f}d")
                
                elif eth_price >= position['take_profit_price']:
                    portfolio.close_position('ETHUSDT', eth_price)
                    self.winning_trades += 1
                    self.current_consecutive_losses = 0
                    hold_days = hold_periods * 4 / 24
                    logger.info(f"ETH PREMIUM Take Profit @ ${eth_price:.2f} - Profit: {current_pnl_pct*100:.2f}% - Hold: {hold_days:.1f}d")
                
                elif hold_periods >= self.max_hold_periods:
                    portfolio.close_position('ETHUSDT', eth_price)
                    if current_pnl_pct > 0:
                        self.winning_trades += 1
                        self.current_consecutive_losses = 0
                    else:
                        self.losing_trades += 1
                        self.current_consecutive_losses += 1
                    hold_days = hold_periods * 4 / 24
                    logger.info(f"ETH PREMIUM Max Time @ ${eth_price:.2f} - PnL: {current_pnl_pct*100:.2f}% - Hold: {hold_days:.1f}d")
                
                elif current_pnl_pct > 0.08 and hold_periods >= self.min_hold_periods:
                    trailing_stop = eth_price * 0.95
                    if trailing_stop > position['stop_loss_price']:
                        portfolio.positions['ETHUSDT']['stop_loss_price'] = trailing_stop
                        
        except Exception as e:
            logger.error(f"Error en gestión avanzada de riesgo: {e}")

class FinalPortfolio:
    def __init__(self, initial_capital):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        
    def has_position(self, symbol):
        return symbol in self.positions
    
    def open_position(self, symbol, price, quantity, stop_loss_price, take_profit_price, entry_bar):
        cost = price * quantity
        if cost <= self.cash:
            self.cash -= cost
            self.positions[symbol] = {
                'quantity': quantity,
                'entry_price': price,
                'stop_loss_price': stop_loss_price,
                'take_profit_price': take_profit_price,
                'entry_bar': entry_bar
            }
    
    def close_position(self, symbol, price):
        if symbol in self.positions:
            position = self.positions[symbol]
            proceeds = position['quantity'] * price
            self.cash += proceeds
            del self.positions[symbol]
    
    def get_portfolio_summary(self):
        total_value = self.cash
        total_pnl = 0
        
        for symbol, position in self.positions.items():
            position_value = position['quantity'] * position['entry_price']
            total_value += position_value
            total_pnl += position_value - (position['quantity'] * position['entry_price'])
        
        return {
            'total_value': total_value,
            'cash': self.cash,
            'total_pnl': total_pnl,
            'return_pct': (total_value - self.initial_capital) / self.initial_capital * 100
        }

def main():
    """Función principal"""
    logger.info("🚀 Iniciando SISTEMA FINAL OPTIMIZADO ROI 15%")
    
    system = FinalOptimizedROISystem(initial_capital=500)
    results = system.run_final_backtest()
    
    if not results.empty:
        print(f"\n🎯 Sistema final optimizado completado!")
        print(f"📊 Resultados guardados en: final_optimized_roi_results.csv")
        print(f"📝 Log guardado en: final_optimized_roi_system.log")
    else:
        print("❌ Error en el sistema final optimizado")

if __name__ == "__main__":
    main()