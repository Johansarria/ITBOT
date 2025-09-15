#!/usr/bin/env python3
"""
Estrategia de scalping agresivo para mercados laterales
Diseñada específicamente para generar 20%+ mensual en condiciones de consolidación
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
import logging

from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class ScalpingAggressiveStrategy(BaseStrategy):
    """
    Estrategia de scalping ultra-agresiva para mercados laterales
    - Múltiples entradas pequeñas
    - Take profits pequeños pero frecuentes  
    - Stop losses muy ajustados
    - Aprovecha micro-movimientos
    """
    
    def __init__(self):
        super().__init__(
            name="ScalpingAggressiveStrategy",
            description="Estrategia de scalping ultra-agresiva para mercados laterales con targets de 0.8% por trade"
        )
        
        # Parámetros de scalping
        self.bb_period = 10          # BB corto para ser responsive
        self.bb_std = 1.5           # Bandas más estrechas
        self.rsi_period = 7         # RSI muy corto
        self.rsi_overbought = 75    
        self.rsi_oversold = 25
        
        # Scalping targets - MUY PEQUEÑOS pero frecuentes
        self.take_profit_pct = 0.8  # Solo 0.8% por trade
        self.stop_loss_pct = 0.3    # Stop muy ajustado 0.3%
        
        # Parámetros de momentum micro
        self.momentum_periods = [3, 5]  # Momentum muy corto
        
        # Estado interno
        self._in_position = False
        self._entry_price = 0.0
        self._entry_index = -1
        self._stop_price = 0.0
        self._target_price = 0.0
        
        # Contadores para múltiples entradas
        self._trade_count = 0
        self._consecutive_losses = 0
        
        # Configuración de volumen
        self.min_bars_required = 25
        
    def get_parameters(self) -> Dict[str, Any]:
        """Devuelve parámetros actuales"""
        return {
            'bb_period': self.bb_period,
            'bb_std': self.bb_std,
            'rsi_period': self.rsi_period,
            'rsi_overbought': self.rsi_overbought,
            'rsi_oversold': self.rsi_oversold,
            'take_profit_pct': self.take_profit_pct,
            'stop_loss_pct': self.stop_loss_pct,
            'momentum_periods': self.momentum_periods
        }
    
    def set_parameters(self, params: Dict[str, Any]):
        """Configura parámetros"""
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Análisis de scalping ultra-agresivo"""
        if data is None or data.empty or len(data) < self.min_bars_required:
            return {"decision": "MANTENER", "score": 0.0, "regime": "insufficient_data"}

        try:
            # Datos actuales
            current = data.iloc[-1]
            close = float(current.get("close", 0))
            high = float(current.get("high", close))
            low = float(current.get("low", close))
            
            # Features necesarios
            rsi = current.get("rsi", 50)
            bb_upper = current.get("bb_upper", close * 1.02)
            bb_lower = current.get("bb_lower", close * 0.98)
            bb_middle = current.get("bb_middle", close)
            volume = current.get("volume", 0)
            
            # Momentum micro
            momentum_3 = current.get("momentum_3", 0)
            momentum_5 = current.get("momentum_5", 0)
            
            # Volatilidad reciente (últimas 10 barras)
            recent_data = data.tail(10)
            recent_high = recent_data['high'].max()
            recent_low = recent_data['low'].min()
            volatility_range = (recent_high - recent_low) / close
            
            # MANEJO DE POSICIÓN EXISTENTE
            if self._in_position:
                # Verificar condiciones de salida
                hit_target = close >= self._target_price
                hit_stop = close <= self._stop_price
                
                if hit_target:
                    # Take profit alcanzado
                    self._reset_position()
                    self._trade_count += 1
                    return {"decision": "VENDER", "score": 1.0, "regime": "scalp_profit"}
                    
                elif hit_stop:
                    # Stop loss hit
                    self._reset_position()
                    self._consecutive_losses += 1
                    return {"decision": "VENDER", "score": -0.8, "regime": "scalp_stop"}
                    
                else:
                    # Mantener posición
                    return {"decision": "MANTENER", "score": 0.3, "regime": "scalp_hold"}
            
            # LÓGICA DE ENTRADA - MÚLTIPLES OPORTUNIDADES
            
            # 1. SCALP EN BANDAS DE BOLLINGER
            near_lower = close <= bb_lower * 1.001  # Muy cerca de banda inferior
            near_upper = close >= bb_upper * 0.999  # Muy cerca de banda superior
            
            # 2. RSI OVERSOLD/OVERBOUGHT SCALP
            rsi_oversold_scalp = rsi <= self.rsi_oversold + 5  # Más permisivo
            rsi_overbought_scalp = rsi >= self.rsi_overbought - 5
            
            # 3. MOMENTUM MICRO REVERSAL
            momentum_reversal_up = momentum_3 < -0.2 and momentum_5 < -0.1  # Momentum bajista para compra
            momentum_reversal_down = momentum_3 > 0.2 and momentum_5 > 0.1  # Momentum alcista para venta
            
            # 4. VOLATILIDAD SPIKE (oportunidad de scalp)
            vol_spike = volatility_range > 0.015  # 1.5% de rango en 10 barras
            
            # 5. MEAN REVERSION SCALP
            distance_from_bb_mid = abs(close - bb_middle) / bb_middle
            far_from_middle = distance_from_bb_mid > 0.008  # Lejos del medio
            
            # SEÑALES DE COMPRA (scalp up)
            buy_signal = False
            buy_score = 0.0
            
            if near_lower and rsi_oversold_scalp:
                # Scalp clásico en oversold + banda inferior
                buy_signal = True
                buy_score = 0.9
                
            elif momentum_reversal_up and close < bb_middle:
                # Scalp en reversión de momentum 
                buy_signal = True
                buy_score = 0.8
                
            elif vol_spike and far_from_middle and close < bb_middle:
                # Scalp en spike de volatilidad
                buy_signal = True
                buy_score = 0.7
                
            elif distance_from_bb_mid > 0.012 and close < bb_lower * 1.005:
                # Scalp extremo de mean reversion
                buy_signal = True
                buy_score = 0.85
            
            # Filtros adicionales para scalping
            if buy_signal:
                # Verificar que no hay demasiadas pérdidas consecutivas
                if self._consecutive_losses >= 3:
                    buy_signal = False
                    
                # Verificar que hay suficiente volatilidad para scalp
                if volatility_range < 0.005:  # Menos de 0.5% de rango
                    buy_signal = False
            
            if buy_signal:
                # Configurar posición de scalping
                self._in_position = True
                self._entry_price = close
                self._entry_index = len(data) - 1
                
                # Targets de scalping MUY PEQUEÑOS
                self._target_price = close * (1 + self.take_profit_pct / 100)  # +0.8%
                self._stop_price = close * (1 - self.stop_loss_pct / 100)      # -0.3%
                
                # Reset consecutive losses en entrada exitosa
                self._consecutive_losses = 0
                
                return {"decision": "COMPRAR", "score": buy_score, "regime": "scalp_entry"}
            
            # Default: no action
            return {"decision": "MANTENER", "score": 0.0, "regime": "scalp_wait"}
            
        except Exception as e:
            logger.error(f"Error en ScalpingAggressiveStrategy.analyze: {e}")
            return {"decision": "MANTENER", "score": 0.0, "regime": "error"}
    
    def _reset_position(self):
        """Reset estado de posición"""
        self._in_position = False
        self._entry_price = 0.0
        self._entry_index = -1
        self._stop_price = 0.0
        self._target_price = 0.0
