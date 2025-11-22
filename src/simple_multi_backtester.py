#!/usr/bin/env python3
"""
Backtester multi-símbolo simplificado para SICAR
Versión sin backtrader para debugging
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime
import sys
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import TRADING_SYMBOLS, CAPITAL_ALLOCATION, CAPITAL_BASE, RISK_PER_TRADE
from robust_data_fetcher import RobustDataFetcher
from multi_symbol_portfolio import MultiSymbolPortfolio
from module_1_causal import CausalCartographer
from module_2_regime import RegimeClassifier
from module_3_metacontroller import MetaController

def load_models():
    """Carga los modelos entrenados"""
    models = {}
    
    for symbol in TRADING_SYMBOLS:
        logger.info(f"🔄 Cargando modelos para {symbol}")
        
        # Cargar modelos
        regime_classifier = RegimeClassifier()
        regime_classifier.load_model('../models/regime_classifier.joblib')
        
        metacontroller = MetaController()
        metacontroller.load_model('../models/metacontroller.joblib')
        
        causal_cartographer = CausalCartographer()
        
        models[symbol] = {
            'regime_classifier': regime_classifier,
            'metacontroller': metacontroller,
            'causal_cartographer': causal_cartographer
        }
        
        logger.info(f"✅ Modelos cargados para {symbol}")
    
    return models

def get_trading_signal(df, models, symbol):
    """Genera señal de trading para un símbolo"""
    try:
        # Obtener características técnicas
        features = models['regime_classifier'].calculate_market_features(df)
        
        if features.empty:
            return {
                'signal': 0.0,
                'confidence': 0.0,
                'strategy': 'none',
                'regime': 'unknown',
                'price': df['Close'].iloc[-1]
            }
        
        # Clasificar régimen
        regime = models['regime_classifier'].predict_regime(features.tail(1))
        
        # Obtener estrategia del metacontrolador
        strategy_data = models['metacontroller'].select_strategy(features, regime)
        strategy = strategy_data['strategy']
        confidence = strategy_data['confidence']
        
        # Generar señal basada en la estrategia
        if strategy == 'momentum':
            signal = 1.0 if df['Close'].iloc[-1] > df['Close'].iloc[-5] else -1.0
        elif strategy == 'mean_reversion':
            sma_20 = df['Close'].rolling(20).mean().iloc[-1]
            signal = -1.0 if df['Close'].iloc[-1] > sma_20 * 1.02 else 1.0
        elif strategy == 'breakout':
            high_20 = df['High'].rolling(20).max().iloc[-1]
            low_20 = df['Low'].rolling(20).min().iloc[-1]
            if df['Close'].iloc[-1] > high_20 * 0.99:
                signal = 1.0
            elif df['Close'].iloc[-1] < low_20 * 1.01:
                signal = -1.0
            else:
                signal = 0.0
        else:
            signal = 0.0
        
        return {
            'signal': signal,
            'confidence': confidence,
            'strategy': strategy,
            'regime': regime,
            'price': df['Close'].iloc[-1]
        }
        
    except Exception as e:
        logger.error(f"Error generando señal para {symbol}: {e}")
        return {
            'signal': 0.0,
            'confidence': 0.0,
            'strategy': 'none',
            'regime': 'unknown',
            'price': df['Close'].iloc[-1]
        }

def run_simple_multi_backtest():
    """Ejecuta backtesting multi-símbolo simplificado"""
    try:
        logger.info("🚀 Iniciando backtesting multi-símbolo simplificado")
        
        # Cargar modelos
        models = load_models()
        
        # Inicializar fetcher de datos
        data_fetcher = RobustDataFetcher()
        
        # Inicializar portfolio multi-símbolo
        portfolio = MultiSymbolPortfolio(
            symbols=TRADING_SYMBOLS,
            capital_allocation=CAPITAL_ALLOCATION
        )
        
        # Cargar datos para cada símbolo
        data_dict = {}
        for symbol in TRADING_SYMBOLS:
            logger.info(f"📊 Cargando datos para {symbol}")
            df = data_fetcher.get_market_data(symbol, '4h', 500)
            
            if df is not None and len(df) > 50:
                data_dict[symbol] = df
                logger.info(f"✅ Datos cargados para {symbol}: {len(df)} barras")
            else:
                logger.error(f"❌ No se pudieron cargar datos para {symbol}")
                return
        
        # Simular backtesting
        logger.info("🔄 Ejecutando simulación...")
        
        # Obtener el rango de fechas común
        min_length = min(len(df) for df in data_dict.values())
        start_idx = 50  # Necesitamos datos históricos para indicadores
        
        results = []
        
        for i in range(start_idx, min_length):
            timestamp = None
            
            # Actualizar precios en el portfolio
            current_prices = {}
            for symbol in TRADING_SYMBOLS:
                df = data_dict[symbol]
                current_prices[symbol] = df['Close'].iloc[i]
                if timestamp is None:
                    timestamp = df.index[i]
            
            portfolio.update_prices(current_prices)
            
            # Generar señales para cada símbolo
            for symbol in TRADING_SYMBOLS:
                df = data_dict[symbol].iloc[:i+1]  # Datos hasta el momento actual
                
                signal_data = get_trading_signal(df, models[symbol], symbol)
                
                # Ejecutar trading si hay señal fuerte
                if abs(signal_data['signal']) > 0.5 and signal_data['confidence'] > 0.5:
                    
                    # Cerrar posición existente si es opuesta
                    if portfolio.is_position_open(symbol):
                        current_pos = portfolio.positions[symbol]
                        if (signal_data['signal'] > 0 and current_pos.side == 'short') or \
                           (signal_data['signal'] < 0 and current_pos.side == 'long'):
                            portfolio.close_position(symbol, current_prices[symbol])
                    
                    # Abrir nueva posición si no hay posición activa
                    if not portfolio.is_position_open(symbol):
                        side = 'long' if signal_data['signal'] > 0 else 'short'
                        
                        # Calcular tamaño de posición basado en riesgo
                        available_capital = portfolio.get_available_capital(symbol)
                        risk_amount = available_capital * RISK_PER_TRADE
                        position_size = risk_amount / current_prices[symbol]
                        
                        if position_size > 0.001:  # Tamaño mínimo
                            portfolio.open_position(
                                symbol=symbol,
                                side=side,
                                size=position_size,
                                entry_price=current_prices[symbol]
                            )
                
                # Registrar resultado
                portfolio_summary = portfolio.get_portfolio_summary()
                
                results.append({
                    'timestamp': timestamp,
                    'symbol': symbol,
                    'price': current_prices[symbol],
                    'signal': signal_data['signal'],
                    'confidence': signal_data['confidence'],
                    'strategy': signal_data['strategy'],
                    'regime': signal_data['regime'],
                    'portfolio_value': portfolio_summary['total_value'],
                    'total_pnl': portfolio_summary['total_pnl'],
                    'return_pct': portfolio_summary['total_return'],
                    'position': 'long' if portfolio.is_position_open(symbol) and portfolio.positions[symbol].side == 'long' else 
                               'short' if portfolio.is_position_open(symbol) and portfolio.positions[symbol].side == 'short' else 'none'
                })
        
        # Guardar resultados
        results_df = pd.DataFrame(results)
        results_df.to_csv('multi_symbol_backtest_results.csv', index=False)
        
        # Mostrar resumen final
        final_summary = portfolio.get_portfolio_summary()
        
        logger.info("📊 === RESUMEN FINAL MULTI-SÍMBOLO ===")
        logger.info(f"💰 Capital inicial: ${CAPITAL_BASE:.2f}")
        logger.info(f"💰 Valor final: ${final_summary['total_value']:.2f}")
        logger.info(f"📈 PnL total: ${final_summary['total_pnl']:.2f}")
        logger.info(f"📊 Retorno: {final_summary['total_return']:.2f}%")
        logger.info(f"📉 Drawdown máximo: {final_summary['max_drawdown']:.2f}%")
        
        logger.info("\n💼 Posiciones por símbolo:")
        for symbol in TRADING_SYMBOLS:
            if portfolio.is_position_open(symbol):
                pos = portfolio.positions[symbol]
                logger.info(f"  {symbol}: {pos.side} {pos.size:.4f} @ ${pos.entry_price:.2f}")
            else:
                logger.info(f"  {symbol}: Sin posición")
        
        logger.info(f"\n📁 Resultados guardados en: multi_symbol_backtest_results.csv")
        logger.info("✅ Backtesting multi-símbolo completado exitosamente")
        
    except Exception as e:
        logger.error(f"❌ Error en backtesting multi-símbolo: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_simple_multi_backtest()