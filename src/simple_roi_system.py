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
        logging.FileHandler('simple_roi_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SimpleROISystem:
    def __init__(self, initial_capital=500):
        self.initial_capital = initial_capital
        self.total_trades = 0
        self.total_fees_paid = 0.0
        self.fee_rate = 0.001  # 0.1% por operación
        
        # Umbrales muy bajos para asegurar operaciones
        self.signal_threshold = 0.1  # Muy bajo
        self.confidence_threshold = 0.2  # Muy bajo
        self.quality_threshold = 0.1  # Muy bajo
        
        # Gestión de riesgo simple
        self.position_size_pct = 0.2  # 20% del capital por posición
        self.stop_loss_pct = 0.04  # 4% stop-loss
        self.take_profit_pct = 0.08  # 8% take-profit (1:2 ratio)
        
        # Métricas de rendimiento
        self.winning_trades = 0
        self.losing_trades = 0
        self.max_consecutive_losses = 0
        self.current_consecutive_losses = 0
        
    def calculate_simple_indicators(self, df):
        """Calcula indicadores técnicos simples"""
        try:
            # RSI simple
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 0.0001)  # Evitar división por cero
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD simple
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            df['macd'] = exp1 - exp2
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            
            # Medias móviles
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            
            # Momentum simple
            df['momentum'] = df['close'] / df['close'].shift(5) - 1
            
            # Volatilidad simple
            df['volatility'] = df['close'].rolling(window=10).std() / df['close'].rolling(window=10).mean()
            
            # Rellenar valores NaN con 0
            df = df.fillna(0)
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculando indicadores: {e}")
            return df
    
    def generate_simple_signal(self, df, i):
        """Genera señales simples y directas"""
        try:
            if i < 50:  # Necesitamos datos suficientes
                return 0.5, 0.5, 0.5  # Valores por defecto para generar operaciones
            
            current = df.iloc[i]
            prev = df.iloc[i-1]
            
            signal = 0.0
            confidence = 0.0
            quality = 0.0
            
            # Señal RSI simple
            rsi = current['rsi']
            if rsi < 40:  # Sobreventa
                signal += 0.3
                confidence += 0.3
            elif rsi > 60:  # Sobrecompra
                signal -= 0.3
                confidence += 0.3
            else:  # Zona neutral
                signal += 0.1
                confidence += 0.2
            
            # Señal MACD simple
            if current['macd'] > current['macd_signal']:
                signal += 0.2
                confidence += 0.2
            else:
                signal -= 0.1
                confidence += 0.1
            
            # Señal de medias móviles
            if current['close'] > current['sma_20']:
                signal += 0.2
                confidence += 0.2
            if current['sma_20'] > current['sma_50']:
                signal += 0.1
                confidence += 0.1
            
            # Señal de momentum
            momentum = current['momentum']
            if momentum > 0.01:  # Momentum positivo
                signal += 0.2
                confidence += 0.2
            elif momentum < -0.01:  # Momentum negativo
                signal -= 0.2
                confidence += 0.2
            
            # Asegurar que siempre hay alguna señal
            if abs(signal) < 0.1:
                signal = 0.2  # Señal mínima positiva
            
            if confidence < 0.2:
                confidence = 0.3  # Confianza mínima
            
            # Calcular calidad simple
            quality = min(confidence * 0.8, 0.8)
            
            # Asegurar valores mínimos para generar operaciones
            signal = max(abs(signal), 0.15) * (1 if signal >= 0 else -1)
            confidence = max(confidence, 0.25)
            quality = max(quality, 0.15)
            
            return signal, confidence, quality
            
        except Exception as e:
            logger.error(f"Error generando señal: {e}")
            return 0.3, 0.3, 0.3  # Valores por defecto
    
    def run_simple_backtest(self):
        """Ejecuta el backtest simple"""
        try:
            logger.info("Iniciando backtest simple para ROI 15% mensual")
            
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
            
            # Calcular indicadores simples
            btc_data = self.calculate_simple_indicators(btc_data)
            eth_data = self.calculate_simple_indicators(eth_data)
            
            # Inicializar portfolio simple
            portfolio = SimplePortfolio(self.initial_capital)
            results = []
            
            logger.info(f"Procesando {len(btc_data)} periodos de datos")
            
            # Alternar entre BTC y ETH para diversificar
            use_btc = True
            
            for i in range(len(btc_data)):
                if i >= len(eth_data):
                    break
                    
                current_time = btc_data.iloc[i]['timestamp']
                
                # Alternar entre BTC y ETH
                if use_btc:
                    price = btc_data.iloc[i]['close']
                    signal, confidence, quality = self.generate_simple_signal(btc_data, i)
                    symbol = 'BTCUSDT'
                else:
                    price = eth_data.iloc[i]['close']
                    signal, confidence, quality = self.generate_simple_signal(eth_data, i)
                    symbol = 'ETHUSDT'
                
                # Gestión de riesgo simple
                self.manage_simple_risk(portfolio, price, symbol)
                
                # Evaluar operaciones
                if (abs(signal) > self.signal_threshold and 
                    confidence > self.confidence_threshold and 
                    quality > self.quality_threshold):
                    
                    position_size = portfolio.cash * self.position_size_pct
                    
                    if signal > 0 and position_size > 10 and not portfolio.has_position(symbol):
                        fees = self.execute_simple_trade(portfolio, symbol, price, position_size, 'buy')
                        logger.info(f"{symbol} LONG @ ${price:.2f} - Size: ${position_size:.2f} - Signal: {signal:.2f} - Confidence: {confidence:.2f}")
                
                # Guardar estado
                portfolio_summary = portfolio.get_portfolio_summary()
                results.append({
                    'timestamp': current_time,
                    'symbol': symbol,
                    'price': price,
                    'signal': signal,
                    'confidence': confidence,
                    'quality': quality,
                    'portfolio_value': portfolio_summary['total_value'],
                    'total_pnl': portfolio_summary['total_pnl'],
                    'return_pct': portfolio_summary['return_pct'],
                    'total_trades': self.total_trades,
                    'fees_paid': self.total_fees_paid
                })
                
                # Log progreso
                if i % 50 == 0:
                    logger.info(f"Periodo {i}/{len(btc_data)} - Valor: ${portfolio_summary['total_value']:.2f} - Operaciones: {self.total_trades}")
                
                # Alternar símbolo
                use_btc = not use_btc
            
            # Crear DataFrame de resultados
            results_df = pd.DataFrame(results)
            
            if not results_df.empty:
                # Guardar resultados
                results_df.to_csv('simple_roi_results.csv', index=False)
                
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
                logger.info("RESUMEN FINAL - SISTEMA SIMPLE ROI")
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
                    
                    # Sugerencias
                    if self.total_trades < 10:
                        logger.info("SUGERENCIA: Reducir umbrales para generar más operaciones")
                    if win_rate < 0.5:
                        logger.info("SUGERENCIA: Mejorar filtros de calidad de señales")
                    if monthly_roi < 0:
                        logger.info("SUGERENCIA: Ajustar stop-loss y take-profit")
                
                return results_df
            else:
                logger.error("No se generaron resultados")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error en backtest simple: {e}")
            return pd.DataFrame()
    
    def execute_simple_trade(self, portfolio, symbol, price, position_size, action):
        """Ejecuta una operación simple"""
        try:
            if action == 'buy' and position_size > 0:
                quantity = position_size / price
                fees = position_size * self.fee_rate
                
                stop_loss_price = price * (1 - self.stop_loss_pct)
                take_profit_price = price * (1 + self.take_profit_pct)
                
                portfolio.open_position(symbol, price, quantity, stop_loss_price, take_profit_price)
                self.total_trades += 1
                self.total_fees_paid += fees
                return fees
            return 0.0
        except Exception as e:
            logger.error(f"Error ejecutando trade simple: {e}")
            return 0.0
    
    def manage_simple_risk(self, portfolio, price, symbol):
        """Gestiona el riesgo de forma simple"""
        try:
            if portfolio.has_position(symbol):
                position = portfolio.positions[symbol]
                entry_price = position['entry_price']
                current_pnl_pct = (price - entry_price) / entry_price
                
                if price <= position['stop_loss_price']:
                    portfolio.close_position(symbol, price)
                    self.losing_trades += 1
                    self.current_consecutive_losses += 1
                    self.max_consecutive_losses = max(self.max_consecutive_losses, self.current_consecutive_losses)
                    logger.info(f"{symbol} Stop Loss @ ${price:.2f} - Loss: {current_pnl_pct*100:.2f}%")
                
                elif price >= position['take_profit_price']:
                    portfolio.close_position(symbol, price)
                    self.winning_trades += 1
                    self.current_consecutive_losses = 0
                    logger.info(f"{symbol} Take Profit @ ${price:.2f} - Profit: {current_pnl_pct*100:.2f}%")
                        
        except Exception as e:
            logger.error(f"Error en gestión de riesgo simple: {e}")

class SimplePortfolio:
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
    logger.info("Iniciando Sistema Simple ROI 15%")
    
    system = SimpleROISystem(initial_capital=500)
    results = system.run_simple_backtest()
    
    if not results.empty:
        print(f"\nSistema simple completado!")
        print(f"Resultados guardados en: simple_roi_results.csv")
        print(f"Log guardado en: simple_roi_system.log")
    else:
        print("Error en el sistema simple")

if __name__ == "__main__":
    main()