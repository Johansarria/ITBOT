#!/usr/bin/env python3
"""
MÓDULO DE INTEGRACIÓN DIRECTA
Estrategias autónomas para integrar con tu bot actual de ITBOT
Compatible con tu arquitectura existente
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Importar desde tu bot actual (ajustar según tu estructura)
# from config import *
# from risk_manager import RiskManager
# from handlers import *

@dataclass
class TradeSignal:
    pair: str
    direction: str  # 'LONG' or 'SHORT'
    entry_price: float
    stop_loss: float
    take_profit: List[float]
    position_size: float
    strategy: str
    confidence: float
    timestamp: datetime

class AutonomousStrategiesModule:
    """
    Módulo de estrategias autónomas para integrar con ITBOT existente
    """
    
    def __init__(self, capital_inicial: float, existing_bot_config: Dict):
        self.capital_inicial = capital_inicial
        self.bot_config = existing_bot_config
        self.active_positions = {}
        self.performance_metrics = {}
        
        # Configuración de estrategias (ajustable)
        self.strategy_config = {
            'scalping_auto': {
                'enabled': True,
                'capital_pct': 0.35,
                'max_positions': 3,
                'timeframes': ['1m', '3m', '5m'],
                'pairs': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT'],
                'risk_per_trade': 0.02
            },
            'mean_reversion': {
                'enabled': True,
                'capital_pct': 0.25,
                'max_positions': 2,
                'timeframes': ['15m', '30m', '1h'],
                'pairs': 'auto_select',  # Selección automática por volumen
                'risk_per_trade': 0.03
            },
            'breakout_momentum': {
                'enabled': True,
                'capital_pct': 0.20,
                'max_positions': 2,
                'timeframes': ['5m', '15m', '30m'],
                'pairs': 'high_volatility',  # Pares con alta volatilidad
                'risk_per_trade': 0.025
            },
            'arbitrage_temporal': {
                'enabled': True,
                'capital_pct': 0.15,
                'max_positions': 5,  # Múltiples oportunidades simultáneas
                'execution_speed': 'ultra_fast',
                'min_profit_threshold': 0.002
            },
            'volatility_trading': {
                'enabled': True,
                'capital_pct': 0.05,
                'max_positions': 1,
                'timeframes': ['1m', '5m'],
                'pairs': ['BTCUSDT', 'ETHUSDT']  # Solo major pairs
            }
        }
        
        # Logging para debugging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """
        Inicializa el módulo con tu bot existente
        """
        self.logger.info("🚀 Iniciando Módulo de Estrategias Autónomas")
        
        # Verificar conexión con Binance (usar tu cliente existente)
        await self.verify_binance_connection()
        
        # Cargar datos históricos necesarios
        await self.load_historical_data()
        
        # Inicializar indicadores en tiempo real
        await self.setup_realtime_indicators()
        
        self.logger.info("✅ Módulo inicializado correctamente")
    
    # ESTRATEGIA 1: SCALPING AUTOMATIZADO
    async def strategy_scalping_auto(self) -> List[TradeSignal]:
        """
        Estrategia de scalping completamente automatizada
        Integrable con tu sistema de ejecución actual
        """
        signals = []
        config = self.strategy_config['scalping_auto']
        
        if not config['enabled']:
            return signals
        
        for pair in config['pairs']:
            try:
                # Obtener datos recientes (usar tu función existente)
                klines = await self.get_recent_klines(pair, '1m', 100)
                df = pd.DataFrame(klines)
                
                # Calcular indicadores
                rsi = self.calculate_rsi(df['close'], 14)
                bb_upper, bb_lower = self.calculate_bollinger_bands(df['close'], 20, 2)
                ema_9 = df['close'].ewm(span=9).mean()
                ema_21 = df['close'].ewm(span=21).mean()
                volume_avg = df['volume'].rolling(20).mean()
                
                current_price = df['close'].iloc[-1]
                current_rsi = rsi.iloc[-1]
                current_volume = df['volume'].iloc[-1]
                volume_spike = current_volume > (volume_avg.iloc[-1] * 1.5)
                
                # Condiciones de entrada LONG
                if (current_rsi < 25 and 
                    current_price <= bb_lower.iloc[-1] and 
                    volume_spike and
                    ema_9.iloc[-1] > ema_9.iloc[-2] and  # EMA9 trending up
                    len([pos for pos in self.active_positions.values() 
                         if pos['strategy'] == 'scalping_auto']) < config['max_positions']):
                    
                    # Calcular position size usando tu método actual
                    position_size = self.calculate_position_size(
                        capital_pct=config['capital_pct'],
                        risk_pct=config['risk_per_trade'],
                        entry_price=current_price,
                        stop_loss_price=current_price * (1 - 0.015)  # 1.5% stop
                    )
                    
                    signal = TradeSignal(
                        pair=pair,
                        direction='LONG',
                        entry_price=current_price,
                        stop_loss=current_price * (1 - 0.015),  # 1.5% stop
                        take_profit=[
                            current_price * (1 + 0.008),  # 0.8% TP1
                            current_price * (1 + 0.012),  # 1.2% TP2
                            current_price * (1 + 0.018)   # 1.8% TP3
                        ],
                        position_size=position_size,
                        strategy='scalping_auto',
                        confidence=self.calculate_signal_confidence(current_rsi, volume_spike, ema_9, ema_21),
                        timestamp=datetime.now()
                    )
                    
                    signals.append(signal)
                    self.logger.info(f"📊 Scalping LONG signal: {pair} @ {current_price}")
                
                # Condiciones de entrada SHORT (similar lógica)
                elif (current_rsi > 75 and 
                      current_price >= bb_upper.iloc[-1] and 
                      volume_spike and
                      ema_9.iloc[-1] < ema_9.iloc[-2]):  # EMA9 trending down
                    
                    position_size = self.calculate_position_size(
                        capital_pct=config['capital_pct'],
                        risk_pct=config['risk_per_trade'],
                        entry_price=current_price,
                        stop_loss_price=current_price * (1 + 0.015)  # 1.5% stop
                    )
                    
                    signal = TradeSignal(
                        pair=pair,
                        direction='SHORT',
                        entry_price=current_price,
                        stop_loss=current_price * (1 + 0.015),
                        take_profit=[
                            current_price * (1 - 0.008),
                            current_price * (1 - 0.012),
                            current_price * (1 - 0.018)
                        ],
                        position_size=position_size,
                        strategy='scalping_auto',
                        confidence=self.calculate_signal_confidence(current_rsi, volume_spike, ema_9, ema_21),
                        timestamp=datetime.now()
                    )
                    
                    signals.append(signal)
                    self.logger.info(f"📊 Scalping SHORT signal: {pair} @ {current_price}")
                    
            except Exception as e:
                self.logger.error(f"❌ Error in scalping strategy for {pair}: {e}")
                
        return signals
    
    # ESTRATEGIA 2: MEAN REVERSION
    async def strategy_mean_reversion(self) -> List[TradeSignal]:
        """
        Estrategia de reversión a la media
        """
        signals = []
        config = self.strategy_config['mean_reversion']
        
        if not config['enabled']:
            return signals
        
        # Seleccionar pares automáticamente por volumen si está configurado
        pairs = await self.auto_select_high_volume_pairs() if config['pairs'] == 'auto_select' else config['pairs']
        
        for pair in pairs[:10]:  # Máximo 10 pares para no sobrecargar
            try:
                # Obtener datos históricos más largos para mean reversion
                klines = await self.get_recent_klines(pair, '15m', 200)
                df = pd.DataFrame(klines)
                
                # Calcular media móvil y desviación estándar
                sma_100 = df['close'].rolling(100).mean()
                std_100 = df['close'].rolling(100).std()
                
                current_price = df['close'].iloc[-1]
                current_mean = sma_100.iloc[-1]
                current_std = std_100.iloc[-1]
                
                # Calcular Z-Score
                z_score = (current_price - current_mean) / current_std
                
                # RSI para confirmación
                rsi = self.calculate_rsi(df['close'], 14)
                current_rsi = rsi.iloc[-1]
                
                # Señal LONG (oversold extreme)
                if (z_score < -2.0 and 
                    current_rsi < 30 and
                    df['volume'].iloc[-1] > df['volume'].rolling(20).mean().iloc[-1]):
                    
                    position_size = self.calculate_position_size(
                        capital_pct=config['capital_pct'],
                        risk_pct=config['risk_per_trade'],
                        entry_price=current_price,
                        stop_loss_price=current_price * (1 - 0.025)
                    )
                    
                    signal = TradeSignal(
                        pair=pair,
                        direction='LONG',
                        entry_price=current_price,
                        stop_loss=current_price * (1 - 0.025),  # 2.5% stop
                        take_profit=[current_mean],  # Target: volver a la media
                        position_size=position_size,
                        strategy='mean_reversion',
                        confidence=min(abs(z_score) / 2.0, 1.0),  # Confidence based on Z-score
                        timestamp=datetime.now()
                    )
                    
                    signals.append(signal)
                    self.logger.info(f"📈 Mean Reversion LONG: {pair} (Z-Score: {z_score:.2f})")
                
                # Señal SHORT (overbought extreme)
                elif (z_score > 2.0 and 
                      current_rsi > 70 and
                      df['volume'].iloc[-1] > df['volume'].rolling(20).mean().iloc[-1]):
                    
                    position_size = self.calculate_position_size(
                        capital_pct=config['capital_pct'],
                        risk_pct=config['risk_per_trade'],
                        entry_price=current_price,
                        stop_loss_price=current_price * (1 + 0.025)
                    )
                    
                    signal = TradeSignal(
                        pair=pair,
                        direction='SHORT',
                        entry_price=current_price,
                        stop_loss=current_price * (1 + 0.025),
                        take_profit=[current_mean],
                        position_size=position_size,
                        strategy='mean_reversion',
                        confidence=min(abs(z_score) / 2.0, 1.0),
                        timestamp=datetime.now()
                    )
                    
                    signals.append(signal)
                    self.logger.info(f"📉 Mean Reversion SHORT: {pair} (Z-Score: {z_score:.2f})")
                    
            except Exception as e:
                self.logger.error(f"❌ Error in mean reversion for {pair}: {e}")
        
        return signals
    
    # ESTRATEGIA 3: BREAKOUT MOMENTUM
    async def strategy_breakout_momentum(self) -> List[TradeSignal]:
        """
        Estrategia de breakout y momentum
        """
        signals = []
        config = self.strategy_config['breakout_momentum']
        
        if not config['enabled']:
            return signals
        
        # Obtener pares con alta volatilidad
        high_vol_pairs = await self.get_high_volatility_pairs()
        
        for pair in high_vol_pairs[:5]:
            try:
                klines = await self.get_recent_klines(pair, '15m', 100)
                df = pd.DataFrame(klines)
                
                # Detectar consolidaciones
                high_20 = df['high'].rolling(20).max()
                low_20 = df['low'].rolling(20).min()
                consolidation_range = (high_20 - low_20) / df['close']
                
                current_range = consolidation_range.iloc[-1]
                avg_volume = df['volume'].rolling(20).mean()
                current_volume = df['volume'].iloc[-1]
                
                # Condiciones de consolidación
                is_consolidating = (current_range < 0.03 and  # Rango < 3%
                                  df['volume'].iloc[-10:].mean() < avg_volume.iloc[-20])
                
                if is_consolidating:
                    # Detectar breakout
                    current_price = df['close'].iloc[-1]
                    resistance = high_20.iloc[-1]
                    support = low_20.iloc[-1]
                    
                    volume_spike = current_volume > (avg_volume.iloc[-1] * 2.0)
                    
                    # Breakout alcista
                    if (current_price > resistance and 
                        volume_spike and
                        df['close'].iloc[-1] > df['close'].iloc[-2]):
                        
                        position_size = self.calculate_position_size(
                            capital_pct=config['capital_pct'],
                            risk_pct=config['risk_per_trade'],
                            entry_price=current_price,
                            stop_loss_price=support
                        )
                        
                        # Target basado en el rango de consolidación
                        target_distance = resistance - support
                        target_price = current_price + (target_distance * 2)  # 2:1 R:R
                        
                        signal = TradeSignal(
                            pair=pair,
                            direction='LONG',
                            entry_price=current_price,
                            stop_loss=support,
                            take_profit=[target_price],
                            position_size=position_size,
                            strategy='breakout_momentum',
                            confidence=0.8,  # Breakouts con volumen tienen alta confianza
                            timestamp=datetime.now()
                        )
                        
                        signals.append(signal)
                        self.logger.info(f"🚀 Breakout LONG: {pair} @ {current_price}")
                    
                    # Breakout bajista
                    elif (current_price < support and 
                          volume_spike and
                          df['close'].iloc[-1] < df['close'].iloc[-2]):
                        
                        position_size = self.calculate_position_size(
                            capital_pct=config['capital_pct'],
                            risk_pct=config['risk_per_trade'],
                            entry_price=current_price,
                            stop_loss_price=resistance
                        )
                        
                        target_distance = resistance - support
                        target_price = current_price - (target_distance * 2)
                        
                        signal = TradeSignal(
                            pair=pair,
                            direction='SHORT',
                            entry_price=current_price,
                            stop_loss=resistance,
                            take_profit=[target_price],
                            position_size=position_size,
                            strategy='breakout_momentum',
                            confidence=0.8,
                            timestamp=datetime.now()
                        )
                        
                        signals.append(signal)
                        self.logger.info(f"🚀 Breakout SHORT: {pair} @ {current_price}")
                        
            except Exception as e:
                self.logger.error(f"❌ Error in breakout strategy for {pair}: {e}")
        
        return signals
    
    # FUNCIÓN DE INTEGRACIÓN PRINCIPAL
    async def get_all_autonomous_signals(self) -> List[TradeSignal]:
        """
        Función principal que combina todas las estrategias
        Esta es la función que tu bot debería llamar periódicamente
        """
        all_signals = []
        
        try:
            # Ejecutar todas las estrategias en paralelo
            strategies = await asyncio.gather(
                self.strategy_scalping_auto(),
                self.strategy_mean_reversion(),
                self.strategy_breakout_momentum(),
                # self.strategy_arbitrage_temporal(),  # Implementar si necesario
                # self.strategy_volatility_trading(),  # Implementar si necesario
                return_exceptions=True
            )
            
            # Combinar todas las señales
            for strategy_signals in strategies:
                if isinstance(strategy_signals, list):
                    all_signals.extend(strategy_signals)
                else:
                    self.logger.error(f"❌ Error in strategy: {strategy_signals}")
            
            # Filtrar señales por calidad y riesgo
            filtered_signals = self.filter_signals_by_risk(all_signals)
            
            # Rankear por confianza
            ranked_signals = sorted(filtered_signals, 
                                  key=lambda x: x.confidence, 
                                  reverse=True)
            
            return ranked_signals[:5]  # Máximo 5 señales por ciclo
            
        except Exception as e:
            self.logger.error(f"❌ Error getting autonomous signals: {e}")
            return []
    
    # FUNCIONES DE UTILIDAD (Adaptar a tu bot)
    def calculate_position_size(self, capital_pct: float, risk_pct: float, 
                              entry_price: float, stop_loss_price: float) -> float:
        """
        Calcula el tamaño de posición basado en riesgo
        Adaptar según tu implementación actual
        """
        available_capital = self.capital_inicial * capital_pct
        risk_amount = available_capital * risk_pct
        price_diff = abs(entry_price - stop_loss_price)
        
        if price_diff == 0:
            return 0
        
        position_size = risk_amount / price_diff
        return position_size
    
    def filter_signals_by_risk(self, signals: List[TradeSignal]) -> List[TradeSignal]:
        """
        Filtra señales basándose en gestión de riesgo
        """
        filtered = []
        total_exposure = 0
        
        for signal in signals:
            # Calcular exposición de la señal
            signal_exposure = signal.position_size * signal.entry_price
            
            # No exceder 10% del capital total en exposición simultánea
            if total_exposure + signal_exposure <= self.capital_inicial * 0.1:
                filtered.append(signal)
                total_exposure += signal_exposure
            
        return filtered
    
    def calculate_signal_confidence(self, rsi: float, volume_spike: bool, 
                                  ema_short: pd.Series, ema_long: pd.Series) -> float:
        """
        Calcula confianza de la señal basada en múltiples factores
        """
        confidence = 0.5  # Base confidence
        
        # RSI extremo aumenta confianza
        if rsi < 20 or rsi > 80:
            confidence += 0.2
        elif rsi < 30 or rsi > 70:
            confidence += 0.1
        
        # Volume spike aumenta confianza
        if volume_spike:
            confidence += 0.2
        
        # EMA alignment
        if abs(ema_short.iloc[-1] - ema_long.iloc[-1]) / ema_long.iloc[-1] > 0.001:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    # FUNCIONES A IMPLEMENTAR (usando tu infraestructura actual)
    async def get_recent_klines(self, pair: str, timeframe: str, limit: int):
        """
        Obtener datos de velas recientes usando el adaptador Binance
        """
        try:
            from strategies.binance_adapter import binance_adapter
            return await binance_adapter.get_recent_klines(pair, timeframe, limit)
        except Exception as e:
            self.logger.error(f"Error obteniendo klines para {pair}: {e}")
            return []
    
    async def auto_select_high_volume_pairs(self) -> List[str]:
        """
        Seleccionar automáticamente pares con mayor volumen
        """
        try:
            from strategies.binance_adapter import binance_adapter
            pairs = await binance_adapter.get_high_volume_pairs(15)
            # Filtrar solo los pares configurados si existen
            if hasattr(self, 'bot_config') and 'pares_favoritos' in self.bot_config:
                preferred_pairs = self.bot_config['pares_favoritos']
                # Priorizar pares preferidos que también tengan alto volumen
                filtered_pairs = [p for p in pairs if p in preferred_pairs]
                # Si no hay suficientes, completar con alto volumen
                if len(filtered_pairs) < 5:
                    for pair in pairs:
                        if pair not in filtered_pairs and len(filtered_pairs) < 10:
                            filtered_pairs.append(pair)
                return filtered_pairs[:10]
            return pairs[:10]
        except Exception as e:
            self.logger.error(f"Error seleccionando pares de alto volumen: {e}")
            return ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
    
    async def get_high_volatility_pairs(self) -> List[str]:
        """
        Obtener pares con alta volatilidad
        """
        try:
            from strategies.binance_adapter import binance_adapter
            return await binance_adapter.get_high_volatility_pairs(8)
        except Exception as e:
            self.logger.error(f"Error obteniendo pares volátiles: {e}")
            return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT']
    
    async def verify_binance_connection(self):
        """
        Verificar conexión con Binance
        """
        try:
            from strategies.binance_adapter import binance_adapter
            # Probar obtener precio de BTC como test
            price = await binance_adapter.get_current_price('BTCUSDT')
            if price > 0:
                self.logger.info(f"✅ Conexión Binance verificada - BTC: ${price:,.2f}")
                return True
            else:
                self.logger.error("❌ Error verificando conexión Binance")
                return False
        except Exception as e:
            self.logger.error(f"❌ Error en verificación Binance: {e}")
            return False
    
    async def load_historical_data(self):
        """
        Cargar datos históricos necesarios para indicadores
        """
        self.logger.info("📊 Cargando datos históricos para indicadores...")
        # Aquí podrías pre-cargar datos si es necesario
        pass
    
    async def setup_realtime_indicators(self):
        """
        Configurar indicadores en tiempo real
        """
        self.logger.info("📈 Configurando indicadores en tiempo real...")
        # Configurar cualquier indicador que necesite inicialización
        pass
    
    # FUNCIONES DE INDICADORES TÉCNICOS
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calcular RSI de forma simple y robusta
        """
        try:
            # Convertir a array numpy para evitar problemas de tipos
            import numpy as np
            
            price_array = np.array(prices, dtype=float)
            deltas = np.diff(price_array)
            
            # Calcular ganancias y pérdidas
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            # Calcular medias móviles usando pandas
            gains_series = pd.Series(gains)
            losses_series = pd.Series(losses)
            
            avg_gains = gains_series.rolling(window=period).mean()
            avg_losses = losses_series.rolling(window=period).mean()
            
            # Calcular RS y RSI
            rs = avg_gains / (avg_losses + 1e-10)  # Evitar división por cero
            rsi = 100 - (100 / (1 + rs))
            
            # Agregar un valor NaN al inicio para compensar el diff
            rsi_with_nan = pd.Series([np.nan] + list(rsi), index=prices.index)
            
            return rsi_with_nan
            
        except Exception as e:
            # Fallback: devolver RSI neutro (50)
            return pd.Series([50.0] * len(prices), index=prices.index)
    
    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series]:
        """
        Calcular Bollinger Bands
        """
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return upper_band, lower_band

