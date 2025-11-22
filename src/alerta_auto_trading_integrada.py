#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema Integrado de Alertas + Auto Trading Paper
Combina detección de rompimientos con activación automática del paper trading bot.
"""

import logging
import json
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
from dataclasses import dataclass
import threading
import uuid

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('alerta_auto_trading.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TradingSignal:
    """Señal de trading detectada."""
    symbol: str
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float
    price: float
    timestamp: datetime
    reason: str
    risk_level: str
    volume_score: float
    
class AutoTradingIntegrator:
    """
    Sistema integrado que detecta oportunidades y activa automáticamente el paper trading.
    """
    
    def __init__(self):
        """Inicializar el sistema integrado."""
        self.symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT',
            'XRPUSDT', 'DOGEUSDT', 'AVAXUSDT', 'DOTUSDT', 'MATICUSDT'
        ]
        
        # Configuración de trading
        self.trading_config = {
            'min_confidence': 60.0,  # Confianza mínima para operar
            'max_risk_level': 'MEDIUM',  # Nivel máximo de riesgo
            'position_size_pct': 10.0,  # % del capital por operación
            'stop_loss_pct': 2.0,  # % de stop loss
            'take_profit_pct': 4.0,  # % de take profit
            'max_positions': 3  # Máximo de posiciones simultáneas
        }
        
        # Estado del sistema
        self.active_positions = {}
        self.pending_orders = {}
        self.session_file = 'data/paper_trading_session.json'
        
        # Base de datos para tracking
        self.init_database()
        
        logger.info("🤖 Sistema Integrado de Alertas + Auto Trading inicializado")
    
    def init_database(self):
        """Inicializar base de datos para tracking."""
        try:
            conn = sqlite3.connect('auto_trading_alerts.db')
            cursor = conn.cursor()
            
            # Tabla de señales detectadas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trading_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    price REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    reason TEXT,
                    risk_level TEXT,
                    volume_score REAL,
                    executed BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Tabla de operaciones ejecutadas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS executed_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id INTEGER,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL,
                    take_profit REAL,
                    timestamp TEXT NOT NULL,
                    status TEXT DEFAULT 'ACTIVE',
                    FOREIGN KEY (signal_id) REFERENCES trading_signals (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Base de datos inicializada correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando base de datos: {e}")
    
    def get_binance_price(self, symbol: str) -> Optional[float]:
        """Obtener precio actual de Binance."""
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return float(data['price'])
            else:
                logger.warning(f"⚠️ Error obteniendo precio de {symbol}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error conectando con Binance para {symbol}: {e}")
            return None
    
    def get_market_data(self, symbol: str) -> Optional[Dict]:
        """Obtener datos de mercado completos."""
        try:
            # Precio actual
            price = self.get_binance_price(symbol)
            if not price:
                return None
            
            # Datos de 24h
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'symbol': symbol,
                    'price': price,
                    'volume': float(data['volume']),
                    'price_change_pct': float(data['priceChangePercent']),
                    'high_24h': float(data['highPrice']),
                    'low_24h': float(data['lowPrice']),
                    'count': int(data['count'])
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos de mercado para {symbol}: {e}")
            return None
    
    def analyze_breakout_signal(self, market_data: Dict) -> Optional[TradingSignal]:
        """Analizar si hay señal de rompimiento."""
        try:
            symbol = market_data['symbol']
            price = market_data['price']
            volume = market_data['volume']
            price_change = market_data['price_change_pct']
            high_24h = market_data['high_24h']
            low_24h = market_data['low_24h']
            
            # Calcular niveles críticos
            resistance = high_24h * 0.998  # Resistencia ajustada
            support = low_24h * 1.002      # Soporte ajustado
            
            # Detectar rompimiento alcista
            if price > resistance and price_change > 2.0 and volume > 1000000:
                confidence = min(95.0, 60.0 + (price_change * 5) + (volume / 100000))
                risk_level = 'LOW' if confidence > 80 else 'MEDIUM'
                
                return TradingSignal(
                    symbol=symbol,
                    signal_type='BUY',
                    confidence=confidence,
                    price=price,
                    timestamp=datetime.now(),
                    reason=f"Rompimiento alcista: ${price:,.2f} > ${resistance:,.2f} (+{price_change:.1f}%)",
                    risk_level=risk_level,
                    volume_score=min(100.0, volume / 10000)
                )
            
            # Detectar rompimiento bajista
            elif price < support and price_change < -2.0 and volume > 1000000:
                confidence = min(95.0, 60.0 + (abs(price_change) * 5) + (volume / 100000))
                risk_level = 'LOW' if confidence > 80 else 'MEDIUM'
                
                return TradingSignal(
                    symbol=symbol,
                    signal_type='SELL',
                    confidence=confidence,
                    price=price,
                    timestamp=datetime.now(),
                    reason=f"Rompimiento bajista: ${price:,.2f} < ${support:,.2f} ({price_change:.1f}%)",
                    risk_level=risk_level,
                    volume_score=min(100.0, volume / 10000)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error analizando señal para {market_data.get('symbol', 'UNKNOWN')}: {e}")
            return None
    
    def save_signal_to_db(self, signal: TradingSignal) -> int:
        """Guardar señal en base de datos."""
        try:
            conn = sqlite3.connect('auto_trading_alerts.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO trading_signals 
                (symbol, signal_type, confidence, price, timestamp, reason, risk_level, volume_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal.symbol,
                signal.signal_type,
                signal.confidence,
                signal.price,
                signal.timestamp.isoformat(),
                signal.reason,
                signal.risk_level,
                signal.volume_score
            ))
            
            signal_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return signal_id
            
        except Exception as e:
            logger.error(f"❌ Error guardando señal: {e}")
            return None
    
    def should_execute_trade(self, signal: TradingSignal) -> bool:
        """Determinar si se debe ejecutar la operación."""
        # Verificar confianza mínima
        if signal.confidence < self.trading_config['min_confidence']:
            logger.info(f"⚠️ {signal.symbol}: Confianza insuficiente ({signal.confidence:.1f}% < {self.trading_config['min_confidence']}%)")
            return False
        
        # Verificar nivel de riesgo
        risk_levels = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3}
        max_risk = risk_levels.get(self.trading_config['max_risk_level'], 2)
        signal_risk = risk_levels.get(signal.risk_level, 3)
        
        if signal_risk > max_risk:
            logger.info(f"⚠️ {signal.symbol}: Riesgo muy alto ({signal.risk_level} > {self.trading_config['max_risk_level']})")
            return False
        
        # Verificar máximo de posiciones
        if len(self.active_positions) >= self.trading_config['max_positions']:
            logger.info(f"⚠️ {signal.symbol}: Máximo de posiciones alcanzado ({len(self.active_positions)}/{self.trading_config['max_positions']})")
            return False
        
        # Verificar si ya hay posición en este símbolo
        if signal.symbol in self.active_positions:
            logger.info(f"⚠️ {signal.symbol}: Ya hay posición activa")
            return False
        
        return True
    
    def execute_paper_trade(self, signal: TradingSignal, signal_id: int) -> bool:
        """Ejecutar operación en paper trading."""
        try:
            # Leer sesión actual
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
            
            current_capital = session_data.get('current_capital', 0)
            
            # Calcular tamaño de posición
            position_value = current_capital * (self.trading_config['position_size_pct'] / 100)
            quantity = position_value / signal.price
            
            # Calcular stop loss y take profit
            if signal.signal_type == 'BUY':
                stop_loss = signal.price * (1 - self.trading_config['stop_loss_pct'] / 100)
                take_profit = signal.price * (1 + self.trading_config['take_profit_pct'] / 100)
                side = 'buy'
            else:  # SELL
                stop_loss = signal.price * (1 + self.trading_config['stop_loss_pct'] / 100)
                take_profit = signal.price * (1 - self.trading_config['take_profit_pct'] / 100)
                side = 'sell'
            
            # Crear orden virtual
            order_id = str(uuid.uuid4())[:8]
            
            trade_data = {
                'order_id': order_id,
                'symbol': signal.symbol,
                'side': side,
                'quantity': quantity,
                'price': signal.price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'timestamp': datetime.now().isoformat(),
                'signal_confidence': signal.confidence,
                'signal_reason': signal.reason
            }
            
            # Actualizar posiciones activas
            self.active_positions[signal.symbol] = trade_data
            
            # Guardar en base de datos
            conn = sqlite3.connect('auto_trading_alerts.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO executed_trades 
                (signal_id, symbol, side, quantity, entry_price, stop_loss, take_profit, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal_id,
                signal.symbol,
                side,
                quantity,
                signal.price,
                stop_loss,
                take_profit,
                datetime.now().isoformat()
            ))
            
            # Marcar señal como ejecutada
            cursor.execute('UPDATE trading_signals SET executed = TRUE WHERE id = ?', (signal_id,))
            
            conn.commit()
            conn.close()
            
            # Actualizar capital (simulado)
            commission = position_value * 0.001  # 0.1% comisión
            session_data['current_capital'] -= commission
            session_data['total_trades'] = session_data.get('total_trades', 0) + 1
            session_data['last_sync'] = datetime.now().isoformat()
            
            # Guardar sesión actualizada
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            logger.info(f"🚀 OPERACIÓN EJECUTADA:")
            logger.info(f"   📊 {signal.symbol} - {side.upper()}")
            logger.info(f"   💰 Cantidad: {quantity:.6f}")
            logger.info(f"   💵 Precio: ${signal.price:,.2f}")
            logger.info(f"   🛑 Stop Loss: ${stop_loss:,.2f}")
            logger.info(f"   🎯 Take Profit: ${take_profit:,.2f}")
            logger.info(f"   📈 Confianza: {signal.confidence:.1f}%")
            logger.info(f"   💡 Razón: {signal.reason}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando operación: {e}")
            return False
    
    def monitor_positions(self):
        """Monitorear posiciones activas para stop loss / take profit."""
        for symbol, position in list(self.active_positions.items()):
            try:
                current_price = self.get_binance_price(symbol)
                if not current_price:
                    continue
                
                entry_price = position['price']
                stop_loss = position['stop_loss']
                take_profit = position['take_profit']
                side = position['side']
                
                should_close = False
                close_reason = ""
                
                if side == 'buy':
                    if current_price <= stop_loss:
                        should_close = True
                        close_reason = f"Stop Loss alcanzado: ${current_price:,.2f} <= ${stop_loss:,.2f}"
                    elif current_price >= take_profit:
                        should_close = True
                        close_reason = f"Take Profit alcanzado: ${current_price:,.2f} >= ${take_profit:,.2f}"
                else:  # sell
                    if current_price >= stop_loss:
                        should_close = True
                        close_reason = f"Stop Loss alcanzado: ${current_price:,.2f} >= ${stop_loss:,.2f}"
                    elif current_price <= take_profit:
                        should_close = True
                        close_reason = f"Take Profit alcanzado: ${current_price:,.2f} <= ${take_profit:,.2f}"
                
                if should_close:
                    self.close_position(symbol, current_price, close_reason)
                    
            except Exception as e:
                logger.error(f"❌ Error monitoreando posición {symbol}: {e}")
    
    def close_position(self, symbol: str, close_price: float, reason: str):
        """Cerrar posición activa."""
        try:
            if symbol not in self.active_positions:
                return
            
            position = self.active_positions[symbol]
            entry_price = position['price']
            quantity = position['quantity']
            side = position['side']
            
            # Calcular PnL
            if side == 'buy':
                pnl = (close_price - entry_price) * quantity
            else:
                pnl = (entry_price - close_price) * quantity
            
            # Actualizar capital
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
            
            session_data['current_capital'] += (quantity * close_price) + pnl
            session_data['last_sync'] = datetime.now().isoformat()
            
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            # Actualizar base de datos
            conn = sqlite3.connect('auto_trading_alerts.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE executed_trades 
                SET status = 'CLOSED' 
                WHERE symbol = ? AND status = 'ACTIVE'
            ''', (symbol,))
            
            conn.commit()
            conn.close()
            
            # Remover de posiciones activas
            del self.active_positions[symbol]
            
            pnl_pct = (pnl / (entry_price * quantity)) * 100
            
            logger.info(f"🔒 POSICIÓN CERRADA:")
            logger.info(f"   📊 {symbol}")
            logger.info(f"   💵 Precio cierre: ${close_price:,.2f}")
            logger.info(f"   💰 PnL: ${pnl:,.2f} ({pnl_pct:+.2f}%)")
            logger.info(f"   💡 Razón: {reason}")
            
        except Exception as e:
            logger.error(f"❌ Error cerrando posición {symbol}: {e}")
    
    def run_continuous_monitoring(self):
        """Ejecutar monitoreo continuo."""
        logger.info("🔄 Iniciando monitoreo continuo de alertas + auto trading...")
        
        cycle_count = 0
        
        while True:
            try:
                cycle_count += 1
                logger.info(f"\n🔍 CICLO {cycle_count} - {datetime.now().strftime('%H:%M:%S')}")
                
                # Monitorear posiciones activas
                if self.active_positions:
                    logger.info(f"📊 Monitoreando {len(self.active_positions)} posiciones activas...")
                    self.monitor_positions()
                
                # Buscar nuevas oportunidades
                signals_detected = 0
                
                for symbol in self.symbols:
                    try:
                        # Obtener datos de mercado
                        market_data = self.get_market_data(symbol)
                        if not market_data:
                            continue
                        
                        # Analizar señal
                        signal = self.analyze_breakout_signal(market_data)
                        if not signal:
                            continue
                        
                        signals_detected += 1
                        
                        logger.info(f"🎯 SEÑAL DETECTADA: {signal.symbol}")
                        logger.info(f"   📈 Tipo: {signal.signal_type}")
                        logger.info(f"   💪 Confianza: {signal.confidence:.1f}%")
                        logger.info(f"   ⚠️ Riesgo: {signal.risk_level}")
                        logger.info(f"   💡 Razón: {signal.reason}")
                        
                        # Guardar señal
                        signal_id = self.save_signal_to_db(signal)
                        
                        # Evaluar si ejecutar
                        if self.should_execute_trade(signal):
                            success = self.execute_paper_trade(signal, signal_id)
                            if success:
                                logger.info(f"✅ Operación ejecutada automáticamente para {signal.symbol}")
                            else:
                                logger.error(f"❌ Error ejecutando operación para {signal.symbol}")
                        else:
                            logger.info(f"⏭️ Señal {signal.symbol} no cumple criterios de ejecución")
                        
                        time.sleep(1)  # Pausa entre símbolos
                        
                    except Exception as e:
                        logger.error(f"❌ Error procesando {symbol}: {e}")
                
                # Resumen del ciclo
                logger.info(f"📊 Resumen ciclo {cycle_count}:")
                logger.info(f"   🎯 Señales detectadas: {signals_detected}")
                logger.info(f"   📈 Posiciones activas: {len(self.active_positions)}")
                
                if self.active_positions:
                    logger.info("   💼 Posiciones:")
                    for symbol, pos in self.active_positions.items():
                        logger.info(f"      {symbol}: {pos['side'].upper()} @ ${pos['price']:,.2f}")
                
                # Pausa antes del siguiente ciclo
                logger.info("⏳ Esperando 30 segundos para el próximo ciclo...\n")
                time.sleep(30)
                
            except KeyboardInterrupt:
                logger.info("🛑 Deteniendo monitoreo por solicitud del usuario...")
                break
            except Exception as e:
                logger.error(f"❌ Error en ciclo de monitoreo: {e}")
                time.sleep(10)

def main():
    """Función principal."""
    try:
        # Crear sistema integrado
        integrator = AutoTradingIntegrator()
        
        # Verificar que el paper trading esté activo
        try:
            with open('data/paper_trading_session.json', 'r') as f:
                session_data = json.load(f)
            
            if not session_data.get('auto_trading', False):
                logger.warning("⚠️ Auto trading no está activado en la sesión")
                logger.info("💡 Activando auto trading...")
                session_data['auto_trading'] = True
                session_data['last_sync'] = datetime.now().isoformat()
                
                with open('data/paper_trading_session.json', 'w') as f:
                    json.dump(session_data, f, indent=2)
                
                logger.info("✅ Auto trading activado")
            
            logger.info(f"💰 Capital actual: ${session_data.get('current_capital', 0):,.2f}")
            logger.info(f"📊 Trades totales: {session_data.get('total_trades', 0)}")
            
        except Exception as e:
            logger.error(f"❌ Error verificando sesión de paper trading: {e}")
            return
        
        # Iniciar monitoreo continuo
        integrator.run_continuous_monitoring()
        
    except Exception as e:
        logger.error(f"❌ Error en función principal: {e}")

if __name__ == "__main__":
    main()