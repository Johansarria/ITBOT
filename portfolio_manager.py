import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class AssetClass(Enum):
    """Clasificación de activos"""
    CRYPTO = "crypto"
    FOREX = "forex"
    INDICES = "indices"
    COMMODITIES = "commodities"

@dataclass
class AssetConfig:
    """Configuración de un activo individual"""
    symbol: str
    asset_class: AssetClass
    target_allocation: float  # Porcentaje objetivo (0-1)
    min_allocation: float = 0.0
    max_allocation: float = 1.0
    risk_multiplier: float = 1.0
    expected_monthly_return: float = 0.0
    max_drawdown: float = 0.0
    volatility: float = 0.0
    
@dataclass
class PortfolioMetrics:
    """Métricas del portafolio"""
    total_value: float
    total_pnl: float
    daily_pnl: float
    unrealized_pnl: float
    realized_pnl: float
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    current_drawdown: float
    volatility: float
    var_95: float  # Value at Risk 95%
    
class PortfolioManager:
    """Gestor de portafolio con diversificación automática"""
    
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.available_capital = initial_capital
        
        # Configuración de activos basada en análisis previo
        self.asset_configs = self._initialize_asset_configs()
        
        # Estado del portafolio
        self.positions: Dict[str, float] = {}  # symbol -> quantity
        self.position_values: Dict[str, float] = {}  # symbol -> current_value
        self.entry_prices: Dict[str, float] = {}  # symbol -> entry_price
        self.current_prices: Dict[str, float] = {}  # symbol -> current_price
        
        # Métricas y tracking
        self.daily_returns: List[float] = []
        self.portfolio_history: List[Dict] = []
        self.rebalance_threshold = 0.05  # 5% desviación para rebalanceo
        self.last_rebalance = datetime.now()
        self.rebalance_frequency = timedelta(days=7)  # Rebalanceo semanal
        
        logger.info(f"Portfolio Manager inicializado con capital: ${initial_capital:,.2f}")
        
    def _initialize_asset_configs(self) -> Dict[str, AssetConfig]:
        """Inicializa configuración de activos basada en análisis previo"""
        configs = {
            # Criptomonedas (50% total)
            'BNBUSDT': AssetConfig(
                symbol='BNBUSDT',
                asset_class=AssetClass.CRYPTO,
                target_allocation=0.15,  # 15% - Mejor performer
                expected_monthly_return=0.6597,  # 65.97%
                max_drawdown=0.15,
                volatility=0.45,
                risk_multiplier=1.2
            ),
            'ADAUSDT': AssetConfig(
                symbol='ADAUSDT',
                asset_class=AssetClass.CRYPTO,
                target_allocation=0.10,  # 10%
                expected_monthly_return=0.6389,  # 63.89%
                max_drawdown=0.12,
                volatility=0.40,
                risk_multiplier=1.1
            ),
            'SOLUSDT': AssetConfig(
                symbol='SOLUSDT',
                asset_class=AssetClass.CRYPTO,
                target_allocation=0.10,  # 10% - Máximo retorno pero más riesgo
                expected_monthly_return=0.7345,  # 73.45%
                max_drawdown=0.20,
                volatility=0.55,
                risk_multiplier=1.5
            ),
            'ETHUSDT': AssetConfig(
                symbol='ETHUSDT',
                asset_class=AssetClass.CRYPTO,
                target_allocation=0.10,  # 10%
                expected_monthly_return=0.5057,  # 50.57%
                max_drawdown=0.10,
                volatility=0.35,
                risk_multiplier=1.0
            ),
            'BTCUSDT': AssetConfig(
                symbol='BTCUSDT',
                asset_class=AssetClass.CRYPTO,
                target_allocation=0.05,  # 5% - Más conservador
                expected_monthly_return=0.0605,  # 6.05%
                max_drawdown=0.08,
                volatility=0.30,
                risk_multiplier=0.8
            ),
            
            # Índices (20% total)
            'NAS100': AssetConfig(
                symbol='NAS100',
                asset_class=AssetClass.INDICES,
                target_allocation=0.20,  # 20% - Principal índice
                expected_monthly_return=0.15,  # 12-18% rango
                max_drawdown=0.06,
                volatility=0.20,
                risk_multiplier=0.7
            ),
            
            # Forex (15% total)
            'AUDCAD': AssetConfig(
                symbol='AUDCAD',
                asset_class=AssetClass.FOREX,
                target_allocation=0.15,  # 15%
                expected_monthly_return=0.10,  # 8-12% rango
                max_drawdown=0.04,
                volatility=0.15,
                risk_multiplier=0.6
            ),
            
            # Commodities (15% total)
            'XAUUSD': AssetConfig(
                symbol='XAUUSD',
                asset_class=AssetClass.COMMODITIES,
                target_allocation=0.15,  # 15% - Oro como refugio
                expected_monthly_return=0.125,  # 10-15% rango
                max_drawdown=0.05,
                volatility=0.18,
                risk_multiplier=0.5
            )
        }
        
        # Verificar que las asignaciones sumen 100%
        total_allocation = sum(config.target_allocation for config in configs.values())
        if abs(total_allocation - 1.0) > 0.001:
            logger.warning(f"Las asignaciones no suman 100%: {total_allocation:.3f}")
            
        return configs
        
    def update_price(self, symbol: str, price: float, timestamp: datetime = None):
        """Actualiza precio de un activo"""
        if timestamp is None:
            timestamp = datetime.now()
            
        self.current_prices[symbol] = price
        
        # Actualizar valor de posición si existe
        if symbol in self.positions and self.positions[symbol] != 0:
            self.position_values[symbol] = self.positions[symbol] * price
            
        # Verificar si necesita rebalanceo
        if self._should_rebalance():
            self._suggest_rebalance()
            
    def calculate_target_position_size(self, symbol: str, signal_strength: float = 1.0) -> float:
        """Calcula el tamaño objetivo de posición para un símbolo"""
        if symbol not in self.asset_configs:
            logger.warning(f"Símbolo {symbol} no configurado en portafolio")
            return 0.0
            
        config = self.asset_configs[symbol]
        current_price = self.current_prices.get(symbol)
        
        if current_price is None:
            logger.warning(f"Precio no disponible para {symbol}")
            return 0.0
            
        # Calcular valor objetivo basado en asignación
        target_value = self.current_capital * config.target_allocation
        
        # Ajustar por fuerza de señal (0-1)
        adjusted_target_value = target_value * signal_strength
        
        # Ajustar por multiplicador de riesgo
        risk_adjusted_value = adjusted_target_value * (1 / config.risk_multiplier)
        
        # Calcular cantidad en unidades
        target_quantity = risk_adjusted_value / current_price
        
        return target_quantity
        
    def calculate_position_size_with_risk(self, symbol: str, signal_strength: float, 
                                        stop_loss_pct: float = 0.02) -> Tuple[float, float]:
        """Calcula tamaño de posición considerando gestión de riesgo"""
        if symbol not in self.asset_configs:
            return 0.0, 0.0
            
        config = self.asset_configs[symbol]
        current_price = self.current_prices.get(symbol)
        
        if current_price is None:
            return 0.0, 0.0
            
        # Riesgo máximo por operación (2% del capital)
        max_risk_per_trade = self.current_capital * 0.02
        
        # Ajustar riesgo por volatilidad del activo
        adjusted_risk = max_risk_per_trade / config.risk_multiplier
        
        # Calcular tamaño basado en stop loss
        risk_per_unit = current_price * stop_loss_pct
        max_quantity_by_risk = adjusted_risk / risk_per_unit
        
        # Calcular tamaño basado en asignación objetivo
        target_quantity = self.calculate_target_position_size(symbol, signal_strength)
        
        # Usar el menor de los dos para gestión de riesgo
        final_quantity = min(max_quantity_by_risk, target_quantity)
        
        # Calcular valor de la posición
        position_value = final_quantity * current_price
        
        return final_quantity, position_value
        
    def get_current_allocation(self) -> Dict[str, float]:
        """Obtiene asignación actual del portafolio"""
        total_value = self.get_total_portfolio_value()
        
        if total_value == 0:
            return {symbol: 0.0 for symbol in self.asset_configs.keys()}
            
        current_allocation = {}
        for symbol in self.asset_configs.keys():
            position_value = self.position_values.get(symbol, 0.0)
            current_allocation[symbol] = position_value / total_value
            
        return current_allocation
        
    def get_allocation_deviation(self) -> Dict[str, float]:
        """Calcula desviación de asignación objetivo"""
        current_allocation = self.get_current_allocation()
        deviations = {}
        
        for symbol, config in self.asset_configs.items():
            current = current_allocation.get(symbol, 0.0)
            target = config.target_allocation
            deviations[symbol] = current - target
            
        return deviations
        
    def _should_rebalance(self) -> bool:
        """Determina si el portafolio necesita rebalanceo"""
        # Verificar frecuencia de rebalanceo
        if datetime.now() - self.last_rebalance < self.rebalance_frequency:
            return False
            
        # Verificar desviaciones significativas
        deviations = self.get_allocation_deviation()
        max_deviation = max(abs(dev) for dev in deviations.values())
        
        return max_deviation > self.rebalance_threshold
        
    def _suggest_rebalance(self) -> Dict[str, Dict]:
        """Sugiere operaciones de rebalanceo"""
        deviations = self.get_allocation_deviation()
        total_value = self.get_total_portfolio_value()
        suggestions = {}
        
        for symbol, deviation in deviations.items():
            if abs(deviation) > self.rebalance_threshold:
                config = self.asset_configs[symbol]
                current_price = self.current_prices.get(symbol)
                
                if current_price is None:
                    continue
                    
                # Calcular ajuste necesario
                target_value = total_value * config.target_allocation
                current_value = self.position_values.get(symbol, 0.0)
                value_adjustment = target_value - current_value
                quantity_adjustment = value_adjustment / current_price
                
                suggestions[symbol] = {
                    'current_allocation': self.get_current_allocation()[symbol],
                    'target_allocation': config.target_allocation,
                    'deviation': deviation,
                    'value_adjustment': value_adjustment,
                    'quantity_adjustment': quantity_adjustment,
                    'action': 'BUY' if quantity_adjustment > 0 else 'SELL'
                }
                
        if suggestions:
            logger.info(f"Rebalanceo sugerido para {len(suggestions)} activos")
            
        return suggestions
        
    def get_total_portfolio_value(self) -> float:
        """Calcula valor total del portafolio"""
        total_positions_value = sum(self.position_values.values())
        return self.available_capital + total_positions_value
        
    def calculate_portfolio_metrics(self) -> PortfolioMetrics:
        """Calcula métricas del portafolio"""
        total_value = self.get_total_portfolio_value()
        total_pnl = total_value - self.initial_capital
        
        # Calcular PnL no realizado
        unrealized_pnl = 0.0
        for symbol, quantity in self.positions.items():
            if quantity != 0 and symbol in self.current_prices and symbol in self.entry_prices:
                current_price = self.current_prices[symbol]
                entry_price = self.entry_prices[symbol]
                unrealized_pnl += (current_price - entry_price) * quantity
                
        # Calcular métricas de riesgo
        if len(self.daily_returns) > 1:
            returns_array = np.array(self.daily_returns)
            volatility = np.std(returns_array) * np.sqrt(252)  # Anualizada
            
            # Sharpe ratio (asumiendo risk-free rate = 2%)
            avg_return = np.mean(returns_array)
            sharpe_ratio = (avg_return - 0.02/252) / (volatility/np.sqrt(252)) if volatility > 0 else 0
            
            # VaR 95%
            var_95 = np.percentile(returns_array, 5) * total_value
        else:
            volatility = 0.0
            sharpe_ratio = 0.0
            var_95 = 0.0
            
        # Calcular drawdown
        if self.portfolio_history:
            peak_value = max(record['total_value'] for record in self.portfolio_history)
            current_drawdown = (peak_value - total_value) / peak_value if peak_value > 0 else 0
            max_drawdown = max(record.get('drawdown', 0) for record in self.portfolio_history)
        else:
            current_drawdown = 0.0
            max_drawdown = 0.0
            
        return PortfolioMetrics(
            total_value=total_value,
            total_pnl=total_pnl,
            daily_pnl=0.0,  # Calcular basado en último día
            unrealized_pnl=unrealized_pnl,
            realized_pnl=total_pnl - unrealized_pnl,
            win_rate=0.0,  # Calcular basado en trades cerrados
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            current_drawdown=current_drawdown,
            volatility=volatility,
            var_95=var_95
        )
        
    def add_position(self, symbol: str, quantity: float, entry_price: float):
        """Añade o actualiza una posición"""
        if symbol in self.positions:
            # Actualizar posición existente (promedio ponderado)
            current_quantity = self.positions[symbol]
            current_entry = self.entry_prices[symbol]
            
            total_quantity = current_quantity + quantity
            if total_quantity != 0:
                weighted_entry = ((current_quantity * current_entry) + (quantity * entry_price)) / total_quantity
                self.entry_prices[symbol] = weighted_entry
            
            self.positions[symbol] = total_quantity
        else:
            self.positions[symbol] = quantity
            self.entry_prices[symbol] = entry_price
            
        # Actualizar valor de posición
        current_price = self.current_prices.get(symbol, entry_price)
        self.position_values[symbol] = self.positions[symbol] * current_price
        
        # Actualizar capital disponible
        position_cost = quantity * entry_price
        self.available_capital -= position_cost
        
        logger.info(f"Posición actualizada: {symbol} = {self.positions[symbol]:.4f} @ {self.entry_prices[symbol]:.2f}")
        
    def remove_position(self, symbol: str, quantity: float, exit_price: float) -> float:
        """Remueve cantidad de una posición y retorna PnL realizado"""
        if symbol not in self.positions or self.positions[symbol] == 0:
            logger.warning(f"No hay posición para {symbol}")
            return 0.0
            
        if quantity > self.positions[symbol]:
            quantity = self.positions[symbol]
            
        # Calcular PnL realizado
        entry_price = self.entry_prices[symbol]
        realized_pnl = (exit_price - entry_price) * quantity
        
        # Actualizar posición
        self.positions[symbol] -= quantity
        
        # Si la posición se cierra completamente
        if self.positions[symbol] <= 0:
            self.positions[symbol] = 0
            if symbol in self.position_values:
                del self.position_values[symbol]
        else:
            # Actualizar valor de posición restante
            current_price = self.current_prices.get(symbol, exit_price)
            self.position_values[symbol] = self.positions[symbol] * current_price
            
        # Actualizar capital disponible
        proceeds = quantity * exit_price
        self.available_capital += proceeds
        
        logger.info(f"Posición reducida: {symbol} = {self.positions[symbol]:.4f}, PnL: ${realized_pnl:.2f}")
        
        return realized_pnl
        
    def get_portfolio_summary(self) -> Dict:
        """Obtiene resumen completo del portafolio"""
        metrics = self.calculate_portfolio_metrics()
        current_allocation = self.get_current_allocation()
        deviations = self.get_allocation_deviation()
        
        # Agrupar por clase de activo
        allocation_by_class = {}
        for symbol, allocation in current_allocation.items():
            asset_class = self.asset_configs[symbol].asset_class.value
            if asset_class not in allocation_by_class:
                allocation_by_class[asset_class] = 0.0
            allocation_by_class[asset_class] += allocation
            
        return {
            'timestamp': datetime.now(),
            'total_value': metrics.total_value,
            'total_pnl': metrics.total_pnl,
            'return_pct': (metrics.total_pnl / self.initial_capital) * 100,
            'available_capital': self.available_capital,
            'positions_count': len([p for p in self.positions.values() if p != 0]),
            'current_allocation': current_allocation,
            'target_allocation': {s: c.target_allocation for s, c in self.asset_configs.items()},
            'allocation_deviations': deviations,
            'allocation_by_class': allocation_by_class,
            'metrics': {
                'sharpe_ratio': metrics.sharpe_ratio,
                'max_drawdown': metrics.max_drawdown,
                'volatility': metrics.volatility,
                'var_95': metrics.var_95
            },
            'needs_rebalance': self._should_rebalance()
        }
        
