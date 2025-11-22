#!/usr/bin/env python3
"""
SICAR Main Bot - Adaptado para Índices
Bot principal adaptado para trading de índices usando Yahoo Finance/IEX
Integra todos los módulos SICAR con el sistema de índices
"""

import os
import sys
import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import warnings
warnings.filterwarnings('ignore')

# Importar módulos SICAR originales
from data_pipeline import DataPipeline
from module_1_causal_cartographer import CausalCartographer
from module_2_regime_classifier import RegimeClassifier
from module_3_metacontroller import MetaController
from portfolio_manager import MultiSymbolPortfolio

# Importar módulos de índices
from indices_data_adapter import IndicesDataAdapter, get_binance_data
from indices_config import IndicesConfigManager
from indices_indicators import IndicesIndicators
from indices_strategies import IndicesStrategies
from indices_risk_manager import IndicesRiskManager
from indices_backtester import IndicesBacktester
from market_hours_system import MarketHoursSystem, MarketSession

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sicar_indices_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuración para índices
INDICES_SYMBOLS = ['SPY', 'QQQ', 'DIA', 'IWM']
CRYPTO_TO_INDICES_MAPPING = {
    'BTCUSDT': 'SPY',
    'ETHUSDT': 'QQQ', 
    'ADAUSDT': 'DIA',
    'SOLUSDT': 'IWM'
}

# Configuración de capital para índices
INDICES_CAPITAL_BASE = 100000.0  # $100k base
INDICES_CAPITAL_ALLOCATION = {
    'SPY': 0.40,   # 40% S&P 500
    'QQQ': 0.30,   # 30% NASDAQ
    'DIA': 0.20,   # 20% Dow Jones
    'IWM': 0.10    # 10% Russell 2000
}

# Parámetros recalibrados para índices
INDICES_RISK_PER_TRADE = 0.01      # 1% riesgo por trade (más conservador)
INDICES_STOP_LOSS_PCT = 0.02       # 2% stop loss (más ajustado)
INDICES_TAKE_PROFIT_PCT = 0.04     # 4% take profit (ratio 2:1)
INDICES_CONFIDENCE_THRESHOLD = 0.65 # 65% confianza mínima
INDICES_MAX_DRAWDOWN = 0.08         # 8% máximo drawdown
INDICES_MAX_POSITIONS = 2           # Máximo 2 posiciones simultáneas

