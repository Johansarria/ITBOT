#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SICAR - Sistema Integrado de Paper Trading Multi-Timeframe con ML
================================================================

Este módulo integra el análisis multi-timeframe con los modelos ML entrenados
con datos recientes desde la implementación de Grok xAI y OpenAI.

Características:
- Análisis multi-timeframe avanzado
- Predicciones ML con modelos entrenados
- Integración con paper trading existente
- Preservación de conexiones IA
- Monitoreo en tiempo real

Autor: SICAR Team
Fecha: 2025-01-21
"""

import os
import sys
import pandas as pd
import numpy as np
import logging
import joblib
import warnings
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from dataclasses import dataclass

# Configuración de warnings
warnings.filterwarnings('ignore')

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('integrated_multi_timeframe_paper_trading.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Importar módulos SICAR existentes
try:
    from paper_trading_system import PaperTradingEngine, PaperOrder, OrderType
    from binance_data_provider import BinanceDataProvider
except ImportError as e:
    logger.warning(f"Algunos módulos SICAR no están disponibles: {e}")

# Importar o definir MultiTimeframeSignal
try:
    from multi_timeframe_paper_trading import MultiTimeframePaperTrading, MultiTimeframeSignal
except ImportError:
    logger.warning("MultiTimeframeSignal no disponible, usando definición local")
    
    @dataclass
    class MultiTimeframeSignal:
        """Señal multi-timeframe (definición local)"""
        symbol: str
        action: str
        confidence: float
        strength: float
        timeframe_signals: Dict[str, str]
        risk_level: str
        entry_price: float
        stop_loss: float
        take_profit: float
        timestamp: datetime
    
    class MultiTimeframePaperTrading:
        """Clase placeholder para MultiTimeframePaperTrading"""
        
        def __init__(self):
            self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
            self.timeframes = ['1m', '5m', '15m', '1h']
        
        async def initialize(self):
            return True
        
        async def analyze_symbol(self, symbol: str) -> Optional[MultiTimeframeSignal]:
            # Análisis simulado
            import random
            
            actions = ['BUY', 'SELL', 'HOLD']
            action = random.choice(actions)
            
            return MultiTimeframeSignal(
                symbol=symbol,
                action=action,
                confidence=random.uniform(0.5, 0.9),
                strength=random.uniform(0.4, 0.8),
                timeframe_signals={tf: action for tf in self.timeframes},
                risk_level=random.choice(['LOW', 'MEDIUM', 'HIGH']),
                entry_price=random.uniform(100, 110000),
                stop_loss=random.uniform(90, 100000),
                take_profit=random.uniform(110, 120000),
                timestamp=datetime.now()
            )
        
        def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
            """Agregar indicadores técnicos básicos"""
            try:
                # RSI
                df['rsi'] = self._calculate_rsi(df['close'])
                
                # MACD
                df['macd'], df['macd_signal'] = self._calculate_macd(df['close'])
                
                # Bollinger Bands
                df['bb_upper'], df['bb_middle'], df['bb_lower'] = self._calculate_bollinger_bands(df['close'])
                
                # Moving Averages
                df['sma_20'] = df['close'].rolling(window=20).mean()
                df['ema_12'] = df['close'].ewm(span=12).mean()
                
                # Volume indicators
                df['volume_sma'] = df['volume'].rolling(window=20).mean()
                df['volume_ratio'] = df['volume'] / df['volume_sma']
                
                return df
                
            except Exception as e:
                logger.warning(f"⚠️ Error agregando indicadores técnicos: {e}")
                return df
        
        def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
            """Calcula RSI"""
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))
        
        def _calculate_macd(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series]:
            """Calcula MACD"""
            ema_12 = prices.ewm(span=12).mean()
            ema_26 = prices.ewm(span=26).mean()
            macd = ema_12 - ema_26
            signal = macd.ewm(span=9).mean()
            return macd, signal
        
        def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20) -> Tuple[pd.Series, pd.Series, pd.Series]:
            """Calcula Bollinger Bands"""
            sma = prices.rolling(window=period).mean()
            std = prices.rolling(window=period).std()
            upper = sma + (std * 2)
            lower = sma - (std * 2)
            return upper, sma, lower

@dataclass
class MLPrediction:
    """Predicción de modelo ML"""
    symbol: str
    timeframe: str
    prediction: float
    confidence: float
    model_name: str
    timestamp: datetime

@dataclass
class IntegratedSignal:
    """Señal integrada multi-timeframe + ML"""
    symbol: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float
    strength: float
    timeframe_consensus: Dict[str, str]
    ml_predictions: List[MLPrediction]
    risk_level: str
    entry_price: float
    stop_loss: float
    take_profit: float
    timestamp: datetime

class MLModelManager:
    """Gestor de modelos ML entrenados"""
    
    def __init__(self, models_dir: str):
        """Inicializar gestor de modelos"""
        self.models_dir = Path(models_dir)
        self.loaded_models = {}
        self.model_metadata = {}
        
        self._load_latest_models()
    
    def _load_latest_models(self):
        """Cargar los modelos más recientes"""
        logger.info("🤖 Cargando modelos ML entrenados...")
        
        try:
            # Buscar archivos de modelos más recientes
            model_files = list(self.models_dir.glob("multi_timeframe_*.joblib"))
            
            if not model_files:
                logger.warning("⚠️ No se encontraron modelos entrenados")
                return
            
            # Agrupar por tipo de modelo
            model_types = {}
            for file in model_files:
                # Extraer tipo de modelo del nombre
                parts = file.stem.split('_')
                if len(parts) >= 4:
                    model_type = '_'.join(parts[2:-1])  # Excluir 'multi_timeframe' y timestamp
                    timestamp = parts[-1]
                    
                    if model_type not in model_types:
                        model_types[model_type] = []
                    model_types[model_type].append((file, timestamp))
            
            # Cargar el modelo más reciente de cada tipo
            for model_type, files in model_types.items():
                # Ordenar por timestamp y tomar el más reciente
                latest_file = max(files, key=lambda x: x[1])[0]
                
                try:
                    model_data = joblib.load(latest_file)
                    self.loaded_models[model_type] = model_data
                    logger.info(f"✅ Modelo cargado: {model_type} (accuracy: {model_data.get('accuracy', 'N/A'):.4f})")
                    
                except Exception as e:
                    logger.error(f"❌ Error cargando modelo {model_type}: {e}")
            
            # Cargar metadatos
            self._load_metadata()
            
        except Exception as e:
            logger.error(f"❌ Error cargando modelos: {e}")
    
    def _load_metadata(self):
        """Cargar metadatos de modelos"""
        try:
            metadata_files = list(self.models_dir.glob("multi_timeframe_metadata_*.json"))
            if metadata_files:
                latest_metadata = max(metadata_files, key=lambda x: x.stat().st_mtime)
                with open(latest_metadata, 'r') as f:
                    self.model_metadata = json.load(f)
                logger.info(f"✅ Metadatos cargados: {latest_metadata}")
        except Exception as e:
            logger.warning(f"⚠️ Error cargando metadatos: {e}")
    
    def predict(self, features: np.ndarray, symbol: str, timeframe: str) -> List[MLPrediction]:
        """Realizar predicciones con todos los modelos cargados"""
        predictions = []
        
        for model_name, model_data in self.loaded_models.items():
            try:
                model = model_data['model']
                scaler = model_data['scaler']
                accuracy = model_data.get('accuracy', 0.5)
                
                # Escalar características
                features_scaled = scaler.transform(features.reshape(1, -1))
                
                # Realizar predicción
                prediction = model.predict_proba(features_scaled)[0]
                
                # Tomar probabilidad de clase positiva
                positive_prob = prediction[1] if len(prediction) > 1 else prediction[0]
                
                ml_pred = MLPrediction(
                    symbol=symbol,
                    timeframe=timeframe,
                    prediction=positive_prob,
                    confidence=accuracy,
                    model_name=model_name,
                    timestamp=datetime.now()
                )
                
                predictions.append(ml_pred)
                
            except Exception as e:
                logger.warning(f"⚠️ Error en predicción con {model_name}: {e}")
        
        return predictions
    
    def get_ensemble_prediction(self, features: np.ndarray, symbol: str, timeframe: str) -> Optional[MLPrediction]:
        """Obtener predicción ensemble de todos los modelos"""
        predictions = self.predict(features, symbol, timeframe)
        
        if not predictions:
            return None
        
        # Calcular predicción ponderada por accuracy
        weighted_sum = 0
        total_weight = 0
        
        for pred in predictions:
            weight = pred.confidence
            weighted_sum += pred.prediction * weight
            total_weight += weight
        
        if total_weight == 0:
            return None
        
        ensemble_prediction = weighted_sum / total_weight
        ensemble_confidence = total_weight / len(predictions)
        
        return MLPrediction(
            symbol=symbol,
            timeframe=timeframe,
            prediction=ensemble_prediction,
            confidence=ensemble_confidence,
            model_name="ensemble",
            timestamp=datetime.now()
        )

class IntegratedMultiTimeframePaperTrading:
    """Sistema integrado de paper trading multi-timeframe con ML"""
    
    def __init__(self, initial_capital: float = 10000.0):
        """Inicializar sistema integrado"""
        self.project_root = Path(__file__).parent.parent
        self.models_dir = self.project_root / "models"
        
        # Componentes principales
        self.paper_trading = None
        self.multi_timeframe = None
        self.ml_manager = None
        self.data_provider = None
        
        # Configuración
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
        self.timeframes = ['1m', '5m', '15m', '1h']
        self.initial_capital = initial_capital
        
        # Estado
        self.is_running = False
        self.last_signals = {}
        self.performance_metrics = {}
        
        logger.info("🚀 IntegratedMultiTimeframePaperTrading inicializado")
    
    async def initialize(self):
        """Inicializar todos los componentes"""
        logger.info("🔧 Inicializando componentes del sistema integrado...")
        
        try:
            # Inicializar paper trading engine
            self.paper_trading = PaperTradingEngine(initial_capital=self.initial_capital)
            
            # Inicializar multi-timeframe analysis
            self.multi_timeframe = MultiTimeframePaperTrading()
            await self.multi_timeframe.initialize()
            
            # Inicializar ML manager
            self.ml_manager = MLModelManager(str(self.models_dir))
            
            # Inicializar data provider
            self.data_provider = BinanceDataProvider()
            
            logger.info("✅ Todos los componentes inicializados correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando componentes: {e}")
            return False
    
    def extract_ml_features(self, df: pd.DataFrame) -> Optional[np.ndarray]:
        """Extraer características para modelos ML"""
        try:
            # Características esperadas por los modelos entrenados
            feature_cols = [
                'rsi', 'macd', 'macd_signal', 'bb_upper', 'bb_middle', 'bb_lower',
                'sma_20', 'ema_12', 'volume_ratio'
            ]
            
            # Verificar que las columnas existan
            available_cols = [col for col in feature_cols if col in df.columns]
            
            if len(available_cols) < 5:  # Mínimo de características
                logger.warning(f"⚠️ Pocas características disponibles: {len(available_cols)}")
                return None
            
            # Tomar la última fila (más reciente)
            latest_row = df[available_cols].iloc[-1]
            
            # Rellenar valores faltantes
            features = latest_row.fillna(0).values
            
            # Asegurar que tenemos exactamente 9 características
            if len(features) < 9:
                features = np.pad(features, (0, 9 - len(features)), 'constant')
            elif len(features) > 9:
                features = features[:9]
            
            return features
            
        except Exception as e:
            logger.warning(f"⚠️ Error extrayendo características ML: {e}")
            return None
    
    async def analyze_symbol_integrated(self, symbol: str) -> Optional[IntegratedSignal]:
        """Análisis integrado multi-timeframe + ML para un símbolo"""
        try:
            # 1. Obtener análisis multi-timeframe
            mt_signal = await self.multi_timeframe.analyze_symbol(symbol)
            
            if not mt_signal:
                return None
            
            # 2. Obtener datos para ML
            ml_predictions = []
            
            for timeframe in self.timeframes:
                try:
                    # Obtener datos históricos
                    df = self.data_provider.get_historical_data(
                        symbol=symbol,
                        interval=timeframe,
                        limit=100
                    )
                    
                    if df is not None and not df.empty:
                        # Agregar indicadores técnicos
                        df = self.multi_timeframe._add_technical_indicators(df)
                        
                        # Extraer características
                        features = self.extract_ml_features(df)
                        
                        if features is not None:
                            # Obtener predicción ML
                            ensemble_pred = self.ml_manager.get_ensemble_prediction(
                                features, symbol, timeframe
                            )
                            
                            if ensemble_pred:
                                ml_predictions.append(ensemble_pred)
                
                except Exception as e:
                    logger.warning(f"⚠️ Error en ML para {symbol}_{timeframe}: {e}")
            
            # 3. Combinar señales multi-timeframe y ML
            integrated_signal = self._combine_signals(mt_signal, ml_predictions)
            
            return integrated_signal
            
        except Exception as e:
            logger.error(f"❌ Error en análisis integrado para {symbol}: {e}")
            return None
    
    def _combine_signals(self, mt_signal: MultiTimeframeSignal, 
                        ml_predictions: List[MLPrediction]) -> IntegratedSignal:
        """Combinar señales multi-timeframe y ML"""
        
        # Calcular confianza ML promedio
        ml_confidence = 0
        ml_prediction_avg = 0.5
        
        if ml_predictions:
            ml_confidence = np.mean([pred.confidence for pred in ml_predictions])
            ml_prediction_avg = np.mean([pred.prediction for pred in ml_predictions])
        
        # Combinar señales
        # Peso 60% multi-timeframe, 40% ML
        mt_weight = 0.6
        ml_weight = 0.4
        
        # Convertir acción MT a score
        mt_score = 0.5  # Neutral por defecto
        if mt_signal.action == 'BUY':
            mt_score = 0.8
        elif mt_signal.action == 'SELL':
            mt_score = 0.2
        
        # Calcular score combinado
        combined_score = (mt_score * mt_weight) + (ml_prediction_avg * ml_weight)
        
        # Determinar acción final
        if combined_score > 0.65:
            final_action = 'BUY'
        elif combined_score < 0.35:
            final_action = 'SELL'
        else:
            final_action = 'HOLD'
        
        # Calcular confianza combinada
        combined_confidence = (mt_signal.confidence * mt_weight) + (ml_confidence * ml_weight)
        
        # Calcular strength combinada
        combined_strength = (mt_signal.strength * mt_weight) + (ml_prediction_avg * ml_weight)
        
        return IntegratedSignal(
            symbol=mt_signal.symbol,
            action=final_action,
            confidence=combined_confidence,
            strength=combined_strength,
            timeframe_consensus=mt_signal.timeframe_signals,
            ml_predictions=ml_predictions,
            risk_level=mt_signal.risk_level,
            entry_price=mt_signal.entry_price,
            stop_loss=mt_signal.stop_loss,
            take_profit=mt_signal.take_profit,
            timestamp=datetime.now()
        )
    
    async def execute_integrated_trade(self, signal: IntegratedSignal):
        """Ejecutar trade basado en señal integrada"""
        try:
            if signal.action == 'HOLD':
                return
            
            # Determinar cantidad basada en confianza y riesgo
            risk_multiplier = {
                'LOW': 0.02,    # 2% del capital
                'MEDIUM': 0.015, # 1.5% del capital
                'HIGH': 0.01     # 1% del capital
            }
            
            position_size = self.paper_trading.capital * risk_multiplier.get(signal.risk_level, 0.01)
            quantity = position_size / signal.entry_price
            
            # Crear orden
            order_type = OrderType.MARKET
            
            # Ejecutar orden
            order = self.paper_trading.place_order(
                symbol=signal.symbol,
                side=signal.action.lower(),
                order_type=order_type,
                quantity=quantity,
                price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit
            )
            
            if order:
                logger.info(f"✅ Orden ejecutada: {signal.symbol} {signal.action} "
                          f"Cantidad: {quantity:.6f} Precio: ${signal.entry_price:.2f} "
                          f"Confianza: {signal.confidence:.2f}")
                
                # Guardar señal para tracking
                self.last_signals[signal.symbol] = signal
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando trade para {signal.symbol}: {e}")
    
    async def monitoring_loop(self):
        """Loop principal de monitoreo"""
        logger.info("🔄 Iniciando loop de monitoreo integrado...")
        
        self.is_running = True
        iteration = 0
        
        while self.is_running:
            try:
                iteration += 1
                logger.info(f"📊 Iteración {iteration} - Análisis integrado multi-timeframe + ML")
                
                # Analizar todos los símbolos
                for symbol in self.symbols:
                    try:
                        # Obtener señal integrada
                        signal = await self.analyze_symbol_integrated(symbol)
                        
                        if signal:
                            logger.info(f"🎯 {symbol}: {signal.action} "
                                      f"(Confianza: {signal.confidence:.2f}, "
                                      f"Strength: {signal.strength:.2f}, "
                                      f"ML Predictions: {len(signal.ml_predictions)})")
                            
                            # Ejecutar trade si es necesario
                            await self.execute_integrated_trade(signal)
                        
                        # Pequeña pausa entre símbolos
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"❌ Error analizando {symbol}: {e}")
                
                # Mostrar estado del portfolio
                self._log_portfolio_status()
                
                # Pausa entre iteraciones (5 minutos)
                logger.info("⏳ Esperando próxima iteración...")
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"❌ Error en loop de monitoreo: {e}")
                await asyncio.sleep(60)  # Pausa más corta en caso de error
    
    def _log_portfolio_status(self):
        """Mostrar estado del portfolio"""
        try:
            portfolio = self.paper_trading.get_portfolio_summary()
            
            logger.info(f"💰 Portfolio - Capital: ${portfolio['total_value']:.2f} "
                       f"P&L: ${portfolio['unrealized_pnl']:.2f} "
                       f"({portfolio['total_return_pct']:.2f}%) "
                       f"Posiciones: {len(portfolio['positions'])}")
            
        except Exception as e:
            logger.warning(f"⚠️ Error mostrando estado del portfolio: {e}")
    
    def stop_monitoring(self):
        """Detener monitoreo"""
        logger.info("🛑 Deteniendo monitoreo integrado...")
        self.is_running = False
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Obtener reporte de rendimiento"""
        try:
            portfolio = self.paper_trading.get_portfolio_summary()
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'portfolio': portfolio,
                'last_signals': {symbol: {
                    'action': signal.action,
                    'confidence': signal.confidence,
                    'strength': signal.strength,
                    'ml_predictions_count': len(signal.ml_predictions),
                    'timestamp': signal.timestamp.isoformat()
                } for symbol, signal in self.last_signals.items()},
                'ml_models_loaded': list(self.ml_manager.loaded_models.keys()) if self.ml_manager else [],
                'symbols_monitored': self.symbols,
                'timeframes_analyzed': self.timeframes
            }
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte: {e}")
            return {}

async def main():
    """Función principal"""
    logger.info("=" * 80)
    logger.info("🚀 SICAR - Sistema Integrado Multi-Timeframe + ML Paper Trading")
    logger.info("=" * 80)
    
    # Crear sistema integrado
    integrated_system = IntegratedMultiTimeframePaperTrading(initial_capital=10000.0)
    
    # Inicializar
    if not await integrated_system.initialize():
        logger.error("❌ Error inicializando sistema")
        return
    
    try:
        # Iniciar monitoreo
        await integrated_system.monitoring_loop()
        
    except KeyboardInterrupt:
        logger.info("⏹️ Detenido por usuario")
    except Exception as e:
        logger.error(f"❌ Error en sistema: {e}")
    finally:
        integrated_system.stop_monitoring()
        
        # Mostrar reporte final
        report = integrated_system.get_performance_report()
        logger.info("📊 Reporte final:")
        logger.info(json.dumps(report, indent=2, default=str))
    
    logger.info("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())