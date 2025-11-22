#!/usr/bin/env python3
"""
Módulo de integración PatchTST con SICAR
Conecta las predicciones de PatchTST con el sistema de decisiones de trading
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# Agregar directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.module_patchtst import PatchTST, PatchTSTConfig
from src.crypto_data_loader import CryptoDataLoader
from src.market_sentiment import MarketSentimentAnalyzer
from src.breakout_validator import BreakoutValidator

logger = logging.getLogger(__name__)

class PatchTSTIntegration:
    """
    Integrador de PatchTST con el sistema SICAR
    """
    
    def __init__(self, symbol: str = "BTC-USD"):
        self.symbol = symbol
        self.patchtst = None
        self.data_loader = CryptoDataLoader(symbol, "1h")  # Inicializar data_loader
        self.sentiment_analyzer = MarketSentimentAnalyzer()  # Analizador de sentimiento
        self.breakout_validator = BreakoutValidator()  # Validador de rupturas anti-fakeout
        self.model_path = f"models/patchtst_{symbol.replace('-', '_')}.pth"
        self.is_initialized = False
        
        logger.info(f"Integración PatchTST inicializada para {symbol}")
    
    def initialize_model(self, 
                        load_pretrained: bool = True,
                        force_retrain: bool = False) -> bool:
        """
        Inicializar el modelo PatchTST
        
        Args:
            load_pretrained: Cargar modelo pre-entrenado si existe
            force_retrain: Forzar re-entrenamiento
            
        Returns:
            True si la inicialización fue exitosa
        """
        logger.info("Inicializando modelo PatchTST")
        
        try:
            # Configuración optimizada para criptomonedas
            config = PatchTSTConfig(
                seq_len=512,      # 512 horas de historia
                pred_len=96,      # 96 horas de predicción
                patch_len=16,     # Patches de 16 horas
                stride=8,         # Overlap de 50%
                d_model=256,      # Modelo más grande para cripto
                n_heads=16,       # Más atención para patrones complejos
                e_layers=4,       # 4 capas encoder
                d_ff=1024,        # Feedforward más grande
                dropout=0.1,
                learning_rate=1e-4,
                batch_size=16,
                epochs=20         # Más épocas para mejor precisión
            )
            
            self.patchtst = PatchTST(config)
            self.data_loader = CryptoDataLoader(self.symbol)
            
            # Intentar cargar modelo pre-entrenado
            if load_pretrained and os.path.exists(self.model_path) and not force_retrain:
                logger.info("Cargando modelo pre-entrenado")
                try:
                    self.patchtst.load_model(self.model_path)
                    self.is_initialized = True
                    return True
                except Exception as e:
                    logger.warning(f"Fallo cargando modelo, reentrenando: {e}")
            
            # Entrenar nuevo modelo
            logger.info("Entrenando nuevo modelo PatchTST")
            success = self._train_model()
            
            if success:
                self.is_initialized = True
                logger.info("Modelo PatchTST entrenado exitosamente")
            
            return success
            
        except Exception as e:
            logger.error(f"Error inicializando modelo: {e}")
            return False
    
    def _train_model(self) -> bool:
        """Entrenar el modelo con datos históricos"""
        logger.info("Iniciando entrenamiento de PatchTST")
        
        try:
            # Inicializar modelo si no existe
            if self.patchtst is None:
                logger.info("Inicializando modelo PatchTST...")
                
                # Configuración optimizada para criptomonedas
                config = PatchTSTConfig(
                    seq_len=96,          # 96 horas de historia (reducido para pruebas)
                    pred_len=1,          # Predecir 1 hora adelante
                    e_layers=2,          # 2 capas de transformer
                    n_heads=8,           # 8 cabezas de atención
                    d_model=128,         # Dimensión del modelo
                    d_ff=256,            # Dimensión feed-forward (reducido)
                    dropout=0.1,         # Dropout para regularización
                    patch_len=16,        # Longitud de cada patch
                    stride=8,            # Paso entre patches
                    epochs=3,            # Épocas de entrenamiento (reducido para pruebas rápidas)
                    batch_size=16,       # Tamaño de batch
                    learning_rate=0.001  # Tasa de aprendizaje
                )
                
                self.patchtst = PatchTST(config)
                logger.info("Modelo PatchTST inicializado exitosamente")
            
            # Obtener datos históricos con ventana optimizada
            # 90 días para momentum/tendencia (rápida adaptación)
            dataset = self.data_loader.prepare_training_data(days_back=90)
            
            # Obtener niveles estructurales con datos históricos completos (365 días)
            structural_levels = self.data_loader.get_structural_levels(days_back=365)
            logger.info(f"Niveles estructurales: Soporte {structural_levels['support_levels']}, Resistencia {structural_levels['resistance_levels']}")
            
            if len(dataset['train']) < 1000:  # Mínimo de datos
                logger.warning("Datos insuficientes para entrenamiento")
                return False
            
            # Preparar datos para PatchTST
            train_data = dataset['train']
            val_data = dataset['validation']
            
            # Almacenar niveles estructurales para uso en predicciones
            self.structural_levels = structural_levels
            
            # Entrenar modelo
            logger.info(f"Entrenando con {len(train_data)} registros")
            logger.info(f"Ventana optimizada: 90 días para momentum | Estructural: 365 días para soportes/resistencias")
            
            # Preparar datos para entrenamiento (formato para PatchTST)
            # PatchTST espera: (batch_size, seq_len, n_features)
            n_features = 5  # HUFL, HULL, MUFL, LUFL, LULL
            seq_len = 96    # Longitud de secuencia para PatchTST (96 horas)
            
            # Preparar datos de entrenamiento
            X_train_list = []
            y_train_list = []
            
            for i in range(len(train_data) - seq_len):
                # Tomar ventana de 96 horas
                X_window = train_data.iloc[i:i+seq_len][['HUFL', 'HULL', 'MUFL', 'LUFL', 'LULL']].values
                y_window = train_data.iloc[i+seq_len]['OT']  # Predicción de la siguiente hora
                
                X_train_list.append(X_window)
                y_train_list.append(y_window)
            
            X_train = np.array(X_train_list)
            y_train = np.array(y_train_list)
            
            # Preparar datos de validación
            X_val_list = []
            y_val_list = []
            
            for i in range(len(val_data) - seq_len):
                X_window = val_data.iloc[i:i+seq_len][['HUFL', 'HULL', 'MUFL', 'LUFL', 'LULL']].values
                y_window = val_data.iloc[i+seq_len]['OT']
                
                X_val_list.append(X_window)
                y_val_list.append(y_window)
            
            X_val = np.array(X_val_list)
            y_val = np.array(y_val_list)
            
            # Entrenar modelo real
            train_losses, val_losses = self.patchtst.train(X_train, y_train)
            
            # Guardar modelo
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            self.patchtst.save_model(self.model_path)
            
            logger.info("Entrenamiento completado")
            self.is_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Error en entrenamiento: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_prediction_signal(self, 
                                 current_data: Optional[pd.DataFrame] = None,
                                 current_price: Optional[float] = None) -> Dict[str, Any]:
        """
        Generar señal de trading basada en predicción PatchTST
        
        Returns:
            Dict con señal, confianza y análisis
        """
        if not self.is_initialized:
            return {"error": "Modelo no inicializado"}
        
        try:
            # Obtener datos actuales si no se proporcionan
            if current_data is None:
                current_data = self.data_loader.get_binance_data(limit=1000)
            
            if current_price is None:
                current_price = current_data['close'].iloc[-1]
            
            # Generar features ETTh1 y usar scaler para desnormalizar
            enriched = self.data_loader.calculate_technical_indicators(current_data)
            patch_features = self.data_loader.create_patchtst_features(enriched)
            scalers = getattr(self.data_loader, 'scalers', None)
            close_scaler = scalers.get('close') if scalers else None
            if close_scaler:
                prediction_result = self.patchtst.generate_trading_signals_from_features(
                    patch_features, close_scaler, current_price
                )
            else:
                prediction_result = self.patchtst.generate_trading_signals(
                    current_data, current_price
                )
            
            # Enriquecer con análisis adicional
            enriched_result = self._enrich_prediction(prediction_result, current_data)
            
            logger.info(f"Señal generada: {enriched_result['signal']} "
                       f"(confianza: {enriched_result['confidence']:.2%})")
            
            return enriched_result
            
        except Exception as e:
            logger.error(f"Error generando señal: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Error generando señal: {e}"}
    
    def generate_signal(self) -> Dict[str, Any]:
        """
        Método público para generar señal de trading (wrapper para compatibilidad)
        """
        return self.generate_prediction_signal()
    
    def _save_breakout_validation(self, enriched_result: Dict):
        """Guardar validación de rupturas en archivo JSON para el servidor web"""
        try:
            import json
            import os
            from datetime import datetime
            
            # Extraer información de validación de rupturas
            breakout_data = enriched_result.get('breakout_validation', {})
            if not breakout_data:
                return
            
            # Preparar datos para guardar
            save_data = {
                "status": breakout_data.get('status', 'UNKNOWN'),
                "confidence": breakout_data.get('confidence', 0.0),
                "factors": breakout_data.get('factors', {}),
                "warnings": breakout_data.get('warnings', []),
                "recommendation": breakout_data.get('recommendation', ''),
                "breakout_factor": breakout_data.get('breakout_factor', 1.0),
                "symbol": self.symbol,
                "timestamp": datetime.now().isoformat(),
                "level_tested": enriched_result.get('market_conditions', {}).get('resistance_level') or 
                                enriched_result.get('market_conditions', {}).get('support_level'),
                "current_price": enriched_result.get('market_conditions', {}).get('current_price', 0),
                "breakout_type": "BULLISH" if enriched_result.get('signal') == 'BUY' else "BEARISH",
                "total_score": breakout_data.get('total_score', 0),
                "validation_threshold": breakout_data.get('validation_threshold', 4),
                "is_valid": breakout_data.get('is_valid', False)
            }
            
            # Crear directorio de reportes si no existe
            reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            # Guardar archivo específico para el símbolo
            filename = f"breakout_validation_{self.symbol.replace('-', '_')}.json"
            filepath = os.path.join(reports_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(save_data, f, indent=2)
            
            logger.info(f"✅ Validación de rupturas guardada: {filepath}")
            
            # También guardar archivo por defecto
            default_filepath = os.path.join(reports_dir, 'breakout_validation.json')
            with open(default_filepath, 'w') as f:
                json.dump(save_data, f, indent=2)
            
            logger.info(f"✅ Validación de rupturas (default) guardada: {default_filepath}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando validación de rupturas: {e}")
    
    def _enrich_prediction(self, prediction: Dict, data: pd.DataFrame) -> Dict:
        """Enriquecer predicción con análisis adicional incluyendo niveles estructurales"""
        
        # Precio actual para todos los análisis
        current_price = data['close'].iloc[-1]
        
        # Análisis de tendencia con ventana optimizada (90 días)
        recent_data = data.tail(72)  # Últimas 72 horas para momentum rápido
        trend_slope = np.polyfit(range(len(recent_data)), recent_data['close'], 1)[0]
        
        # Volatilidad reciente
        recent_volatility = recent_data['close'].pct_change().std() * np.sqrt(24)  # Anualizada
        
        # Análisis estructural (usando niveles de 365 días)
        structural_analysis = {}
        if hasattr(self, 'structural_levels'):
            levels = self.structural_levels
            
            # Calcular distancia a soportes/resistencias clave
            if levels['support_levels']:
                nearest_support = max([s for s in levels['support_levels'] if s < current_price], default=None)
                support_distance = ((current_price - nearest_support) / current_price * 100) if nearest_support else None
            else:
                nearest_support = None
                support_distance = None
                
            if levels['resistance_levels']:
                nearest_resistance = min([r for r in levels['resistance_levels'] if r > current_price], default=None)
                resistance_distance = ((nearest_resistance - current_price) / current_price * 100) if nearest_resistance else None
            else:
                nearest_resistance = None
                resistance_distance = None
            
            structural_analysis = {
                'nearest_support': nearest_support,
                'nearest_resistance': nearest_resistance,
                'support_distance_pct': support_distance,
                'resistance_distance_pct': resistance_distance,
                'structural_volatility': levels.get('structural_volatility', 0),
                'price_vs_range': ((current_price - levels['min_price']) / (levels['max_price'] - levels['min_price'])) * 100
            }
            
            logger.info(f"Análisis estructural: Soporte {nearest_support} ({support_distance:.2f}% dist), Resistencia {nearest_resistance} ({resistance_distance:.2f}% dist)")
        
        # Volumen promedio
        avg_volume = recent_data['volume'].mean()
        current_volume = recent_data['volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # ANÁLISIS DE SENTIMIENTO DEL MERCADO
        sentiment_analysis = self.sentiment_analyzer.get_combined_sentiment_score(self.symbol)
        sentiment_score = sentiment_analysis.get('sentiment_score', 0)
        sentiment_classification = sentiment_analysis.get('sentiment_classification', 'NEUTRAL')
        
        logger.info(f"Análisis de sentimiento: {sentiment_classification} (score: {sentiment_score:.3f})")
        
        # ANÁLISIS ATR DINÁMICO - CRÍTICO PARA FILTROS DE SENSIBILIDAD
        atr_analysis = self.data_loader.get_atr_analysis(data, current_price)
        volatility_level = atr_analysis.get('volatility_level', 'NORMAL')
        volatility_factor_atr = atr_analysis.get('volatility_factor', 1.0)
        current_atr_percent = atr_analysis.get('current_atr_percent', 0)
        
        logger.info(f"Análisis ATR: {volatility_level} volatility ({current_atr_percent:.2f}%), factor: {volatility_factor_atr}")
        
        # VALIDACIÓN DE RUPTURAS ANTI-FAKEOUT - OPTIMIZACIÓN #5
        breakout_validation = None
        sentiment_data_for_validation = {
            'combined_score': sentiment_score,
            'extreme_fear_signal': sentiment_analysis.get('extreme_fear_signal', False),
            'extreme_greed_signal': sentiment_analysis.get('extreme_greed_signal', False)
        }
        
        # Validar ruptura usando el sistema completo de 6 factores
        breakout_result = self.breakout_validator.validate_breakout(
            data=data,
            signal_type=prediction['signal'],
            current_price=current_price,
            sentiment_data=sentiment_data_for_validation,
            structural_levels=self.structural_levels if hasattr(self, 'structural_levels') else None
        )
        breakout_validation = breakout_result
        logger.info(f"Validación ruptura: {breakout_result['status']} (score: {breakout_result['total_score']}/{breakout_result['validation_threshold']})")
        
        # Ajustar confianza basado en condiciones de mercado
        base_confidence = prediction['confidence']
        
        # Factor de tendencia
        trend_factor = 1.0
        if prediction['signal'] == 'BUY' and trend_slope > 0:
            trend_factor = 1.1  # Reforzar señal alcista en tendencia alcista
        elif prediction['signal'] == 'SELL' and trend_slope < 0:
            trend_factor = 1.1  # Reforzar señal bajista en tendencia bajista
        elif (prediction['signal'] == 'BUY' and trend_slope < 0) or \
             (prediction['signal'] == 'SELL' and trend_slope > 0):
            trend_factor = 0.9  # Reducir confianza en señales contratendencia
        
        # Factor de volatilidad
        vol_factor = 1.0
        if recent_volatility < 0.02:  # Baja volatilidad
            vol_factor = 1.05  # Mayor confianza en mercados estables
        elif recent_volatility > 0.05:  # Alta volatilidad
            vol_factor = 0.85  # Menor confianza en mercados volátiles
        
        # Factor de volumen
        volume_factor = min(volume_ratio, 1.5)  # Máx 50% boost
        
        # Factor de sentimiento - CRÍTICO PARA EVITAR SEÑALES EN MERCADOS DE MIEDO EXTREMO
        sentiment_factor = 1.0
        if sentiment_analysis.get('signals'):
            signals = sentiment_analysis['signals']
            
            # REDUCIR drásticamente confianza en miedo extremo
            if 'EXTREME_FEAR' in signals:
                sentiment_factor = 0.5  # Reducir 50% la confianza en miedo extremo
                logger.warning(f"🚨 MIEDO EXTREMO DETECTADO (F&G: {sentiment_analysis['fear_greed']['current_value']}) - Reduciendo confianza al 50%")
            
            # Ajustar según sentimiento vs dirección de señal
            if prediction['signal'] == 'BUY' and sentiment_score < -0.5:
                sentiment_factor *= 0.7  # No comprar en sentimiento muy bajista
                logger.info(f"🔴 Señal BUY en sentimiento bajista - Reduciendo confianza")
            elif prediction['signal'] == 'SELL' and sentiment_score > 0.5:
                sentiment_factor *= 0.7  # No vender en sentimiento muy alcista
                logger.info(f"🟢 Señal SELL en sentimiento alcista - Reduciendo confianza")
        
        # Aplicar factores (incluyendo ATR dinámico)
        adjusted_confidence = base_confidence * trend_factor * vol_factor * volume_factor * sentiment_factor * volatility_factor_atr
        
        # Aplicar validación de ruptura anti-fakeout
        breakout_factor = 1.0
        breakout_summary = None
        if breakout_validation:
            if breakout_validation['is_valid']:
                breakout_factor = 1.0  # Ruptura válida, no reducir confianza
                logger.info(f"✅ Ruptura VALIDADA - Factor: {breakout_factor:.2f}")
            else:
                breakout_factor = 0.5  # Ruptura inválida, reducir confianza drásticamente
                logger.warning(f"🚨 Ruptura FAKEOUT detectada - Factor: {breakout_factor:.2f}")
                # Agregar advertencia al análisis
                if 'warnings' not in prediction:
                    prediction['warnings'] = []
                prediction['warnings'].append("Ruptura potencialmente falsa detectada")
            
            breakout_summary = self.breakout_validator.get_validation_summary()
        
        adjusted_confidence *= breakout_factor
        
        # Filtro anti-fakeout basado en niveles estructurales (mantener como respaldo)
        if structural_analysis and prediction['signal'] == 'BUY':
            # Si el precio está cerca de resistencia (>5% debajo), reducir confianza
            if structural_analysis.get('resistance_distance_pct') and structural_analysis['resistance_distance_pct'] < 5:
                adjusted_confidence *= 0.7  # Reducir drásticamente confianza en resistencias
                logger.info(f"Filtro anti-fakeout activado: Resistencia cercana a {structural_analysis['resistance_distance_pct']:.2f}%")
            
            # Si el precio está lejos de soporte (>15% encima), reducir confianza
            if structural_analysis.get('support_distance_pct') and structural_analysis['support_distance_pct'] > 15:
                adjusted_confidence *= 0.8  # Reducir confianza - posible sobrecompra
                logger.info(f"Filtro de sobrecompra activado: Lejos de soporte {structural_analysis['support_distance_pct']:.2f}%")
        
        adjusted_confidence = min(adjusted_confidence, 0.95)  # Máx 95%
        
        # Análisis de riesgo
        risk_analysis = self._calculate_risk_metrics(data, prediction)
        
        enriched_result = {
            **prediction,
            'confidence': adjusted_confidence,
            'market_conditions': {
                'trend_slope': float(trend_slope),
                'recent_volatility': float(recent_volatility),
                'volume_ratio': float(volume_ratio),
                'avg_volume_24h': float(avg_volume),
                **structural_analysis,  # Incluir análisis estructural
                'sentiment_score': float(sentiment_score),
                'sentiment_classification': sentiment_classification,
                'sentiment_factor': float(sentiment_factor),
                **atr_analysis  # Incluir análisis ATR dinámico completo
            },
            'risk_analysis': risk_analysis,
            'recommendation': self._generate_enhanced_recommendation(
                prediction['signal'], adjusted_confidence, risk_analysis, structural_analysis, sentiment_analysis, atr_analysis
            ),
            'breakout_validation': {
                'summary': breakout_summary,
                'validation': breakout_validation,
                'breakout_factor': breakout_factor
            } if breakout_validation else None,
            'model_info': {
                'model': 'PatchTST',
                'prediction_horizon': '96 horas',
                'last_update': datetime.now().isoformat(),
                'symbol': self.symbol,
                'training_window': '90 días (momentum) + 365 días (estructural)',
                'filters_applied': ['anti_fakeout', 'structural_levels', 'trend_confirmation', 'sentiment_analysis', 'atr_dynamic_filters', 'breakout_validation'],
                'sentiment_data': sentiment_analysis,  # Incluir datos completos de sentimiento
                'atr_analysis': atr_analysis,  # Incluir análisis ATR dinámico
                'breakout_validation_applied': breakout_validation is not None
            }
        }
        
        # Guardar validación de rupturas en archivo para el servidor web
        self._save_breakout_validation(enriched_result)
        
        return enriched_result
    
    def _calculate_risk_metrics(self, data: pd.DataFrame, prediction: Dict) -> Dict:
        """Calcular métricas de riesgo"""
        
        # VaR (Value at Risk) simple
        returns = data['close'].pct_change().dropna()
        var_95 = np.percentile(returns, 5)  # 5% VaR
        
        # Máxima caída (Drawdown)
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Sharpe ratio simple
        mean_return = returns.mean()
        volatility = returns.std()
        sharpe = mean_return / volatility if volatility > 0 else 0
        
        # Análisis de soporte/resistencia
        support_level = data['low'].tail(48).min()  # Mínimo de últimas 48h
        resistance_level = data['high'].tail(48).max()  # Máximo de últimas 48h
        current_price = data['close'].iloc[-1]
        
        # Calcular distancias
        support_distance = (current_price - support_level) / current_price * 100
        resistance_distance = (resistance_level - current_price) / current_price * 100
        
        risk_score = self._calculate_risk_score(var_95, max_drawdown, sharpe)
        
        return {
            'var_95': float(var_95),
            'max_drawdown': float(max_drawdown),
            'sharpe_ratio': float(sharpe),
            'support_level': float(support_level),
            'resistance_level': float(resistance_level),
            'support_distance_pct': float(support_distance),
            'resistance_distance_pct': float(resistance_distance),
            'risk_score': risk_score,  # 0-10, mayor es más riesgoso
            'risk_level': self._get_risk_level(risk_score)
        }
    
    def _calculate_risk_score(self, var_95: float, max_drawdown: float, sharpe: float) -> float:
        """Calcular score de riesgo (0-10)"""
        
        # VaR component (0-4 puntos)
        var_score = min(abs(var_95) * 100, 4.0)
        
        # Drawdown component (0-4 puntos)  
        dd_score = min(abs(max_drawdown) * 100, 4.0)
        
        # Sharpe component (0-2 puntos)
        sharpe_score = max(0, (0.5 - sharpe) * 2) if sharpe < 0.5 else 0
        
        return var_score + dd_score + sharpe_score
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Obtener nivel de riesgo"""
        if risk_score < 3:
            return "LOW"
        elif risk_score < 6:
            return "MEDIUM"
        elif risk_score < 8:
            return "HIGH"
        else:
            return "VERY_HIGH"
    
    def _generate_enhanced_recommendation(self, signal: str, confidence: float, risk_analysis: Dict, structural_analysis: Dict = None, sentiment_analysis: Dict = None, atr_analysis: Dict = None) -> str:
        """Generar recomendación mejorada con análisis estructural, sentimiento y ATR dinámico"""
        
        base_rec = f"Señal {signal} con {confidence:.1%} confianza."
        
        # Agregar análisis de riesgo
        risk_level = risk_analysis['risk_level']
        risk_comment = f" Riesgo {risk_level.lower()}."
        
        # ANÁLISIS DE SENTIMIENTO - CRÍTICO
        sentiment_comment = ""
        if sentiment_analysis and sentiment_analysis.get('signals'):
            signals = sentiment_analysis['signals']
            sentiment_score = sentiment_analysis.get('sentiment_score', 0)
            
            # ADVERTENCIA DE MIEDO EXTREMO
            if 'EXTREME_FEAR' in signals:
                sentiment_comment = f" ⚠️ MIEDO EXTREMO (F&G: {sentiment_analysis['fear_greed']['current_value']}) - Evitar operaciones."
            
            # Señales de funding
            if 'HIGH_FUNDING' in signals:
                sentiment_comment += " 🔥 Funding alto - Posible corrección inminente."
            elif 'LOW_FUNDING' in signals:
                sentiment_comment += " 📉 Funding bajo - Posible rebote."
            
            # Alineación señal-sentimiento
            if signal == 'BUY' and sentiment_score < -0.5:
                sentiment_comment += " 🔴 Señal BUY en sentimiento bajista - ALTO RIESGO."
            elif signal == 'SELL' and sentiment_score > 0.5:
                sentiment_comment += " 🔴 Señal SELL en sentimiento alcista - ALTO RIESGO."
        
        # ANÁLISIS ATR DINÁMICO
        atr_comment = ""
        if atr_analysis:
            volatility_level = atr_analysis.get('volatility_level', 'NORMAL')
            current_atr_percent = atr_analysis.get('current_atr_percent', 0)
            volatility_trend = atr_analysis.get('volatility_trend', 'STABLE')
            
            # Comentario sobre nivel de volatilidad
            if volatility_level == "HIGH":
                atr_comment = f" 📊 ALTA volatilidad ({current_atr_percent:.2f}% ATR) - Reduciendo confianza."
            elif volatility_level == "LOW":
                atr_comment = f" 📊 BAJA volatilidad ({current_atr_percent:.2f}% ATR) - Aumentando confianza."
            
            # Comentario sobre tendencia de volatilidad
            if volatility_trend == "INCREASING":
                atr_comment += " Volatilidad CRECIENDO - Mayor riesgo."
            elif volatility_trend == "DECREASING":
                atr_comment += " Volatilidad DECRECIENDO - Menor riesgo."
            
            # Señales de breakout ATR
            breakout_signals = atr_analysis.get('breakout_signals', {})
            if breakout_signals.get('high_breakout'):
                atr_comment += " 🔥 Breakout ATR alcista detectado."
            if breakout_signals.get('low_breakout'):
                atr_comment += " 📉 Breakout ATR bajista detectado."
        
        # Análisis de soporte/resistencia con filtros mejorados
        level_comment = ""
        
        if signal == "BUY":
            # Filtro anti-fakeout: no comprar cerca de resistencia
            if structural_analysis and structural_analysis.get('resistance_distance_pct'):
                if structural_analysis['resistance_distance_pct'] < 5:
                    level_comment = f" ATENCIÓN: Resistencia cercana ({structural_analysis['resistance_distance_pct']:.1f}%) - Alto riesgo de fakeout."
                elif structural_analysis['resistance_distance_pct'] < 10:
                    level_comment = f" Resistencia a {structural_analysis['resistance_distance_pct']:.1f}% - Proceder con cautela."
            
            # Filtro de sobrecompra: no comprar lejos de soporte
            if structural_analysis and structural_analysis.get('support_distance_pct'):
                if structural_analysis['support_distance_pct'] > 15:
                    level_comment += f" Sobrecompra detectada: {structural_analysis['support_distance_pct']:.1f}% sobre soporte."
                elif structural_analysis['support_distance_pct'] < 3:
                    level_comment += " Cerca de soporte - buen punto de entrada."
                    
        elif signal == "SELL":
            if structural_analysis and structural_analysis.get('support_distance_pct'):
                if structural_analysis['support_distance_pct'] < 5:
                    level_comment = f" ATENCIÓN: Cerca de soporte ({structural_analysis['support_distance_pct']:.1f}%) - Posible rebote."
            
            if structural_analysis and structural_analysis.get('resistance_distance_pct'):
                if structural_analysis['resistance_distance_pct'] < 3:
                    level_comment += " Cerca de resistencia - buen punto de salida."
        
        # Si no hay comentarios específicos, agregar análisis general
        if not level_comment and structural_analysis:
            level_comment = " Análisis estructural aplicado."
        
        return base_rec + risk_comment + sentiment_comment + atr_comment + level_comment
    
    def analyze_risk(self, current_data: pd.DataFrame, current_price: float) -> Dict[str, Any]:
        """
        Analizar riesgo basado en datos actuales y precio actual
        
        Args:
            current_data: DataFrame con datos históricos
            current_price: Precio actual del activo
            
        Returns:
            Dict con análisis de riesgo completo
        """
        try:
            # Crear predicción temporal para el análisis de riesgo
            temp_prediction = {
                'signal': 'HOLD',  # Señal temporal, no usada en el análisis de riesgo
                'confidence': 0.5,
                'predicted_price_96h': current_price,
                'price_change_pct': 0.0
            }
            
            # Usar el método existente para calcular métricas de riesgo
            risk_metrics = self._calculate_risk_metrics(current_data, temp_prediction)
            
            # Enriquecer con análisis adicional
            enriched_analysis = {
                'risk_metrics': risk_metrics,
                'current_price': current_price,
                'price_volatility': current_data['close'].pct_change().std() * np.sqrt(24),
                'support_resistance': {
                    'support_level': risk_metrics['support_level'],
                    'resistance_level': risk_metrics['resistance_level'],
                    'support_distance_pct': risk_metrics['support_distance_pct'],
                    'resistance_distance_pct': risk_metrics['resistance_distance_pct']
                },
                'risk_assessment': {
                    'overall_risk': risk_metrics['risk_level'],
                    'risk_score': risk_metrics['risk_score'],
                    'recommendation': self._generate_enhanced_recommendation(
                        'HOLD', 0.5, risk_metrics
                    )
                },
                'market_conditions': {
                    'var_95': risk_metrics['var_95'],
                    'max_drawdown': risk_metrics['max_drawdown'],
                    'sharpe_ratio': risk_metrics['sharpe_ratio']
                }
            }
            
            return enriched_analysis
            
        except Exception as e:
            logger.error(f"Error en análisis de riesgo: {e}")
            return {
                'error': f"Error en análisis de riesgo: {e}",
                'risk_level': 'UNKNOWN',
                'risk_score': 5.0
            }

    def get_model_status(self) -> Dict[str, Any]:
        """Obtener estado del modelo"""
        return {
            'initialized': self.is_initialized,
            'symbol': self.symbol,
            'model_path': self.model_path,
            'model_exists': os.path.exists(self.model_path) if self.model_path else False,
            'last_training': datetime.fromtimestamp(os.path.getmtime(self.model_path)).isoformat() 
                           if os.path.exists(self.model_path) else None
        }

