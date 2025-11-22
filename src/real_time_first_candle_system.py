#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISTEMA DE PAPER TRADING EN TIEMPO REAL - PRIMERA VELA
======================================================
Sistema de simulación continua conectado a Binance que ejecuta
la estrategia de primera vela en tiempo real con paper trading
"""

import asyncio
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import websocket
import threading
import time
import requests
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

# Importar sistema de logging avanzado multi-símbolo
from advanced_logging_system import (
    AdvancedLoggingSystem, 
    LogLevel, 
    EventType, 
    PerformanceMetrics,
    DecisionContext,
    MarketConditions,
    ExecutionEvent
)

# Importar módulos de IA para análisis avanzado
from module_1_causal import CausalCartographer
from module_xai import generate_cognitive_report

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('real_time_first_candle.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class RealTimeFirstCandleSystem:
    """Sistema de paper trading en tiempo real para estrategia de primera vela"""
    
    def __init__(self, config_file='first_candle_strategy_config.json'):
        # Cargar configuración
        self.load_config(config_file)
        
        # Inicializar sistema de logging avanzado multi-símbolo
        self.advanced_logger = AdvancedLoggingSystem(symbols=self.config['symbols'])
        self.advanced_logger.start_logging()
        
        # Estado del sistema
        self.is_running = False
        self.current_capital = self.config['capital_management']['initial_capital']
        self.positions = {}
        self.trades_history = []
        self.market_data = {}
        self.indicators = {}
        
        # Conexiones WebSocket
        self.ws_connections = {}
        self.price_data = {}
        
        # Control de sesiones
        self.current_session_date = None
        self.session_trades_count = 0
        self.first_candle_processed = {}
        
        # Métricas de rendimiento por símbolo
        self.symbol_performance = {symbol: {} for symbol in self.config['symbols']}
        self.analysis_start_times = {}
        
        # Inicializar módulos de IA
        try:
            self.causal_cartographer = CausalCartographer()
            self.ai_enabled = True
            logging.info("✅ Módulos de IA inicializados correctamente (Grok xAI + OpenAI)")
        except Exception as e:
            logging.warning(f"⚠️ Error inicializando módulos de IA: {str(e)}")
            self.causal_cartographer = None
            self.ai_enabled = False
        
        # Cache para análisis de narrativa de mercado
        self.market_narrative_cache = {}
        self.last_narrative_update = {}
        
        logging.info("=== SISTEMA DE PAPER TRADING EN TIEMPO REAL INICIALIZADO ===")
        logging.info(f"Capital inicial: ${self.current_capital:.2f}")
        logging.info(f"Símbolos monitoreados: {self.config['symbols']}")
        logging.info(f"IA habilitada: {'✅ SÍ' if self.ai_enabled else '❌ NO'}")
        
        # Log de inicio del sistema con logging avanzado
        self.advanced_logger.log(
            LogLevel.INFO,
            EventType.SYSTEM_START,
            f"Sistema First Candle iniciado con {len(self.config['symbols'])} símbolos: {', '.join(self.config['symbols'])}",
            "FirstCandleSystem",
            data={
                'initial_capital': self.current_capital,
                'symbols_count': len(self.config['symbols']),
                'symbols': self.config['symbols'],
                'ai_enabled': self.ai_enabled
            }
        )

    def load_config(self, config_file):
        """Carga la configuración de la estrategia"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            logging.info(f"Configuración cargada desde {config_file}")
        except FileNotFoundError:
            logging.error(f"Archivo de configuración {config_file} no encontrado")
            raise
        except json.JSONDecodeError:
            logging.error(f"Error al decodificar JSON en {config_file}")
            raise

    def get_binance_klines(self, symbol, interval='1h', limit=100):
        """Obtiene datos históricos de Binance"""
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Convertir a DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convertir tipos de datos
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logging.error(f"Error obteniendo datos de {symbol}: {str(e)}")
            return None

    def calculate_indicators(self, df):
        """Calcula indicadores técnicos en tiempo real"""
        if len(df) < 50:
            return df
        
        # EMAs
        df['ema_9'] = df['close'].ewm(span=self.config['technical_indicators']['ema_fast']).mean()
        df['ema_21'] = df['close'].ewm(span=self.config['technical_indicators']['ema_slow']).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.config['technical_indicators']['rsi_period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.config['technical_indicators']['rsi_period']).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=self.config['technical_indicators']['macd_fast']).mean()
        exp2 = df['close'].ewm(span=self.config['technical_indicators']['macd_slow']).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=self.config['technical_indicators']['macd_signal']).mean()
        
        # Bandas de Bollinger
        df['bb_middle'] = df['close'].rolling(window=self.config['technical_indicators']['bollinger_period']).mean()
        bb_std = df['close'].rolling(window=self.config['technical_indicators']['bollinger_period']).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * self.config['technical_indicators']['bollinger_std'])
        df['bb_lower'] = df['bb_middle'] - (bb_std * self.config['technical_indicators']['bollinger_std'])
        
        # Volumen
        df['volume_avg'] = df['volume'].rolling(window=self.config['technical_indicators']['volume_avg_period']).mean()
        df['volume_ratio'] = df['volume'] / df['volume_avg']
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(window=self.config['technical_indicators']['atr_period']).mean()
        
        # Momentum
        df['momentum'] = df['close'] / df['close'].shift(self.config['technical_indicators']['momentum_period']) - 1
        
        return df

    def get_market_narrative_analysis(self, symbol):
        """Obtiene análisis de narrativa de mercado con Grok xAI"""
        if not self.ai_enabled or not self.causal_cartographer:
            return None
        
        try:
            # Verificar cache (actualizar cada 30 minutos)
            current_time = datetime.now(timezone.utc)
            cache_key = symbol
            
            if (cache_key in self.last_narrative_update and 
                (current_time - self.last_narrative_update[cache_key]).total_seconds() < 1800):
                return self.market_narrative_cache.get(cache_key)
            
            # Obtener análisis de narrativa con Grok xAI
            logging.info(f"🤖 Obteniendo análisis de narrativa de mercado para {symbol} con Grok xAI...")
            narrative_analysis = self.causal_cartographer.analyze_market_narrative_with_grok(symbol)
            
            # Actualizar cache
            self.market_narrative_cache[cache_key] = narrative_analysis
            self.last_narrative_update[cache_key] = current_time
            
            if narrative_analysis and 'dominant_narrative' in narrative_analysis:
                logging.info(f"📊 Narrativa dominante para {symbol}: {narrative_analysis['dominant_narrative']}")
            
            return narrative_analysis
            
        except Exception as e:
            logging.error(f"Error obteniendo análisis de narrativa para {symbol}: {str(e)}")
            return None

    def is_first_candle_of_session(self, timestamp):
        """Verifica si es la primera vela de la sesión"""
        hour = timestamp.hour
        return hour == self.config['strategy_parameters']['session_start_hour']

    def generate_signal(self, symbol, current_data, previous_data):
        """Genera señales de trading en tiempo real"""
        try:
            if len(current_data) < 2:
                return None
            
            current_time = current_data.index[-1]
            
            # Verificar si es primera vela de sesión
            if not self.is_first_candle_of_session(current_time):
                return None
            
            # Verificar si ya procesamos esta sesión
            session_key = f"{symbol}_{current_time.date()}"
            if session_key in self.first_candle_processed:
                return None
            
            # Datos actuales y anteriores
            current_price = current_data.iloc[-1]['close']
            prev_price = current_data.iloc[-2]['close']
            volume_ratio = current_data.iloc[-1]['volume_ratio']
            rsi = current_data.iloc[-1]['rsi']
            macd = current_data.iloc[-1]['macd']
            macd_signal = current_data.iloc[-1]['macd_signal']
            bb_upper = current_data.iloc[-1]['bb_upper']
            bb_lower = current_data.iloc[-1]['bb_lower']
            momentum = current_data.iloc[-1]['momentum']
            
            # Verificar datos válidos
            if pd.isna(rsi) or pd.isna(macd) or pd.isna(volume_ratio):
                return None
            
            # Calcular cambio de precio
            price_change = (current_price - prev_price) / prev_price
            
            # Obtener análisis de narrativa de mercado con Grok xAI
            market_narrative = self.get_market_narrative_analysis(symbol)
            narrative_sentiment = 0.0  # Neutral por defecto
            
            if market_narrative and 'sentiment_score' in market_narrative:
                narrative_sentiment = market_narrative['sentiment_score']
                logging.info(f"🎯 Sentimiento de narrativa para {symbol}: {narrative_sentiment:.3f}")
            
            # CONDICIONES DE SEÑAL
            
            # 1. Breakout de primera vela
            breakout_condition = abs(price_change) >= self.config['strategy_parameters']['breakout_threshold']
            
            # 2. Volumen confirmatorio
            volume_condition = volume_ratio >= self.config['strategy_parameters']['min_volume_ratio']
            
            # 3. Condiciones técnicas (incluyendo sentimiento de narrativa)
            if price_change > 0:  # Señal alcista
                technical_condition = (
                    rsi < self.config['technical_indicators']['rsi_overbought'] and
                    macd > macd_signal and
                    current_price > bb_lower and
                    momentum > -0.02 and
                    narrative_sentiment >= -0.3  # Narrativa no muy negativa
                )
                signal_type = 'BUY'
            else:  # Señal bajista
                technical_condition = (
                    rsi > self.config['technical_indicators']['rsi_oversold'] and
                    macd < macd_signal and
                    current_price < bb_upper and
                    momentum < 0.02 and
                    narrative_sentiment <= 0.3  # Narrativa no muy positiva
                )
                signal_type = 'SELL'
            
            # 4. Filtros de calidad
            candle_size = abs(price_change)
            quality_condition = (
                candle_size >= self.config['strategy_parameters']['min_candle_size'] and
                candle_size <= self.config['strategy_parameters']['max_candle_size']
            )
            
            # Generar señal si todas las condiciones se cumplen
            if (breakout_condition and volume_condition and 
                technical_condition and quality_condition):
                
                # Marcar sesión como procesada
                self.first_candle_processed[session_key] = True
                
                # Calcular confianza mejorada con narrativa
                base_confidence = abs(price_change) * 50 + volume_ratio * 0.2
                narrative_boost = abs(narrative_sentiment) * 0.1 if market_narrative else 0
                final_confidence = min(0.95, base_confidence + narrative_boost)
                
                signal = {
                    'timestamp': current_time,
                    'symbol': symbol,
                    'type': signal_type,
                    'price': current_price,
                    'price_change': price_change,
                    'volume_ratio': volume_ratio,
                    'rsi': rsi,
                    'macd': macd,
                    'momentum': momentum,
                    'confidence': final_confidence,
                    'narrative_sentiment': narrative_sentiment,
                    'market_narrative': market_narrative
                }
                
                logging.info(f"🚨 SEÑAL GENERADA: {signal_type} {symbol} @ ${current_price:.4f} (Confianza: {final_confidence:.2f})")
                if market_narrative:
                    logging.info(f"📊 Narrativa: {market_narrative.get('dominant_narrative', 'N/A')}")
                
                return signal
            
            return None
            
        except Exception as e:
            logging.error(f"Error generando señal para {symbol}: {str(e)}")
            return None

    def execute_paper_trade(self, signal):
        """Ejecuta trade en modo paper trading"""
        execution_start = datetime.now(timezone.utc)
        
        try:
            # Verificar límites diarios
            if self.session_trades_count >= self.config['risk_management']['max_daily_trades']:
                logging.warning("Límite diario de trades alcanzado")
                return False
            
            # Calcular tamaño de posición
            risk_amount = self.current_capital * self.config['risk_management']['max_risk_per_trade']
            stop_loss_pct = self.config['risk_management']['stop_loss_pct']
            position_size = risk_amount / stop_loss_pct
            
            # Verificar capital suficiente
            if position_size > self.current_capital * 0.95:
                position_size = self.current_capital * 0.95
            
            if position_size < 10:  # Mínimo $10 por trade
                logging.warning("Capital insuficiente para trade")
                return False
            
            # Calcular precios de stop loss y take profit
            entry_price = signal['price']
            
            if signal['type'] == 'BUY':
                stop_loss_price = entry_price * (1 - stop_loss_pct)
                take_profit_price = entry_price * (1 + self.config['risk_management']['take_profit_pct'])
            else:  # SELL
                stop_loss_price = entry_price * (1 + stop_loss_pct)
                take_profit_price = entry_price * (1 - self.config['risk_management']['take_profit_pct'])
            
            # Crear posición
            position = {
                'id': f"{signal['symbol']}_{int(signal['timestamp'].timestamp())}",
                'symbol': signal['symbol'],
                'type': signal['type'],
                'entry_price': entry_price,
                'position_size': position_size,
                'stop_loss': stop_loss_price,
                'take_profit': take_profit_price,
                'entry_time': signal['timestamp'],
                'status': 'OPEN'
            }
            
            # Log evento de ejecución
            execution_event = ExecutionEvent(
                timestamp=datetime.now(timezone.utc),
                symbol=signal['symbol'],
                trade_type=signal['type'],
                order_type="MARKET",
                quantity=position_size / entry_price,
                price=entry_price,
                execution_time_ms=(datetime.now(timezone.utc) - execution_start).total_seconds() * 1000,
                fees=0.0,  # Paper trading sin fees
                slippage=0.0,
                order_id=position['id'],
                status="FILLED",
                remaining_capital=self.current_capital - position_size,
                position_size_after=position_size,
                stop_loss=stop_loss_price,
                take_profit=take_profit_price
            )
            
            self.advanced_logger.log_execution_event(execution_event)
            
            # Guardar posición
            self.positions[position['id']] = position
            self.session_trades_count += 1
            
            logging.info(f"✅ TRADE EJECUTADO: {signal['type']} {signal['symbol']}")
            logging.info(f"   Precio entrada: ${entry_price:.4f}")
            logging.info(f"   Tamaño posición: ${position_size:.2f}")
            logging.info(f"   Stop Loss: ${stop_loss_price:.4f}")
            logging.info(f"   Take Profit: ${take_profit_price:.4f}")
            
            # Log al sistema avanzado
            self.advanced_logger.log(
                LogLevel.INFO,
                EventType.TRADE_EXECUTED,
                f"Posición {signal['type']} abierta en {signal['symbol']}",
                "TradeExecutor",
                data={
                    'symbol': signal['symbol'],
                    'trade_type': signal['type'],
                    'entry_price': entry_price,
                    'position_size': position_size,
                    'stop_loss': stop_loss_price,
                    'take_profit': take_profit_price,
                    'capital_remaining': self.current_capital - position_size
                }
            )
            
            # Generar reporte cognitivo con OpenAI
            self.generate_cognitive_report(signal, position)
            
            return True
            
        except Exception as e:
            # Log error de ejecución
            execution_duration = (datetime.now(timezone.utc) - execution_start).total_seconds() * 1000
            
            self.advanced_logger.log(
                LogLevel.ERROR,
                EventType.ERROR,
                f"Error ejecutando trade para {signal.get('symbol', 'UNKNOWN')}: {str(e)}",
                "TradeExecutor",
                data={
                    'symbol': signal.get('symbol', 'UNKNOWN'),
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'signal': signal,
                    'execution_duration_ms': execution_duration
                }
            )
            
            logging.error(f"Error ejecutando trade: {str(e)}")
            return False

    def generate_cognitive_report(self, signal, position):
        """Genera reporte cognitivo con OpenAI para explicar la decisión de trading"""
        if not self.ai_enabled:
            return
        
        try:
            # Preparar datos para el reporte
            strategy_decision = signal['type']
            market_regime = "BREAKOUT_FIRST_CANDLE"
            
            # Factores XAI
            xai_factors = {
                'confidence': signal['confidence'],
                'signal_strength': abs(signal['price_change']),
                'volume_confirmation': signal['volume_ratio'],
                'technical_alignment': {
                    'rsi': signal['rsi'],
                    'macd': signal['macd'],
                    'momentum': signal['momentum']
                }
            }
            
            # Factores causales (narrativa de mercado)
            causal_factors = []
            if signal.get('market_narrative'):
                narrative = signal['market_narrative']
                causal_factors.append({
                    'factor': 'Market Narrative',
                    'description': narrative.get('dominant_narrative', 'N/A'),
                    'sentiment': signal['narrative_sentiment'],
                    'confidence': narrative.get('confidence', 0.5)
                })
            
            # Generar reporte cognitivo
            logging.info(f"🧠 Generando reporte cognitivo para {signal['symbol']} con OpenAI...")
            
            cognitive_report = generate_cognitive_report(
                decision=strategy_decision,
                strategy="First Candle Breakout",
                market_regime=market_regime,
                xai_factors=xai_factors,
                causal_factors=causal_factors
            )
            
            if cognitive_report:
                logging.info(f"📋 Reporte cognitivo generado para {signal['symbol']}")
                logging.info(f"📄 Resumen: {cognitive_report[:200]}...")
                
                # Guardar reporte en el historial de trades
                if hasattr(self, 'trades_history'):
                    trade_record = {
                        'timestamp': signal['timestamp'],
                        'symbol': signal['symbol'],
                        'type': signal['type'],
                        'price': signal['price'],
                        'position_size': position['position_size'],
                        'cognitive_report': cognitive_report,
                        'narrative_sentiment': signal['narrative_sentiment']
                    }
                    self.trades_history.append(trade_record)
            
        except Exception as e:
            logging.error(f"Error generando reporte cognitivo: {str(e)}")

    def check_exit_conditions(self, symbol, current_price):
        """Verifica condiciones de salida para posiciones abiertas"""
        try:
            positions_to_close = []
            
            for pos_id, position in self.positions.items():
                if position['symbol'] != symbol or position['status'] != 'OPEN':
                    continue
                
                should_close = False
                exit_reason = ""
                exit_price = current_price
                
                # Verificar Stop Loss
                if position['type'] == 'BUY' and current_price <= position['stop_loss']:
                    should_close = True
                    exit_reason = "STOP_LOSS"
                elif position['type'] == 'SELL' and current_price >= position['stop_loss']:
                    should_close = True
                    exit_reason = "STOP_LOSS"
                
                # Verificar Take Profit
                elif position['type'] == 'BUY' and current_price >= position['take_profit']:
                    should_close = True
                    exit_reason = "TAKE_PROFIT"
                elif position['type'] == 'SELL' and current_price <= position['take_profit']:
                    should_close = True
                    exit_reason = "TAKE_PROFIT"
                
                if should_close:
                    # Calcular P&L
                    if position['type'] == 'BUY':
                        pnl = (exit_price - position['entry_price']) / position['entry_price'] * position['position_size']
                    else:  # SELL
                        pnl = (position['entry_price'] - exit_price) / position['entry_price'] * position['position_size']
                    
                    # Actualizar capital
                    self.current_capital += pnl
                    
                    # Registrar trade cerrado
                    trade_record = {
                        'id': pos_id,
                        'symbol': symbol,
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'entry_time': position['entry_time'],
                        'exit_time': datetime.now(),
                        'position_size': position['position_size'],
                        'pnl': pnl,
                        'pnl_pct': (pnl / position['position_size']) * 100,
                        'exit_reason': exit_reason,
                        'result': 'WIN' if pnl > 0 else 'LOSS'
                    }
                    
                    self.trades_history.append(trade_record)
                    positions_to_close.append(pos_id)
                    
                    logging.info(f"🔄 TRADE CERRADO: {exit_reason} {symbol}")
                    logging.info(f"   P&L: ${pnl:.2f} ({(pnl/position['position_size'])*100:.2f}%)")
                    logging.info(f"   Capital actual: ${self.current_capital:.2f}")
            
            # Cerrar posiciones
            for pos_id in positions_to_close:
                self.positions[pos_id]['status'] = 'CLOSED'
                
        except Exception as e:
            logging.error(f"Error verificando condiciones de salida: {str(e)}")

    def update_market_data(self, symbol):
        """Actualiza datos de mercado para un símbolo"""
        analysis_start = datetime.now(timezone.utc)
        self.analysis_start_times[symbol] = analysis_start
        
        try:
            # Log inicio de análisis
            self.advanced_logger.log(
                LogLevel.DEBUG,
                EventType.ANALYSIS_START,
                f"Iniciando análisis de mercado para {symbol}",
                "MarketDataUpdater",
                data={'symbol': symbol}
            )
            
            # Obtener datos históricos
            data_fetch_start = datetime.now(timezone.utc)
            df = self.get_binance_klines(symbol, interval='1h', limit=100)
            data_fetch_duration = (datetime.now(timezone.utc) - data_fetch_start).total_seconds() * 1000
            
            if df is None:
                return
            
            # Calcular indicadores
            indicator_start = datetime.now(timezone.utc)
            df = self.calculate_indicators(df)
            indicator_duration = (datetime.now(timezone.utc) - indicator_start).total_seconds() * 1000
            
            # Guardar datos
            self.market_data[symbol] = df
            
            # Log condiciones de mercado
            current_data = df.iloc[-1]
            market_conditions = MarketConditions(
                timestamp=datetime.now(timezone.utc),
                symbol=symbol,
                price=float(current_data['close']),
                volume=float(current_data['volume']),
                volatility=float(current_data.get('atr', 0)),
                trend_direction="bullish" if current_data.get('ema_9', 0) > current_data.get('ema_21', 0) else "bearish",
                market_session="active",
                spread=0.01  # Spread por defecto
            )
            
            self.advanced_logger.log_market_conditions(market_conditions)
            
            # Verificar señales (solo en primera vela de sesión)
            current_time = datetime.now()
            signal_duration = 0
            if self.is_first_candle_of_session(current_time):
                signal_start = datetime.now(timezone.utc)
                signal = self.generate_signal(symbol, df, None)
                signal_duration = (datetime.now(timezone.utc) - signal_start).total_seconds() * 1000
                
                if signal:
                    # Log contexto de decisión
                    decision_context = DecisionContext(
                        timestamp=datetime.now(timezone.utc),
                        symbol=symbol,
                        signal_type=signal['type'],
                        confidence_score=signal.get('confidence', 0.5),
                        entry_price=signal['price'],
                        stop_loss=signal.get('stop_loss', signal['price'] * 0.98),
                        take_profit=signal.get('take_profit', signal['price'] * 1.02),
                        risk_reward_ratio=2.0,
                        position_size=signal.get('position_size', 100),
                        market_conditions=f"RSI: {current_data.get('rsi', 50):.1f}, Volume: {current_data['volume']:.0f}",
                        technical_indicators={
                            'rsi': float(current_data.get('rsi', 50)),
                            'ema_9': float(current_data.get('ema_9', 0)),
                            'ema_21': float(current_data.get('ema_21', 0)),
                            'volume_ratio': signal.get('volume_ratio', 1.0)
                        },
                        reasoning=f"Primera vela breakout {signal['type']} con cambio de precio {signal.get('price_change', 0):.2f}%"
                    )
                    
                    self.advanced_logger.log_decision_context(decision_context)
                    self.execute_paper_trade(signal)
            
            # Verificar condiciones de salida
            current_price = df.iloc[-1]['close']
            self.check_exit_conditions(symbol, current_price)
            
            # Calcular y log métricas de rendimiento
            analysis_duration = (datetime.now(timezone.utc) - analysis_start).total_seconds() * 1000
            
            performance_metrics = PerformanceMetrics(
                timestamp=datetime.now(timezone.utc),
                analysis_duration_ms=analysis_duration,
                data_fetch_duration_ms=data_fetch_duration,
                indicator_calculation_duration_ms=indicator_duration,
                signal_generation_duration_ms=signal_duration,
                memory_usage_mb=self._get_memory_usage(),
                cpu_usage_percent=self._get_cpu_usage(),
                api_response_time_ms=data_fetch_duration,
                total_requests=1,
                successful_requests=1,
                failed_requests=0
            )
            
            self.advanced_logger.log_performance(performance_metrics, "MarketDataUpdater", symbol)
            
            # Log finalización exitosa
            self.advanced_logger.log(
                LogLevel.DEBUG,
                EventType.ANALYSIS_COMPLETE,
                f"Análisis completado para {symbol} en {analysis_duration:.1f}ms",
                "MarketDataUpdater",
                data={
                    'symbol': symbol,
                    'analysis_duration_ms': analysis_duration,
                    'data_points': len(df),
                    'current_price': float(current_data['close']),
                    'volume': float(current_data['volume'])
                }
            )
            
        except Exception as e:
            # Log error con detalles
            error_duration = (datetime.now(timezone.utc) - analysis_start).total_seconds() * 1000
            
            self.advanced_logger.log(
                LogLevel.ERROR,
                EventType.ERROR,
                f"Error actualizando datos para {symbol}: {str(e)}",
                "MarketDataUpdater",
                data={
                    'symbol': symbol,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'analysis_duration_ms': error_duration
                }
            )
            
            # Log métricas de error
            error_performance = PerformanceMetrics(
                timestamp=datetime.now(timezone.utc),
                analysis_duration_ms=error_duration,
                data_fetch_duration_ms=0,
                indicator_calculation_duration_ms=0,
                signal_generation_duration_ms=0,
                memory_usage_mb=self._get_memory_usage(),
                cpu_usage_percent=self._get_cpu_usage(),
                api_response_time_ms=0,
                total_requests=1,
                successful_requests=0,
                failed_requests=1
            )
            
            self.advanced_logger.log_performance(error_performance, "MarketDataUpdater", symbol)
            
            logging.error(f"Error actualizando datos de {symbol}: {str(e)}")
    
    def _get_memory_usage(self) -> float:
        """Obtiene uso de memoria en MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """Obtiene uso de CPU en porcentaje"""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except:
            return 0.0

    def reset_daily_counters(self):
        """Resetea contadores diarios"""
        current_date = datetime.now().date()
        if self.current_session_date != current_date:
            self.current_session_date = current_date
            self.session_trades_count = 0
            self.first_candle_processed = {}
            logging.info(f"🌅 Nueva sesión iniciada: {current_date}")

    def display_status(self):
        """Muestra estado actual del sistema"""
        try:
            open_positions = len([p for p in self.positions.values() if p['status'] == 'OPEN'])
            total_trades = len(self.trades_history)
            
            if total_trades > 0:
                winning_trades = len([t for t in self.trades_history if t['result'] == 'WIN'])
                win_rate = (winning_trades / total_trades) * 100
                total_pnl = sum([t['pnl'] for t in self.trades_history])
            else:
                win_rate = 0
                total_pnl = 0
            
            initial_capital = self.config['capital_management']['initial_capital']
            total_return = ((self.current_capital - initial_capital) / initial_capital) * 100
            
            print(f"\n{'='*60}")
            print(f"ESTADO DEL SISTEMA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")
            print(f"Capital actual: ${self.current_capital:.2f}")
            print(f"Retorno total: {total_return:.2f}%")
            print(f"Posiciones abiertas: {open_positions}")
            print(f"Total trades: {total_trades}")
            print(f"Tasa de aciertos: {win_rate:.1f}%")
            print(f"P&L total: ${total_pnl:.2f}")
            print(f"Trades hoy: {self.session_trades_count}")
            print(f"{'='*60}")
            
        except Exception as e:
            logging.error(f"Error mostrando estado: {str(e)}")

    async def run_real_time_system(self):
        """Ejecuta el sistema en tiempo real"""
        logging.info("🚀 INICIANDO SISTEMA EN TIEMPO REAL")
        self.is_running = True
        
        # Log inicio del sistema
        self.advanced_logger.log(
            LogLevel.INFO,
            EventType.SYSTEM_START,
            f"Sistema First Candle iniciado con {len(self.config['symbols'])} símbolos",
            "SystemManager",
            data={
                'initial_capital': self.current_capital,
                'symbols': self.config['symbols'],
                'session_start': datetime.now(timezone.utc).isoformat()
            }
        )
        
        try:
            while self.is_running:
                # Resetear contadores diarios
                self.reset_daily_counters()
                
                # Verificar si es primera vela de sesión
                current_time = datetime.now()
                if self.is_first_candle_of_session(current_time):
                    # Log evento de primera vela
                    self.advanced_logger.log(
                        LogLevel.INFO,
                        EventType.ANALYSIS_START,
                        f"Primera vela de sesión detectada",
                        "SessionManager",
                        data={
                            'session_time': current_time.strftime('%H:%M:%S'),
                            'symbols_to_process': len(self.config['symbols'])
                        }
                    )
                
                # Actualizar datos para cada símbolo
                for symbol in self.config['symbols']:
                    self.update_market_data(symbol)
                    await asyncio.sleep(1)  # Evitar rate limiting
                
                # Mostrar estado cada 5 minutos
                if datetime.now().minute % 5 == 0:
                    self.display_status()
                
                # Esperar 60 segundos antes de la siguiente actualización
                await asyncio.sleep(60)
                
        except KeyboardInterrupt:
            logging.info("Sistema detenido por usuario")
            
            # Log parada del sistema
            self.advanced_logger.log(
                LogLevel.INFO,
                EventType.SYSTEM_START,
                "Sistema detenido por el usuario",
                "SystemManager",
                data={
                    'stop_reason': 'user_interrupt',
                    'final_capital': self.current_capital
                }
            )
            
        except Exception as e:
            logging.error(f"Error en sistema en tiempo real: {str(e)}")
            
            # Log error del sistema
            self.advanced_logger.log(
                LogLevel.ERROR,
                EventType.ERROR,
                f"Error crítico en el sistema: {str(e)}",
                "SystemManager",
                data={
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            )
            
        finally:
            self.is_running = False
            logging.info("Sistema detenido")
            self.generate_advanced_session_summary()
    
    def generate_advanced_session_summary(self):
        """Genera resumen avanzado de la sesión con métricas por símbolo"""
        try:
            logging.info("\n" + "="*80)
            logging.info("📊 RESUMEN AVANZADO DE SESIÓN")
            logging.info("="*80)
            
            # Obtener resumen de sesión del logger avanzado
            session_summary = self.advanced_logger.get_session_summary()
            
            # Mostrar métricas generales
            logging.info(f"🕐 Duración de sesión: {session_summary.get('session_duration', 'N/A')}")
            logging.info(f"📈 Total de análisis: {session_summary.get('total_analyses', 0)}")
            logging.info(f"🎯 Total de señales: {session_summary.get('total_signals', 0)}")
            logging.info(f"💼 Total de trades: {session_summary.get('total_trades', 0)}")
            logging.info(f"⚠️  Total de errores: {session_summary.get('total_errors', 0)}")
            
            # Mostrar métricas por símbolo
            symbol_metrics = session_summary.get('symbol_metrics', {})
            
            for symbol in self.config['symbols']:
                if symbol in symbol_metrics:
                    metrics = symbol_metrics[symbol]
                    logging.info(f"\n📊 {symbol}:")
                    logging.info(f"   Análisis: {metrics.get('analyses', 0)}")
                    logging.info(f"   Señales: {metrics.get('signals', 0)}")
                    logging.info(f"   Trades: {metrics.get('trades', 0)}")
                    logging.info(f"   Tasa éxito: {metrics.get('success_rate', 0):.1f}%")
                    logging.info(f"   Tiempo promedio análisis: {metrics.get('avg_analysis_time', 0):.1f}ms")
                    logging.info(f"   Confianza promedio: {metrics.get('avg_confidence', 0):.2f}")
            
            # Log resumen final al sistema avanzado
            self.advanced_logger.log(
                LogLevel.INFO,
                EventType.ANALYSIS_COMPLETE,
                "Resumen de sesión generado",
                "SessionManager",
                data={
                    'session_summary': session_summary,
                    'symbols_processed': len(self.config['symbols']),
                    'final_timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            
            logging.info("\n" + "="*80)
            
        except Exception as e:
            logging.error(f"Error generando resumen avanzado: {str(e)}")
            
            self.advanced_logger.log(
                LogLevel.ERROR,
                EventType.ERROR,
                f"Error generando resumen de sesión: {str(e)}",
                "SessionManager",
                data={
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            )

    def save_session_data(self):
        """Guarda datos de la sesión"""
        try:
            session_data = {
                'timestamp': datetime.now().isoformat(),
                'current_capital': self.current_capital,
                'positions': self.positions,
                'trades_history': self.trades_history,
                'session_trades_count': self.session_trades_count
            }
            
            with open('real_time_session_data.json', 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, default=str)
                
            logging.info("Datos de sesión guardados")
            
        except Exception as e:
            logging.error(f"Error guardando datos de sesión: {str(e)}")

def main():
    """Función principal"""
    try:
        # Crear sistema
        system = RealTimeFirstCandleSystem()
        
        # Ejecutar en tiempo real
        asyncio.run(system.run_real_time_system())
        
    except KeyboardInterrupt:
        logging.info("Sistema detenido por usuario")
    except Exception as e:
        logging.error(f"Error en main: {str(e)}")
    finally:
        # Guardar datos al finalizar
        if 'system' in locals():
            system.save_session_data()

if __name__ == "__main__":
    main()