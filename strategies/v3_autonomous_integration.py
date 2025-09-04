#!/usr/bin/env python3
"""
INTEGRACIÓN AUTÓNOMA V3
======================
Módulo para integrar las estrategias V3 optimizadas con el sistema de trading autónomo existente.

Este módulo:
- Utiliza las configuraciones optimizadas probadas en V3
- Se integra con el execution_worker.py y order_executor.py existentes
- Proporciona análisis continuo y autónomo de mercado
- Genera decisiones de trading para la cola de mensajes

Configuraciones probadas con mejores resultados:
- Scalping SOL/USDT 30m: 14.15% mensual
- Híbrido SOL/USDT 15m: 13.47% mensual  
- Híbrido BTC/USDT 1h: 11.23% mensual
"""

import ccxt
import pandas as pd
import numpy as np
import ta
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
import warnings
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import settings
from utils.message_queue import mq
from utils.structured_logger import StructuredLogger

warnings.filterwarnings('ignore')
logger = StructuredLogger(__name__)

@dataclass
class TradingSignal:
    """Señal de trading generada por V3"""
    symbol: str
    type: str  # 'BUY', 'SELL', 'HOLD'
    side: str
    quantity: float
    strategy_id: str
    timestamp_decision: str
    analysis_score: float
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    features: Dict = None
    reason: str = ""
    model_version: str = "V3_AUTONOMOUS"