def demo_integration():
    """Demo de integración PatchTST con SICAR"""
    print("🚀 Demo de Integración PatchTST-SICAR")
    print("="*60)
    
    # Inicializar integración
    integration = PatchTSTIntegration("BTC-USD")
    
    # Inicializar modelo (usará modelo pre-entrenado si existe)
    success = integration.initialize_model(load_pretrained=True)
    
    if not success:
        print("❌ Error inicializando modelo")
        return
    
    # Generar señal de trading
    print("📊 Generando señal de trading...")
    signal = integration.generate_prediction_signal()
    
    if 'error' in signal:
        print(f"❌ Error: {signal['error']}")
        return
    
    # Mostrar resultados
    print(f"\n🎯 Resultados del Análisis PatchTST:")
    print(f"   💡 Señal: {signal['signal']}")
    print(f"   📈 Confianza: {signal['confidence']:.1%}")
    print(f"   💰 Precio actual: ${signal['current_price']:,.2f}")
    print(f"   🔮 Precio predicho (96h): ${signal['predicted_price_96h']:,.2f}")
    print(f"   📊 Cambio esperado: {signal['price_change_pct']:.1f}%")
    print(f"   ⚠️  Riesgo: {signal['risk_analysis']['risk_level']}")
    print(f"   📝 Recomendación: {signal['recommendation']}")
    
    # Detalles adicionales
    print(f"\n📋 Detalles del Modelo:")
    print(f"   🧠 Modelo: {signal['model_info']['model']}")
    print(f"   ⏰ Horizonte: {signal['model_info']['prediction_horizon']}")
    print(f"   🔄 Actualizado: {signal['model_info']['last_update']}")
    
    print(f"\n📊 Condiciones de Mercado:")
    market = signal['market_conditions']
    print(f"   📈 Pendiente de tendencia: {market['trend_slope']:.4f}")
    print(f"   ⚡ Volatilidad: {market['recent_volatility']:.2%}")
    print(f"   📊 Ratio de volumen: {market['volume_ratio']:.1f}x")
    
    print(f"\n⚠️  Análisis de Riesgo:")
    risk = signal['risk_analysis']
    print(f"   📉 VaR (95%): {risk['var_95']:.2%}")
    print(f"   📊 Max Drawdown: {risk['max_drawdown']:.2%}")
    print(f"   📈 Sharpe Ratio: {risk['sharpe_ratio']:.2f}")
    print(f"   🎯 Score de Riesgo: {risk['risk_score']:.1f}/10")
    
    return signal

if __name__ == '__main__':
    try:
        results = demo_integration()
        print("\n✅ Demo de integración completada exitosamente!")
    except Exception as e:
        print(f"\n❌ Error en demo: {e}")
        import traceback
        traceback.print_exc()
