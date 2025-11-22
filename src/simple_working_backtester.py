#!/usr/bin/env python3
"""
Backtester Multi-Símbolo Simplificado y Funcional
Versión que funciona sin dependencias complejas de modelos entrenados
"""

import os
import sys
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('simple_working_backtest.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from robust_data_fetcher import RobustDataFetcher
from multi_symbol_portfolio import MultiSymbolPortfolio
from config import TRADING_SYMBOLS, CAPITAL_ALLOCATION

def calculate_simple_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula indicadores técnicos simples"""
    try:
        df = df.copy()
        
        if len(df) < 50:
            logger.warning(f"Datos insuficientes: {len(df)} filas")
            return df
        
        # RSI simple
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Medias móviles
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        
        # MACD simple
        df['EMA_12'] = df['Close'].ewm(span=12).mean()
        df['EMA_26'] = df['Close'].ewm(span=26).mean()
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
        
        # Bollinger Bands
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        
        return df
        
    except Exception as e:
        logger.error(f"Error calculando indicadores: {e}")
        return df

def generate_simple_signal(df: pd.DataFrame, symbol: str) -> Dict:
    """Genera señales de trading simples basadas en indicadores técnicos"""
    try:
        if len(df) < 50:
            return {
                'signal': 0.0,
                'confidence': 0.0,
                'strategy': 'none',
                'regime': 'unknown',
                'price': df['Close'].iloc[-1] if len(df) > 0 else 0.0
            }
        
        # Calcular indicadores
        df_with_indicators = calculate_simple_indicators(df)
        current_data = df_with_indicators.iloc[-1]
        
        signals = []
        confidences = []
        strategies = []
        
        # Estrategia 1: RSI
        if not pd.isna(current_data['RSI']):
            if current_data['RSI'] < 30:
                signals.append(0.8)  # Señal de compra fuerte
                confidences.append(0.7)
                strategies.append('RSI_oversold')
            elif current_data['RSI'] > 70:
                signals.append(-0.8)  # Señal de venta fuerte
                confidences.append(0.7)
                strategies.append('RSI_overbought')
            else:
                signals.append(0.0)
                confidences.append(0.3)
                strategies.append('RSI_neutral')
        
        # Estrategia 2: Cruce de medias móviles
        if not pd.isna(current_data['SMA_20']) and not pd.isna(current_data['SMA_50']):
            if current_data['SMA_20'] > current_data['SMA_50']:
                # Tendencia alcista
                if current_data['Close'] > current_data['SMA_20']:
                    signals.append(0.6)
                    confidences.append(0.6)
                    strategies.append('SMA_bullish')
                else:
                    signals.append(0.2)
                    confidences.append(0.4)
                    strategies.append('SMA_weak_bullish')
            else:
                # Tendencia bajista
                if current_data['Close'] < current_data['SMA_20']:
                    signals.append(-0.6)
                    confidences.append(0.6)
                    strategies.append('SMA_bearish')
                else:
                    signals.append(-0.2)
                    confidences.append(0.4)
                    strategies.append('SMA_weak_bearish')
        
        # Estrategia 3: MACD
        if not pd.isna(current_data['MACD']) and not pd.isna(current_data['MACD_Signal']):
            if current_data['MACD'] > current_data['MACD_Signal']:
                signals.append(0.5)
                confidences.append(0.5)
                strategies.append('MACD_bullish')
            else:
                signals.append(-0.5)
                confidences.append(0.5)
                strategies.append('MACD_bearish')
        
        # Estrategia 4: Bollinger Bands
        if not pd.isna(current_data['BB_Upper']) and not pd.isna(current_data['BB_Lower']):
            if current_data['Close'] < current_data['BB_Lower']:
                signals.append(0.7)
                confidences.append(0.6)
                strategies.append('BB_oversold')
            elif current_data['Close'] > current_data['BB_Upper']:
                signals.append(-0.7)
                confidences.append(0.6)
                strategies.append('BB_overbought')
            else:
                signals.append(0.0)
                confidences.append(0.3)
                strategies.append('BB_neutral')
        
        # Combinar señales
        if signals and confidences:
            weighted_signal = sum(s * c for s, c in zip(signals, confidences))
            total_confidence = sum(confidences)
            
            if total_confidence > 0:
                final_signal = weighted_signal / total_confidence
                final_confidence = total_confidence / len(signals)
            else:
                final_signal = 0.0
                final_confidence = 0.0
            
            # Determinar estrategia dominante
            max_conf_idx = confidences.index(max(confidences))
            dominant_strategy = strategies[max_conf_idx]
        else:
            final_signal = 0.0
            final_confidence = 0.0
            dominant_strategy = 'none'
        
        # Determinar régimen simple basado en volatilidad y tendencia
        regime = 'unknown'
        try:
            if len(df_with_indicators) >= 20:
                recent_returns = df_with_indicators['Close'].pct_change().tail(20)
                volatility = recent_returns.std()
                trend = (current_data['Close'] - df_with_indicators['Close'].iloc[-20]) / df_with_indicators['Close'].iloc[-20]
                
                if volatility > 0.03:  # Alta volatilidad
                    regime = 'volatil'
                elif trend > 0.05:  # Tendencia alcista
                    regime = 'alcista'
                elif trend < -0.05:  # Tendencia bajista
                    regime = 'bajista'
                else:
                    regime = 'lateral'
        except:
            regime = 'unknown'
        
        return {
            'signal': final_signal,
            'confidence': final_confidence,
            'strategy': dominant_strategy,
            'regime': regime,
            'price': current_data['Close']
        }
        
    except Exception as e:
        logger.error(f"Error generando señal para {symbol}: {e}")
        return {
            'signal': 0.0,
            'confidence': 0.0,
            'strategy': 'error',
            'regime': 'unknown',
            'price': df['Close'].iloc[-1] if len(df) > 0 else 0.0
        }

def run_simple_working_backtest():
    """Ejecuta el backtesting multi-símbolo simplificado"""
    logger.info("Iniciando backtesting multi-simbolo simplificado")
    
    # Inicializar fetcher de datos
    fetcher = RobustDataFetcher()
    
    # Obtener datos para todos los símbolos
    all_data = {}
    for symbol in TRADING_SYMBOLS:
        try:
            logger.info(f"Obteniendo datos para {symbol}")
            data = fetcher.get_market_data(symbol, '4h', limit=500)
            if data is not None and len(data) > 50:
                all_data[symbol] = data
                logger.info(f"{symbol}: {len(data)} periodos obtenidos")
            else:
                logger.warning(f"Datos insuficientes para {symbol}")
        except Exception as e:
            logger.error(f"Error obteniendo datos para {symbol}: {e}")
    
    if not all_data:
        logger.error("No se pudieron obtener datos para ningun simbolo")
        return
    
    # Encontrar la longitud mínima de datos
    min_length = min(len(data) for data in all_data.values())
    logger.info(f"Longitud minima de datos: {min_length} periodos")
    
    # Inicializar portfolio
    portfolio = MultiSymbolPortfolio(
        symbols=list(all_data.keys()),
        capital_allocation=CAPITAL_ALLOCATION
    )
    
    # Ejecutar backtesting
    results = []
    
    for i in range(50, min_length):  # Empezar desde el período 50 para tener suficientes datos
        for symbol in all_data.keys():
            try:
                # Obtener datos hasta el período actual
                historical_data = all_data[symbol].iloc[:i+1]
                current_time = historical_data.index[-1]
                
                # Generar señal de trading
                signal_data = generate_simple_signal(historical_data, symbol)
                
                # Ejecutar operación si hay señal fuerte (umbrales optimizados)
                if abs(signal_data['signal']) > 0.25 and signal_data['confidence'] > 0.4:
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
                    
                    # Lógica simple de cierre (umbrales optimizados)
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
                
                # Guardar resultados
                portfolio_summary = portfolio.get_portfolio_summary()
                
                position_status = 'none'
                if portfolio.is_position_open(symbol):
                    pos = portfolio.positions[symbol]
                    if hasattr(pos, 'size'):
                        position_status = 'long' if pos.size > 0 else 'short'
                
                results.append({
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
                    'position': position_status
                })
                
            except Exception as e:
                logger.error(f"Error procesando {symbol} en periodo {i}: {e}")
                continue
        
        # Log progreso cada 25 períodos
        if i % 25 == 0:
            portfolio_summary = portfolio.get_portfolio_summary()
            logger.info(f"Periodo {i}/{min_length} - Valor: ${portfolio_summary['total_value']:.2f} - PnL: ${portfolio_summary['total_pnl']:.2f}")
    
    # Guardar resultados
    if results:
        results_df = pd.DataFrame(results)
        results_df.to_csv('simple_backtest_results.csv', index=False)
        logger.info("Resultados guardados en simple_backtest_results.csv")
        
        # Mostrar resumen final
        final_summary = portfolio.get_portfolio_summary()
        logger.info("=" * 50)
        logger.info("RESUMEN FINAL DEL BACKTESTING")
        logger.info("=" * 50)
        logger.info(f"Capital inicial: $500.00")
        logger.info(f"Valor final: ${final_summary['total_value']:.2f}")
        logger.info(f"PnL total: ${final_summary['total_pnl']:.2f}")
        logger.info(f"Retorno: {final_summary['total_return']:.2f}%")
        logger.info(f"Drawdown máximo: {final_summary['max_drawdown']:.2f}%")
        logger.info(f"Posiciones abiertas: {final_summary['open_positions']}")
        
        # Estadísticas por símbolo
        for symbol in TRADING_SYMBOLS:
            symbol_results = results_df[results_df['symbol'] == symbol]
            if not symbol_results.empty:
                trades = len(symbol_results[symbol_results['position'] != 'none'])
                signals = len(symbol_results[symbol_results['signal'].abs() > 0.25])
                logger.info(f"{symbol}: {trades} operaciones, {signals} señales fuertes")
        
        print(f"\nBacktesting completado exitosamente!")
        print(f"Resultados guardados en: simple_backtest_results.csv")
        print(f"Log guardado en: simple_backtest.log")
        
        return results_df
    
    else:
        logger.error("No se generaron resultados")
        return None

def main():
    run_simple_working_backtest()

if __name__ == "__main__":
    main()