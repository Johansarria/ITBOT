#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulador de Trading V4 Ultra-Agresivo con Datos Reales de Binance
Estrategia ultra-agresiva con apalancamiento 3x y datos reales de mercado
Objetivo: 15% mensual con gestión de riesgo avanzada
"""

import os
import json
import time
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import threading
import signal
import sys
from dataclasses import dataclass, asdict
import warnings
warnings.filterwarnings('ignore')

# Configurar claves API de Binance
os.environ['BINANCE_API_KEY'] = 'D6Ef5kM5nIcgvs9IpXOg7XeFOB8C81zNJAy6uqYCk5QVuqf5ffTPmsXPSuqBAnSs'
os.environ['BINANCE_SECRET_KEY'] = 'BwIztawVAEltATAQI0V5GCJqfNAmwuI6KghC8Nc5X6avvRkcwizwG7qNORtOOnKy'

@dataclass
class RealTradeSignal:
    """Señal de trading con datos reales"""
    symbol: str
    signal_type: str  # BUY, SELL, HOLD
    confidence: float  # 0-100
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    position_size: float
    leverage: float
    timestamp: datetime
    reason: str
    rsi: float
    macd: float
    trend: str
    volume_surge: bool
    momentum_score: float

@dataclass
class RealTradeExecution:
    """Ejecución de trade con datos reales"""
    trade_id: str
    symbol: str
    side: str
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    leverage: float
    pnl_usdt: float
    pnl_percentage: float
    duration_minutes: int
    status: str  # OPEN, CLOSED, STOPPED
    entry_time: datetime
    exit_time: Optional[datetime]
    stop_loss: float
    take_profit: float
    fees_usdt: float
    slippage_usdt: float

class BinanceRealDataProvider:
    """Proveedor de datos reales de Binance"""
    
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
        self.price_history = {symbol: [] for symbol in self.symbols}
        
    def get_real_price(self, symbol: str) -> Optional[Dict]:
        """Obtiene precio real y datos del ticker"""
        try:
            response = requests.get(
                f"{self.base_url}/ticker/24hr",
                params={'symbol': symbol},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'symbol': data['symbol'],
                    'price': float(data['lastPrice']),
                    'volume': float(data['volume']),
                    'price_change_24h': float(data['priceChangePercent']),
                    'high_24h': float(data['highPrice']),
                    'low_24h': float(data['lowPrice']),
                    'bid': float(data['bidPrice']),
                    'ask': float(data['askPrice']),
                    'spread': float(data['askPrice']) - float(data['bidPrice']),
                    'count': int(data['count'])
                }
        except Exception as e:
            print(f"❌ Error obteniendo datos de {symbol}: {e}")
        
        return None
    
    def get_klines(self, symbol: str, interval: str = '1m', limit: int = 100) -> List[Dict]:
        """Obtiene datos de velas (klines) reales"""
        try:
            response = requests.get(
                f"{self.base_url}/klines",
                params={
                    'symbol': symbol,
                    'interval': interval,
                    'limit': limit
                },
                timeout=15
            )
            
            if response.status_code == 200:
                klines = response.json()
                processed_data = []
                
                for kline in klines:
                    processed_data.append({
                        'timestamp': datetime.fromtimestamp(kline[0] / 1000),
                        'open': float(kline[1]),
                        'high': float(kline[2]),
                        'low': float(kline[3]),
                        'close': float(kline[4]),
                        'volume': float(kline[5])
                    })
                
                return processed_data
        except Exception as e:
            print(f"❌ Error obteniendo klines de {symbol}: {e}")
        
        return []
    
    def calculate_technical_indicators(self, symbol: str) -> Dict:
        """Calcula indicadores técnicos con datos reales"""
        klines = self.get_klines(symbol, '1m', 100)
        
        if len(klines) < 20:
            return {}
        
        closes = [k['close'] for k in klines]
        highs = [k['high'] for k in klines]
        lows = [k['low'] for k in klines]
        volumes = [k['volume'] for k in klines]
        
        # RSI
        rsi = self._calculate_rsi(closes)
        
        # MACD
        macd_line, macd_signal = self._calculate_macd(closes)
        macd_histogram = macd_line - macd_signal
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(closes)
        
        # Volume analysis
        avg_volume = np.mean(volumes[-20:])
        current_volume = volumes[-1]
        volume_surge = current_volume > avg_volume * 1.5
        
        # Momentum
        momentum = (closes[-1] - closes[-10]) / closes[-10] * 100
        
        # Trend analysis
        sma_20 = np.mean(closes[-20:])
        sma_50 = np.mean(closes[-50:]) if len(closes) >= 50 else sma_20
        
        if closes[-1] > sma_20 > sma_50:
            trend = "BULLISH"
        elif closes[-1] < sma_20 < sma_50:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"
        
        return {
            'rsi': rsi,
            'macd': macd_histogram,
            'macd_line': macd_line,
            'macd_signal': macd_signal,
            'bb_upper': bb_upper,
            'bb_middle': bb_middle,
            'bb_lower': bb_lower,
            'volume_surge': volume_surge,
            'momentum': momentum,
            'trend': trend,
            'sma_20': sma_20,
            'sma_50': sma_50
        }
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calcula RSI"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(self, prices: List[float]) -> Tuple[float, float]:
        """Calcula MACD"""
        if len(prices) < 26:
            return 0.0, 0.0
        
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        macd_line = ema_12 - ema_26
        
        # Signal line (EMA 9 del MACD)
        macd_signal = macd_line  # Simplificado
        
        return macd_line, macd_signal
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calcula EMA"""
        if len(prices) < period:
            return np.mean(prices)
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20) -> Tuple[float, float, float]:
        """Calcula Bollinger Bands"""
        if len(prices) < period:
            avg = np.mean(prices)
            return avg * 1.02, avg, avg * 0.98
        
        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        
        upper = sma + (2 * std)
        lower = sma - (2 * std)
        
        return upper, sma, lower