if __name__ == "__main__":
    # Ejemplo de uso
    portfolio = PortfolioManager(initial_capital=10000)
    
    # Simular precios
    portfolio.update_price('BNBUSDT', 300.0)
    portfolio.update_price('ETHUSDT', 2500.0)
    portfolio.update_price('BTCUSDT', 45000.0)
    
    # Calcular tamaños de posición
    bnb_qty, bnb_value = portfolio.calculate_position_size_with_risk('BNBUSDT', 0.8)
    eth_qty, eth_value = portfolio.calculate_position_size_with_risk('ETHUSDT', 0.6)
    
    print(f"\nTamaños de posición sugeridos:")
    print(f"BNBUSDT: {bnb_qty:.4f} unidades (${bnb_value:.2f})")
    print(f"ETHUSDT: {eth_qty:.4f} unidades (${eth_value:.2f})")
    
    # Añadir posiciones
    portfolio.add_position('BNBUSDT', bnb_qty, 300.0)
    portfolio.add_position('ETHUSDT', eth_qty, 2500.0)
    
    # Mostrar resumen
    summary = portfolio.get_portfolio_summary()
    print(f"\n=== RESUMEN DEL PORTAFOLIO ===")
    print(f"Valor Total: ${summary['total_value']:,.2f}")
    print(f"PnL Total: ${summary['total_pnl']:,.2f} ({summary['return_pct']:.2f}%)")
    print(f"Capital Disponible: ${summary['available_capital']:,.2f}")
    print(f"\nAsignación Actual:")
    for symbol, allocation in summary['current_allocation'].items():
        target = summary['target_allocation'][symbol]
        deviation = summary['allocation_deviations'][symbol]
        print(f"  {symbol}: {allocation:.1%} (objetivo: {target:.1%}, desv: {deviation:+.1%})")