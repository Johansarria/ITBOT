#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SICAR - Sistema Integrado de Trading para Forex y Metales
Implementación avanzada para mercados tradicionales con gestión de horarios y volatilidad adaptada
"""

import asyncio
import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import requests
import yfinance as yf
from pathlib import Path
import pytz

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('forex_metals_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ForexMetalsSignal:
    """Señal de trading para Forex/Metales"""
    symbol: str
    signal_type: str  # 'bullish_breakout', 'bearish_breakout'
    confidence: float
    risk_level: str
    price: float
    volume: float
    timestamp: datetime
    market_session: str
    volatility: float
    spread: float

class MarketSessionManager:
    """Gestor de sesiones de mercado para Forex y Metales"""
    
    def __init__(self):
        self.forex_sessions = {
            'sydney': {'start': 22, 'end': 7},    # 22:00-07:00 UTC
            'tokyo': {'start': 0, 'end': 9},      # 00:00-09:00 UTC  
            'london': {'start': 8, 'end': 17},    # 08:00-17:00 UTC
            'new_york': {'start': 13, 'end': 22}  # 13:00-22:00 UTC
        }
        
        self.session_priorities = {
            'london_ny_overlap': {'start': 13, 'end': 17, 'priority': 'HIGH'},
            'london': {'start': 8, 'end': 17, 'priority': 'MEDIUM'},
            'new_york': {'start': 13, 'end': 22, 'priority': 'MEDIUM'},
            'tokyo': {'start': 0, 'end': 9, 'priority': 'LOW'},
            'sydney': {'start': 22, 'end': 7, 'priority': 'LOW'}
        }
    
    def get_current_session(self) -> Dict:
        """Obtiene la sesión actual del mercado"""
        now_utc = datetime.now(timezone.utc)
        current_hour = now_utc.hour
        current_weekday = now_utc.weekday()
        
        # Verificar si es fin de semana (Forex cerrado)
        if current_weekday >= 5:  # Sábado=5, Domingo=6
            return {
                'session': 'CLOSED',
                'priority': 'NONE',
                'is_open': False,
                'next_open': self._get_next_market_open()
            }
        
        # Verificar overlap Londres-Nueva York (mayor liquidez)
        if 13 <= current_hour <= 17:
            return {
                'session': 'LONDON_NY_OVERLAP',
                'priority': 'HIGH',
                'is_open': True,
                'liquidity': 'HIGHEST'
            }
        
        # Verificar otras sesiones
        for session, times in self.forex_sessions.items():
            if self._is_in_session(current_hour, times['start'], times['end']):
                priority = next((s['priority'] for s in self.session_priorities.values() 
                               if self._is_in_session(current_hour, s['start'], s['end'])), 'LOW')
                return {
                    'session': session.upper(),
                    'priority': priority,
                    'is_open': True,
                    'liquidity': 'HIGH' if priority == 'HIGH' else 'MEDIUM'
                }
        
        return {
            'session': 'CLOSED',
            'priority': 'NONE', 
            'is_open': False,
            'next_open': self._get_next_market_open()
        }
    
    def _is_in_session(self, current_hour: int, start: int, end: int) -> bool:
        """Verifica si la hora actual está en la sesión"""
        if start <= end:
            return start <= current_hour < end
        else:  # Sesión que cruza medianoche
            return current_hour >= start or current_hour < end
    
    def _get_next_market_open(self) -> datetime:
        """Calcula cuándo abre el próximo mercado"""
        now_utc = datetime.now(timezone.utc)
        
        # Si es viernes después de las 22:00 UTC, el próximo mercado abre el lunes a las 22:00
        if now_utc.weekday() == 4 and now_utc.hour >= 22:
            days_until_monday = 3
        elif now_utc.weekday() >= 5:  # Fin de semana
            days_until_monday = 7 - now_utc.weekday()
        else:
            days_until_monday = 0
        
        next_open = now_utc.replace(hour=22, minute=0, second=0, microsecond=0)
        if days_until_monday > 0:
            next_open += timedelta(days=days_until_monday)
        
        return next_open

class ForexMetalsDataProvider:
    """Proveedor de datos para Forex y Metales"""
    
    def __init__(self):
        # Múltiples fuentes de datos con fallbacks
        self.symbols_mapping = {
            # Forex Major Pairs - usando múltiples fuentes
            'EURUSD': {
                'yahoo': 'EURUSD=X',
                'binance': 'EURUSDT',  # Proxy usando USDT
                'fallback_price': 1.0850  # Precio de fallback
            },
            'GBPUSD': {
                'yahoo': 'GBPUSD=X',
                'binance': 'GBPUSDT',
                'fallback_price': 1.2650
            },
            'USDJPY': {
                'yahoo': 'USDJPY=X', 
                'fallback_price': 149.50
            },
            'AUDUSD': {
                'yahoo': 'AUDUSD=X',
                'binance': 'AUDUSDT',
                'fallback_price': 0.6750
            },
            
            # Metales Preciosos
            'XAUUSD': {
                'yahoo': 'GC=F',
                'fallback_price': 2650.00
            },
            'XAGUSD': {
                'yahoo': 'SI=F',
                'fallback_price': 31.50
            }
        }
        
        self.cache = {}
        self.cache_duration = 60  # 1 minuto
        
        # API keys para fuentes alternativas (si están disponibles)
        self.api_keys = {
            'alpha_vantage': None,  # Se puede configurar
            'finhub': None
        }
    
    async def get_market_data(self, symbol: str) -> Optional[Dict]:
        """Obtiene datos de mercado para un símbolo con múltiples fuentes"""
        try:
            # Verificar cache
            cache_key = f"{symbol}_{int(time.time() // self.cache_duration)}"
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            symbol_config = self.symbols_mapping.get(symbol)
            if not symbol_config:
                logger.warning(f"Símbolo {symbol} no encontrado en mapping")
                return None
            
            # Intentar obtener datos de Yahoo Finance primero
            data = await self._get_yahoo_data(symbol, symbol_config)
            
            # Si Yahoo falla, intentar Binance (para pares disponibles)
            if not data and 'binance' in symbol_config:
                data = await self._get_binance_data(symbol, symbol_config)
            
            # Si todo falla, usar datos simulados realistas
            if not data:
                data = self._get_simulated_data(symbol, symbol_config)
            
            if data:
                # Guardar en cache
                self.cache[cache_key] = data
                return data
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo datos para {symbol}: {e}")
            return None
    
    async def _get_yahoo_data(self, symbol: str, config: Dict) -> Optional[Dict]:
        """Intenta obtener datos de Yahoo Finance"""
        try:
            yahoo_symbol = config.get('yahoo')
            if not yahoo_symbol:
                return None
            
            ticker = yf.Ticker(yahoo_symbol)
            hist = ticker.history(period="1d", interval="5m")
            
            if hist.empty:
                return None
            
            current_price = float(hist['Close'].iloc[-1])
            volume = float(hist['Volume'].iloc[-1]) if 'Volume' in hist.columns else 1000000
            
            # Calcular volatilidad
            if len(hist) >= 10:
                volatility = float(hist['Close'].tail(10).pct_change().std() * 100)
            else:
                volatility = 0.5
            
            return self._build_market_data(symbol, current_price, volume, volatility, hist)
            
        except Exception as e:
            logger.debug(f"Yahoo Finance falló para {symbol}: {e}")
            return None
    
    async def _get_binance_data(self, symbol: str, config: Dict) -> Optional[Dict]:
        """Intenta obtener datos de Binance (para pares disponibles)"""
        try:
            binance_symbol = config.get('binance')
            if not binance_symbol:
                return None
            
            # Usar API pública de Binance
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={binance_symbol}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                current_price = float(data['lastPrice'])
                volume = float(data['volume'])
                change_24h = float(data['priceChangePercent'])
                
                # Estimar volatilidad basada en el rango de 24h
                high_24h = float(data['highPrice'])
                low_24h = float(data['lowPrice'])
                volatility = ((high_24h - low_24h) / current_price) * 100
                
                return {
                    'symbol': symbol,
                    'price': current_price,
                    'volume': volume,
                    'volatility': volatility,
                    'spread': self._estimate_spread(symbol, current_price),
                    'timestamp': datetime.now(timezone.utc),
                    'high_24h': high_24h,
                    'low_24h': low_24h,
                    'change_24h': change_24h
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Binance falló para {symbol}: {e}")
            return None
    
    def _get_simulated_data(self, symbol: str, config: Dict) -> Dict:
        """Genera datos simulados realistas basados en precios de referencia"""
        try:
            base_price = config.get('fallback_price', 1.0)
            
            # Simular variación de precio realista (-0.5% a +0.5%)
            import random
            price_variation = random.uniform(-0.005, 0.005)
            current_price = base_price * (1 + price_variation)
            
            # Simular volumen
            volume = random.randint(500000, 2000000)
            
            # Simular volatilidad típica del activo
            if symbol.startswith('XAU') or symbol.startswith('XAG'):
                volatility = random.uniform(0.8, 2.0)  # Metales más volátiles
            else:
                volatility = random.uniform(0.3, 1.2)  # Forex menos volátil
            
            # Simular cambio de 24h
            change_24h = random.uniform(-1.5, 1.5)
            
            logger.info(f"[DATA] Usando datos simulados para {symbol}: ${current_price:.4f}")
            
            return {
                'symbol': symbol,
                'price': current_price,
                'volume': volume,
                'volatility': volatility,
                'spread': self._estimate_spread(symbol, current_price),
                'timestamp': datetime.now(timezone.utc),
                'high_24h': current_price * 1.01,
                'low_24h': current_price * 0.99,
                'change_24h': change_24h
            }
            
        except Exception as e:
            logger.error(f"Error generando datos simulados para {symbol}: {e}")
            return None
    
    def _build_market_data(self, symbol: str, price: float, volume: float, volatility: float, hist) -> Dict:
        """Construye el diccionario de datos de mercado"""
        try:
            return {
                'symbol': symbol,
                'price': price,
                'volume': volume,
                'volatility': volatility,
                'spread': self._estimate_spread(symbol, price),
                'timestamp': datetime.now(timezone.utc),
                'high_24h': float(hist['High'].max()),
                'low_24h': float(hist['Low'].min()),
                'change_24h': ((price - float(hist['Open'].iloc[0])) / float(hist['Open'].iloc[0])) * 100
            }
        except:
            return {
                'symbol': symbol,
                'price': price,
                'volume': volume,
                'volatility': volatility,
                'spread': self._estimate_spread(symbol, price),
                'timestamp': datetime.now(timezone.utc),
                'high_24h': price * 1.01,
                'low_24h': price * 0.99,
                'change_24h': 0.0
            }
    
    def _estimate_spread(self, symbol: str, price: float) -> float:
        """Estima el spread para diferentes tipos de activos"""
        # Spreads típicos para Forex (en pips convertidos a precio)
        forex_spreads = {
            'EURUSD': 0.00015,  # 1.5 pips
            'GBPUSD': 0.00020,  # 2.0 pips
            'USDJPY': 0.015,    # 1.5 pips (en JPY)
            'AUDUSD': 0.00025,  # 2.5 pips
        }
        
        # Spreads típicos para metales preciosos
        metals_spreads = {
            'XAUUSD': 0.50,     # $0.50 para oro
            'XAGUSD': 0.03,     # $0.03 para plata
        }
        
        if symbol in forex_spreads:
            return forex_spreads[symbol]
        elif symbol in metals_spreads:
            return metals_spreads[symbol]
        elif symbol.startswith('XAU') or symbol.startswith('XAG'):
            return price * 0.002  # 0.2% para metales
        else:
            return price * 0.0002  # 0.02% para Forex por defecto

class ForexMetalsBreakoutDetector:
    """Detector de breakouts adaptado para Forex y Metales"""
    
    def __init__(self):
        self.min_confidence = 0.65  # Mayor confianza requerida
        self.forex_params = {
            'min_price_change': 0.3,    # 0.3% mínimo para Forex
            'min_volume_ratio': 1.2,    # 20% más volumen
            'volatility_threshold': 0.8  # Volatilidad mínima
        }
        
        self.metals_params = {
            'min_price_change': 0.5,    # 0.5% mínimo para Metales  
            'min_volume_ratio': 1.5,    # 50% más volumen
            'volatility_threshold': 1.0  # Volatilidad mínima
        }
    
    async def analyze_breakout(self, data: Dict, session_info: Dict) -> Optional[ForexMetalsSignal]:
        """Analiza breakouts para Forex/Metales"""
        try:
            symbol = data['symbol']
            price = data['price']
            volume = data['volume']
            volatility = data['volatility']
            change_24h = data['change_24h']
            
            # Seleccionar parámetros según tipo de activo
            if symbol.startswith('XAU') or symbol.startswith('XAG') or symbol.startswith('XPT') or symbol.startswith('XPD'):
                params = self.metals_params
                asset_type = 'METALS'
            else:
                params = self.forex_params
                asset_type = 'FOREX'
            
            # Verificar condiciones básicas
            if abs(change_24h) < params['min_price_change']:
                return None
            
            if volatility < params['volatility_threshold']:
                return None
            
            # Calcular confianza basada en múltiples factores
            confidence = self._calculate_confidence(
                change_24h, volatility, volume, session_info, params
            )
            
            if confidence < self.min_confidence:
                return None
            
            # Determinar tipo de señal
            signal_type = 'bullish_breakout' if change_24h > 0 else 'bearish_breakout'
            
            # Calcular nivel de riesgo
            risk_level = self._calculate_risk_level(volatility, session_info, asset_type)
            
            return ForexMetalsSignal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                risk_level=risk_level,
                price=price,
                volume=volume,
                timestamp=datetime.now(timezone.utc),
                market_session=session_info['session'],
                volatility=volatility,
                spread=data['spread']
            )
            
        except Exception as e:
            logger.error(f"Error analizando breakout para {data.get('symbol', 'unknown')}: {e}")
            return None
    
    def _calculate_confidence(self, change_24h: float, volatility: float, 
                            volume: float, session_info: Dict, params: Dict) -> float:
        """Calcula la confianza de la señal"""
        confidence = 0.0
        
        # Factor de cambio de precio (30%)
        price_factor = min(abs(change_24h) / (params['min_price_change'] * 3), 1.0) * 0.3
        confidence += price_factor
        
        # Factor de volatilidad (25%)
        vol_factor = min(volatility / (params['volatility_threshold'] * 2), 1.0) * 0.25
        confidence += vol_factor
        
        # Factor de sesión de mercado (25%)
        session_factor = {
            'HIGH': 0.25,
            'MEDIUM': 0.15,
            'LOW': 0.05,
            'NONE': 0.0
        }.get(session_info.get('priority', 'LOW'), 0.05)
        confidence += session_factor
        
        # Factor de volumen (20%)
        if volume > 0:
            volume_factor = min(volume / 1000000, 1.0) * 0.2  # Normalizado
            confidence += volume_factor
        
        return min(confidence, 1.0)
    
    def _calculate_risk_level(self, volatility: float, session_info: Dict, asset_type: str) -> str:
        """Calcula el nivel de riesgo"""
        risk_score = 0
        
        # Volatilidad
        if volatility > 2.0:
            risk_score += 2
        elif volatility > 1.0:
            risk_score += 1
        
        # Sesión de mercado
        if session_info.get('priority') == 'LOW':
            risk_score += 1
        elif session_info.get('priority') == 'NONE':
            risk_score += 2
        
        # Tipo de activo
        if asset_type == 'METALS':
            risk_score += 1  # Metales generalmente más volátiles
        
        if risk_score >= 3:
            return 'HIGH'
        elif risk_score >= 1:
            return 'MEDIUM'
        else:
            return 'LOW'

class ForexMetalsTradingEngine:
    """Motor de trading para Forex y Metales"""
    
    def __init__(self, initial_capital: float = 500.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.active_positions = {}
        self.pending_orders = {}
        self.max_positions = 4  # Máximo 4 posiciones simultáneas
        self.max_risk_per_trade = 0.02  # 2% máximo por trade
        
        # Parámetros específicos por tipo de activo
        self.trading_params = {
            'FOREX': {
                'position_size': 0.03,      # 3% del capital
                'stop_loss': 0.008,         # 0.8%
                'take_profit': 0.016,       # 1.6% (ratio 1:2)
                'max_spread': 0.0005        # 0.05% spread máximo
            },
            'METALS': {
                'position_size': 0.025,     # 2.5% del capital
                'stop_loss': 0.012,         # 1.2%
                'take_profit': 0.024,       # 2.4% (ratio 1:2)
                'max_spread': 0.001         # 0.1% spread máximo
            }
        }
        
        # Inicializar base de datos
        self._init_database()
    
    def _init_database(self):
        """Inicializa la base de datos para tracking"""
        try:
            self.conn = sqlite3.connect('forex_metals_trading.db')
            cursor = self.conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS forex_metals_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    symbol TEXT,
                    signal_type TEXT,
                    confidence REAL,
                    risk_level TEXT,
                    price REAL,
                    volume REAL,
                    market_session TEXT,
                    volatility REAL,
                    spread REAL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS forex_metals_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    symbol TEXT,
                    side TEXT,
                    quantity REAL,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    status TEXT,
                    exit_price REAL,
                    pnl REAL,
                    capital_after REAL
                )
            ''')
            
            self.conn.commit()
            logger.info("[DB] Base de datos inicializada correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando base de datos: {e}")
    
    def should_execute_trade(self, signal: ForexMetalsSignal) -> bool:
        """Determina si se debe ejecutar un trade"""
        # Verificar confianza mínima
        if signal.confidence < 0.65:
            return False
        
        # Verificar riesgo máximo
        if signal.risk_level == 'HIGH':
            return False
        
        # Verificar número máximo de posiciones
        if len(self.active_positions) >= self.max_positions:
            return False
        
        # Verificar si ya hay posición en este símbolo
        if signal.symbol in self.active_positions:
            return False
        
        # Verificar spread máximo
        asset_type = 'METALS' if signal.symbol.startswith('XAU') or signal.symbol.startswith('XAG') else 'FOREX'
        max_spread = self.trading_params[asset_type]['max_spread']
        
        if signal.spread > max_spread:
            logger.info(f"❌ Spread muy alto para {signal.symbol}: {signal.spread:.6f} > {max_spread:.6f}")
            return False
        
        return True
    
    async def execute_paper_trade(self, signal: ForexMetalsSignal) -> bool:
        """Ejecuta un trade en paper trading"""
        try:
            asset_type = 'METALS' if signal.symbol.startswith('XAU') or signal.symbol.startswith('XAG') else 'FOREX'
            params = self.trading_params[asset_type]
            
            # Calcular tamaño de posición
            position_value = self.current_capital * params['position_size']
            quantity = position_value / signal.price
            
            # Calcular stop loss y take profit
            if signal.signal_type == 'bullish_breakout':
                side = 'BUY'
                stop_loss = signal.price * (1 - params['stop_loss'])
                take_profit = signal.price * (1 + params['take_profit'])
            else:
                side = 'SELL'
                stop_loss = signal.price * (1 + params['stop_loss'])
                take_profit = signal.price * (1 - params['take_profit'])
            
            # Crear posición
            position = {
                'symbol': signal.symbol,
                'side': side,
                'quantity': quantity,
                'entry_price': signal.price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'timestamp': signal.timestamp,
                'asset_type': asset_type
            }
            
            self.active_positions[signal.symbol] = position
            
            # Guardar en base de datos
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO forex_metals_trades 
                (timestamp, symbol, side, quantity, entry_price, stop_loss, take_profit, status, capital_after)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal.timestamp.isoformat(),
                signal.symbol,
                side,
                quantity,
                signal.price,
                stop_loss,
                take_profit,
                'OPEN',
                self.current_capital
            ))
            self.conn.commit()
            
            logger.info(f"✅ TRADE EJECUTADO: {side} {signal.symbol} @ ${signal.price:.4f}")
            logger.info(f"   💰 Cantidad: {quantity:.4f}")
            logger.info(f"   🛑 Stop Loss: ${stop_loss:.4f}")
            logger.info(f"   🎯 Take Profit: ${take_profit:.4f}")
            logger.info(f"   📊 Confianza: {signal.confidence:.1%}")
            logger.info(f"   ⚠️ Riesgo: {signal.risk_level}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error ejecutando trade: {e}")
            return False
    
    async def monitor_positions(self, data_provider: ForexMetalsDataProvider):
        """Monitorea posiciones activas"""
        positions_to_close = []
        
        for symbol, position in self.active_positions.items():
            try:
                # Obtener precio actual
                market_data = await data_provider.get_market_data(symbol)
                if not market_data:
                    continue
                
                current_price = market_data['price']
                entry_price = position['entry_price']
                side = position['side']
                
                # Verificar stop loss y take profit
                should_close = False
                exit_reason = ""
                
                if side == 'BUY':
                    if current_price <= position['stop_loss']:
                        should_close = True
                        exit_reason = "STOP_LOSS"
                    elif current_price >= position['take_profit']:
                        should_close = True
                        exit_reason = "TAKE_PROFIT"
                else:  # SELL
                    if current_price >= position['stop_loss']:
                        should_close = True
                        exit_reason = "STOP_LOSS"
                    elif current_price <= position['take_profit']:
                        should_close = True
                        exit_reason = "TAKE_PROFIT"
                
                if should_close:
                    await self._close_position(symbol, current_price, exit_reason)
                    positions_to_close.append(symbol)
                
            except Exception as e:
                logger.error(f"Error monitoreando posición {symbol}: {e}")
        
        # Remover posiciones cerradas
        for symbol in positions_to_close:
            if symbol in self.active_positions:
                del self.active_positions[symbol]
    
    async def _close_position(self, symbol: str, exit_price: float, reason: str):
        """Cierra una posición"""
        try:
            position = self.active_positions[symbol]
            entry_price = position['entry_price']
            quantity = position['quantity']
            side = position['side']
            
            # Calcular PnL
            if side == 'BUY':
                pnl = (exit_price - entry_price) * quantity
            else:  # SELL
                pnl = (entry_price - exit_price) * quantity
            
            # Actualizar capital
            self.current_capital += pnl
            
            # Actualizar en base de datos
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE forex_metals_trades 
                SET status = ?, exit_price = ?, pnl = ?, capital_after = ?
                WHERE symbol = ? AND status = 'OPEN'
            ''', ('CLOSED', exit_price, pnl, self.current_capital, symbol))
            self.conn.commit()
            
            pnl_pct = (pnl / (entry_price * quantity)) * 100
            
            logger.info(f"🔒 POSICIÓN CERRADA: {symbol}")
            logger.info(f"   📈 Entrada: ${entry_price:.4f} → Salida: ${exit_price:.4f}")
            logger.info(f"   💰 PnL: ${pnl:.2f} ({pnl_pct:+.2f}%)")
            logger.info(f"   📊 Capital: ${self.current_capital:.2f}")
            logger.info(f"   🔍 Razón: {reason}")
            
        except Exception as e:
            logger.error(f"Error cerrando posición {symbol}: {e}")

class ForexMetalsAutoTradingSystem:
    """Sistema principal de auto trading para Forex y Metales"""
    
    def __init__(self):
        self.session_manager = MarketSessionManager()
        self.data_provider = ForexMetalsDataProvider()
        self.breakout_detector = ForexMetalsBreakoutDetector()
        self.trading_engine = ForexMetalsTradingEngine()
        
        # Símbolos a monitorear
        self.symbols = [
            # Forex Major Pairs
            'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD',
            # Metales Preciosos
            'XAUUSD', 'XAGUSD'
        ]
        
        self.cycle_count = 0
        self.total_signals = 0
        
        logger.info("[INIT] SICAR Forex & Metals Auto Trading System INICIADO")
        logger.info(f"[CAPITAL] Capital inicial: ${self.trading_engine.initial_capital:.2f}")
        logger.info(f"[SYMBOLS] Símbolos monitoreados: {', '.join(self.symbols)}")
    
    async def run_monitoring_cycle(self):
        """Ejecuta un ciclo de monitoreo"""
        self.cycle_count += 1
        current_time = datetime.now(timezone.utc).strftime("%H:%M:%S")
        
        logger.info(f"\n[CYCLE] CICLO {self.cycle_count} - {current_time}")
        
        # Obtener información de sesión actual
        session_info = self.session_manager.get_current_session()
        logger.info(f"[SESSION] Sesión: {session_info['session']} | Prioridad: {session_info.get('priority', 'N/A')}")
        
        # Si el mercado está cerrado, esperar
        if not session_info['is_open']:
            next_open = session_info.get('next_open')
            if next_open:
                logger.info(f"[CLOSED] Mercado cerrado. Próxima apertura: {next_open.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            return
        
        # Monitorear posiciones activas
        await self.trading_engine.monitor_positions(self.data_provider)
        
        # Buscar nuevas señales
        signals_detected = 0
        
        for symbol in self.symbols:
            try:
                # Obtener datos de mercado
                market_data = await self.data_provider.get_market_data(symbol)
                if not market_data:
                    continue
                
                # Analizar breakout
                signal = await self.breakout_detector.analyze_breakout(market_data, session_info)
                if not signal:
                    continue
                
                signals_detected += 1
                self.total_signals += 1
                
                # Guardar señal en base de datos
                cursor = self.trading_engine.conn.cursor()
                cursor.execute('''
                    INSERT INTO forex_metals_signals 
                    (timestamp, symbol, signal_type, confidence, risk_level, price, volume, market_session, volatility, spread)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    signal.timestamp.isoformat(),
                    signal.symbol,
                    signal.signal_type,
                    signal.confidence,
                    signal.risk_level,
                    signal.price,
                    signal.volume,
                    signal.market_session,
                    signal.volatility,
                    signal.spread
                ))
                self.trading_engine.conn.commit()
                
                logger.info(f"[SIGNAL] SEÑAL DETECTADA: {signal.symbol} | {signal.signal_type.upper()}")
                logger.info(f"   [CONF] Confianza: {signal.confidence:.1%} | Riesgo: {signal.risk_level}")
                logger.info(f"   [PRICE] Precio: ${signal.price:.4f} | Spread: {signal.spread:.6f}")
                
                # Evaluar si ejecutar trade
                if self.trading_engine.should_execute_trade(signal):
                    await self.trading_engine.execute_paper_trade(signal)
                else:
                    logger.info(f"[SKIP] Trade no ejecutado para {signal.symbol} (condiciones no cumplidas)")
                
            except Exception as e:
                logger.error(f"Error procesando {symbol}: {e}")
        
        # Resumen del ciclo
        active_positions = len(self.trading_engine.active_positions)
        current_capital = self.trading_engine.current_capital
        
        logger.info(f"[SIGNALS] Señales detectadas: {signals_detected}")
        logger.info(f"[POSITIONS] Posiciones activas: {active_positions}")
        
        if active_positions > 0:
            logger.info("[PORTFOLIO] Posiciones:")
            for symbol, pos in self.trading_engine.active_positions.items():
                logger.info(f"   {symbol}: {pos['side']} @ ${pos['entry_price']:.4f}")
        
        logger.info(f"[CAPITAL] Capital actual: ${current_capital:.2f}")
        
        # Estadísticas generales
        if self.cycle_count % 10 == 0:  # Cada 10 ciclos
            roi = ((current_capital - self.trading_engine.initial_capital) / self.trading_engine.initial_capital) * 100
            logger.info(f"[STATS] ROI Total: {roi:+.2f}% | Señales totales: {self.total_signals}")
    
    async def start_monitoring(self):
        """Inicia el monitoreo continuo"""
        logger.info("[START] Iniciando monitoreo continuo...")
        
        while True:
            try:
                await self.run_monitoring_cycle()
                logger.info("[WAIT] Esperando 60 segundos para el próximo ciclo...")
                await asyncio.sleep(60)  # Ciclo cada minuto
                
            except KeyboardInterrupt:
                logger.info("[STOP] Deteniendo sistema por interrupción del usuario")
                break
            except Exception as e:
                logger.error(f"Error en ciclo de monitoreo: {e}")
                await asyncio.sleep(30)  # Esperar 30 segundos antes de reintentar

async def main():
    """Función principal"""
    system = ForexMetalsAutoTradingSystem()
    await system.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main())