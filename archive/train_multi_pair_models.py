#!/usr/bin/env python3
"""
Sistema de Entrenamiento Multi-Par para Trading Institucional
Entrena modelos ML individualizados para cada par de criptomonedas
"""

import pandas as pd
import numpy as np
import os
import json
import pickle
from datetime import datetime
import logging
import time
from typing import Dict, List, Tuple, Optional

import lightgbm as lgb
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import matplotlib.pyplot as plt
import seaborn as sns

from utils.logger_setup import setup_logging
from database.database_manager import get_klines
from config import settings

setup_logging()
logger = logging.getLogger(__name__)

class MultiPairMLTrainer:
    def __init__(self):
        # Configuración de pares de la configuración multi-par
        self.config_file = "data/multi_pair_historical/multi_pair_config.json"
        self.load_pair_config()
        
        # Directorios de trabajo
        self.data_path = "data/multi_pair_historical/"
        self.model_path = "models/multi_pair/"
        self.results_path = "results/multi_pair/"
        
        # Crear directorios
        for path in [self.model_path, self.results_path]:
            os.makedirs(path, exist_ok=True)
        
        # Configuración ML por categoría de riesgo
        self.ml_configs = {
            "Low Risk": {
                "learning_rate": 0.05,
                "n_estimators": 300,
                "max_depth": 8,
                "feature_fraction": 0.8,
                "bagging_fraction": 0.8,
                "regularization_lambda": 1.0,
                "regularization_alpha": 0.1
            },
            "Medium Risk": {
                "learning_rate": 0.08,
                "n_estimators": 400,
                "max_depth": 10,
                "feature_fraction": 0.85,
                "bagging_fraction": 0.85,
                "regularization_lambda": 1.2,
                "regularization_alpha": 0.15
            },
            "High Risk": {
                "learning_rate": 0.1,
                "n_estimators": 500,
                "max_depth": 12,
                "feature_fraction": 0.9,
                "bagging_fraction": 0.9,
                "regularization_lambda": 1.5,
                "regularization_alpha": 0.2
            }
        }
        
        # Métricas de entrenamiento
        self.training_results = {}
        
    def load_pair_config(self):
        """Cargar configuración de pares"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.pair_config = config['multi_pair_config']
                self.trading_pairs = list(self.pair_config['pairs'].keys())
                self.risk_tiers = self.pair_config['risk_tiers']
                logger.info(f"✅ Configuración cargada: {len(self.trading_pairs)} pares")
        except Exception as e:
            logger.error(f"❌ Error cargando configuración: {e}")
            # Fallback a configuración básica
            self.trading_pairs = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
            self.risk_tiers = {"Low Risk": ["BTCUSDT", "ETHUSDT"], "Medium Risk": ["BNBUSDT"]}
    
    def get_risk_tier(self, symbol: str) -> str:
        """Obtener el nivel de riesgo de un par"""
        for tier, pairs in self.risk_tiers.items():
            if symbol in pairs:
                return tier
        return "Medium Risk"  # Default
    
    def create_features(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Crear características técnicas para un par específico"""
        logger.info(f"📊 Creando características para {symbol}")
        
        df = df.copy()
        
        # Características básicas de precio
        df['price_change'] = df['close'].pct_change()
        df['high_low_ratio'] = df['high'] / df['low']
        df['volume_change'] = df['volume'].pct_change()
        
        # Medias móviles (ajustadas por volatilidad del par)
        risk_tier = self.get_risk_tier(symbol)
        if risk_tier == "High Risk":
            # Períodos más cortos para alta volatilidad
            short, medium, long = 12, 24, 72
        elif risk_tier == "Medium Risk":
            short, medium, long = 20, 50, 100
        else:  # Low Risk
            # Períodos más largos para estabilidad
            short, medium, long = 24, 72, 200
        
        df[f'ma_{short}'] = df['close'].rolling(window=short).mean()
        df[f'ma_{medium}'] = df['close'].rolling(window=medium).mean()
        df[f'ma_{long}'] = df['close'].rolling(window=long).mean()
        
        # Relaciones entre medias móviles
        df['ma_short_medium'] = df[f'ma_{short}'] / df[f'ma_{medium}']
        df['ma_medium_long'] = df[f'ma_{medium}'] / df[f'ma_{long}']
        
        # RSI adaptivo
        rsi_period = 14 if risk_tier != "High Risk" else 10
        df['rsi'] = self.calculate_rsi(df['close'], rsi_period)
        
        # Volatilidad
        df['volatility'] = df['close'].rolling(window=24).std()
        df['volatility_ratio'] = df['volatility'] / df['volatility'].rolling(window=168).mean()
        
        # Características de volumen
        df['volume_ma'] = df['volume'].rolling(window=24).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        bb_period = 20
        df['bb_middle'] = df['close'].rolling(window=bb_period).mean()
        bb_std = df['close'].rolling(window=bb_period).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Características temporales
        df['hour'] = df.index.hour
        df['day_of_week'] = df.index.dayofweek
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        
        # Target: Movimiento del precio en próximas horas
        future_periods = 6  # 6 horas adelante
        df['future_return'] = df['close'].shift(-future_periods) / df['close'] - 1
        
        # Clasificación binaria: 1 si sube más del umbral, 0 si no
        threshold = 0.002 if risk_tier == "Low Risk" else 0.005 if risk_tier == "Medium Risk" else 0.01
        df['target'] = (df['future_return'] > threshold).astype(int)
        
        # Eliminar NaN y seleccionar características
        feature_columns = [col for col in df.columns if col not in 
                          ['open', 'high', 'low', 'close', 'volume', 'close_time', 
                           'quote_asset_volume', 'number_of_trades', 'taker_buy_base_volume',
                           'taker_buy_quote_volume', 'ignore', 'future_return']]
        
        df_features = df[feature_columns].dropna()
        
        logger.info(f"✅ {symbol}: {len(df_features)} muestras, {len(feature_columns)-1} características")
        return df_features
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcular RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def train_pair_model(self, symbol: str) -> Dict:
        """Entrenar modelo ML para un par específico"""
        logger.info(f"🤖 ENTRENANDO MODELO PARA {symbol}")
        logger.info("─" * 50)
        
        # Cargar datos
        csv_file = f"{self.data_path}{symbol.lower()}_1h_historical.csv"
        if not os.path.exists(csv_file):
            logger.error(f"❌ No se encontraron datos para {symbol}")
            return None
        
        df = pd.read_csv(csv_file, index_col='timestamp', parse_dates=True)
        
        # Crear características
        df_features = self.create_features(df, symbol)
        
        if df_features.empty:
            logger.error(f"❌ No se pudieron crear características para {symbol}")
            return None
        
        # Preparar datos para entrenamiento
        X = df_features.drop(['target'], axis=1)
        y = df_features['target']
        
        # Limpiar datos: reemplazar infinitos y NaN
        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.ffill().fillna(0)
        
        # División temporal para series de tiempo
        split_point = int(len(df_features) * 0.8)
        X_train, X_test = X[:split_point], X[split_point:]
        y_train, y_test = y[:split_point], y[split_point:]
        
        # Normalización
        scaler = RobustScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Configuración ML específica del par
        risk_tier = self.get_risk_tier(symbol)
        ml_config = self.ml_configs[risk_tier]
        
        logger.info(f"📊 {symbol} - Tier: {risk_tier}")
        logger.info(f"   • Entrenamiento: {len(X_train)} muestras")
        logger.info(f"   • Prueba: {len(X_test)} muestras")
        logger.info(f"   • Características: {len(X.columns)}")
        logger.info(f"   • Balance clases: {y_train.value_counts().to_dict()}")
        
        # Entrenar modelo LightGBM
        train_data = lgb.Dataset(X_train_scaled, label=y_train)
        valid_data = lgb.Dataset(X_test_scaled, label=y_test, reference=train_data)
        
        params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': ml_config['learning_rate'],
            'feature_fraction': ml_config['feature_fraction'],
            'bagging_fraction': ml_config['bagging_fraction'],
            'bagging_freq': 5,
            'max_depth': ml_config['max_depth'],
            'lambda_l1': ml_config['regularization_alpha'],
            'lambda_l2': ml_config['regularization_lambda'],
            'min_data_in_leaf': 20,
            'verbose': -1,
            'random_state': 42
        }
        
        # Entrenar con early stopping
        model = lgb.train(
            params,
            train_data,
            valid_sets=[valid_data],
            num_boost_round=ml_config['n_estimators'],
            callbacks=[
                lgb.early_stopping(stopping_rounds=50),
                lgb.log_evaluation(period=100)
            ]
        )
        
        # Predicciones y métricas
        y_pred_proba = model.predict(X_test_scaled)
        y_pred = (y_pred_proba > 0.5).astype(int)
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1_score': f1_score(y_test, y_pred)
        }
        
        logger.info(f"📈 MÉTRICAS {symbol}:")
        logger.info(f"   • Precisión: {metrics['accuracy']:.3f}")
        logger.info(f"   • Precision: {metrics['precision']:.3f}")
        logger.info(f"   • Recall: {metrics['recall']:.3f}")
        logger.info(f"   • F1-Score: {metrics['f1_score']:.3f}")
        
        # Guardar modelo y scaler
        model_file = f"{self.model_path}{symbol.lower()}_model.txt"
        scaler_file = f"{self.model_path}{symbol.lower()}_scaler.pkl"
        
        model.save_model(model_file)
        with open(scaler_file, 'wb') as f:
            pickle.dump(scaler, f)
        
        # Análisis de importancia de características
        feature_importance = model.feature_importance()
        feature_names = X.columns
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': feature_importance
        }).sort_values('importance', ascending=False)
        
        logger.info(f"🔍 TOP 5 CARACTERÍSTICAS {symbol}:")
        for idx, row in enumerate(importance_df.head(5).itertuples(), 1):
            logger.info(f"   {idx}. {row.feature}: {row.importance}")
        
        # Resultado del entrenamiento
        result = {
            'symbol': symbol,
            'risk_tier': risk_tier,
            'metrics': metrics,
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'features_count': len(X.columns),
            'model_file': model_file,
            'scaler_file': scaler_file,
            'feature_importance': importance_df.to_dict('records')[:10],
            'training_time': time.time()
        }
        
        return result
    
    def train_all_models(self):
        """Entrenar modelos para todos los pares"""
        logger.info("🚀 INICIANDO ENTRENAMIENTO MULTI-PAR")
        logger.info("🤖 Sistema de ML Institucional Diversificado")
        logger.info("="*70)
        
        start_time = time.time()
        successful_trainings = 0
        
        for symbol in self.trading_pairs:
            logger.info("")
            result = self.train_pair_model(symbol)
            
            if result:
                self.training_results[symbol] = result
                successful_trainings += 1
                logger.info(f"✅ {symbol}: Modelo entrenado exitosamente")
            else:
                logger.error(f"❌ {symbol}: Error en entrenamiento")
        
        total_time = time.time() - start_time
        
        # Generar reporte final
        self.generate_training_report(successful_trainings, total_time)
        
        return successful_trainings > 0
    
    def generate_training_report(self, successful_trainings: int, total_time: float):
        """Generar reporte completo del entrenamiento"""
        logger.info("")
        logger.info("="*80)
        logger.info("🎉 ENTRENAMIENTO MULTI-PAR COMPLETADO")
        logger.info("="*80)
        
        logger.info(f"📊 Resumen general:")
        logger.info(f"   • Modelos entrenados: {successful_trainings}/{len(self.trading_pairs)}")
        logger.info(f"   • Tiempo total: {total_time/60:.1f} minutos")
        logger.info(f"   • Tiempo promedio/modelo: {total_time/max(successful_trainings, 1)/60:.1f} minutos")
        logger.info("")
        
        if not self.training_results:
            logger.warning("⚠️ No hay resultados para reportar")
            return
        
        # Análisis por tier de riesgo
        logger.info("📈 ANÁLISIS POR TIER DE RIESGO:")
        logger.info("─" * 60)
        
        tier_metrics = {}
        for tier in ["Low Risk", "Medium Risk", "High Risk"]:
            tier_results = [r for r in self.training_results.values() if r['risk_tier'] == tier]
            if tier_results:
                avg_accuracy = np.mean([r['metrics']['accuracy'] for r in tier_results])
                avg_f1 = np.mean([r['metrics']['f1_score'] for r in tier_results])
                
                tier_metrics[tier] = {
                    'pairs_count': len(tier_results),
                    'avg_accuracy': avg_accuracy,
                    'avg_f1': avg_f1
                }
                
                logger.info(f"🎯 {tier}:")
                logger.info(f"   • Pares: {len(tier_results)}")
                logger.info(f"   • Precisión promedio: {avg_accuracy:.3f}")
                logger.info(f"   • F1-Score promedio: {avg_f1:.3f}")
                logger.info("")
        
        # Ranking de modelos
        logger.info("🏆 RANKING DE MODELOS (Por F1-Score):")
        logger.info("─" * 50)
        
        sorted_results = sorted(self.training_results.values(), 
                              key=lambda x: x['metrics']['f1_score'], reverse=True)
        
        for i, result in enumerate(sorted_results, 1):
            logger.info(f"   {i}. {result['symbol']}: F1={result['metrics']['f1_score']:.3f} "
                       f"(Acc={result['metrics']['accuracy']:.3f}, Tier={result['risk_tier']})")
        
        # Guardar resultados
        results_file = f"{self.results_path}training_results.json"
        with open(results_file, 'w') as f:
            # Convertir numpy types para JSON
            json_results = {}
            for symbol, result in self.training_results.items():
                json_result = result.copy()
                for metric_key in ['accuracy', 'precision', 'recall', 'f1_score']:
                    json_result['metrics'][metric_key] = float(json_result['metrics'][metric_key])
                json_results[symbol] = json_result
            
            json.dump({
                'training_summary': {
                    'timestamp': datetime.now().isoformat(),
                    'successful_trainings': successful_trainings,
                    'total_time_minutes': round(total_time/60, 2),
                    'tier_metrics': tier_metrics
                },
                'individual_results': json_results
            }, f, indent=2)
        
        logger.info(f"📝 Resultados guardados en: {results_file}")
        logger.info("")
        logger.info("🚀 SISTEMA MULTI-PAR ML LISTO PARA TRADING")
        logger.info("💡 Próximo paso: Validación con paper trading")
        logger.info("="*80)

async def main():
    """Función principal"""
    trainer = MultiPairMLTrainer()
    success = trainer.train_all_models()
    
    if success:
        logger.info("🎉 Entrenamiento multi-par completado exitosamente")
    else:
        logger.error("❌ Error en entrenamiento multi-par")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
