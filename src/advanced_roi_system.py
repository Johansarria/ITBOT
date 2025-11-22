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
        logging.FileHandler('advanced_roi_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AdvancedROISystem:
    def __init__(self, initial_capital=500):
        self.initial_capital = initial_capital
        self.total_trades = 0
        self.total_fees_paid = 0.0
        self.fee_rate = 0.001  # 0.1% por operación
        
        # Umbrales más selectivos para mejor calidad
        self.signal_threshold = 0.4  # Más alto para mejor calidad
        self.confidence_threshold = 0.6  # Más alto para mejor confianza
        self.quality_threshold = 0.5  # Más alto para mejor calidad
        
        # Gestión de riesgo avanzada
        self.max_position_size = 0.25  # 25% del capital por posición
        self.dynamic_stop_loss = True
        self.trailing_stop = True
        self.position_sizing_method = 'kelly'  # Kelly Criterion
        
        # Parámetros de mercado
        self.min_volatility = 0.01  # Volatilidad mínima para operar
        self.max_volatility = 0.08  # Volatilidad máxima para operar
        self.trend_confirmation_periods = 3  # Períodos para confirmar tendencia
        
        # Métricas de rendimiento
        self.winning_trades = 0
        self.losing_trades = 0
        self.max_consecutive_losses = 0
        self.current_consecutive_losses = 0
        
    def calculate_advanced_indicators(self, df, symbol):
        """Calcula indicadores técnicos avanzados"""
        try:
            # RSI con múltiples períodos
            for period in [14, 21]:
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
                rs = gain / loss
                df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
            
            # MACD con configuración optimizada
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            df['macd'] = exp1 - exp2
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Bollinger Bands con múltiples desviaciones
            for std_dev in [1.5, 2.0, 2.5]:
                bb_middle = df['close'].rolling(window=20).mean()
                bb_std = df['close'].rolling(window=20).std()
                df[f'bb_upper_{std_dev}'] = bb_middle + (bb_std * std_dev)
                df[f'bb_lower_{std_dev}'] = bb_middle - (bb_std * std_dev)
                df[f'bb_position_{std_dev}'] = (df['close'] - df[f'bb_lower_{std_dev}']) / (df[f'bb_upper_{std_dev}'] - df[f'bb_lower_{std_dev}'])
            
            # Indicadores de momentum
            df['momentum_10'] = df['close'] / df['close'].shift(10) - 1
            df['momentum_20'] = df['close'] / df['close'].shift(20) - 1
            df['rate_of_change'] = df['close'].pct_change(periods=10)
            
            # Volatilidad y ATR
            df['volatility'] = df['close'].rolling(window=20).std() / df['close'].rolling(window=20).mean()
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['atr'] = true_range.rolling(window=14).mean()
            
            # Indicadores de volumen
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            df['volume_trend'] = df['volume'].rolling(window=5).mean() / df['volume'].rolling(window=20).mean()
            
            # Soporte y resistencia dinámicos
            df['resistance'] = df['high'].rolling(window=20).max()
            df['support'] = df['low'].rolling(window=20).min()
            df['support_resistance_ratio'] = (df['close'] - df['support']) / (df['resistance'] - df['support'])
            
            # Tendencia de largo plazo
            df['ema_50'] = df['close'].ewm(span=50).mean()
            df['ema_200'] = df['close'].ewm(span=200).mean()
            df['trend_long'] = np.where(df['ema_50'] > df['ema_200'], 1, -1)
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculando indicadores para {symbol}: {e}")
            return df
    
    def generate_advanced_signal(self, df, i, symbol):
        """Genera señales avanzadas con múltiples confirmaciones"""
        try:
            if i < 50:  # Necesitamos más datos para indicadores avanzados
                return 0.0, 0.0, 0.0
            
            current = df.iloc[i]
            prev = df.iloc[i-1]
            
            # Verificar condiciones de mercado
            if current['volatility'] < self.min_volatility or current['volatility'] > self.max_volatility:
                return 0.0, 0.0, 0.0  # Volatilidad fuera de rango
            
            signals = []
            confidences = []
            
            # Señal RSI multi-período
            rsi_14 = current['rsi_14']
            rsi_21 = current['rsi_21']
            
            if rsi_14 < 30 and rsi_21 < 35:  # Sobreventa confirmada
                signals.append(0.8)
                confidences.append(0.7)
            elif rsi_14 > 70 and rsi_21 > 65:  # Sobrecompra confirmada
                signals.append(-0.8)
                confidences.append(0.7)
            elif 40 < rsi_14 < 60 and 40 < rsi_21 < 60:  # Zona neutral
                signals.append(0.1)
                confidences.append(0.3)
            
            # Señal MACD con confirmación
            if (current['macd'] > current['macd_signal'] and 
                prev['macd'] <= prev['macd_signal'] and 
                current['macd_histogram'] > 0):
                signals.append(0.7)
                confidences.append(0.8)
            elif (current['macd'] < current['macd_signal'] and 
                  prev['macd'] >= prev['macd_signal'] and 
                  current['macd_histogram'] < 0):
                signals.append(-0.7)
                confidences.append(0.8)
            
            # Señal Bollinger Bands con múltiples niveles
            bb_signals = []
            for std_dev in [1.5, 2.0, 2.5]:
                bb_pos = current[f'bb_position_{std_dev}']
                if bb_pos < 0.1:  # Cerca del límite inferior
                    bb_signals.append(0.6 * (2.5 - std_dev + 1))  # Más peso a BB más estrechas
                elif bb_pos > 0.9:  # Cerca del límite superior
                    bb_signals.append(-0.6 * (2.5 - std_dev + 1))
            
            if bb_signals:
                signals.append(np.mean(bb_signals))
                confidences.append(0.6)
            
            # Señal de momentum con confirmación
            if current['momentum_10'] > 0.03 and current['momentum_20'] > 0.02:
                signals.append(0.5)
                confidences.append(0.5)
            elif current['momentum_10'] < -0.03 and current['momentum_20'] < -0.02:
                signals.append(-0.5)
                confidences.append(0.5)
            
            # Señal de volumen
            if current['volume_ratio'] > 1.5 and current['volume_trend'] > 1.2:
                signals.append(0.3)
                confidences.append(0.4)
            elif current['volume_ratio'] < 0.7:
                signals.append(-0.2)
                confidences.append(0.3)
            
            # Señal de soporte/resistencia
            sr_ratio = current['support_resistance_ratio']
            if sr_ratio < 0.2:  # Cerca del soporte
                signals.append(0.4)
                confidences.append(0.5)
            elif sr_ratio > 0.8:  # Cerca de la resistencia
                signals.append(-0.4)
                confidences.append(0.5)
            
            # Confirmación de tendencia
            trend_signal = 0.0
            if current['trend_long'] == 1:  # Tendencia alcista
                trend_signal = 0.2
            elif current['trend_long'] == -1:  # Tendencia bajista
                trend_signal = -0.2
            
            # Combinar señales con pesos adaptativos
            if signals:
                final_signal = np.mean(signals) + trend_signal
                final_confidence = np.mean(confidences)
                
                # Ajustar por volatilidad
                volatility_factor = 1.0
                if current['volatility'] > 0.05:
                    volatility_factor = 0.8  # Reducir confianza en alta volatilidad
                elif current['volatility'] < 0.02:
                    volatility_factor = 1.2  # Aumentar confianza en baja volatilidad
                
                final_confidence *= volatility_factor
                
                # Calcular calidad basada en convergencia
                signal_std = np.std(signals) if len(signals) > 1 else 0.5
                quality_score = final_confidence * (1 - signal_std) * len(signals) / 6
                
                return final_signal, final_confidence, quality_score
            
            return 0.0, 0.0, 0.0
            
        except Exception as e:
            logger.error(f"Error generando señal para {symbol}: {e}")
            return 0.0, 0.0, 0.0
    
    def calculate_dynamic_position_size(self, signal, confidence, quality_score, current_capital, volatility):
        """Calcula tamaño de posición usando Kelly Criterion modificado"""
        try:
            # Kelly Criterion básico
            win_rate = self.winning_trades / max(self.total_trades, 1) if self.total_trades > 0 else 0.5
            avg_win = 0.06  # 6% ganancia promedio esperada
            avg_loss = 0.03  # 3% pérdida promedio esperada
            
            if win_rate > 0 and avg_loss > 0:
                kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
                kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Limitar entre 0 y 25%
            else:
                kelly_fraction = 0.1  # Fracción conservadora por defecto
            
            # Ajustar por confianza y calidad
            confidence_multiplier = min(confidence / 0.6, 1.5)
            quality_multiplier = min(quality_score / 0.5, 1.3)
            signal_multiplier = min(abs(signal) / 0.5, 1.2)
            
            # Ajustar por volatilidad (menor posición en alta volatilidad)
            volatility_multiplier = 1.0
            if volatility > 0.05:
                volatility_multiplier = 0.7
            elif volatility < 0.02:
                volatility_multiplier = 1.2
            
            # Ajustar por racha de pérdidas
            loss_multiplier = 1.0
            if self.current_consecutive_losses > 2:
                loss_multiplier = 0.5  # Reducir posición después de pérdidas consecutivas
            elif self.current_consecutive_losses == 0:
                loss_multiplier = 1.1  # Aumentar ligeramente después de ganar
            
            # Calcular tamaño final
            position_fraction = (kelly_fraction * confidence_multiplier * quality_multiplier * 
                               signal_multiplier * volatility_multiplier * loss_multiplier)
            
            # Limitar al máximo permitido
            position_fraction = min(position_fraction, self.max_position_size)
            
            # Calcular valor en USD
            position_value = current_capital * position_fraction
            
            return max(position_value, 10)  # Mínimo $10
            
        except Exception as e:
            logger.error(f"Error calculando tamaño de posición: {e}")
            return 0.0
    
    def calculate_dynamic_stop_loss(self, entry_price, volatility, atr):
        """Calcula stop-loss dinámico basado en volatilidad y ATR"""
        try:
            # Stop-loss base
            base_stop = 0.025  # 2.5%
            
            # Ajustar por volatilidad
            if volatility > 0.05:
                volatility_stop = volatility * 0.8  # 80% de la volatilidad
            else:
                volatility_stop = base_stop
            
            # Ajustar por ATR
            atr_stop = (atr / entry_price) * 1.5  # 1.5x ATR
            
            # Usar el mayor de los tres
            dynamic_stop = max(base_stop, volatility_stop, atr_stop)
            
            # Limitar entre 1.5% y 5%
            dynamic_stop = max(0.015, min(dynamic_stop, 0.05))
            
            return dynamic_stop
            
        except Exception as e:
            logger.error(f"Error calculando stop-loss dinámico: {e}")
            return 0.025
    
    def run_advanced_backtest(self):
        """Ejecuta el backtest avanzado"""
        try:
            logger.info("Iniciando backtest avanzado para ROI 15% mensual")
            
            # Importar y usar el fetcher de datos
            from robust_data_fetcher import RobustDataFetcher
            
            # Crear fetcher
            fetcher = RobustDataFetcher()
            
            # Obtener datos históricos
            logger.info("Obteniendo datos historicos...")
            btc_data = fetcher.get_market_data('BTCUSDT', '4h', 500)
            eth_data = fetcher.get_market_data('ETHUSDT', '4h', 500)
            
            if btc_data is None or eth_data is None or btc_data.empty or eth_data.empty:
                logger.error("No se pudieron obtener datos historicos")
                return pd.DataFrame()
            
            # Normalizar nombres de columnas a minúsculas
            btc_data.columns = [col.lower() for col in btc_data.columns]
            eth_data.columns = [col.lower() for col in eth_data.columns]
            
            # Resetear índice para tener timestamp como columna
            btc_data = btc_data.reset_index()
            eth_data = eth_data.reset_index()
            
            # Agregar columna de volumen si no existe
            if 'volume' not in btc_data.columns:
                btc_data['volume'] = 1000000  # Volumen dummy
            if 'volume' not in eth_data.columns:
                eth_data['volume'] = 1000000  # Volumen dummy
            
            logger.info(f"Datos BTC: {len(btc_data)} registros")
            logger.info(f"Datos ETH: {len(eth_data)} registros")
            
            # Calcular indicadores avanzados
            btc_data = self.calculate_advanced_indicators(btc_data, 'BTCUSDT')
            eth_data = self.calculate_advanced_indicators(eth_data, 'ETHUSDT')
            
            # Alinear datos por timestamp
            merged_data = pd.merge(btc_data, eth_data, on='timestamp', suffixes=('_btc', '_eth'))
            
            # Inicializar portfolio avanzado
            portfolio = AdvancedPortfolio(self.initial_capital)
            results = []
            
            logger.info(f"Procesando {len(merged_data)} periodos de datos")
            
            for i in range(len(merged_data)):
                current_time = merged_data.iloc[i]['timestamp']
                
                # Procesar BTC
                btc_price = merged_data.iloc[i]['close_btc']
                btc_volatility = merged_data.iloc[i]['volatility_btc']
                btc_atr = merged_data.iloc[i]['atr_btc']
                btc_signal, btc_confidence, btc_quality = self.generate_advanced_signal(
                    btc_data, i, 'BTCUSDT'
                )
                
                # Procesar ETH
                eth_price = merged_data.iloc[i]['close_eth']
                eth_volatility = merged_data.iloc[i]['volatility_eth']
                eth_atr = merged_data.iloc[i]['atr_eth']
                eth_signal, eth_confidence, eth_quality = self.generate_advanced_signal(
                    eth_data, i, 'ETHUSDT'
                )
                
                # Gestión de riesgo avanzada
                self.manage_advanced_risk(portfolio, btc_price, eth_price, btc_volatility, eth_volatility, btc_atr, eth_atr)
                
                # Evaluar operaciones para BTC
                if (abs(btc_signal) > self.signal_threshold and 
                    btc_confidence > self.confidence_threshold and 
                    btc_quality > self.quality_threshold):
                    
                    position_size = self.calculate_dynamic_position_size(
                        btc_signal, btc_confidence, btc_quality, portfolio.cash, btc_volatility
                    )
                    
                    if btc_signal > 0 and position_size > 10 and not portfolio.has_position('BTCUSDT'):
                        # Calcular stop-loss dinámico
                        stop_loss_pct = self.calculate_dynamic_stop_loss(btc_price, btc_volatility, btc_atr)
                        take_profit_pct = stop_loss_pct * 2  # Risk-reward 1:2
                        
                        fees = self.execute_advanced_trade(portfolio, 'BTCUSDT', btc_price, position_size, 'buy', stop_loss_pct, take_profit_pct)
                        logger.info(f"BTC LONG @ ${btc_price:.2f} - Size: ${position_size:.2f} - SL: {stop_loss_pct*100:.1f}% - TP: {take_profit_pct*100:.1f}% - Fee: ${fees:.2f}")
                
                # Evaluar operaciones para ETH
                if (abs(eth_signal) > self.signal_threshold and 
                    eth_confidence > self.confidence_threshold and 
                    eth_quality > self.quality_threshold):
                    
                    position_size = self.calculate_dynamic_position_size(
                        eth_signal, eth_confidence, eth_quality, portfolio.cash, eth_volatility
                    )
                    
                    if eth_signal > 0 and position_size > 10 and not portfolio.has_position('ETHUSDT'):
                        # Calcular stop-loss dinámico
                        stop_loss_pct = self.calculate_dynamic_stop_loss(eth_price, eth_volatility, eth_atr)
                        take_profit_pct = stop_loss_pct * 2  # Risk-reward 1:2
                        
                        fees = self.execute_advanced_trade(portfolio, 'ETHUSDT', eth_price, position_size, 'buy', stop_loss_pct, take_profit_pct)
                        logger.info(f"ETH LONG @ ${eth_price:.2f} - Size: ${position_size:.2f} - SL: {stop_loss_pct*100:.1f}% - TP: {take_profit_pct*100:.1f}% - Fee: ${fees:.2f}")
                
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
                    'fees_paid': self.total_fees_paid,
                    'win_rate': self.winning_trades / max(self.total_trades, 1)
                })
                
                # Log progreso
                if i % 50 == 0:
                    logger.info(f"Periodo {i}/{len(merged_data)} - Valor: ${portfolio_summary['total_value']:.2f} - Operaciones: {self.total_trades} - Win Rate: {(self.winning_trades / max(self.total_trades, 1))*100:.1f}%")
            
            # Crear DataFrame de resultados
            results_df = pd.DataFrame(results)
            
            if not results_df.empty:
                # Guardar resultados
                results_df.to_csv('advanced_roi_results.csv', index=False)
                
                # Calcular métricas finales
                final_summary = portfolio.get_portfolio_summary()
                net_pnl = final_summary['total_pnl'] - self.total_fees_paid
                net_return = net_pnl / self.initial_capital
                
                # Calcular ROI mensual
                duration_days = (results_df['timestamp'].max() - results_df['timestamp'].min()).days
                duration_months = duration_days / 30.44
                monthly_roi = (((final_summary['total_value'] - self.total_fees_paid) / self.initial_capital) ** (1/duration_months) - 1) if duration_months > 0 else 0
                
                # Calcular métricas avanzadas
                win_rate = self.winning_trades / max(self.total_trades, 1) if self.total_trades > 0 else 0
                avg_win = final_summary['total_pnl'] / max(self.winning_trades, 1) if self.winning_trades > 0 else 0
                avg_loss = abs(final_summary['total_pnl']) / max(self.losing_trades, 1) if self.losing_trades > 0 else 0
                profit_factor = avg_win / max(avg_loss, 0.01)
                
                logger.info("=" * 70)
                logger.info("RESUMEN FINAL - SISTEMA AVANZADO ROI")
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
                logger.info(f"Drawdown maximo: {final_summary['max_drawdown']:.2f}%")
                
                # Verificar objetivo
                target_roi = 0.15  # 15% mensual
                if monthly_roi >= target_roi:
                    logger.info(f"OBJETIVO ALCANZADO! ROI mensual: {monthly_roi*100:.2f}% >= {target_roi*100:.0f}%")
                else:
                    gap = target_roi - monthly_roi
                    logger.info(f"Objetivo no alcanzado. Gap: {gap*100:.2f}% para llegar al {target_roi*100:.0f}%")
                    
                    # Sugerencias específicas
                    if win_rate < 0.6:
                        logger.info("SUGERENCIA: Mejorar filtros de entrada para aumentar win rate")
                    if profit_factor < 1.5:
                        logger.info("SUGERENCIA: Optimizar ratio riesgo/beneficio")
                    if self.max_consecutive_losses > 5:
                        logger.info("SUGERENCIA: Implementar circuit breaker para rachas de perdidas")
                
                return results_df
            else:
                logger.error("No se generaron resultados")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error en backtest avanzado: {e}")
            return pd.DataFrame()
    
    def execute_advanced_trade(self, portfolio, symbol, price, position_size, action, stop_loss_pct, take_profit_pct):
        """Ejecuta una operación avanzada con stop-loss y take-profit"""
        try:
            if action == 'buy' and position_size > 0:
                quantity = position_size / price
                fees = position_size * self.fee_rate
                
                # Calcular niveles de stop-loss y take-profit
                stop_loss_price = price * (1 - stop_loss_pct)
                take_profit_price = price * (1 + take_profit_pct)
                
                portfolio.open_advanced_position(symbol, price, quantity, stop_loss_price, take_profit_price)
                self.total_trades += 1
                self.total_fees_paid += fees
                return fees
            return 0.0
        except Exception as e:
            logger.error(f"Error ejecutando trade avanzado: {e}")
            return 0.0
    
    def manage_advanced_risk(self, portfolio, btc_price, eth_price, btc_volatility, eth_volatility, btc_atr, eth_atr):
        """Gestiona el riesgo de forma avanzada"""
        try:
            # Gestionar BTC
            if portfolio.has_position('BTCUSDT'):
                position = portfolio.positions['BTCUSDT']
                entry_price = position['entry_price']
                current_pnl_pct = (btc_price - entry_price) / entry_price
                
                # Stop-loss dinámico
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
                
                # Trailing stop (opcional)
                elif self.trailing_stop and current_pnl_pct > 0.02:  # Solo si hay ganancia > 2%
                    new_stop_loss = btc_price * (1 - self.calculate_dynamic_stop_loss(btc_price, btc_volatility, btc_atr))
                    if new_stop_loss > position['stop_loss_price']:
                        position['stop_loss_price'] = new_stop_loss
            
            # Gestionar ETH (similar lógica)
            if portfolio.has_position('ETHUSDT'):
                position = portfolio.positions['ETHUSDT']
                entry_price = position['entry_price']
                current_pnl_pct = (eth_price - entry_price) / entry_price
                
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
                
                elif self.trailing_stop and current_pnl_pct > 0.02:
                    new_stop_loss = eth_price * (1 - self.calculate_dynamic_stop_loss(eth_price, eth_volatility, eth_atr))
                    if new_stop_loss > position['stop_loss_price']:
                        position['stop_loss_price'] = new_stop_loss
                        
        except Exception as e:
            logger.error(f"Error en gestión de riesgo avanzada: {e}")