class IndicesTradingBot:
    """
    Bot de Trading SICAR adaptado para Índices
    
    Integra todos los módulos SICAR con el sistema de índices:
    - Adaptador de datos (Binance -> Yahoo Finance/IEX)
    - Estrategias específicas para índices
    - Gestión de riesgo adaptada
    - Filtros de horarios de mercado US
    """
    
    def __init__(self, config_path: str = None):
        """
        Inicializa el bot de trading para índices.
        
        Args:
            config_path: Ruta al archivo de configuración
        """
        self.config = self._load_indices_config(config_path)
        
        # Inicializar adaptador de datos
        self.data_adapter = IndicesDataAdapter()
        
        # Inicializar módulos de índices
        self.config_manager = IndicesConfigManager()
        self.market_hours = MarketHoursSystem()
        self.indicators = IndicesIndicators()
        self.strategies = IndicesStrategies()
        self.risk_manager = IndicesRiskManager()
        self.backtester = IndicesBacktester()
        
        # Inicializar módulos SICAR originales (adaptados)
        symbols = self.config.get('symbols', INDICES_SYMBOLS)
        self.data_pipeline = DataPipeline(symbols=symbols)
        self.causal_cartographer = CausalCartographer()
        self.regime_classifier = RegimeClassifier()
        self.metacontroller = MetaController()
        
        # Inicializar portafolio para índices
        self.portfolio = MultiSymbolPortfolio(
            symbols=symbols,
            capital_allocation=self.config.get('capital_allocation', INDICES_CAPITAL_ALLOCATION)
        )
        
        # Estado del bot
        self.is_running = False
        self.current_positions = {}  # Posiciones por símbolo
        self.current_orders = {}     # Órdenes por símbolo
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
        
        logger.info("🚀 Bot SICAR para Índices inicializado correctamente")
    
    def _load_indices_config(self, config_path: str = None) -> Dict:
        """
        Carga la configuración específica para índices.
        
        Args:
            config_path: Ruta al archivo de configuración
            
        Returns:
            Diccionario con configuración para índices
        """
        default_config = {
            'symbol': 'SPY',  # Símbolo principal
            'symbols': INDICES_SYMBOLS,
            'capital_allocation': INDICES_CAPITAL_ALLOCATION,
            'timeframe': '1d',  # Diario para índices
            'initial_capital': float(os.getenv('INITIAL_CAPITAL', str(INDICES_CAPITAL_BASE))),
            'risk_per_trade': float(os.getenv('RISK_PER_TRADE', str(INDICES_RISK_PER_TRADE))),
            'max_drawdown_limit': float(os.getenv('MAX_DRAWDOWN_LIMIT', str(INDICES_MAX_DRAWDOWN))),
            'min_confidence': float(os.getenv('MIN_CONFIDENCE', str(INDICES_CONFIDENCE_THRESHOLD))),
            'stop_loss_pct': float(os.getenv('STOP_LOSS_PCT', str(INDICES_STOP_LOSS_PCT))),
            'take_profit_pct': float(os.getenv('TAKE_PROFIT_PCT', str(INDICES_TAKE_PROFIT_PCT))),
            'analysis_interval': int(os.getenv('ANALYSIS_INTERVAL', '14400')),  # Análisis cada 4 horas
            'max_positions': int(os.getenv('MAX_POSITIONS', str(INDICES_MAX_POSITIONS))),
            'enable_xai_reports': os.getenv('ENABLE_XAI_REPORTS', 'true').lower() == 'true',
            'enable_news_analysis': os.getenv('ENABLE_NEWS_ANALYSIS', 'true').lower() == 'true',
            'enable_regime_analysis': os.getenv('ENABLE_REGIME_ANALYSIS', 'true').lower() == 'true',
            'log_decisions': os.getenv('LOG_DECISIONS', 'true').lower() == 'true',
            # Configuración específica para índices
            'trading_mode': 'indices',
            'paper_trading': os.getenv('PAPER_TRADING', 'true').lower() == 'true',
            'market_hours_filter': True,  # Filtrar por horarios de mercado
            'volatility_adjustment': True,  # Ajustar por volatilidad
            'sector_rotation': True,  # Habilitar rotación sectorial
        }
        
        # Cargar configuración personalizada si existe
        if config_path and os.path.exists(config_path):
            try:
                import json
                with open(config_path, 'r') as f:
                    custom_config = json.load(f)
                default_config.update(custom_config)
                logger.info(f"Configuración cargada desde {config_path}")
            except Exception as e:
                logger.warning(f"Error cargando configuración: {e}")
        
        return default_config
    
    def initialize_models(self) -> bool:
        """
        Inicializa todos los modelos SICAR adaptados para índices.
        
        Returns:
            True si la inicialización fue exitosa
        """
        try:
            logger.info("🔧 Inicializando modelos SICAR para índices...")
            
            # Verificar que el mercado esté disponible
            market_status = self.market_hours.is_market_open()
            logger.info(f"📊 Estado del mercado: {market_status}")
            
            # Cargar modelos existentes
            regime_loaded = self.regime_classifier.load_model()
            metacontroller_loaded = self.metacontroller.load_model()
            
            # Entrenar modelos si no existen, usando datos de índices
            if not regime_loaded:
                logger.warning("Modelo de régimen no encontrado, entrenando con datos de índices...")
                success = self._train_regime_model()
                if not success:
                    logger.error("Error entrenando modelo de régimen")
                    return False
            
            if not metacontroller_loaded:
                logger.warning("Modelo de metacontrolador no encontrado, entrenando con datos de índices...")
                success = self._train_metacontroller_model()
                if not success:
                    logger.error("Error entrenando modelo de metacontrolador")
                    return False
            
            logger.info("✅ Modelos SICAR para índices inicializados correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error inicializando modelos: {str(e)}")
            return False
    
    def _train_regime_model(self) -> bool:
        """Entrenar modelo de régimen con datos de índices"""
        try:
            # Obtener datos históricos del índice principal
            df = self.data_adapter.get_binance_data(
                symbol='BTCUSDT',  # Se mapea a SPY
                interval='1d',
                limit=500
            )
            
            if df is None or df.empty:
                logger.error("No se pudieron obtener datos para entrenar modelo de régimen")
                return False
            
            # Agregar indicadores técnicos
            processed_data = self.data_pipeline.add_technical_indicators(df)
            
            # Entrenar clasificador de régimen
            self.regime_classifier.train_classifier(processed_data)
            
            logger.info("✅ Modelo de régimen entrenado con datos de índices")
            return True
            
        except Exception as e:
            logger.error(f"Error entrenando modelo de régimen: {e}")
            return False
    
    def _train_metacontroller_model(self) -> bool:
        """Entrenar modelo de metacontrolador con datos de índices"""
        try:
            # Obtener datos históricos
            df = self.data_adapter.get_binance_data(
                symbol='BTCUSDT',  # Se mapea a SPY
                interval='1d',
                limit=500
            )
            
            if df is None or df.empty:
                logger.error("No se pudieron obtener datos para entrenar metacontrolador")
                return False
            
            # Procesar datos
            processed_data = self.data_pipeline.add_technical_indicators(df)
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
                
                logger.info("✅ Modelo de metacontrolador entrenado con datos de índices")
                return True
            else:
                logger.error("No hay datos suficientes para entrenar metacontrolador")
                return False
            
        except Exception as e:
            logger.error(f"Error entrenando metacontrolador: {e}")
            return False
    
    def run_analysis_cycle(self) -> Dict[str, Any]:
        """
        Ejecuta un ciclo completo de análisis para índices.
        
        Returns:
            Diccionario con resultados del análisis
        """
        try:
            logger.info("🔍 Iniciando ciclo de análisis para índices...")
            
            # Verificar horarios de mercado
            market_status = self.market_hours.is_market_open()
            if not market_status.get('is_open', False) and self.config.get('market_hours_filter', True):
                logger.info("🕐 Mercado cerrado, esperando apertura...")
                return {'status': 'market_closed', 'market_status': market_status}
            
            analysis_results = {}
            
            # Analizar cada índice
            for symbol in self.config['symbols']:
                try:
                    logger.info(f"📊 Analizando {symbol}...")
                    
                    # Obtener datos usando el adaptador
                    crypto_symbol = self._get_crypto_mapping(symbol)
                    df = self.data_adapter.get_binance_data(
                        symbol=crypto_symbol,
                        interval=self.config['timeframe'],
                        limit=200
                    )
                    
                    if df is None or df.empty:
                        logger.warning(f"No hay datos disponibles para {symbol}")
                        continue
                    
                    # Análisis técnico específico para índices
                    technical_analysis = self._analyze_technical_indicators(df, symbol)
                    
                    # Análisis de régimen de mercado
                    regime_analysis = self._analyze_market_regime(df, symbol)
                    
                    # Análisis de estrategias específicas
                    strategy_analysis = self._analyze_indices_strategies(df, symbol)
                    
                    # Análisis de riesgo
                    risk_analysis = self._analyze_risk_factors(df, symbol)
                    
                    # Consolidar análisis
                    symbol_analysis = {
                        'symbol': symbol,
                        'timestamp': datetime.now(),
                        'market_status': market_status,
                        'technical': technical_analysis,
                        'regime': regime_analysis,
                        'strategies': strategy_analysis,
                        'risk': risk_analysis,
                        'data_quality': self._assess_data_quality(df)
                    }
                    
                    analysis_results[symbol] = symbol_analysis
                    
                    logger.info(f"✅ Análisis completado para {symbol}")
                    
                except Exception as e:
                    logger.error(f"Error analizando {symbol}: {e}")
                    continue
            
            # Análisis global del portafolio
            portfolio_analysis = self._analyze_portfolio(analysis_results)
            analysis_results['portfolio'] = portfolio_analysis
            
            # Actualizar tiempo de último análisis
            self.last_analysis_time = datetime.now()
            
            logger.info("✅ Ciclo de análisis completado")
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error en ciclo de análisis: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _get_crypto_mapping(self, index_symbol: str) -> str:
        """Obtener mapeo inverso de índice a crypto para compatibilidad"""
        reverse_mapping = {v: k for k, v in CRYPTO_TO_INDICES_MAPPING.items()}
        return reverse_mapping.get(index_symbol, 'BTCUSDT')
    
    def _analyze_technical_indicators(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Análisis de indicadores técnicos específicos para índices"""
        try:
            # Calcular indicadores usando el módulo de índices
            indicators_data = self.indicators.calculate_all_indicators(df)
            
            # Obtener configuración específica del índice
            config = self.config_manager.get_config(symbol)
            
            # Análisis de tendencia
            trend_analysis = self.indicators.analyze_trend(indicators_data, config.trend_config)
            
            # Análisis de momentum
            momentum_analysis = self.indicators.analyze_momentum(indicators_data, config.momentum_config)
            
            # Análisis de volatilidad
            volatility_analysis = self.indicators.analyze_volatility(indicators_data, config.volatility_config)
            
            return {
                'trend': trend_analysis,
                'momentum': momentum_analysis,
                'volatility': volatility_analysis,
                'indicators': indicators_data.iloc[-1].to_dict() if not indicators_data.empty else {}
            }
            
        except Exception as e:
            logger.error(f"Error en análisis técnico para {symbol}: {e}")
            return {}
    
    def _analyze_market_regime(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Análisis de régimen de mercado adaptado para índices"""
        try:
            # Procesar datos para análisis de régimen
            processed_data = self.data_pipeline.add_technical_indicators(df)
            
            # Clasificar régimen
            regime_results = self.regime_classifier.classify_regimes(processed_data)
            
            if regime_results is not None and not regime_results.empty:
                current_regime = regime_results.iloc[-1]
                return {
                    'current_regime': current_regime.to_dict(),
                    'regime_confidence': float(current_regime.get('confidence', 0.0)),
                    'regime_stability': self._calculate_regime_stability(regime_results)
                }
            else:
                return {'current_regime': 'unknown', 'regime_confidence': 0.0}
            
        except Exception as e:
            logger.error(f"Error en análisis de régimen para {symbol}: {e}")
            return {}
    
    def _analyze_indices_strategies(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Análisis de estrategias específicas para índices"""
        try:
            # Obtener configuración del índice
            config = self.config_manager.get_config(symbol)
            
            # Analizar estrategias disponibles
            strategies_results = {}
            
            # Estrategia de momentum
            momentum_signal = self.strategies.momentum_strategy(df, config)
            strategies_results['momentum'] = momentum_signal
            
            # Estrategia de mean reversion
            mean_reversion_signal = self.strategies.mean_reversion_strategy(df, config)
            strategies_results['mean_reversion'] = mean_reversion_signal
            
            # Estrategia de breakout
            breakout_signal = self.strategies.breakout_strategy(df, config)
            strategies_results['breakout'] = breakout_signal
            
            # Estrategia de rotación sectorial
            sector_rotation_signal = self.strategies.sector_rotation_strategy(df, symbol, config)
            strategies_results['sector_rotation'] = sector_rotation_signal
            
            return strategies_results
            
        except Exception as e:
            logger.error(f"Error en análisis de estrategias para {symbol}: {e}")
            return {}
    
    def _analyze_risk_factors(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Análisis de factores de riesgo específicos para índices"""
        try:
            # Obtener configuración del índice
            config = self.config_manager.get_config(symbol)
            
            # Calcular métricas de riesgo
            risk_metrics = self.risk_manager.calculate_risk_metrics(df, config)
            
            # Evaluar riesgo de posición
            current_price = df['Close'].iloc[-1] if not df.empty else 0
            position_risk = self.risk_manager.evaluate_position_risk(
                symbol, current_price, 'long', 1.0, config
            )
            
            # Verificar límites de riesgo
            risk_limits = self.risk_manager.check_risk_limits(symbol, config)
            
            return {
                'metrics': risk_metrics,
                'position_risk': position_risk,
                'risk_limits': risk_limits,
                'volatility_regime': self._classify_volatility_regime(df)
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de riesgo para {symbol}: {e}")
            return {}
    
    def _assess_data_quality(self, df: pd.DataFrame) -> Dict:
        """Evaluar calidad de los datos"""
        try:
            if df.empty:
                return {'quality_score': 0.0, 'issues': ['no_data']}
            
            issues = []
            quality_score = 1.0
            
            # Verificar datos faltantes
            missing_pct = df.isnull().sum().sum() / (len(df) * len(df.columns))
            if missing_pct > 0.05:  # Más del 5% de datos faltantes
                issues.append('missing_data')
                quality_score -= 0.2
            
            # Verificar outliers en precios
            price_changes = df['Close'].pct_change().abs()
            extreme_changes = (price_changes > 0.1).sum()  # Cambios > 10%
            if extreme_changes > len(df) * 0.02:  # Más del 2% de cambios extremos
                issues.append('price_outliers')
                quality_score -= 0.1
            
            # Verificar continuidad temporal
            if len(df) < 50:  # Menos de 50 períodos
                issues.append('insufficient_data')
                quality_score -= 0.3
            
            return {
                'quality_score': max(0.0, quality_score),
                'issues': issues,
                'data_points': len(df),
                'missing_pct': missing_pct
            }
            
        except Exception as e:
            logger.error(f"Error evaluando calidad de datos: {e}")
            return {'quality_score': 0.0, 'issues': ['evaluation_error']}
    
    def _analyze_portfolio(self, analysis_results: Dict) -> Dict:
        """Análisis global del portafolio de índices"""
        try:
            portfolio_metrics = {
                'total_symbols': len([k for k in analysis_results.keys() if k != 'portfolio']),
                'analyzed_symbols': len([k for k, v in analysis_results.items() 
                                       if k != 'portfolio' and v.get('technical')]),
                'average_quality': np.mean([v.get('data_quality', {}).get('quality_score', 0) 
                                          for k, v in analysis_results.items() if k != 'portfolio']),
                'risk_distribution': self._calculate_risk_distribution(analysis_results),
                'correlation_analysis': self._analyze_correlations(analysis_results),
                'sector_allocation': self._analyze_sector_allocation(analysis_results)
            }
            
            return portfolio_metrics
            
        except Exception as e:
            logger.error(f"Error en análisis de portafolio: {e}")
            return {}
    
    def _calculate_regime_stability(self, regime_results: pd.DataFrame) -> float:
        """Calcular estabilidad del régimen"""
        try:
            if len(regime_results) < 10:
                return 0.5
            
            # Calcular cambios de régimen en los últimos 10 períodos
            recent_regimes = regime_results.tail(10)
            regime_changes = (recent_regimes != recent_regimes.shift(1)).sum().sum()
            
            # Estabilidad inversa a los cambios
            stability = max(0.0, 1.0 - (regime_changes / len(recent_regimes)))
            return stability
            
        except Exception as e:
            logger.error(f"Error calculando estabilidad de régimen: {e}")
            return 0.5
    
    def _classify_volatility_regime(self, df: pd.DataFrame) -> str:
        """Clasificar régimen de volatilidad"""
        try:
            if df.empty or len(df) < 20:
                return 'unknown'
            
            # Calcular volatilidad reciente
            returns = df['Close'].pct_change().dropna()
            recent_vol = returns.tail(20).std() * np.sqrt(252)  # Volatilidad anualizada
            
            # Clasificar régimen
            if recent_vol < 0.15:
                return 'low_volatility'
            elif recent_vol < 0.25:
                return 'normal_volatility'
            else:
                return 'high_volatility'
                
        except Exception as e:
            logger.error(f"Error clasificando volatilidad: {e}")
            return 'unknown'
    
    def _calculate_risk_distribution(self, analysis_results: Dict) -> Dict:
        """Calcular distribución de riesgo en el portafolio"""
        try:
            risk_levels = {'low': 0, 'medium': 0, 'high': 0}
            
            for symbol, analysis in analysis_results.items():
                if symbol == 'portfolio':
                    continue
                
                risk_data = analysis.get('risk', {})
                volatility_regime = risk_data.get('volatility_regime', 'unknown')
                
                if volatility_regime == 'low_volatility':
                    risk_levels['low'] += 1
                elif volatility_regime == 'normal_volatility':
                    risk_levels['medium'] += 1
                else:
                    risk_levels['high'] += 1
            
            return risk_levels
            
        except Exception as e:
            logger.error(f"Error calculando distribución de riesgo: {e}")
            return {'low': 0, 'medium': 0, 'high': 0}
    
    def _analyze_correlations(self, analysis_results: Dict) -> Dict:
        """Analizar correlaciones entre índices"""
        try:
            # Simplificado - en implementación real se calcularían correlaciones históricas
            return {
                'SPY_QQQ': 0.85,  # Correlación típica S&P 500 - NASDAQ
                'SPY_DIA': 0.90,  # Correlación típica S&P 500 - Dow Jones
                'SPY_IWM': 0.75,  # Correlación típica S&P 500 - Russell 2000
                'diversification_score': 0.7
            }
            
        except Exception as e:
            logger.error(f"Error analizando correlaciones: {e}")
            return {}
    
    def _analyze_sector_allocation(self, analysis_results: Dict) -> Dict:
        """Analizar asignación sectorial"""
        try:
            # Mapeo simplificado de índices a sectores
            sector_mapping = {
                'SPY': 'broad_market',
                'QQQ': 'technology',
                'DIA': 'industrial',
                'IWM': 'small_cap'
            }
            
            allocation = {}
            for symbol in self.config['symbols']:
                sector = sector_mapping.get(symbol, 'unknown')
                weight = self.config['capital_allocation'].get(symbol, 0)
                allocation[sector] = allocation.get(sector, 0) + weight
            
            return allocation
            
        except Exception as e:
            logger.error(f"Error analizando asignación sectorial: {e}")
            return {}
    
    def check_kill_switch(self) -> bool:
        """
        Verificar kill switch adaptado para índices.
        
        Returns:
            True si se debe parar el bot
        """
        try:
            # Calcular drawdown actual
            if self.current_value < self.peak_value:
                current_drawdown = (self.peak_value - self.current_value) / self.peak_value
                
                if current_drawdown > self.max_drawdown:
                    self.max_drawdown = current_drawdown
                
                # Verificar límite de drawdown (más conservador para índices)
                if current_drawdown >= self.config['max_drawdown_limit']:
                    logger.critical(f"🛑 KILL SWITCH ACTIVADO: Drawdown {current_drawdown:.2%} excede límite {self.config['max_drawdown_limit']:.2%}")
                    self.kill_switch_triggered = True
                    return True
            else:
                # Nuevo pico de valor
                self.peak_value = self.current_value
            
            return False
            
        except Exception as e:
            logger.error(f"Error verificando kill switch: {str(e)}")
            return False
    
    def run(self):
        """
        Ejecutar el bot de trading para índices.
        """
        try:
            logger.info("🚀 Iniciando Bot SICAR para Índices...")
            
            # Inicializar modelos
            if not self.initialize_models():
                logger.error("Error inicializando modelos, abortando...")
                return
            
            self.is_running = True
            
            while self.is_running:
                try:
                    # Verificar kill switch
                    if self.check_kill_switch():
                        logger.critical("🛑 Kill switch activado, deteniendo bot...")
                        break
                    
                    # Ejecutar ciclo de análisis
                    analysis_results = self.run_analysis_cycle()
                    
                    if analysis_results.get('status') == 'market_closed':
                        logger.info("💤 Mercado cerrado, esperando...")
                        time.sleep(3600)  # Esperar 1 hora
                        continue
                    
                    # Log de resultados
                    if self.config.get('log_decisions', True):
                        self.decisions_log.append({
                            'timestamp': datetime.now(),
                            'analysis': analysis_results
                        })
                    
                    # Esperar hasta el próximo análisis
                    time.sleep(self.config['analysis_interval'])
                    
                except KeyboardInterrupt:
                    logger.info("🛑 Interrupción del usuario, deteniendo bot...")
                    break
                except Exception as e:
                    logger.error(f"Error en ciclo principal: {e}")
                    time.sleep(60)  # Esperar 1 minuto antes de reintentar
            
            self.is_running = False
            logger.info("🏁 Bot SICAR para Índices detenido")
            
        except Exception as e:
            logger.error(f"Error crítico en bot: {e}")
            self.is_running = False

def main():
    """Función principal para ejecutar el bot"""
    try:
        # Crear y ejecutar bot
        bot = IndicesTradingBot()
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("🛑 Programa interrumpido por el usuario")
    except Exception as e:
        logger.error(f"Error crítico: {e}")

if __name__ == "__main__":
    main()