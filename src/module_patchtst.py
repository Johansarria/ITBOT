#!/usr/bin/env python3
"""
Módulo PatchTST para SICAR - Sistema de predicción de series temporales
Basado en IBM Granite PatchTST para análisis de precios de criptomonedas

Características:
- Predicción de precios a 96 horas
- Análisis de patrones temporales
- Integración con sistema de decisiones SICAR
- Fine-tuning con datos de criptomonedas
"""

import os
import sys
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

# Configurar logging
logger = logging.getLogger(__name__)

@dataclass
class PatchTSTConfig:
    """Configuración para PatchTST"""
    seq_len: int = 512  # Longitud de secuencia histórica (512 horas)
    pred_len: int = 96  # Longitud de predicción (96 horas)
    patch_len: int = 16  # Longitud de cada patch
    stride: int = 8  # Stride para patches
    d_model: int = 128  # Dimensiones del modelo
    n_heads: int = 8  # Número de heads de atención
    e_layers: int = 3  # Número de capas encoder
    d_ff: int = 512  # Dimensiones feedforward
    dropout: float = 0.1  # Dropout rate
    learning_rate: float = 5e-5  # Tasa de aprendizaje
    batch_size: int = 8  # Tamaño de batch
    epochs: int = 10  # Número de épocas