class AdvancedPortfolio:
    def __init__(self, initial_capital):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        self.max_value = initial_capital
        
    def has_position(self, symbol):
        """Verifica si tiene posición en el símbolo"""
        return symbol in self.positions
    
    def open_advanced_position(self, symbol, price, quantity, stop_loss_price, take_profit_price):
        """Abre una posición avanzada con stop-loss y take-profit"""
        cost = price * quantity
        if cost <= self.cash:
            self.cash -= cost
            self.positions[symbol] = {
                'quantity': quantity,
                'entry_price': price,
                'stop_loss_price': stop_loss_price,
                'take_profit_price': take_profit_price,
                'size': quantity
            }
    
    def close_position(self, symbol, price):
        """Cierra una posición"""
        if symbol in self.positions:
            position = self.positions[symbol]
            proceeds = position['quantity'] * price
            self.cash += proceeds
            del self.positions[symbol]
    
    def get_portfolio_summary(self):
        """Obtiene resumen del portfolio"""
        total_value = self.cash
        total_pnl = 0
        
        # Agregar valor de posiciones abiertas
        for symbol, position in self.positions.items():
            position_value = position['quantity'] * position['entry_price']
            total_value += position_value
            total_pnl += position_value - (position['quantity'] * position['entry_price'])
        
        # Actualizar máximo valor
        self.max_value = max(self.max_value, total_value)
        
        # Calcular drawdown
        drawdown = (self.max_value - total_value) / self.max_value * 100
        
        return {
            'total_value': total_value,
            'cash': self.cash,
            'total_pnl': total_pnl,
            'return_pct': (total_value - self.initial_capital) / self.initial_capital * 100,
            'max_drawdown': drawdown
        }

def main():
    """Función principal"""
    logger.info("Iniciando Sistema Avanzado ROI 15%")
    
    system = AdvancedROISystem(initial_capital=500)
    results = system.run_advanced_backtest()
    
    if not results.empty:
        print(f"\nSistema avanzado completado!")
        print(f"Resultados guardados en: advanced_roi_results.csv")
        print(f"Log guardado en: advanced_roi_system.log")
    else:
        print("Error en el sistema avanzado")

if __name__ == "__main__":
    main()