#!/usr/bin/env python3
"""
Sistema Ensemble SICAR - Combinando los Mejores Elementos
Integra multi-pair, arbitraje, market making, ML y momentum agresivo
Objetivo: 15% ROI mensual con apalancamiento optimizado
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import sys
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ensemble_sicar_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.robust_data_fetcher import RobustDataFetcher

class EnsembleSicarSystem:
    def __init__(self, initial_capital=500, leverage=1.0):
        """
        Sistema Ensemble SICAR - Combinando mejores estrategias
        
        Args:
            initial_capital: Capital inicial en USD
            leverage: Sin apalancamiento (1.0x para trading conservador)
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.leverage = leverage
        self.fee_rate = 0.001  # 0.1% por operación
        
        # Configuración de estrategias
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT']  # Multi-pair
        self.timeframes = ['15m', '1h']  # Multi-timeframe
        self.max_positions = 5  # Máximo 5 posiciones simultáneas
        self.position_size_pct = 0.3  # 30% del capital por posición
        
        # Pesos de estrategias (basado en performance histórica)
        self.strategy_weights = {
            'market_making': 0.35,    # Mejor performer (10.52% ROI)
            'momentum': 0.25,         # Segundo mejor (4.74% ROI)
            'multi_pair': 0.20,       # Tercero (3.63% ROI)
            'arbitrage': 0.15,        # Cuarto (1.86% ROI)
            'ml_signals': 0.05        # Quinto (-11.09% ROI, peso mínimo)
        }
        
        # Configuración de market making
        self.mm_spread_base = 0.002  # 0.2% spread base
        self.mm_inventory_target = 0.5  # 50% target inventory
        
        # Configuración de momentum
        self.momentum_threshold = 0.015  # 1.5% momentum mínimo
        self.momentum_periods = [7, 14, 21]
        
        # Configuración de arbitraje
        self.arbitrage_threshold = 0.001  # 0.1% diferencia mínima
        
        # ML Configuration
        self.ml_model = RandomForestClassifier(n_estimators=50, random_state=42)
        self.scaler = StandardScaler()
        self.ml_trained = False
        
        # Tracking
        self.operations = []
        self.positions = {}
        self.total_fees = 0
        self.strategy_performance = {strategy: {'trades': 0, 'pnl': 0} for strategy in self.strategy_weights.keys()}
        self.strategy_performance['ensemble'] = {'trades': 0, 'pnl': 0}  # Agregar ensemble
        
        logging.info(f"🚀 Sistema Ensemble SICAR iniciado")
        logging.info(f"💰 Capital inicial: ${initial_capital}")
        logging.info(f"⚡ Apalancamiento: {leverage}x")
        logging.info(f"🎯 Estrategias: {list(self.strategy_weights.keys())}")
        logging.info(f"📊 Pesos: {self.strategy_weights}")

    def calculate_technical_indicators(self, data):
        """Calcula indicadores técnicos completos"""
        df = data.copy()
        
        # Precios básicos
        df['returns'] = df['close'].pct_change()
        df['high_low_ratio'] = df['high'] / df['low']
        df['volume_change'] = df['volume'].pct_change()
        
        # Medias móviles
        for period in [5, 10, 20, 50]:
            df[f'sma_{period}'] = df['close'].rolling(period).mean()
            df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
        
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
        df['bb_middle'] = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Momentum indicators
        for period in self.momentum_periods:
            df[f'momentum_{period}'] = (df['close'] / df['close'].shift(period) - 1) * 100
        
        # Volatilidad
        df['volatility'] = df['returns'].rolling(20).std()
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        return df

    def market_making_signal(self, data, idx):
        """Señal de market making"""
        if idx < 20:
            return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'market_making'}
        
        current = data.iloc[idx]
        
        # Calcular volatilidad
        volatility = data['volatility'].iloc[idx]
        if pd.isna(volatility) or volatility == 0:
            return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'market_making'}
        
        # Spread dinámico basado en volatilidad
        dynamic_spread = self.mm_spread_base * (1 + volatility * 10)
        
        # Señal basada en posición en Bollinger Bands
        bb_position = current['bb_position']
        
        if bb_position < 0.3:  # Cerca del límite inferior
            return {
                'signal': 'BUY',
                'confidence': 0.8,
                'strategy': 'market_making',
                'spread': dynamic_spread,
                'reason': 'bb_lower'
            }
        elif bb_position > 0.7:  # Cerca del límite superior
            return {
                'signal': 'SELL',
                'confidence': 0.8,
                'strategy': 'market_making',
                'spread': dynamic_spread,
                'reason': 'bb_upper'
            }
        
        return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'market_making'}

    def momentum_signal(self, data, idx):
        """Señal de momentum"""
        if idx < 30:
            return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'momentum'}
        
        current = data.iloc[idx]
        
        # Calcular momentum score
        momentum_score = 0
        momentum_values = []
        
        for period in self.momentum_periods:
            momentum = current[f'momentum_{period}']
            if not pd.isna(momentum):
                momentum_values.append(momentum)
                if momentum > self.momentum_threshold:
                    momentum_score += 1
                elif momentum < -self.momentum_threshold:
                    momentum_score -= 1
        
        # RSI confirmation
        rsi = current['rsi']
        rsi_signal = 0
        if rsi < 30:
            rsi_signal = 1
        elif rsi > 70:
            rsi_signal = -1
        
        # MACD confirmation
        macd_signal = 0
        if current['macd'] > current['macd_signal'] and current['macd_histogram'] > 0:
            macd_signal = 1
        elif current['macd'] < current['macd_signal'] and current['macd_histogram'] < 0:
            macd_signal = -1
        
        # Volume confirmation
        volume_confirmation = current['volume_ratio'] > 1.2
        
        # Señal final
        total_score = momentum_score + rsi_signal + macd_signal
        
        if total_score >= 2 and volume_confirmation:
            confidence = min(0.9, abs(np.mean(momentum_values)) / 5.0) if momentum_values else 0.5
            return {
                'signal': 'BUY',
                'confidence': confidence,
                'strategy': 'momentum',
                'momentum_score': momentum_score,
                'total_score': total_score
            }
        elif total_score <= -2 and volume_confirmation:
            confidence = min(0.9, abs(np.mean(momentum_values)) / 5.0) if momentum_values else 0.5
            return {
                'signal': 'SELL',
                'confidence': confidence,
                'strategy': 'momentum',
                'momentum_score': momentum_score,
                'total_score': total_score
            }
        
        return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'momentum'}

    def arbitrage_signal(self, data, idx):
        """Señal de arbitraje simulado"""
        if idx < 5:
            return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'arbitrage'}
        
        current = data.iloc[idx]
        prev = data.iloc[idx-1]
        
        # Simular diferencia de precios entre exchanges
        price_diff = np.random.normal(0, 0.002)  # Diferencia simulada
        
        if abs(price_diff) > self.arbitrage_threshold:
            signal = 'BUY' if price_diff > 0 else 'SELL'
            confidence = min(0.95, abs(price_diff) / 0.005)
            
            return {
                'signal': signal,
                'confidence': confidence,
                'strategy': 'arbitrage',
                'price_diff': price_diff
            }
        
        return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'arbitrage'}

    def ml_signal(self, data, idx):
        """Señal de machine learning"""
        if not self.ml_trained or idx < 50:
            return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'ml_signals'}
        
        # Preparar features
        feature_cols = ['rsi', 'macd', 'bb_position', 'volume_ratio', 'volatility']
        features = []
        
        for col in feature_cols:
            value = data[col].iloc[idx]
            if pd.isna(value):
                return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'ml_signals'}
            features.append(value)
        
        try:
            # Predecir
            features_scaled = self.scaler.transform([features])
            prediction = self.ml_model.predict(features_scaled)[0]
            probabilities = self.ml_model.predict_proba(features_scaled)[0]
            confidence = np.max(probabilities)
            
            if prediction == 2 and confidence > 0.6:  # Compra
                return {
                    'signal': 'BUY',
                    'confidence': confidence,
                    'strategy': 'ml_signals',
                    'prediction': prediction
                }
            elif prediction == 0 and confidence > 0.6:  # Venta
                return {
                    'signal': 'SELL',
                    'confidence': confidence,
                    'strategy': 'ml_signals',
                    'prediction': prediction
                }
        except Exception as e:
            logging.warning(f"Error en ML signal: {e}")
        
        return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'ml_signals'}

    def train_ml_model(self, data):
        """Entrena el modelo de ML"""
        if len(data) < 100:
            return
        
        try:
            # Preparar features
            feature_cols = ['rsi', 'macd', 'bb_position', 'volume_ratio', 'volatility']
            X = data[feature_cols].dropna()
            
            # Crear target (movimiento futuro)
            future_returns = data['close'].shift(-5) / data['close'] - 1
            conditions = [future_returns <= -0.01, future_returns >= 0.01]
            y = np.select(conditions, [0, 2], default=1)
            y = pd.Series(y, index=data.index)
            
            # Alinear X e y
            common_idx = X.index.intersection(y.index)
            X = X.loc[common_idx]
            y = y.loc[common_idx]
            
            if len(X) < 50:
                return
            
            # Entrenar
            X_scaled = self.scaler.fit_transform(X)
            self.ml_model.fit(X_scaled, y)
            self.ml_trained = True
            
            logging.info("🧠 Modelo ML entrenado exitosamente")
            
        except Exception as e:
            logging.warning(f"Error entrenando ML: {e}")

    def ensemble_decision(self, signals):
        """Toma decisión ensemble basada en múltiples señales"""
        if not signals:
            return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'ensemble'}
        
        # Calcular votos ponderados
        buy_weight = 0
        sell_weight = 0
        total_confidence = 0
        
        for signal in signals:
            if signal['signal'] == 'HOLD':
                continue
                
            strategy = signal['strategy']
            weight = self.strategy_weights.get(strategy, 0.1)
            confidence = signal['confidence']
            
            weighted_confidence = weight * confidence
            total_confidence += weighted_confidence
            
            if signal['signal'] == 'BUY':
                buy_weight += weighted_confidence
            elif signal['signal'] == 'SELL':
                sell_weight += weighted_confidence
        
        # Decisión final
        if buy_weight > sell_weight and buy_weight > 0.3:
            return {
                'signal': 'BUY',
                'confidence': min(buy_weight, 0.95),
                'strategy': 'ensemble',
                'buy_weight': buy_weight,
                'sell_weight': sell_weight
            }
        elif sell_weight > buy_weight and sell_weight > 0.3:
            return {
                'signal': 'SELL',
                'confidence': min(sell_weight, 0.95),
                'strategy': 'ensemble',
                'buy_weight': buy_weight,
                'sell_weight': sell_weight
            }
        
        return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'ensemble'}

    def calculate_position_size(self, signal_data, current_price):
        """Calcula tamaño de posición optimizado"""
        base_size = self.current_capital * self.position_size_pct
        
        # Ajustar por confianza
        confidence_multiplier = signal_data['confidence']
        
        # Ajustar por estrategia
        strategy_multiplier = self.strategy_weights.get(signal_data['strategy'], 0.1)
        
        # Tamaño final con apalancamiento
        position_size = base_size * confidence_multiplier * strategy_multiplier * self.leverage
        
        # Limitar
        max_size = self.current_capital * self.leverage * 0.8
        return min(position_size, max_size)

    def execute_trade(self, signal_data, current_price, timestamp, symbol):
        """Ejecuta una operación"""
        if signal_data['signal'] == 'HOLD':
            return
        
        if len(self.positions) >= self.max_positions:
            return
        
        position_size = self.calculate_position_size(signal_data, current_price)
        
        if position_size < 50:  # Mínimo $50
            return
        
        quantity = position_size / current_price
        fee = position_size * self.fee_rate
        
        # Actualizar capital
        self.current_capital -= (position_size + fee)
        self.total_fees += fee
        
        # Crear posición
        position_id = f"{signal_data['signal']}_{symbol}_{timestamp}"
        position = {
            'type': signal_data['signal'],
            'symbol': symbol,
            'entry_price': current_price,
            'quantity': quantity,
            'size': position_size,
            'timestamp': timestamp,
            'strategy': signal_data['strategy'],
            'confidence': signal_data['confidence'],
            'stop_loss': current_price * (0.97 if signal_data['signal'] == 'BUY' else 1.03),
            'take_profit': current_price * (1.06 if signal_data['signal'] == 'BUY' else 0.94)
        }
        
        self.positions[position_id] = position
        
        # Registrar operación
        operation = {
            'timestamp': timestamp,
            'symbol': symbol,
            'type': f"{signal_data['signal']}_ENSEMBLE",
            'price': current_price,
            'quantity': quantity,
            'size': position_size,
            'fee': fee,
            'strategy': signal_data['strategy'],
            'confidence': signal_data['confidence'],
            'capital_after': self.current_capital,
            'position_id': position_id
        }
        
        self.operations.append(operation)
        
        # Actualizar performance de estrategia
        self.strategy_performance[signal_data['strategy']]['trades'] += 1
        
        logging.info(f"📊 ENSEMBLE {signal_data['signal']}: {symbol} ${position_size:.2f} @ ${current_price:.2f} | Strategy: {signal_data['strategy']} | Conf: {signal_data['confidence']:.3f}")

    def manage_positions(self, current_prices, timestamp):
        """Gestiona posiciones abiertas"""
        positions_to_close = []
        
        for position_id, position in self.positions.items():
            symbol = position['symbol']
            current_price = current_prices.get(symbol, position['entry_price'])
            
            # Calcular PnL
            if position['type'] == 'BUY':
                pnl_pct = (current_price - position['entry_price']) / position['entry_price']
            else:  # SELL
                pnl_pct = (position['entry_price'] - current_price) / position['entry_price']
            
            # Stop loss
            if ((position['type'] == 'BUY' and current_price <= position['stop_loss']) or
                (position['type'] == 'SELL' and current_price >= position['stop_loss'])):
                positions_to_close.append((position_id, current_price, "stop_loss"))
            
            # Take profit
            elif ((position['type'] == 'BUY' and current_price >= position['take_profit']) or
                  (position['type'] == 'SELL' and current_price <= position['take_profit'])):
                positions_to_close.append((position_id, current_price, "take_profit"))
        
        # Cerrar posiciones
        for position_id, price, reason in positions_to_close:
            self.close_position(position_id, price, timestamp, reason)

    def close_position(self, position_id, current_price, timestamp, reason="signal"):
        """Cierra una posición"""
        if position_id not in self.positions:
            return
        
        position = self.positions[position_id]
        
        # Calcular PnL
        if position['type'] == 'BUY':
            pnl = (current_price - position['entry_price']) * position['quantity']
        else:  # SELL
            pnl = (position['entry_price'] - current_price) * position['quantity']
        
        # Fees de cierre
        close_size = position['quantity'] * current_price
        close_fee = close_size * self.fee_rate
        net_pnl = pnl - close_fee
        
        # Actualizar capital
        self.current_capital += (position['size'] + net_pnl)
        self.total_fees += close_fee
        
        # Actualizar performance de estrategia
        self.strategy_performance[position['strategy']]['pnl'] += net_pnl
        
        # Registrar cierre
        operation = {
            'timestamp': timestamp,
            'symbol': position['symbol'],
            'type': f"CLOSE_{position['type']}",
            'price': current_price,
            'quantity': position['quantity'],
            'size': close_size,
            'fee': close_fee,
            'pnl': net_pnl,
            'capital_after': self.current_capital,
            'position_id': position_id,
            'strategy': position['strategy'],
            'reason': reason
        }
        
        self.operations.append(operation)
        
        # Eliminar posición
        del self.positions[position_id]
        
        logging.info(f"🔚 CLOSE {position['type']}: {position['symbol']} PnL ${net_pnl:.2f} | Strategy: {position['strategy']} | Reason: {reason}")

    def run_backtest(self, days=60):
        """Ejecuta backtest del sistema ensemble"""
        logging.info(f"🔄 Iniciando backtest Ensemble para {len(self.symbols)} símbolos")
        
        # Obtener datos para todos los símbolos
        all_data = {}
        fetcher = RobustDataFetcher()
        
        for symbol in self.symbols:
            data = fetcher.get_market_data(symbol, '15m', limit=days*24*4)
            if data is not None and not data.empty:
                data.columns = data.columns.str.lower()
                if data.index.name == 'timestamp' or 'timestamp' in str(data.index.name).lower():
                    data.reset_index(inplace=True)
                
                # Calcular indicadores
                data_with_indicators = self.calculate_technical_indicators(data)
                all_data[symbol] = data_with_indicators
                
                logging.info(f"📊 {symbol}: {len(data)} velas obtenidas")
        
        if not all_data:
            logging.error("❌ No se pudieron obtener datos")
            return
        
        # Entrenar modelo ML con el primer símbolo
        first_symbol = list(all_data.keys())[0]
        self.train_ml_model(all_data[first_symbol])
        
        # Determinar longitud mínima
        min_length = min(len(data) for data in all_data.values())
        
        logging.info("🔄 Iniciando backtest ensemble...")
        
        # Backtest
        for idx in range(50, min_length):
            current_prices = {}
            
            # Obtener precios actuales
            for symbol, data in all_data.items():
                current_prices[symbol] = data['close'].iloc[idx]
            
            timestamp = all_data[first_symbol].get('timestamp', pd.Series([idx])).iloc[idx]
            
            # Generar señales para cada símbolo
            for symbol, data in all_data.items():
                current_price = current_prices[symbol]
                
                # Obtener señales de todas las estrategias
                signals = []
                
                # Market Making
                mm_signal = self.market_making_signal(data, idx)
                if mm_signal['signal'] != 'HOLD':
                    signals.append(mm_signal)
                
                # Momentum
                momentum_signal = self.momentum_signal(data, idx)
                if momentum_signal['signal'] != 'HOLD':
                    signals.append(momentum_signal)
                
                # Arbitraje
                arb_signal = self.arbitrage_signal(data, idx)
                if arb_signal['signal'] != 'HOLD':
                    signals.append(arb_signal)
                
                # ML
                ml_signal = self.ml_signal(data, idx)
                if ml_signal['signal'] != 'HOLD':
                    signals.append(ml_signal)
                
                # Decisión ensemble
                ensemble_signal = self.ensemble_decision(signals)
                
                # Ejecutar trade
                self.execute_trade(ensemble_signal, current_price, timestamp, symbol)
            
            # Gestionar posiciones
            self.manage_positions(current_prices, timestamp)
        
        # Cerrar todas las posiciones al final
        final_prices = {symbol: data['close'].iloc[-1] for symbol, data in all_data.items()}
        for position_id in list(self.positions.keys()):
            position = self.positions[position_id]
            final_price = final_prices[position['symbol']]
            self.close_position(position_id, final_price, min_length-1, "backtest_end")
        
        # Calcular métricas finales
        self.calculate_final_metrics(days)

    def calculate_final_metrics(self, days):
        """Calcula métricas finales del backtest"""
        if not self.operations:
            logging.warning("⚠️ No se generaron operaciones ensemble")
            return
        
        # Métricas básicas
        total_operations = len(self.operations)
        buy_ops = len([op for op in self.operations if 'BUY' in op['type']])
        sell_ops = len([op for op in self.operations if 'SELL' in op['type']])
        close_ops = len([op for op in self.operations if 'CLOSE' in op['type']])
        
        # Win rate
        close_operations = [op for op in self.operations if 'CLOSE' in op['type'] and 'pnl' in op]
        winning_ops = len([op for op in close_operations if op['pnl'] > 0])
        win_rate = (winning_ops / len(close_operations)) * 100 if close_operations else 0
        
        # Retornos
        net_pnl = self.current_capital - self.initial_capital
        net_return = (net_pnl / self.initial_capital) * 100
        
        # ROI mensual
        months = days / 30.44
        monthly_roi = (((self.current_capital / self.initial_capital) ** (1/months)) - 1) * 100
        
        # Gap al objetivo
        target_roi = 15.0
        roi_gap = target_roi - monthly_roi
        
        # Performance por estrategia
        strategy_stats = {}
        for strategy, perf in self.strategy_performance.items():
            if perf['trades'] > 0:
                avg_pnl = perf['pnl'] / perf['trades']
                strategy_stats[strategy] = {
                    'trades': perf['trades'],
                    'total_pnl': perf['pnl'],
                    'avg_pnl': avg_pnl
                }
        
        # Logging de resultados
        logging.info("=" * 80)
        logging.info("RESULTADOS SISTEMA ENSEMBLE SICAR")
        logging.info("=" * 80)
        logging.info(f"💰 Capital inicial: ${self.initial_capital:.2f}")
        logging.info(f"💰 Capital final: ${self.current_capital:.2f}")
        logging.info(f"💸 Fees totales: ${self.total_fees:.2f}")
        logging.info(f"💵 PnL neto: ${net_pnl:.2f}")
        logging.info(f"📊 Retorno neto: {net_return:.2f}%")
        logging.info(f"🎯 ROI mensual: {monthly_roi:.2f}%")
        logging.info(f"🔄 Total operaciones: {total_operations}")
        logging.info(f"📈 Operaciones de compra: {buy_ops}")
        logging.info(f"📉 Operaciones de venta: {sell_ops}")
        logging.info(f"🔚 Operaciones cerradas: {close_ops}")
        logging.info(f"🏆 Win rate: {win_rate:.1f}%")
        logging.info(f"📅 Duración: {days} días ({months:.1f} meses)")
        logging.info(f"⚡ Apalancamiento: {self.leverage}x")
        logging.info(f"⚡ Gap al objetivo: {roi_gap:.2f}% (Objetivo: {target_roi}%)")
        
        # Performance por estrategia
        logging.info("\n📊 PERFORMANCE POR ESTRATEGIA:")
        for strategy, stats in strategy_stats.items():
            logging.info(f"  {strategy}: {stats['trades']} trades, PnL total: ${stats['total_pnl']:.2f}, PnL promedio: ${stats['avg_pnl']:.2f}")
        
        logging.info("=" * 80)
        
        # Guardar resultados
        self.save_results()
        
        # Resumen final
        print(f"\n✅ Backtest Ensemble completado!")
        print(f"📊 ROI mensual: {monthly_roi:.2f}%")
        print(f"🎯 Objetivo: {target_roi}%")
        print(f"🔄 Total operaciones: {total_operations}")
        print(f"🏆 Win rate: {win_rate:.1f}%")
        print(f"⚡ Apalancamiento: {self.leverage}x")
        print(f"📁 Resultados guardados en: ensemble_sicar_results.csv")

    def save_results(self):
        """Guarda los resultados en CSV"""
        if self.operations:
            df = pd.DataFrame(self.operations)
            df.to_csv('ensemble_sicar_results.csv', index=False)
            logging.info("💾 Resultados guardados en ensemble_sicar_results.csv")

def main():
    """Función principal"""
    try:
        # Crear y ejecutar sistema ensemble
        system = EnsembleSicarSystem(
            initial_capital=500,
            leverage=1.0  # Sin apalancamiento
        )
        
        # Ejecutar backtest
        system.run_backtest(days=60)
        
    except Exception as e:
        logging.error(f"❌ Error en sistema ensemble: {str(e)}")
        raise

if __name__ == "__main__":
    main()