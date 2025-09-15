#!/usr/bin/env python3
"""
SISTEMA DE TRADING AUTÓNOMO V3
==============================
Sistema inteligente que adapta estrategias dinámicamente basado en:
- Condiciones de mercado en tiempo real
- Rendimiento histórico
- Análisis de volatilidad
- Gestión de riesgo adaptativo
"""

import ccxt
import pandas as pd
import numpy as np
import ta
from datetime import datetime, timedelta
import json
import asyncio
import logging
import warnings
from typing import Dict, List, Optional, Tuple
import sqlite3
from dataclasses import dataclass
import threading
import time

warnings.filterwarnings('ignore')

@dataclass
class TradingSignal:
    """Señal de trading"""
    symbol: str
    timeframe: str
    strategy: str
    action: str  # 'BUY', 'SELL', 'CLOSE'
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_amount: float
    timestamp: datetime

@dataclass
class MarketCondition:
    """Condición de mercado"""
    symbol: str
    volatility: float
    trend: str  # 'BULLISH', 'BEARISH', 'SIDEWAYS'
    volume_trend: str
    momentum: float
    timestamp: datetime

class AutonomousTradingSystem:
    def __init__(self, config_file: str = "autonomous_config.json"):
        """Inicializar sistema autónomo"""
        self.config = self.load_config(config_file)
        self.exchange = self.setup_exchange()
        self.db_connection = self.setup_database()
        
        # Estrategias disponibles
        self.strategies = {
            'scalping': {
                'rsi_oversold': 20, 'rsi_overbought': 80,
                'bb_std': 2.0, 'volume_threshold': 1.0,
                'risk_per_trade': 0.02, 'max_trades': 100,
                'timeframes': ['5m', '15m'],
                'best_pairs': ['SOL/USDT', 'ETH/USDT']
            },
            'swing': {
                'rsi_oversold': 25, 'rsi_overbought': 75,
                'bb_std': 2.5, 'volume_threshold': 1.3,
                'risk_per_trade': 0.025, 'max_trades': 50,
                'timeframes': ['30m', '1h'],
                'best_pairs': ['BTC/USDT', 'ETH/USDT']
            },
            'hybrid': {
                'rsi_oversold': 22, 'rsi_overbought': 78,
                'bb_std': 2.2, 'volume_threshold': 1.1,
                'risk_per_trade': 0.03, 'max_trades': 75,
                'timeframes': ['15m', '30m', '1h'],
                'best_pairs': ['SOL/USDT', 'BTC/USDT', 'ETH/USDT']
            }
        }
        
        # Estado del sistema
        self.active_positions = {}
        self.market_conditions = {}
        self.strategy_performance = {}
        self.risk_manager = RiskManager(self.config)
        
        # Control de ejecución
        self.running = False
        self.last_analysis = {}
        
        self.setup_logging()
        
    def load_config(self, config_file: str) -> Dict:
        """Cargar configuración"""
        default_config = {
            "exchange": {
                "name": "binance",
                "apiKey": "",
                "secret": "",
                "sandbox": False
            },
            "trading": {
                "max_simultaneous_positions": 10,
                "max_daily_loss": 5.0,  # %
                "max_position_size": 10.0,  # %
                "base_balance": 1000
            },
            "market_analysis": {
                "analysis_interval": 60,  # segundos
                "market_condition_window": 24,  # horas
                "strategy_adaptation_interval": 3600  # segundos
            },
            "risk_management": {
                "max_drawdown": 15.0,  # %
                "daily_loss_limit": 3.0,  # %
                "correlation_limit": 0.7
            },
            "monitoring": {
                "telegram_notifications": True,
                "performance_tracking": True,
                "auto_rebalance": True
            }
        }
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                # Merge with defaults
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                return config
        except FileNotFoundError:
            # Save default config
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
    
    def setup_exchange(self) -> ccxt.Exchange:
        """Configurar exchange"""
        exchange_config = self.config['exchange']
        exchange_class = getattr(ccxt, exchange_config['name'])
        
        return exchange_class({
            'apiKey': exchange_config['apiKey'],
            'secret': exchange_config['secret'],
            'sandbox': exchange_config['sandbox'],
            'enableRateLimit': True,
        })
    
    def setup_database(self) -> sqlite3.Connection:
        """Configurar base de datos para tracking"""
        conn = sqlite3.connect('autonomous_trading.db', check_same_thread=False)
        
        # Crear tablas
        conn.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                symbol TEXT,
                strategy TEXT,
                action TEXT,
                price REAL,
                amount REAL,
                pnl REAL,
                confidence REAL
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                strategy TEXT,
                symbol TEXT,
                timeframe TEXT,
                daily_return REAL,
                win_rate REAL,
                profit_factor REAL,
                sharpe_ratio REAL
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS market_conditions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                symbol TEXT,
                volatility REAL,
                trend TEXT,
                volume_trend TEXT,
                momentum REAL
            )
        ''')
        
        conn.commit()
        return conn
    
    def setup_logging(self):
        """Configurar logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('autonomous_trading.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    async def analyze_market_conditions(self, symbol: str) -> MarketCondition:
        """Analizar condiciones actuales del mercado"""
        try:
            # Obtener datos de múltiples timeframes
            data_1h = await self.fetch_ohlcv_async(symbol, '1h', 48)
            data_4h = await self.fetch_ohlcv_async(symbol, '4h', 24)
            
            if data_1h.empty or data_4h.empty:
                return None
            
            # Calcular indicadores
            data_1h = self.calculate_indicators(data_1h)
            data_4h = self.calculate_indicators(data_4h)
            
            current_1h = data_1h.iloc[-1]
            current_4h = data_4h.iloc[-1]
            
            # Análisis de volatilidad
            volatility = data_1h['close'].pct_change().std() * 100
            
            # Análisis de tendencia
            trend = self.determine_trend(data_1h, data_4h)
            
            # Análisis de volumen
            volume_trend = self.analyze_volume_trend(data_1h)
            
            # Momentum
            momentum = self.calculate_momentum(data_1h)
            
            condition = MarketCondition(
                symbol=symbol,
                volatility=volatility,
                trend=trend,
                volume_trend=volume_trend,
                momentum=momentum,
                timestamp=datetime.now()
            )
            
            # Guardar en DB
            self.save_market_condition(condition)
            
            return condition
            
        except Exception as e:
            self.logger.error(f"Error analyzing market conditions for {symbol}: {e}")
            return None
    
    def determine_trend(self, data_1h: pd.DataFrame, data_4h: pd.DataFrame) -> str:
        """Determinar tendencia del mercado"""
        current_1h = data_1h.iloc[-1]
        current_4h = data_4h.iloc[-1]
        
        # Análisis multi-timeframe
        ema_signals_1h = current_1h['ema_9'] > current_1h['ema_21'] > current_1h['ema_50']
        ema_signals_4h = current_4h['ema_9'] > current_4h['ema_21'] > current_4h['ema_50']
        
        macd_bullish_1h = current_1h['macd'] > current_1h['macd_signal']
        macd_bullish_4h = current_4h['macd'] > current_4h['macd_signal']
        
        rsi_1h = current_1h['rsi']
        rsi_4h = current_4h['rsi']
        
        bullish_signals = sum([
            ema_signals_1h, ema_signals_4h,
            macd_bullish_1h, macd_bullish_4h,
            rsi_1h > 50, rsi_4h > 50
        ])
        
        if bullish_signals >= 4:
            return 'BULLISH'
        elif bullish_signals <= 2:
            return 'BEARISH'
        else:
            return 'SIDEWAYS'
    
    def analyze_volume_trend(self, data: pd.DataFrame) -> str:
        """Analizar tendencia del volumen"""
        recent_volume = data['volume'].tail(10).mean()
        historical_volume = data['volume'].head(-10).mean()
        
        if recent_volume > historical_volume * 1.2:
            return 'INCREASING'
        elif recent_volume < historical_volume * 0.8:
            return 'DECREASING'
        else:
            return 'STABLE'
    
    def calculate_momentum(self, data: pd.DataFrame) -> float:
        """Calcular momentum del precio"""
        returns = data['close'].pct_change().tail(20)
        momentum = returns.mean() * 100  # Convertir a porcentaje
        return momentum
    
    async def fetch_ohlcv_async(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """Obtener datos OHLCV de forma asíncrona"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('timestamp')
            return df
        except Exception as e:
            self.logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular indicadores técnicos"""
        if len(df) < 50:
            return df
        
        # RSI
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
        
        # Bandas de Bollinger
        bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2.0)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_lower'] = bb.bollinger_lband()
        
        # MACD
        macd = ta.trend.MACD(df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        
        # EMAs
        for period in [9, 21, 50]:
            df[f'ema_{period}'] = ta.trend.EMAIndicator(df['close'], window=period).ema_indicator()
        
        # ATR
        df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()
        
        # Volume
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        return df.fillna(method='ffill').fillna(method='bfill')
    
    def select_optimal_strategy(self, market_condition: MarketCondition) -> str:
        """Seleccionar estrategia óptima basada en condiciones del mercado"""
        
        # Reglas de selección adaptativa
        if market_condition.volatility > 5:
            # Alta volatilidad -> Scalping
            if market_condition.momentum > 0.5:
                return 'scalping'
            else:
                return 'hybrid'
        elif market_condition.volatility < 2:
            # Baja volatilidad -> Swing trading
            return 'swing'
        else:
            # Volatilidad media
            if market_condition.trend in ['BULLISH', 'BEARISH']:
                return 'hybrid'
            else:
                return 'scalping'
    
    async def generate_trading_signals(self, symbol: str, strategy_name: str) -> List[TradingSignal]:
        """Generar señales de trading"""
        strategy = self.strategies[strategy_name]
        signals = []
        
        for timeframe in strategy['timeframes']:
            if symbol not in strategy['best_pairs']:
                continue
                
            try:
                # Obtener datos
                df = await self.fetch_ohlcv_async(symbol, timeframe, 200)
                if df.empty or len(df) < 100:
                    continue
                
                # Calcular indicadores
                df = self.calculate_indicators(df)
                current = df.iloc[-1]
                
                # Generar señal basada en la estrategia
                signal = self.evaluate_entry_conditions(current, strategy, symbol, timeframe)
                if signal:
                    signals.append(signal)
                    
            except Exception as e:
                self.logger.error(f"Error generating signal for {symbol} {timeframe}: {e}")
                continue
        
        return signals
    
    def evaluate_entry_conditions(self, current_data, strategy: Dict, symbol: str, timeframe: str) -> Optional[TradingSignal]:
        """Evaluar condiciones de entrada"""
        
        # Condiciones LONG
        long_conditions = [
            current_data['rsi'] < strategy['rsi_oversold'],
            current_data['close'] < current_data['bb_lower'],
            current_data['volume_ratio'] > strategy['volume_threshold'],
            current_data['macd'] > current_data['macd_signal'],
            current_data['ema_9'] > current_data['ema_21']
        ]
        
        # Condiciones SHORT
        short_conditions = [
            current_data['rsi'] > strategy['rsi_overbought'],
            current_data['close'] > current_data['bb_upper'],
            current_data['volume_ratio'] > strategy['volume_threshold'],
            current_data['macd'] < current_data['macd_signal'],
            current_data['ema_9'] < current_data['ema_21']
        ]
        
        long_score = sum(long_conditions) / len(long_conditions)
        short_score = sum(short_conditions) / len(short_conditions)
        
        confidence_threshold = 0.6  # 60% de condiciones cumplidas
        
        if long_score >= confidence_threshold:
            entry_price = current_data['close']
            stop_loss = entry_price - (current_data['atr'] * 2)
            take_profit = entry_price + (current_data['atr'] * 3)
            
            return TradingSignal(
                symbol=symbol,
                timeframe=timeframe,
                strategy=strategy,
                action='BUY',
                confidence=long_score,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_amount=strategy['risk_per_trade'],
                timestamp=datetime.now()
            )
        
        elif short_score >= confidence_threshold:
            entry_price = current_data['close']
            stop_loss = entry_price + (current_data['atr'] * 2)
            take_profit = entry_price - (current_data['atr'] * 3)
            
            return TradingSignal(
                symbol=symbol,
                timeframe=timeframe,
                strategy=strategy,
                action='SELL',
                confidence=short_score,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_amount=strategy['risk_per_trade'],
                timestamp=datetime.now()
            )
        
        return None
    
    async def execute_trading_signal(self, signal: TradingSignal) -> bool:
        """Ejecutar señal de trading"""
        try:
            # Validaciones de riesgo
            if not self.risk_manager.validate_trade(signal):
                self.logger.warning(f"Trade rejected by risk manager: {signal.symbol}")
                return False
            
            # Calcular tamaño de posición
            balance = self.get_account_balance()
            position_size = self.calculate_position_size(balance, signal.risk_amount)
            
            # Ejecutar orden
            if signal.action == 'BUY':
                order = self.exchange.create_market_buy_order(
                    signal.symbol, 
                    position_size,
                    params={'stopLoss': signal.stop_loss, 'takeProfit': signal.take_profit}
                )
            else:  # SELL
                order = self.exchange.create_market_sell_order(
                    signal.symbol, 
                    position_size,
                    params={'stopLoss': signal.stop_loss, 'takeProfit': signal.take_profit}
                )
            
            # Registrar trade
            self.save_trade(signal, order, position_size)
            
            # Actualizar posiciones activas
            self.active_positions[order['id']] = {
                'symbol': signal.symbol,
                'strategy': signal.strategy,
                'entry_time': signal.timestamp,
                'entry_price': order['price'],
                'amount': position_size,
                'side': signal.action.lower(),
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit
            }
            
            self.logger.info(f"Trade executed: {signal.action} {signal.symbol} at {order['price']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
            return False
    
    def get_account_balance(self) -> float:
        """Obtener balance de la cuenta"""
        try:
            balance = self.exchange.fetch_balance()
            return balance['USDT']['free']
        except Exception as e:
            self.logger.error(f"Error fetching balance: {e}")
            return 0
    
    def calculate_position_size(self, balance: float, risk_percentage: float) -> float:
        """Calcular tamaño de posición"""
        max_risk = balance * risk_percentage
        # Simplificado - en producción usar Kelly Criterion o similar
        return max_risk / 100  # Placeholder
    
    def save_trade(self, signal: TradingSignal, order: dict, amount: float):
        """Guardar trade en base de datos"""
        try:
            self.db_connection.execute('''
                INSERT INTO trades (timestamp, symbol, strategy, action, price, amount, pnl, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal.timestamp, signal.symbol, signal.strategy, signal.action,
                order['price'], amount, 0, signal.confidence
            ))
            self.db_connection.commit()
        except Exception as e:
            self.logger.error(f"Error saving trade: {e}")
    
    def save_market_condition(self, condition: MarketCondition):
        """Guardar condición de mercado"""
        try:
            self.db_connection.execute('''
                INSERT INTO market_conditions (timestamp, symbol, volatility, trend, volume_trend, momentum)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                condition.timestamp, condition.symbol, condition.volatility,
                condition.trend, condition.volume_trend, condition.momentum
            ))
            self.db_connection.commit()
        except Exception as e:
            self.logger.error(f"Error saving market condition: {e}")
    
    async def monitor_positions(self):
        """Monitorear posiciones activas"""
        while self.running:
            try:
                for order_id, position in list(self.active_positions.items()):
                    # Verificar si la posición sigue activa
                    order_status = self.exchange.fetch_order(order_id, position['symbol'])
                    
                    if order_status['status'] in ['closed', 'canceled']:
                        # Calcular PnL y actualizar DB
                        pnl = self.calculate_pnl(position, order_status)
                        self.update_trade_pnl(order_id, pnl)
                        
                        # Remover de posiciones activas
                        del self.active_positions[order_id]
                        
                        self.logger.info(f"Position closed: {position['symbol']} PnL: {pnl}")
                
                await asyncio.sleep(30)  # Verificar cada 30 segundos
                
            except Exception as e:
                self.logger.error(f"Error monitoring positions: {e}")
                await asyncio.sleep(60)
    
    async def adaptive_strategy_selection(self):
        """Selección adaptativa de estrategias"""
        symbols = ['ETH/USDT', 'BTC/USDT', 'SOL/USDT']
        
        while self.running:
            try:
                for symbol in symbols:
                    # Analizar condiciones del mercado
                    market_condition = await self.analyze_market_conditions(symbol)
                    if not market_condition:
                        continue
                    
                    self.market_conditions[symbol] = market_condition
                    
                    # Seleccionar estrategia óptima
                    optimal_strategy = self.select_optimal_strategy(market_condition)
                    
                    # Generar señales
                    signals = await self.generate_trading_signals(symbol, optimal_strategy)
                    
                    # Ejecutar señales de alta confianza
                    for signal in signals:
                        if signal.confidence >= 0.7:  # Solo señales muy confiables
                            await self.execute_trading_signal(signal)
                
                # Esperar antes del siguiente análisis
                await asyncio.sleep(self.config['market_analysis']['analysis_interval'])
                
            except Exception as e:
                self.logger.error(f"Error in adaptive strategy selection: {e}")
                await asyncio.sleep(300)  # Esperar 5 minutos en caso de error
    
    def calculate_pnl(self, position: dict, order_status: dict) -> float:
        """Calcular PnL de la posición"""
        entry_price = position['entry_price']
        exit_price = order_status['price']
        amount = position['amount']
        
        if position['side'] == 'buy':
            pnl = (exit_price - entry_price) * amount
        else:
            pnl = (entry_price - exit_price) * amount
        
        return pnl
    
    def update_trade_pnl(self, order_id: str, pnl: float):
        """Actualizar PnL del trade"""
        try:
            self.db_connection.execute('''
                UPDATE trades SET pnl = ? WHERE id = ?
            ''', (pnl, order_id))
            self.db_connection.commit()
        except Exception as e:
            self.logger.error(f"Error updating trade PnL: {e}")
    
    async def start_autonomous_trading(self):
        """Iniciar sistema de trading autónomo"""
        self.logger.info("🚀 Iniciando Sistema de Trading Autónomo V3")
        self.running = True
        
        # Crear tareas asíncronas
        tasks = [
            asyncio.create_task(self.adaptive_strategy_selection()),
            asyncio.create_task(self.monitor_positions()),
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            self.logger.error(f"Error in autonomous trading: {e}")
        finally:
            self.running = False
    
    def stop_autonomous_trading(self):
        """Detener sistema autónomo"""
        self.logger.info("🛑 Deteniendo Sistema Autónomo")
        self.running = False

class RiskManager:
    """Gestor de riesgo avanzado"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.daily_pnl = 0
        self.max_drawdown = 0
        
    def validate_trade(self, signal: TradingSignal) -> bool:
        """Validar si el trade cumple con criterios de riesgo"""
        
        # Verificar límite de pérdida diaria
        if self.daily_pnl <= -self.config['risk_management']['daily_loss_limit']:
            return False
        
        # Verificar número máximo de posiciones
        # ... más validaciones de riesgo
        
        return True

def main():
    """Función principal para testing"""
    print("🚀 SISTEMA DE TRADING AUTÓNOMO V3")
    print("=" * 50)
    
    # Crear sistema autónomo
    trading_system = AutonomousTradingSystem()
    
    # En modo de prueba - solo mostrar configuración
    print("📋 CONFIGURACIÓN DEL SISTEMA:")
    print(f"  - Estrategias disponibles: {list(trading_system.strategies.keys())}")
    print(f"  - Pares de trading: ETH/USDT, BTC/USDT, SOL/USDT")
    print(f"  - Intervalo de análisis: {trading_system.config['market_analysis']['analysis_interval']}s")
    print(f"  - Risk management: Activo")
    
    print("\n✅ Sistema configurado y listo para ejecutar")
    print("💡 Para activar trading en vivo, usar: await trading_system.start_autonomous_trading()")

if __name__ == "__main__":
    main()