class V3AutonomousSystem:
    """Sistema V3 Autónomo integrado con la infraestructura existente"""
    
    def __init__(self):
        """Inicializar sistema V3 autónomo"""
        self.exchange = ccxt.binance({
            'apiKey': getattr(settings, 'BINANCE_API_KEY', ''),
            'secret': getattr(settings, 'BINANCE_SECRET_KEY', ''),
            'sandbox': False,
            'enableRateLimit': True,
        })
        
        # Configuraciones optimizadas basadas en resultados de pruebas
        self.proven_strategies = {
            'scalping_sol_30m': {
                'name': 'Scalping_SOL_30m_Ultimate',
                'symbol': 'SOL/USDT',
                'timeframe': '30m',
                'rsi_oversold': 20, 'rsi_overbought': 80,
                'bb_std': 2.0, 'volume_threshold': 1.0,
                'risk_per_trade': 0.02, 'max_trades': 100,
                'atr_multiplier_sl': 1.5, 'atr_multiplier_tp': 3.0,
                'priority': 1,  # Máxima prioridad (14.15% mensual)
                'proven_return': 14.15
            },
            'hybrid_sol_15m': {
                'name': 'Híbrido_SOL_15m_Ultimate', 
                'symbol': 'SOL/USDT',
                'timeframe': '15m',
                'rsi_oversold': 22, 'rsi_overbought': 78,
                'bb_std': 2.2, 'volume_threshold': 1.1,
                'risk_per_trade': 0.03, 'max_trades': 75,
                'atr_multiplier_sl': 1.8, 'atr_multiplier_tp': 3.5,
                'priority': 2,  # Segunda prioridad (13.47% mensual)
                'proven_return': 13.47
            },
            'hybrid_btc_1h': {
                'name': 'Híbrido_BTC_1h_Ultimate',
                'symbol': 'BTC/USDT', 
                'timeframe': '1h',
                'rsi_oversold': 22, 'rsi_overbought': 78,
                'bb_std': 2.2, 'volume_threshold': 1.1,
                'risk_per_trade': 0.025, 'max_trades': 50,
                'atr_multiplier_sl': 2.0, 'atr_multiplier_tp': 4.0,
                'priority': 3,  # Tercera prioridad (11.23% mensual)
                'proven_return': 11.23
            }
        }
        
        # Estado del sistema
        self.is_running = False
        self.last_analysis = {}
        self.analysis_intervals = {
            '15m': 15 * 60,  # 15 minutos
            '30m': 30 * 60,  # 30 minutos
            '1h': 60 * 60    # 1 hora
        }
    
    async def fetch_market_data(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Obtener datos de mercado de forma asíncrona"""
        try:
            # Ejecutar fetch_ohlcv en un hilo para no bloquear
            ohlcv = await asyncio.to_thread(
                self.exchange.fetch_ohlcv,
                symbol, timeframe, limit=limit
            )
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('timestamp')
            
            logger.info(
                "MARKET_DATA_FETCHED",
                f"Datos obtenidos para {symbol} {timeframe}: {len(df)} velas",
                details={"symbol": symbol, "timeframe": timeframe, "rows": len(df)}
            )
            
            return df
            
        except Exception as e:
            logger.error(
                "MARKET_DATA_ERROR", 
                f"Error obteniendo datos de {symbol} {timeframe}: {e}",
                details={"symbol": symbol, "timeframe": timeframe},
                exc_info=True
            )
            return pd.DataFrame()
    
    def calculate_v3_indicators(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        """Calcular indicadores V3 optimizados"""
        if len(df) < 50:
            return df
            
        try:
            # RSI optimizado
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            
            # Bandas de Bollinger dinámicas
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=config['bb_std'])
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_middle'] = bb.bollinger_mavg()
            df['bb_lower'] = bb.bollinger_lband()
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle'] * 100
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            
            # MACD refinado
            macd = ta.trend.MACD(df['close'], window_slow=26, window_fast=12, window_sign=9)
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['macd_histogram'] = macd.macd_diff()
            
            # EMAs múltiples
            df['ema_9'] = ta.trend.EMAIndicator(df['close'], window=9).ema_indicator()
            df['ema_21'] = ta.trend.EMAIndicator(df['close'], window=21).ema_indicator()
            df['ema_50'] = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator()
            df['ema_200'] = ta.trend.EMAIndicator(df['close'], window=200).ema_indicator()
            
            # ATR para stop-loss dinámico
            df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()
            
            # Stochastic optimizado
            stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'], window=14, smooth_window=3)
            df['stoch_k'] = stoch.stoch()
            df['stoch_d'] = stoch.stoch_signal()
            
            # Volume analysis
            df['volume_sma'] = ta.volume.VolumeSMAIndicator(df['close'], df['volume'], window=20).volume_sma()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # Momentum adicional
            df['williams_r'] = ta.momentum.WilliamsRIndicator(df['high'], df['low'], df['close'], lbp=14).williams_r()
            df['cci'] = ta.trend.CCIIndicator(df['high'], df['low'], df['close'], window=20).cci()
            
            return df
            
        except Exception as e:
            logger.error("INDICATORS_ERROR", f"Error calculando indicadores: {e}", exc_info=True)
            return df
    
    def generate_v3_ultimate_signal(self, df: pd.DataFrame, config: Dict) -> Tuple[str, float, str]:
        """Generar señal V3 Ultimate con 12 condiciones optimizadas"""
        if len(df) < 2:
            return 'HOLD', 0.0, 'Datos insuficientes'
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Condiciones de entrada LONG optimizadas
        long_conditions = []
        long_reasons = []
        
        # 1. RSI en sobreventa
        if current['rsi'] < config['rsi_oversold']:
            long_conditions.append(True)
            long_reasons.append(f"RSI_oversold({current['rsi']:.1f})")
        else:
            long_conditions.append(False)
        
        # 2. Precio cerca de Bollinger inferior
        if current['bb_position'] < 0.2:
            long_conditions.append(True)
            long_reasons.append(f"BB_lower({current['bb_position']:.2f})")
        else:
            long_conditions.append(False)
        
        # 3. MACD momentum positivo
        if current['macd_histogram'] > prev['macd_histogram']:
            long_conditions.append(True) 
            long_reasons.append("MACD_momentum_up")
        else:
            long_conditions.append(False)
        
        # 4. EMA trend alignment
        if current['ema_9'] > current['ema_21']:
            long_conditions.append(True)
            long_reasons.append("EMA_trend_up")
        else:
            long_conditions.append(False)
        
        # 5. Stochastic en zona de sobreventa
        if current['stoch_k'] < 20:
            long_conditions.append(True)
            long_reasons.append(f"Stoch_oversold({current['stoch_k']:.1f})")
        else:
            long_conditions.append(False)
        
        # 6. Volume confirmation
        if current['volume_ratio'] > config['volume_threshold']:
            long_conditions.append(True)
            long_reasons.append(f"Volume_high({current['volume_ratio']:.1f})")
        else:
            long_conditions.append(False)
        
        # Condiciones SHORT simétricas
        short_conditions = []
        short_reasons = []
        
        # 7. RSI en sobrecompra
        if current['rsi'] > config['rsi_overbought']:
            short_conditions.append(True)
            short_reasons.append(f"RSI_overbought({current['rsi']:.1f})")
        else:
            short_conditions.append(False)
        
        # 8. Precio cerca de Bollinger superior
        if current['bb_position'] > 0.8:
            short_conditions.append(True)
            short_reasons.append(f"BB_upper({current['bb_position']:.2f})")
        else:
            short_conditions.append(False)
        
        # 9. MACD momentum negativo
        if current['macd_histogram'] < prev['macd_histogram']:
            short_conditions.append(True)
            short_reasons.append("MACD_momentum_down")
        else:
            short_conditions.append(False)
        
        # 10. EMA trend down
        if current['ema_9'] < current['ema_21']:
            short_conditions.append(True)
            short_reasons.append("EMA_trend_down")
        else:
            short_conditions.append(False)
        
        # 11. Stochastic en sobrecompra
        if current['stoch_k'] > 80:
            short_conditions.append(True)
            short_reasons.append(f"Stoch_overbought({current['stoch_k']:.1f})")
        else:
            short_conditions.append(False)
        
        # 12. Volume confirmation
        if current['volume_ratio'] > config['volume_threshold']:
            short_conditions.append(True)
            short_reasons.append(f"Volume_high({current['volume_ratio']:.1f})")
        else:
            short_conditions.append(False)
        
        # Evaluar señales
        long_score = sum(long_conditions) / len(long_conditions)
        short_score = sum(short_conditions) / len(short_conditions)
        
        # Thresholds dinámicos según configuración
        min_conditions_pct = 0.5  # Mínimo 50% de condiciones
        
        if long_score >= min_conditions_pct and long_score > short_score:
            active_reasons = [reason for condition, reason in zip(long_conditions, long_reasons) if condition]
            return 'BUY', long_score, f"LONG: {', '.join(active_reasons)}"
        
        elif short_score >= min_conditions_pct and short_score > long_score:
            active_reasons = [reason for condition, reason in zip(short_conditions, short_reasons) if condition]
            return 'SELL', short_score, f"SHORT: {', '.join(active_reasons)}"
        
        else:
            return 'HOLD', max(long_score, short_score), f"Condiciones insuficientes (L:{long_score:.2f}, S:{short_score:.2f})"
    
    async def analyze_strategy(self, strategy_key: str, config: Dict) -> Optional[TradingSignal]:
        """Analizar una estrategia específica"""
        try:
            symbol = config['symbol']
            timeframe = config['timeframe']
            
            # Obtener datos de mercado
            df = await self.fetch_market_data(symbol, timeframe, limit=200)
            if df.empty:
                return None
            
            # Calcular indicadores
            df_with_indicators = self.calculate_v3_indicators(df, config)
            if df_with_indicators.empty:
                return None
            
            # Generar señal
            signal_type, score, reason = self.generate_v3_ultimate_signal(df_with_indicators, config)
            
            if signal_type == 'HOLD':
                logger.debug(
                    "NO_SIGNAL_GENERATED",
                    f"No hay señal para {strategy_key}: {reason}",
                    details={"strategy": strategy_key, "score": score}
                )
                return None
            
            # Calcular stop-loss y take-profit dinámicos
            current_price = df_with_indicators.iloc[-1]['close']
            atr = df_with_indicators.iloc[-1]['atr']
            
            if signal_type == 'BUY':
                stop_loss_pct = (atr * config['atr_multiplier_sl'] / current_price) * 100
                take_profit_pct = (atr * config['atr_multiplier_tp'] / current_price) * 100
            else:  # SELL
                stop_loss_pct = (atr * config['atr_multiplier_sl'] / current_price) * 100
                take_profit_pct = (atr * config['atr_multiplier_tp'] / current_price) * 100
            
            # Crear features para auditoría
            features = {
                'rsi': float(df_with_indicators.iloc[-1]['rsi']),
                'bb_position': float(df_with_indicators.iloc[-1]['bb_position']),
                'macd_histogram': float(df_with_indicators.iloc[-1]['macd_histogram']),
                'volume_ratio': float(df_with_indicators.iloc[-1]['volume_ratio']),
                'atr': float(atr),
                'price': float(current_price)
            }
            
            # Crear señal de trading
            signal = TradingSignal(
                symbol=symbol.replace('/', ''),  # SOLUSDT formato
                type='TRADE',
                side=signal_type,
                quantity=config['risk_per_trade'],  # Porcentaje del balance
                strategy_id=config['name'],
                timestamp_decision=datetime.now().isoformat(),
                analysis_score=score,
                take_profit=take_profit_pct,
                stop_loss=stop_loss_pct,
                features=features,
                reason=reason,
                model_version=f"V3_AUTONOMOUS_{strategy_key.upper()}"
            )
            
            logger.info(
                "SIGNAL_GENERATED",
                f"Señal {signal_type} generada para {symbol} ({strategy_key}): score {score:.2f}",
                details={
                    "strategy": strategy_key,
                    "signal": signal_type,
                    "score": score,
                    "reason": reason,
                    "symbol": symbol
                }
            )
            
            return signal
            
        except Exception as e:
            logger.error(
                "STRATEGY_ANALYSIS_ERROR",
                f"Error analizando estrategia {strategy_key}: {e}",
                details={"strategy": strategy_key},
                exc_info=True
            )
            return None
    
    async def run_analysis_cycle(self) -> None:
        """Ejecutar un ciclo de análisis de todas las estrategias"""
        logger.info("ANALYSIS_CYCLE_START", "Iniciando ciclo de análisis V3")
        
        signals_generated = 0
        
        # Analizar estrategias por prioridad
        sorted_strategies = sorted(
            self.proven_strategies.items(),
            key=lambda x: x[1]['priority']
        )
        
        for strategy_key, config in sorted_strategies:
            try:
                signal = await self.analyze_strategy(strategy_key, config)
                
                if signal:
                    # Enviar señal a la cola de mensajes
                    decision_data = {
                        'type': signal.type,
                        'symbol': signal.symbol,
                        'side': signal.side,
                        'quantity': signal.quantity,
                        'strategy_id': signal.strategy_id,
                        'timestamp_decision': signal.timestamp_decision,
                        'analysis_score': signal.analysis_score,
                        'take_profit': signal.take_profit,
                        'stop_loss': signal.stop_loss,
                        'features': signal.features,
                        'reason': signal.reason,
                        'model_version': signal.model_version
                    }
                    
                    # Enviar a cola de mensajes (será procesado por execution_worker.py)
                    mq.send_decision(decision_data)
                    signals_generated += 1
                    
                    logger.info(
                        "SIGNAL_SENT_TO_QUEUE",
                        f"Señal enviada a cola: {signal.side} {signal.symbol}",
                        details=decision_data
                    )
                
                # Pausa entre análisis para rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(
                    "STRATEGY_CYCLE_ERROR",
                    f"Error en ciclo de estrategia {strategy_key}: {e}",
                    details={"strategy": strategy_key},
                    exc_info=True
                )
                continue
        
        logger.info(
            "ANALYSIS_CYCLE_COMPLETE",
            f"Ciclo de análisis completado. Señales generadas: {signals_generated}",
            details={"signals_count": signals_generated}
        )
    
    async def run_autonomous_system(self) -> None:
        """Ejecutar sistema autónomo V3"""
        logger.info(
            "V3_AUTONOMOUS_START",
            "Sistema V3 Autónomo iniciado con estrategias probadas",
            details={
                "strategies_count": len(self.proven_strategies),
                "strategies": list(self.proven_strategies.keys())
            }
        )
        
        self.is_running = True
        
        while self.is_running:
            try:
                # Ejecutar ciclo de análisis
                await self.run_analysis_cycle()
                
                # Determinar próximo intervalo (usar el menor para máxima responsividad)
                min_interval = min(self.analysis_intervals.values())
                
                logger.info(
                    "AUTONOMOUS_SLEEP",
                    f"Esperando {min_interval/60:.1f} minutos hasta próximo análisis",
                    details={"sleep_seconds": min_interval}
                )
                
                # Dormir hasta próximo análisis
                await asyncio.sleep(min_interval)
                
            except Exception as e:
                logger.error(
                    "AUTONOMOUS_SYSTEM_ERROR",
                    f"Error en sistema autónomo: {e}",
                    exc_info=True
                )
                # Esperar antes de reintentar
                await asyncio.sleep(300)  # 5 minutos de espera en caso de error\n    \n    def stop_autonomous_system(self) -> None:\n        \"\"\"Detener sistema autónomo\"\"\"\n        self.is_running = False\n        logger.info(\"V3_AUTONOMOUS_STOP\", \"Sistema V3 Autónomo detenido\")\n\n\n# Instancia global del sistema V3\nv3_autonomous = V3AutonomousSystem()\n\n\ndef start_v3_autonomous_system() -> None:\n    \"\"\"Iniciar sistema V3 autónomo en un nuevo loop de eventos\"\"\"\n    try:\n        asyncio.run(v3_autonomous.run_autonomous_system())\n    except KeyboardInterrupt:\n        logger.info(\"V3_AUTONOMOUS_INTERRUPTED\", \"Sistema V3 interrumpido por usuario\")\n    except Exception as e:\n        logger.error(\"V3_AUTONOMOUS_FATAL\", f\"Error fatal en sistema V3: {e}\", exc_info=True)\n\n\nif __name__ == \"__main__\":\n    print(\"🚀 SISTEMA V3 AUTÓNOMO - INTEGRACIÓN COMPLETA\")\n    print(\"=\" * 60)\n    print(\"Estrategias optimizadas probadas:\")\n    for key, config in v3_autonomous.proven_strategies.items():\n        print(f\"✅ {config['name']}: {config['proven_return']:.2f}% mensual\")\n    print(\"\\nIniciando sistema autónomo...\")\n    \n    start_v3_autonomous_system()\n
