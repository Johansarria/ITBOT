#!/usr/bin/env python3
"""
Backtester Multi-Símbolo Mejorado para SICAR
Maneja múltiples activos con gestión de riesgo distribuida y señales de trading robustas
"""

import os
import sys
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import joblib
from typing import Dict, List, Tuple, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhanced_multi_backtest.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from robust_data_fetcher import RobustDataFetcher
from multi_symbol_portfolio import MultiSymbolPortfolio
from module_2_regime import RegimeClassifier
from module_3_metacontroller import MetaController
from config import TRADING_SYMBOLS, CAPITAL_ALLOCATION

def load_models() -> Dict:
    """Carga los modelos entrenados"""
    models = {}
    models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
    
    try:
        # Siempre usar objetos nuevos para evitar problemas de serialización
        models['regime_classifier'] = RegimeClassifier()
        models['metacontroller'] = MetaController()
        
        # Intentar cargar parámetros entrenados si existen
        regime_path = os.path.join(models_dir, "regime_classifier.joblib")
        if os.path.exists(regime_path):
            try:
                loaded_data = joblib.load(regime_path)
                if hasattr(loaded_data, 'model') and hasattr(loaded_data, 'scaler'):
                    # Si es un objeto RegimeClassifier válido, usarlo
                    models['regime_classifier'] = loaded_data
                    logger.info("✅ Clasificador de régimen entrenado cargado")
                else:
                    logger.info("⚠️ Archivo de modelo no válido, usando clasificador por defecto")
            except Exception as e:
                logger.warning(f"Error cargando modelo entrenado: {e}, usando por defecto")
        else:
            logger.info("⚠️ Usando clasificador de régimen por defecto")
        
        # Similar para metacontrolador
        meta_path = os.path.join(models_dir, "metacontroller.joblib")
        if os.path.exists(meta_path):
            try:
                loaded_meta = joblib.load(meta_path)
                if hasattr(loaded_meta, 'strategies'):
                    models['metacontroller'] = loaded_meta
                    logger.info("✅ Metacontrolador entrenado cargado")
                else:
                    logger.info("⚠️ Archivo de metacontrolador no válido, usando por defecto")
            except Exception as e:
                logger.warning(f"Error cargando metacontrolador: {e}, usando por defecto")
        else:
            logger.info("⚠️ Usando metacontrolador por defecto")
            
    except Exception as e:
        logger.error(f"Error cargando modelos: {e}")
        models['regime_classifier'] = RegimeClassifier()
        models['metacontroller'] = MetaController()
    
    return models

