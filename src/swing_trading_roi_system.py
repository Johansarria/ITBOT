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
        logging.FileHandler('swing_trading_roi_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SwingTradingROISystem:
    def __init__(self, initial_capital=500):
        self.initial_capital = initial_capital
        self.total_trades = 0
        self.total_fees_paid = 0.0
        self.fee_rate = 0.001  # 0.1% por operación
        
        # Umbrales equilibrados para swing trading
        self.signal_threshold = 0.15  # Más bajo para generar operaciones
        self.confidence_threshold = 0.2  # Más bajo para generar operaciones
        self.quality_threshold = 0.1  # Más bajo para generar operaciones
        
        # Gestión de riesgo para swing trading (posiciones más largas)
        self.position_size_pct = 0.3  # 30% del capital por posición
        self.stop_loss_pct = 0.04  # 4% stop-loss (más amplio para swing)
        self.take_profit_pct = 0.12  # 12% take-profit (ratio 1:3)
        
        # Parámetros de swing trading
        self.min_hold_periods = 8  # Mínimo 8 períodos (2 días en 4h)
        self.max_hold_periods = 42  # Máximo 42 períodos (7 días en 4h)
        self.trend_confirmation_periods = 3  # Confirmar tendencia en 3 períodos
        
        # Filtros más permisivos
        self.min_volume_ratio = 1.0  # Volumen mínimo más bajo
        self.volatility_min = 0.005  # Volatilidad mínima
        self.volatility_max = 0.15  # Volatilidad máxima más alta
        
        # Métricas de rendimiento
        self.winning_trades = 0
        self.losing_trades = 0
        self.max_consecutive_losses = 0
        self.current_consecutive_losses = 0
        
        # Control de posiciones swing
        self.position_entry_bars = {}  # Tracking de cuándo se abrió cada posición
        self.min_bars_between_entries = 2  # Mínimo 2 barras entre entradas
        self.last_entry_bar = -10
        
    def calculate_swing_indicators(self, df):
        """Calcula indicadores técnicos optimizados para swing trading"""
        try:
            # RSI con períodos más largos para swing
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=21).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=21).mean()
            rs = gain / (loss + 0.0001)
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD para swing trading
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            df['macd'] = exp1 - exp2
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Bollinger Bands más amplias
            bb_middle = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = bb_middle + (bb_std * 2.2)  # Más amplias
            df['bb_lower'] = bb_middle - (bb_std * 2.2)
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / bb_middle
            
            # Medias móviles para tendencia swing
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['sma_100'] = df['close'].rolling(window=100).mean()
            df['ema_20'] = df['close'].ewm(span=20).mean()
            df['ema_50'] = df['close'].ewm(span=50).mean()
            
            # Momentum para swing trading
            df['momentum_10'] = df['close'] / df['close'].shift(10) - 1
            df['momentum_20'] = df['close'] / df['close'].shift(20) - 1
            df['momentum_50'] = df['close'] / df['close'].shift(50) - 1
            
            # Volatilidad y ATR
            df['volatility'] = df['close'].rolling(window=20).std() / df['close'].rolling(window=20).mean()
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['atr'] = true_range.rolling(window=14).mean()
            df['atr_pct'] = df['atr'] / df['close']
            
            # Volumen para swing
            df['volume_ma_20'] = df['volume'].rolling(window=20).mean()
            df['volume_ma_50'] = df['volume'].rolling(window=50).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma_20']
            df['volume_trend'] = df['volume_ma_20'] / df['volume_ma_50']
            
            # Indicadores de tendencia swing
            df['trend_short'] = np.where(df['sma_20'] > df['sma_50'], 1, -1)
            df['trend_medium'] = np.where(df['sma_50'] > df['sma_100'], 1, -1)
            df['trend_macd'] = np.where(df['macd'] > df['macd_signal'], 1, -1)
            df['trend_price'] = np.where(df['close'] > df['sma_20'], 1, -1)
            
            # Fuerza de tendencia swing
            df['trend_strength'] = (df['trend_short'] + df['trend_medium'] + 
                                  df['trend_macd'] + df['trend_price']) / 4
            
            # Indicadores de reversión
            df['rsi_oversold'] = np.where(df['rsi'] < 35, 1, 0)
            df['rsi_overbought'] = np.where(df['rsi'] > 65, 1, 0)
            df['bb_squeeze'] = np.where(df['bb_width'] < 0.1, 1, 0)
            
            # Divergencias MACD (simplificada)
            df['macd_bullish_div'] = np.where(
                (df['macd'] > df['macd'].shift(1)) & 
                (df['close'] < df['close'].shift(1)), 1, 0
            )
            
            # Rellenar valores NaN
            df = df.fillna(method='ffill').fillna(0)
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculando indicadores swing: {e}")
            return df
    
    def generate_swing_signal(self, df, i):
        """Genera señales optimizadas para swing trading"""
        try:
            if i < 100:  # Necesitamos más datos para swing
                return 0.0, 0.0, 0.0
            
            current = df.iloc[i]
            prev = df.iloc[i-1]
            prev2 = df.iloc[i-2]
            
            # Verificar frecuencia de entradas
            if i - self.last_entry_bar < self.min_bars_between_entries:
                return 0.0, 0.0, 0.0
            
            signals = []
            confidences = []
            
            # 1. Señal RSI para swing (zonas más amplias)
            rsi = current['rsi']
            if 20 < rsi < 40:  # Zona de sobreventa amplia
                rsi_signal = 0.6
                rsi_confidence = 0.7
                signals.append(rsi_signal)
                confidences.append(rsi_confidence)
            elif 60 < rsi < 80:  # Zona de sobrecompra amplia
                rsi_signal = -0.6
                rsi_confidence = 0.7
                signals.append(rsi_signal)
                confidences.append(rsi_confidence)
            elif 45 < rsi < 55:  # Zona neutral
                signals.append(0.2)
                confidences.append(0.3)
            
            # 2. Señal MACD para swing
            if (current['macd'] > current['macd_signal'] and 
                prev['macd'] <= prev['macd_signal']):
                signals.append(0.7)
                confidences.append(0.8)
            elif (current['macd'] < current['macd_signal'] and 
                  prev['macd'] >= prev['macd_signal']):
                signals.append(-0.7)
                confidences.append(0.8)
            elif current['macd_histogram'] > 0:
                signals.append(0.3)
                confidences.append(0.4)
            
            # 3. Señal Bollinger Bands para swing
            bb_pos = current['bb_position']
            if bb_pos < 0.2:  # Cerca del límite inferior
                signals.append(0.5)
                confidences.append(0.6)
            elif bb_pos > 0.8:  # Cerca del límite superior
                signals.append(-0.5)
                confidences.append(0.6)
            elif 0.4 < bb_pos < 0.6:  # Zona media
                signals.append(0.1)
                confidences.append(0.2)
            
            # 4. Señal de tendencia (más permisiva)
            trend_strength = current['trend_strength']
            if trend_strength > 0.25:  # Tendencia alcista moderada
                signals.append(0.4)
                confidences.append(0.5)
            elif trend_strength < -0.25:  # Tendencia bajista moderada
                signals.append(-0.4)
                confidences.append(0.5)
            
            # 5. Señal de momentum swing
            momentum_20 = current['momentum_20']
            if momentum_20 > 0.02:  # Momentum positivo
                signals.append(0.3)
                confidences.append(0.4)
            elif momentum_20 < -0.02:  # Momentum negativo
                signals.append(-0.3)
                confidences.append(0.4)
            
            # 6. Filtros básicos (más permisivos)
            volatility = current['volatility']
            if volatility < self.volatility_min or volatility > self.volatility_max:
                return 0.0, 0.0, 0.0
            
            volume_ratio = current['volume_ratio']
            if volume_ratio < self.min_volume_ratio:
                return 0.0, 0.0, 0.0
            
            # 7. Combinar señales (más permisivo)
            if len(signals) >= 1:  # Solo necesitamos 1 señal
                final_signal = np.mean(signals)
                final_confidence = np.mean(confidences)
                
                # Ajustar por volumen
                volume_boost = min(volume_ratio / self.min_volume_ratio, 1.3)
                final_confidence *= volume_boost
                
                # Ajustar por volatilidad
                vol_factor = 1.0
                if 0.02 < volatility < 0.05:  # Volatilidad ideal
                    vol_factor = 1.2
                final_confidence *= vol_factor
                
                # Calcular calidad
                quality_score = final_confidence * (len(signals) / 5) * vol_factor
                
                # Aplicar umbrales (más bajos)
                if (abs(final_signal) >= self.signal_threshold and 
                    final_confidence >= self.confidence_threshold and 
                    quality_score >= self.quality_threshold):
                    
                    return final_signal, final_confidence, quality_score
            
            return 0.0, 0.0, 0.0
            
        except Exception as e:
            logger.error(f"Error generando señal swing: {e}")
            return 0.0, 0.0, 0.0
    
    def calculate_swing_position_size(self, signal, confidence, quality_score, current_capital, volatility):
        """Calcula tamaño de posición para swing trading"""
        try:
            # Tamaño base más grande para swing
            base_size = self.position_size_pct
            
            # Ajustar por confianza
            confidence_multiplier = min(confidence / self.confidence_threshold, 1.4)
            
            # Ajustar por calidad
            quality_multiplier = min(quality_score / self.quality_threshold, 1.3)
            
            # Ajustar por volatilidad (importante para swing)
            volatility_multiplier = 1.0
            if volatility > 0.06:
                volatility_multiplier = 0.7  # Reducir en alta volatilidad
            elif volatility < 0.02:
                volatility_multiplier = 1.2  # Aumentar en baja volatilidad
            
            # Ajustar por racha de pérdidas
            loss_multiplier = 1.0
            if self.current_consecutive_losses > 1:
                loss_multiplier = 0.7
            elif self.current_consecutive_losses == 0:
                loss_multiplier = 1.1
            
            # Calcular tamaño final
            position_fraction = (base_size * confidence_multiplier * quality_multiplier * 
                               volatility_multiplier * loss_multiplier)
            
            # Limitar al máximo
            position_fraction = min(position_fraction, 0.4)  # Máximo 40% para swing
            
            # Calcular valor en USD
            position_value = current_capital * position_fraction
            
            return max(position_value, 25)  # Mínimo $25 para swing
            
        except Exception as e:
            logger.error(f"Error calculando tamaño de posición swing: {e}")
            return 0.0
    
    def calculate_swing_levels(self, price, volatility, atr, signal_strength):
        """Calcula stop-loss y take-profit para swing trading"""
        try:
            # Stop-loss más amplio para swing
            base_stop = self.stop_loss_pct
            
            # Ajustar por volatilidad
            if volatility > 0.05:
                volatility_stop = volatility * 1.5
            else:
                volatility_stop = base_stop
            
            # ATR stop más amplio
            atr_stop = (atr / price) * 2.5 if atr > 0 else base_stop
            
            # Usar el mayor pero limitado
            stop_loss_pct = max(base_stop, min(volatility_stop, atr_stop, 0.08))
            
            # Take-profit más amplio para swing
            base_tp = self.take_profit_pct
            signal_multiplier = min(abs(signal_strength) / 0.3, 1.4)
            take_profit_pct = base_tp * signal_multiplier
            
            # Asegurar ratio mínimo 1:2.5 para swing
            take_profit_pct = max(take_profit_pct, stop_loss_pct * 2.5)
            
            return stop_loss_pct, take_profit_pct
            
        except Exception as e:
            logger.error(f"Error calculando niveles swing: {e}")
            return self.stop_loss_pct, self.take_profit_pct
    
    def should_close_swing_position(self, symbol, current_bar, entry_bar, current_pnl_pct):
        """Determina si cerrar una posición swing por tiempo"""
        try:
            hold_periods = current_bar - entry_bar
            
            # Cerrar por tiempo mínimo con ganancia
            if hold_periods >= self.min_hold_periods and current_pnl_pct > 0.02:
                return True, "Min hold + profit"
            
            # Cerrar por tiempo máximo
            if hold_periods >= self.max_hold_periods:
                return True, "Max hold time"
            
            # Cerrar por ganancia significativa antes del tiempo
            if current_pnl_pct > 0.08 and hold_periods >= 4:
                return True, "High profit early"
            
            return False, ""
            
        except Exception as e:
            logger.error(f"Error evaluando cierre swing: {e}")
            return False, ""
    
    def run_swing_backtest(self):
        """Ejecuta el backtest de swing trading"""
        try:
            logger.info("Iniciando backtest de Swing Trading para ROI 15% mensual")
            
            # Importar y usar el fetcher de datos
            from robust_data_fetcher import RobustDataFetcher
            
            # Crear fetcher
            fetcher = RobustDataFetcher()
            
            # Obtener datos históricos (más datos para swing)
            logger.info("Obteniendo datos historicos para swing trading...")
            btc_data = fetcher.get_market_data('BTCUSDT', '4h', 800)
            eth_data = fetcher.get_market_data('ETHUSDT', '4h', 800)
            
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
            
            # Calcular indicadores swing
            btc_data = self.calculate_swing_indicators(btc_data)
            eth_data = self.calculate_swing_indicators(eth_data)
            
            # Inicializar portfolio swing
            portfolio = SwingPortfolio(self.initial_capital)
            results = []
            
            logger.info(f"Procesando {len(btc_data)} periodos para swing trading")
            
            for i in range(len(btc_data)):
                if i >= len(eth_data):
                    break
                    
                current_time = btc_data.iloc[i]['timestamp']
                
                # Procesar BTC
                btc_price = btc_data.iloc[i]['close']
                btc_volatility = btc_data.iloc[i]['volatility']
                btc_atr = btc_data.iloc[i]['atr']
                btc_signal, btc_confidence, btc_quality = self.generate_swing_signal(btc_data, i)
                
                # Procesar ETH
                eth_price = eth_data.iloc[i]['close']
                eth_volatility = eth_data.iloc[i]['volatility']
                eth_atr = eth_data.iloc[i]['atr']
                eth_signal, eth_confidence, eth_quality = self.generate_swing_signal(eth_data, i)
                
                # Gestión de riesgo swing
                self.manage_swing_risk(portfolio, btc_price, eth_price, i)
                
                # Evaluar nuevas entradas BTC
                if (btc_signal != 0.0 and btc_confidence != 0.0 and btc_quality != 0.0):
                    position_size = self.calculate_swing_position_size(
                        btc_signal, btc_confidence, btc_quality, portfolio.cash, btc_volatility
                    )
                    
                    if btc_signal > 0 and position_size > 20 and not portfolio.has_position('BTCUSDT'):
                        stop_loss_pct, take_profit_pct = self.calculate_swing_levels(
                            btc_price, btc_volatility, btc_atr, btc_signal
                        )
                        
                        fees = self.execute_swing_trade(portfolio, 'BTCUSDT', btc_price, position_size, 'buy', stop_loss_pct, take_profit_pct, i)
                        self.last_entry_bar = i
                        logger.info(f"BTC SWING LONG @ ${btc_price:.2f} - Size: ${position_size:.2f} - SL: {stop_loss_pct*100:.1f}% - TP: {take_profit_pct*100:.1f}% - Q: {btc_quality:.2f}")
                
                # Evaluar nuevas entradas ETH
                if (eth_signal != 0.0 and eth_confidence != 0.0 and eth_quality != 0.0):
                    position_size = self.calculate_swing_position_size(
                        eth_signal, eth_confidence, eth_quality, portfolio.cash, eth_volatility
                    )
                    
                    if eth_signal > 0 and position_size > 20 and not portfolio.has_position('ETHUSDT'):
                        stop_loss_pct, take_profit_pct = self.calculate_swing_levels(
                            eth_price, eth_volatility, eth_atr, eth_signal
                        )
                        
                        fees = self.execute_swing_trade(portfolio, 'ETHUSDT', eth_price, position_size, 'buy', stop_loss_pct, take_profit_pct, i)
                        self.last_entry_bar = i
                        logger.info(f"ETH SWING LONG @ ${eth_price:.2f} - Size: ${position_size:.2f} - SL: {stop_loss_pct*100:.1f}% - TP: {take_profit_pct*100:.1f}% - Q: {eth_quality:.2f}")
                
                # Guardar estado
                portfolio_summary = portfolio.get_portfolio_summary()
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
                    'fees_paid': self.total_fees_paid
                })
                
                # Log progreso
                if i % 100 == 0:
                    win_rate = self.winning_trades / max(self.total_trades, 1) if self.total_trades > 0 else 0
                    logger.info(f"Periodo {i}/{len(btc_data)} - Valor: ${portfolio_summary['total_value']:.2f} - Operaciones: {self.total_trades} - Win Rate: {win_rate*100:.1f}%")
            
            # Crear DataFrame de resultados
            results_df = pd.DataFrame(results)
            
            if not results_df.empty:
                # Guardar resultados
                results_df.to_csv('swing_trading_roi_results.csv', index=False)
                
                # Calcular métricas finales
                final_summary = portfolio.get_portfolio_summary()
                net_pnl = final_summary['total_pnl'] - self.total_fees_paid
                net_return = net_pnl / self.initial_capital
                
                # Calcular ROI mensual
                duration_days = (results_df['timestamp'].max() - results_df['timestamp'].min()).days
                duration_months = duration_days / 30.44
                monthly_roi = (((final_summary['total_value'] - self.total_fees_paid) / self.initial_capital) ** (1/duration_months) - 1) if duration_months > 0 else 0
                
                # Métricas adicionales
                win_rate = self.winning_trades / max(self.total_trades, 1) if self.total_trades > 0 else 0
                avg_win = final_summary['total_pnl'] / max(self.winning_trades, 1) if self.winning_trades > 0 else 0
                avg_loss = abs(final_summary['total_pnl']) / max(self.losing_trades, 1) if self.losing_trades > 0 else 0
                profit_factor = avg_win / max(avg_loss, 0.01)
                
                logger.info("=" * 70)
                logger.info("RESUMEN FINAL - SISTEMA SWING TRADING ROI")
                logger.info("=" * 70)
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
                logger.info(f"Max perdidas consecutivas: {self.max_consecutive_losses}")
                
                # Verificar objetivo
                target_roi = 0.15  # 15% mensual
                if monthly_roi >= target_roi:
                    logger.info(f"OBJETIVO ALCANZADO! ROI mensual: {monthly_roi*100:.2f}% >= {target_roi*100:.0f}%")
                else:
                    gap = target_roi - monthly_roi
                    logger.info(f"Objetivo no alcanzado. Gap: {gap*100:.2f}% para llegar al {target_roi*100:.0f}%")
                    
                    # Análisis de mejoras
                    if win_rate < 0.5:
                        logger.info("ANALISIS: Win rate bajo - necesita mejores filtros de entrada")
                    if profit_factor < 1.3:
                        logger.info("ANALISIS: Profit factor bajo - ajustar ratio riesgo/beneficio")
                    if self.total_trades < 3:
                        logger.info("ANALISIS: Pocas operaciones - reducir filtros")
                    elif self.total_trades > 30:
                        logger.info("ANALISIS: Demasiadas operaciones - aumentar filtros")
                
                return results_df
            else:
                logger.error("No se generaron resultados")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error en backtest swing: {e}")
            return pd.DataFrame()
    
    def execute_swing_trade(self, portfolio, symbol, price, position_size, action, stop_loss_pct, take_profit_pct, entry_bar):
        """Ejecuta una operación swing"""
        try:
            if action == 'buy' and position_size > 0:
                quantity = position_size / price
                fees = position_size * self.fee_rate
                
                stop_loss_price = price * (1 - stop_loss_pct)
                take_profit_price = price * (1 + take_profit_pct)
                
                portfolio.open_position(symbol, price, quantity, stop_loss_price, take_profit_price, entry_bar)
                self.position_entry_bars[symbol] = entry_bar
                self.total_trades += 1
                self.total_fees_paid += fees
                return fees
            return 0.0
        except Exception as e:
            logger.error(f"Error ejecutando trade swing: {e}")
            return 0.0
    
    def manage_swing_risk(self, portfolio, btc_price, eth_price, current_bar):
        """Gestiona el riesgo para swing trading"""
        try:
            # Gestionar BTC
            if portfolio.has_position('BTCUSDT'):
                position = portfolio.positions['BTCUSDT']
                entry_price = position['entry_price']
                entry_bar = position['entry_bar']
                current_pnl_pct = (btc_price - entry_price) / entry_price
                
                # Verificar stop-loss
                if btc_price <= position['stop_loss_price']:
                    portfolio.close_position('BTCUSDT', btc_price)
                    self.losing_trades += 1
                    self.current_consecutive_losses += 1
                    self.max_consecutive_losses = max(self.max_consecutive_losses, self.current_consecutive_losses)
                    hold_days = (current_bar - entry_bar) * 4 / 24  # Convertir a días
                    logger.info(f"BTC SWING Stop Loss @ ${btc_price:.2f} - Loss: {current_pnl_pct*100:.2f}% - Hold: {hold_days:.1f} days")
                
                # Verificar take-profit
                elif btc_price >= position['take_profit_price']:
                    portfolio.close_position('BTCUSDT', btc_price)
                    self.winning_trades += 1
                    self.current_consecutive_losses = 0
                    hold_days = (current_bar - entry_bar) * 4 / 24
                    logger.info(f"BTC SWING Take Profit @ ${btc_price:.2f} - Profit: {current_pnl_pct*100:.2f}% - Hold: {hold_days:.1f} days")
                
                # Verificar cierre por tiempo
                else:
                    should_close, reason = self.should_close_swing_position('BTCUSDT', current_bar, entry_bar, current_pnl_pct)
                    if should_close:
                        portfolio.close_position('BTCUSDT', btc_price)
                        if current_pnl_pct > 0:
                            self.winning_trades += 1
                            self.current_consecutive_losses = 0
                        else:
                            self.losing_trades += 1
                            self.current_consecutive_losses += 1
                        hold_days = (current_bar - entry_bar) * 4 / 24
                        logger.info(f"BTC SWING Close ({reason}) @ ${btc_price:.2f} - PnL: {current_pnl_pct*100:.2f}% - Hold: {hold_days:.1f} days")
            
            # Gestionar ETH
            if portfolio.has_position('ETHUSDT'):
                position = portfolio.positions['ETHUSDT']
                entry_price = position['entry_price']
                entry_bar = position['entry_bar']
                current_pnl_pct = (eth_price - entry_price) / entry_price
                
                # Verificar stop-loss
                if eth_price <= position['stop_loss_price']:
                    portfolio.close_position('ETHUSDT', eth_price)
                    self.losing_trades += 1
                    self.current_consecutive_losses += 1
                    self.max_consecutive_losses = max(self.max_consecutive_losses, self.current_consecutive_losses)
                    hold_days = (current_bar - entry_bar) * 4 / 24
                    logger.info(f"ETH SWING Stop Loss @ ${eth_price:.2f} - Loss: {current_pnl_pct*100:.2f}% - Hold: {hold_days:.1f} days")
                
                # Verificar take-profit
                elif eth_price >= position['take_profit_price']:
                    portfolio.close_position('ETHUSDT', eth_price)
                    self.winning_trades += 1
                    self.current_consecutive_losses = 0
                    hold_days = (current_bar - entry_bar) * 4 / 24
                    logger.info(f"ETH SWING Take Profit @ ${eth_price:.2f} - Profit: {current_pnl_pct*100:.2f}% - Hold: {hold_days:.1f} days")
                
                # Verificar cierre por tiempo
                else:
                    should_close, reason = self.should_close_swing_position('ETHUSDT', current_bar, entry_bar, current_pnl_pct)
                    if should_close:
                        portfolio.close_position('ETHUSDT', eth_price)
                        if current_pnl_pct > 0:
                            self.winning_trades += 1
                            self.current_consecutive_losses = 0
                        else:
                            self.losing_trades += 1
                            self.current_consecutive_losses += 1
                        hold_days = (current_bar - entry_bar) * 4 / 24
                        logger.info(f"ETH SWING Close ({reason}) @ ${eth_price:.2f} - PnL: {current_pnl_pct*100:.2f}% - Hold: {hold_days:.1f} days")
                        
        except Exception as e:
            logger.error(f"Error en gestión de riesgo swing: {e}")

class SwingPortfolio:
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
    logger.info("Iniciando Sistema Swing Trading ROI 15%")
    
    system = SwingTradingROISystem(initial_capital=500)
    results = system.run_swing_backtest()
    
    if not results.empty:
        print(f"\nSistema swing trading completado!")
        print(f"Resultados guardados en: swing_trading_roi_results.csv")
        print(f"Log guardado en: swing_trading_roi_system.log")
    else:
        print("Error en el sistema swing trading")

if __name__ == "__main__":
    main()