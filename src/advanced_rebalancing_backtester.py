# /src/advanced_rebalancing_backtester.py
"""
Backtester Avanzado con Rebalanceo Automático para SICAR
Combina el backtesting multi-símbolo con rebalanceo dinámico del portfolio.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from datetime import datetime
import sys
import os

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from robust_data_fetcher import RobustDataFetcher
from multi_symbol_portfolio import MultiSymbolPortfolio
from portfolio_rebalancer import PortfolioRebalancer, create_rebalancer
from config import TRADING_SYMBOLS, CAPITAL_ALLOCATION, CAPITAL_BASE

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('advanced_rebalancing_backtest.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuración del backtesting
INITIAL_CAPITAL = 500.0
SYMBOLS = ['BTCUSDT', 'ETHUSDT']
CAPITAL_ALLOCATION = {'BTCUSDT': 0.5, 'ETHUSDT': 0.5}
REBALANCE_FREQUENCY = 50  # Rebalancear cada 50 períodos

def calculate_technical_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula indicadores técnicos para el análisis.
    
    Args:
        data: DataFrame con datos OHLCV
        
    Returns:
        DataFrame con indicadores calculados
    """
    df = data.copy()
    
    try:
        # RSI (14 períodos)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Medias móviles
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['EMA_12'] = df['Close'].ewm(span=12).mean()
        df['EMA_26'] = df['Close'].ewm(span=26).mean()
        
        # MACD
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
        df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
        
        # Bandas de Bollinger
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle']
        df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
        
        return df
        
    except Exception as e:
        logger.error(f"Error calculando indicadores técnicos: {e}")
        return df

