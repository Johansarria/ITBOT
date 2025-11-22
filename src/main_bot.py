# /src/main_bot.py

import os
import sys
import time
import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar módulos SICAR
from pipelines.data_pipeline import DataPipeline
from module_1_causal import CausalCartographer
from module_2_regime import RegimeClassifier
from module_3_metacontroller import MetaController
from module_xai import generate_cognitive_report
from trade_logger import trade_logger_instance
from multi_symbol_portfolio import MultiSymbolPortfolio
from config import *
from enhanced_config import CONFIG
from enhanced_logger import SICAR_LOGGER

# Importar Binance API
try:
    from binance.client import Client
    from binance.enums import *
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False
    logging.warning("python-binance no instalado. Ejecutar: pip install python-binance")

logger = SICAR_LOGGER.get_logger('main')

def get_binance_data(symbol='BTCUSDT', interval='4h', limit=500):
    """
    Obtiene datos reales de Binance usando fetcher robusto con fallbacks.
    
    Args:
        symbol: Par de trading (ej: 'BTCUSDT')
        interval: Intervalo de tiempo ('1h', '4h', '1d')
        limit: Número máximo de velas (máx 1000)
        
    Returns:
        DataFrame con datos OHLCV o None si falla
    """
    try:
        logger.info(f"📊 Obteniendo datos para {symbol} - Intervalo: {interval}")
        
        # Importar el fetcher robusto
        from robust_data_fetcher import RobustDataFetcher
        
        # Crear instancia del fetcher robusto
        fetcher = RobustDataFetcher()
        
        # Obtener datos usando múltiples estrategias de fallback
        df = fetcher.get_market_data(symbol, interval, limit)
        
        if df is None or df.empty:
            logger.error(f"No se pudieron obtener datos para {symbol}")
            return None
        
        # Verificar que tenemos las columnas necesarias
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']
        for col in required_columns:
            if col not in df.columns:
                logger.error(f"Columna faltante: {col}")
                return None
        
        # Agregar columnas adicionales para análisis
        df['price'] = df['Close']
        df['returns'] = df['Close'].pct_change()
        df['volatility'] = df['returns'].rolling(window=20).std()
        
        # Limpiar datos
        df = df.dropna()
        
        logger.info(f"✅ Datos obtenidos exitosamente con fetcher robusto")
        logger.info(f"📈 Dataset: {len(df)} puntos de datos")
        logger.info(f"📅 Período: {df.index[0]} a {df.index[-1]}")
        logger.info(f"💰 Precio inicial: ${df['Close'].iloc[0]:.2f}")
        logger.info(f"💰 Precio final: ${df['Close'].iloc[-1]:.2f}")
        logger.info(f"📊 Rango de precios: ${df['Close'].min():.2f} - ${df['Close'].max():.2f}")
        
        return df
        
    except Exception as e:
        logger.error(f"Error obteniendo datos de Binance: {str(e)}")
        return None

