import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('optimized_roi_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OptimizedROISystem:
    def __init__(self, initial_capital=500):
        self.initial_capital = initial_capital
        self.total_trades = 0
        self.total_fees_paid = 0.0
        self.fee_rate = 0.001  # 0.1% por operación
        
        # Umbrales optimizados para generar más operaciones
        self.signal_threshold = 0.3  # Reducido de 0.7
        self.confidence_threshold = 0.4  # Reducido de 0.8
        self.quality_threshold = 0.25  # Reducido de 0.6
        
        # Parámetros de riesgo
        self.max_position_size = 0.4  # 40% del capital por posición
        self.stop_loss_pct = 0.03  # 3% stop loss
        self.take_profit_pct = 0.06  # 6% take profit
        
    def calculate_technical_indicators(self, df, symbol):
        """Calcula indicadores técnicos optimizados"""
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
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            
            # Momentum
            df['momentum'] = df['close'] / df['close'].shift(10) - 1
            
            # Volatilidad
            df['volatility'] = df['close'].rolling(window=20).std() / df['close'].rolling(window=20).mean()
            
            # Volume Profile (simplificado)
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculando indicadores para {symbol}: {e}")
            return df
    
    def generate_optimized_signal(self, df, i, symbol):
        """Genera señales optimizadas con umbrales más bajos"""
        try:
            if i < 30:  # Necesitamos suficientes datos
                return 0.0, 0.0, 0.0
            
            current = df.iloc[i]
            
            # Señales RSI (más agresivas)
            rsi_signal = 0.0
            if current['rsi'] < 35:  # Sobreventa (era 30)
                rsi_signal = 0.6
            elif current['rsi'] > 65:  # Sobrecompra (era 70)
                rsi_signal = -0.6
            elif 40 < current['rsi'] < 60:  # Zona neutral favorable
                rsi_signal = 0.2
            
            # Señales MACD (más sensibles)
            macd_signal = 0.0
            if current['macd'] > current['macd_signal'] and current['macd_histogram'] > 0:
                macd_signal = 0.5
            elif current['macd'] < current['macd_signal'] and current['macd_histogram'] < 0:
                macd_signal = -0.5
            
            # Señales Bollinger Bands
            bb_signal = 0.0
            if current['bb_position'] < 0.2:  # Cerca del límite inferior
                bb_signal = 0.4
            elif current['bb_position'] > 0.8:  # Cerca del límite superior
                bb_signal = -0.4
            
            # Señal de momentum
            momentum_signal = 0.0
            if current['momentum'] > 0.02:  # Momentum positivo
                momentum_signal = 0.3
            elif current['momentum'] < -0.02:  # Momentum negativo
                momentum_signal = -0.3
            
            # Señal de volumen
            volume_signal = 0.0
            if current['volume_ratio'] > 1.5:  # Alto volumen
                volume_signal = 0.2
            elif current['volume_ratio'] < 0.5:  # Bajo volumen
                volume_signal = -0.1
            
            # Combinar señales con pesos optimizados
            signal = (rsi_signal * 0.3 + 
                     macd_signal * 0.25 + 
                     bb_signal * 0.2 + 
                     momentum_signal * 0.15 + 
                     volume_signal * 0.1)
            
            # Calcular confianza basada en convergencia de indicadores
            signals = [rsi_signal, macd_signal, bb_signal, momentum_signal]
            non_zero_signals = [s for s in signals if abs(s) > 0.1]
            
            if len(non_zero_signals) >= 2:
                # Verificar si las señales van en la misma dirección
                positive_signals = sum(1 for s in non_zero_signals if s > 0)
                negative_signals = sum(1 for s in non_zero_signals if s < 0)
                
                if positive_signals >= 2 and negative_signals == 0:
                    confidence = 0.6 + (positive_signals - 2) * 0.1
                elif negative_signals >= 2 and positive_signals == 0:
                    confidence = 0.6 + (negative_signals - 2) * 0.1
                else:
                    confidence = 0.3  # Señales mixtas
            else:
                confidence = 0.2
            
            # Ajustar por volatilidad
            if current['volatility'] > 0.05:  # Alta volatilidad
                confidence *= 0.8
                signal *= 1.2  # Amplificar señal en alta volatilidad
            
            # Calcular score de calidad
            quality_factors = []
            
            # Factor 1: Convergencia de indicadores
            if len(non_zero_signals) >= 3:
                quality_factors.append(0.4)
            elif len(non_zero_signals) >= 2:
                quality_factors.append(0.3)
            else:
                quality_factors.append(0.1)
            
            # Factor 2: Fuerza de la señal
            if abs(signal) > 0.4:
                quality_factors.append(0.3)
            elif abs(signal) > 0.2:
                quality_factors.append(0.2)
            else:
                quality_factors.append(0.1)
            
            # Factor 3: Volumen
            if current['volume_ratio'] > 1.2:
                quality_factors.append(0.2)
            else:
                quality_factors.append(0.1)
            
            # Factor 4: Condición de mercado
            if 0.3 < current['bb_position'] < 0.7:  # Mercado estable
                quality_factors.append(0.1)
            else:
                quality_factors.append(0.05)
            
            quality_score = sum(quality_factors)
            
            return signal, confidence, quality_score
            
        except Exception as e:
            logger.error(f"Error generando señal para {symbol}: {e}")
            return 0.0, 0.0, 0.0
    
    def calculate_position_size(self, signal, confidence, quality_score, current_capital):
        """Calcula el tamaño de posición basado en señal y riesgo"""
        try:
            # Tamaño base
            base_size = 0.2  # 20% del capital
            
            # Ajustar por confianza
            confidence_multiplier = min(confidence / 0.5, 1.5)
            
            # Ajustar por calidad
            quality_multiplier = min(quality_score / 0.3, 1.3)
            
            # Ajustar por fuerza de señal
            signal_multiplier = min(abs(signal) / 0.4, 1.2)
            
            # Calcular tamaño final
            position_size = base_size * confidence_multiplier * quality_multiplier * signal_multiplier
            
            # Limitar al máximo permitido
            position_size = min(position_size, self.max_position_size)
            
            # Calcular cantidad en USD
            position_value = current_capital * position_size
            
            return position_value
            
        except Exception as e:
            logger.error(f"Error calculando tamaño de posición: {e}")
            return 0.0
    
    def run_backtest(self):
        """Ejecuta el backtest optimizado"""
        try:
            logger.info("Iniciando backtest optimizado para ROI 15% mensual")
            
            # Importar y usar el fetcher de datos
            from robust_data_fetcher import RobustDataFetcher
            
            # Crear fetcher
            fetcher = RobustDataFetcher()
            
            # Obtener datos históricos
            logger.info("Obteniendo datos históricos...")
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
            
            # Calcular indicadores
            btc_data = self.calculate_technical_indicators(btc_data, 'BTCUSDT')
            eth_data = self.calculate_technical_indicators(eth_data, 'ETHUSDT')
            
            # Alinear datos por timestamp
            merged_data = pd.merge(btc_data, eth_data, on='timestamp', suffixes=('_btc', '_eth'))
            
            # Inicializar portfolio
            portfolio = SimplePortfolio(self.initial_capital)
            results = []
            
            logger.info(f"Procesando {len(merged_data)} periodos de datos")
            
            for i in range(len(merged_data)):
                current_time = merged_data.iloc[i]['timestamp']
                
                # Procesar BTC
                btc_price = merged_data.iloc[i]['close_btc']
                btc_signal, btc_confidence, btc_quality = self.generate_optimized_signal(
                    btc_data, i, 'BTCUSDT'
                )
                
                # Procesar ETH
                eth_price = merged_data.iloc[i]['close_eth']
                eth_signal, eth_confidence, eth_quality = self.generate_optimized_signal(
                    eth_data, i, 'ETHUSDT'
                )
                
                # Evaluar operaciones para BTC
                if (abs(btc_signal) > self.signal_threshold and 
                    btc_confidence > self.confidence_threshold and 
                    btc_quality > self.quality_threshold):
                    
                    position_size = self.calculate_position_size(
                        btc_signal, btc_confidence, btc_quality, portfolio.cash
                    )
                    
                    if btc_signal > 0 and position_size > 10:  # Compra
                        fees = self.execute_trade(portfolio, 'BTCUSDT', btc_price, position_size, 'buy')
                        logger.info(f"BTC LONG @ ${btc_price:.2f} - Size: ${position_size:.2f} - Fee: ${fees:.2f}")
                    elif btc_signal < 0 and portfolio.positions.get('BTCUSDT', {}).get('size', 0) > 0:  # Venta
                        fees = self.execute_trade(portfolio, 'BTCUSDT', btc_price, 0, 'sell')
                        logger.info(f"BTC SHORT @ ${btc_price:.2f} - Fee: ${fees:.2f}")
                
                # Evaluar operaciones para ETH
                if (abs(eth_signal) > self.signal_threshold and 
                    eth_confidence > self.confidence_threshold and 
                    eth_quality > self.quality_threshold):
                    
                    position_size = self.calculate_position_size(
                        eth_signal, eth_confidence, eth_quality, portfolio.cash
                    )
                    
                    if eth_signal > 0 and position_size > 10:  # Compra
                        fees = self.execute_trade(portfolio, 'ETHUSDT', eth_price, position_size, 'buy')
                        logger.info(f"ETH LONG @ ${eth_price:.2f} - Size: ${position_size:.2f} - Fee: ${fees:.2f}")
                    elif eth_signal < 0 and portfolio.positions.get('ETHUSDT', {}).get('size', 0) > 0:  # Venta
                        fees = self.execute_trade(portfolio, 'ETHUSDT', eth_price, 0, 'sell')
                        logger.info(f"ETH SHORT @ ${eth_price:.2f} - Fee: ${fees:.2f}")
                
                # Gestión de riesgo - Stop Loss y Take Profit
                self.manage_risk(portfolio, btc_price, eth_price)
                
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
                results_df.to_csv('optimized_roi_results.csv', index=False)
                
                # Calcular métricas finales
                final_summary = portfolio.get_portfolio_summary()
                net_pnl = final_summary['total_pnl'] - self.total_fees_paid
                net_return = net_pnl / self.initial_capital
                
                # Calcular ROI mensual
                duration_days = (results_df['timestamp'].max() - results_df['timestamp'].min()).days
                duration_months = duration_days / 30.44
                monthly_roi = (((final_summary['total_value'] - self.total_fees_paid) / self.initial_capital) ** (1/duration_months) - 1) if duration_months > 0 else 0
                
                # Calcular win rate
                if self.total_trades > 0:
                    profitable_periods = len(results_df[results_df['total_pnl'] > results_df['total_pnl'].shift(1)])
                    win_rate = profitable_periods / len(results_df) if len(results_df) > 0 else 0
                else:
                    win_rate = 0
                
                logger.info("=" * 70)
                logger.info("RESUMEN FINAL - SISTEMA OPTIMIZADO ROI")
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
                
                return results_df
            else:
                logger.error("No se generaron resultados")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error en backtest: {e}")
            return pd.DataFrame()
    
    def execute_trade(self, portfolio, symbol, price, position_size, action):
        """Ejecuta una operación y calcula fees"""
        try:
            if action == 'buy' and position_size > 0:
                quantity = position_size / price
                fees = position_size * self.fee_rate
                portfolio.open_position(symbol, price, quantity)
                self.total_trades += 1
                self.total_fees_paid += fees
                return fees
            elif action == 'sell':
                fees = portfolio.positions.get(symbol, {}).get('size', 0) * price * self.fee_rate
                portfolio.close_position(symbol, price)
                self.total_trades += 1
                self.total_fees_paid += fees
                return fees
            return 0.0
        except Exception as e:
            logger.error(f"Error ejecutando trade: {e}")
            return 0.0
    
    def manage_risk(self, portfolio, btc_price, eth_price):
        """Gestiona el riesgo con stop-loss y take-profit"""
        try:
            # Gestionar BTC
            if 'BTCUSDT' in portfolio.positions:
                position = portfolio.positions['BTCUSDT']
                entry_price = position['entry_price']
                current_pnl_pct = (btc_price - entry_price) / entry_price
                
                if current_pnl_pct <= -self.stop_loss_pct:  # Stop Loss
                    fees = self.execute_trade(portfolio, 'BTCUSDT', btc_price, 0, 'sell')
                    logger.info(f"BTC Stop Loss @ ${btc_price:.2f} - Loss: {current_pnl_pct*100:.2f}%")
                elif current_pnl_pct >= self.take_profit_pct:  # Take Profit
                    fees = self.execute_trade(portfolio, 'BTCUSDT', btc_price, 0, 'sell')
                    logger.info(f"BTC Take Profit @ ${btc_price:.2f} - Profit: {current_pnl_pct*100:.2f}%")
            
            # Gestionar ETH
            if 'ETHUSDT' in portfolio.positions:
                position = portfolio.positions['ETHUSDT']
                entry_price = position['entry_price']
                current_pnl_pct = (eth_price - entry_price) / entry_price
                
                if current_pnl_pct <= -self.stop_loss_pct:  # Stop Loss
                    fees = self.execute_trade(portfolio, 'ETHUSDT', eth_price, 0, 'sell')
                    logger.info(f"ETH Stop Loss @ ${eth_price:.2f} - Loss: {current_pnl_pct*100:.2f}%")
                elif current_pnl_pct >= self.take_profit_pct:  # Take Profit
                    fees = self.execute_trade(portfolio, 'ETHUSDT', eth_price, 0, 'sell')
                    logger.info(f"ETH Take Profit @ ${eth_price:.2f} - Profit: {current_pnl_pct*100:.2f}%")
                    
        except Exception as e:
            logger.error(f"Error en gestión de riesgo: {e}")

class SimplePortfolio:
    def __init__(self, initial_capital):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        self.max_value = initial_capital
        
    def open_position(self, symbol, price, quantity):
        """Abre una posición"""
        cost = price * quantity
        if cost <= self.cash:
            self.cash -= cost
            self.positions[symbol] = {
                'quantity': quantity,
                'entry_price': price,
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
        
        # Agregar valor de posiciones abiertas (estimado)
        for symbol, position in self.positions.items():
            # Usar precio de entrada como estimación
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
    logger.info("Iniciando Sistema Optimizado ROI 15%")
    
    system = OptimizedROISystem(initial_capital=500)
    results = system.run_backtest()
    
    if not results.empty:
        print(f"\nSistema optimizado completado!")
        print(f"Resultados guardados en: optimized_roi_results.csv")
        print(f"Log guardado en: optimized_roi_system.log")
    else:
        print("Error en el sistema optimizado")

if __name__ == "__main__":
    main()