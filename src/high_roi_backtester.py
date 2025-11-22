# /src/high_roi_backtester.py
"""
Backtester Optimizado para Alto ROI - Objetivo: 15% mensual después de fees
Incluye apalancamiento controlado, fees reales y estrategias agresivas.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from datetime import datetime
import sys
import os

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from robust_data_fetcher import RobustDataFetcher
from multi_symbol_portfolio import MultiSymbolPortfolio

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('high_roi_backtest.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HighROIBacktester:
    """Backtester optimizado para alto ROI con gestión avanzada de riesgo."""
    
    def __init__(self, initial_capital: float = 500.0, leverage: float = 1.0):
        """
        Inicializa el backtester de alto ROI.
        
        Args:
            initial_capital: Capital inicial
            leverage: Apalancamiento máximo permitido
        """
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.symbols = ['BTCUSDT', 'ETHUSDT']
        
        # Fees de Binance
        self.maker_fee = 0.001  # 0.1%
        self.taker_fee = 0.001  # 0.1%
        
        # Configuración agresiva
        self.risk_per_trade = 0.05  # 5% de riesgo por operación
        self.max_positions = 4  # Máximo 4 posiciones simultáneas
        self.signal_threshold = 0.1  # Umbral muy bajo para más operaciones
        self.confidence_threshold = 0.15  # Umbral de confianza muy bajo
        
        # Métricas de rendimiento
        self.total_fees_paid = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
    def calculate_advanced_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula indicadores técnicos avanzados para señales más precisas.
        
        Args:
            data: DataFrame con datos OHLCV
            
        Returns:
            DataFrame con indicadores avanzados
        """
        df = data.copy()
        
        try:
            # RSI múltiples períodos
            for period in [7, 14, 21]:
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
                rs = gain / loss
                df[f'RSI_{period}'] = 100 - (100 / (1 + rs))
            
            # Medias móviles múltiples
            for period in [5, 10, 20, 50]:
                df[f'SMA_{period}'] = df['Close'].rolling(window=period).mean()
                df[f'EMA_{period}'] = df['Close'].ewm(span=period).mean()
            
            # MACD múltiples
            df['MACD_12_26'] = df['EMA_12'] - df['EMA_26']
            df['MACD_Signal_12_26'] = df['MACD_12_26'].ewm(span=9).mean()
            df['MACD_Histogram_12_26'] = df['MACD_12_26'] - df['MACD_Signal_12_26']
            
            # MACD rápido
            df['EMA_5'] = df['Close'].ewm(span=5).mean()
            df['EMA_13'] = df['Close'].ewm(span=13).mean()
            df['MACD_5_13'] = df['EMA_5'] - df['EMA_13']
            df['MACD_Signal_5_13'] = df['MACD_5_13'].ewm(span=4).mean()
            
            # Bandas de Bollinger múltiples
            for period in [10, 20]:
                bb_middle = df['Close'].rolling(window=period).mean()
                bb_std = df['Close'].rolling(window=period).std()
                df[f'BB_Upper_{period}'] = bb_middle + (bb_std * 2)
                df[f'BB_Lower_{period}'] = bb_middle - (bb_std * 2)
                df[f'BB_Position_{period}'] = (df['Close'] - df[f'BB_Lower_{period}']) / (df[f'BB_Upper_{period}'] - df[f'BB_Lower_{period}'])
            
            # Momentum y volatilidad
            df['Momentum_5'] = df['Close'] / df['Close'].shift(5) - 1
            df['Momentum_10'] = df['Close'] / df['Close'].shift(10) - 1
            df['Volatility_10'] = df['Close'].pct_change().rolling(10).std()
            df['Volatility_20'] = df['Close'].pct_change().rolling(20).std()
            
            # Stochastic RSI
            rsi_14 = df['RSI_14']
            stoch_rsi = (rsi_14 - rsi_14.rolling(14).min()) / (rsi_14.rolling(14).max() - rsi_14.rolling(14).min())
            df['StochRSI'] = stoch_rsi.rolling(3).mean()
            
            # Williams %R
            high_14 = df['High'].rolling(14).max()
            low_14 = df['Low'].rolling(14).min()
            df['Williams_R'] = -100 * (high_14 - df['Close']) / (high_14 - low_14)
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculando indicadores avanzados: {e}")
            return df
    
    def generate_aggressive_signal(self, data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Genera señales agresivas para maximizar oportunidades de trading.
        
        Args:
            data: DataFrame con datos e indicadores
            symbol: Símbolo del activo
            
        Returns:
            Diccionario con información de la señal
        """
        try:
            if len(data) < 50:
                return self._empty_signal(data)
            
            latest = data.iloc[-1]
            prev = data.iloc[-2]
            
            # Recopilar indicadores
            indicators = {
                'rsi_7': latest.get('RSI_7', 50),
                'rsi_14': latest.get('RSI_14', 50),
                'rsi_21': latest.get('RSI_21', 50),
                'macd_fast': latest.get('MACD_5_13', 0),
                'macd_signal_fast': latest.get('MACD_Signal_5_13', 0),
                'macd_slow': latest.get('MACD_12_26', 0),
                'macd_signal_slow': latest.get('MACD_Signal_12_26', 0),
                'bb_pos_10': latest.get('BB_Position_10', 0.5),
                'bb_pos_20': latest.get('BB_Position_20', 0.5),
                'momentum_5': latest.get('Momentum_5', 0),
                'momentum_10': latest.get('Momentum_10', 0),
                'stoch_rsi': latest.get('StochRSI', 0.5),
                'williams_r': latest.get('Williams_R', -50),
                'volatility': latest.get('Volatility_10', 0.02),
                'price': latest['Close']
            }
            
            # Señales individuales con pesos
            signals = []
            weights = []
            strategies = []
            
            # RSI multi-timeframe (peso alto)
            rsi_signal, rsi_strategy = self._calculate_rsi_signal(indicators)
            signals.append(rsi_signal)
            weights.append(0.25)
            strategies.append(rsi_strategy)
            
            # MACD multi-timeframe (peso alto)
            macd_signal, macd_strategy = self._calculate_macd_signal(indicators, prev)
            signals.append(macd_signal)
            weights.append(0.25)
            strategies.append(macd_strategy)
            
            # Bandas de Bollinger (peso medio)
            bb_signal, bb_strategy = self._calculate_bb_signal(indicators)
            signals.append(bb_signal)
            weights.append(0.2)
            strategies.append(bb_strategy)
            
            # Momentum (peso medio)
            momentum_signal, momentum_strategy = self._calculate_momentum_signal(indicators)
            signals.append(momentum_signal)
            weights.append(0.15)
            strategies.append(momentum_strategy)
            
            # Stochastic RSI (peso bajo)
            stoch_signal, stoch_strategy = self._calculate_stoch_signal(indicators)
            signals.append(stoch_signal)
            weights.append(0.15)
            strategies.append(stoch_strategy)
            
            # Combinar señales con pesos
            if signals and weights:
                combined_signal = np.average(signals, weights=weights)
                confidence = min(0.95, abs(combined_signal) + 0.2)  # Confianza más alta
                dominant_strategy = strategies[np.argmax([abs(s) for s in signals])]
            else:
                combined_signal = 0.0
                confidence = 0.0
                dominant_strategy = 'no_signal'
            
            # Ajuste por volatilidad
            vol_adjustment = min(1.5, 1 + indicators['volatility'] * 10)
            combined_signal *= vol_adjustment
            
            # Determinar régimen de mercado
            regime = self._determine_market_regime(indicators)
            
            return {
                'signal': combined_signal,
                'confidence': confidence,
                'strategy': dominant_strategy,
                'regime': regime,
                'price': indicators['price'],
                'indicators': indicators,
                'volatility_adjustment': vol_adjustment
            }
            
        except Exception as e:
            logger.error(f"Error generando señal agresiva para {symbol}: {e}")
            return self._empty_signal(data)
    
    def _calculate_rsi_signal(self, indicators: Dict) -> Tuple[float, str]:
        """Calcula señal basada en RSI multi-timeframe."""
        rsi_7 = indicators['rsi_7']
        rsi_14 = indicators['rsi_14']
        rsi_21 = indicators['rsi_21']
        
        # Señales extremas
        if rsi_7 < 20 and rsi_14 < 30:
            return 0.9, 'RSI_extreme_oversold'
        elif rsi_7 > 80 and rsi_14 > 70:
            return -0.9, 'RSI_extreme_overbought'
        
        # Señales fuertes
        elif rsi_7 < 30 or rsi_14 < 35:
            return 0.6, 'RSI_oversold'
        elif rsi_7 > 70 or rsi_14 > 65:
            return -0.6, 'RSI_overbought'
        
        # Señales medias
        elif rsi_14 < 45 and rsi_21 < 50:
            return 0.3, 'RSI_bullish'
        elif rsi_14 > 55 and rsi_21 > 50:
            return -0.3, 'RSI_bearish'
        
        return 0.0, 'RSI_neutral'
    
    def _calculate_macd_signal(self, indicators: Dict, prev_data: pd.Series) -> Tuple[float, str]:
        """Calcula señal basada en MACD multi-timeframe."""
        macd_fast = indicators['macd_fast']
        macd_signal_fast = indicators['macd_signal_fast']
        macd_slow = indicators['macd_slow']
        macd_signal_slow = indicators['macd_signal_slow']
        
        # Cruces rápidos
        if macd_fast > macd_signal_fast and prev_data.get('MACD_5_13', 0) <= prev_data.get('MACD_Signal_5_13', 0):
            return 0.8, 'MACD_fast_bullish_cross'
        elif macd_fast < macd_signal_fast and prev_data.get('MACD_5_13', 0) >= prev_data.get('MACD_Signal_5_13', 0):
            return -0.8, 'MACD_fast_bearish_cross'
        
        # Cruces lentos
        elif macd_slow > macd_signal_slow and prev_data.get('MACD_12_26', 0) <= prev_data.get('MACD_Signal_12_26', 0):
            return 0.6, 'MACD_slow_bullish_cross'
        elif macd_slow < macd_signal_slow and prev_data.get('MACD_12_26', 0) >= prev_data.get('MACD_Signal_12_26', 0):
            return -0.6, 'MACD_slow_bearish_cross'
        
        # Tendencias
        elif macd_fast > macd_signal_fast and macd_slow > macd_signal_slow:
            return 0.4, 'MACD_double_bullish'
        elif macd_fast < macd_signal_fast and macd_slow < macd_signal_slow:
            return -0.4, 'MACD_double_bearish'
        
        return 0.0, 'MACD_neutral'
    
    def _calculate_bb_signal(self, indicators: Dict) -> Tuple[float, str]:
        """Calcula señal basada en Bandas de Bollinger."""
        bb_pos_10 = indicators['bb_pos_10']
        bb_pos_20 = indicators['bb_pos_20']
        
        # Señales extremas
        if bb_pos_10 < 0.1 and bb_pos_20 < 0.15:
            return 0.7, 'BB_extreme_oversold'
        elif bb_pos_10 > 0.9 and bb_pos_20 > 0.85:
            return -0.7, 'BB_extreme_overbought'
        
        # Señales normales
        elif bb_pos_20 < 0.2:
            return 0.4, 'BB_oversold'
        elif bb_pos_20 > 0.8:
            return -0.4, 'BB_overbought'
        
        return 0.0, 'BB_neutral'
    
    def _calculate_momentum_signal(self, indicators: Dict) -> Tuple[float, str]:
        """Calcula señal basada en momentum."""
        mom_5 = indicators['momentum_5']
        mom_10 = indicators['momentum_10']
        
        if mom_5 > 0.03 and mom_10 > 0.02:
            return 0.6, 'Momentum_strong_bullish'
        elif mom_5 < -0.03 and mom_10 < -0.02:
            return -0.6, 'Momentum_strong_bearish'
        elif mom_5 > 0.01:
            return 0.3, 'Momentum_bullish'
        elif mom_5 < -0.01:
            return -0.3, 'Momentum_bearish'
        
        return 0.0, 'Momentum_neutral'
    
    def _calculate_stoch_signal(self, indicators: Dict) -> Tuple[float, str]:
        """Calcula señal basada en Stochastic RSI."""
        stoch_rsi = indicators['stoch_rsi']
        williams_r = indicators['williams_r']
        
        if stoch_rsi < 0.2 and williams_r < -80:
            return 0.5, 'Stoch_oversold'
        elif stoch_rsi > 0.8 and williams_r > -20:
            return -0.5, 'Stoch_overbought'
        
        return 0.0, 'Stoch_neutral'
    
    def _determine_market_regime(self, indicators: Dict) -> str:
        """Determina el régimen de mercado."""
        volatility = indicators['volatility']
        momentum = indicators['momentum_10']
        
        if volatility > 0.04:
            if momentum > 0.02:
                return 'alta_volatilidad_alcista'
            elif momentum < -0.02:
                return 'alta_volatilidad_bajista'
            else:
                return 'alta_volatilidad_lateral'
        elif volatility < 0.015:
            return 'baja_volatilidad'
        else:
            if momentum > 0.01:
                return 'tendencia_alcista'
            elif momentum < -0.01:
                return 'tendencia_bajista'
            else:
                return 'lateral'
    
    def _empty_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Retorna una señal vacía."""
        return {
            'signal': 0.0,
            'confidence': 0.0,
            'strategy': 'insufficient_data',
            'regime': 'unknown',
            'price': data['Close'].iloc[-1] if not data.empty else 0.0,
            'indicators': {},
            'volatility_adjustment': 1.0
        }
    
    def calculate_position_size(self, signal_data: Dict, available_capital: float) -> float:
        """
        Calcula el tamaño de posición con apalancamiento y gestión de riesgo.
        
        Args:
            signal_data: Datos de la señal
            available_capital: Capital disponible
            
        Returns:
            Tamaño de posición
        """
        # Tamaño base con apalancamiento
        base_size = available_capital * self.risk_per_trade * self.leverage
        
        # Ajuste por confianza de la señal
        confidence_multiplier = signal_data['confidence']
        
        # Ajuste por volatilidad (más volatilidad = menor posición)
        volatility = signal_data['indicators'].get('volatility', 0.02)
        volatility_adjustment = max(0.5, 1 - volatility * 10)
        
        # Tamaño final
        position_size = base_size * confidence_multiplier * volatility_adjustment
        
        # Convertir a cantidad de activo
        price = signal_data['price']
        quantity = position_size / price
        
        return quantity
    
    def calculate_fees(self, trade_value: float, is_maker: bool = False) -> float:
        """
        Calcula los fees de una operación.
        
        Args:
            trade_value: Valor de la operación
            is_maker: Si es orden maker (menor fee)
            
        Returns:
            Fee calculado
        """
        fee_rate = self.maker_fee if is_maker else self.taker_fee
        return trade_value * fee_rate
    
    def run_high_roi_backtest(self) -> pd.DataFrame:
        """
        Ejecuta el backtesting optimizado para alto ROI.
        
        Returns:
            DataFrame con resultados
        """
        try:
            logger.info("Iniciando backtesting optimizado para alto ROI (objetivo: 15% mensual)")
            
            # Inicializar componentes
            fetcher = RobustDataFetcher()
            
            # Obtener datos
            all_data = {}
            for symbol in self.symbols:
                logger.info(f"Obteniendo datos para {symbol}")
                data = fetcher.get_market_data(symbol, interval='1h', limit=1000)  # Datos horarios para más oportunidades
                if data is not None and not data.empty:
                    data_with_indicators = self.calculate_advanced_indicators(data)
                    all_data[symbol] = data_with_indicators
                    logger.info(f"{symbol}: {len(data)} periodos obtenidos")
                else:
                    logger.error(f"No se pudieron obtener datos para {symbol}")
                    return pd.DataFrame()
            
            if not all_data:
                logger.error("No se pudieron obtener datos")
                return pd.DataFrame()
            
            # Inicializar portfolio con apalancamiento
            portfolio = MultiSymbolPortfolio(
                symbols=list(all_data.keys()),
                capital_allocation={'BTCUSDT': 0.5, 'ETHUSDT': 0.5}
            )
            
            # Simular capital con apalancamiento
            effective_capital = self.initial_capital * self.leverage
            
            results = []
            min_length = min(len(data) for data in all_data.values())
            
            logger.info(f"Ejecutando backtest en {min_length} periodos")
            
            for i in range(50, min_length):
                period_results = []
                
                for symbol in all_data.keys():
                    try:
                        historical_data = all_data[symbol].iloc[:i+1]
                        current_time = historical_data.index[-1]
                        
                        # Generar señal agresiva
                        signal_data = self.generate_aggressive_signal(historical_data, symbol)
                        
                        # Ejecutar operación con umbrales muy bajos
                        if abs(signal_data['signal']) > self.signal_threshold and signal_data['confidence'] > self.confidence_threshold:
                            
                            # Calcular tamaño de posición
                            available_capital = portfolio.positions[symbol].available_capital
                            position_size = self.calculate_position_size(signal_data, available_capital)
                            
                            trade_value = position_size * signal_data['price']
                            
                            if signal_data['signal'] > 0:
                                # Operación de compra
                                fees = self.calculate_fees(trade_value)
                                self.total_fees_paid += fees
                                
                                portfolio.open_position(
                                    symbol=symbol,
                                    size=position_size,
                                    entry_price=signal_data['price']
                                )
                                
                                self.total_trades += 1
                                logger.info(f"{symbol}: LONG ${trade_value:.2f} @ ${signal_data['price']:.2f} (Fee: ${fees:.2f})")
                                
                            else:
                                # Operación de venta
                                fees = self.calculate_fees(trade_value)
                                self.total_fees_paid += fees
                                
                                portfolio.open_position(
                                    symbol=symbol,
                                    size=-position_size,
                                    entry_price=signal_data['price']
                                )
                                
                                self.total_trades += 1
                                logger.info(f"{symbol}: SHORT ${trade_value:.2f} @ ${signal_data['price']:.2f} (Fee: ${fees:.2f})")
                        
                        # Gestión de posiciones existentes
                        if portfolio.is_position_open(symbol):
                            current_position = portfolio.positions[symbol]
                            should_close = False
                            
                            if hasattr(current_position, 'size'):
                                # Stop loss dinámico
                                if current_position.size > 0 and signal_data['signal'] < -0.3:
                                    should_close = True
                                elif current_position.size < 0 and signal_data['signal'] > 0.3:
                                    should_close = True
                                elif signal_data['confidence'] < 0.1:  # Muy baja confianza
                                    should_close = True
                            
                            if should_close:
                                close_value = abs(current_position.size) * signal_data['price']
                                fees = self.calculate_fees(close_value)
                                self.total_fees_paid += fees
                                
                                portfolio.close_position(symbol, signal_data['price'])
                                logger.info(f"{symbol}: Cerrando posición @ ${signal_data['price']:.2f} (Fee: ${fees:.2f})")
                        
                        # Actualizar precios
                        portfolio.update_prices({symbol: signal_data['price']})
                        
                        # Guardar resultados
                        portfolio_summary = portfolio.get_portfolio_summary()
                        
                        position_status = 'none'
                        position_size_current = 0
                        if portfolio.is_position_open(symbol):
                            pos = portfolio.positions[symbol]
                            if hasattr(pos, 'size'):
                                position_status = 'long' if pos.size > 0 else 'short'
                                position_size_current = abs(pos.size)
                        
                        period_result = {
                            'timestamp': current_time,
                            'symbol': symbol,
                            'price': signal_data['price'],
                            'signal': signal_data['signal'],
                            'confidence': signal_data['confidence'],
                            'strategy': signal_data['strategy'],
                            'regime': signal_data['regime'],
                            'portfolio_value': portfolio_summary['total_value'],
                            'total_pnl': portfolio_summary['total_pnl'],
                            'return_pct': portfolio_summary['total_return'],
                            'position': position_status,
                            'position_size': position_size_current,
                            'fees_paid': self.total_fees_paid,
                            'total_trades': self.total_trades,
                            'volatility_adj': signal_data.get('volatility_adjustment', 1.0)
                        }
                        
                        period_results.append(period_result)
                        
                    except Exception as e:
                        logger.error(f"Error procesando {symbol} en periodo {i}: {e}")
                        continue
                
                results.extend(period_results)
                
                # Log progreso
                if i % 50 == 0:
                    portfolio_summary = portfolio.get_portfolio_summary()
                    logger.info(f"Periodo {i}/{min_length} - Valor: ${portfolio_summary['total_value']:.2f} - Fees: ${self.total_fees_paid:.2f}")
            
            # Crear DataFrame de resultados
            results_df = pd.DataFrame(results)
            
            if not results_df.empty:
                # Guardar resultados
                results_df.to_csv('high_roi_backtest_results.csv', index=False)
                
                # Calcular métricas finales
                final_summary = portfolio.get_portfolio_summary()
                net_pnl = final_summary['total_pnl'] - self.total_fees_paid
                net_return = net_pnl / self.initial_capital
                
                # Calcular ROI mensual
                duration_days = (results_df['timestamp'].max() - results_df['timestamp'].min()).days
                duration_months = duration_days / 30.44
                monthly_roi = (((final_summary['total_value'] - self.total_fees_paid) / self.initial_capital) ** (1/duration_months) - 1) if duration_months > 0 else 0
                
                logger.info("=" * 60)
                logger.info("RESUMEN FINAL - BACKTESTING ALTO ROI")
                logger.info("=" * 60)
                logger.info(f"Capital inicial: ${self.initial_capital:.2f}")
                logger.info(f"Apalancamiento: {self.leverage}x")
                logger.info(f"Valor final: ${final_summary['total_value']:.2f}")
                logger.info(f"PnL bruto: ${final_summary['total_pnl']:.2f}")
                logger.info(f"Fees totales: ${self.total_fees_paid:.2f}")
                logger.info(f"PnL neto: ${net_pnl:.2f}")
                logger.info(f"Retorno neto: {net_return*100:.2f}%")
                logger.info(f"ROI mensual: {monthly_roi*100:.2f}%")
                logger.info(f"Total operaciones: {self.total_trades}")
                logger.info(f"Drawdown máximo: {final_summary['max_drawdown']:.2f}%")
                
                # Verificar objetivo
                target_achieved = monthly_roi >= 0.15
                logger.info(f"Objetivo 15% mensual: {'✓ ALCANZADO' if target_achieved else '✗ NO ALCANZADO'}")
                
                if not target_achieved:
                    gap = 0.15 - monthly_roi
                    logger.info(f"Brecha restante: {gap*100:.2f}%")
                
            return results_df
            
        except Exception as e:
            logger.error(f"Error en backtesting alto ROI: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

def main():
    """Función principal."""
    backtester = HighROIBacktester(initial_capital=500.0, leverage=3.0)  # Apalancamiento 3x
    results = backtester.run_high_roi_backtest()
    
    if not results.empty:
        print(f"\nBacktesting completado!")
        print(f"Resultados guardados en: high_roi_backtest_results.csv")
        print(f"Log guardado en: high_roi_backtest.log")
    else:
        print("Error en el backtesting")

if __name__ == "__main__":
    main()