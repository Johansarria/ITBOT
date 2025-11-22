# /src/backtester.py

import backtrader as bt
import pandas as pd
import numpy as np
import os
import sys
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar módulos SICAR
from pipelines.data_pipeline import DataPipeline
from module_1_causal import CausalCartographer
from module_2_regime import RegimeClassifier
from module_3_metacontroller import MetaController, create_labels
from config import *

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SicarStrategy(bt.Strategy):
    """
    Estrategia SICAR que integra todos los módulos:
    - Módulo 1: Análisis causal de noticias
    - Módulo 2: Clasificación de regímenes de mercado
    - Módulo 3: Metacontrolador para selección de estrategias
    """
    
    params = (
        ('risk_per_trade', 0.02),  # 2% de riesgo por operación
        ('max_positions', 1),      # Máximo 1 posición abierta
        ('stop_loss_pct', 0.05),   # Stop loss del 5%
        ('take_profit_pct', 0.10), # Take profit del 10%
        ('min_confidence', 0.5),   # Confianza mínima para operar
        ('metacontroller', None),  # Instancia del metacontrolador
        ('regime_classifier', None),  # Instancia del clasificador de regímenes
        ('causal_cartographer', None),  # Instancia del cartógrafo causal
    )
    
    def __init__(self):
        """Inicializa la estrategia SICAR."""
        self.metacontroller = self.params.metacontroller
        self.regime_classifier = self.params.regime_classifier
        self.causal_cartographer = self.params.causal_cartographer
        
        # Variables de estado
        self.current_position = None
        self.entry_price = None
        self.stop_loss_price = None
        self.take_profit_price = None
        
        # Métricas de rendimiento
        self.trades_count = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        
        # Datos para análisis
        self.market_data = []
        self.decisions_log = []
        
        logger.info("Estrategia SICAR inicializada")
    
    def set_models(self, metacontroller, regime_classifier, causal_cartographer):
        """
        Establece los modelos entrenados para la estrategia.
        
        Args:
            metacontroller: Instancia del metacontrolador entrenado
            regime_classifier: Instancia del clasificador de regímenes entrenado
            causal_cartographer: Instancia del cartógrafo causal
        """
        self.metacontroller = metacontroller
        self.regime_classifier = regime_classifier
        self.causal_cartographer = causal_cartographer
        logger.info("Modelos SICAR configurados en la estrategia")
    
    def next(self):
        """
        Lógica principal de la estrategia ejecutada en cada barra.
        """
        try:
            # Verificar que tenemos suficientes datos
            if len(self.data) < 50:
                return
            
            # Recopilar datos de mercado actuales
            current_data = self._get_current_market_data()
            
            # Análisis de régimen (Módulo 2)
            regime_info = self._analyze_regime(current_data)
            
            # Análisis causal (Módulo 1) - simulado para backtesting
            causal_info = self._analyze_causal_factors()
            
            # Decisión del metacontrolador (Módulo 3)
            strategy_decision = self._get_strategy_decision(current_data, regime_info, causal_info)
            
            # Ejecutar decisión de trading
            self._execute_trading_decision(strategy_decision)
            
            # Registrar decisión para análisis posterior
            self._log_decision(current_data, regime_info, causal_info, strategy_decision)
            
        except Exception as e:
            logger.error(f"Error en next(): {str(e)}")
    
    def _get_current_market_data(self):
        """
        Recopila los datos de mercado actuales para análisis.
        
        Returns:
            DataFrame con datos de mercado
        """
        try:
            # Obtener las últimas 100 barras para análisis
            lookback = min(100, len(self.data))
            
            data = {
                'open': [self.data.open[-i] for i in range(lookback, 0, -1)],
                'high': [self.data.high[-i] for i in range(lookback, 0, -1)],
                'low': [self.data.low[-i] for i in range(lookback, 0, -1)],
                'close': [self.data.close[-i] for i in range(lookback, 0, -1)],
                'volume': [self.data.volume[-i] for i in range(lookback, 0, -1)]
            }
            
            # Crear índice temporal
            current_time = self.data.datetime.datetime(0)
            dates = [current_time - timedelta(hours=4*i) for i in range(lookback-1, -1, -1)]
            
            df = pd.DataFrame(data, index=dates)
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de mercado: {str(e)}")
            return pd.DataFrame()
    
    def _analyze_regime(self, market_data):
        """
        Analiza el régimen de mercado actual usando el Módulo 2.
        
        Args:
            market_data: DataFrame con datos de mercado
            
        Returns:
            Diccionario con información del régimen
        """
        try:
            if self.regime_classifier is None or market_data.empty:
                return {'regime': 0, 'confidence': 0.0, 'regime_name': 'Desconocido'}
            
            # Clasificar régimen actual
            regime_results = self.regime_classifier.classify_regimes(market_data)
            
            if regime_results.empty:
                return {'regime': 0, 'confidence': 0.0, 'regime_name': 'Desconocido'}
            
            current_regime = regime_results.iloc[-1]
            regime_name = self.regime_classifier.regime_names.get(current_regime['regime'], 'Desconocido')
            
            return {
                'regime': current_regime['regime'],
                'confidence': current_regime.get('confidence', 0.0),
                'regime_name': regime_name
            }
            
        except Exception as e:
            logger.error(f"Error analizando régimen: {str(e)}")
            return {'regime': 0, 'confidence': 0.0, 'regime_name': 'Error'}
    
    def _analyze_causal_factors(self):
        """
        Analiza factores causales (simulado para backtesting).
        
        Returns:
            Diccionario con información causal
        """
        try:
            # En backtesting, simulamos el análisis causal
            # En producción, esto usaría noticias reales
            
            # Simular sentimiento basado en volatilidad reciente
            recent_volatility = np.std([self.data.close[-i] for i in range(1, 21)])
            avg_volatility = np.mean([np.std([self.data.close[-i-j] for j in range(20)]) 
                                    for i in range(21, 41)])
            
            if recent_volatility > avg_volatility * 1.5:
                sentiment = -0.3  # Volatilidad alta = sentimiento negativo
            elif recent_volatility < avg_volatility * 0.7:
                sentiment = 0.2   # Volatilidad baja = sentimiento positivo
            else:
                sentiment = 0.0   # Neutral
            
            return {
                'sentiment': sentiment,
                'causal_strength': abs(sentiment),
                'news_count': np.random.randint(5, 20),
                'primary_factors': ['volatilidad', 'momentum']
            }
            
        except Exception as e:
            logger.error(f"Error analizando factores causales: {str(e)}")
            return {'sentiment': 0.0, 'causal_strength': 0.0, 'news_count': 0, 'primary_factors': []}
    
    def _get_strategy_decision(self, market_data, regime_info, causal_info):
        """
        Obtiene la decisión de estrategia del metacontrolador.
        
        Args:
            market_data: DataFrame con datos de mercado
            regime_info: Información del régimen
            causal_info: Información causal
            
        Returns:
            Diccionario con decisión de estrategia
        """
        try:
            if self.metacontroller is None or market_data.empty:
                return {'strategy': 'hold', 'confidence': 0.0, 'signal': 0.0}
            
            # Preparar características para el metacontrolador
            features = self.metacontroller.prepare_features(market_data)
            
            if features.empty:
                return {'strategy': 'hold', 'confidence': 0.0, 'signal': 0.0}
            
            # Obtener predicción de estrategia
            strategy, confidence = self.metacontroller.predict_strategy(features)
            
            # Ejecutar estrategia para obtener señal
            signal = self.metacontroller.execute_strategy(strategy, market_data)
            
            return {
                'strategy': strategy,
                'confidence': confidence,
                'signal': signal
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo decisión de estrategia: {str(e)}")
            return {'strategy': 'hold', 'confidence': 0.0, 'signal': 0.0}
    
    def _execute_trading_decision(self, strategy_decision):
        """
        Ejecuta la decisión de trading basada en la estrategia.
        
        Args:
            strategy_decision: Diccionario con decisión de estrategia
        """
        try:
            signal = strategy_decision['signal']
            confidence = strategy_decision['confidence']
            
            # Verificar confianza mínima
            if confidence < self.params.min_confidence:
                return
            
            current_price = self.data.close[0]
            
            # Gestión de posiciones existentes
            if self.current_position is not None:
                self._manage_existing_position(current_price)
            
            # Nueva entrada si no hay posición
            if self.current_position is None and abs(signal) > 0.5:
                self._enter_new_position(signal, current_price)
                
        except Exception as e:
            logger.error(f"Error ejecutando decisión de trading: {str(e)}")
    
    def _manage_existing_position(self, current_price):
        """
        Gestiona posiciones existentes (stop loss, take profit).
        
        Args:
            current_price: Precio actual
        """
        try:
            if self.current_position == 'long':
                # Verificar stop loss o take profit para posición larga
                if current_price <= self.stop_loss_price:
                    self.sell(size=self.position.size)
                    logger.info(f"Stop loss ejecutado en {current_price}")
                elif current_price >= self.take_profit_price:
                    self.sell(size=self.position.size)
                    logger.info(f"Take profit ejecutado en {current_price}")
                    
            elif self.current_position == 'short':
                # Verificar stop loss o take profit para posición corta
                if current_price >= self.stop_loss_price:
                    self.buy(size=abs(self.position.size))
                    logger.info(f"Stop loss ejecutado en {current_price}")
                elif current_price <= self.take_profit_price:
                    self.buy(size=abs(self.position.size))
                    logger.info(f"Take profit ejecutado en {current_price}")
                    
        except Exception as e:
            logger.error(f"Error gestionando posición existente: {str(e)}")
    
    def _enter_new_position(self, signal, current_price):
        """
        Entra en una nueva posición.
        
        Args:
            signal: Señal de trading
            current_price: Precio actual
        """
        try:
            # Calcular tamaño de posición basado en riesgo
            account_value = self.broker.getvalue()
            risk_amount = account_value * self.params.risk_per_trade
            
            logger.info(f"Intentando nueva posición: signal={signal}, price={current_price}, account_value={account_value}, risk_amount={risk_amount}")
            
            if signal > 0:  # Señal de compra
                stop_loss_price = current_price * (1 - self.params.stop_loss_pct)
                take_profit_price = current_price * (1 + self.params.take_profit_pct)
                
                # Calcular tamaño basado en stop loss
                risk_per_share = current_price - stop_loss_price
                logger.info(f"Compra: risk_per_share={risk_per_share}")
                
                if risk_per_share > 0:
                    # Usar un tamaño mínimo para crypto (fracciones)
                    size = max(0.001, risk_amount / current_price)  # Al menos 0.001 unidades
                    logger.info(f"Tamaño calculado: {size}")
                    
                    if size > 0:
                        self.buy(size=size)
                        self.current_position = 'long'
                        self.entry_price = current_price
                        self.stop_loss_price = stop_loss_price
                        self.take_profit_price = take_profit_price
                        logger.info(f"Posición larga abierta: {size} unidades a {current_price}")
                        
            elif signal < 0:  # Señal de venta
                stop_loss_price = current_price * (1 + self.params.stop_loss_pct)
                take_profit_price = current_price * (1 - self.params.take_profit_pct)
                
                # Calcular tamaño basado en stop loss
                risk_per_share = stop_loss_price - current_price
                logger.info(f"Venta: risk_per_share={risk_per_share}")
                
                if risk_per_share > 0:
                    # Usar un tamaño mínimo para crypto (fracciones)
                    size = max(0.001, risk_amount / current_price)  # Al menos 0.001 unidades
                    logger.info(f"Tamaño calculado: {size}")
                    
                    if size > 0:
                        self.sell(size=size)
                        self.current_position = 'short'
                        self.entry_price = current_price
                        self.stop_loss_price = stop_loss_price
                        self.take_profit_price = take_profit_price
                        logger.info(f"Posición corta abierta: {size} unidades a {current_price}")
                        
        except Exception as e:
            logger.error(f"Error entrando nueva posición: {str(e)}")
    
    def _log_decision(self, market_data, regime_info, causal_info, strategy_decision):
        """
        Registra la decisión para análisis posterior.
        
        Args:
            market_data: Datos de mercado
            regime_info: Información del régimen
            causal_info: Información causal
            strategy_decision: Decisión de estrategia
        """
        try:
            decision_log = {
                'timestamp': self.data.datetime.datetime(0),
                'price': self.data.close[0],
                'regime': regime_info.get('regime_name', 'Desconocido'),
                'regime_confidence': regime_info.get('confidence', 0.0),
                'strategy': strategy_decision.get('strategy', 'hold'),
                'strategy_confidence': strategy_decision.get('confidence', 0.0),
                'signal': strategy_decision.get('signal', 0.0),
                'causal_sentiment': causal_info.get('sentiment', 0.0),
                'position': self.current_position,
                'portfolio_value': self.broker.getvalue()
            }
            
            self.decisions_log.append(decision_log)
            
        except Exception as e:
            logger.error(f"Error registrando decisión: {str(e)}")
    
    def notify_order(self, order):
        """Notificación de órdenes ejecutadas."""
        if order.status in [order.Completed]:
            if order.isbuy():
                logger.info(f"COMPRA EJECUTADA: {order.executed.size} a {order.executed.price}")
            else:
                logger.info(f"VENTA EJECUTADA: {order.executed.size} a {order.executed.price}")
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning(f"Orden {order.status}")
    
    def notify_trade(self, trade):
        """Notificación de trades cerrados."""
        if trade.isclosed:
            self.trades_count += 1
            pnl = trade.pnl
            self.total_pnl += pnl
            
            if pnl > 0:
                self.winning_trades += 1
                
            logger.info(f"TRADE CERRADO: PnL = {pnl:.2f}, Total PnL = {self.total_pnl:.2f}")
            
            # Resetear posición
            self.current_position = None
            self.entry_price = None
            self.stop_loss_price = None
            self.take_profit_price = None
    
    def stop(self):
        """Función ejecutada al final del backtest."""
        try:
            # Calcular métricas finales
            win_rate = (self.winning_trades / self.trades_count * 100) if self.trades_count > 0 else 0
            final_value = self.broker.getvalue()
            
            logger.info("=== RESULTADOS DEL BACKTEST ===")
            logger.info(f"Valor final del portafolio: ${final_value:.2f}")
            logger.info(f"Total de trades: {self.trades_count}")
            logger.info(f"Trades ganadores: {self.winning_trades}")
            logger.info(f"Tasa de acierto: {win_rate:.1f}%")
            logger.info(f"PnL total: ${self.total_pnl:.2f}")
            
            # Guardar log de decisiones
            if self.decisions_log:
                decisions_df = pd.DataFrame(self.decisions_log)
                log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                      "data", "processed", "backtest_decisions.csv")
                os.makedirs(os.path.dirname(log_path), exist_ok=True)
                decisions_df.to_csv(log_path, index=False)
                logger.info(f"Log de decisiones guardado en {log_path}")
                
        except Exception as e:
            logger.error(f"Error en stop(): {str(e)}")