# INTEGRACIÓN CON TU BOT ACTUAL
def integrate_with_existing_bot():
    """
    Ejemplo de como integrar este módulo con tu bot actual
    """
    
    # Configuración (adaptar a tu config actual)
    config = {
        'binance_api_key': 'tu_api_key',
        'binance_secret': 'tu_secret',
        'capital_inicial': 10000,
        # ... resto de tu configuración
    }
    
    # Inicializar módulo autónomo
    autonomous_module = AutonomousStrategiesModule(
        capital_inicial=config['capital_inicial'],
        existing_bot_config=config
    )
    
    return autonomous_module

# FUNCIÓN PRINCIPAL PARA TU BOT
async def run_autonomous_strategies_cycle():
    """
    Ciclo principal que tu bot debería ejecutar cada minuto
    """
    
    # Inicializar módulo
    autonomous = integrate_with_existing_bot()
    await autonomous.initialize()
    
    # Obtener señales de todas las estrategias
    signals = await autonomous.get_all_autonomous_signals()
    
    # Procesar señales (integrar con tu sistema de ejecución)
    for signal in signals:
        print(f"🎯 Nueva señal: {signal.strategy} - {signal.pair} {signal.direction} @ {signal.entry_price}")
        
        # Aquí ejecutarías usando tu sistema actual de trades
        # await tu_execute_trade(signal)
    
    return signals

if __name__ == "__main__":
    # Test del módulo
    print("🤖 Testeando Módulo de Estrategias Autónomas")
    
    # Ejecutar ciclo de prueba
    # asyncio.run(run_autonomous_strategies_cycle())