def generate_enhanced_signal(data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """
    Genera señales de trading mejoradas con múltiples indicadores.
    
    Args:
        data: DataFrame con datos e indicadores
        symbol: Símbolo del activo
        
    Returns:
        Diccionario con información de la señal
    """
    try:
        if len(data) < 50:
            return {
                'signal': 0.0,
                'confidence': 0.0,
                'strategy': 'insufficient_data',
                'regime': 'unknown',
                'price': data['Close'].iloc[-1] if not data.empty else 0.0,
                'indicators': {}
            }
        
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        
        # Valores de indicadores
        rsi = latest['RSI']
        macd = latest['MACD']
        macd_signal = latest['MACD_Signal']
        bb_position = latest['BB_Position']
        sma_20 = latest['SMA_20']
        sma_50 = latest['SMA_50']
        price = latest['Close']
        
        # Señales individuales
        signals = []
        strategies = []
        
        # Señal RSI
        if rsi < 30:
            signals.append(0.7)  # Fuerte compra
            strategies.append('RSI_oversold')
        elif rsi > 70:
            signals.append(-0.7)  # Fuerte venta
            strategies.append('RSI_overbought')
        elif rsi < 40:
            signals.append(0.3)
            strategies.append('RSI_bullish')
        elif rsi > 60:
            signals.append(-0.3)
            strategies.append('RSI_bearish')
        else:
            signals.append(0.0)
            strategies.append('RSI_neutral')
        
        # Señal MACD
        if macd > macd_signal and prev['MACD'] <= prev['MACD_Signal']:
            signals.append(0.6)  # Cruce alcista
            strategies.append('MACD_bullish_cross')
        elif macd < macd_signal and prev['MACD'] >= prev['MACD_Signal']:
            signals.append(-0.6)  # Cruce bajista
            strategies.append('MACD_bearish_cross')
        elif macd > macd_signal:
            signals.append(0.2)
            strategies.append('MACD_bullish')
        else:
            signals.append(-0.2)
            strategies.append('MACD_bearish')
        
        # Señal Bandas de Bollinger
        if bb_position < 0.2:
            signals.append(0.5)  # Cerca del límite inferior
            strategies.append('BB_oversold')
        elif bb_position > 0.8:
            signals.append(-0.5)  # Cerca del límite superior
            strategies.append('BB_overbought')
        else:
            signals.append(0.0)
            strategies.append('BB_neutral')
        
        # Señal de tendencia (SMA)
        if price > sma_20 > sma_50:
            signals.append(0.4)
            strategies.append('SMA_bullish')
        elif price < sma_20 < sma_50:
            signals.append(-0.4)
            strategies.append('SMA_bearish')
        else:
            signals.append(0.0)
            strategies.append('SMA_neutral')
        
        # Combinar señales
        if signals:
            combined_signal = np.mean(signals)
            confidence = min(0.9, abs(combined_signal) + 0.1)
            dominant_strategy = strategies[np.argmax([abs(s) for s in signals])]
        else:
            combined_signal = 0.0
            confidence = 0.0
            dominant_strategy = 'no_signal'
        
        # Determinar régimen de mercado
        volatility = data['Close'].pct_change().rolling(20).std().iloc[-1]
        if volatility > 0.03:
            regime = 'alta_volatilidad'
        elif volatility < 0.015:
            regime = 'baja_volatilidad'
        else:
            regime = 'volatilidad_normal'
        
        return {
            'signal': combined_signal,
            'confidence': confidence,
            'strategy': dominant_strategy,
            'regime': regime,
            'price': price,
            'indicators': {
                'rsi': rsi,
                'macd': macd,
                'bb_position': bb_position,
                'sma_trend': 'bullish' if price > sma_20 > sma_50 else 'bearish' if price < sma_20 < sma_50 else 'neutral',
                'volatility': volatility
            }
        }
        
    except Exception as e:
        logger.error(f"Error generando señal para {symbol}: {e}")
        return {
            'signal': 0.0,
            'confidence': 0.0,
            'strategy': 'error',
            'regime': 'unknown',
            'price': data['Close'].iloc[-1] if not data.empty else 0.0,
            'indicators': {}
        }

def run_advanced_rebalancing_backtest():
    """
    Ejecuta el backtesting avanzado con rebalanceo automático.
    """
    try:
        logger.info("Iniciando backtesting avanzado con rebalanceo automatico")
        
        # Inicializar componentes
        fetcher = RobustDataFetcher()
        rebalancer = create_rebalancer({
            'min_allocation': 0.2,
            'max_allocation': 0.8,
            'rebalance_threshold': 0.1,
            'lookback_periods': 50
        })
        
        # Obtener datos para todos los símbolos
        all_data = {}
        for symbol in SYMBOLS:
            logger.info(f"Obteniendo datos para {symbol}")
            data = fetcher.get_market_data(symbol, interval='4h', limit=500)
            if data is not None and not data.empty:
                # Calcular indicadores técnicos
                data_with_indicators = calculate_technical_indicators(data)
                all_data[symbol] = data_with_indicators
                logger.info(f"{symbol}: {len(data)} periodos obtenidos")
            else:
                logger.error(f"No se pudieron obtener datos para {symbol}")
                return None
        
        if not all_data:
            logger.error("No se pudieron obtener datos para ningun simbolo")
            return None
        
        # Encontrar la longitud mínima de datos
        min_length = min(len(data) for data in all_data.values())
        logger.info(f"Longitud minima de datos: {min_length} periodos")
        
        # Inicializar portfolio
        portfolio = MultiSymbolPortfolio(
            symbols=list(all_data.keys()),
            capital_allocation=CAPITAL_ALLOCATION
        )
        
        # Ejecutar backtesting con rebalanceo
        results = []
        rebalance_events = []
        
        for i in range(50, min_length):  # Empezar desde el período 50
            period_results = []
            
            # Procesar cada símbolo en el período actual
            for symbol in all_data.keys():
                try:
                    # Obtener datos hasta el período actual
                    historical_data = all_data[symbol].iloc[:i+1]
                    current_time = historical_data.index[-1]
                    
                    # Generar señal de trading
                    signal_data = generate_enhanced_signal(historical_data, symbol)
                    
                    # Ejecutar operación si hay señal válida (umbrales muy optimizados)
                    if abs(signal_data['signal']) > 0.15 and signal_data['confidence'] > 0.2:
                        # Calcular tamaño de posición (2% de riesgo)
                        available_capital = portfolio.positions[symbol].available_capital
                        risk_amount = available_capital * 0.02
                        position_size = risk_amount / signal_data['price']
                        
                        if signal_data['signal'] > 0:
                            # Señal de compra
                            portfolio.open_position(
                                symbol=symbol,
                                size=position_size,
                                entry_price=signal_data['price']
                            )
                            logger.info(f"{symbol}: Abriendo posicion LONG - Precio: ${signal_data['price']:.2f}")
                        else:
                            # Señal de venta
                            portfolio.open_position(
                                symbol=symbol,
                                size=-position_size,
                                entry_price=signal_data['price']
                            )
                            logger.info(f"{symbol}: Abriendo posicion SHORT - Precio: ${signal_data['price']:.2f}")
                    
                    # Cerrar posiciones si la señal cambia
                    if portfolio.is_position_open(symbol):
                        current_position = portfolio.positions[symbol]
                        should_close = False
                        
                        if hasattr(current_position, 'size'):
                            if current_position.size > 0 and signal_data['signal'] < -0.2:
                                should_close = True
                            elif current_position.size < 0 and signal_data['signal'] > 0.2:
                                should_close = True
                            elif signal_data['confidence'] < 0.25:
                                should_close = True
                        
                        if should_close:
                            portfolio.close_position(symbol, signal_data['price'])
                            logger.info(f"{symbol}: Cerrando posicion - Precio: ${signal_data['price']:.2f}")
                    
                    # Actualizar precios del portfolio
                    portfolio.update_prices({symbol: signal_data['price']})
                    
                    # Guardar resultados del período
                    portfolio_summary = portfolio.get_portfolio_summary()
                    
                    position_status = 'none'
                    if portfolio.is_position_open(symbol):
                        pos = portfolio.positions[symbol]
                        if hasattr(pos, 'size'):
                            position_status = 'long' if pos.size > 0 else 'short'
                    
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
                        'allocation': portfolio.capital_allocation.get(symbol, 0.5),
                        'rsi': signal_data['indicators'].get('rsi', 0),
                        'macd': signal_data['indicators'].get('macd', 0),
                        'volatility': signal_data['indicators'].get('volatility', 0)
                    }
                    
                    period_results.append(period_result)
                    
                except Exception as e:
                    logger.error(f"Error procesando {symbol} en periodo {i}: {e}")
                    continue
            
            # Agregar resultados del período
            results.extend(period_results)
            
            # Ejecutar rebalanceo periódico
            if i % REBALANCE_FREQUENCY == 0 and len(results) > 100:
                logger.info(f"Evaluando rebalanceo en periodo {i}")
                
                # Crear DataFrame temporal para análisis
                temp_df = pd.DataFrame(results)
                
                # Analizar y ejecutar rebalanceo si es necesario
                rebalance_analysis = rebalancer.analyze_and_rebalance(portfolio, temp_df)
                
                if rebalance_analysis.get('rebalance_executed', False):
                    logger.info("Rebalanceo ejecutado exitosamente")
                    rebalance_events.append({
                        'period': i,
                        'timestamp': rebalance_analysis['timestamp'],
                        'old_allocations': rebalance_analysis['current_allocations'],
                        'new_allocations': rebalance_analysis['recommended_allocations']
                    })
            
            # Log progreso cada 25 períodos
            if i % 25 == 0:
                portfolio_summary = portfolio.get_portfolio_summary()
                logger.info(f"Periodo {i}/{min_length} - Valor: ${portfolio_summary['total_value']:.2f} - PnL: ${portfolio_summary['total_pnl']:.2f}")
        
        # Guardar resultados
        if results:
            results_df = pd.DataFrame(results)
            results_df.to_csv('advanced_rebalancing_backtest_results.csv', index=False)
            logger.info("Resultados guardados en advanced_rebalancing_backtest_results.csv")
            
            # Guardar eventos de rebalanceo
            if rebalance_events:
                rebalance_df = pd.DataFrame(rebalance_events)
                rebalance_df.to_csv('rebalance_events.csv', index=False)
                logger.info("Eventos de rebalanceo guardados en rebalance_events.csv")
            
            # Mostrar resumen final
            final_summary = portfolio.get_portfolio_summary()
            rebalance_summary = rebalancer.get_rebalance_summary()
            
            logger.info("=" * 60)
            logger.info("RESUMEN FINAL DEL BACKTESTING AVANZADO")
            logger.info("=" * 60)
            logger.info(f"Capital inicial: ${INITIAL_CAPITAL:.2f}")
            logger.info(f"Valor final: ${final_summary['total_value']:.2f}")
            logger.info(f"PnL total: ${final_summary['total_pnl']:.2f}")
            logger.info(f"Retorno: {final_summary['total_return']:.2f}%")
            logger.info(f"Drawdown maximo: {final_summary['max_drawdown']:.2f}%")
            logger.info(f"Posiciones abiertas: {final_summary['open_positions']}")
            logger.info(f"Total de rebalanceos: {rebalance_summary['total_rebalances']}")
            
            # Estadísticas por símbolo
            logger.info("\nEstadisticas por simbolo:")
            for symbol in SYMBOLS:
                symbol_results = results_df[results_df['symbol'] == symbol]
                if not symbol_results.empty:
                    trades = len(symbol_results[symbol_results['position'] != 'none'])
                    signals = len(symbol_results[symbol_results['signal'].abs() > 0.15])
                    final_allocation = portfolio.capital_allocation.get(symbol, 0.5)
                    logger.info(f"{symbol}: {trades} operaciones, {signals} señales fuertes, asignacion final: {final_allocation*100:.1f}%")
            
            print(f"\nBacktesting avanzado completado exitosamente!")
            print(f"Resultados guardados en: advanced_rebalancing_backtest_results.csv")
            print(f"Eventos de rebalanceo en: rebalance_events.csv")
            print(f"Log guardado en: advanced_rebalancing_backtest.log")
            
            return results_df
        
        else:
            logger.error("No se generaron resultados")
            return None
            
    except Exception as e:
        logger.error(f"Error en backtesting avanzado: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Función principal."""
    run_advanced_rebalancing_backtest()

if __name__ == "__main__":
    main()