"""
SICAR Indices Risk Manager
Sistema de gestión de riesgo adaptado para índices
Incluye sizing dinámico, stops adaptativos y control de volatilidad
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Union
import logging
from dataclasses import dataclass, field
from enum import Enum
import warnings

# Importar módulos del proyecto
from indices_indicators import IndicesIndicators
from market_hours_system import MarketHoursSystem
from indices_config import get_index_config

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """Niveles de riesgo del mercado"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"

class PositionSizeMethod(Enum):
    """Métodos de cálculo de tamaño de posición"""
    FIXED_PERCENT = "fixed_percent"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    ATR_BASED = "atr_based"
    KELLY_CRITERION = "kelly_criterion"
    RISK_PARITY = "risk_parity"

@dataclass
class RiskMetrics:
    """Métricas de riesgo del portafolio"""
    portfolio_value: float = 0.0
    total_exposure: float = 0.0
    cash_available: float = 0.0
    daily_var: float = 0.0  # Value at Risk diario
    max_drawdown: float = 0.0
    volatility: float = 0.0
    beta: float = 1.0
    correlation_spy: float = 0.0
    risk_level: RiskLevel = RiskLevel.MEDIUM
    
@dataclass
class PositionRisk:
    """Riesgo específico de una posición"""
    symbol: str
    quantity: int
    entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_amount: float = 0.0
    position_size_pct: float = 0.0
    days_held: int = 0
    volatility: float = 0.0