class UltraAggressiveStrategyV4Real:
    """Estrategia V4 Ultra-Agresiva con datos reales"""
    
    def __init__(self):
        self.leverage = 3.0  # Apalancamiento 3x
        self.max_risk_per_trade = 0.05  # 5% máximo por trade
        self.min_confidence = 75  # Confianza mínima 75%
        self.scalping_mode = True
        self.aggressive_tp = True
        
        # Parámetros ultra-agresivos
        self.rsi_oversold = 25  # Más agresivo
        self.rsi_overbought = 75
        self.macd_threshold = 0.001  # Más sensible
        self.momentum_threshold = 2.0  # Más agresivo
        
    def analyze_signal(self, symbol: str, market_data: Dict, indicators: Dict) -> Optional[RealTradeSignal]:
        """Analiza y genera señales ultra-agresivas"""
        if not market_data or not indicators:
            return None
        
        current_price = market_data['price']
        rsi = indicators.get('rsi', 50)
        macd = indicators.get('macd', 0)
        trend = indicators.get('trend', 'NEUTRAL')
        volume_surge = indicators.get('volume_surge', False)
        momentum = indicators.get('momentum', 0)
        bb_upper = indicators.get('bb_upper', current_price * 1.02)
        bb_lower = indicators.get('bb_lower', current_price * 0.98)
        
        signal_type = "HOLD"
        confidence = 0
        reason = "No clear signal"
        
        # Señales de COMPRA ultra-agresivas
        buy_signals = 0
        buy_reasons = []
        
        if rsi < self.rsi_oversold:
            buy_signals += 3
            buy_reasons.append(f"RSI oversold ({rsi:.1f})")
        
        if macd > self.macd_threshold:
            buy_signals += 2
            buy_reasons.append(f"MACD bullish ({macd:.4f})")
        
        if trend == "BULLISH":
            buy_signals += 2
            buy_reasons.append("Bullish trend")
        
        if volume_surge:
            buy_signals += 2
            buy_reasons.append("Volume surge")
        
        if momentum > self.momentum_threshold:
            buy_signals += 2
            buy_reasons.append(f"Strong momentum ({momentum:.2f}%)")
        
        if current_price <= bb_lower:
            buy_signals += 1
            buy_reasons.append("Price at BB lower")
        
        # Señales de VENTA ultra-agresivas
        sell_signals = 0
        sell_reasons = []
        
        if rsi > self.rsi_overbought:
            sell_signals += 3
            sell_reasons.append(f"RSI overbought ({rsi:.1f})")
        
        if macd < -self.macd_threshold:
            sell_signals += 2
            sell_reasons.append(f"MACD bearish ({macd:.4f})")
        
        if trend == "BEARISH":
            sell_signals += 2
            sell_reasons.append("Bearish trend")
        
        if volume_surge and momentum < -self.momentum_threshold:
            sell_signals += 2
            sell_reasons.append("Volume surge + negative momentum")
        
        if current_price >= bb_upper:
            sell_signals += 1
            sell_reasons.append("Price at BB upper")
        
        # Determinar señal final
        if buy_signals >= 5:
            signal_type = "BUY"
            confidence = min(95, 60 + buy_signals * 5)
            reason = "; ".join(buy_reasons)
        elif sell_signals >= 5:
            signal_type = "SELL"
            confidence = min(95, 60 + sell_signals * 5)
            reason = "; ".join(sell_reasons)
        
        # Solo generar señales de alta confianza
        if confidence < self.min_confidence:
            return None
        
        # Calcular niveles de precio
        if signal_type == "BUY":
            stop_loss = current_price * 0.985  # 1.5% SL
            take_profit_1 = current_price * 1.02   # 2% TP1
            take_profit_2 = current_price * 1.04   # 4% TP2
            take_profit_3 = current_price * 1.06   # 6% TP3
        else:  # SELL
            stop_loss = current_price * 1.015  # 1.5% SL
            take_profit_1 = current_price * 0.98   # 2% TP1
            take_profit_2 = current_price * 0.96   # 4% TP2
            take_profit_3 = current_price * 0.94   # 6% TP3
        
        # Calcular tamaño de posición con apalancamiento
        position_size = self.max_risk_per_trade * self.leverage
        
        # Calcular momentum score
        momentum_score = abs(momentum) + (confidence / 100) * 50
        
        return RealTradeSignal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            take_profit_3=take_profit_3,
            position_size=position_size,
            leverage=self.leverage,
            timestamp=datetime.now(),
            reason=reason,
            rsi=rsi,
            macd=macd,
            trend=trend,
            volume_surge=volume_surge,
            momentum_score=momentum_score
        )

