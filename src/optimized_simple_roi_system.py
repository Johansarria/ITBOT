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
        logging.FileHandler('optimized_simple_roi_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OptimizedSimpleROISystem:
    def __init__(self, initial_capital=500):
        self.initial_capital = initial_capital
        self.total_trades = 0
        self.total_fees_paid = 0.0
        self.fee_rate = 0.001  # 0.1% por operación
        
        # Umbrales optimizados para mejor calidad
        self.signal_threshold = 0.3  # Más alto para mejor calidad
        self.confidence_threshold = 0.4  # Más alto para mejor calidad
        self.quality_threshold = 0.25  # Más alto para mejor calidad
        
        # Gestión de riesgo optimizada
        self.position_size_pct = 0.25  # 25% del capital por posición
        self.stop_loss_pct = 0.025  # 2.5% stop-loss (más ajustado)
        self.take_profit_pct = 0.075  # 7.5% take-profit (ratio 1:3)
        
        # Parámetros de filtrado
        self.min_volume_ratio = 1.2  # Volumen mínimo
        self.trend_confirmation = True  # Confirmar tendencia
        self.momentum_filter = True  # Filtro de momentum
        
        # Métricas de rendimiento
        self.winning_trades = 0
        self.losing_trades = 0
        self.max_consecutive_losses = 0
        self.current_consecutive_losses = 0
        
        # Control de frecuencia de operaciones
        self.min_bars_between_trades = 3  # Mínimo 3 barras entre operaciones
        self.last_trade_bar = -10
        
    def calculate_optimized_indicators(self, df):
        """Calcula indicadores técnicos optimizados"""
        try:
            # RSI optimizado
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 0.0001)
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD optimizado
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
            
            # Medias móviles múltiples
            df['sma_10'] = df['close'].rolling(window=10).mean()
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()
            
            # Momentum múltiple
            df['momentum_5'] = df['close'] / df['close'].shift(5) - 1
            df['momentum_10'] = df['close'] / df['close'].shift(10) - 1
            df['momentum_20'] = df['close'] / df['close'].shift(20) - 1
            
            # Volatilidad y ATR
            df['volatility'] = df['close'].rolling(window=20).std() / df['close'].rolling(window=20).mean()
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['atr'] = true_range.rolling(window=14).mean()
            
            # Volumen optimizado
            df['volume_ma_10'] = df['volume'].rolling(window=10).mean()
            df['volume_ma_20'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma_20']
            df['volume_trend'] = df['volume_ma_10'] / df['volume_ma_20']
            
            # Indicadores de tendencia
            df['trend_short'] = np.where(df['sma_10'] > df['sma_20'], 1, -1)
            df['trend_medium'] = np.where(df['sma_20'] > df['sma_50'], 1, -1)
            df['trend_macd'] = np.where(df['macd'] > df['macd_signal'], 1, -1)
            
            # Fuerza de tendencia
            df['trend_strength'] = (df['trend_short'] + df['trend_medium'] + df['trend_macd']) / 3
            
            # Rellenar valores NaN
            df = df.fillna(method='ffill').fillna(0)
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculando indicadores optimizados: {e}")
            return df
    
    def generate_optimized_signal(self, df, i):
        """Genera señales optimizadas con múltiples filtros"""
        try:
            if i < 50:  # Necesitamos datos suficientes
                return 0.0, 0.0, 0.0
            
            current = df.iloc[i]
            prev = df.iloc[i-1]
            
            # Verificar frecuencia de operaciones
            if i - self.last_trade_bar < self.min_bars_between_trades:
                return 0.0, 0.0, 0.0
            
            signals = []
            confidences = []
            
            # 1. Señal RSI con zonas optimizadas
            rsi = current['rsi']
            if 25 < rsi < 35:  # Sobreventa moderada
                signals.append(0.7)
                confidences.append(0.8)
            elif 65 < rsi < 75:  # Sobrecompra moderada
                signals.append(-0.7)
                confidences.append(0.8)
            elif 40 < rsi < 60:  # Zona neutral favorable
                signals.append(0.2)
                confidences.append(0.4)
            else:
                return 0.0, 0.0, 0.0  # Zonas extremas evitadas
            
            # 2. Señal MACD con confirmación
            if (current['macd'] > current['macd_signal'] and 
                prev['macd'] <= prev['macd_signal'] and 
                current['macd_histogram'] > 0):
                signals.append(0.6)
                confidences.append(0.7)
            elif (current['macd'] < current['macd_signal'] and 
                  prev['macd'] >= prev['macd_signal'] and 
                  current['macd_histogram'] < 0):
                signals.append(-0.6)
                confidences.append(0.7)
            
            # 3. Señal Bollinger Bands
            bb_pos = current['bb_position']
            if 0.1 < bb_pos < 0.3:  # Cerca del límite inferior pero no extremo
                signals.append(0.5)
                confidences.append(0.6)
            elif 0.7 < bb_pos < 0.9:  # Cerca del límite superior pero no extremo
                signals.append(-0.5)
                confidences.append(0.6)
            
            # 4. Filtro de tendencia (OBLIGATORIO)
            if self.trend_confirmation:
                trend_strength = current['trend_strength']
                if trend_strength < 0.3:  # Tendencia débil o mixta
                    return 0.0, 0.0, 0.0  # No operar en tendencias débiles
                
                # Ajustar señales según tendencia
                trend_multiplier = min(abs(trend_strength), 1.0)
                signals = [s * trend_multiplier for s in signals]
            
            # 5. Filtro de momentum (OBLIGATORIO)
            if self.momentum_filter:
                momentum_5 = current['momentum_5']
                momentum_10 = current['momentum_10']
                
                # Momentum debe ser consistente
                if momentum_5 * momentum_10 < 0:  # Momentum divergente
                    return 0.0, 0.0, 0.0
                
                # Momentum mínimo requerido
                if abs(momentum_5) < 0.005:  # Menos de 0.5%
                    return 0.0, 0.0, 0.0
            
            # 6. Filtro de volumen (OBLIGATORIO)
            volume_ratio = current['volume_ratio']
            volume_trend = current['volume_trend']
            
            if volume_ratio < self.min_volume_ratio or volume_trend < 1.0:
                return 0.0, 0.0, 0.0  # Volumen insuficiente
            
            # 7. Filtro de volatilidad
            volatility = current['volatility']
            if volatility > 0.08 or volatility < 0.01:  # Volatilidad extrema
                return 0.0, 0.0, 0.0
            
            # Combinar señales si pasaron todos los filtros
            if len(signals) >= 2:  # Mínimo 2 señales confirmatorias
                final_signal = np.mean(signals)
                final_confidence = np.mean(confidences)
                
                # Ajustar por volumen
                volume_boost = min(volume_ratio / self.min_volume_ratio, 1.5)
                final_confidence *= volume_boost
                
                # Ajustar por consistencia de señales
                signal_std = np.std(signals)
                consistency_factor = max(0.5, 1 - signal_std)
                
                # Calcular calidad final
                quality_score = final_confidence * consistency_factor * (len(signals) / 4)
                
                # Aplicar umbrales finales
                if (abs(final_signal) >= self.signal_threshold and 
                    final_confidence >= self.confidence_threshold and 
                    quality_score >= self.quality_threshold):
                    
                    return final_signal, final_confidence, quality_score
            
            return 0.0, 0.0, 0.0
            
        except Exception as e:
            logger.error(f"Error generando señal optimizada: {e}")
            return 0.0, 0.0, 0.0
    
    def calculate_dynamic_position_size(self, signal, confidence, quality_score, current_capital, volatility):
        """Calcula tamaño de posición dinámico"""
        try:
            # Tamaño base
            base_size = self.position_size_pct
            
            # Ajustar por confianza
            confidence_multiplier = min(confidence / self.confidence_threshold, 1.5)
            
            # Ajustar por calidad
            quality_multiplier = min(quality_score / self.quality_threshold, 1.3)
            
            # Ajustar por fuerza de señal
            signal_multiplier = min(abs(signal) / self.signal_threshold, 1.2)
            
            # Ajustar por volatilidad (menor posición en alta volatilidad)
            volatility_multiplier = 1.0
            if volatility > 0.05:
                volatility_multiplier = 0.8
            elif volatility < 0.02:
                volatility_multiplier = 1.1
            
            # Ajustar por racha de pérdidas
            loss_multiplier = 1.0
            if self.current_consecutive_losses > 2:
                loss_multiplier = 0.6  # Reducir significativamente
            elif self.current_consecutive_losses == 0:
                loss_multiplier = 1.1  # Aumentar ligeramente
            
            # Calcular tamaño final
            position_fraction = (base_size * confidence_multiplier * quality_multiplier * 
                               signal_multiplier * volatility_multiplier * loss_multiplier)
            
            # Limitar al máximo
            position_fraction = min(position_fraction, 0.35)  # Máximo 35%
            
            # Calcular valor en USD
            position_value = current_capital * position_fraction
            
            return max(position_value, 20)  # Mínimo $20
            
        except Exception as e:
            logger.error(f"Error calculando tamaño de posición dinámico: {e}")
            return 0.0
    
    def calculate_dynamic_levels(self, price, volatility, atr, signal_strength):
        """Calcula stop-loss y take-profit dinámicos"""
        try:
            # Stop-loss base ajustado por volatilidad
            base_stop = self.stop_loss_pct
            
            if volatility > 0.04:
                volatility_stop = volatility * 1.2
            else:
                volatility_stop = base_stop
            
            # ATR stop
            atr_stop = (atr / price) * 1.8 if atr > 0 else base_stop
            
            # Usar el mayor pero limitado
            stop_loss_pct = max(base_stop, min(volatility_stop, atr_stop, 0.04))
            
            # Take-profit dinámico basado en fuerza de señal
            base_tp = self.take_profit_pct
            signal_multiplier = min(abs(signal_strength) / 0.5, 1.5)
            take_profit_pct = base_tp * signal_multiplier
            
            # Asegurar ratio mínimo 1:2.5
            take_profit_pct = max(take_profit_pct, stop_loss_pct * 2.5)
            
            return stop_loss_pct, take_profit_pct
            
        except Exception as e:
            logger.error(f"Error calculando niveles dinámicos: {e}")
            return self.stop_loss_pct, self.take_profit_pct
    
    def run_optimized_backtest(self):
        """Ejecuta el backtest optimizado"""
        try:
            logger.info("Iniciando backtest optimizado para ROI 15% mensual")
            
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
            
            # Calcular indicadores optimizados
            btc_data = self.calculate_optimized_indicators(btc_data)
            eth_data = self.calculate_optimized_indicators(eth_data)
            
            # Inicializar portfolio optimizado
            portfolio = OptimizedPortfolio(self.initial_capital)
            results = []
            
            logger.info(f"Procesando {len(btc_data)} periodos de datos")
            
            for i in range(len(btc_data)):
                if i >= len(eth_data):
                    break
                    
                current_time = btc_data.iloc[i]['timestamp']
                
                # Procesar BTC
                btc_price = btc_data.iloc[i]['close']
                btc_volatility = btc_data.iloc[i]['volatility']
                btc_atr = btc_data.iloc[i]['atr']
                btc_signal, btc_confidence, btc_quality = self.generate_optimized_signal(btc_data, i)
                
                # Procesar ETH
                eth_price = eth_data.iloc[i]['close']
                eth_volatility = eth_data.iloc[i]['volatility']
                eth_atr = eth_data.iloc[i]['atr']
                eth_signal, eth_confidence, eth_quality = self.generate_optimized_signal(eth_data, i)
                
                # Gestión de riesgo optimizada
                self.manage_optimized_risk(portfolio, btc_price, eth_price)
                
                # Evaluar operaciones para BTC
                if (btc_signal != 0.0 and btc_confidence != 0.0 and btc_quality != 0.0):
                    position_size = self.calculate_dynamic_position_size(
                        btc_signal, btc_confidence, btc_quality, portfolio.cash, btc_volatility
                    )
                    
                    if btc_signal > 0 and position_size > 15 and not portfolio.has_position('BTCUSDT'):
                        stop_loss_pct, take_profit_pct = self.calculate_dynamic_levels(
                            btc_price, btc_volatility, btc_atr, btc_signal
                        )
                        
                        fees = self.execute_optimized_trade(portfolio, 'BTCUSDT', btc_price, position_size, 'buy', stop_loss_pct, take_profit_pct)
                        self.last_trade_bar = i
                        logger.info(f"BTC LONG @ ${btc_price:.2f} - Size: ${position_size:.2f} - SL: {stop_loss_pct*100:.1f}% - TP: {take_profit_pct*100:.1f}% - Q: {btc_quality:.2f}")
                
                # Evaluar operaciones para ETH
                if (eth_signal != 0.0 and eth_confidence != 0.0 and eth_quality != 0.0):
                    position_size = self.calculate_dynamic_position_size(
                        eth_signal, eth_confidence, eth_quality, portfolio.cash, eth_volatility
                    )
                    
                    if eth_signal > 0 and position_size > 15 and not portfolio.has_position('ETHUSDT'):
                        stop_loss_pct, take_profit_pct = self.calculate_dynamic_levels(
                            eth_price, eth_volatility, eth_atr, eth_signal
                        )
                        
                        fees = self.execute_optimized_trade(portfolio, 'ETHUSDT', eth_price, position_size, 'buy', stop_loss_pct, take_profit_pct)
                        self.last_trade_bar = i
                        logger.info(f"ETH LONG @ ${eth_price:.2f} - Size: ${position_size:.2f} - SL: {stop_loss_pct*100:.1f}% - TP: {take_profit_pct*100:.1f}% - Q: {eth_quality:.2f}")
                
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
                if i % 50 == 0:
                    win_rate = self.winning_trades / max(self.total_trades, 1) if self.total_trades > 0 else 0
                    logger.info(f"Periodo {i}/{len(btc_data)} - Valor: ${portfolio_summary['total_value']:.2f} - Operaciones: {self.total_trades} - Win Rate: {win_rate*100:.1f}%")
            
            # Crear DataFrame de resultados
            results_df = pd.DataFrame(results)
            
            if not results_df.empty:
                # Guardar resultados
                results_df.to_csv('optimized_simple_roi_results.csv', index=False)
                
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
                logger.info("RESUMEN FINAL - SISTEMA OPTIMIZADO SIMPLE ROI")
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
                    if win_rate < 0.6:
                        logger.info("ANALISIS: Win rate bajo - necesita mejores filtros de entrada")
                    if profit_factor < 1.5:
                        logger.info("ANALISIS: Profit factor bajo - ajustar ratio riesgo/beneficio")
                    if self.total_trades < 5:
                        logger.info("ANALISIS: Pocas operaciones - reducir filtros")
                    elif self.total_trades > 50:
                        logger.info("ANALISIS: Demasiadas operaciones - aumentar filtros")
                
                return results_df
            else:
                logger.error("No se generaron resultados")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error en backtest optimizado: {e}")
            return pd.DataFrame()
    
    def execute_optimized_trade(self, portfolio, symbol, price, position_size, action, stop_loss_pct, take_profit_pct):
        """Ejecuta una operación optimizada"""
        try:
            if action == 'buy' and position_size > 0:
                quantity = position_size / price
                fees = position_size * self.fee_rate
                
                stop_loss_price = price * (1 - stop_loss_pct)
                take_profit_price = price * (1 + take_profit_pct)
                
                portfolio.open_position(symbol, price, quantity, stop_loss_price, take_profit_price)
                self.total_trades += 1
                self.total_fees_paid += fees
                return fees
            return 0.0
        except Exception as e:
            logger.error(f"Error ejecutando trade optimizado: {e}")
            return 0.0
    
    def manage_optimized_risk(self, portfolio, btc_price, eth_price):
        """Gestiona el riesgo de forma optimizada"""
        try:
            # Gestionar BTC
            if portfolio.has_position('BTCUSDT'):
                position = portfolio.positions['BTCUSDT']
                entry_price = position['entry_price']
                current_pnl_pct = (btc_price - entry_price) / entry_price
                
                if btc_price <= position['stop_loss_price']:
                    portfolio.close_position('BTCUSDT', btc_price)
                    self.losing_trades += 1
                    self.current_consecutive_losses += 1
                    self.max_consecutive_losses = max(self.max_consecutive_losses, self.current_consecutive_losses)
                    logger.info(f"BTC Stop Loss @ ${btc_price:.2f} - Loss: {current_pnl_pct*100:.2f}%")
                
                elif btc_price >= position['take_profit_price']:
                    portfolio.close_position('BTCUSDT', btc_price)
                    self.winning_trades += 1
                    self.current_consecutive_losses = 0
                    logger.info(f"BTC Take Profit @ ${btc_price:.2f} - Profit: {current_pnl_pct*100:.2f}%")
            
            # Gestionar ETH
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
                        
        except Exception as e:
            logger.error(f"Error en gestión de riesgo optimizada: {e}")

class OptimizedPortfolio:
    def __init__(self, initial_capital):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        
    def has_position(self, symbol):
        return symbol in self.positions
    
    def open_position(self, symbol, price, quantity, stop_loss_price, take_profit_price):
        cost = price * quantity
        if cost <= self.cash:
            self.cash -= cost
            self.positions[symbol] = {
                'quantity': quantity,
                'entry_price': price,
                'stop_loss_price': stop_loss_price,
                'take_profit_price': take_profit_price
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
    logger.info("Iniciando Sistema Optimizado Simple ROI 15%")
    
    system = OptimizedSimpleROISystem(initial_capital=500)
    results = system.run_optimized_backtest()
    
    if not results.empty:
        print(f"\nSistema optimizado simple completado!")
        print(f"Resultados guardados en: optimized_simple_roi_results.csv")
        print(f"Log guardado en: optimized_simple_roi_system.log")
    else:
        print("Error en el sistema optimizado simple")

if __name__ == "__main__":
    main()