class IndicesRiskManager:
    """
    Gestor de riesgo especializado para índices
    Maneja sizing dinámico, stops adaptativos y control de volatilidad
    """
    
    def __init__(self, 
                 initial_capital: float = 100000,
                 max_portfolio_risk: float = 0.02,  # 2% del portafolio por día
                 max_position_risk: float = 0.01,   # 1% por posición
                 max_correlation: float = 0.8):     # Máxima correlación entre posiciones
        
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_portfolio_risk = max_portfolio_risk
        self.max_position_risk = max_position_risk
        self.max_correlation = max_correlation
        
        # Componentes del sistema
        self.indicators = IndicesIndicators()
        self.market_hours = MarketHoursSystem()
        
        # Estado del portafolio
        self.positions = {}  # symbol -> PositionRisk
        self.daily_returns = []
        self.equity_history = []
        
        # Configuración de riesgo
        self.risk_config = {
            'volatility_lookback': 20,
            'var_confidence': 0.05,  # 95% VaR
            'max_positions': 5,
            'rebalance_threshold': 0.05,  # 5%
            'emergency_stop_loss': 0.10,  # 10%
            'volatility_multiplier': 2.0,
            'correlation_window': 60
        }
        
        # Cache para cálculos
        self.volatility_cache = {}
        self.correlation_cache = {}
        
    def calculate_position_size(self, 
                               symbol: str,
                               entry_price: float,
                               stop_loss: float,
                               method: PositionSizeMethod = PositionSizeMethod.VOLATILITY_ADJUSTED,
                               market_data: pd.DataFrame = None) -> int:
        """
        Calcula el tamaño óptimo de posición basado en el riesgo
        
        Args:
            symbol: Símbolo del índice
            entry_price: Precio de entrada
            stop_loss: Precio de stop loss
            method: Método de cálculo
            market_data: Datos de mercado para cálculos avanzados
        
        Returns:
            Cantidad de acciones a comprar
        """
        
        # Verificar límites básicos
        if not self._can_open_position(symbol):
            return 0
        
        # Calcular riesgo por acción
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share <= 0:
            logger.warning(f"Riesgo por acción inválido para {symbol}")
            return 0
        
        # Obtener configuración del índice
        config = get_index_config(symbol)
        
        # Calcular según el método seleccionado
        if method == PositionSizeMethod.FIXED_PERCENT:
            position_size = self._calculate_fixed_percent_size(
                entry_price, risk_per_share, config
            )
        
        elif method == PositionSizeMethod.VOLATILITY_ADJUSTED:
            position_size = self._calculate_volatility_adjusted_size(
                symbol, entry_price, risk_per_share, market_data, config
            )
        
        elif method == PositionSizeMethod.ATR_BASED:
            position_size = self._calculate_atr_based_size(
                symbol, entry_price, market_data, config
            )
        
        elif method == PositionSizeMethod.KELLY_CRITERION:
            position_size = self._calculate_kelly_size(
                symbol, entry_price, risk_per_share, market_data, config
            )
        
        else:
            position_size = self._calculate_fixed_percent_size(
                entry_price, risk_per_share, config
            )
        
        # Aplicar límites finales
        position_size = self._apply_position_limits(
            symbol, position_size, entry_price
        )
        
        logger.info(f"Tamaño calculado para {symbol}: {position_size} acciones")
        
        return position_size
    
    def _calculate_fixed_percent_size(self, entry_price: float, 
                                    risk_per_share: float, config: Dict) -> int:
        """Calcula tamaño basado en porcentaje fijo del capital"""
        
        risk_amount = self.current_capital * self.max_position_risk
        position_size = int(risk_amount / risk_per_share)
        
        return position_size
    
    def _calculate_volatility_adjusted_size(self, symbol: str, entry_price: float,
                                          risk_per_share: float, market_data: pd.DataFrame,
                                          config: Dict) -> int:
        """Calcula tamaño ajustado por volatilidad"""
        
        if market_data is None or market_data.empty:
            return self._calculate_fixed_percent_size(entry_price, risk_per_share, config)
        
        # Calcular volatilidad histórica
        volatility = self._get_volatility(symbol, market_data)
        
        # Ajustar riesgo por volatilidad
        base_volatility = 0.15  # 15% anual como base
        volatility_adjustment = base_volatility / max(volatility, 0.05)
        
        # Calcular tamaño ajustado
        adjusted_risk = self.current_capital * self.max_position_risk * volatility_adjustment
        position_size = int(adjusted_risk / risk_per_share)
        
        return position_size
    
    def _calculate_atr_based_size(self, symbol: str, entry_price: float,
                                market_data: pd.DataFrame, config: Dict) -> int:
        """Calcula tamaño basado en ATR"""
        
        if market_data is None or market_data.empty:
            return self._calculate_fixed_percent_size(entry_price, entry_price * 0.02, config)
        
        # Calcular ATR
        atr_period = config.get('atr_period', 14)
        if len(market_data) >= atr_period:
            atr = self.indicators.atr(
                market_data['High'], 
                market_data['Low'], 
                market_data['Close'], 
                atr_period
            ).iloc[-1]
        else:
            atr = entry_price * 0.02  # 2% como fallback
        
        # Usar ATR como medida de riesgo
        atr_multiplier = config.get('atr_stop_multiplier', 2.0)
        risk_per_share = atr * atr_multiplier
        
        # Calcular tamaño
        risk_amount = self.current_capital * self.max_position_risk
        position_size = int(risk_amount / risk_per_share)
        
        return position_size
    
    def _calculate_kelly_size(self, symbol: str, entry_price: float,
                            risk_per_share: float, market_data: pd.DataFrame,
                            config: Dict) -> int:
        """Calcula tamaño usando criterio de Kelly"""
        
        if market_data is None or len(market_data) < 30:
            return self._calculate_fixed_percent_size(entry_price, risk_per_share, config)
        
        # Estimar probabilidad de éxito y ratio win/loss
        # (Simplificado - en producción usar datos históricos de la estrategia)
        returns = market_data['Close'].pct_change().dropna()
        
        positive_returns = returns[returns > 0]
        negative_returns = returns[returns < 0]
        
        if len(positive_returns) == 0 or len(negative_returns) == 0:
            return self._calculate_fixed_percent_size(entry_price, risk_per_share, config)
        
        win_rate = len(positive_returns) / len(returns)
        avg_win = positive_returns.mean()
        avg_loss = abs(negative_returns.mean())
        
        # Fórmula de Kelly: f = (bp - q) / b
        # donde b = avg_win/avg_loss, p = win_rate, q = 1-win_rate
        if avg_loss > 0:
            b = avg_win / avg_loss
            kelly_fraction = (b * win_rate - (1 - win_rate)) / b
        else:
            kelly_fraction = 0
        
        # Limitar Kelly fraction para ser conservador
        kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Máximo 25%
        
        # Calcular tamaño
        kelly_amount = self.current_capital * kelly_fraction
        position_size = int(kelly_amount / entry_price)
        
        return position_size
    
    def _apply_position_limits(self, symbol: str, position_size: int, 
                             entry_price: float) -> int:
        """Aplica límites finales al tamaño de posición"""
        
        # Límite por capital disponible
        max_by_capital = int(self.current_capital * 0.95 / entry_price)
        position_size = min(position_size, max_by_capital)
        
        # Límite por número máximo de posiciones
        if len(self.positions) >= self.risk_config['max_positions']:
            position_size = 0
        
        # Límite por concentración
        position_value = position_size * entry_price
        max_position_value = self.current_capital * 0.3  # Máximo 30% en una posición
        
        if position_value > max_position_value:
            position_size = int(max_position_value / entry_price)
        
        # Límite mínimo práctico
        if position_size < 1:
            position_size = 0
        
        return position_size
    
    def calculate_dynamic_stop_loss(self, symbol: str, entry_price: float,
                                  direction: str, market_data: pd.DataFrame = None) -> float:
        """
        Calcula stop loss dinámico basado en volatilidad
        
        Args:
            symbol: Símbolo del índice
            entry_price: Precio de entrada
            direction: 'long' o 'short'
            market_data: Datos de mercado
        
        Returns:
            Precio de stop loss
        """
        
        config = get_index_config(symbol)
        
        if market_data is None or market_data.empty:
            # Stop loss fijo como fallback
            stop_pct = config.get('stop_loss_pct', 0.05)
            if direction == 'long':
                return entry_price * (1 - stop_pct)
            else:
                return entry_price * (1 + stop_pct)
        
        # Calcular ATR para stop dinámico
        atr_period = config.get('atr_period', 14)
        if len(market_data) >= atr_period:
            atr = self.indicators.atr(
                market_data['High'], 
                market_data['Low'], 
                market_data['Close'], 
                atr_period
            ).iloc[-1]
        else:
            atr = entry_price * 0.02
        
        # Multiplicador de ATR basado en volatilidad del mercado
        volatility = self._get_volatility(symbol, market_data)
        
        if volatility < 0.10:  # Baja volatilidad
            atr_multiplier = 1.5
        elif volatility < 0.20:  # Volatilidad media
            atr_multiplier = 2.0
        else:  # Alta volatilidad
            atr_multiplier = 2.5
        
        # Calcular stop loss
        stop_distance = atr * atr_multiplier
        
        if direction == 'long':
            stop_loss = entry_price - stop_distance
        else:
            stop_loss = entry_price + stop_distance
        
        # Aplicar límites mínimos y máximos
        min_stop_pct = 0.02  # Mínimo 2%
        max_stop_pct = 0.08  # Máximo 8%
        
        if direction == 'long':
            min_stop = entry_price * (1 - max_stop_pct)
            max_stop = entry_price * (1 - min_stop_pct)
            stop_loss = max(min_stop, min(stop_loss, max_stop))
        else:
            min_stop = entry_price * (1 + min_stop_pct)
            max_stop = entry_price * (1 + max_stop_pct)
            stop_loss = min(max_stop, max(stop_loss, min_stop))
        
        return stop_loss
    
    def calculate_take_profit(self, symbol: str, entry_price: float,
                            stop_loss: float, direction: str,
                            market_data: pd.DataFrame = None) -> float:
        """
        Calcula take profit dinámico
        
        Args:
            symbol: Símbolo del índice
            entry_price: Precio de entrada
            stop_loss: Precio de stop loss
            direction: 'long' o 'short'
            market_data: Datos de mercado
        
        Returns:
            Precio de take profit
        """
        
        config = get_index_config(symbol)
        
        # Calcular distancia del stop loss
        if direction == 'long':
            stop_distance = entry_price - stop_loss
        else:
            stop_distance = stop_loss - entry_price
        
        # Ratio riesgo/beneficio basado en volatilidad
        if market_data is not None and not market_data.empty:
            volatility = self._get_volatility(symbol, market_data)
            
            if volatility < 0.10:  # Baja volatilidad - ratio más conservador
                risk_reward_ratio = 1.5
            elif volatility < 0.20:  # Volatilidad media
                risk_reward_ratio = 2.0
            else:  # Alta volatilidad - ratio más agresivo
                risk_reward_ratio = 2.5
        else:
            risk_reward_ratio = 2.0  # Ratio por defecto
        
        # Calcular take profit
        profit_distance = stop_distance * risk_reward_ratio
        
        if direction == 'long':
            take_profit = entry_price + profit_distance
        else:
            take_profit = entry_price - profit_distance
        
        return take_profit
    
    def update_position_risk(self, symbol: str, current_price: float,
                           market_data: pd.DataFrame = None):
        """Actualiza el riesgo de una posición existente"""
        
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        # Actualizar precio y P&L
        position.current_price = current_price
        position.market_value = position.quantity * current_price
        position.unrealized_pnl = (current_price - position.entry_price) * position.quantity
        
        # Actualizar días en posición
        position.days_held += 1
        
        # Actualizar volatilidad si tenemos datos
        if market_data is not None and not market_data.empty:
            position.volatility = self._get_volatility(symbol, market_data)
        
        # Verificar si necesitamos ajustar stops
        self._check_trailing_stops(symbol, current_price, market_data)
    
    def _check_trailing_stops(self, symbol: str, current_price: float,
                            market_data: pd.DataFrame = None):
        """Verifica y ajusta trailing stops"""
        
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        if position.stop_loss is None:
            return
        
        # Determinar dirección de la posición
        direction = 'long' if position.quantity > 0 else 'short'
        
        # Calcular nuevo trailing stop
        if market_data is not None and not market_data.empty:
            atr = self.indicators.atr(
                market_data['High'], 
                market_data['Low'], 
                market_data['Close'], 
                14
            ).iloc[-1] if len(market_data) >= 14 else current_price * 0.02
            
            trailing_distance = atr * 2.0
        else:
            trailing_distance = current_price * 0.03  # 3% como fallback
        
        # Ajustar trailing stop
        if direction == 'long':
            new_stop = current_price - trailing_distance
            if new_stop > position.stop_loss:
                position.stop_loss = new_stop
                logger.info(f"Trailing stop actualizado para {symbol}: {new_stop:.2f}")
        
        else:  # short
            new_stop = current_price + trailing_distance
            if new_stop < position.stop_loss:
                position.stop_loss = new_stop
                logger.info(f"Trailing stop actualizado para {symbol}: {new_stop:.2f}")
    
    def calculate_portfolio_risk(self) -> RiskMetrics:
        """Calcula métricas de riesgo del portafolio completo"""
        
        # Calcular valor total del portafolio
        total_market_value = sum(pos.market_value for pos in self.positions.values())
        portfolio_value = self.current_capital + total_market_value
        
        # Calcular exposición total
        total_exposure = sum(abs(pos.market_value) for pos in self.positions.values())
        
        # Calcular VaR diario (simplificado)
        if len(self.daily_returns) >= 20:
            returns_array = np.array(self.daily_returns[-20:])
            daily_var = np.percentile(returns_array, self.risk_config['var_confidence'] * 100)
        else:
            daily_var = 0.0
        
        # Calcular drawdown máximo
        if len(self.equity_history) >= 2:
            equity_series = pd.Series(self.equity_history)
            running_max = equity_series.expanding().max()
            drawdown = (equity_series - running_max) / running_max
            max_drawdown = drawdown.min()
        else:
            max_drawdown = 0.0
        
        # Calcular volatilidad del portafolio
        if len(self.daily_returns) >= 10:
            portfolio_volatility = np.std(self.daily_returns[-20:]) * np.sqrt(252)
        else:
            portfolio_volatility = 0.0
        
        # Determinar nivel de riesgo
        risk_level = self._determine_risk_level(portfolio_volatility, max_drawdown, total_exposure)
        
        return RiskMetrics(
            portfolio_value=portfolio_value,
            total_exposure=total_exposure,
            cash_available=self.current_capital,
            daily_var=daily_var,
            max_drawdown=max_drawdown,
            volatility=portfolio_volatility,
            risk_level=risk_level
        )
    
    def _determine_risk_level(self, volatility: float, drawdown: float, 
                            exposure: float) -> RiskLevel:
        """Determina el nivel de riesgo actual del portafolio"""
        
        risk_score = 0
        
        # Factor volatilidad
        if volatility > 0.25:
            risk_score += 3
        elif volatility > 0.20:
            risk_score += 2
        elif volatility > 0.15:
            risk_score += 1
        
        # Factor drawdown
        if abs(drawdown) > 0.15:
            risk_score += 3
        elif abs(drawdown) > 0.10:
            risk_score += 2
        elif abs(drawdown) > 0.05:
            risk_score += 1
        
        # Factor exposición
        exposure_ratio = exposure / (self.current_capital + exposure)
        if exposure_ratio > 0.8:
            risk_score += 2
        elif exposure_ratio > 0.6:
            risk_score += 1
        
        # Determinar nivel
        if risk_score >= 6:
            return RiskLevel.EXTREME
        elif risk_score >= 4:
            return RiskLevel.HIGH
        elif risk_score >= 2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def should_reduce_exposure(self) -> bool:
        """Determina si se debe reducir la exposición del portafolio"""
        
        risk_metrics = self.calculate_portfolio_risk()
        
        # Criterios para reducir exposición
        reduce_exposure = (
            risk_metrics.risk_level in [RiskLevel.HIGH, RiskLevel.EXTREME] or
            risk_metrics.max_drawdown < -0.10 or  # Drawdown > 10%
            risk_metrics.volatility > 0.30 or     # Volatilidad > 30%
            risk_metrics.total_exposure > self.current_capital * 0.8  # Exposición > 80%
        )
        
        return reduce_exposure
    
    def _can_open_position(self, symbol: str) -> bool:
        """Verifica si se puede abrir una nueva posición"""
        
        # Verificar número máximo de posiciones
        if len(self.positions) >= self.risk_config['max_positions']:
            return False
        
        # Verificar si ya tenemos posición en este símbolo
        if symbol in self.positions:
            return False
        
        # Verificar nivel de riesgo del portafolio
        if self.should_reduce_exposure():
            return False
        
        # Verificar capital disponible
        if self.current_capital < self.initial_capital * 0.1:  # Mínimo 10% de capital
            return False
        
        return True
    
    def _get_volatility(self, symbol: str, market_data: pd.DataFrame) -> float:
        """Calcula volatilidad histórica del símbolo"""
        
        cache_key = f"{symbol}_{len(market_data)}"
        if cache_key in self.volatility_cache:
            return self.volatility_cache[cache_key]
        
        if len(market_data) < 10:
            return 0.15  # Volatilidad por defecto
        
        # Calcular retornos
        returns = market_data['Close'].pct_change().dropna()
        
        # Volatilidad anualizada
        volatility = returns.std() * np.sqrt(252)
        
        # Guardar en cache
        self.volatility_cache[cache_key] = volatility
        
        return volatility
    
    def add_position(self, symbol: str, quantity: int, entry_price: float,
                    stop_loss: float = None, take_profit: float = None):
        """Agrega una nueva posición al portafolio"""
        
        position = PositionRisk(
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            current_price=entry_price,
            market_value=quantity * entry_price,
            unrealized_pnl=0.0,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_amount=abs(quantity * (entry_price - (stop_loss or entry_price * 0.95))),
            position_size_pct=(quantity * entry_price) / self.current_capital * 100,
            days_held=0
        )
        
        self.positions[symbol] = position
        
        # Actualizar capital
        self.current_capital -= quantity * entry_price
        
        logger.info(f"Posición agregada: {symbol}, {quantity} acciones @ {entry_price}")
    
    def remove_position(self, symbol: str, exit_price: float) -> Optional[PositionRisk]:
        """Remueve una posición del portafolio"""
        
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        
        # Calcular P&L final
        final_pnl = (exit_price - position.entry_price) * position.quantity
        
        # Actualizar capital
        self.current_capital += position.quantity * exit_price
        
        # Remover posición
        removed_position = self.positions.pop(symbol)
        
        logger.info(f"Posición cerrada: {symbol}, P&L: ${final_pnl:.2f}")
        
        return removed_position
    
    def get_risk_summary(self) -> Dict:
        """Genera un resumen del estado de riesgo"""
        
        risk_metrics = self.calculate_portfolio_risk()
        
        return {
            'portfolio_value': risk_metrics.portfolio_value,
            'cash_available': risk_metrics.cash_available,
            'total_exposure': risk_metrics.total_exposure,
            'exposure_ratio': risk_metrics.total_exposure / risk_metrics.portfolio_value if risk_metrics.portfolio_value > 0 else 0,
            'daily_var': risk_metrics.daily_var,
            'max_drawdown': risk_metrics.max_drawdown,
            'volatility': risk_metrics.volatility,
            'risk_level': risk_metrics.risk_level.value,
            'num_positions': len(self.positions),
            'should_reduce_exposure': self.should_reduce_exposure(),
            'positions': {
                symbol: {
                    'quantity': pos.quantity,
                    'market_value': pos.market_value,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'days_held': pos.days_held,
                    'position_size_pct': pos.position_size_pct
                }
                for symbol, pos in self.positions.items()
            }
        }