class PatchTST:
    """
    Clase principal para PatchTST en SICAR
    """
    
    def __init__(self, config: Optional[PatchTSTConfig] = None):
        self.config = config or PatchTSTConfig()
        self.model = None
        self.scaler = None
        self.is_trained = False
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        logger.info(f"PatchTST inicializado en dispositivo: {self.device}")
    
    def prepare_crypto_data(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Preparar datos de criptomonedas para PatchTST
        
        Args:
            data: DataFrame con columnas ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            
        Returns:
            X: Datos de entrada (features)
            y: Datos objetivo (predicción)
        """
        logger.info("Preparando datos de criptomonedas para PatchTST")
        
        # Seleccionar features relevantes (similar a ETTh1 dataset)
        features = ['HUFL', 'HULL', 'MUFL', 'MULL', 'LUFL', 'LULL', 'OT']  # Mapear a cripto
        
        # Mapear datos de cripto a formato ETTh1
        crypto_mapping = {
            'HUFL': 'high',      # High Upper FL
            'HULL': 'low',       # High Upper LL  
            'MUFL': 'open',      # Mid Upper FL
            'MULL': 'close',     # Mid Upper LL
            'LUFL': 'volume',    # Low Upper FL
            'LULL': 'volatility', # Low Upper LL (calculado)
            'OT': 'close'        # Output Target
        }
        
        # Crear dataset con features necesarias
        dataset = pd.DataFrame()
        dataset['timestamp'] = pd.to_datetime(data['timestamp'])
        
        for patch_feature, crypto_feature in crypto_mapping.items():
            if crypto_feature == 'volatility':
                # Calcular volatilidad como rolling std
                dataset[patch_feature] = data['close'].rolling(window=24).std()
            elif crypto_feature in data.columns:
                dataset[patch_feature] = data[crypto_feature]
            else:
                dataset[patch_feature] = data['close']  # Default
        
        # Eliminar NaN
        dataset = dataset.dropna()
        
        # Normalizar datos
        from sklearn.preprocessing import StandardScaler
        self.scaler = StandardScaler()
        
        # Preparar secuencias
        X, y = self._create_sequences(dataset[features].values)
        
        logger.info(f"Datos preparados: X shape {X.shape}, y shape {y.shape}")
        return X, y
    
    def _create_sequences(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Crear secuencias para entrenamiento"""
        seq_len = self.config.seq_len
        pred_len = self.config.pred_len
        
        X, y = [], []
        
        for i in range(len(data) - seq_len - pred_len + 1):
            # Secuencia de entrada
            seq_x = data[i:i + seq_len]
            # Secuencia objetivo (solo el canal OT - precio de cierre)
            seq_y = data[i + seq_len:i + seq_len + pred_len, -1]  # OT es la última columna
            
            X.append(seq_x)
            y.append(seq_y)
        
        return np.array(X), np.array(y)
    
    def build_model(self):
        """Construir arquitectura PatchTST"""
        logger.info("Construyendo arquitectura PatchTST")
        
        class PatchTSTEncoder(nn.Module):
            def __init__(self, config):
                super().__init__()
                self.config = config
                
                # Patch embedding
                self.patch_embedding = nn.Linear(config.patch_len, config.d_model)
                
                # Positional encoding
                self.pos_encoding = nn.Parameter(
                    torch.randn(1, config.seq_len // config.stride, config.d_model)
                )
                
                # Transformer encoder
                encoder_layer = nn.TransformerEncoderLayer(
                    d_model=config.d_model,
                    nhead=config.n_heads,
                    dim_feedforward=config.d_ff,
                    dropout=config.dropout,
                    batch_first=True
                )
                self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=config.e_layers)
                
                # Head para predicción (1 valor para predicción de precio)
                self.predict_head = nn.Linear(config.d_model, 1)
                # Cabeza de cuantiles (q10,q50,q90)
                self.quantile_head = nn.Linear(config.d_model, 3)
                # Cabeza de dirección (up/down)
                self.class_head = nn.Linear(config.d_model, 1)
                
            def forward(self, x):
                # x: [batch, seq_len, features]
                batch_size, seq_len, n_features = x.shape
                
                # Crear patches
                patches = []
                for i in range(0, seq_len - self.config.patch_len + 1, self.config.stride):
                    patch = x[:, i:i + self.config.patch_len, :]
                    patches.append(patch)
                
                patches = torch.stack(patches, dim=1)  # [batch, n_patches, patch_len, features]
                
                # Aplicar embedding a cada patch
                n_patches = patches.shape[1]
                patches_embedded = self.patch_embedding(patches.mean(dim=-1))  # Promediar features
                
                # Agregar positional encoding
                patches_embedded = patches_embedded + self.pos_encoding[:, :n_patches, :]
                
                # Aplicar transformer
                encoded = self.transformer(patches_embedded)
                
                # Predicción
                pooled = encoded.mean(dim=1)
                out_mean = self.predict_head(pooled)
                out_quants = self.quantile_head(pooled)
                out_dir = self.class_head(pooled)
                return out_mean, out_quants, out_dir
        
        self.model = PatchTSTEncoder(self.config).to(self.device)
        logger.info("Modelo PatchTST construido exitosamente")
    
    def train(self, X: np.ndarray, y: np.ndarray, validation_split: float = 0.2):
        """Entrenar el modelo PatchTST"""
        logger.info("Iniciando entrenamiento de PatchTST")
        
        if self.model is None:
            self.build_model()
        
        # Convertir a tensores
        X_tensor = torch.FloatTensor(X).to(self.device)
        y_tensor = torch.FloatTensor(y).to(self.device)
        
        # Dividir en train/validation
        n_samples = X_tensor.shape[0]
        n_train = int(n_samples * (1 - validation_split))
        
        X_train, X_val = X_tensor[:n_train], X_tensor[n_train:]
        y_train, y_val = y_tensor[:n_train], y_tensor[n_train:]
        
        # Configurar optimizador y pérdida
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.config.learning_rate, weight_decay=1e-5)
        mse_loss = nn.MSELoss()
        bce_loss = nn.BCEWithLogitsLoss()
        
        # Entrenamiento
        train_losses, val_losses = [], []
        
        for epoch in range(self.config.epochs):
            # Training
            self.model.train()
            train_loss = 0
            
            for i in range(0, len(X_train), self.config.batch_size):
                batch_X = X_train[i:i + self.config.batch_size]
                batch_y = y_train[i:i + self.config.batch_size]
                
                optimizer.zero_grad()
                out_mean, out_quants, out_dir = self.model(batch_X)
                # MSE sobre media
                loss_mse = mse_loss(out_mean.squeeze(-1), batch_y.squeeze(-1))
                # Pinball loss para cuantiles
                q_vals = torch.tensor([0.1, 0.5, 0.9], device=self.device).unsqueeze(0).expand(out_quants.shape[0], -1)
                y_exp = batch_y.squeeze(-1).unsqueeze(-1).expand_as(out_quants)
                diff = y_exp - out_quants
                pinball = torch.maximum(q_vals*diff, (q_vals-1)*diff).mean()
                # Dirección: comparar futuro vs último OT del input
                current_close = batch_X[:, -1, -1]  # última hora canal OT
                dir_target = (batch_y.squeeze(-1) - current_close > 0).float()
                loss_bce = bce_loss(out_dir.squeeze(-1), dir_target)
                loss = loss_mse + 0.5*pinball + 0.2*loss_bce
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
            
            # Validation
            self.model.eval()
            with torch.no_grad():
                vm, vq, vd = self.model(X_val)
                val_loss = mse_loss(vm.squeeze(-1), y_val.squeeze(-1)).item()
            
            train_loss_avg = train_loss / (len(X_train) // self.config.batch_size + 1)
            train_losses.append(train_loss_avg)
            val_losses.append(val_loss)
            
            if epoch % 2 == 0:
                logger.info(f"Epoch {epoch}: Train Loss = {train_loss_avg:.4f}, Val Loss = {val_loss:.4f}")
        
        self.is_trained = True
        logger.info("Entrenamiento de PatchTST completado")
        
        return train_losses, val_losses
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Realizar predicciones con el modelo entrenado"""
        if not self.is_trained:
            raise ValueError("El modelo debe ser entrenado antes de hacer predicciones")
        
        self.model.eval()
        
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X).to(self.device)
            out_mean, out_quants, out_dir = self.model(X_tensor)
            
        return out_mean.cpu().numpy()

    def predict_with_quantiles(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if not self.is_trained:
            raise ValueError("El modelo debe ser entrenado antes de hacer predicciones")
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X).to(self.device)
            out_mean, out_quants, _ = self.model(X_tensor)
        return out_mean.cpu().numpy(), out_quants.cpu().numpy()
    
    def generate_trading_signals(self, 
                                 historical_data: pd.DataFrame, 
                                 current_price: float) -> Dict[str, Any]:
        """
        Generar señales de trading basadas en predicciones PatchTST
        
        Returns:
            Dict con señales, confianza y análisis
        """
        logger.info("Generando señales de trading con PatchTST")
        
        # Preparar datos
        X, _ = self.prepare_crypto_data(historical_data)
        
        if len(X) == 0:
            return {"error": "Datos insuficientes para predicción"}
        
        # Tomar la última secuencia
        last_sequence = X[-1:]
        
        # Predecir próximas 96 horas
        predictions = self.predict(last_sequence)[0]
        
        # Análisis de señales
        current_pred = predictions[0]
        future_pred = predictions[-1]
        
        # Calcular tendencia y confianza
        price_change_pct = (future_pred - current_price) / current_price * 100
        trend_strength = abs(price_change_pct)
        
        # Generar señal
        if price_change_pct > 2.0:  # Subida significativa
            signal = "BUY"
            confidence = min(trend_strength / 5.0, 0.9)  # Máx 90% confianza
        elif price_change_pct < -2.0:  # Bajada significativa
            signal = "SELL"
            confidence = min(trend_strength / 5.0, 0.9)
        else:
            signal = "HOLD"
            confidence = 0.5
        
        result = {
            "signal": signal,
            "confidence": float(confidence),
            "current_price": current_price,
            "predicted_price_96h": float(future_pred),
            "price_change_pct": float(price_change_pct),
            "prediction_horizon": "96 horas",
            "model_used": "PatchTST",
            "predictions_series": predictions.tolist(),
            "analysis": {
                "trend": "alcista" if price_change_pct > 0 else "bajista",
                "strength": float(trend_strength),
                "recommendation": self._generate_recommendation(signal, confidence, price_change_pct)
            }
        }
        
        logger.info(f"Señal generada: {signal} con confianza {confidence:.2f}")
        return result

    def generate_trading_signals_from_features(self,
                                               features_df: pd.DataFrame,
                                               close_scaler,
                                               current_price: float) -> Dict[str, Any]:
        """
        Generar señales usando features ya normalizados (ETTh1: HUFL,HULL,MUFL,MULL,LUFL,LULL,OT)
        y desnormalizar la predicción a USD usando el scaler del cierre.
        """
        required = ['HUFL','HULL','MUFL','MULL','LUFL','LULL','OT']
        for c in required:
            if c not in features_df.columns:
                raise ValueError("Features ETTh1 incompletos para PatchTST")

        seq_len = self.config.seq_len
        X_list = []
        for i in range(len(features_df) - seq_len):
            X_window = features_df.iloc[i:i+seq_len][required[:-1]].values  # sin OT como feature
            # Incluir OT como última columna para consistencia (7 canales) si el modelo lo espera
            # El modelo usa mean de features; mantener 6 canales es suficiente
            X_list.append(X_window)
        if not X_list:
            return {"error":"Datos insuficientes para predicción"}
        X = np.array(X_list)
        last_seq = X[-1:]
        mean_norm, quants_norm = self.predict_with_quantiles(last_seq)
        mean_norm = mean_norm.flatten()
        quants_norm = quants_norm.flatten()
        try:
            preds_usd = close_scaler.inverse_transform(mean_norm.reshape(-1,1)).flatten()
            quants_usd = close_scaler.inverse_transform(quants_norm.reshape(-1,1)).flatten()
        except Exception:
            recent_close = features_df['MULL'].values.reshape(-1,1)
            min_v, max_v = recent_close.min(), recent_close.max()
            preds_usd = mean_norm * (max_v - min_v) + min_v
            quants_usd = quants_norm * (max_v - min_v) + min_v

        current_pred_usd = float(preds_usd[0])
        future_pred_usd = float(preds_usd[-1])
        price_change_pct = (future_pred_usd - current_price) / current_price * 100
        trend_strength = abs(price_change_pct)
        if price_change_pct > 2.0:
            signal = "BUY"; confidence = min(trend_strength/5.0, 0.9)
        elif price_change_pct < -2.0:
            signal = "SELL"; confidence = min(trend_strength/5.0, 0.9)
        else:
            signal = "HOLD"; confidence = 0.5

        return {
            "signal": signal,
            "confidence": float(confidence),
            "current_price": current_price,
            "predicted_price_96h": future_pred_usd,
            "price_change_pct": float(price_change_pct),
            "prediction_horizon": "96 horas",
            "model_used": "PatchTST",
            "predictions_series": preds_usd.tolist(),
            "quantiles": {"p10": float(quants_usd[0]), "p50": float(quants_usd[1]), "p90": float(quants_usd[2])},
            "analysis": {
                "trend": "alcista" if price_change_pct > 0 else "bajista",
                "strength": float(trend_strength),
                "recommendation": self._generate_recommendation(signal, confidence, price_change_pct)
            }
        }
    
    def _generate_recommendation(self, signal: str, confidence: float, price_change: float) -> str:
        """Generar recomendación detallada"""
        if signal == "BUY":
            return f"Fuerte señal de compra. El modelo predice una subida del {price_change:.1f}% en las próximas 96 horas."
        elif signal == "SELL":
            return f"Fuerte señal de venta. El modelo predice una bajada del {abs(price_change):.1f}% en las próximas 96 horas."
        else:
            return "Mercado sin tendencia clara. Mantener posición actual."
    
    def save_model(self, filepath: str):
        """Guardar modelo entrenado"""
        if not self.is_trained:
            raise ValueError("El modelo debe ser entrenado antes de guardar")
        
        from dataclasses import asdict
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'config': asdict(self.config),
            'scaler': self.scaler,
            'is_trained': self.is_trained
        }, filepath)
        
        logger.info(f"Modelo PatchTST guardado en {filepath}")
    
    def load_model(self, filepath: str):
        """Cargar modelo entrenado"""
        checkpoint = torch.load(filepath, map_location=self.device, weights_only=False)
        cfg_dict = checkpoint.get('config', {})
        if isinstance(cfg_dict, dict):
            self.config = PatchTSTConfig(**cfg_dict)
        self.scaler = checkpoint.get('scaler')
        self.is_trained = checkpoint.get('is_trained', True)
        self.build_model()
        self.model.load_state_dict(checkpoint['model_state_dict'])
        
        logger.info(f"Modelo PatchTST cargado desde {filepath}")

def demo_patchtst():
    """Demo básica de PatchTST"""
    print("🚀 Demo de PatchTST para SICAR")
    print("="*50)
    
    # Crear datos de ejemplo (simulando datos de BTC)
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=1000, freq='H')
    
    # Simular precios de Bitcoin
    base_price = 45000
    volatility = 0.02
    
    prices = [base_price]
    for i in range(1, len(dates)):
        change = np.random.normal(0, volatility)
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    
    # Crear DataFrame
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': prices,
        'volume': np.random.uniform(1000, 10000, len(dates))
    })
    
    print(f"📊 Datos de ejemplo creados: {len(df)} registros")
    
    # Inicializar PatchTST
    patchtst = PatchTST()
    
    # Preparar datos
    X, y = patchtst.prepare_crypto_data(df)
    print(f"📈 Datos preparados: X={X.shape}, y={y.shape}")
    
    # Entrenar modelo (mini entrenamiento)
    print("🧠 Entrenando modelo...")
    train_losses, val_losses = patchtst.train(X, y, validation_split=0.2)
    
    # Generar señal de trading
    current_price = df['close'].iloc[-1]
    signal = patchtst.generate_trading_signals(df, current_price)
    
    print(f"\n🎯 Resultados del análisis:")
    print(f"   Señal: {signal['signal']}")
    print(f"   Confianza: {signal['confidence']:.2%}")
    print(f"   Precio actual: ${signal['current_price']:,.2f}")
    print(f"   Precio predicho (96h): ${signal['predicted_price_96h']:,.2f}")
    print(f"   Cambio esperado: {signal['price_change_pct']:.1f}%")
    print(f"   Recomendación: {signal['analysis']['recommendation']}")
    
    # Guardar modelo
    model_path = "models/patchtst_crypto_model.pth"
    os.makedirs("models", exist_ok=True)
    patchtst.save_model(model_path)
    print(f"\n💾 Modelo guardado en: {model_path}")
    
    return patchtst, signal

if __name__ == '__main__':
    try:
        model, results = demo_patchtst()
        print("\n✅ Demo de PatchTST completada exitosamente!")
    except Exception as e:
        print(f"\n❌ Error en demo: {str(e)}")
        import traceback
        traceback.print_exc()