class TradingBot:
    """
    Bot Principal de SICAR
    
    Integra todos los módulos para operación en vivo:
    - Módulo 1: Análisis causal de noticias
    - Módulo 2: Clasificación de regímenes de mercado  
    - Módulo 3: Metacontrolador para selección de estrategias
    - Módulo XAI: Generación de informes cognitivos
    """
    
    def __init__(self, config_path: str = None):
        """
        Inicializa el bot de trading SICAR.
        
        Args:
            config_path: Ruta al archivo de configuración
        """
        self.config = self._load_config(config_path)
        
        # Inicializar módulos SICAR
        symbols = self.config.get('symbols', TRADING_SYMBOLS)
        self.data_pipeline = DataPipeline(symbols=symbols)
        self.causal_cartographer = CausalCartographer()
        self.regime_classifier = RegimeClassifier()
        self.metacontroller = MetaController()
        
        # Inicializar portafolio multi-símbolo
        self.portfolio = MultiSymbolPortfolio(
            symbols=symbols,
            capital_allocation=self.config.get('capital_allocation', CAPITAL_ALLOCATION)
        )
        
        # Inicializar cliente Binance
        self.binance_client = None
        self._initialize_binance_client()
        
        # Estado del bot
        self.is_running = False
        self.current_position = None
        self.current_order_id = None
        self.current_trade_id = None  # ID del trade actual para logging detallado
        self.entry_price = None
        self.stop_loss_price = None
        self.take_profit_price = None
        self.last_analysis_time = None
        
        # Métricas de rendimiento
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_value = self.config['initial_capital']
        self.current_value = self.config['initial_capital']
        
        # Logs y reportes
        self.decisions_log = []
        self.trades_log = []
        
        # Kill switch
        self.kill_switch_triggered = False
        
        logger.info("Bot SICAR inicializado correctamente")
    
    def _load_config(self, config_path: str = None) -> Dict:
        """
        Carga la configuración del bot.
        
        Args:
            config_path: Ruta al archivo de configuración
            
        Returns:
            Diccionario con configuración
        """
        # Cargar configuración desde variables de entorno
        default_config = {
            'symbol': os.getenv('SYMBOL', 'BTCUSDT'),  # Símbolo principal para compatibilidad
            'symbols': TRADING_SYMBOLS,  # Lista de símbolos para multi-trading
            'capital_allocation': CAPITAL_ALLOCATION,  # Distribución de capital
            'timeframe': '4h',
            'initial_capital': float(os.getenv('INITIAL_CAPITAL', str(CAPITAL_BASE))),
            'risk_per_trade': float(os.getenv('RISK_PER_TRADE', str(RISK_PER_TRADE))),
            'max_drawdown_limit': float(os.getenv('MAX_DRAWDOWN_LIMIT', str(KILL_SWITCH_MAX_DRAWDOWN))),  # Usar valor optimizado
            'min_confidence': float(os.getenv('MIN_CONFIDENCE', str(CONFIDENCE_THRESHOLD))),  # Usar valor optimizado
            'stop_loss_pct': float(os.getenv('STOP_LOSS_PCT', str(STOP_LOSS_PCT))),  # Usar valor optimizado
            'take_profit_pct': float(os.getenv('TAKE_PROFIT_PCT', str(TAKE_PROFIT_PCT))),  # Usar valor optimizado
            'analysis_interval': int(os.getenv('ANALYSIS_INTERVAL', '3600')),  # Análisis cada hora
            'max_positions': int(os.getenv('MAX_POSITIONS', str(MAX_POSITIONS))),  # Usar valor optimizado
            'enable_xai_reports': os.getenv('ENABLE_XAI_REPORTS', 'true').lower() == 'true',
            'enable_news_analysis': os.getenv('ENABLE_NEWS_ANALYSIS', 'true').lower() == 'true',
            'enable_regime_analysis': os.getenv('ENABLE_REGIME_ANALYSIS', 'true').lower() == 'true',
            'log_decisions': os.getenv('LOG_DECISIONS', 'true').lower() == 'true',
            # Configuración de trading
            'trading_mode': os.getenv('TRADING_MODE', 'testnet').lower(),
            'paper_trading': os.getenv('PAPER_TRADING', 'true').lower() == 'true',
            'binance_api_key': os.getenv('BINANCE_API_KEY', ''),
            'binance_secret_key': os.getenv('BINANCE_SECRET_KEY', ''),
            'min_order_size': 0.001,  # Tamaño mínimo de orden en BTC
            'max_order_size': 0.1,  # Tamaño máximo de orden en BTC
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
                logger.info(f"Configuración cargada desde {config_path}")
            except Exception as e:
                logger.warning(f"Error cargando configuración: {str(e)}, usando configuración por defecto")
        
        return default_config
    
    def _initialize_binance_client(self):
        """
        Inicializa el cliente de Binance para paper trading.
        """
        try:
            if not BINANCE_AVAILABLE:
                logger.warning("Binance API no disponible, usando simulación local")
                return
            
            # Obtener credenciales de variables de entorno
            api_key = os.getenv('BINANCE_API_KEY', self.config.get('binance_api_key', ''))
            secret_key = os.getenv('BINANCE_SECRET_KEY', self.config.get('binance_secret_key', ''))
            
            if not api_key or not secret_key:
                logger.warning("Credenciales de Binance no configuradas, usando simulación local")
                logger.info("Para usar Binance Testnet:")
                logger.info("1. Crear cuenta en https://testnet.binance.vision/")
                logger.info("2. Generar API Key y Secret")
                logger.info("3. Configurar variables de entorno BINANCE_API_KEY y BINANCE_SECRET_KEY")
                return
            
            runtime_modes = CONFIG.safe_runtime_modes()
            trading_mode = runtime_modes['trading_mode']
            paper_trading = runtime_modes['paper_trading']
            if trading_mode == 'live' and not CONFIG.is_live_trading_allowed():
                trading_mode = 'testnet'
                paper_trading = True
            
            # Inicializar cliente
            if trading_mode == 'testnet':
                # Usar Testnet
                self.binance_client = Client(
                    api_key=api_key,
                    api_secret=secret_key,
                    testnet=True
                )
                logger.info("Cliente Binance Testnet inicializado correctamente")
            else:
                # Usar API de producción
                self.binance_client = Client(
                    api_key=api_key,
                    api_secret=secret_key
                )
                if paper_trading:
                    logger.info("Cliente Binance PRODUCCIÓN inicializado en MODO PAPER TRADING")
                    logger.info("📊 Datos reales, operaciones simuladas")
                else:
                    logger.warning("Cliente Binance REAL inicializado - ¡TRADING CON DINERO REAL!")
                    logger.warning("💰 ¡OPERACIONES REALES CON DINERO REAL!")
            
            # Sincronizar tiempo del servidor
            try:
                server_time = self.binance_client.get_server_time()
                logger.info("Tiempo del servidor Binance sincronizado")
            except Exception as sync_error:
                logger.warning(f"Error de sincronización de tiempo: {sync_error}")
                logger.info("Continuando con operación local...")
            
            # Verificar conexión
            try:
                account_info = self.binance_client.get_account()
                logger.info(f"Cuenta Binance conectada: {len(account_info['balances'])} balances disponibles")
                
                # Mostrar balance de USDT
                for balance in account_info['balances']:
                    if balance['asset'] == 'USDT' and float(balance['free']) > 0:
                        logger.info(f"Balance USDT disponible: {balance['free']}")
                        break
            except Exception as conn_error:
                logger.warning(f"Error verificando cuenta: {conn_error}")
                logger.info("El bot continuará en modo simulación")
                    
        except Exception as e:
            logger.error(f"Error inicializando cliente Binance: {str(e)}")
            self.binance_client = None
    
    def initialize_models(self) -> bool:
        """
        Inicializa y carga los modelos entrenados.
        
        Returns:
            True si la inicialización fue exitosa, False en caso contrario
        """
        try:
            logger.info("Inicializando modelos SICAR...")
            
            # Cargar modelos entrenados
            regime_loaded = self.regime_classifier.load_model()
            metacontroller_loaded = self.metacontroller.load_model()
            
            if not regime_loaded:
                logger.warning("Modelo de régimen no encontrado, entrenando con datos recientes...")
                # Entrenar con datos recientes si no existe modelo
                recent_data = self.data_pipeline.download_market_data(
                    self.config['symbol'], 
                    period='6mo', 
                    interval=self.config['timeframe']
                )
                if not recent_data.empty:
                    processed_data = self.data_pipeline.add_technical_indicators(recent_data)
                    self.regime_classifier.train_classifier(processed_data)
                    regime_loaded = True
            
            if not metacontroller_loaded:
                logger.warning("Modelo de metacontrolador no encontrado, entrenando con datos recientes...")
                # Entrenar metacontrolador si no existe
                recent_data = self.data_pipeline.download_market_data(
                    self.config['symbol'], 
                    period='6mo', 
                    interval=self.config['timeframe']
                )
                if not recent_data.empty:
                    processed_data = self.data_pipeline.add_technical_indicators(recent_data)
                    regime_results = self.regime_classifier.classify_regimes(processed_data)
                    features = self.metacontroller.prepare_features(processed_data, regime_results)
                    
                    # Crear etiquetas para entrenamiento
                    from module_3_metacontroller import create_labels
                    labels = create_labels(processed_data)
                    
                    # Alinear datos
                    aligned_data = pd.concat([features, labels.rename('label')], axis=1).dropna()
                    if len(aligned_data) > 0:
                        features_aligned = aligned_data.drop(columns=['label'])
                        labels_aligned = aligned_data['label']
                        self.metacontroller.train_metacontroller(features_aligned, labels_aligned)
                        metacontroller_loaded = True
            
            if regime_loaded and metacontroller_loaded:
                logger.info("Modelos SICAR inicializados correctamente")
                return True
            else:
                logger.error("Error inicializando modelos SICAR")
                return False
                
        except Exception as e:
            logger.error(f"Error inicializando modelos: {str(e)}")
            return False
    
    def check_kill_switch(self) -> bool:
        """
        Verifica si se debe activar el kill switch por máximo drawdown.
        
        Returns:
            True si se debe parar el bot, False en caso contrario
        """
        try:
            # Calcular drawdown actual
            if self.current_value < self.peak_value:
                current_drawdown = (self.peak_value - self.current_value) / self.peak_value
                
                if current_drawdown > self.max_drawdown:
                    self.max_drawdown = current_drawdown
                
                # Verificar límite de drawdown
                if current_drawdown >= self.config['max_drawdown_limit']:
                    logger.critical(f"KILL SWITCH ACTIVADO: Drawdown {current_drawdown:.2%} excede límite {self.config['max_drawdown_limit']:.2%}")
                    self.kill_switch_triggered = True
                    return True
            else:
                # Nuevo pico de valor
                self.peak_value = self.current_value
            
            return False
            
        except Exception as e:
            logger.error(f"Error verificando kill switch: {str(e)}")
            return False
    
    def calculate_position_size(self, entry_price: float, stop_loss_price: float) -> float:
        """
        Calcula el tamaño de posición basado en gestión de riesgo.
        
        Args:
            entry_price: Precio de entrada
            stop_loss_price: Precio de stop loss
            
        Returns:
            Tamaño de posición en unidades base
        """
        try:
            # Calcular riesgo por acción/unidad
            risk_per_unit = abs(entry_price - stop_loss_price)
            
            if risk_per_unit <= 0:
                return 0.0
            
            # Calcular cantidad de capital a arriesgar
            risk_amount = self.current_value * self.config['risk_per_trade']
            
            # Calcular tamaño de posición
            position_size = risk_amount / risk_per_unit
            
            # Limitar tamaño máximo (no más del 50% del capital)
            max_position_value = self.current_value * 0.5
            max_position_size = max_position_value / entry_price
            
            position_size = min(position_size, max_position_size)
            
            logger.info(f"Tamaño de posición calculado: {position_size:.6f} unidades")
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculando tamaño de posición: {str(e)}")
            return 0.0
    
    def get_market_data(self) -> pd.DataFrame:
        """
        Obtiene datos de mercado actuales usando Binance como fuente principal.
        
        Returns:
            DataFrame con datos de mercado procesados
        """
        try:
            logger.info("🔄 Obteniendo datos de mercado...")
            
            # 1. Intentar obtener datos reales de Binance primero
            if BINANCE_AVAILABLE:
                logger.info("📊 Intentando obtener datos reales de Binance...")
                
                # Usar configuración del bot para símbolo e intervalo
                symbol = self.config['symbol']
                interval = self.config['timeframe']
                
                # Obtener datos de Binance
                binance_data = get_binance_data(symbol=symbol, interval=interval, limit=500)
                
                if binance_data is not None and len(binance_data) >= 50:
                    logger.info(f"✅ Datos reales obtenidos de Binance: {len(binance_data)} barras")
                    
                    # Agregar indicadores técnicos usando DataPipeline
                    processed_data = self.data_pipeline._add_technical_indicators(binance_data)
                    
                    logger.info(f"📈 Datos procesados con indicadores técnicos")
                    return processed_data
                else:
                    logger.warning("⚠️ Datos insuficientes de Binance, intentando fallback...")
            
            # 2. Fallback a DataPipeline (Yahoo Finance)
            logger.info("🔄 Usando DataPipeline como fallback...")
            raw_data = self.data_pipeline.get_market_data(
                ticker=self.config['symbol'],
                period='1mo',
                interval=self.config['timeframe']
            )
            
            if raw_data is None or raw_data.empty:
                logger.error("❌ No se pudieron obtener datos de mercado de ninguna fuente")
                return pd.DataFrame()
            
            # Los datos ya vienen con indicadores técnicos desde DataPipeline
            processed_data = raw_data
            
            logger.info(f"✅ Datos de mercado obtenidos (fallback): {len(processed_data)} barras")
            
            return processed_data
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos de mercado: {str(e)}")
            return pd.DataFrame()
    
    def analyze_multi_timeframe_market(self, symbol: str = 'BTCUSDT') -> Dict:
        """
        Realiza análisis completo del mercado usando múltiples timeframes.
        
        Args:
            symbol: Símbolo a analizar
            
        Returns:
            Diccionario con resultados del análisis multi-timeframe
        """
        try:
            logger.info("🔄 Iniciando análisis multi-timeframe SICAR...")
            
            # Definir timeframes a analizar (de menor a mayor para análisis jerárquico)
            timeframes = ['15m', '30m', '45m', '1h', '2h', '3h', '4h']
            
            # 1. Obtener datos de múltiples timeframes
            logger.info("📊 Obteniendo datos multi-timeframe...")
            multi_data = self.data_pipeline.get_multi_timeframe_data(
                ticker=symbol, 
                timeframes=timeframes
            )
            
            if not multi_data:
                logger.error("❌ No se pudieron obtener datos multi-timeframe")
                return self._fallback_single_timeframe_analysis(symbol)
            
            # 2. Análisis de regímenes multi-timeframe
            logger.info("🎯 Analizando regímenes multi-timeframe...")
            multi_regime_analysis = self.regime_classifier.analyze_multi_timeframe_regimes(multi_data)
            
            # 3. Análisis de estrategias multi-timeframe
            logger.info("⚡ Analizando estrategias multi-timeframe...")
            multi_strategy_analysis = self.metacontroller.analyze_multi_timeframe_strategies(
                multi_data, multi_regime_analysis
            )
            
            # 4. Análisis causal (usando datos del timeframe principal)
            causal_analysis = {}
            if self.config['enable_news_analysis']:
                try:
                    main_timeframe_data = multi_data.get('4h', multi_data.get('1h'))
                    if main_timeframe_data is not None:
                        causal_analysis = self._simulate_causal_analysis(main_timeframe_data)
                except Exception as e:
                    logger.error(f"Error en análisis causal multi-timeframe: {str(e)}")
                    causal_analysis = {'sentiment': 0.0, 'confidence': 0.0}
            
            # 5. Generar consenso final
            final_consensus = self._generate_final_consensus(
                multi_regime_analysis, 
                multi_strategy_analysis, 
                causal_analysis
            )
            
            # 6. Generar reporte XAI multi-timeframe
            xai_report = None
            if self.config['enable_xai_reports']:
                try:
                    xai_report = self._generate_multi_timeframe_xai_report(
                        final_consensus, 
                        multi_regime_analysis, 
                        multi_strategy_analysis,
                        causal_analysis
                    )
                except Exception as e:
                    logger.error(f"Error generando reporte XAI multi-timeframe: {str(e)}")
                    xai_report = "Error generando reporte cognitivo multi-timeframe"
            
            # Compilar resultados finales
            analysis_results = {
                'timestamp': datetime.now(),
                'analysis_type': 'multi_timeframe',
                'timeframes_analyzed': timeframes,
                'price': final_consensus.get('current_price', 0.0),
                'multi_regime_analysis': multi_regime_analysis,
                'multi_strategy_analysis': multi_strategy_analysis,
                'causal_analysis': causal_analysis,
                'final_consensus': final_consensus,
                'strategy_decision': {
                    'strategy': final_consensus.get('consensus_strategy', 'hold'),
                    'confidence': final_consensus.get('overall_confidence', 0.0),
                    'signal': final_consensus.get('consensus_signal', 0.0)
                },
                'xai_report': xai_report
            }
            
            logger.info(f"✅ Análisis multi-timeframe completado")
            logger.info(f"🎯 Consenso: {final_consensus.get('consensus_strategy', 'hold')} "
                       f"(señal: {final_consensus.get('consensus_signal', 0.0):.2f}, "
                       f"confianza: {final_consensus.get('overall_confidence', 0.0):.2f})")
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"❌ Error en análisis multi-timeframe: {str(e)}")
            return self._fallback_single_timeframe_analysis(symbol)
    
    def _generate_final_consensus(self, multi_regime_analysis: Dict, 
                                multi_strategy_analysis: Dict, 
                                causal_analysis: Dict) -> Dict:
        """
        Genera consenso final combinando análisis de regímenes, estrategias y factores causales.
        
        Args:
            multi_regime_analysis: Análisis de regímenes multi-timeframe
            multi_strategy_analysis: Análisis de estrategias multi-timeframe
            causal_analysis: Análisis causal
            
        Returns:
            Diccionario con consenso final
        """
        try:
            # Obtener consensos individuales
            regime_consensus = multi_regime_analysis.get('consensus', {})
            strategy_consensus = multi_strategy_analysis.get('consensus', {})
            
            # Pesos para diferentes componentes del análisis
            weights = {
                'strategy': 0.5,    # 50% peso a estrategias
                'regime': 0.3,      # 30% peso a regímenes
                'causal': 0.2       # 20% peso a factores causales
            }
            
            # Señal de estrategia
            strategy_signal = strategy_consensus.get('consensus_signal', 0.0)
            strategy_confidence = strategy_consensus.get('overall_confidence', 0.0)
            
            # Señal de régimen (convertir a señal numérica)
            regime_signal = self._convert_regime_to_signal(regime_consensus)
            regime_confidence = regime_consensus.get('overall_confidence', 0.0)
            
            # Señal causal
            causal_signal = causal_analysis.get('sentiment', 0.0)
            causal_confidence = causal_analysis.get('confidence', 0.0)
            
            # Calcular señal ponderada final
            weighted_signal = (
                weights['strategy'] * strategy_confidence * strategy_signal +
                weights['regime'] * regime_confidence * regime_signal +
                weights['causal'] * causal_confidence * causal_signal
            )
            
            total_weighted_confidence = (
                weights['strategy'] * strategy_confidence +
                weights['regime'] * regime_confidence +
                weights['causal'] * causal_confidence
            )
            
            final_signal = weighted_signal / total_weighted_confidence if total_weighted_confidence > 0 else 0.0
            final_confidence = total_weighted_confidence
            
            # Determinar estrategia final
            if abs(final_signal) < 0.1:
                final_strategy = 'hold'
            elif final_signal > 0:
                final_strategy = 'momentum' if final_signal > 0.5 else 'mean_reversion'
            else:
                final_strategy = 'breakout' if final_signal < -0.5 else 'hold'
            
            # Obtener precio actual
            current_price = 0.0
            if multi_strategy_analysis.get('timeframe_analysis'):
                for tf_analysis in multi_strategy_analysis['timeframe_analysis'].values():
                    if 'current_price' in tf_analysis:
                        current_price = tf_analysis['current_price']
                        break
            
            consensus = {
                'consensus_strategy': final_strategy,
                'consensus_signal': final_signal,
                'overall_confidence': final_confidence,
                'current_price': current_price,
                'component_signals': {
                    'strategy': {'signal': strategy_signal, 'confidence': strategy_confidence},
                    'regime': {'signal': regime_signal, 'confidence': regime_confidence},
                    'causal': {'signal': causal_signal, 'confidence': causal_confidence}
                },
                'agreement_analysis': {
                    'strategy_agreement': strategy_consensus.get('agreement_level', 'bajo'),
                    'regime_agreement': regime_consensus.get('agreement_level', 'bajo'),
                    'overall_agreement': self._calculate_overall_agreement(
                        strategy_signal, regime_signal, causal_signal
                    )
                },
                'risk_assessment': self._assess_multi_timeframe_risk(
                    multi_regime_analysis, multi_strategy_analysis
                )
            }
            
            return consensus
            
        except Exception as e:
            logger.error(f"Error generando consenso final: {str(e)}")
            return {
                'consensus_strategy': 'hold',
                'consensus_signal': 0.0,
                'overall_confidence': 0.0,
                'current_price': 0.0
            }
    
    def _convert_regime_to_signal(self, regime_consensus: Dict) -> float:
        """
        Convierte el consenso de régimen a una señal numérica.
        
        Args:
            regime_consensus: Consenso de régimen
            
        Returns:
            Señal numérica entre -1 y 1
        """
        regime_name = regime_consensus.get('consensus_regime', 'Consolidación')
        
        # Mapeo de regímenes a señales
        regime_signals = {
            'Tendencia Alcista': 0.7,
            'Tendencia Bajista': -0.7,
            'Alta Volatilidad': -0.3,
            'Baja Volatilidad': 0.2,
            'Consolidación': 0.0,
            'Breakout': 0.5,
            'Reversión': -0.4
        }
        
        return regime_signals.get(regime_name, 0.0)
    
    def _calculate_overall_agreement(self, strategy_signal: float, 
                                   regime_signal: float, 
                                   causal_signal: float) -> str:
        """
        Calcula el nivel de acuerdo general entre las señales.
        
        Args:
            strategy_signal: Señal de estrategia
            regime_signal: Señal de régimen
            causal_signal: Señal causal
            
        Returns:
            Nivel de acuerdo ('alto', 'medio', 'bajo')
        """
        signals = [strategy_signal, regime_signal, causal_signal]
        
        # Calcular desviación estándar de las señales
        signal_std = np.std(signals)
        
        if signal_std < 0.2:
            return 'alto'
        elif signal_std < 0.5:
            return 'medio'
        else:
            return 'bajo'
    
    def _assess_multi_timeframe_risk(self, multi_regime_analysis: Dict, 
                                   multi_strategy_analysis: Dict) -> Dict:
        """
        Evalúa el riesgo basado en el análisis multi-timeframe.
        
        Args:
            multi_regime_analysis: Análisis de regímenes
            multi_strategy_analysis: Análisis de estrategias
            
        Returns:
            Diccionario con evaluación de riesgo
        """
        try:
            # Analizar divergencias entre timeframes
            strategy_divergences = multi_strategy_analysis.get('consensus', {}).get('divergences', [])
            regime_divergences = multi_regime_analysis.get('consensus', {}).get('divergences', [])
            
            # Calcular nivel de riesgo
            divergence_count = len(strategy_divergences) + len(regime_divergences)
            
            if divergence_count == 0:
                risk_level = 'bajo'
            elif divergence_count <= 2:
                risk_level = 'medio'
            else:
                risk_level = 'alto'
            
            # Analizar volatilidad entre timeframes
            volatility_levels = []
            for tf_analysis in multi_strategy_analysis.get('timeframe_analysis', {}).values():
                if 'recent_volatility' in tf_analysis:
                    volatility_levels.append(tf_analysis['recent_volatility'])
            
            avg_volatility = np.mean(volatility_levels) if volatility_levels else 0.0
            
            return {
                'risk_level': risk_level,
                'divergence_count': divergence_count,
                'average_volatility': avg_volatility,
                'strategy_divergences': strategy_divergences,
                'regime_divergences': regime_divergences,
                'recommendation': self._generate_risk_recommendation(risk_level, avg_volatility)
            }
            
        except Exception as e:
            logger.error(f"Error evaluando riesgo multi-timeframe: {str(e)}")
            return {'risk_level': 'medio', 'recommendation': 'Proceder con cautela'}
    
    def _generate_risk_recommendation(self, risk_level: str, volatility: float) -> str:
        """
        Genera recomendación basada en el nivel de riesgo.
        
        Args:
            risk_level: Nivel de riesgo
            volatility: Volatilidad promedio
            
        Returns:
            Recomendación textual
        """
        if risk_level == 'alto' or volatility > 0.03:
            return "Riesgo elevado - Reducir tamaño de posición o evitar trading"
        elif risk_level == 'medio':
            return "Riesgo moderado - Proceder con cautela y gestión estricta de riesgo"
        else:
            return "Riesgo bajo - Condiciones favorables para trading"
    
    def _generate_multi_timeframe_xai_report(self, final_consensus: Dict,
                                           multi_regime_analysis: Dict,
                                           multi_strategy_analysis: Dict,
                                           causal_analysis: Dict) -> str:
        """
        Genera reporte XAI específico para análisis multi-timeframe.
        
        Args:
            final_consensus: Consenso final
            multi_regime_analysis: Análisis de regímenes
            multi_strategy_analysis: Análisis de estrategias
            causal_analysis: Análisis causal
            
        Returns:
            Reporte XAI textual
        """
        try:
            report_lines = [
                "🤖 REPORTE COGNITIVO MULTI-TIMEFRAME SICAR",
                "=" * 50,
                f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "📊 CONSENSO FINAL:",
                f"   Estrategia: {final_consensus.get('consensus_strategy', 'N/A')}",
                f"   Señal: {final_consensus.get('consensus_signal', 0.0):.3f}",
                f"   Confianza: {final_consensus.get('overall_confidence', 0.0):.1%}",
                f"   Acuerdo General: {final_consensus.get('agreement_analysis', {}).get('overall_agreement', 'N/A')}",
                "",
                "🎯 ANÁLISIS POR TIMEFRAME:",
            ]
            
            # Agregar análisis por timeframe
            for tf, analysis in multi_strategy_analysis.get('timeframe_analysis', {}).items():
                report_lines.extend([
                    f"   {tf}: {analysis.get('strategy', 'N/A')} "
                    f"(señal: {analysis.get('signal', 0.0):.2f}, "
                    f"confianza: {analysis.get('confidence', 0.0):.1%})"
                ])
            
            # Agregar información de riesgo
            risk_info = final_consensus.get('risk_assessment', {})
            report_lines.extend([
                "",
                "⚠️ EVALUACIÓN DE RIESGO:",
                f"   Nivel: {risk_info.get('risk_level', 'N/A')}",
                f"   Recomendación: {risk_info.get('recommendation', 'N/A')}",
                f"   Divergencias: {risk_info.get('divergence_count', 0)}",
                ""
            ])
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"Error generando reporte XAI multi-timeframe: {str(e)}")
            return "Error generando reporte cognitivo multi-timeframe"
    
    def _fallback_single_timeframe_analysis(self, symbol: str) -> Dict:
        """
        Análisis de respaldo usando un solo timeframe si falla el multi-timeframe.
        
        Args:
            symbol: Símbolo a analizar
            
        Returns:
            Diccionario con análisis de un solo timeframe
        """
        try:
            logger.warning("🔄 Ejecutando análisis de respaldo (timeframe único)...")
            
            # Obtener datos del timeframe principal
            market_data = get_binance_data(symbol, self.config['timeframe'])
            
            if market_data is not None:
                return self.analyze_market(market_data)
            else:
                logger.error("❌ No se pudieron obtener datos para análisis de respaldo")
                return {
                    'timestamp': datetime.now(),
                    'analysis_type': 'fallback_failed',
                    'strategy_decision': {'strategy': 'hold', 'confidence': 0.0, 'signal': 0.0}
                }
                
        except Exception as e:
            logger.error(f"❌ Error en análisis de respaldo: {str(e)}")
            return {
                'timestamp': datetime.now(),
                'analysis_type': 'fallback_failed',
                'strategy_decision': {'strategy': 'hold', 'confidence': 0.0, 'signal': 0.0}
            }

    def analyze_market(self, market_data: pd.DataFrame) -> Dict:
        """
        Realiza análisis completo del mercado usando todos los módulos SICAR.
        
        Args:
            market_data: DataFrame con datos de mercado
            
        Returns:
            Diccionario con resultados del análisis
        """
        try:
            logger.info("Iniciando análisis de mercado SICAR...")
            
            # Determinar el nombre de la columna de cierre
            close_col = 'Close' if 'Close' in market_data.columns else 'close'
            
            analysis_results = {
                'timestamp': datetime.now(),
                'price': market_data[close_col].iloc[-1],
                'causal_analysis': {},
                'regime_analysis': {},
                'strategy_decision': {},
                'xai_report': None
            }
            
            # 1. Análisis Causal (Módulo 1)
            if self.config['enable_news_analysis']:
                try:
                    logger.info("Ejecutando análisis causal...")
                    # En producción, esto analizaría noticias reales
                    # Para demo, simulamos el análisis
                    causal_results = self._simulate_causal_analysis(market_data)
                    analysis_results['causal_analysis'] = causal_results
                    logger.info(f"Análisis causal completado: sentimiento {causal_results.get('sentiment', 0):.2f}")
                except Exception as e:
                    logger.error(f"Error en análisis causal: {str(e)}")
                    analysis_results['causal_analysis'] = {'sentiment': 0.0, 'confidence': 0.0}
            
            # 2. Análisis de Régimen (Módulo 2)
            if self.config['enable_regime_analysis']:
                try:
                    logger.info("Ejecutando análisis de régimen...")
                    regime_results = self.regime_classifier.classify_regimes(market_data)
                    
                    if not regime_results.empty:
                        current_regime = regime_results.iloc[-1]
                        regime_name = self.regime_classifier.regime_names.get(
                            current_regime['regime'], 'Desconocido'
                        )
                        
                        analysis_results['regime_analysis'] = {
                            'regime': current_regime['regime'],
                            'regime_name': regime_name,
                            'confidence': current_regime.get('confidence', 0.0)
                        }
                        logger.info(f"Régimen identificado: {regime_name}")
                    else:
                        analysis_results['regime_analysis'] = {'regime': 0, 'regime_name': 'Desconocido', 'confidence': 0.0}
                        
                except Exception as e:
                    logger.error(f"Error en análisis de régimen: {str(e)}")
                    analysis_results['regime_analysis'] = {'regime': 0, 'regime_name': 'Error', 'confidence': 0.0}
            
            # 3. Decisión de Estrategia (Módulo 3)
            try:
                logger.info("Ejecutando metacontrolador...")
                
                # Preparar características
                features = self.metacontroller.prepare_features(
                    market_data, 
                    pd.DataFrame([analysis_results['regime_analysis']]) if analysis_results['regime_analysis'] else None
                )
                
                if not features.empty:
                    # Obtener decisión de estrategia
                    strategy, confidence = self.metacontroller.predict_strategy(features)
                    signal = self.metacontroller.execute_strategy(strategy, market_data)
                    
                    analysis_results['strategy_decision'] = {
                        'strategy': strategy,
                        'confidence': confidence,
                        'signal': signal
                    }
                    logger.info(f"Estrategia seleccionada: {strategy} (confianza: {confidence:.2f}, señal: {signal:.2f})")
                else:
                    analysis_results['strategy_decision'] = {'strategy': 'hold', 'confidence': 0.0, 'signal': 0.0}
                    
            except Exception as e:
                logger.error(f"Error en metacontrolador: {str(e)}")
                analysis_results['strategy_decision'] = {'strategy': 'hold', 'confidence': 0.0, 'signal': 0.0}
            
            # 4. Generar Reporte Cognitivo (Módulo XAI)
            if self.config['enable_xai_reports']:
                try:
                    logger.info("Generando reporte cognitivo...")
                    xai_report = generate_cognitive_report(
                        decision=analysis_results['strategy_decision']['strategy'],
                        strategy=analysis_results['strategy_decision']['strategy'],
                        market_regime=analysis_results['regime_analysis']['regime_name'],
                        xai_factors={
                            'confidence': analysis_results['strategy_decision']['confidence'],
                            'signal_strength': abs(analysis_results['strategy_decision']['signal'])
                        },
                        primary_causal_factors=analysis_results['causal_analysis'].get('factors', [])
                    )
                    analysis_results['xai_report'] = xai_report
                    logger.info("Reporte cognitivo generado")
                except Exception as e:
                    logger.error(f"Error generando reporte XAI: {str(e)}")
                    analysis_results['xai_report'] = "Error generando reporte cognitivo"
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error en análisis de mercado: {str(e)}")
            return {}
    
    def analyze_multi_symbol_market(self) -> Dict[str, Dict]:
        """
        Realiza análisis completo del mercado para múltiples símbolos.
        
        Returns:
            Diccionario con resultados del análisis por símbolo
        """
        try:
            logger.info(f"🔄 Iniciando análisis multi-símbolo para {len(self.portfolio.symbols)} activos...")
            
            # Obtener datos de múltiples símbolos
            multi_data = self.data_pipeline.get_multi_symbol_data(
                period='1mo', 
                interval=self.config['timeframe']
            )
            
            if not multi_data:
                logger.error("❌ No se pudieron obtener datos para ningún símbolo")
                return {}
            
            # Actualizar precios en el portafolio
            current_prices = {}
            for symbol, data in multi_data.items():
                if not data.empty:
                    current_prices[symbol] = data['Close'].iloc[-1]
            
            self.portfolio.update_prices(current_prices)
            
            # Análisis por símbolo
            symbol_analyses = {}
            
            for symbol, data in multi_data.items():
                try:
                    logger.info(f"📊 Analizando {symbol}...")
                    
                    # Análisis individual del símbolo
                    analysis = self.analyze_market(data)
                    analysis['symbol'] = symbol
                    analysis['current_price'] = current_prices.get(symbol, 0)
                    analysis['portfolio_allocation'] = self.portfolio.get_symbol_allocation(symbol)
                    analysis['available_capital'] = self.portfolio.get_available_capital(symbol)
                    analysis['position_open'] = self.portfolio.is_position_open(symbol)
                    
                    symbol_analyses[symbol] = analysis
                    
                    logger.info(f"✅ {symbol}: Estrategia {analysis['strategy_decision']['strategy']} "
                              f"(confianza: {analysis['strategy_decision']['confidence']:.2f})")
                    
                except Exception as e:
                    logger.error(f"❌ Error analizando {symbol}: {str(e)}")
                    symbol_analyses[symbol] = {
                        'symbol': symbol,
                        'error': str(e),
                        'strategy_decision': {'strategy': 'hold', 'confidence': 0.0, 'signal': 0.0}
                    }
            
            # Resumen del portafolio
            portfolio_summary = self.portfolio.get_portfolio_summary()
            
            logger.info(f"💼 Resumen del portafolio:")
            logger.info(f"   💰 Valor total: ${portfolio_summary['total_value']:.2f}")
            logger.info(f"   📈 Retorno total: {portfolio_summary['total_return']:.2f}%")
            logger.info(f"   📊 Posiciones abiertas: {portfolio_summary['open_positions']}")
            
            return {
                'timestamp': datetime.now(),
                'symbols': symbol_analyses,
                'portfolio_summary': portfolio_summary,
                'total_symbols_analyzed': len(symbol_analyses),
                'successful_analyses': len([a for a in symbol_analyses.values() if 'error' not in a])
            }
            
        except Exception as e:
            logger.error(f"❌ Error en análisis multi-símbolo: {str(e)}")
            return {}
    
    def _simulate_causal_analysis(self, market_data: pd.DataFrame) -> Dict:
        """
        Simula análisis causal para demo (en producción usaría noticias reales).
        
        Args:
            market_data: DataFrame con datos de mercado
            
        Returns:
            Diccionario con resultados del análisis causal simulado
        """
        try:
            # Detectar nombre de columna de precio de cierre
            close_col = 'Close' if 'Close' in market_data.columns else 'close'
            
            # Calcular volatilidad reciente vs histórica
            recent_volatility = market_data[close_col].pct_change().tail(24).std()
            historical_volatility = market_data[close_col].pct_change().std()
            
            # Calcular momentum
            momentum = market_data[close_col].pct_change(periods=24).iloc[-1]
            
            # Simular sentimiento basado en condiciones de mercado
            if recent_volatility > historical_volatility * 1.5:
                sentiment = -0.3  # Alta volatilidad = sentimiento negativo
                factors = ['alta_volatilidad', 'incertidumbre_mercado']
            elif momentum > 0.05:
                sentiment = 0.4   # Momentum positivo = sentimiento positivo
                factors = ['momentum_alcista', 'confianza_mercado']
            elif momentum < -0.05:
                sentiment = -0.4  # Momentum negativo = sentimiento negativo
                factors = ['momentum_bajista', 'presion_vendedora']
            else:
                sentiment = 0.0   # Neutral
                factors = ['mercado_lateral', 'consolidacion']
            
            return {
                'sentiment': sentiment,
                'confidence': min(abs(sentiment) + 0.2, 1.0),
                'factors': factors,
                'volatility_ratio': recent_volatility / historical_volatility,
                'momentum': momentum
            }
            
        except Exception as e:
            logger.error(f"Error simulando análisis causal: {str(e)}")
            return {'sentiment': 0.0, 'confidence': 0.0, 'factors': []}
    
    def execute_trading_decision(self, analysis_results: Dict, market_data: pd.DataFrame) -> bool:
        """
        Ejecuta decisión de trading basada en el análisis.
        
        Args:
            analysis_results: Resultados del análisis de mercado
            market_data: DataFrame con datos de mercado
            
        Returns:
            True si se ejecutó una acción, False en caso contrario
        """
        try:
            strategy_decision = analysis_results.get('strategy_decision', {})
            signal = strategy_decision.get('signal', 0.0)
            confidence = strategy_decision.get('confidence', 0.0)
            current_price = analysis_results.get('price', 0.0)
            
            # Verificar confianza mínima
            if confidence < self.config['min_confidence']:
                logger.info(f"Confianza {confidence:.2f} menor que mínimo {self.config['min_confidence']:.2f}, no operando")
                return False
            
            # Gestionar posición existente
            if self.current_position is not None:
                return self._manage_existing_position(current_price)
            
            # Evaluar nueva entrada
            if abs(signal) > 0.5 and self.config['max_positions'] > 0:
                return self._enter_new_position(signal, current_price, analysis_results)
            
            return False
            
        except Exception as e:
            logger.error(f"Error ejecutando decisión de trading: {str(e)}")
            return False
    
    def execute_multi_symbol_trading_decisions(self, portfolio_analysis: Dict) -> Dict[str, bool]:
        """
        Ejecuta decisiones de trading para múltiples símbolos basado en el análisis del portafolio.
        
        Args:
            portfolio_analysis: Resultados del análisis multi-símbolo
            
        Returns:
            Dict con las acciones ejecutadas por símbolo
        """
        actions_taken = {}
        
        try:
            # Verificar que tenemos análisis de símbolos válidos
            if 'symbol_analyses' not in portfolio_analysis:
                logger.warning("⚠️ No hay análisis de símbolos disponibles para ejecutar decisiones")
                return {symbol: False for symbol in self.config.get('symbols', ['BTCUSDT'])}
            
            for symbol, analysis_results in portfolio_analysis['symbol_analyses'].items():
                if not analysis_results:
                    actions_taken[symbol] = False
                    continue
                
                logger.info(f"🔄 Procesando decisión para {symbol}")
                
                # Obtener datos específicos del símbolo
                market_data = self.data_pipeline.get_data(symbol, self.config['timeframe'])
                
                if market_data.empty:
                    logger.warning(f"⚠️ No hay datos de mercado para {symbol}")
                    actions_taken[symbol] = False
                    continue
                
                # Ejecutar decisión para este símbolo específico
                action_taken = self.execute_trading_decision(analysis_results, market_data)
                actions_taken[symbol] = action_taken
                
                if action_taken:
                    logger.info(f"✅ Acción ejecutada para {symbol}")
                else:
                    logger.info(f"⏸️ Sin acción para {symbol}")
            
            return actions_taken
            
        except Exception as e:
            logger.error(f"Error ejecutando decisiones multi-símbolo: {str(e)}")
            return {symbol: False for symbol in portfolio_analysis.get('symbol_analyses', {}).keys()}
    
    def _manage_existing_position(self, current_price: float) -> bool:
        """
        Gestiona posición existente (stop loss, take profit).
        
        Args:
            current_price: Precio actual
            
        Returns:
            True si se cerró la posición, False en caso contrario
        """
        try:
            if self.current_position == 'long':
                # Verificar stop loss o take profit para posición larga
                if current_price <= self.stop_loss_price:
                    self._close_position(current_price, 'stop_loss')
                    return True
                elif current_price >= self.take_profit_price:
                    self._close_position(current_price, 'take_profit')
                    return True
                    
            elif self.current_position == 'short':
                # Verificar stop loss o take profit para posición corta
                if current_price >= self.stop_loss_price:
                    self._close_position(current_price, 'stop_loss')
                    return True
                elif current_price <= self.take_profit_price:
                    self._close_position(current_price, 'take_profit')
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error gestionando posición existente: {str(e)}")
            return False
    
    def _enter_new_position(self, signal: float, current_price: float, analysis_results: Dict) -> bool:
        """
        Entra en una nueva posición usando Binance API o simulación.
        
        Args:
            signal: Señal de trading
            current_price: Precio actual
            analysis_results: Resultados del análisis
            
        Returns:
            True si se abrió posición, False en caso contrario
        """
        try:
            if signal > 0:  # Señal de compra
                self.stop_loss_price = current_price * (1 - self.config['stop_loss_pct'])
                self.take_profit_price = current_price * (1 + self.config['take_profit_pct'])
                position_type = 'long'
                side = 'BUY'
                
            elif signal < 0:  # Señal de venta
                self.stop_loss_price = current_price * (1 + self.config['stop_loss_pct'])
                self.take_profit_price = current_price * (1 - self.config['take_profit_pct'])
                position_type = 'short'
                side = 'SELL'
            else:
                return False
            
            # Calcular tamaño de posición
            position_size = self.calculate_position_size(current_price, self.stop_loss_price)
            
            if position_size <= 0:
                logger.warning("Tamaño de posición inválido")
                return False
            
            # Validar tamaño mínimo y máximo
            min_size = self.config.get('min_order_size', 0.001)
            max_size = self.config.get('max_order_size', 0.1)
            position_size = max(min_size, min(position_size, max_size))
            
            # Ejecutar orden
            order_success = False
            order_id = None
            actual_price = current_price
            
            if self.binance_client and not self.config.get('paper_trading', True):
                # Trading real con Binance
                try:
                    # Formatear cantidad según las reglas de Binance
                    quantity = f"{position_size:.6f}".rstrip('0').rstrip('.')
                    
                    # Crear orden de mercado
                    order = self.binance_client.order_market(
                        symbol=self.config['symbol'],
                        side=side,
                        quantity=quantity
                    )
                    
                    order_id = order['orderId']
                    actual_price = float(order.get('fills', [{}])[0].get('price', current_price))
                    order_success = True
                    
                    logger.info(f"Orden Binance ejecutada: {order_id}")
                    
                except Exception as e:
                    logger.error(f"Error ejecutando orden Binance: {str(e)}")
                    logger.info("Fallback a simulación")
                    order_success = True  # Continuar con simulación
                    
            else:
                # Paper trading / simulación
                order_success = True
                logger.info("Ejecutando en modo simulación")
            
            if not order_success:
                return False
            
            # Registrar entrada con logging detallado
            self.current_trade_id = trade_logger_instance.log_trade_entry(
                symbol=self.config['symbol'],
                position_type=position_type,
                entry_price=actual_price,
                position_size=position_size,
                stop_loss=self.stop_loss_price,
                take_profit=self.take_profit_price,
                strategy=analysis_results.get('strategy_decision', {}).get('strategy', 'unknown'),
                confidence=analysis_results.get('strategy_decision', {}).get('confidence', 0.0),
                regime=analysis_results.get('regime_analysis', {}).get('regime_name', 'unknown'),
                analysis_results=analysis_results,
                order_id=order_id,
                is_simulation=self.config.get('paper_trading', True) or self.binance_client is None
            )
            
            # Actualizar estado del bot
            self.current_position = position_type
            self.entry_price = actual_price
            self.current_order_id = order_id
            
            # Registrar trade en log interno (mantener compatibilidad)
            trade_info = {
                'timestamp': datetime.now(),
                'action': 'open',
                'position_type': position_type,
                'entry_price': actual_price,
                'position_size': position_size,
                'stop_loss': self.stop_loss_price,
                'take_profit': self.take_profit_price,
                'strategy': analysis_results.get('strategy_decision', {}).get('strategy', 'unknown'),
                'confidence': analysis_results.get('strategy_decision', {}).get('confidence', 0.0),
                'regime': analysis_results.get('regime_analysis', {}).get('regime_name', 'unknown'),
                'order_id': order_id,
                'is_simulation': self.config.get('paper_trading', True) or self.binance_client is None,
                'trade_id': self.current_trade_id
            }
            
            self.trades_log.append(trade_info)
            
            logger.info(f"POSICIÓN ABIERTA: {position_type.upper()} {position_size:.6f} a ${actual_price:.2f}")
            logger.info(f"Stop Loss: ${self.stop_loss_price:.2f}, Take Profit: ${self.take_profit_price:.2f}")
            logger.info(f"Trade ID: {self.current_trade_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error abriendo nueva posición: {str(e)}")
            return False
    
    def _close_position(self, current_price: float, reason: str):
        """
        Cierra la posición actual usando Binance API o simulación.
        
        Args:
            current_price: Precio de cierre
            reason: Razón del cierre ('stop_loss', 'take_profit', 'manual')
        """
        try:
            if self.current_position is None:
                return
            
            # Determinar lado de la orden de cierre
            if self.current_position == 'long':
                close_side = 'SELL'
            else:  # short
                close_side = 'BUY'
            
            # Ejecutar orden de cierre
            close_order_id = None
            actual_close_price = current_price
            
            if self.binance_client and not self.config.get('paper_trading', True):
                # Trading real con Binance
                try:
                    # Obtener balance actual para determinar cantidad a cerrar
                    account_info = self.binance_client.get_account()
                    
                    # Buscar balance del asset base (BTC para BTCUSDT)
                    base_asset = self.config['symbol'].replace('USDT', '')
                    quantity = 0.0
                    
                    for balance in account_info['balances']:
                        if balance['asset'] == base_asset:
                            quantity = float(balance['free'])
                            break
                    
                    if quantity > 0:
                        # Formatear cantidad
                        quantity_str = f"{quantity:.6f}".rstrip('0').rstrip('.')
                        
                        # Crear orden de mercado para cerrar
                        close_order = self.binance_client.order_market(
                            symbol=self.config['symbol'],
                            side=close_side,
                            quantity=quantity_str
                        )
                        
                        close_order_id = close_order['orderId']
                        actual_close_price = float(close_order.get('fills', [{}])[0].get('price', current_price))
                        
                        logger.info(f"Orden de cierre Binance ejecutada: {close_order_id}")
                    else:
                        logger.warning("No hay balance disponible para cerrar posición")
                        
                except Exception as e:
                    logger.error(f"Error cerrando posición en Binance: {str(e)}")
                    logger.info("Cerrando en modo simulación")
            
            # Calcular PnL
            if self.current_position == 'long':
                pnl_pct = (actual_close_price - self.entry_price) / self.entry_price
            else:  # short
                pnl_pct = (self.entry_price - actual_close_price) / self.entry_price
            
            # Actualizar métricas
            self.total_trades += 1
            if pnl_pct > 0:
                self.winning_trades += 1
            
            # Actualizar valor del portafolio (simplificado)
            trade_pnl = self.current_value * self.config['risk_per_trade'] * (pnl_pct / self.config['stop_loss_pct'])
            self.current_value += trade_pnl
            self.total_pnl += trade_pnl
            
            # Registrar salida con logging detallado
            if self.current_trade_id:
                trade_logger_instance.log_trade_exit(
                    trade_id=self.current_trade_id,
                    exit_price=actual_close_price,
                    exit_reason=reason,
                    pnl_percentage=pnl_pct,
                    pnl_amount=trade_pnl,
                    portfolio_value=self.current_value,
                    close_order_id=close_order_id,
                    is_simulation=self.config.get('paper_trading', True) or self.binance_client is None,
                    additional_context={
                        'entry_price': self.entry_price,
                        'stop_loss_price': self.stop_loss_price,
                        'take_profit_price': self.take_profit_price,
                        'position_type': self.current_position
                    }
                )
            
            # Registrar cierre en log interno (mantener compatibilidad)
            trade_info = {
                'timestamp': datetime.now(),
                'action': 'close',
                'position_type': self.current_position,
                'exit_price': actual_close_price,
                'pnl_pct': pnl_pct,
                'pnl_amount': trade_pnl,
                'reason': reason,
                'portfolio_value': self.current_value,
                'close_order_id': close_order_id,
                'is_simulation': self.config.get('paper_trading', True) or self.binance_client is None,
                'trade_id': self.current_trade_id
            }
            
            self.trades_log.append(trade_info)
            
            logger.info(f"POSICIÓN CERRADA: {self.current_position.upper()} a ${actual_close_price:.2f}")
            logger.info(f"Razón: {reason}, PnL: {pnl_pct:.2%} (${trade_pnl:.2f})")
            logger.info(f"Valor del portafolio: ${self.current_value:.2f}")
            logger.info(f"Trade ID completado: {self.current_trade_id}")
            
            # Resetear posición
            self.current_position = None
            self.current_trade_id = None
            self.entry_price = None
            self.stop_loss_price = None
            self.take_profit_price = None
            self.current_order_id = None
            
        except Exception as e:
            logger.error(f"Error cerrando posición: {str(e)}")
    
    def _check_binance_order_status(self, order_id: str) -> Dict:
        """
        Verifica el estado de una orden en Binance.
        
        Args:
            order_id: ID de la orden a verificar
            
        Returns:
            Información del estado de la orden
        """
        try:
            if not self.binance_client or not order_id:
                return {'status': 'UNKNOWN', 'error': 'Cliente no disponible'}
            
            order_status = self.binance_client.get_order(
                symbol=self.config['symbol'],
                orderId=order_id
            )
            
            return {
                'status': order_status['status'],
                'side': order_status['side'],
                'quantity': order_status['origQty'],
                'price': order_status.get('price', 'MARKET'),
                'executed_qty': order_status['executedQty'],
                'time': order_status['time']
            }
            
        except Exception as e:
            logger.error(f"Error verificando orden {order_id}: {str(e)}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def _get_binance_account_info(self) -> Dict:
        """
        Obtiene información de la cuenta de Binance.
        
        Returns:
            Información de la cuenta y balances
        """
        try:
            if not self.binance_client:
                return {'error': 'Cliente Binance no disponible'}
            
            account_info = self.binance_client.get_account()
            
            # Filtrar solo balances con cantidad > 0
            active_balances = []
            for balance in account_info['balances']:
                free_balance = float(balance['free'])
                locked_balance = float(balance['locked'])
                if free_balance > 0 or locked_balance > 0:
                    active_balances.append({
                        'asset': balance['asset'],
                        'free': free_balance,
                        'locked': locked_balance,
                        'total': free_balance + locked_balance
                    })
            
            return {
                'balances': active_balances,
                'can_trade': account_info['canTrade'],
                'can_withdraw': account_info['canWithdraw'],
                'can_deposit': account_info['canDeposit'],
                'update_time': account_info['updateTime']
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo información de cuenta: {str(e)}")
            return {'error': str(e)}
    
    def save_logs(self):
        """Guarda logs de decisiones y trades."""
        try:
            # Crear directorio de logs
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
            os.makedirs(logs_dir, exist_ok=True)
            
            # Guardar log de decisiones
            if self.decisions_log:
                decisions_df = pd.DataFrame(self.decisions_log)
                decisions_path = os.path.join(logs_dir, f"decisions_{datetime.now().strftime('%Y%m%d')}.csv")
                decisions_df.to_csv(decisions_path, index=False)
                logger.info(f"Log de decisiones guardado en {decisions_path}")
            
            # Guardar log de trades
            if self.trades_log:
                trades_df = pd.DataFrame(self.trades_log)
                trades_path = os.path.join(logs_dir, f"trades_{datetime.now().strftime('%Y%m%d')}.csv")
                trades_df.to_csv(trades_path, index=False)
                logger.info(f"Log de trades guardado en {trades_path}")
                
        except Exception as e:
            logger.error(f"Error guardando logs: {str(e)}")
    
    def _get_next_4h_candle_time(self) -> datetime:
        """
        Calcula el tiempo de la próxima vela de 4 horas.
        Las velas de 4h en Binance empiezan a las 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC.
        
        Returns:
            datetime: Tiempo de la próxima vela de 4 horas
        """
        now = datetime.utcnow()
        
        # Horas de inicio de velas de 4h
        candle_hours = [0, 4, 8, 12, 16, 20]
        
        # Encontrar la próxima hora de vela
        current_hour = now.hour
        next_hour = None
        
        for hour in candle_hours:
            if hour > current_hour:
                next_hour = hour
                break
        
        # Si no hay hora mayor hoy, usar la primera del día siguiente
        if next_hour is None:
            next_candle = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        else:
            next_candle = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
        
        return next_candle
    
    def _save_cognitive_diary(self, cycle: int, analysis_results: Dict, action_taken: bool):
        """
        Guarda el Diario Cognitivo del ciclo actual.
        
        Args:
            cycle: Número del ciclo
            analysis_results: Resultados del análisis SICAR
            action_taken: Si se tomó alguna acción de trading
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            diary_filename = f"../reports/diario_cognitivo_ciclo_{cycle}_{timestamp}.txt"
            
            # Crear directorio si no existe
            os.makedirs(os.path.dirname(diary_filename), exist_ok=True)
            
            with open(diary_filename, 'w', encoding='utf-8') as f:
                f.write(f"🧠 DIARIO COGNITIVO SICAR - CICLO {cycle}\n")
                f.write(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"💰 Precio: ${analysis_results.get('price', 0):.2f}\n")
                f.write(f"📊 Símbolo: {self.config['symbol']}\n")
                f.write(f"🎯 Acción tomada: {'Sí' if action_taken else 'No'}\n")
                f.write(f"💼 Posición actual: {self.current_position or 'Ninguna'}\n")
                f.write(f"💵 Valor portafolio: ${self.current_value:.2f}\n")
                f.write("="*80 + "\n\n")
                
                # Agregar reporte XAI completo
                if analysis_results.get('xai_report'):
                    f.write(analysis_results['xai_report'])
                    f.write("\n\n")
                
                # Agregar detalles técnicos
                f.write("📈 DETALLES TÉCNICOS:\n")
                f.write("-"*40 + "\n")
                
                regime_analysis = analysis_results.get('regime_analysis', {})
                f.write(f"🏛️ Régimen de mercado: {regime_analysis.get('regime_name', 'Desconocido')}\n")
                f.write(f"📊 Confianza régimen: {regime_analysis.get('confidence', 0):.2%}\n")
                
                strategy_decision = analysis_results.get('strategy_decision', {})
                f.write(f"⚡ Estrategia recomendada: {strategy_decision.get('strategy', 'hold')}\n")
                f.write(f"🎯 Confianza estrategia: {strategy_decision.get('confidence', 0):.2%}\n")
                f.write(f"📡 Señal: {strategy_decision.get('signal', 0):.3f}\n")
                
                causal_analysis = analysis_results.get('causal_analysis', {})
                f.write(f"📰 Sentimiento noticias: {causal_analysis.get('sentiment', 0):.3f}\n")
                f.write(f"🔗 Relaciones causales: {causal_analysis.get('causal_strength', 0):.3f}\n")
                
                f.write(f"📊 Volatilidad: {analysis_results.get('market_volatility', 0):.3f}\n")
                f.write(f"📈 Fuerza tendencia: {analysis_results.get('trend_strength', 0):.3f}\n")
                
                f.write("\n" + "="*80 + "\n")
                f.write("🤖 Generado por SICAR - Sistema Inteligente de Análisis y Recomendaciones\n")
            
            logger.info(f"📝 Diario Cognitivo guardado: {diary_filename}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando Diario Cognitivo: {str(e)}")
    
    def _show_cycle_statistics(self, cycle: int, analysis_results: Dict):
        """
        Muestra estadísticas del ciclo actual.
        
        Args:
            cycle: Número del ciclo
            analysis_results: Resultados del análisis
        """
        try:
            logger.info("📊 === ESTADÍSTICAS DEL CICLO ===")
            logger.info(f"🔢 Ciclo: {cycle}")
            logger.info(f"💰 Precio actual: ${analysis_results.get('price', 0):.2f}")
            logger.info(f"💼 Posición: {self.current_position or 'Ninguna'}")
            logger.info(f"💵 Valor portafolio: ${self.current_value:.2f}")
            
            if self.total_trades > 0:
                win_rate = (self.winning_trades / self.total_trades) * 100
                logger.info(f"📈 Total trades: {self.total_trades}")
                logger.info(f"🎯 Tasa de acierto: {win_rate:.1f}%")
                logger.info(f"💹 PnL total: ${self.total_pnl:.2f}")
                logger.info(f"📉 Drawdown máximo: {self.max_drawdown:.2%}")
            
            # Estadísticas del análisis actual
            regime_analysis = analysis_results.get('regime_analysis', {})
            strategy_decision = analysis_results.get('strategy_decision', {})
            
            logger.info(f"🏛️ Régimen: {regime_analysis.get('regime_name', 'Desconocido')}")
            logger.info(f"⚡ Estrategia: {strategy_decision.get('strategy', 'hold')}")
            logger.info(f"🎯 Confianza: {strategy_decision.get('confidence', 0):.1%}")
            
            logger.info("================================")
            
        except Exception as e:
            logger.error(f"❌ Error mostrando estadísticas: {str(e)}")
    
    def show_trades_summary(self):
        """
        Muestra un resumen detallado de todas las operaciones realizadas.
        """
        try:
            logger.info("=== RESUMEN DETALLADO DE TRADES ===")
            
            # Obtener resumen del trade logger
            summary = trade_logger_instance.get_trades_summary()
            
            if summary.get('total_trades', 0) == 0:
                logger.info("📊 No hay trades completados para mostrar")
                return
            
            logger.info(f"📈 Total de Trades: {summary['total_trades']}")
            logger.info(f"✅ Trades Ganadores: {summary['winning_trades']}")
            logger.info(f"❌ Trades Perdedores: {summary['losing_trades']}")
            logger.info(f"🎯 Tasa de Acierto: {summary['win_rate']:.1%}")
            logger.info(f"💰 PnL Total: ${summary['total_pnl']:.2f}")
            logger.info(f"⏱️ Duración Promedio: {summary['average_duration_hours']:.1f} horas")
            logger.info(f"💼 Valor del Portafolio: ${summary['last_portfolio_value']:.2f}")
            
            # Calcular retorno total
            initial_capital = self.config['initial_capital']
            total_return = ((summary['last_portfolio_value'] - initial_capital) / initial_capital) * 100
            logger.info(f"📊 Retorno Total: {total_return:.2f}%")
            
            logger.info("===================================")
            
        except Exception as e:
            logger.error(f"Error mostrando resumen de trades: {str(e)}")
    
    def export_trades_analysis(self):
        """
        Exporta los trades a CSV para análisis posterior.
        """
        try:
            logger.info("📤 Exportando análisis de trades...")
            
            # Exportar trades detallados
            csv_path = trade_logger_instance.export_trades_to_csv()
            
            if csv_path:
                logger.info(f"✅ Trades exportados exitosamente a: {csv_path}")
                logger.info("📊 El archivo contiene coordenadas exactas de entrada y salida")
                logger.info("🔍 Úsalo para análisis posterior y optimización de estrategias")
            else:
                logger.warning("⚠️ No se pudo exportar el archivo de trades")
                
        except Exception as e:
            logger.error(f"Error exportando análisis de trades: {str(e)}")
    
    def run(self):
        """
        Bucle principal del bot de trading SICAR.
        Ejecuta análisis cada 4 horas sincronizado con las velas de Binance.
        Soporta múltiples símbolos de trading.
        """
        try:
            logger.info("🚀 === INICIANDO BOT SICAR AUTÓNOMO MULTI-SÍMBOLO ===")
            logger.info("🧠 Inteligencia Artificial de Trading Activada")
            
            # Inicializar modelos
            if not self.initialize_models():
                logger.error("❌ Error inicializando modelos, abortando")
                return
            
            self.is_running = True
            logger.info(f"💰 Capital inicial: ${self.config['initial_capital']:,.2f}")
            logger.info(f"📊 Símbolos: {', '.join(self.config['symbols'])}")
            logger.info(f"📈 Timeframe: {self.config['timeframe']}")
            logger.info(f"⚡ Riesgo por trade: {self.config['risk_per_trade']:.1%}")
            logger.info(f"🎯 Confianza mínima: {self.config['min_confidence']:.1%}")
            logger.info("📝 Modo: PAPER TRADING (Simulación)")
            
            # Mostrar distribución de capital
            for symbol, allocation in self.config['capital_allocation'].items():
                allocated_capital = self.config['initial_capital'] * allocation
                logger.info(f"💼 {symbol}: ${allocated_capital:,.2f} ({allocation:.1%})")
            
            # Contador de ciclos
            cycle_count = 0
            
            while self.is_running:
                try:
                    cycle_count += 1
                    current_time = datetime.utcnow()
                    
                    logger.info(f"\n🔄 === CICLO {cycle_count} - {current_time.strftime('%Y-%m-%d %H:%M:%S')} ===")
                    
                    # Verificar kill switch
                    if self.check_kill_switch():
                        logger.critical("🛑 Bot detenido por kill switch")
                        break
                    
                    # Calcular tiempo hasta próxima vela de 4h
                    next_4h_candle = self._get_next_4h_candle_time()
                    time_to_wait = (next_4h_candle - current_time).total_seconds()
                    
                    if time_to_wait > 300:  # Si faltan más de 5 minutos
                        hours = int(time_to_wait // 3600)
                        minutes = int((time_to_wait % 3600) // 60)
                        logger.info(f"⏰ Esperando próxima vela de 4h: {hours}h {minutes}m")
                        logger.info(f"🕐 Próximo análisis: {next_4h_candle.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        # Esperar en intervalos de 5 minutos mostrando progreso
                        while time_to_wait > 300:
                            time.sleep(300)  # 5 minutos
                            time_to_wait -= 300
                            current_time = datetime.utcnow()
                            remaining_hours = int(time_to_wait // 3600)
                            remaining_minutes = int((time_to_wait % 3600) // 60)
                            logger.info(f"⏳ Tiempo restante: {remaining_hours}h {remaining_minutes}m")
                    
                    # Esperar los últimos minutos
                    if time_to_wait > 0:
                        logger.info(f"⏱️ Esperando últimos {int(time_to_wait)}s para sincronización...")
                        time.sleep(max(0, time_to_wait))
                    
                    logger.info("🎯 === INICIANDO ANÁLISIS SICAR MULTI-SÍMBOLO ===")
                    
                    # Realizar análisis multi-símbolo con todos los módulos SICAR
                    portfolio_analysis = self.analyze_multi_symbol_market()
                    
                    if not portfolio_analysis:
                        logger.warning("⚠️ Error en análisis multi-símbolo, reintentando...")
                        time.sleep(300)
                        continue
                    
                    # Mostrar resumen del portafolio
                    portfolio_summary = portfolio_analysis.get('portfolio_summary', {})
                    logger.info(f"📊 Valor total del portafolio: ${portfolio_summary.get('total_value', 0):,.2f}")
                    logger.info(f"📈 PnL total: ${portfolio_summary.get('total_pnl', 0):,.2f}")
                    logger.info(f"📊 Retorno: {portfolio_summary.get('total_return', 0):.2f}%")
                    
                    # Verificar que tenemos análisis de símbolos válidos
                    if 'symbol_analyses' not in portfolio_analysis:
                        logger.warning("⚠️ No se encontraron análisis de símbolos, reintentando...")
                        time.sleep(300)
                        continue
                    
                    # Procesar resultados de cada símbolo
                    for symbol, analysis_results in portfolio_analysis['symbol_analyses'].items():
                        if analysis_results:
                            logger.info(f"🔍 {symbol}: {analysis_results.get('strategy_decision', {}).get('strategy', 'hold')} - Confianza: {analysis_results.get('strategy_decision', {}).get('confidence', 0.0):.1%}")
                    
                    # Usar el primer símbolo válido para compatibilidad con el resto del código
                    analysis_results = None
                    for symbol, result in portfolio_analysis['symbol_analyses'].items():
                        if result:
                            analysis_results = result
                            break
                    
                    if not analysis_results:
                        logger.warning("⚠️ No se obtuvieron análisis válidos para ningún símbolo")
                        time.sleep(300)
                        continue
                    
                    # Registrar decisión detallada
                    if self.config['log_decisions']:
                        decision_log = {
                            'cycle': cycle_count,
                            'timestamp': analysis_results['timestamp'],
                            'price': analysis_results['price'],
                            'regime': analysis_results.get('regime_analysis', {}).get('regime_name', 'unknown'),
                            'strategy': analysis_results.get('strategy_decision', {}).get('strategy', 'hold'),
                            'confidence': analysis_results.get('strategy_decision', {}).get('confidence', 0.0),
                            'signal': analysis_results.get('strategy_decision', {}).get('signal', 0.0),
                            'sentiment': analysis_results.get('causal_analysis', {}).get('sentiment', 0.0),
                            'position': self.current_position,
                            'portfolio_value': self.current_value,
                            'market_volatility': analysis_results.get('market_volatility', 0.0),
                            'trend_strength': analysis_results.get('trend_strength', 0.0)
                        }
                        self.decisions_log.append(decision_log)
                    
                    # Ejecutar decisiones de trading multi-símbolo (paper trading)
                    actions_taken = self.execute_multi_symbol_trading_decisions(portfolio_analysis)
                    
                    # Para compatibilidad con el resto del código, usar la primera acción válida
                    action_taken = any(actions_taken.values())
                    
                    # Generar y guardar Diario Cognitivo
                    if analysis_results.get('xai_report'):
                        self._save_cognitive_diary(cycle_count, analysis_results, action_taken)
                        
                        logger.info("📋 === DIARIO COGNITIVO GENERADO ===")
                        logger.info(analysis_results['xai_report'][:500] + "..." if len(analysis_results['xai_report']) > 500 else analysis_results['xai_report'])
                        logger.info("==================================")
                    
                    # Mostrar estadísticas del ciclo
                    self._show_cycle_statistics(cycle_count, analysis_results)
                    
                    # Guardar logs cada 10 ciclos
                    if cycle_count % 10 == 0:
                        self.save_logs()
                        logger.info(f"💾 Logs guardados - Ciclo {cycle_count}")
                    
                    # Actualizar tiempo del último análisis
                    self.last_analysis_time = datetime.now()
                    
                    logger.info(f"✅ Ciclo {cycle_count} completado exitosamente")
                    
                except KeyboardInterrupt:
                    logger.info("⏹️ Interrupción del usuario, deteniendo bot...")
                    break
                except Exception as e:
                    logger.error(f"❌ Error en ciclo {cycle_count}: {str(e)}")
                    logger.info("🔄 Reintentando en 5 minutos...")
                    time.sleep(300)  # Esperar 5 minutos antes de reintentar
            
            # Cerrar posición abierta si existe
            if self.current_position is not None:
                market_data = self.get_market_data()
                if not market_data.empty:
                    close_col = 'Close' if 'Close' in market_data.columns else 'close'
                    current_price = market_data[close_col].iloc[-1]
                    self._close_position(current_price, 'manual')
            
            # Guardar logs finales
            self.save_logs()
            
            # Mostrar resumen detallado de trades con coordenadas exactas
            self.show_trades_summary()
            
            # Exportar análisis de trades para análisis posterior
            self.export_trades_analysis()
            
            # Mostrar resumen final básico
            logger.info("=== RESUMEN FINAL BÁSICO ===")
            logger.info(f"Total trades: {self.total_trades}")
            if self.total_trades > 0:
                win_rate = (self.winning_trades / self.total_trades) * 100
                logger.info(f"Tasa de acierto: {win_rate:.1f}%")
            logger.info(f"PnL total: ${self.total_pnl:.2f}")
            logger.info(f"Valor final: ${self.current_value:.2f}")
            logger.info(f"Retorno total: {((self.current_value - self.config['initial_capital']) / self.config['initial_capital'] * 100):.2f}%")
            logger.info("============================")
            
        except Exception as e:
            logger.error(f"Error crítico en bot: {str(e)}")
        finally:
            self.is_running = False
            logger.info("Bot SICAR detenido")

def main():
    """Función principal para ejecutar el bot."""
    try:
        # Crear y ejecutar bot
        bot = TradingBot()
        bot.run()
        
    except Exception as e:
        logger.error(f"Error ejecutando bot: {str(e)}")
        print(f"❌ Error: {str(e)}")
        print("\nAsegúrate de:")
        print("1. Instalar dependencias: pip install -r requirements.txt")
        print("2. Configurar APIs en .env")
        print("3. Entrenar modelos ejecutando backtester.py primero")

if __name__ == '__main__':
    main()