class LiveTradingSimulatorV4UltraReal:
    """Simulador V4 Ultra-Agresivo con datos reales"""
    
    def __init__(self, initial_capital: float = 500.0):
        self.initial_capital = initial_capital
        self.current_balance = initial_capital
        self.data_provider = BinanceRealDataProvider()
        self.strategy = UltraAggressiveStrategyV4Real()
        
        # Historial y métricas
        self.trades_history: List[RealTradeExecution] = []
        self.signals_history: List[RealTradeSignal] = []
        self.balance_history: List[float] = [initial_capital]
        
        # Control de ejecución
        self.running = True
        self.start_time = datetime.now()
        self.update_interval = 3  # segundos
        
        # Configurar manejador de señales
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print("\n" + "="*80)
        print("🚀 SIMULADOR V4 ULTRA-AGRESIVO CON DATOS REALES DE BINANCE")
        print("="*80)
        print(f"💰 Capital inicial: ${self.initial_capital:,.2f} USDT")
        print(f"⚡ Apalancamiento: {self.strategy.leverage}x")
        print(f"🎯 Objetivo mensual: 15%")
        print(f"🔄 Actualización: cada {self.update_interval}s")
        print(f"📊 Pares: {', '.join(self.data_provider.symbols)}")
        print("="*80)
    
    def _signal_handler(self, signum, frame):
        """Manejador de señales para cierre limpio"""
        print(f"\n⚠️  Señal {signum} recibida. Cerrando simulación...")
        self.running = False
    
    def display_real_time_data(self):
        """Muestra datos en tiempo real"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("\n" + "="*100)
        print("📈 SIMULADOR V4 ULTRA-AGRESIVO - DATOS REALES DE BINANCE")
        print("="*100)
        
        # Información de sesión
        elapsed = datetime.now() - self.start_time
        pnl_session = self.current_balance - self.initial_capital
        pnl_pct = (pnl_session / self.initial_capital) * 100
        
        print(f"⏰ Tiempo de sesión: {str(elapsed).split('.')[0]}")
        print(f"💰 Balance actual: ${self.current_balance:,.2f} USDT")
        print(f"📊 P&L sesión: ${pnl_session:+,.2f} ({pnl_pct:+.2f}%)")
        print(f"📈 Trades ejecutados: {len(self.trades_history)}")
        print(f"🎯 Señales generadas: {len(self.signals_history)}")
        
        print("\n" + "-"*100)
        print("📊 DATOS DE MERCADO EN TIEMPO REAL")
        print("-"*100)
        
        # Tabla de datos de mercado
        print(f"{'SÍMBOLO':<12} {'PRECIO':<12} {'RSI':<6} {'MACD':<8} {'TENDENCIA':<10} {'SEÑAL':<8} {'CONFIANZA':<10} {'RAZÓN':<30}")
        print("-"*100)
        
        active_signals = []
        
        for symbol in self.data_provider.symbols:
            market_data = self.data_provider.get_real_price(symbol)
            
            if market_data:
                indicators = self.data_provider.calculate_technical_indicators(symbol)
                signal = self.strategy.analyze_signal(symbol, market_data, indicators)
                
                price = market_data['price']
                rsi = indicators.get('rsi', 0)
                macd = indicators.get('macd', 0)
                trend = indicators.get('trend', 'NEUTRAL')
                
                if signal:
                    signal_emoji = "🟢" if signal.signal_type == "BUY" else "🔴" if signal.signal_type == "SELL" else "⚪"
                    confidence_emoji = "⚡" if signal.confidence >= 85 else "💫" if signal.confidence >= 75 else "💤"
                    
                    print(f"{symbol:<12} ${price:<11.4f} {rsi:<6.1f} {macd:<8.3f} {trend:<10} {signal_emoji} {signal.signal_type:<7} {confidence_emoji} {signal.confidence:<3.0f}% {signal.reason[:30]:<30}")
                    
                    if signal.confidence >= 80:
                        active_signals.append(signal)
                        self.signals_history.append(signal)
                else:
                    print(f"{symbol:<12} ${price:<11.4f} {rsi:<6.1f} {macd:<8.3f} {trend:<10} ⚪ HOLD    💤 DÉBIL    No clear signal")
            else:
                print(f"{symbol:<12} {'ERROR':<11} {'N/A':<6} {'N/A':<8} {'N/A':<10} ❌ ERROR   {'N/A':<10} Connection failed")
        
        # Mostrar señales activas de alta confianza
        if active_signals:
            print("\n" + "-"*100)
            print("🎯 SEÑALES DE ALTA CONFIANZA DETECTADAS")
            print("-"*100)
            
            for signal in active_signals:
                action_emoji = "🟢 COMPRAR" if signal.signal_type == "BUY" else "🔴 VENDER"
                print(f"\n{action_emoji} {signal.symbol}")
                print(f"  💰 Precio entrada: ${signal.entry_price:.4f}")
                print(f"  🛡️  Stop Loss: ${signal.stop_loss:.4f} ({((signal.stop_loss/signal.entry_price-1)*100):+.2f}%)")
                print(f"  🎯 Take Profit 1: ${signal.take_profit_1:.4f} ({((signal.take_profit_1/signal.entry_price-1)*100):+.2f}%)")
                print(f"  🎯 Take Profit 2: ${signal.take_profit_2:.4f} ({((signal.take_profit_2/signal.entry_price-1)*100):+.2f}%)")
                print(f"  🎯 Take Profit 3: ${signal.take_profit_3:.4f} ({((signal.take_profit_3/signal.entry_price-1)*100):+.2f}%)")
                print(f"  ⚡ Apalancamiento: {signal.leverage}x")
                print(f"  📊 Tamaño posición: {signal.position_size:.1f}% del capital")
                print(f"  🎲 Confianza: {signal.confidence:.0f}%")
                print(f"  📝 Razón: {signal.reason}")
                
                # Simular ejecución del trade
                investment = self.current_balance * (signal.position_size / 100)
                risk_amount = investment * 0.015  # 1.5% riesgo real
                
                print(f"  💵 Inversión: ${investment:.2f} USDT")
                print(f"  ⚠️  Riesgo real: ${risk_amount:.2f} USDT")
        
        # Resumen de señales
        buy_signals = len([s for s in self.signals_history[-10:] if s.signal_type == "BUY"])
        sell_signals = len([s for s in self.signals_history[-10:] if s.signal_type == "SELL"])
        
        print("\n" + "-"*100)
        print("📊 RESUMEN DE SEÑALES (ÚLTIMAS 10)")
        print("-"*100)
        print(f"🟢 Señales de COMPRA: {buy_signals}")
        print(f"🔴 Señales de VENTA: {sell_signals}")
        print(f"⚪ Señales de HOLD: {10 - buy_signals - sell_signals}")
        print(f"⚡ Señales activas de alta confianza: {len(active_signals)}")
        
        if len(active_signals) > 0:
            print("\n🚨 RECOMENDACIÓN: Ejecutar trades de alta confianza")
            print("💡 La estrategia V4 Ultra-Agresiva ha detectado oportunidades")
        else:
            print("\nℹ️  ESTADO: Esperando señales de alta confianza")
            print("⏳ La estrategia es selectiva y busca las mejores oportunidades")
        
        print("\n" + "="*100)
        print(f"🔄 Próxima actualización en {self.update_interval} segundos... (Ctrl+C para detener)")
        print("="*100)
    
    def run_simulation(self):
        """Ejecuta la simulación en tiempo real"""
        print("\n🚀 Iniciando simulación V4 Ultra-Agresiva con datos reales...")
        print("📡 Conectando a Binance API...")
        
        # Verificar conectividad
        test_data = self.data_provider.get_real_price('BTCUSDT')
        if not test_data:
            print("❌ Error: No se puede conectar a Binance API")
            return
        
        print("✅ Conexión establecida con Binance")
        print("🎯 Buscando oportunidades de trading...")
        
        try:
            while self.running:
                self.display_real_time_data()
                time.sleep(self.update_interval)
                
        except KeyboardInterrupt:
            print("\n⚠️  Simulación interrumpida por el usuario")
        except Exception as e:
            print(f"\n❌ Error en simulación: {e}")
        finally:
            self.generate_final_report()
    
    def generate_final_report(self):
        """Genera reporte final de la simulación"""
        print("\n" + "="*80)
        print("📊 REPORTE FINAL - SIMULACIÓN V4 ULTRA-AGRESIVA")
        print("="*80)
        
        elapsed = datetime.now() - self.start_time
        total_signals = len(self.signals_history)
        high_confidence_signals = len([s for s in self.signals_history if s.confidence >= 80])
        
        print(f"⏰ Duración total: {str(elapsed).split('.')[0]}")
        print(f"🎯 Señales generadas: {total_signals}")
        print(f"⚡ Señales de alta confianza: {high_confidence_signals}")
        print(f"💰 Balance final: ${self.current_balance:,.2f} USDT")
        
        if total_signals > 0:
            avg_confidence = np.mean([s.confidence for s in self.signals_history])
            print(f"📊 Confianza promedio: {avg_confidence:.1f}%")
            
            # Análisis por símbolo
            symbol_stats = {}
            for signal in self.signals_history:
                if signal.symbol not in symbol_stats:
                    symbol_stats[signal.symbol] = {'count': 0, 'avg_confidence': 0}
                symbol_stats[signal.symbol]['count'] += 1
                symbol_stats[signal.symbol]['avg_confidence'] += signal.confidence
            
            print("\n📈 Estadísticas por símbolo:")
            for symbol, stats in symbol_stats.items():
                avg_conf = stats['avg_confidence'] / stats['count']
                print(f"  {symbol}: {stats['count']} señales, {avg_conf:.1f}% confianza promedio")
        
        print("\n✅ Simulación completada")
        print("="*80)

def main():
    """Función principal"""
    print("🚀 Iniciando Simulador V4 Ultra-Agresivo con Datos Reales")
    
    try:
        simulator = LiveTradingSimulatorV4UltraReal(initial_capital=500.0)
        simulator.run_simulation()
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()