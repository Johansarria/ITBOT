# /src/multi_symbol_portfolio.py
"""
Gestor de Portafolio Multi-Símbolo para SICAR
Maneja múltiples activos de trading con distribución de capital y riesgo.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import numpy as np

from config import TRADING_SYMBOLS, CAPITAL_ALLOCATION, CAPITAL_BASE, RISK_PER_TRADE

logger = logging.getLogger(__name__)

@dataclass
class SymbolPosition:
    """Representa una posición en un símbolo específico."""
    symbol: str
    size: float = 0.0
    entry_price: float = 0.0
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    allocated_capital: float = 0.0
    available_capital: float = 0.0
    
    @property
    def is_open(self) -> bool:
        """Verifica si la posición está abierta."""
        return abs(self.size) > 1e-8
    
    @property
    def market_value(self) -> float:
        """Valor de mercado actual de la posición."""
        return self.size * self.current_price
    
    @property
    def pnl_percentage(self) -> float:
        """PnL como porcentaje del capital asignado."""
        if self.allocated_capital > 0:
            return (self.unrealized_pnl / self.allocated_capital) * 100
        return 0.0

class MultiSymbolPortfolio:
    """
    Gestor de portafolio para múltiples símbolos de trading.
    
    Características:
    - Distribución de capital por símbolo
    - Gestión de riesgo independiente por activo
    - Correlación entre activos
    - Métricas agregadas del portafolio
    """
    
    def __init__(self, symbols: List[str] = None, capital_allocation: Dict[str, float] = None):
        """
        Inicializa el portafolio multi-símbolo.
        
        Args:
            symbols: Lista de símbolos a gestionar
            capital_allocation: Distribución de capital por símbolo
        """
        self.symbols = symbols or TRADING_SYMBOLS
        self.capital_allocation = capital_allocation or CAPITAL_ALLOCATION
        self.total_capital = CAPITAL_BASE
        
        # Validar que la distribución sume 1.0
        total_allocation = sum(self.capital_allocation.values())
        if abs(total_allocation - 1.0) > 0.01:
            logger.warning(f"⚠️ Distribución de capital no suma 1.0: {total_allocation}")
            # Normalizar distribución
            self.capital_allocation = {
                symbol: allocation / total_allocation 
                for symbol, allocation in self.capital_allocation.items()
            }
        
        # Inicializar posiciones
        self.positions: Dict[str, SymbolPosition] = {}
        for symbol in self.symbols:
            allocated_capital = self.total_capital * self.capital_allocation.get(symbol, 0)
            self.positions[symbol] = SymbolPosition(
                symbol=symbol,
                allocated_capital=allocated_capital,
                available_capital=allocated_capital
            )
        
        # Métricas del portafolio
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_value = self.total_capital
        
        logger.info(f"💼 Portafolio multi-símbolo inicializado:")
        for symbol, allocation in self.capital_allocation.items():
            capital = self.total_capital * allocation
            logger.info(f"   📊 {symbol}: ${capital:.2f} ({allocation*100:.1f}%)")
    
    def update_prices(self, prices: Dict[str, float]) -> None:
        """
        Actualiza los precios actuales de todos los símbolos.
        
        Args:
            prices: Diccionario con precios actuales {symbol: price}
        """
        for symbol, price in prices.items():
            if symbol in self.positions:
                position = self.positions[symbol]
                position.current_price = price
                
                # Calcular PnL no realizado
                if position.is_open:
                    if position.size > 0:  # Posición larga
                        position.unrealized_pnl = position.size * (price - position.entry_price)
                    else:  # Posición corta
                        position.unrealized_pnl = abs(position.size) * (position.entry_price - price)
        
        # Actualizar métricas del portafolio
        self._update_portfolio_metrics()
    
    def can_open_position(self, symbol: str, trade_size_usd: float) -> bool:
        """
        Verifica si se puede abrir una posición en el símbolo dado.
        
        Args:
            symbol: Símbolo a verificar
            trade_size_usd: Tamaño del trade en USD
            
        Returns:
            True si se puede abrir la posición
        """
        if symbol not in self.positions:
            return False
        
        position = self.positions[symbol]
        
        # Verificar si ya hay una posición abierta
        if position.is_open:
            logger.warning(f"⚠️ Ya existe una posición abierta en {symbol}")
            return False
        
        # Verificar capital disponible
        if trade_size_usd > position.available_capital:
            logger.warning(f"⚠️ Capital insuficiente en {symbol}: ${trade_size_usd:.2f} > ${position.available_capital:.2f}")
            return False
        
        # Verificar límite de riesgo por trade
        max_risk_usd = position.allocated_capital * RISK_PER_TRADE
        if trade_size_usd > max_risk_usd:
            logger.warning(f"⚠️ Trade excede límite de riesgo en {symbol}: ${trade_size_usd:.2f} > ${max_risk_usd:.2f}")
            return False
        
        return True
    
    def open_position(self, symbol: str, size: float, entry_price: float) -> bool:
        """
        Abre una nueva posición en el símbolo especificado.
        
        Args:
            symbol: Símbolo del activo
            size: Tamaño de la posición (positivo para long, negativo para short)
            entry_price: Precio de entrada
            
        Returns:
            True si la posición se abrió exitosamente
        """
        if symbol not in self.positions:
            logger.error(f"❌ Símbolo {symbol} no está en el portafolio")
            return False
        
        trade_size_usd = abs(size) * entry_price
        
        if not self.can_open_position(symbol, trade_size_usd):
            return False
        
        position = self.positions[symbol]
        position.size = size
        position.entry_price = entry_price
        position.current_price = entry_price
        position.available_capital -= trade_size_usd
        position.unrealized_pnl = 0.0
        
        logger.info(f"✅ Posición abierta en {symbol}: {size:.6f} @ ${entry_price:.2f}")
        return True
    
    def close_position(self, symbol: str, exit_price: float) -> Optional[float]:
        """
        Cierra la posición en el símbolo especificado.
        
        Args:
            symbol: Símbolo del activo
            exit_price: Precio de salida
            
        Returns:
            PnL realizado de la operación
        """
        if symbol not in self.positions:
            logger.error(f"❌ Símbolo {symbol} no está en el portafolio")
            return None
        
        position = self.positions[symbol]
        
        if not position.is_open:
            logger.warning(f"⚠️ No hay posición abierta en {symbol}")
            return None
        
        # Calcular PnL realizado
        if position.size > 0:  # Posición larga
            realized_pnl = position.size * (exit_price - position.entry_price)
        else:  # Posición corta
            realized_pnl = abs(position.size) * (position.entry_price - exit_price)
        
        # Actualizar capital disponible
        trade_value = abs(position.size) * exit_price
        position.available_capital += trade_value + realized_pnl
        
        # Resetear posición
        position.size = 0.0
        position.entry_price = 0.0
        position.unrealized_pnl = 0.0
        
        # Actualizar PnL total
        self.total_pnl += realized_pnl
        
        logger.info(f"✅ Posición cerrada en {symbol} @ ${exit_price:.2f} | PnL: ${realized_pnl:.2f}")
        return realized_pnl
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Obtiene un resumen completo del portafolio.
        
        Returns:
            Diccionario con métricas del portafolio
        """
        total_value = 0.0
        total_unrealized_pnl = 0.0
        open_positions = 0
        
        positions_summary = {}
        
        for symbol, position in self.positions.items():
            position_value = position.available_capital
            if position.is_open:
                position_value += position.market_value
                total_unrealized_pnl += position.unrealized_pnl
                open_positions += 1
            
            total_value += position_value
            
            positions_summary[symbol] = {
                'allocated_capital': position.allocated_capital,
                'available_capital': position.available_capital,
                'position_size': position.size,
                'entry_price': position.entry_price,
                'current_price': position.current_price,
                'market_value': position.market_value,
                'unrealized_pnl': position.unrealized_pnl,
                'pnl_percentage': position.pnl_percentage,
                'is_open': position.is_open
            }
        
        return {
            'total_capital': self.total_capital,
            'total_value': total_value,
            'total_pnl': self.total_pnl,
            'unrealized_pnl': total_unrealized_pnl,
            'total_return': ((total_value - self.total_capital) / self.total_capital) * 100,
            'max_drawdown': self.max_drawdown,
            'open_positions': open_positions,
            'positions': positions_summary
        }
    
    def _update_portfolio_metrics(self) -> None:
        """Actualiza las métricas del portafolio."""
        summary = self.get_portfolio_summary()
        current_value = summary['total_value']
        
        # Actualizar peak value
        if current_value > self.peak_value:
            self.peak_value = current_value
        
        # Calcular drawdown actual
        if self.peak_value > 0:
            current_drawdown = (self.peak_value - current_value) / self.peak_value
            self.max_drawdown = max(self.max_drawdown, current_drawdown)
    
    def get_symbol_allocation(self, symbol: str) -> float:
        """
        Obtiene la asignación de capital para un símbolo específico.
        
        Args:
            symbol: Símbolo del activo
            
        Returns:
            Porcentaje de asignación (0.0 - 1.0)
        """
        return self.capital_allocation.get(symbol, 0.0)
    
    def get_available_capital(self, symbol: str) -> float:
        """
        Obtiene el capital disponible para un símbolo específico.
        
        Args:
            symbol: Símbolo del activo
            
        Returns:
            Capital disponible en USD
        """
        if symbol in self.positions:
            return self.positions[symbol].available_capital
        return 0.0
    
    def is_position_open(self, symbol: str) -> bool:
        """
        Verifica si hay una posición abierta en el símbolo.
        
        Args:
            symbol: Símbolo del activo
            
        Returns:
            True si hay una posición abierta
        """
        if symbol in self.positions:
            return self.positions[symbol].is_open
        return False