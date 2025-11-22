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
        logging.FileHandler('balanced_final_roi_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BalancedFinalROISystem:
    def __init__(self, initial_capital=500):
        self.initial_capital = initial_capital
        self.total_trades = 0
        self.total_fees_paid = 0.0
        self.fee_rate = 0.001  # 0.1% por operación
        
        # Umbrales equilibrados para generar operaciones de calidad
        self.signal_threshold = 0.25  # Reducido para permitir más operaciones
        self.confidence_threshold = 0.3  # Reducido para permitir más operaciones
        self.quality_threshold = 0.15  # Reducido para permitir más operaciones
        
        # Gestión de riesgo optimizada
        self.position_size_pct = 0.25  # 25% del capital por posición
        self.stop_loss_pct = 0.025  # 2.5% stop-loss
        self.take_profit_pct = 0.12  # 12% take-profit (ratio 1:4.8)
        
        # Parámetros de trading equilibrados
        self.min_hold_periods = 3  # Mínimo 3 períodos
        self.max_hold_periods = 40  # Máximo 40 períodos
        self.min_bars_between_trades = 3  # Mínimo 3 barras entre operaciones
        
        # Filtros equilibrados
        self.min_volume_ratio = 1.1  # Volumen mínimo reducido
        self.volatility_min = 0.008  # Volatilidad mínima reducida
        self.volatility_max = 0.12  # Volatilidad máxima aumentada
        self.trend_strength_min = 0.3  # Tendencia reducida
        
        # Métricas de rendimiento
        self.winning_trades = 0
        self.losing_trades = 0
        self.max_consecutive_losses = 0
        self.current_consecutive_losses = 0
        self.last_trade_bar = -10
        
        # Control de capital equilibrado
        self.max_positions = 2  # Máximo 2 posiciones simultáneas
        self.capital_preservation_mode = False
        self.drawdown_threshold = 0.12  # 12% drawdown máximo
        
    def calculate_indicators(self, df):
        """Calcula indicadores técnicos esenciales"""
        try:
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 0.0001)
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            df['macd'] = exp1 - exp2
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Bollinger Bands
            bb_middle = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = bb_middle + (bb_std * 2)
            df['bb_lower'] = bb_middle - (bb_std * 2)
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / bb_middle
            
            # Medias móviles
            for period in [10, 20, 50]:
                df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
                df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
            
            # Momentum
            for period in [5, 10, 20]:
                df[f'momentum_{period}'] = df['close'] / df['close'].shift(period) - 1
            
            # Volatilidad
            df['volatility'] = df['close'].rolling(window=20).std() / df['close'].rolling(window=20).mean()
            
            # ATR
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['atr'] = true_range.rolling(window=14).mean()
            df['atr_pct'] = df['atr'] / df['close']
            
            # Volumen
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
            # Tendencia
            df['trend_sma'] = np.where(df['sma_10'] > df['sma_20'], 1, -1)
            df['trend_ema'] = np.where(df['ema_10'] > df['ema_20'], 1, -1)
            df['trend_macd'] = np.where(df['macd'] > df['macd_signal'], 1, -1)
            df['trend_price'] = np.where(df['close'] > df['sma_20'], 1, -1)
            
            # Fuerza de tendencia
            df['trend_strength'] = (df['trend_sma'] + df['trend_ema'] + 
                                  df['trend_macd'] + df['trend_price']) / 4
            
            # Rellenar valores NaN
            df = df.fillna(method='ffill').fillna(0)
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculando indicadores: {e}")
            return df
    
    def generate_balanced_signal(self, df, i):
        """Genera señales equilibradas de buena calidad"""
        try:
            if i < 50:  # Necesitamos datos suficientes
                return 0.0, 0.0, 0.0
            
            current = df.iloc[i]
            prev = df.iloc[i-1]
            
            # Verificar frecuencia de operaciones
            if i - self.last_trade_bar < self.min_bars_between_trades:
                return 0.0, 0.0, 0.0
            
            # Verificar modo de preservación de capital
            if self.capital_preservation_mode:
                return 0.0, 0.0, 0.0
            
            signals = []
            confidences = []
            
            # 1. FILTRO DE TENDENCIA (EQUILIBRADO)
            trend_strength = current['trend_strength']
            if abs(trend_strength) < self.trend_strength_min:
                return 0.0, 0.0, 0.0
            
            # 2. FILTRO DE VOLATILIDAD (EQUILIBRADO)
            volatility = current['volatility']
            if volatility < self.volatility_min or volatility > self.volatility_max:
                return 0.0, 0.0, 0.0
            
            # 3. FILTRO DE VOLUMEN (EQUILIBRADO)
            volume_ratio = current['volume_ratio']
            if volume_ratio < self.min_volume_ratio:
                return 0.0, 0.0, 0.0
            
            # 4. SEÑAL RSI
            rsi = current['rsi']
            if 20 < rsi < 40:  # Zona de sobreventa
                signals.append(0.6)
                confidences.append(0.7)
            elif 60 < rsi < 80:  # Zona de sobrecompra
                signals.append(-0.6)
                confidences.append(0.7)
            elif 40 < rsi < 60:  # Zona neutral
                signals.append(0.2)
                confidences.append(0.4)
            else:
                return 0.0, 0.0, 0.0
            
            # 5. SEÑAL MACD
            if (current['macd'] > current['macd_signal'] and 
                prev['macd'] <= prev['macd_signal']):
                signals.append(0.7)
                confidences.append(0.8)
            elif current['macd'] > current['macd_signal']:
                signals.append(0.4)
                confidences.append(0.5)
            else:
                signals.append(0.1)
                confidences.append(0.3)
            
            # 6. SEÑAL BOLLINGER BANDS
            bb_pos = current['bb_position']
            if bb_pos < 0.2:  # Cerca del límite inferior
                signals.append(0.5)
                confidences.append(0.6)
            elif bb_pos > 0.8:  # Cerca del límite superior
                signals.append(-0.5)
                confidences.append(0.6)
            elif 0.3 < bb_pos < 0.7:  # Zona media
                signals.append(0.2)
                confidences.append(0.4)
            else:
                signals.append(0.1)
                confidences.append(0.2)
            
            # 7. SEÑAL MOMENTUM
            momentum = current['momentum_10']
            if momentum > 0.01:
                signals.append(0.4)
                confidences.append(0.5)
            elif momentum > 0:
                signals.append(0.2)
                confidences.append(0.3)
            else:
                signals.append(0.1)
                confidences.append(0.2)
            
            # 8. COMBINACIÓN FINAL
            if len(signals) >= 3:  # Mínimo 3 señales
                final_signal = np.mean(signals)
                final_confidence = np.mean(confidences)
                
                # Boost por volumen
                volume_boost = min(volume_ratio / self.min_volume_ratio, 1.3)
                final_confidence *= volume_boost
                
                # Boost por tendencia
                trend_boost = min(abs(trend_strength) / self.trend_strength_min, 1.2)
                final_confidence *= trend_boost
                
                # Calcular calidad
                quality_score = final_confidence * (len(signals) / 4) * trend_boost
                
                # Aplicar umbrales equilibrados
                if (abs(final_signal) >= self.signal_threshold and 
                    final_confidence >= self.confidence_threshold and 
                    quality_score >= self.quality_threshold):
                    
                    return final_signal, final_confidence, quality_score
            
            return 0.0, 0.0, 0.0
            
        except Exception as e:
            logger.error(f"Error generando señal equilibrada: {e}")
            return 0.0, 0.0, 0.0
    
    def calculate_position_size(self, signal, confidence, quality_score, current_capital, volatility):
        """Calcula tamaño de posición equilibrado"""
        try:
            # Tamaño base
            base_size = self.position_size_pct
            
            # Ajustar por calidad de señal
            quality_multiplier = min(quality_score / self.quality_threshold, 1.3)
            
            # Ajustar por confianza
            confidence_multiplier = min(confidence / self.confidence_threshold, 1.2)
            
            # Ajustar por volatilidad
            volatility_multiplier = 1.0
            if volatility > 0.05:
                volatility_multiplier = 0.8
            elif volatility < 0.02:
                volatility_multiplier = 1.1
            
            # Ajustar por racha de pérdidas
            loss_multiplier = 1.0
            if self.current_consecutive_losses >= 2:
                loss_multiplier = 0.7
            elif self.current_consecutive_losses == 1:
                loss_multiplier = 0.9
            
            # Calcular tamaño final
            position_fraction = (base_size * quality_multiplier * confidence_multiplier * 
                               volatility_multiplier * loss_multiplier)
            
            # Limitar al máximo
            position_fraction = min(position_fraction, 0.35)  # Máximo 35%
            
            # Calcular valor en USD
            position_value = current_capital * position_fraction
            
            return max(position_value, 25)  # Mínimo $25
            
        except Exception as e:
            logger.error(f"Error calculando tamaño de posición: {e}")
            return 0.0
    
    def calculate_risk_levels(self, price, volatility, atr, signal_strength):
        """Calcula niveles de riesgo equilibrados"""
        try:
            # Stop-loss equilibrado
            base_stop = self.stop_loss_pct
            volatility_stop = volatility * 1.5
            atr_stop = (atr / price) * 1.8 if atr > 0 else base_stop
            
            stop_loss_pct = max(base_stop, min(volatility_stop, atr_stop, 0.05))
            
            # Take-profit equilibrado
            base_tp = self.take_profit_pct
            signal_multiplier = min(abs(signal_strength) / 0.3, 1.4)
            take_profit_pct = base_tp * signal_multiplier
            
            # Asegurar ratio mínimo 1:3.5
            min_tp = stop_loss_pct * 3.5
            take_profit_pct = max(take_profit_pct, min_tp)
            
            # Limitar TP máximo
            take_profit_pct = min(take_profit_pct, 0.20)  # Máximo 20%
            
            return stop_loss_pct, take_profit_pct
            
        except Exception as e:
            logger.error(f"Error calculando niveles de riesgo: {e}")
            return self.stop_loss_pct, self.take_profit_pct
    
    def run_balanced_backtest(self):
        """Ejecuta el backtest equilibrado"""
        try:
            logger.info("Iniciando BACKTEST EQUILIBRADO FINAL para ROI 15% mensual")
            
            # Importar y usar el fetcher de datos
            from robust_data_fetcher import RobustDataFetcher
            
            # Crear fetcher
            fetcher = RobustDataFetcher()
            
            # Obtener datos históricos
            logger.info("Obteniendo datos historicos...")
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
            
            # Calcular indicadores
            btc_data = self.calculate_indicators(btc_data)
            eth_data = self.calculate_indicators(eth_data)
            
            # Inicializar portfolio
            portfolio = BalancedPortfolio(self.initial_capital)
            results = []
            
            logger.info(f"Procesando {len(btc_data)} periodos con análisis equilibrado")
            
            for i in range(len(btc_data)):
                if i >= len(eth_data):
                    break
                    
                current_time = btc_data.iloc[i]['timestamp']
                
                # Verificar preservación de capital
                portfolio_summary = portfolio.get_portfolio_summary()
                self.check_capital_preservation(portfolio_summary['total_value'])
                
                # Procesar BTC
                btc_price = btc_data.iloc[i]['close']
                btc_volatility = btc_data.iloc[i]['volatility']
                btc_atr = btc_data.iloc[i]['atr']
                btc_signal, btc_confidence, btc_quality = self.generate_balanced_signal(btc_data, i)
                
                # Procesar ETH
                eth_price = eth_data.iloc[i]['close']
                eth_volatility = eth_data.iloc[i]['volatility']
                eth_atr = eth_data.iloc[i]['atr']
                eth_signal, eth_confidence, eth_quality = self.generate_balanced_signal(eth_data, i)
                
                # Gestión de riesgo
                self.manage_risk(portfolio, btc_price, eth_price, i)
                
                # Verificar límite de posiciones
                active_positions = len(portfolio.positions)
                
                # Evaluar nuevas entradas BTC
                if (btc_signal != 0.0 and btc_confidence != 0.0 and btc_quality != 0.0 and 
                    active_positions < self.max_positions):
                    
                    position_size = self.calculate_position_size(
                        btc_signal, btc_confidence, btc_quality, portfolio.cash, btc_volatility
                    )
                    
                    if btc_signal > 0 and position_size > 20 and not portfolio.has_position('BTCUSDT'):
                        stop_loss_pct, take_profit_pct = self.calculate_risk_levels(
                            btc_price, btc_volatility, btc_atr, btc_signal
                        )
                        
                        fees = self.execute_trade(portfolio, 'BTCUSDT', btc_price, position_size, 'buy', stop_loss_pct, take_profit_pct, i)
                        self.last_trade_bar = i
                        logger.info(f"BTC LONG @ ${btc_price:.2f} - Size: ${position_size:.2f} - SL: {stop_loss_pct*100:.1f}% - TP: {take_profit_pct*100:.1f}% - Q: {btc_quality:.2f}")
                
                # Evaluar nuevas entradas ETH
                if (eth_signal != 0.0 and eth_confidence != 0.0 and eth_quality != 0.0 and 
                    active_positions < self.max_positions):
                    
                    position_size = self.calculate_position_size(
                        eth_signal, eth_confidence, eth_quality, portfolio.cash, eth_volatility
                    )
                    
                    if eth_signal > 0 and position_size > 20 and not portfolio.has_position('ETHUSDT'):
                        stop_loss_pct, take_profit_pct = self.calculate_risk_levels(
                            eth_price, eth_volatility, eth_atr, eth_signal
                        )
                        
                        fees = self.execute_trade(portfolio, 'ETHUSDT', eth_price, position_size, 'buy', stop_loss_pct, take_profit_pct, i)
                        self.last_trade_bar = i
                        logger.info(f"ETH LONG @ ${eth_price:.2f} - Size: ${position_size:.2f} - SL: {stop_loss_pct*100:.1f}% - TP: {take_profit_pct*100:.1f}% - Q: {eth_quality:.2f}")
                
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
                    'active_positions': active_positions
                })
                
                # Log progreso
                if i % 100 == 0:
                    win_rate = self.winning_trades / max(self.total_trades, 1) if self.total_trades > 0 else 0
                    logger.info(f"Periodo {i}/{len(btc_data)} - Valor: ${portfolio_summary['total_value']:.2f} - Operaciones: {self.total_trades} - Win Rate: {win_rate*100:.1f}%")
            
            # Crear DataFrame de resultados
            results_df = pd.DataFrame(results)
            
            if not results_df.empty:
                # Guardar resultados
                results_df.to_csv('balanced_final_roi_results.csv', index=False)
                
                # Calcular métricas finales
                final_summary = portfolio.get_portfolio_summary()
                net_pnl = final_summary['total_pnl'] - self.total_fees_paid
                net_return = net_pnl / self.initial_capital
                
                # Calcular ROI mensual
                duration_days = (results_df['timestamp'].max() - results_df['timestamp'].min()).days
                duration_months = duration_days / 30.44
                monthly_roi = (((final_summary['total_value'] - self.total_fees_paid) / self.initial_capital) ** (1/duration_months) - 1) if duration_months > 0 else 0
                
                # Métricas
                win_rate = self.winning_trades / max(self.total_trades, 1) if self.total_trades > 0 else 0
                
                # Drawdown máximo
                portfolio_values = results_df['portfolio_value'].values
                peak = np.maximum.accumulate(portfolio_values)
                drawdown = (peak - portfolio_values) / peak
                max_drawdown = np.max(drawdown)
                
                logger.info("=" * 80)
                logger.info("RESUMEN FINAL - SISTEMA EQUILIBRADO ROI 15%")
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
                logger.info(f"Max drawdown: {max_drawdown*100:.1f}%")
                logger.info(f"Duracion: {duration_days} dias ({duration_months:.1f} meses)")
                
                # Verificar objetivo
                target_roi = 0.15  # 15% mensual
                if monthly_roi >= target_roi:
                    logger.info("=" * 80)
                    logger.info(f"🎯 OBJETIVO ALCANZADO! ROI mensual: {monthly_roi*100:.2f}% >= {target_roi*100:.0f}%")
                    logger.info("🏆 SISTEMA EQUILIBRADO EXITOSO!")
                    logger.info("=" * 80)
                else:
                    gap = target_roi - monthly_roi
                    logger.info("=" * 80)
                    logger.info(f"❌ Objetivo no alcanzado. Gap: {gap*100:.2f}% para llegar al {target_roi*100:.0f}%")
                    logger.info("=" * 80)
                
                return results_df
            else:
                logger.error("No se generaron resultados")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error en backtest equilibrado: {e}")
            return pd.DataFrame()
    
    def execute_trade(self, portfolio, symbol, price, position_size, action, stop_loss_pct, take_profit_pct, entry_bar):
        """Ejecuta una operación"""
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
            logger.error(f"Error ejecutando trade: {e}")
            return 0.0
    
    def manage_risk(self, portfolio, btc_price, eth_price, current_bar):
        """Gestiona el riesgo"""
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
                    logger.info(f"BTC Stop Loss @ ${btc_price:.2f} - Loss: {current_pnl_pct*100:.2f}%")
                
                # Take-profit
                elif btc_price >= position['take_profit_price']:
                    portfolio.close_position('BTCUSDT', btc_price)
                    self.winning_trades += 1
                    self.current_consecutive_losses = 0
                    logger.info(f"BTC Take Profit @ ${btc_price:.2f} - Profit: {current_pnl_pct*100:.2f}%")
                
                # Cierre por tiempo máximo
                elif hold_periods >= self.max_hold_periods:
                    portfolio.close_position('BTCUSDT', btc_price)
                    if current_pnl_pct > 0:
                        self.winning_trades += 1
                        self.current_consecutive_losses = 0
                    else:
                        self.losing_trades += 1
                        self.current_consecutive_losses += 1
                    logger.info(f"BTC Max Time @ ${btc_price:.2f} - PnL: {current_pnl_pct*100:.2f}%")
            
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
                    logger.info(f"ETH Stop Loss @ ${eth_price:.2f} - Loss: {current_pnl_pct*100:.2f}%")
                
                elif eth_price >= position['take_profit_price']:
                    portfolio.close_position('ETHUSDT', eth_price)
                    self.winning_trades += 1
                    self.current_consecutive_losses = 0
                    logger.info(f"ETH Take Profit @ ${eth_price:.2f} - Profit: {current_pnl_pct*100:.2f}%")
                
                elif hold_periods >= self.max_hold_periods:
                    portfolio.close_position('ETHUSDT', eth_price)
                    if current_pnl_pct > 0:
                        self.winning_trades += 1
                        self.current_consecutive_losses = 0
                    else:
                        self.losing_trades += 1
                        self.current_consecutive_losses += 1
                    logger.info(f"ETH Max Time @ ${eth_price:.2f} - PnL: {current_pnl_pct*100:.2f}%")
                        
        except Exception as e:
            logger.error(f"Error en gestión de riesgo: {e}")
    
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

class BalancedPortfolio:
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
    logger.info("🚀 Iniciando SISTEMA EQUILIBRADO FINAL ROI 15%")
    
    system = BalancedFinalROISystem(initial_capital=500)
    results = system.run_balanced_backtest()
    
    if not results.empty:
        print(f"\n🎯 Sistema equilibrado final completado!")
        print(f"📊 Resultados guardados en: balanced_final_roi_results.csv")
        print(f"📝 Log guardado en: balanced_final_roi_system.log")
    else:
        print("❌ Error en el sistema equilibrado final")

if __name__ == "__main__":
    main()