def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula indicadores técnicos básicos para generar señales"""
    try:
        df = df.copy()
        
        # Asegurar que tenemos suficientes datos
        if len(df) < 50:
            logger.warning(f"Datos insuficientes para indicadores: {len(df)} filas")
            return df
        
        # RSI
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
        
        # Bollinger Bands
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
        
        # Volatilidad
        df['Returns'] = df['Close'].pct_change()
        df['Volatility'] = df['Returns'].rolling(window=20).std()
        
        # Momentum
        df['Momentum_10'] = df['Close'].pct_change(periods=10)
        df['Momentum_20'] = df['Close'].pct_change(periods=20)
        
        return df
        
    except Exception as e:
        logger.error(f"Error calculando indicadores técnicos: {e}")
        return df

def generate_enhanced_signal(df: pd.DataFrame, models: Dict, symbol: str) -> Dict:
    """Genera señal de trading mejorada usando múltiples estrategias"""
    try:
        if len(df) < 50:
            return {
                'signal': 0.0,
                'confidence': 0.0,
                'strategy': 'insufficient_data',
                'regime': 'unknown',
                'price': df['Close'].iloc[-1] if len(df) > 0 else 0
            }
        
        # Calcular indicadores técnicos
        df_with_indicators = calculate_technical_indicators(df)
        
        # Obtener valores actuales
        current_data = df_with_indicators.iloc[-1]
        prev_data = df_with_indicators.iloc[-2] if len(df_with_indicators) > 1 else current_data
        
        # Inicializar señales
        signals = []
        confidences = []
        strategies = []
        
        # 1. Estrategia de Momentum
        if not pd.isna(current_data.get('Momentum_10', np.nan)):
            momentum_signal = 0
            momentum_confidence = 0
            
            if current_data['Momentum_10'] > 0.02:  # 2% momentum positivo
                momentum_signal = 1
                momentum_confidence = min(abs(current_data['Momentum_10']) * 10, 1.0)
            elif current_data['Momentum_10'] < -0.02:  # 2% momentum negativo
                momentum_signal = -1
                momentum_confidence = min(abs(current_data['Momentum_10']) * 10, 1.0)
            
            signals.append(momentum_signal)
            confidences.append(momentum_confidence)
            strategies.append('momentum')
        
        # 2. Estrategia de RSI
        if not pd.isna(current_data.get('RSI', np.nan)):
            rsi_signal = 0
            rsi_confidence = 0
            
            if current_data['RSI'] < 30:  # Sobreventa
                rsi_signal = 1
                rsi_confidence = (30 - current_data['RSI']) / 30
            elif current_data['RSI'] > 70:  # Sobrecompra
                rsi_signal = -1
                rsi_confidence = (current_data['RSI'] - 70) / 30
            
            signals.append(rsi_signal)
            confidences.append(rsi_confidence)
            strategies.append('rsi')
        
        # 3. Estrategia de Medias Móviles
        if not pd.isna(current_data.get('SMA_20', np.nan)) and not pd.isna(current_data.get('SMA_50', np.nan)):
            ma_signal = 0
            ma_confidence = 0
            
            if current_data['SMA_20'] > current_data['SMA_50'] and current_data['Close'] > current_data['SMA_20']:
                ma_signal = 1
                ma_confidence = 0.7
            elif current_data['SMA_20'] < current_data['SMA_50'] and current_data['Close'] < current_data['SMA_20']:
                ma_signal = -1
                ma_confidence = 0.7
            
            signals.append(ma_signal)
            confidences.append(ma_confidence)
            strategies.append('moving_average')
        
        # 4. Estrategia de MACD
        if not pd.isna(current_data.get('MACD', np.nan)) and not pd.isna(current_data.get('MACD_Signal', np.nan)):
            macd_signal = 0
            macd_confidence = 0
            
            if current_data['MACD'] > current_data['MACD_Signal'] and prev_data['MACD'] <= prev_data['MACD_Signal']:
                macd_signal = 1
                macd_confidence = 0.8
            elif current_data['MACD'] < current_data['MACD_Signal'] and prev_data['MACD'] >= prev_data['MACD_Signal']:
                macd_signal = -1
                macd_confidence = 0.8
            
            signals.append(macd_signal)
            confidences.append(macd_confidence)
            strategies.append('macd')
        
        # 5. Estrategia de Bollinger Bands
        if not pd.isna(current_data.get('BB_Position', np.nan)):
            bb_signal = 0
            bb_confidence = 0
            
            if current_data['BB_Position'] < 0.1:  # Cerca del límite inferior
                bb_signal = 1
                bb_confidence = 0.6
            elif current_data['BB_Position'] > 0.9:  # Cerca del límite superior
                bb_signal = -1
                bb_confidence = 0.6
            
            signals.append(bb_signal)
            confidences.append(bb_confidence)
            strategies.append('bollinger')
        
        # Combinar señales
        if not signals:
            return {
                'signal': 0.0,
                'confidence': 0.0,
                'strategy': 'no_signals',
                'regime': 'unknown',
                'price': current_data['Close']
            }
        
        # Calcular señal ponderada por confianza
        weighted_signal = sum(s * c for s, c in zip(signals, confidences))
        total_confidence = sum(confidences)
        
        if total_confidence > 0:
            final_signal = weighted_signal / total_confidence
            final_confidence = total_confidence / len(signals)
        else:
            final_signal = 0.0
            final_confidence = 0.0
        
        # Determinar estrategia dominante
        if confidences:
            max_conf_idx = confidences.index(max(confidences))
            dominant_strategy = strategies[max_conf_idx]
        else:
            dominant_strategy = 'none'
        
        # Intentar clasificar régimen
        regime = 'unknown'
        try:
            # Preparar datos para el clasificador de régimen
            regime_data = df.copy()
            regime_data.columns = regime_data.columns.str.lower()
            
            if 'regime_classifier' in models:
                features = models['regime_classifier'].calculate_market_features(regime_data)
                if not features.empty and len(features) > 0:
                    regime_pred = models['regime_classifier'].predict_regime(features.tail(1))
                    if hasattr(regime_pred, '__iter__') and len(regime_pred) > 0:
                        regime_code = regime_pred[0] if hasattr(regime_pred[0], '__iter__') else regime_pred
                        regime_names = {
                            0: "lateral",
                            1: "alcista", 
                            2: "bajista",
                            3: "volatil"
                        }
                        regime = regime_names.get(regime_code, 'unknown')
        except Exception as e:
            logger.warning(f"Error clasificando régimen para {symbol}: {e}")
        
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
            'price': df['Close'].iloc[-1] if len(df) > 0 else 0
        }

def run_enhanced_multi_symbol_backtest():
    """Ejecuta el backtesting multi-símbolo mejorado"""
    logger.info("🚀 Iniciando backtesting multi-símbolo mejorado...")
    
    # Cargar modelos
    models = load_models()
    
    # Inicializar fetcher de datos
    data_fetcher = RobustDataFetcher()
    
    # Cargar datos para todos los símbolos
    all_data = {}
    for symbol in TRADING_SYMBOLS:
        try:
            logger.info(f"📊 Cargando datos para {symbol}...")
            data = data_fetcher.get_market_data(symbol, interval='4h', limit=500)
            if data is not None and not data.empty:
                all_data[symbol] = data
                logger.info(f"✅ Datos cargados para {symbol}: {len(data)} filas")
            else:
                logger.error(f"❌ No se pudieron cargar datos para {symbol}")
        except Exception as e:
            logger.error(f"❌ Error cargando datos para {symbol}: {e}")
    
    if not all_data:
        logger.error("❌ No se pudieron cargar datos para ningún símbolo")
        return
    
    # Inicializar portfolio
    portfolio = MultiSymbolPortfolio(
        symbols=list(all_data.keys()),
        capital_allocation=CAPITAL_ALLOCATION
    )
    
    # Obtener rango de fechas común
    min_length = min(len(data) for data in all_data.values())
    logger.info(f"📅 Usando {min_length} períodos para el backtesting")
    
    # Resultados del backtesting
    results = []
    
    # Simular trading
    for i in range(50, min_length):  # Empezar desde 50 para tener suficientes datos para indicadores
        current_time = None
        
        for symbol in all_data.keys():
            try:
                # Obtener datos hasta el período actual
                historical_data = all_data[symbol].iloc[:i+1]
                current_time = historical_data.index[-1]
                
                # Generar señal de trading
                signal_data = generate_enhanced_signal(historical_data, models, symbol)
                
                # Ejecutar operación si hay señal fuerte
                if abs(signal_data['signal']) > 0.3 and signal_data['confidence'] > 0.5:
                    # Calcular tamaño de posición basado en el capital disponible
                    available_capital = portfolio.positions[symbol].available_capital
                    risk_amount = available_capital * 0.02  # 2% de riesgo por trade
                    position_size = risk_amount / signal_data['price']
                    
                    if signal_data['signal'] > 0:
                        # Señal de compra (posición larga)
                        portfolio.open_position(
                            symbol=symbol,
                            size=position_size,
                            entry_price=signal_data['price']
                        )
                    else:
                        # Señal de venta (posición corta)
                        portfolio.open_position(
                            symbol=symbol,
                            size=-position_size,
                            entry_price=signal_data['price']
                        )
                
                # Cerrar posiciones si la señal cambia o es débil
                if portfolio.is_position_open(symbol):
                    current_position = portfolio.positions[symbol]
                    should_close = False
                    
                    if current_position.side == 'long' and signal_data['signal'] < -0.2:
                        should_close = True
                    elif current_position.side == 'short' and signal_data['signal'] > 0.2:
                        should_close = True
                    elif signal_data['confidence'] < 0.3:
                        should_close = True
                    
                    if should_close:
                        portfolio.close_position(symbol, signal_data['price'])
                
                # Actualizar precios del portfolio
                portfolio.update_prices({symbol: signal_data['price']})
                
                # Guardar resultados
                portfolio_summary = portfolio.get_portfolio_summary()
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
                    'position': 'long' if portfolio.is_position_open(symbol) and portfolio.positions[symbol].side == 'long' else 
                               'short' if portfolio.is_position_open(symbol) and portfolio.positions[symbol].side == 'short' else 'none'
                })
                
            except Exception as e:
                logger.error(f"Error procesando {symbol} en período {i}: {e}")
                continue
        
        # Log progreso cada 50 períodos
        if i % 50 == 0:
            portfolio_summary = portfolio.get_portfolio_summary()
            logger.info(f"📊 Período {i}/{min_length} - Valor: ${portfolio_summary['total_value']:.2f} - PnL: ${portfolio_summary['total_pnl']:.2f}")
    
    # Guardar resultados
    if results:
        results_df = pd.DataFrame(results)
        results_df.to_csv('enhanced_multi_symbol_backtest_results.csv', index=False)
        logger.info("💾 Resultados guardados en enhanced_multi_symbol_backtest_results.csv")
        
        # Mostrar resumen final
        final_summary = portfolio.get_portfolio_summary()
        logger.info("=" * 50)
        logger.info("📈 RESUMEN FINAL DEL BACKTESTING")
        logger.info("=" * 50)
        logger.info(f"💰 Capital inicial: $500.00")
        logger.info(f"💰 Valor final: ${final_summary['total_value']:.2f}")
        logger.info(f"📈 PnL total: ${final_summary['total_pnl']:.2f}")
        logger.info(f"📊 Retorno: {final_summary['total_return']:.2f}%")
        logger.info(f"📉 Drawdown máximo: {final_summary['max_drawdown']:.2f}%")
        logger.info(f"🔄 Posiciones abiertas: {len(final_summary['open_positions'])}")
        
        # Estadísticas por símbolo
        for symbol in TRADING_SYMBOLS:
            symbol_results = results_df[results_df['symbol'] == symbol]
            if not symbol_results.empty:
                trades = len(symbol_results[symbol_results['position'] != 'none'])
                signals = len(symbol_results[symbol_results['signal'].abs() > 0.3])
                logger.info(f"📊 {symbol}: {trades} operaciones, {signals} señales fuertes")
    
    else:
        logger.error("❌ No se generaron resultados")

if __name__ == "__main__":
    run_enhanced_multi_symbol_backtest()