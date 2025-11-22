#!/usr/bin/env python3
"""
Sistema de Momentum Agresivo SICAR
Estrategias de momentum con alto apalancamiento y gestión de riesgo
Objetivo: 15% ROI mensual con apalancamiento
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import sys
import os
import warnings
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('aggressive_momentum_sicar_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.robust_data_fetcher import RobustDataFetcher

class AggressiveMomentumSicarSystem:
    def __init__(self, initial_capital=500, leverage=1.0):
        """
        Sistema de Momentum Agresivo SICAR
        
        Args:
            initial_capital: Capital inicial en USD
            leverage: Apalancamiento (8x para momentum agresivo)
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.leverage = leverage
        self.fee_rate = 0.001  # 0.1% por operación
        
        # Configuración de momentum
        self.momentum_periods = [3, 7, 14, 21]  # Períodos de momentum
        self.momentum_threshold = 0.02  # 2% momentum mínimo
        self.breakout_threshold = 0.015  # 1.5% breakout mínimo
        self.volume_multiplier = 1.5  # Volumen 1.5x promedio
        self.max_position_size = 0.4  # 40% del capital por posición
        
        # Gestión de riesgo agresiva
        self.stop_loss_pct = 0.03  # 3% stop loss
        self.take_profit_pct = 0.08  # 8% take profit
        self.trailing_stop_pct = 0.02  # 2% trailing stop
        self.max_positions = 3  # Máximo 3 posiciones simultáneas
        
        # Tracking
        self.operations = []
        self.positions = {}
        self.total_fees = 0
        self.momentum_signals = []
        self.breakout_signals = []
        
        logging.info(f"🚀 Sistema de Momentum Agresivo SICAR iniciado")
        logging.info(f"💰 Capital inicial: ${initial_capital}")
        logging.info(f"⚡ Apalancamiento: {leverage}x")
        logging.info(f"📈 Períodos momentum: {self.momentum_periods}")

    def calculate_momentum_indicators(self, data):
        """
        Calcula indicadores de momentum
        
        Args:
            data: DataFrame con datos OHLCV
            
        Returns:
            DataFrame: Datos con indicadores de momentum
        """
        df = data.copy()
        
        # Momentum básico
        for period in self.momentum_periods:
            df[f'momentum_{period}'] = (df['close'] / df['close'].shift(period) - 1) * 100
            df[f'roc_{period}'] = ((df['close'] - df['close'].shift(period)) / df['close'].shift(period)) * 100
        
        # RSI momentum
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi_momentum'] = df['rsi'].diff(3)  # Cambio en RSI
        
        # MACD momentum
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        df['macd_momentum'] = df['macd_histogram'].diff()
        
        # Stochastic momentum
        low_14 = df['low'].rolling(14).min()
        high_14 = df['high'].rolling(14).max()
        df['stoch_k'] = 100 * ((df['close'] - low_14) / (high_14 - low_14))
        df['stoch_d'] = df['stoch_k'].rolling(3).mean()
        df['stoch_momentum'] = df['stoch_k'] - df['stoch_d']
        
        # Williams %R momentum
        df['williams_r'] = -100 * ((high_14 - df['close']) / (high_14 - low_14))
        df['williams_momentum'] = df['williams_r'].diff(3)
        
        # Volume momentum
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        df['volume_momentum'] = df['volume_ratio'].diff(3)
        
        # Price momentum acceleration
        df['price_acceleration'] = df['momentum_7'].diff()
        df['momentum_strength'] = (df['momentum_3'] + df['momentum_7'] + df['momentum_14']) / 3
        
        # Volatility momentum
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(20).std()
        df['volatility_momentum'] = df['volatility'].diff(5)
        
        return df

    def detect_momentum_signals(self, data, idx):
        """
        Detecta señales de momentum
        
        Args:
            data: DataFrame con indicadores
            idx: Índice actual
            
        Returns:
            dict: Señales de momentum
        """
        if idx < 50:  # Necesitamos suficientes datos
            return {'signal': 'HOLD', 'strength': 0, 'confidence': 0}
        
        current = data.iloc[idx]
        prev = data.iloc[idx-1]
        
        signals = []
        strengths = []
        
        # 1. Momentum multi-período
        momentum_score = 0
        for period in self.momentum_periods:
            momentum = current[f'momentum_{period}']
            if momentum > self.momentum_threshold:
                momentum_score += 1
            elif momentum < -self.momentum_threshold:
                momentum_score -= 1
        
        if momentum_score >= 3:
            signals.append('BUY')
            strengths.append(abs(momentum_score) / len(self.momentum_periods))
        elif momentum_score <= -3:
            signals.append('SELL')
            strengths.append(abs(momentum_score) / len(self.momentum_periods))
        
        # 2. RSI momentum divergence
        if current['rsi'] > 70 and current['rsi_momentum'] > 5:
            signals.append('BUY')
            strengths.append(0.8)
        elif current['rsi'] < 30 and current['rsi_momentum'] < -5:
            signals.append('SELL')
            strengths.append(0.8)
        
        # 3. MACD momentum
        if (current['macd'] > current['macd_signal'] and 
            current['macd_momentum'] > 0 and 
            prev['macd'] <= prev['macd_signal']):
            signals.append('BUY')
            strengths.append(0.9)
        elif (current['macd'] < current['macd_signal'] and 
              current['macd_momentum'] < 0 and 
              prev['macd'] >= prev['macd_signal']):
            signals.append('SELL')
            strengths.append(0.9)
        
        # 4. Stochastic momentum
        if (current['stoch_k'] > current['stoch_d'] and 
            current['stoch_momentum'] > 5 and 
            current['stoch_k'] < 80):
            signals.append('BUY')
            strengths.append(0.7)
        elif (current['stoch_k'] < current['stoch_d'] and 
              current['stoch_momentum'] < -5 and 
              current['stoch_k'] > 20):
            signals.append('SELL')
            strengths.append(0.7)
        
        # 5. Volume momentum confirmation
        volume_confirmation = current['volume_ratio'] > self.volume_multiplier
        
        # 6. Price acceleration
        acceleration_signal = False
        if current['price_acceleration'] > 0.5:
            acceleration_signal = True
        
        # Determinar señal final
        if not signals:
            return {'signal': 'HOLD', 'strength': 0, 'confidence': 0}
        
        # Contar votos
        buy_votes = signals.count('BUY')
        sell_votes = signals.count('SELL')
        
        if buy_votes > sell_votes:
            final_signal = 'BUY'
            strength = np.mean([s for i, s in enumerate(strengths) if signals[i] == 'BUY'])
        elif sell_votes > buy_votes:
            final_signal = 'SELL'
            strength = np.mean([s for i, s in enumerate(strengths) if signals[i] == 'SELL'])
        else:
            final_signal = 'HOLD'
            strength = 0
        
        # Calcular confianza
        confidence = len(signals) / 5  # Máximo 5 señales
        
        # Bonus por confirmaciones
        if volume_confirmation:
            confidence += 0.1
        if acceleration_signal:
            confidence += 0.1
        
        confidence = min(confidence, 1.0)
        
        return {
            'signal': final_signal,
            'strength': strength,
            'confidence': confidence,
            'momentum_score': momentum_score,
            'volume_confirmation': volume_confirmation,
            'acceleration': acceleration_signal
        }

    def detect_breakout_signals(self, data, idx):
        """
        Detecta señales de breakout
        
        Args:
            data: DataFrame con datos
            idx: Índice actual
            
        Returns:
            dict: Señales de breakout
        """
        if idx < 20:
            return {'signal': 'HOLD', 'strength': 0}
        
        current = data.iloc[idx]
        
        # Resistance/Support levels
        high_20 = data['high'].iloc[idx-20:idx].max()
        low_20 = data['low'].iloc[idx-20:idx].min()
        
        # Breakout detection
        price_change = (current['close'] - current['open']) / current['open']
        
        # Upward breakout
        if (current['high'] > high_20 and 
            price_change > self.breakout_threshold and
            current['volume'] > current['volume_sma'] * self.volume_multiplier):
            return {'signal': 'BUY', 'strength': 0.9, 'confidence': 0.85, 'type': 'resistance_breakout'}
        
        # Downward breakout
        elif (current['low'] < low_20 and 
              price_change < -self.breakout_threshold and
              current['volume'] > current['volume_sma'] * self.volume_multiplier):
            return {'signal': 'SELL', 'strength': 0.9, 'confidence': 0.85, 'type': 'support_breakdown'}
        
        return {'signal': 'HOLD', 'strength': 0, 'confidence': 0}

    def calculate_position_size(self, signal_strength, confidence, current_price):
        """
        Calcula el tamaño de posición basado en la fuerza de la señal
        
        Args:
            signal_strength: Fuerza de la señal (0-1)
            confidence: Confianza de la señal (0-1)
            current_price: Precio actual
            
        Returns:
            float: Tamaño de posición en USD
        """
        # Tamaño base
        base_size = self.current_capital * self.max_position_size
        
        # Ajustar por fuerza y confianza
        strength_multiplier = signal_strength
        confidence_multiplier = confidence
        
        # Tamaño final
        position_size = base_size * strength_multiplier * confidence_multiplier * self.leverage
        
        # Limitar al capital disponible
        max_size = self.current_capital * self.leverage * 0.9
        
        return min(position_size, max_size)

    def execute_momentum_trade(self, signal_data, current_price, timestamp):
        """
        Ejecuta una operación basada en señales de momentum
        
        Args:
            signal_data: Datos de la señal
            current_price: Precio actual
            timestamp: Timestamp de la operación
        """
        if signal_data['signal'] == 'HOLD':
            return
        
        # Verificar límite de posiciones
        if len(self.positions) >= self.max_positions:
            return
        
        position_size = self.calculate_position_size(
            signal_data['strength'], 
            signal_data['confidence'], 
            current_price
        )
        
        if position_size < 100:  # Mínimo $100
            return
        
        # Ejecutar operación
        if signal_data['signal'] == 'BUY':
            self.execute_buy_order(current_price, position_size, signal_data, timestamp)
        elif signal_data['signal'] == 'SELL':
            self.execute_sell_order(current_price, position_size, signal_data, timestamp)

    def execute_buy_order(self, price, size, signal_data, timestamp):
        """Ejecuta una orden de compra"""
        quantity = size / price
        fee = size * self.fee_rate
        
        # Actualizar capital
        self.current_capital -= (size + fee)
        self.total_fees += fee
        
        # Registrar posición
        position_id = f"LONG_{timestamp}"
        self.positions[position_id] = {
            'type': 'LONG',
            'entry_price': price,
            'quantity': quantity,
            'size': size,
            'timestamp': timestamp,
            'signal_data': signal_data,
            'stop_loss': price * (1 - self.stop_loss_pct),
            'take_profit': price * (1 + self.take_profit_pct),
            'trailing_stop': price * (1 - self.trailing_stop_pct),
            'highest_price': price
        }
        
        # Registrar operación
        operation = {
            'timestamp': timestamp,
            'type': 'BUY_MOMENTUM',
            'price': price,
            'quantity': quantity,
            'size': size,
            'fee': fee,
            'signal_strength': signal_data['strength'],
            'confidence': signal_data['confidence'],
            'capital_after': self.current_capital,
            'position_id': position_id
        }
        
        self.operations.append(operation)
        
        logging.info(f"📈 MOMENTUM BUY: ${size:.2f} @ ${price:.2f} | Strength: {signal_data['strength']:.3f}")

    def execute_sell_order(self, price, size, signal_data, timestamp):
        """Ejecuta una orden de venta"""
        quantity = size / price
        fee = size * self.fee_rate
        
        # Actualizar capital
        self.current_capital -= (size + fee)
        self.total_fees += fee
        
        # Registrar posición
        position_id = f"SHORT_{timestamp}"
        self.positions[position_id] = {
            'type': 'SHORT',
            'entry_price': price,
            'quantity': quantity,
            'size': size,
            'timestamp': timestamp,
            'signal_data': signal_data,
            'stop_loss': price * (1 + self.stop_loss_pct),
            'take_profit': price * (1 - self.take_profit_pct),
            'trailing_stop': price * (1 + self.trailing_stop_pct),
            'lowest_price': price
        }
        
        # Registrar operación
        operation = {
            'timestamp': timestamp,
            'type': 'SELL_MOMENTUM',
            'price': price,
            'quantity': quantity,
            'size': size,
            'fee': fee,
            'signal_strength': signal_data['strength'],
            'confidence': signal_data['confidence'],
            'capital_after': self.current_capital,
            'position_id': position_id
        }
        
        self.operations.append(operation)
        
        logging.info(f"📉 MOMENTUM SELL: ${size:.2f} @ ${price:.2f} | Strength: {signal_data['strength']:.3f}")

    def manage_positions(self, current_price, timestamp):
        """Gestiona posiciones abiertas con stop loss, take profit y trailing stop"""
        positions_to_close = []
        
        for position_id, position in self.positions.items():
            # Calcular PnL actual
            if position['type'] == 'LONG':
                pnl_pct = (current_price - position['entry_price']) / position['entry_price']
                
                # Actualizar trailing stop
                if current_price > position['highest_price']:
                    position['highest_price'] = current_price
                    position['trailing_stop'] = current_price * (1 - self.trailing_stop_pct)
                
                # Verificar condiciones de cierre
                if current_price <= position['stop_loss']:
                    positions_to_close.append((position_id, "stop_loss"))
                elif current_price >= position['take_profit']:
                    positions_to_close.append((position_id, "take_profit"))
                elif current_price <= position['trailing_stop']:
                    positions_to_close.append((position_id, "trailing_stop"))
                    
            else:  # SHORT
                pnl_pct = (position['entry_price'] - current_price) / position['entry_price']
                
                # Actualizar trailing stop
                if current_price < position['lowest_price']:
                    position['lowest_price'] = current_price
                    position['trailing_stop'] = current_price * (1 + self.trailing_stop_pct)
                
                # Verificar condiciones de cierre
                if current_price >= position['stop_loss']:
                    positions_to_close.append((position_id, "stop_loss"))
                elif current_price <= position['take_profit']:
                    positions_to_close.append((position_id, "take_profit"))
                elif current_price >= position['trailing_stop']:
                    positions_to_close.append((position_id, "trailing_stop"))
        
        # Cerrar posiciones
        for position_id, reason in positions_to_close:
            self.close_position(position_id, current_price, timestamp, reason)

    def close_position(self, position_id, current_price, timestamp, reason="signal"):
        """Cierra una posición abierta"""
        if position_id not in self.positions:
            return
        
        position = self.positions[position_id]
        
        # Calcular PnL
        if position['type'] == 'LONG':
            pnl = (current_price - position['entry_price']) * position['quantity']
        else:  # SHORT
            pnl = (position['entry_price'] - current_price) * position['quantity']
        
        # Fees de cierre
        close_size = position['quantity'] * current_price
        close_fee = close_size * self.fee_rate
        
        # PnL neto
        net_pnl = pnl - close_fee
        
        # Actualizar capital
        self.current_capital += (position['size'] + net_pnl)
        self.total_fees += close_fee
        
        # Registrar cierre
        operation = {
            'timestamp': timestamp,
            'type': f"CLOSE_{position['type']}",
            'price': current_price,
            'quantity': position['quantity'],
            'size': close_size,
            'fee': close_fee,
            'pnl': net_pnl,
            'capital_after': self.current_capital,
            'position_id': position_id,
            'reason': reason
        }
        
        self.operations.append(operation)
        
        # Eliminar posición
        del self.positions[position_id]
        
        logging.info(f"🔚 CLOSE {position['type']}: PnL ${net_pnl:.2f} | Reason: {reason}")

    def run_backtest(self, symbol='BTCUSDT', days=60):
        """
        Ejecuta backtest del sistema de momentum agresivo
        
        Args:
            symbol: Par de trading
            days: Días de backtest
        """
        logging.info(f"🔄 Iniciando backtest de Momentum Agresivo para {symbol}")
        
        # Obtener datos
        fetcher = RobustDataFetcher()
        data = fetcher.get_market_data(symbol, '15m', limit=days*24*4)  # 15 minutos para más señales
        
        if data is None or data.empty:
            logging.error(f"❌ No se pudieron obtener datos para {symbol}")
            return
        
        # Normalizar datos
        data.columns = data.columns.str.lower()
        if data.index.name == 'timestamp' or 'timestamp' in str(data.index.name).lower():
            data.reset_index(inplace=True)
        
        logging.info(f"📊 Datos obtenidos: {len(data)} velas de 15m")
        
        # Calcular indicadores de momentum
        data_with_indicators = self.calculate_momentum_indicators(data)
        
        # Backtest
        logging.info("🔄 Iniciando backtest con señales de momentum...")
        
        for idx in range(50, len(data_with_indicators)):
            current_price = data_with_indicators['close'].iloc[idx]
            timestamp = data_with_indicators.get('timestamp', pd.Series([idx])).iloc[idx]
            
            # Detectar señales de momentum
            momentum_signal = self.detect_momentum_signals(data_with_indicators, idx)
            breakout_signal = self.detect_breakout_signals(data_with_indicators, idx)
            
            # Registrar señales
            self.momentum_signals.append({
                'timestamp': timestamp,
                'momentum_signal': momentum_signal,
                'breakout_signal': breakout_signal,
                'price': current_price
            })
            
            # Combinar señales
            if momentum_signal['signal'] != 'HOLD' and momentum_signal['confidence'] > 0.6:
                self.execute_momentum_trade(momentum_signal, current_price, timestamp)
            elif breakout_signal['signal'] != 'HOLD' and breakout_signal['strength'] > 0.8:
                self.execute_momentum_trade(breakout_signal, current_price, timestamp)
            
            # Gestionar posiciones
            self.manage_positions(current_price, timestamp)
        
        # Cerrar todas las posiciones al final
        final_price = data_with_indicators['close'].iloc[-1]
        for position_id in list(self.positions.keys()):
            self.close_position(position_id, final_price, data.index[-1], "backtest_end")
        
        # Calcular métricas finales
        self.calculate_final_metrics(days)

    def calculate_final_metrics(self, days):
        """Calcula métricas finales del backtest"""
        if not self.operations:
            logging.warning("⚠️ No se generaron operaciones de momentum")
            return
        
        # Métricas básicas
        total_operations = len(self.operations)
        buy_ops = len([op for op in self.operations if 'BUY' in op['type']])
        sell_ops = len([op for op in self.operations if 'SELL' in op['type']])
        close_ops = len([op for op in self.operations if 'CLOSE' in op['type']])
        
        # Calcular win rate
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
        
        # Fuerza promedio de señales
        momentum_ops = [op for op in self.operations if 'signal_strength' in op]
        avg_signal_strength = np.mean([op['signal_strength'] for op in momentum_ops]) if momentum_ops else 0
        
        # Logging de resultados
        logging.info("=" * 80)
        logging.info("RESULTADOS SISTEMA DE MOMENTUM AGRESIVO SICAR")
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
        logging.info(f"💪 Fuerza promedio señales: {avg_signal_strength:.3f}")
        logging.info(f"📅 Duración: {days} días ({months:.1f} meses)")
        logging.info(f"⚡ Apalancamiento: {self.leverage}x")
        logging.info(f"⚡ Gap al objetivo: {roi_gap:.2f}% (Objetivo: {target_roi}%)")
        logging.info("=" * 80)
        
        # Guardar resultados
        self.save_results()
        
        # Resumen final
        print(f"\n✅ Backtest de Momentum Agresivo completado!")
        print(f"📊 ROI mensual: {monthly_roi:.2f}%")
        print(f"🎯 Objetivo: {target_roi}%")
        print(f"🔄 Total operaciones: {total_operations}")
        print(f"🏆 Win rate: {win_rate:.1f}%")
        print(f"💪 Fuerza promedio señales: {avg_signal_strength:.3f}")
        print(f"⚡ Apalancamiento: {self.leverage}x")
        print(f"📁 Resultados guardados en: aggressive_momentum_sicar_results.csv")

    def save_results(self):
        """Guarda los resultados en CSV"""
        if self.operations:
            df = pd.DataFrame(self.operations)
            df.to_csv('aggressive_momentum_sicar_results.csv', index=False)
            logging.info("💾 Resultados guardados en aggressive_momentum_sicar_results.csv")
        
        if self.momentum_signals:
            signals_df = pd.DataFrame(self.momentum_signals)
            signals_df.to_csv('momentum_signals_log.csv', index=False)
            logging.info("💾 Log de señales guardado en momentum_signals_log.csv")

def main():
    """Función principal"""
    try:
        # Crear y ejecutar sistema de momentum agresivo
        system = AggressiveMomentumSicarSystem(
            initial_capital=500,
            leverage=8.0  # Apalancamiento muy agresivo
        )
        
        # Ejecutar backtest
        system.run_backtest(symbol='BTCUSDT', days=60)
        
    except Exception as e:
        logging.error(f"❌ Error en sistema de momentum: {str(e)}")
        raise

if __name__ == "__main__":
    main()