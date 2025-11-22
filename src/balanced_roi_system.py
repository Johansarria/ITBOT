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
        logging.FileHandler('balanced_roi_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BalancedROISystem:
    def __init__(self, initial_capital=500):
        self.initial_capital = initial_capital
        self.total_trades = 0
        self.total_fees_paid = 0.0
        self.fee_rate = 0.001  # 0.1% por operación
        
        # Umbrales equilibrados para generar operaciones
        self.signal_threshold = 0.25  # Reducido para más operaciones
        self.confidence_threshold = 0.35  # Reducido para más operaciones
        self.quality_threshold = 0.3  # Reducido para más operaciones
        
        # Gestión de riesgo equilibrada
        self.max_position_size = 0.3  # 30% del capital por posición
        self.base_stop_loss = 0.03  # 3% stop-loss base
        self.base_take_profit = 0.06  # 6% take-profit base (1:2 ratio)
        
        # Métricas de rendimiento
        self.winning_trades = 0
        self.losing_trades = 0
        self.max_consecutive_losses = 0
        self.current_consecutive_losses = 0
        
    def calculate_indicators(self, df, symbol):
        """Calcula indicadores técnicos equilibrados"""
        try:
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
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
            
            # Momentum
            df['momentum'] = df['close'] / df['close'].shift(10) - 1
            
            # Volatilidad
            df['volatility'] = df['close'].rolling(window=20).std() / df['close'].rolling(window=20).mean()
            
            # ATR para stop-loss dinámico
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['atr'] = true_range.rolling(window=14).mean()
            
            # Volumen
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
            # Tendencia
            df['ema_20'] = df['close'].ewm(span=20).mean()
            df['ema_50'] = df['close'].ewm(span=50).mean()
            df['trend'] = np.where(df['ema_20'] > df['ema_50'], 1, -1)
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculando indicadores para {symbol}: {e}")
            return df
    
    def generate_signal(self, df, i, symbol):
        """Genera señales equilibradas"""
        try:
            if i < 50:  # Necesitamos datos suficientes
                return 0.0, 0.0, 0.0
            
            current = df.iloc[i]
            prev = df.iloc[i-1]
            
            signals = []
            confidences = []
            
            # Señal RSI (más permisiva)
            rsi = current['rsi']
            if rsi < 35:  # Sobreventa
                signals.append(0.6)
                confidences.append(0.7)
            elif rsi > 65:  # Sobrecompra
                signals.append(-0.6)
                confidences.append(0.7)
            elif 45 < rsi < 55:  # Zona neutral
                signals.append(0.2)
                confidences.append(0.4)
            
            # Señal MACD
            if (current['macd'] > current['macd_signal'] and 
                prev['macd'] <= prev['macd_signal']):
                signals.append(0.5)
                confidences.append(0.6)
            elif (current['macd'] < current['macd_signal'] and 
                  prev['macd'] >= prev['macd_signal']):
                signals.append(-0.5)
                confidences.append(0.6)
            
            # Señal Bollinger Bands
            bb_pos = current['bb_position']
            if bb_pos < 0.2:  # Cerca del límite inferior
                signals.append(0.4)
                confidences.append(0.5)
            elif bb_pos > 0.8:  # Cerca del límite superior
                signals.append(-0.4)
                confidences.append(0.5)
            
            # Señal de momentum
            momentum = current['momentum']
            if momentum > 0.02:  # Momentum positivo
                signals.append(0.3)
                confidences.append(0.4)
            elif momentum < -0.02:  # Momentum negativo
                signals.append(-0.3)
                confidences.append(0.4)
            
            # Señal de volumen
            if current['volume_ratio'] > 1.3:  # Volumen alto
                signals.append(0.2)
                confidences.append(0.3)
            
            # Confirmación de tendencia
            trend_signal = current['trend'] * 0.1
            
            # Combinar señales
            if signals:
                final_signal = np.mean(signals) + trend_signal
                final_confidence = np.mean(confidences)
                
                # Ajustar por volatilidad
                volatility = current['volatility']
                if volatility > 0.05:
                    final_confidence *= 0.8  # Reducir confianza en alta volatilidad
                elif volatility < 0.02:
                    final_confidence *= 1.1  # Aumentar confianza en baja volatilidad
                
                # Calcular calidad
                signal_consistency = 1 - np.std(signals) if len(signals) > 1 else 0.5
                quality_score = final_confidence * signal_consistency * (len(signals) / 5)
                
                return final_signal, final_confidence, quality_score
            
            return 0.0, 0.0, 0.0
            
        except Exception as e:
            logger.error(f"Error generando señal para {symbol}: {e}")
            return 0.0, 0.0, 0.0
    
    def calculate_position_size(self, signal, confidence, quality_score, current_capital):
        """Calcula tamaño de posición equilibrado"""
        try:
            # Tamaño base
            base_size = 0.15  # 15% del capital
            
            # Ajustar por confianza
            confidence_multiplier = min(confidence / 0.4, 1.5)
            
            # Ajustar por calidad
            quality_multiplier = min(quality_score / 0.3, 1.3)
            
            # Ajustar por fuerza de señal
            signal_multiplier = min(abs(signal) / 0.3, 1.2)
            
            # Ajustar por racha de pérdidas
            loss_multiplier = 1.0
            if self.current_consecutive_losses > 2:
                loss_multiplier = 0.7  # Reducir después de pérdidas
            elif self.current_consecutive_losses == 0:
                loss_multiplier = 1.1  # Aumentar después de ganar
            
            # Calcular tamaño final
            position_fraction = (base_size * confidence_multiplier * quality_multiplier * 
                               signal_multiplier * loss_multiplier)
            
            # Limitar al máximo
            position_fraction = min(position_fraction, self.max_position_size)
            
            # Calcular valor en USD
            position_value = current_capital * position_fraction
            
            return max(position_value, 15)  # Mínimo $15
            
        except Exception as e:
            logger.error(f"Error calculando tamaño de posición: {e}")
            return 0.0
    
    def calculate_dynamic_levels(self, price, volatility, atr):
        """Calcula stop-loss y take-profit dinámicos"""
        try:
            # Stop-loss dinámico
            volatility_stop = volatility * 1.5 if volatility > 0.02 else self.base_stop_loss
            atr_stop = (atr / price) * 2 if atr > 0 else self.base_stop_loss
            
            stop_loss_pct = max(self.base_stop_loss, min(volatility_stop, atr_stop, 0.06))
            
            # Take-profit (ratio 1:2)
            take_profit_pct = stop_loss_pct * 2
            
            return stop_loss_pct, take_profit_pct
            
        except Exception as e:
            logger.error(f"Error calculando niveles dinámicos: {e}")
            return self.base_stop_loss, self.base_take_profit
    
    def run_balanced_backtest(self):
        """Ejecuta el backtest equilibrado"""
        try:
            logger.info("Iniciando backtest equilibrado para ROI 15% mensual")
            
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
            
            # Calcular indicadores
            btc_data = self.calculate_indicators(btc_data, 'BTCUSDT')
            eth_data = self.calculate_indicators(eth_data, 'ETHUSDT')
            
            # Alinear datos
            merged_data = pd.merge(btc_data, eth_data, on='timestamp', suffixes=('_btc', '_eth'))
            
            # Inicializar portfolio
            portfolio = BalancedPortfolio(self.initial_capital)
            results = []
            
            logger.info(f"Procesando {len(merged_data)} periodos de datos")
            
            for i in range(len(merged_data)):
                current_time = merged_data.iloc[i]['timestamp']
                
                # Procesar BTC
                btc_price = merged_data.iloc[i]['close_btc']
                btc_volatility = merged_data.iloc[i]['volatility_btc']
                btc_atr = merged_data.iloc[i]['atr_btc']
                btc_signal, btc_confidence, btc_quality = self.generate_signal(btc_data, i, 'BTCUSDT')
                
                # Procesar ETH
                eth_price = merged_data.iloc[i]['close_eth']
                eth_volatility = merged_data.iloc[i]['volatility_eth']
                eth_atr = merged_data.iloc[i]['atr_eth']
                eth_signal, eth_confidence, eth_quality = self.generate_signal(eth_data, i, 'ETHUSDT')
                
                # Gestión de riesgo
                self.manage_risk(portfolio, btc_price, eth_price)
                
                # Evaluar operaciones para BTC
                if (abs(btc_signal) > self.signal_threshold and 
                    btc_confidence > self.confidence_threshold and 
                    btc_quality > self.quality_threshold):
                    
                    position_size = self.calculate_position_size(
                        btc_signal, btc_confidence, btc_quality, portfolio.cash
                    )
                    
                    if btc_signal > 0 and position_size > 10 and not portfolio.has_position('BTCUSDT'):
                        stop_loss_pct, take_profit_pct = self.calculate_dynamic_levels(
                            btc_price, btc_volatility, btc_atr
                        )
                        
                        fees = self.execute_trade(portfolio, 'BTCUSDT', btc_price, position_size, 'buy', stop_loss_pct, take_profit_pct)
                        logger.info(f"BTC LONG @ ${btc_price:.2f} - Size: ${position_size:.2f} - SL: {stop_loss_pct*100:.1f}% - TP: {take_profit_pct*100:.1f}%")
                
                # Evaluar operaciones para ETH
                if (abs(eth_signal) > self.signal_threshold and 
                    eth_confidence > self.confidence_threshold and 
                    eth_quality > self.quality_threshold):
                    
                    position_size = self.calculate_position_size(
                        eth_signal, eth_confidence, eth_quality, portfolio.cash
                    )
                    
                    if eth_signal > 0 and position_size > 10 and not portfolio.has_position('ETHUSDT'):
                        stop_loss_pct, take_profit_pct = self.calculate_dynamic_levels(
                            eth_price, eth_volatility, eth_atr
                        )
                        
                        fees = self.execute_trade(portfolio, 'ETHUSDT', eth_price, position_size, 'buy', stop_loss_pct, take_profit_pct)
                        logger.info(f"ETH LONG @ ${eth_price:.2f} - Size: ${position_size:.2f} - SL: {stop_loss_pct*100:.1f}% - TP: {take_profit_pct*100:.1f}%")
                
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
                    logger.info(f"Periodo {i}/{len(merged_data)} - Valor: ${portfolio_summary['total_value']:.2f} - Operaciones: {self.total_trades}")
            
            # Crear DataFrame de resultados
            results_df = pd.DataFrame(results)
            
            if not results_df.empty:
                # Guardar resultados
                results_df.to_csv('balanced_roi_results.csv', index=False)
                
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
                
                logger.info("=" * 70)
                logger.info("RESUMEN FINAL - SISTEMA EQUILIBRADO ROI")
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
                logger.info(f"Max perdidas consecutivas: {self.max_consecutive_losses}")
                
                # Verificar objetivo
                target_roi = 0.15  # 15% mensual
                if monthly_roi >= target_roi:
                    logger.info(f"OBJETIVO ALCANZADO! ROI mensual: {monthly_roi*100:.2f}% >= {target_roi*100:.0f}%")
                else:
                    gap = target_roi - monthly_roi
                    logger.info(f"Objetivo no alcanzado. Gap: {gap*100:.2f}% para llegar al {target_roi*100:.0f}%")
                
                return results_df
            else:
                logger.error("No se generaron resultados")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error en backtest equilibrado: {e}")
            return pd.DataFrame()
    
    def execute_trade(self, portfolio, symbol, price, position_size, action, stop_loss_pct, take_profit_pct):
        """Ejecuta una operación"""
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
            logger.error(f"Error ejecutando trade: {e}")
            return 0.0
    
    def manage_risk(self, portfolio, btc_price, eth_price):
        """Gestiona el riesgo"""
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
            logger.error(f"Error en gestión de riesgo: {e}")

class BalancedPortfolio:
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
    logger.info("Iniciando Sistema Equilibrado ROI 15%")
    
    system = BalancedROISystem(initial_capital=500)
    results = system.run_balanced_backtest()
    
    if not results.empty:
        print(f"\nSistema equilibrado completado!")
        print(f"Resultados guardados en: balanced_roi_results.csv")
        print(f"Log guardado en: balanced_roi_system.log")
    else:
        print("Error en el sistema equilibrado")

if __name__ == "__main__":
    main()