# Función de utilidad para crear el risk manager
def create_indices_risk_manager(initial_capital: float = 100000,
                               max_portfolio_risk: float = 0.02) -> IndicesRiskManager:
    """Crea una instancia del gestor de riesgo para índices"""
    return IndicesRiskManager(
        initial_capital=initial_capital,
        max_portfolio_risk=max_portfolio_risk
    )

if __name__ == "__main__":
    # Ejemplo de uso
    risk_manager = create_indices_risk_manager()
    
    # Crear datos de ejemplo
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
    np.random.seed(42)
    
    market_data = pd.DataFrame({
        'High': 100 + np.random.randn(len(dates)).cumsum() * 0.5 + 1,
        'Low': 100 + np.random.randn(len(dates)).cumsum() * 0.5 - 1,
        'Close': 100 + np.random.randn(len(dates)).cumsum() * 0.5,
    }, index=dates)
    
    # Calcular tamaño de posición
    entry_price = 100.0
    stop_loss = 95.0
    
    position_size = risk_manager.calculate_position_size(
        'SPY', entry_price, stop_loss, 
        PositionSizeMethod.VOLATILITY_ADJUSTED, 
        market_data
    )
    
    print(f"Tamaño de posición calculado: {position_size} acciones")
    
    # Calcular stop loss dinámico
    dynamic_stop = risk_manager.calculate_dynamic_stop_loss(
        'SPY', entry_price, 'long', market_data
    )
    
    print(f"Stop loss dinámico: ${dynamic_stop:.2f}")
    
    # Resumen de riesgo
    risk_summary = risk_manager.get_risk_summary()
    print(f"Resumen de riesgo: {risk_summary}")