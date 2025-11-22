#!/usr/bin/env python3
"""
Backtester Multi-Símbolo para SICAR
Permite realizar backtesting con múltiples activos simultáneamente.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import backtrader as bt
from pathlib import Path
import sys
import os

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import TRADING_SYMBOLS, CAPITAL_ALLOCATION, CAPITAL_BASE, RISK_PER_TRADE
from multi_symbol_portfolio import MultiSymbolPortfolio
from module_1_causal import CausalCartographer
from module_2_regime import RegimeClassifier
from module_3_metacontroller import MetaController
from robust_data_fetcher import RobustDataFetcher

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MultiSymbolStrategy(bt.Strategy):
    """
    Estrategia de trading multi-símbolo para SICAR.
    Gestiona múltiples activos con modelos independientes.
    """
    
    params = (
        ('symbols', TRADING_SYMBOLS),
        ('capital_allocation', CAPITAL_ALLOCATION),
        ('risk_per_trade', RISK_PER_TRADE),
        ('stop_loss_pct', 0.05),
        ('take_profit_pct', 0.10),
        ('min_confidence', 0.5),
        ('models', None),  # Diccionario con modelos por símbolo
    )
    
    def __init__(self):
        """Inicializa la estrategia multi-símbolo."""
        logger.info("🚀 Inicializando estrategia multi-símbolo SICAR")
        
        # Inicializar portfolio
        self.portfolio = MultiSymbolPortfolio(
            symbols=self.params.symbols,
            capital_allocation=self.params.capital_allocation
        )
        
        # Mapear datos por símbolo
        self.symbol_data = {}
        self.symbol_orders = {}
        self.symbol_positions = {}
        
        # Inicializar datos para cada símbolo
        for i, symbol in enumerate(self.params.symbols):
            if i < len(self.datas):
                self.symbol_data[symbol] = self.datas[i]
                self.symbol_orders[symbol] = None
                self.symbol_positions[symbol] = None
                logger.info(f"📊 Configurado {symbol} con datos índice {i}")
        
        # Modelos SICAR por símbolo
        self.models = self.params.models or {}
        
        # Archivo de decisiones
        self.decisions_file = Path("../data/processed/multi_symbol_backtest_decisions.csv")
        self.decisions_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Inicializar archivo CSV
        with open(self.decisions_file, 'w') as f:
            f.write("timestamp,symbol,price,regime,regime_confidence,strategy,strategy_confidence,signal,causal_sentiment,position,portfolio_value,symbol_pnl\n")
    
    def next(self):
        """Ejecuta la lógica de trading en cada barra."""
        try:
            current_prices = {}
            
            # Obtener precios actuales de todos los símbolos
            for symbol, data in self.symbol_data.items():
                if len(data) > 0:
                    current_prices[symbol] = data.close[0]
            
            # Actualizar precios en el portfolio
            self.portfolio.update_prices(current_prices)
            
            # Procesar cada símbolo
            for symbol in self.params.symbols:
                if symbol in self.symbol_data and symbol in current_prices:
                    self._process_symbol(symbol, current_prices[symbol])
                    
        except Exception as e:
            logger.error(f"Error en next(): {str(e)}")
    
    def _process_symbol(self, symbol: str, current_price: float):
        """
        Procesa un símbolo específico para decisiones de trading.
        
        Args:
            symbol: Símbolo a procesar
            current_price: Precio actual del símbolo
        """
        try:
            data = self.symbol_data[symbol]
            
            # Verificar que tenemos suficientes datos
            if len(data) < 50:
                return
            
            # Obtener datos de mercado
            market_data = self._get_market_data(symbol, data)
            
            # Análisis de régimen
            regime_info = self._analyze_regime(symbol, market_data)
            
            # Análisis causal (simplificado para backtesting)
            causal_info = {'sentiment': 0.0}
            
            # Decisión de estrategia
            strategy_decision = self._get_strategy_decision(symbol, market_data, regime_info, causal_info)
            
            # Ejecutar decisión de trading
            self._execute_trading_decision(symbol, strategy_decision, current_price)
            
            # Registrar decisión
            self._log_decision(symbol, market_data, regime_info, causal_info, strategy_decision)
            
        except Exception as e:
            logger.error(f"Error procesando {symbol}: {str(e)}")
    
    def _get_market_data(self, symbol: str, data) -> Dict[str, Any]:
        """
        Obtiene datos de mercado para el símbolo.
        
        Args:
            symbol: Símbolo del activo
            data: Datos de backtrader
            
        Returns:
            Diccionario con datos de mercado
        """
        try:
            # Obtener datos históricos
            lookback = min(100, len(data))
            
            closes = np.array([data.close[-i] for i in range(lookback-1, -1, -1)])
            volumes = np.array([data.volume[-i] for i in range(lookback-1, -1, -1)])
            highs = np.array([data.high[-i] for i in range(lookback-1, -1, -1)])
            lows = np.array([data.low[-i] for i in range(lookback-1, -1, -1)])
            
            # Crear DataFrame
            df = pd.DataFrame({
                'close': closes,
                'volume': volumes,
                'high': highs,
                'low': lows
            })
            
            # Calcular indicadores técnicos
            df['returns'] = df['close'].pct_change()
            df['volatility'] = df['returns'].rolling(20).std()
            df['sma_20'] = df['close'].rolling(20).mean()
            df['sma_50'] = df['close'].rolling(50).mean()
            
            return {
                'symbol': symbol,
                'current_price': data.close[0],
                'dataframe': df,
                'timestamp': data.datetime.datetime(0)
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de mercado para {symbol}: {str(e)}")
            return {'symbol': symbol, 'current_price': data.close[0], 'dataframe': pd.DataFrame()}
    
    def _analyze_regime(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analiza el régimen de mercado para el símbolo.
        
        Args:
            symbol: Símbolo del activo
            market_data: Datos de mercado
            
        Returns:
            Información del régimen
        """
        try:
            if symbol in self.models and 'regime_classifier' in self.models[symbol]:
                regime_classifier = self.models[symbol]['regime_classifier']
                df = market_data['dataframe']
                
                if len(df) > 20:
                    regime, confidence = regime_classifier.classify_current_regime(df)
                    return {
                        'regime': regime,
                        'confidence': confidence
                    }
            
            return {'regime': 'Desconocido', 'confidence': 0.0}
            
        except Exception as e:
            logger.error(f"Error analizando régimen para {symbol}: {str(e)}")
            return {'regime': 'Desconocido', 'confidence': 0.0}
    
    def _get_strategy_decision(self, symbol: str, market_data: Dict[str, Any], 
                             regime_info: Dict[str, Any], causal_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Obtiene la decisión de estrategia para el símbolo.
        
        Args:
            symbol: Símbolo del activo
            market_data: Datos de mercado
            regime_info: Información del régimen
            causal_info: Información causal
            
        Returns:
            Decisión de estrategia
        """
        try:
            if symbol in self.models and 'metacontroller' in self.models[symbol]:
                metacontroller = self.models[symbol]['metacontroller']
                df = market_data['dataframe']
                
                if len(df) > 20:
                    strategy, confidence = metacontroller.select_strategy(
                        df, regime_info['regime'], causal_info['sentiment']
                    )
                    signal = metacontroller.execute_strategy(strategy, df)
                    
                    return {
                        'strategy': strategy,
                        'confidence': confidence,
                        'signal': signal
                    }
            
            return {'strategy': 'hold', 'confidence': 0.0, 'signal': 0.0}
            
        except Exception as e:
            logger.error(f"Error obteniendo decisión de estrategia para {symbol}: {str(e)}")
            return {'strategy': 'hold', 'confidence': 0.0, 'signal': 0.0}
    
    def _execute_trading_decision(self, symbol: str, strategy_decision: Dict[str, Any], current_price: float):
        """
        Ejecuta la decisión de trading para el símbolo.
        
        Args:
            symbol: Símbolo del activo
            strategy_decision: Decisión de estrategia
            current_price: Precio actual
        """
        try:
            signal = strategy_decision['signal']
            confidence = strategy_decision['confidence']
            
            # Verificar confianza mínima
            if confidence < self.params.min_confidence:
                return
            
            # Gestión de posiciones existentes
            if self.portfolio.is_position_open(symbol):
                self._manage_existing_position(symbol, current_price)
            
            # Nueva entrada si no hay posición y señal fuerte
            if not self.portfolio.is_position_open(symbol) and abs(signal) > 0.5:
                self._enter_new_position(symbol, signal, current_price)
                
        except Exception as e:
            logger.error(f"Error ejecutando decisión de trading para {symbol}: {str(e)}")
    
    def _enter_new_position(self, symbol: str, signal: float, current_price: float):
        """
        Entra en una nueva posición para el símbolo.
        
        Args:
            symbol: Símbolo del activo
            signal: Señal de trading
            current_price: Precio actual
        """
        try:
            # Obtener capital disponible para este símbolo
            available_capital = self.portfolio.get_available_capital(symbol)
            risk_amount = available_capital * self.params.risk_per_trade
            
            # Calcular tamaño de posición
            size = max(0.001, risk_amount / current_price)
            
            if signal < 0:  # Señal de venta (posición corta)
                size = -size
            
            logger.info(f"Intentando nueva posición en {symbol}: signal={signal}, price={current_price}, size={size}")
            
            # Abrir posición en el portfolio
            if self.portfolio.open_position(symbol, size, current_price):
                # Ejecutar orden en backtrader
                if signal > 0:
                    order = self.buy(data=self.symbol_data[symbol], size=abs(size))
                else:
                    order = self.sell(data=self.symbol_data[symbol], size=abs(size))
                
                self.symbol_orders[symbol] = order
                logger.info(f"✅ Posición abierta en {symbol}: {size:.6f} @ ${current_price:.2f}")
                
        except Exception as e:
            logger.error(f"Error entrando nueva posición en {symbol}: {str(e)}")
    
    def _manage_existing_position(self, symbol: str, current_price: float):
        """
        Gestiona posiciones existentes (stop loss, take profit).
        
        Args:
            symbol: Símbolo del activo
            current_price: Precio actual
        """
        try:
            position = self.portfolio.positions[symbol]
            
            if not position.is_open:
                return
            
            # Calcular precios de stop loss y take profit
            if position.size > 0:  # Posición larga
                stop_loss_price = position.entry_price * (1 - self.params.stop_loss_pct)
                take_profit_price = position.entry_price * (1 + self.params.take_profit_pct)
                
                if current_price <= stop_loss_price or current_price >= take_profit_price:
                    self._close_position(symbol, current_price)
                    
            else:  # Posición corta
                stop_loss_price = position.entry_price * (1 + self.params.stop_loss_pct)
                take_profit_price = position.entry_price * (1 - self.params.take_profit_pct)
                
                if current_price >= stop_loss_price or current_price <= take_profit_price:
                    self._close_position(symbol, current_price)
                    
        except Exception as e:
            logger.error(f"Error gestionando posición existente en {symbol}: {str(e)}")
    
    def _close_position(self, symbol: str, exit_price: float):
        """
        Cierra la posición para el símbolo.
        
        Args:
            symbol: Símbolo del activo
            exit_price: Precio de salida
        """
        try:
            # Cerrar posición en el portfolio
            pnl = self.portfolio.close_position(symbol, exit_price)
            
            if pnl is not None:
                # Cerrar orden en backtrader
                if self.symbol_orders[symbol]:
                    self.close(data=self.symbol_data[symbol])
                    self.symbol_orders[symbol] = None
                
                logger.info(f"✅ Posición cerrada en {symbol} @ ${exit_price:.2f} | PnL: ${pnl:.2f}")
                
        except Exception as e:
            logger.error(f"Error cerrando posición en {symbol}: {str(e)}")
    
    def _log_decision(self, symbol: str, market_data: Dict[str, Any], regime_info: Dict[str, Any], 
                     causal_info: Dict[str, Any], strategy_decision: Dict[str, Any]):
        """
        Registra la decisión para análisis posterior.
        
        Args:
            symbol: Símbolo del activo
            market_data: Datos de mercado
            regime_info: Información del régimen
            causal_info: Información causal
            strategy_decision: Decisión de estrategia
        """
        try:
            timestamp = market_data.get('timestamp', datetime.now())
            current_price = market_data['current_price']
            
            # Obtener información de posición
            position_info = ""
            symbol_pnl = 0.0
            
            if symbol in self.portfolio.positions:
                position = self.portfolio.positions[symbol]
                if position.is_open:
                    position_info = "long" if position.size > 0 else "short"
                    symbol_pnl = position.unrealized_pnl
            
            # Obtener valor total del portfolio
            portfolio_summary = self.portfolio.get_portfolio_summary()
            portfolio_value = portfolio_summary['total_value']
            
            # Escribir al archivo CSV
            with open(self.decisions_file, 'a') as f:
                f.write(f"{timestamp},{symbol},{current_price:.2f},{regime_info['regime']},{regime_info['confidence']:.6f},"
                       f"{strategy_decision['strategy']},{strategy_decision['confidence']:.6f},{strategy_decision['signal']:.1f},"
                       f"{causal_info['sentiment']:.1f},{position_info},{portfolio_value:.2f},{symbol_pnl:.2f}\n")
                
        except Exception as e:
            logger.error(f"Error registrando decisión para {symbol}: {str(e)}")


def load_models_for_symbols(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Carga los modelos entrenados para cada símbolo.
    
    Args:
        symbols: Lista de símbolos
        
    Returns:
        Diccionario con modelos por símbolo
    """
    models = {}
    
    for symbol in symbols:
        try:
            # Por ahora, usar los mismos modelos para todos los símbolos
            # En el futuro, se pueden entrenar modelos específicos por símbolo
            
            # Cargar modelos
            regime_classifier = RegimeClassifier()
            regime_classifier.load_model("../models/regime_classifier.joblib")
            
            metacontroller = MetaController()
            metacontroller.load_model("../models/metacontroller.joblib")
            
            causal_cartographer = CausalCartographer()
            
            models[symbol] = {
                'regime_classifier': regime_classifier,
                'metacontroller': metacontroller,
                'causal_cartographer': causal_cartographer
            }
            
            logger.info(f"✅ Modelos cargados para {symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error cargando modelos para {symbol}: {str(e)}")
            models[symbol] = {}
    
    return models


def run_multi_symbol_backtest():
    """Ejecuta el backtesting multi-símbolo."""
    logger.info("🚀 Iniciando backtesting multi-símbolo SICAR")
    
    try:
        # Cargar modelos
        models = load_models_for_symbols(TRADING_SYMBOLS)
        
        # Configurar cerebro de backtrader
        cerebro = bt.Cerebro()
        
        # Cargar datos para cada símbolo
        data_fetcher = RobustDataFetcher()
        
        for symbol in TRADING_SYMBOLS:
            logger.info(f"📊 Cargando datos para {symbol}")
            
            # Obtener datos históricos
            df = data_fetcher.get_market_data(
                symbol=symbol,
                interval='4h',
                limit=500
            )
            
            if df is not None and len(df) > 0:
                # Convertir a formato backtrader
                data = bt.feeds.PandasData(
                    dataname=df,
                    datetime=None,  # Usar el índice como datetime
                    open='Open',
                    high='High',
                    low='Low',
                    close='Close',
                    volume='Volume'
                )
                
                cerebro.adddata(data, name=symbol)
                logger.info(f"✅ Datos cargados para {symbol}: {len(df)} barras")
            else:
                logger.error(f"❌ No se pudieron cargar datos para {symbol}")
        
        # Agregar estrategia
        cerebro.addstrategy(
            MultiSymbolStrategy,
            symbols=TRADING_SYMBOLS,
            capital_allocation=CAPITAL_ALLOCATION,
            models=models
        )
        
        # Configurar broker
        cerebro.broker.setcash(CAPITAL_BASE)
        cerebro.broker.setcommission(commission=0.001)
        
        # Agregar analizadores
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        
        # Ejecutar backtesting
        logger.info("🔄 Ejecutando backtesting...")
        results = cerebro.run()
        
        # Mostrar resultados
        strategy = results[0]
        
        logger.info("📊 RESULTADOS DEL BACKTESTING MULTI-SÍMBOLO:")
        logger.info(f"💰 Valor final del portafolio: ${cerebro.broker.getvalue():.2f}")
        logger.info(f"📈 Retorno total: {((cerebro.broker.getvalue() - CAPITAL_BASE) / CAPITAL_BASE) * 100:.2f}%")
        
        # Mostrar métricas por analizador
        if hasattr(strategy.analyzers.sharpe, 'get_analysis'):
            sharpe = strategy.analyzers.sharpe.get_analysis()
            if 'sharperatio' in sharpe:
                logger.info(f"📊 Sharpe Ratio: {sharpe['sharperatio']:.3f}")
        
        if hasattr(strategy.analyzers.drawdown, 'get_analysis'):
            drawdown = strategy.analyzers.drawdown.get_analysis()
            if 'max' in drawdown:
                logger.info(f"📉 Máximo Drawdown: {drawdown['max']['drawdown']:.2f}%")
        
        # Mostrar resumen del portfolio
        portfolio_summary = strategy.portfolio.get_portfolio_summary()
        logger.info("\n💼 RESUMEN DEL PORTFOLIO:")
        for symbol, position in portfolio_summary['positions'].items():
            logger.info(f"   📊 {symbol}:")
            logger.info(f"      💰 Capital asignado: ${position['allocated_capital']:.2f}")
            logger.info(f"      💵 Capital disponible: ${position['available_capital']:.2f}")
            logger.info(f"      📈 PnL no realizado: ${position['unrealized_pnl']:.2f}")
            logger.info(f"      📊 Posición: {'Abierta' if position['is_open'] else 'Cerrada'}")
        
        logger.info(f"\n✅ Archivo de decisiones guardado en: {strategy.decisions_file}")
        logger.info("🎉 Backtesting multi-símbolo completado exitosamente")
        
    except Exception as e:
        logger.error(f"❌ Error en backtesting multi-símbolo: {str(e)}")
        raise


if __name__ == "__main__":
    run_multi_symbol_backtest()