def run_backtest(symbol='BTCUSDT', start_date='2023-01-01', end_date='2024-01-01'):
    """
    Ejecuta un backtest completo del sistema SICAR.
    
    Args:
        symbol: Símbolo a testear
        start_date: Fecha de inicio
        end_date: Fecha de fin
    """
    try:
        logger.info("=== INICIANDO BACKTEST SICAR ===")
        
        # 1. Preparar datos
        logger.info("Preparando datos...")
        data_pipeline = DataPipeline()
        
        # Descargar datos de mercado (ya incluye indicadores técnicos)
        processed_data = data_pipeline.get_market_data(symbol, period='2y', interval='4h')
        
        if processed_data.empty:
            logger.error("No se pudieron obtener datos de mercado")
            return
        
        logger.info(f"Datos descargados: {len(processed_data)} registros")
        logger.info(f"Rango de fechas disponible: {processed_data.index[0]} a {processed_data.index[-1]}")
        
        # Filtrar por fechas si están dentro del rango disponible
        try:
            if start_date in processed_data.index or end_date in processed_data.index:
                processed_data = processed_data[start_date:end_date]
            else:
                logger.warning(f"Fechas {start_date} - {end_date} no están en el rango disponible")
                logger.info("Usando todos los datos disponibles")
        except Exception as e:
            logger.warning(f"Error filtrando fechas: {e}. Usando todos los datos disponibles")
        
        logger.info(f"Datos después del filtrado: {len(processed_data)} registros")
        
        # 2. Entrenar modelos
        logger.info("Entrenando modelos SICAR...")
        
        # Dividir datos: 70% entrenamiento, 30% testing
        split_idx = int(len(processed_data) * 0.7)
        train_data = processed_data.iloc[:split_idx]
        test_data = processed_data.iloc[split_idx:]
        
        # Entrenar Módulo 2 (Clasificador de Regímenes)
        regime_classifier = RegimeClassifier()
        regime_results = regime_classifier.classify_regimes(train_data)
        
        # Entrenar Módulo 3 (Metacontrolador)
        metacontroller = MetaController()
        
        # Preparar datos para metacontrolador
        regime_results = regime_classifier.classify_regimes(train_data)
        features = metacontroller.prepare_features(train_data, regime_results)
        labels = create_labels(train_data)
        
        # Alinear datos
        aligned_data = pd.concat([features, labels.rename('label')], axis=1).dropna()
        if len(aligned_data) > 0:
            features_aligned = aligned_data.drop(columns=['label'])
            labels_aligned = aligned_data['label']
            metacontroller.train_metacontroller(features_aligned, labels_aligned)
        
        # Módulo 1 (Cartógrafo Causal) - para análisis
        causal_cartographer = CausalCartographer()
        
        # 3. Configurar backtrader
        logger.info("Configurando backtest...")
        cerebro = bt.Cerebro()
        
        # Agregar estrategia con modelos configurados
        cerebro.addstrategy(SicarStrategy, 
                          metacontroller=metacontroller,
                          regime_classifier=regime_classifier, 
                          causal_cartographer=causal_cartographer)
        
        # Preparar datos para backtrader
        bt_data = bt.feeds.PandasData(
            dataname=test_data,
            datetime=None,
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=None
        )
        
        cerebro.adddata(bt_data)
        
        # Configurar broker
        cerebro.broker.setcash(500.0)  # $500 inicial
        cerebro.broker.setcommission(commission=0.001)  # 0.1% comisión
        
        # Agregar analizadores
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        # 4. Ejecutar backtest
        logger.info("Ejecutando backtest...")
        initial_value = cerebro.broker.getvalue()
        
        results = cerebro.run()
        strategy = results[0]
        
        final_value = cerebro.broker.getvalue()
        
        # 5. Mostrar resultados
        logger.info("=== RESULTADOS FINALES ===")
        logger.info(f"Valor inicial: ${initial_value:.2f}")
        logger.info(f"Valor final: ${final_value:.2f}")
        logger.info(f"Retorno total: {((final_value - initial_value) / initial_value * 100):.2f}%")
        
        # Análisis detallado
        try:
            sharpe = strategy.analyzers.sharpe.get_analysis()
            drawdown = strategy.analyzers.drawdown.get_analysis()
            returns = strategy.analyzers.returns.get_analysis()
            trades = strategy.analyzers.trades.get_analysis()
            
            logger.info(f"Sharpe Ratio: {sharpe.get('sharperatio', 'N/A')}")
            logger.info(f"Máximo Drawdown: {drawdown.get('max', {}).get('drawdown', 'N/A'):.2f}%")
            logger.info(f"Total de trades: {trades.get('total', {}).get('total', 0)}")
            logger.info(f"Trades ganadores: {trades.get('won', {}).get('total', 0)}")
            
        except Exception as e:
            logger.warning(f"Error obteniendo análisis detallado: {str(e)}")
        
        # Opcional: Plotear resultados
        try:
            cerebro.plot(style='candlestick', barup='green', bardown='red')
        except Exception as e:
            logger.warning(f"No se pudo generar gráfico: {str(e)}")
        
        logger.info("=== BACKTEST COMPLETADO ===")
        
    except Exception as e:
        logger.error(f"Error en backtest: {str(e)}")

if __name__ == '__main__':
    """
    Ejecuta el backtest principal.
    """
    try:
        # Verificar dependencias
        logger.info("Verificando dependencias...")
        
        # Ejecutar backtest
        run_backtest(
            symbol='BTCUSDT',
            start_date='2023-01-01',
            end_date='2024-01-01'
        )
        
    except Exception as e:
        logger.error(f"Error ejecutando backtest: {str(e)}")
        print(f"❌ Error: {str(e)}")
        print("\nAsegúrate de:")
        print("1. Instalar dependencias: pip install -r requirements.txt")
        print("2. Configurar APIs en .env")
        print("3. Ejecutar primero el data pipeline")