#!/usr/bin/env python3
"""
Sistema de Machine Learning SICAR - Predicción de Señales Avanzadas
Utiliza algoritmos de ML para predecir movimientos de precios
Objetivo: 15% ROI mensual con apalancamiento
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import sys
import os
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import warnings
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ml_signals_sicar_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.robust_data_fetcher import RobustDataFetcher

class MLSignalsSicarSystem:
    def __init__(self, initial_capital=500, leverage=1.0):
        """
        Sistema de ML para Señales SICAR
        
        Args:
            initial_capital: Capital inicial en USD
            leverage: Apalancamiento (6x para ML agresivo)
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.leverage = leverage
        self.fee_rate = 0.001  # 0.1% por operación
        
        # Configuración de ML
        self.lookback_period = 50  # Períodos para features
        self.prediction_horizon = 4  # Predecir 4 períodos adelante
        self.confidence_threshold = 0.45  # 45% confianza mínima (más agresivo)
        self.max_position_size = 0.35  # 35% del capital por posición
        
        # Modelos de ML
        self.models = {
            'rf': RandomForestClassifier(n_estimators=100, random_state=42),
            'gb': GradientBoostingClassifier(n_estimators=100, random_state=42),
            'lr': LogisticRegression(random_state=42, max_iter=1000)
        }
        self.scaler = StandardScaler()
        self.trained_models = {}
        
        # Tracking
        self.operations = []
        self.positions = {}
        self.total_fees = 0
        self.predictions_log = []
        
        logging.info(f"🚀 Sistema de ML Señales SICAR iniciado")
        logging.info(f"💰 Capital inicial: ${initial_capital}")
        logging.info(f"⚡ Apalancamiento: {leverage}x")
        logging.info(f"🧠 Modelos: {list(self.models.keys())}")

    def create_technical_features(self, data):
        """
        Crea features técnicos para el modelo de ML
        
        Args:
            data: DataFrame con datos OHLCV
            
        Returns:
            DataFrame: Features técnicos
        """
        df = data.copy()
        
        # Precios básicos
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        df['price_change'] = df['close'] - df['open']
        df['high_low_ratio'] = df['high'] / df['low']
        df['volume_change'] = df['volume'].pct_change()
        
        # Medias móviles
        for period in [5, 10, 20, 50]:
            df[f'sma_{period}'] = df['close'].rolling(period).mean()
            df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
            df[f'price_sma_{period}_ratio'] = df['close'] / df[f'sma_{period}']
        
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
        
        # Volatilidad
        df['volatility'] = df['returns'].rolling(20).std()
        df['volatility_ratio'] = df['volatility'] / df['volatility'].rolling(50).mean()
        
        # Volume features
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        df['price_volume'] = df['close'] * df['volume']
        
        # Momentum features
        for period in [3, 7, 14]:
            df[f'momentum_{period}'] = df['close'] / df['close'].shift(period) - 1
            df[f'roc_{period}'] = ((df['close'] - df['close'].shift(period)) / df['close'].shift(period)) * 100
        
        # Support/Resistance levels
        df['high_20'] = df['high'].rolling(20).max()
        df['low_20'] = df['low'].rolling(20).min()
        df['support_distance'] = (df['close'] - df['low_20']) / df['close']
        df['resistance_distance'] = (df['high_20'] - df['close']) / df['close']
        
        # Time-based features
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.dayofweek
            df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
            df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
            df['dow_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
            df['dow_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        
        return df

    def create_target_variable(self, data, horizon=4):
        """
        Crea la variable objetivo para el modelo
        
        Args:
            data: DataFrame con datos
            horizon: Horizonte de predicción
            
        Returns:
            Series: Variable objetivo (0=venta, 1=mantener, 2=compra)
        """
        future_returns = data['close'].shift(-horizon) / data['close'] - 1
        
        # Clasificación en 3 clases (más sensible)
        conditions = [
            future_returns <= -0.005,  # Caída > 0.5%
            future_returns >= 0.005    # Subida > 0.5%
        ]
        choices = [0, 2]  # 0=venta, 2=compra
        
        target = np.select(conditions, choices, default=1)  # 1=mantener
        
        return pd.Series(target, index=data.index)

    def prepare_ml_data(self, data):
        """
        Prepara los datos para entrenamiento de ML
        
        Args:
            data: DataFrame con datos técnicos
            
        Returns:
            tuple: (X, y) features y target
        """
        # Seleccionar features relevantes
        feature_cols = [col for col in data.columns if col not in 
                       ['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
        # Eliminar features con nombres problemáticos
        feature_cols = [col for col in feature_cols if not any(x in col.lower() for x in ['unnamed', 'index'])]
        
        X = data[feature_cols].copy()
        
        # Crear target
        y = self.create_target_variable(data, self.prediction_horizon)
        
        # Eliminar filas con NaN
        mask = ~(X.isna().any(axis=1) | y.isna())
        X = X[mask]
        y = y[mask]
        
        return X, y

    def train_models(self, X_train, y_train):
        """
        Entrena todos los modelos de ML
        
        Args:
            X_train: Features de entrenamiento
            y_train: Target de entrenamiento
        """
        logging.info("🧠 Entrenando modelos de ML...")
        
        # Escalar features
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        # Entrenar cada modelo
        for name, model in self.models.items():
            logging.info(f"📚 Entrenando modelo {name.upper()}...")
            model.fit(X_train_scaled, y_train)
            self.trained_models[name] = model
            
            # Calcular accuracy en entrenamiento
            train_pred = model.predict(X_train_scaled)
            train_acc = accuracy_score(y_train, train_pred)
            logging.info(f"✅ {name.upper()} - Accuracy entrenamiento: {train_acc:.3f}")

    def predict_ensemble(self, X):
        """
        Realiza predicción ensemble con todos los modelos
        
        Args:
            X: Features para predicción
            
        Returns:
            tuple: (predicción, confianza)
        """
        if not self.trained_models:
            return 1, 0.0  # Mantener con confianza 0
        
        X_scaled = self.scaler.transform(X.reshape(1, -1))
        
        predictions = []
        probabilities = []
        
        for name, model in self.trained_models.items():
            pred = model.predict(X_scaled)[0]
            
            # Obtener probabilidades si están disponibles
            if hasattr(model, 'predict_proba'):
                proba = model.predict_proba(X_scaled)[0]
                confidence = np.max(proba)
            else:
                confidence = 0.7  # Confianza por defecto
            
            predictions.append(pred)
            probabilities.append(confidence)
        
        # Ensemble por votación mayoritaria
        final_prediction = np.bincount(predictions).argmax()
        
        # Confianza promedio
        avg_confidence = np.mean(probabilities)
        
        return final_prediction, avg_confidence

    def calculate_position_size(self, confidence, current_price):
        """
        Calcula el tamaño de posición basado en la confianza del modelo
        
        Args:
            confidence: Confianza de la predicción
            current_price: Precio actual
            
        Returns:
            float: Tamaño de posición en USD
        """
        # Tamaño base
        base_size = self.current_capital * self.max_position_size
        
        # Ajustar por confianza
        confidence_multiplier = min(confidence / self.confidence_threshold, 2.0)
        
        # Aplicar apalancamiento
        position_size = base_size * confidence_multiplier * self.leverage
        
        # Limitar al capital disponible
        max_size = self.current_capital * self.leverage * 0.8
        
        return min(position_size, max_size)

    def execute_ml_trade(self, prediction, confidence, current_price, timestamp):
        """
        Ejecuta una operación basada en la predicción de ML
        
        Args:
            prediction: Predicción del modelo (0=venta, 1=mantener, 2=compra)
            confidence: Confianza de la predicción
            current_price: Precio actual
            timestamp: Timestamp de la operación
        """
        if confidence < self.confidence_threshold:
            return  # No operar si la confianza es baja
        
        position_size = self.calculate_position_size(confidence, current_price)
        
        if position_size < 50:  # Mínimo $50
            return
        
        # Determinar tipo de operación
        if prediction == 2:  # Compra
            self.execute_buy_order(current_price, position_size, confidence, timestamp)
        elif prediction == 0:  # Venta
            self.execute_sell_order(current_price, position_size, confidence, timestamp)
        # prediction == 1 (mantener) no hace nada

    def execute_buy_order(self, price, size, confidence, timestamp):
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
            'confidence': confidence
        }
        
        # Registrar operación
        operation = {
            'timestamp': timestamp,
            'type': 'BUY_ML',
            'price': price,
            'quantity': quantity,
            'size': size,
            'fee': fee,
            'confidence': confidence,
            'capital_after': self.current_capital,
            'position_id': position_id
        }
        
        self.operations.append(operation)
        
        logging.info(f"📈 ML BUY: ${size:.2f} @ ${price:.2f} | Conf: {confidence:.3f}")

    def execute_sell_order(self, price, size, confidence, timestamp):
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
            'confidence': confidence
        }
        
        # Registrar operación
        operation = {
            'timestamp': timestamp,
            'type': 'SELL_ML',
            'price': price,
            'quantity': quantity,
            'size': size,
            'fee': fee,
            'confidence': confidence,
            'capital_after': self.current_capital,
            'position_id': position_id
        }
        
        self.operations.append(operation)
        
        logging.info(f"📉 ML SELL: ${size:.2f} @ ${price:.2f} | Conf: {confidence:.3f}")

    def close_position(self, position_id, current_price, timestamp, reason="ml_signal"):
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
        Ejecuta backtest del sistema de ML
        
        Args:
            symbol: Par de trading
            days: Días de backtest
        """
        logging.info(f"🔄 Iniciando backtest de ML para {symbol}")
        
        # Obtener datos
        fetcher = RobustDataFetcher()
        data = fetcher.get_market_data(symbol, '1h', limit=days*24)
        
        if data is None or data.empty:
            logging.error(f"❌ No se pudieron obtener datos para {symbol}")
            return
        
        # Normalizar datos
        data.columns = data.columns.str.lower()
        if data.index.name == 'timestamp' or 'timestamp' in str(data.index.name).lower():
            data.reset_index(inplace=True)
        
        logging.info(f"📊 Datos obtenidos: {len(data)} velas de 1h")
        
        # Crear features técnicos
        data_with_features = self.create_technical_features(data)
        
        # Preparar datos para ML
        X, y = self.prepare_ml_data(data_with_features)
        
        if len(X) < 100:
            logging.error("❌ Datos insuficientes para entrenamiento")
            return
        
        # Split train/test
        split_idx = int(len(X) * 0.7)  # 70% entrenamiento
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        # Entrenar modelos
        self.train_models(X_train, y_train)
        
        # Backtest en datos de test
        logging.info("🔄 Iniciando backtest con predicciones ML...")
        
        for idx in range(len(X_test)):
            current_idx = split_idx + idx
            current_price = data_with_features['close'].iloc[current_idx]
            timestamp = data_with_features.get('timestamp', pd.Series([current_idx])).iloc[current_idx]
            
            # Realizar predicción
            features = X_test.iloc[idx].values
            prediction, confidence = self.predict_ensemble(features)
            
            # Registrar predicción
            self.predictions_log.append({
                'timestamp': timestamp,
                'prediction': prediction,
                'confidence': confidence,
                'actual_price': current_price
            })
            
            # Ejecutar trade basado en ML
            self.execute_ml_trade(prediction, confidence, current_price, timestamp)
            
            # Cerrar posiciones antiguas (stop loss/take profit)
            self.manage_positions(current_price, timestamp)
        
        # Cerrar todas las posiciones al final
        final_price = data_with_features['close'].iloc[-1]
        for position_id in list(self.positions.keys()):
            self.close_position(position_id, final_price, data.index[-1], "backtest_end")
        
        # Calcular métricas finales
        self.calculate_final_metrics(days)

    def manage_positions(self, current_price, timestamp):
        """Gestiona posiciones abiertas con stop loss y take profit"""
        positions_to_close = []
        
        for position_id, position in self.positions.items():
            # Calcular PnL actual
            if position['type'] == 'LONG':
                pnl_pct = (current_price - position['entry_price']) / position['entry_price']
            else:  # SHORT
                pnl_pct = (position['entry_price'] - current_price) / position['entry_price']
            
            # Stop loss: -5%
            if pnl_pct <= -0.05:
                positions_to_close.append((position_id, "stop_loss"))
            
            # Take profit: +10%
            elif pnl_pct >= 0.10:
                positions_to_close.append((position_id, "take_profit"))
        
        # Cerrar posiciones
        for position_id, reason in positions_to_close:
            self.close_position(position_id, current_price, timestamp, reason)

    def calculate_final_metrics(self, days):
        """Calcula métricas finales del backtest"""
        if not self.operations:
            logging.warning("⚠️ No se generaron operaciones de ML")
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
        
        # Confianza promedio
        ml_ops = [op for op in self.operations if 'confidence' in op]
        avg_confidence = np.mean([op['confidence'] for op in ml_ops]) if ml_ops else 0
        
        # Logging de resultados
        logging.info("=" * 80)
        logging.info("RESULTADOS SISTEMA DE ML SEÑALES SICAR")
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
        logging.info(f"🧠 Confianza promedio: {avg_confidence:.3f}")
        logging.info(f"📅 Duración: {days} días ({months:.1f} meses)")
        logging.info(f"⚡ Apalancamiento: {self.leverage}x")
        logging.info(f"⚡ Gap al objetivo: {roi_gap:.2f}% (Objetivo: {target_roi}%)")
        logging.info("=" * 80)
        
        # Guardar resultados
        self.save_results()
        
        # Resumen final
        print(f"\n✅ Backtest de ML completado!")
        print(f"📊 ROI mensual: {monthly_roi:.2f}%")
        print(f"🎯 Objetivo: {target_roi}%")
        print(f"🔄 Total operaciones: {total_operations}")
        print(f"🏆 Win rate: {win_rate:.1f}%")
        print(f"🧠 Confianza promedio: {avg_confidence:.3f}")
        print(f"⚡ Apalancamiento: {self.leverage}x")
        print(f"📁 Resultados guardados en: ml_signals_sicar_results.csv")

    def save_results(self):
        """Guarda los resultados en CSV"""
        if self.operations:
            df = pd.DataFrame(self.operations)
            df.to_csv('ml_signals_sicar_results.csv', index=False)
            logging.info("💾 Resultados guardados en ml_signals_sicar_results.csv")
        
        if self.predictions_log:
            pred_df = pd.DataFrame(self.predictions_log)
            pred_df.to_csv('ml_predictions_log.csv', index=False)
            logging.info("💾 Log de predicciones guardado en ml_predictions_log.csv")

def main():
    """Función principal"""
    try:
        # Crear y ejecutar sistema de ML
        system = MLSignalsSicarSystem(
            initial_capital=500,
            leverage=6.0  # Apalancamiento agresivo para ML
        )
        
        # Ejecutar backtest
        system.run_backtest(symbol='BTCUSDT', days=60)
        
    except Exception as e:
        logging.error(f"❌ Error en sistema de ML: {str(e)}")
        raise

if __name__ == "__main__":
    main()