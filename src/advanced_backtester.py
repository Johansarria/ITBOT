"""Sistema de Backtesting Avanzado - Phase 2
Backtesting completo con análisis de drawdown y métricas avanzadas
Incluye Combinatorial Purged Cross-Validation (CPCV) para validación robusta
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, NamedTuple, Callable
from dataclasses import dataclass
from enum import Enum
import json
import warnings
from itertools import combinations
from sklearn.model_selection import TimeSeriesSplit
import concurrent.futures
from threading import Lock
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrderType(Enum):
    """Tipos de órdenes"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderSide(Enum):
    """Lado de la orden"""
    BUY = "buy"
    SELL = "sell"

class PositionStatus(Enum):
    """Estado de la posición"""
    OPEN = "open"
    CLOSED = "closed"
    PARTIAL = "partial"

@dataclass
class Order:
    """Orden de trading"""
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float]
    stop_price: Optional[float]
    timestamp: datetime
    filled_quantity: float = 0.0
    filled_price: Optional[float] = None
    status: str = "pending"
    commission: float = 0.0

@dataclass
class Trade:
    """Trade ejecutado"""
    id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    timestamp: datetime
    commission: float
    pnl: float = 0.0

@dataclass
class Position:
    """Posición abierta"""
    symbol: str
    quantity: float
    entry_price: float
    entry_time: datetime
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    status: PositionStatus
    trades: List[Trade]
    max_profit: float = 0.0
    max_loss: float = 0.0

@dataclass
class DrawdownPeriod:
    """Período de drawdown"""
    start_date: datetime
    end_date: Optional[datetime]
    peak_value: float
    trough_value: float
    drawdown_pct: float
    duration_days: int
    recovery_days: Optional[int]
    is_recovered: bool

@dataclass
class BacktestMetrics:
    """Métricas del backtest"""
    # Retornos
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    
    # Drawdown
    max_drawdown: float
    avg_drawdown: float
    max_drawdown_duration: int
    avg_drawdown_duration: float
    recovery_factor: float
    
    # Trading
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    
    # Riesgo
    var_95: float
    cvar_95: float
    beta: float
    alpha: float
    information_ratio: float
    
    # Otros
    start_date: datetime
    end_date: datetime
    trading_days: int
    commission_paid: float

@dataclass
class AdvancedMetrics:
    """Métricas avanzadas de performance"""
    # Métricas de retorno ajustadas por riesgo
    treynor_ratio: float
    jensen_alpha: float
    modigliani_ratio: float
    information_ratio: float
    tracking_error: float
    
    # Métricas de drawdown avanzadas
    ulcer_index: float
    pain_index: float
    lake_ratio: float
    burke_ratio: float
    
    # Métricas de consistencia
    gain_to_pain_ratio: float
    sterling_ratio: float
    kappa_three: float
    omega_ratio: float
    
    # Métricas de tail risk
    tail_ratio: float
    expected_shortfall_ratio: float
    conditional_drawdown_risk: float
    maximum_adverse_excursion: float
    
    # Métricas de timing
    up_capture_ratio: float
    down_capture_ratio: float
    capture_ratio: float
    batting_average: float
    
    # Métricas de estabilidad
    return_stability: float
    sharpe_stability: float
    performance_consistency: float
    rolling_sharpe_std: float

@dataclass
class BacktestResult:
    """Resultado completo del backtest"""
    metrics: BacktestMetrics
    advanced_metrics: Optional[AdvancedMetrics]
    equity_curve: pd.DataFrame
    trades: List[Trade]
    positions: List[Position]
    drawdown_periods: List[DrawdownPeriod]
    daily_returns: pd.Series
    monthly_returns: pd.Series
    success: bool
    message: str

@dataclass
class CPCVResult:
    """Resultado de Combinatorial Purged Cross-Validation"""
    mean_return: float
    std_return: float
    mean_sharpe: float
    std_sharpe: float
    mean_max_drawdown: float
    std_max_drawdown: float
    win_rate: float
    total_folds: int
    successful_folds: int
    fold_results: List[BacktestResult]
    confidence_interval_95: Tuple[float, float]
    robustness_score: float  # Métrica de robustez (0-1)

@dataclass
class CPCVConfig:
    """Configuración para CPCV"""
    n_splits: int = 5  # Número de splits para cross-validation
    purge_pct: float = 0.02  # Porcentaje de datos a purgar entre train/test
    embargo_pct: float = 0.01  # Porcentaje de embargo después del test
    min_train_length: int = 252  # Mínimo días de entrenamiento (1 año aprox)
    min_test_length: int = 63   # Mínimo días de test (3 meses aprox)
    n_combinations: int = 10    # Número de combinaciones a probar
    parallel_execution: bool = True  # Ejecución en paralelo
    confidence_level: float = 0.95  # Nivel de confianza para intervalos

class AdvancedBacktester:
    """
    Backtester avanzado con soporte para CPCV
    """
    
    def __init__(self, initial_capital: float = 100000, commission_rate: float = 0.001):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.market_data = {}
        self.current_capital = initial_capital
        self.current_positions = {}
        self.closed_positions = []
        self.all_trades = []
        self.all_orders = []
        self.equity_history = []
        self.drawdown_history = []
        self.peak_equity = initial_capital
        self.current_timestamp = None
        self.current_prices = {}
        self.order_counter = 0
        self.trade_counter = 0
        self.logger = logging.getLogger(__name__)
        self._lock = Lock()  # Para ejecución paralela segura
        
        # Configuración
        self.slippage = 0.001  # 0.1% slippage
        self.risk_free_rate = 0.02  # 2% anual
        
        self.logger.info("✅ AdvancedBacktester inicializado")
    
    def load_market_data(self, data: Dict[str, pd.DataFrame]):
        """Carga datos de mercado para el backtest"""
        try:
            self.market_data = {}
            
            for symbol, df in data.items():
                # Asegurar que tenemos las columnas necesarias
                required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                if not all(col in df.columns for col in required_cols):
                    self.logger.warning(f"⚠️ Datos incompletos para {symbol}")
                    continue
                
                # Ordenar por timestamp
                df_sorted = df.sort_values('timestamp').reset_index(drop=True)
                self.market_data[symbol] = df_sorted
                
                self.logger.info(f"📊 Cargados {len(df_sorted)} períodos para {symbol}")
            
            if not self.market_data:
                raise ValueError("No se cargaron datos de mercado válidos")
            
            self.logger.info(f"✅ Datos de mercado cargados para {len(self.market_data)} símbolos")
            
        except Exception as e:
            self.logger.error(f"❌ Error cargando datos de mercado: {e}")
            raise
    
    def get_position(self, symbol: str) -> float:
        """Obtiene la cantidad de posición actual para un símbolo"""
        return self.current_positions.get(symbol, 0.0)
    
    @property
    def available_capital(self) -> float:
        """Obtiene el capital disponible"""
        return self.current_capital
    
    def place_order(self, symbol: str, side, order_type=None, quantity: float = None, price: Optional[float] = None, stop_price: Optional[float] = None) -> str:
        """Versión sobrecargada de place_order que acepta strings y parámetros posicionales"""
        try:
            # Si se llama con strings (como en demo_multi_capital_debug.py)
            if isinstance(side, str):
                # Formato: place_order(symbol, side_str, quantity, price)
                side_str = side
                
                # Los parámetros se desplazan cuando side es string
                if order_type is not None and quantity is None:
                    # place_order(symbol, "buy", quantity)
                    quantity = order_type
                    order_type = None
                elif order_type is not None and quantity is not None:
                    # place_order(symbol, "buy", quantity, price)
                    price = quantity
                    quantity = order_type
                    order_type = None
                
                # Convertir string a enum
                if side_str.lower() == 'buy':
                    side_enum = OrderSide.BUY
                elif side_str.lower() == 'sell':
                    side_enum = OrderSide.SELL
                else:
                    raise ValueError(f"Lado de orden inválido: {side_str}")
                
                return self._place_order_internal(symbol, side_enum, OrderType.MARKET, quantity or 0, price, stop_price)
            else:
                # Formato original con enums
                return self._place_order_internal(symbol, side, order_type or OrderType.MARKET, quantity or 0, price, stop_price)
                
        except Exception as e:
            self.logger.error(f"❌ Error en place_order: {e}")
            return ""
    
    def _place_order_internal(self, symbol: str, side: OrderSide, order_type: OrderType,
                   quantity: float, price: Optional[float] = None,
                   stop_price: Optional[float] = None) -> str:
        """Coloca una orden (método interno)"""
        try:
            order_id = f"order_{len(self.all_orders) + 1}_{int(datetime.now().timestamp())}"
            
            order = Order(
                id=order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                stop_price=stop_price,
                timestamp=self.current_timestamp,
                commission=quantity * (price or self.current_prices.get(symbol, 0)) * self.commission_rate
            )
            
            self.all_orders.append(order)
            
            # Intentar ejecutar inmediatamente si es orden de mercado
            if order_type == OrderType.MARKET:
                self._execute_order(order)
            
            return order_id
            
        except Exception as e:
            self.logger.error(f"❌ Error colocando orden: {e}")
            return ""
    
    def _execute_order(self, order: Order) -> bool:
        """Ejecuta una orden"""
        try:
            if order.symbol not in self.current_prices:
                return False
            
            current_price = self.current_prices[order.symbol]
            
            # Verificar si la orden puede ejecutarse
            can_execute = False
            execution_price = current_price
            
            if order.order_type == OrderType.MARKET:
                can_execute = True
                # Aplicar slippage
                if order.side == OrderSide.BUY:
                    execution_price *= (1 + self.slippage)
                else:
                    execution_price *= (1 - self.slippage)
            
            elif order.order_type == OrderType.LIMIT:
                if order.side == OrderSide.BUY and current_price <= order.price:
                    can_execute = True
                    execution_price = order.price
                elif order.side == OrderSide.SELL and current_price >= order.price:
                    can_execute = True
                    execution_price = order.price
            
            elif order.order_type == OrderType.STOP:
                if order.side == OrderSide.BUY and current_price >= order.stop_price:
                    can_execute = True
                elif order.side == OrderSide.SELL and current_price <= order.stop_price:
                    can_execute = True
            
            if not can_execute:
                return False
            
            # Verificar capital disponible para compras
            if order.side == OrderSide.BUY:
                required_capital = order.quantity * execution_price + order.commission
                if required_capital > self.current_capital:
                    self.logger.warning(f"⚠️ Capital insuficiente para orden {order.id}")
                    return False
            
            # Verificar cantidad disponible para ventas
            elif order.side == OrderSide.SELL:
                current_position = self.current_positions.get(order.symbol, 0)
                if order.quantity > current_position:
                    self.logger.warning(f"⚠️ Posición insuficiente para venta de {order.symbol}")
                    return False
            
            # Ejecutar la orden
            trade_id = f"trade_{len(self.all_trades) + 1}_{int(datetime.now().timestamp())}"
            
            trade = Trade(
                id=trade_id,
                order_id=order.id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=execution_price,
                timestamp=self.current_timestamp,
                commission=order.commission
            )
            
            # Actualizar posiciones y capital
            if order.side == OrderSide.BUY:
                self.current_positions[order.symbol] = self.current_positions.get(order.symbol, 0) + order.quantity
                self.current_capital -= (order.quantity * execution_price + order.commission)
            else:
                self.current_positions[order.symbol] = self.current_positions.get(order.symbol, 0) - order.quantity
                self.current_capital += (order.quantity * execution_price - order.commission)
            
            # Actualizar orden
            order.filled_quantity = order.quantity
            order.filled_price = execution_price
            order.status = "filled"
            
            self.all_trades.append(trade)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error ejecutando orden {order.id}: {e}")
            return False
    
    def _update_positions(self):
        """Actualiza el valor de las posiciones actuales"""
        try:
            total_position_value = 0
            
            for symbol, quantity in self.current_positions.items():
                if quantity > 0 and symbol in self.current_prices:
                    position_value = quantity * self.current_prices[symbol]
                    total_position_value += position_value
            
            # Valor total del portafolio
            total_equity = self.current_capital + total_position_value
            
            # Actualizar historial de equity
            self.equity_history.append({
                'timestamp': self.current_timestamp,
                'equity': total_equity,
                'cash': self.current_capital,
                'positions_value': total_position_value
            })
            
            # Actualizar peak y drawdown
            if total_equity > self.peak_equity:
                self.peak_equity = total_equity
            
            current_drawdown = (self.peak_equity - total_equity) / self.peak_equity
            self.drawdown_history.append({
                'timestamp': self.current_timestamp,
                'drawdown': current_drawdown,
                'peak_equity': self.peak_equity,
                'current_equity': total_equity
            })
            
        except Exception as e:
            self.logger.error(f"❌ Error actualizando posiciones: {e}")
    
    def _calculate_metrics(self) -> BacktestMetrics:
        """Calcula métricas del backtest"""
        try:
            if not self.equity_history:
                raise ValueError("No hay historial de equity para calcular métricas")
            
            # Convertir a DataFrame
            equity_df = pd.DataFrame(self.equity_history)
            equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
            equity_df = equity_df.set_index('timestamp')
            
            # Calcular retornos
            equity_df['returns'] = equity_df['equity'].pct_change()
            daily_returns = equity_df['returns'].dropna()
            
            # Métricas básicas
            total_return = (equity_df['equity'].iloc[-1] / self.initial_capital) - 1
            trading_days = len(equity_df)
            annualized_return = (1 + total_return) ** (252 / trading_days) - 1 if trading_days > 0 else 0
            volatility = daily_returns.std() * np.sqrt(252) if len(daily_returns) > 1 else 0
            
            # Ratios de riesgo
            sharpe_ratio = (annualized_return - self.risk_free_rate) / volatility if volatility > 0 else 0
            
            # Sortino ratio (solo downside deviation)
            downside_returns = daily_returns[daily_returns < 0]
            downside_deviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 1 else 0
            sortino_ratio = (annualized_return - self.risk_free_rate) / downside_deviation if downside_deviation > 0 else 0
            
            # Drawdown
            drawdown_df = pd.DataFrame(self.drawdown_history)
            max_drawdown = drawdown_df['drawdown'].max() if not drawdown_df.empty else 0
            avg_drawdown = drawdown_df['drawdown'].mean() if not drawdown_df.empty else 0
            
            # Calmar ratio
            calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0
            
            # Métricas de trading
            total_trades = len(self.all_trades)
            winning_trades = len([t for t in self.all_trades if t.pnl > 0])
            losing_trades = total_trades - winning_trades
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            wins = [t.pnl for t in self.all_trades if t.pnl > 0]
            losses = [abs(t.pnl) for t in self.all_trades if t.pnl < 0]
            
            avg_win = np.mean(wins) if wins else 0
            avg_loss = np.mean(losses) if losses else 0
            profit_factor = sum(wins) / sum(losses) if losses and sum(losses) > 0 else 0
            
            # VaR y CVaR
            var_95 = np.percentile(daily_returns, 5) if len(daily_returns) > 0 else 0
            cvar_95 = daily_returns[daily_returns <= var_95].mean() if len(daily_returns) > 0 else 0
            
            # Comisiones pagadas
            commission_paid = sum(t.commission for t in self.all_trades)
            
            return BacktestMetrics(
                total_return=total_return,
                annualized_return=annualized_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                calmar_ratio=calmar_ratio,
                max_drawdown=max_drawdown,
                avg_drawdown=avg_drawdown,
                max_drawdown_duration=0,  # Simplificado
                avg_drawdown_duration=0,  # Simplificado
                recovery_factor=total_return / max_drawdown if max_drawdown > 0 else 0,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                avg_win=avg_win,
                avg_loss=avg_loss,
                profit_factor=profit_factor,
                var_95=var_95,
                cvar_95=cvar_95,
                beta=0,  # Simplificado
                alpha=0,  # Simplificado
                information_ratio=0,  # Simplificado
                start_date=equity_df.index[0] if not equity_df.empty else datetime.now(),
                end_date=equity_df.index[-1] if not equity_df.empty else datetime.now(),
                trading_days=trading_days,
                commission_paid=commission_paid
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando métricas: {e}")
            # Retornar métricas vacías en caso de error
            return BacktestMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, datetime.now(), datetime.now(), 0, 0)
    
    def _calculate_advanced_metrics(self, daily_returns: pd.Series, equity_df: pd.DataFrame, 
                                  basic_metrics: BacktestMetrics) -> AdvancedMetrics:
        """Calcula métricas avanzadas de performance"""
        try:
            if len(daily_returns) < 10:
                # Retornar métricas vacías si no hay suficientes datos
                return AdvancedMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            
            # Benchmark (asumimos S&P 500 con retorno anual del 10%)
            benchmark_daily_return = 0.10 / 252
            benchmark_returns = pd.Series([benchmark_daily_return] * len(daily_returns), index=daily_returns.index)
            
            # === MÉTRICAS DE RETORNO AJUSTADAS POR RIESGO ===
            
            # Treynor Ratio
            portfolio_beta = self._calculate_beta(daily_returns, benchmark_returns)
            treynor_ratio = (basic_metrics.annualized_return - self.risk_free_rate) / portfolio_beta if portfolio_beta != 0 else 0
            
            # Jensen's Alpha
            expected_return = self.risk_free_rate + portfolio_beta * (0.10 - self.risk_free_rate)
            jensen_alpha = basic_metrics.annualized_return - expected_return
            
            # Modigliani Ratio (M²)
            benchmark_volatility = benchmark_returns.std() * np.sqrt(252)
            if basic_metrics.volatility > 0:
                adjusted_return = basic_metrics.annualized_return * (benchmark_volatility / basic_metrics.volatility)
                modigliani_ratio = adjusted_return - 0.10  # Benchmark return
            else:
                modigliani_ratio = 0
            
            # Information Ratio mejorado
            excess_returns = daily_returns - benchmark_returns
            tracking_error = excess_returns.std() * np.sqrt(252)
            information_ratio = excess_returns.mean() * np.sqrt(252) / tracking_error if tracking_error > 0 else 0
            
            # === MÉTRICAS DE DRAWDOWN AVANZADAS ===
            
            # Ulcer Index
            ulcer_index = self._calculate_ulcer_index(equity_df)
            
            # Pain Index
            pain_index = self._calculate_pain_index(equity_df)
            
            # Lake Ratio
            lake_ratio = self._calculate_lake_ratio(equity_df)
            
            # Burke Ratio
            burke_ratio = basic_metrics.annualized_return / np.sqrt(np.mean([dd**2 for dd in self._get_drawdown_series(equity_df)])) if len(self._get_drawdown_series(equity_df)) > 0 else 0
            
            # === MÉTRICAS DE CONSISTENCIA ===
            
            # Gain to Pain Ratio
            positive_returns = daily_returns[daily_returns > 0].sum()
            negative_returns = abs(daily_returns[daily_returns < 0].sum())
            gain_to_pain_ratio = positive_returns / negative_returns if negative_returns > 0 else float('inf')
            
            # Sterling Ratio
            avg_max_drawdown = np.mean([abs(dd) for dd in self._get_drawdown_series(equity_df)])
            sterling_ratio = basic_metrics.annualized_return / avg_max_drawdown if avg_max_drawdown > 0 else 0
            
            # Kappa Three (downside risk measure)
            kappa_three = self._calculate_kappa_three(daily_returns)
            
            # Omega Ratio
            omega_ratio = self._calculate_omega_ratio(daily_returns)
            
            # === MÉTRICAS DE TAIL RISK ===
            
            # Tail Ratio
            tail_ratio = abs(np.percentile(daily_returns, 95)) / abs(np.percentile(daily_returns, 5)) if np.percentile(daily_returns, 5) != 0 else 0
            
            # Expected Shortfall Ratio
            var_5 = np.percentile(daily_returns, 5)
            expected_shortfall = daily_returns[daily_returns <= var_5].mean()
            expected_shortfall_ratio = abs(daily_returns.mean() / expected_shortfall) if expected_shortfall != 0 else 0
            
            # Conditional Drawdown Risk
            conditional_drawdown_risk = self._calculate_conditional_drawdown_risk(equity_df)
            
            # Maximum Adverse Excursion
            maximum_adverse_excursion = self._calculate_max_adverse_excursion()
            
            # === MÉTRICAS DE TIMING ===
            
            # Up/Down Capture Ratios
            up_capture_ratio, down_capture_ratio = self._calculate_capture_ratios(daily_returns, benchmark_returns)
            capture_ratio = up_capture_ratio / down_capture_ratio if down_capture_ratio != 0 else 0
            
            # Batting Average
            batting_average = len(daily_returns[daily_returns > benchmark_returns]) / len(daily_returns) if len(daily_returns) > 0 else 0
            
            # === MÉTRICAS DE ESTABILIDAD ===
            
            # Return Stability
            return_stability = self._calculate_return_stability(daily_returns)
            
            # Sharpe Stability
            sharpe_stability = self._calculate_sharpe_stability(daily_returns)
            
            # Performance Consistency
            performance_consistency = self._calculate_performance_consistency(daily_returns)
            
            # Rolling Sharpe Standard Deviation
            rolling_sharpe_std = self._calculate_rolling_sharpe_std(daily_returns)
            
            return AdvancedMetrics(
                treynor_ratio=treynor_ratio,
                jensen_alpha=jensen_alpha,
                modigliani_ratio=modigliani_ratio,
                information_ratio=information_ratio,
                tracking_error=tracking_error,
                ulcer_index=ulcer_index,
                pain_index=pain_index,
                lake_ratio=lake_ratio,
                burke_ratio=burke_ratio,
                gain_to_pain_ratio=gain_to_pain_ratio,
                sterling_ratio=sterling_ratio,
                kappa_three=kappa_three,
                omega_ratio=omega_ratio,
                tail_ratio=tail_ratio,
                expected_shortfall_ratio=expected_shortfall_ratio,
                conditional_drawdown_risk=conditional_drawdown_risk,
                maximum_adverse_excursion=maximum_adverse_excursion,
                up_capture_ratio=up_capture_ratio,
                down_capture_ratio=down_capture_ratio,
                capture_ratio=capture_ratio,
                batting_average=batting_average,
                return_stability=return_stability,
                sharpe_stability=sharpe_stability,
                performance_consistency=performance_consistency,
                rolling_sharpe_std=rolling_sharpe_std
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando métricas avanzadas: {e}")
            return AdvancedMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    
    def _create_equity_curve(self) -> pd.DataFrame:
        """Crea la curva de equity"""
        try:
            if not self.equity_history:
                return pd.DataFrame()
            
            df = pd.DataFrame(self.equity_history)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
            df['returns'] = df['equity'].pct_change()
            df['cumulative_returns'] = (1 + df['returns']).cumprod() - 1
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Error creando curva de equity: {e}")
            return pd.DataFrame()
    
    # === MÉTODOS AUXILIARES PARA MÉTRICAS AVANZADAS ===
    
    def _calculate_beta(self, portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> float:
        """Calcula el beta del portafolio"""
        try:
            if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) < 2:
                return 1.0
            
            covariance = np.cov(portfolio_returns, benchmark_returns)[0][1]
            benchmark_variance = np.var(benchmark_returns)
            
            return covariance / benchmark_variance if benchmark_variance != 0 else 1.0
        except:
            return 1.0
    
    def _calculate_ulcer_index(self, equity_df: pd.DataFrame) -> float:
        """Calcula el Ulcer Index"""
        try:
            if equity_df.empty or 'equity' not in equity_df.columns:
                return 0.0
            
            equity_series = equity_df['equity']
            running_max = equity_series.expanding().max()
            drawdown_pct = ((equity_series - running_max) / running_max) * 100
            
            ulcer_index = np.sqrt(np.mean(drawdown_pct ** 2))
            return ulcer_index
        except:
            return 0.0
    
    def _calculate_pain_index(self, equity_df: pd.DataFrame) -> float:
        """Calcula el Pain Index"""
        try:
            if equity_df.empty or 'equity' not in equity_df.columns:
                return 0.0
            
            equity_series = equity_df['equity']
            running_max = equity_series.expanding().max()
            drawdown_pct = ((equity_series - running_max) / running_max) * 100
            
            pain_index = np.mean(np.abs(drawdown_pct))
            return pain_index
        except:
            return 0.0
    
    def _calculate_lake_ratio(self, equity_df: pd.DataFrame) -> float:
        """Calcula el Lake Ratio"""
        try:
            if equity_df.empty or 'equity' not in equity_df.columns:
                return 0.0
            
            equity_series = equity_df['equity']
            running_max = equity_series.expanding().max()
            drawdown = running_max - equity_series
            
            lake_ratio = np.sum(drawdown) / (len(equity_series) * equity_series.iloc[-1])
            return lake_ratio
        except:
            return 0.0
    
    def _get_drawdown_series(self, equity_df: pd.DataFrame) -> List[float]:
        """Obtiene serie de drawdowns"""
        try:
            if equity_df.empty or 'equity' not in equity_df.columns:
                return []
            
            equity_series = equity_df['equity']
            running_max = equity_series.expanding().max()
            drawdown_pct = ((equity_series - running_max) / running_max) * 100
            
            return drawdown_pct.tolist()
        except:
            return []
    
    def _calculate_kappa_three(self, returns: pd.Series) -> float:
        """Calcula Kappa Three (downside risk measure)"""
        try:
            if len(returns) < 10:
                return 0.0
            
            target_return = 0.0  # Threshold return
            downside_returns = returns[returns < target_return]
            
            if len(downside_returns) == 0:
                return float('inf')
            
            downside_deviation = np.sqrt(np.mean((downside_returns - target_return) ** 3))
            excess_return = returns.mean() - target_return
            
            kappa_three = excess_return / downside_deviation if downside_deviation != 0 else 0
            return kappa_three
        except:
            return 0.0
    
    def _calculate_omega_ratio(self, returns: pd.Series, threshold: float = 0.0) -> float:
        """Calcula el Omega Ratio"""
        try:
            if len(returns) < 10:
                return 1.0
            
            gains = returns[returns > threshold].sum()
            losses = abs(returns[returns <= threshold].sum())
            
            omega_ratio = gains / losses if losses > 0 else float('inf')
            return omega_ratio
        except:
            return 1.0
    
    def _calculate_conditional_drawdown_risk(self, equity_df: pd.DataFrame) -> float:
        """Calcula el Conditional Drawdown Risk"""
        try:
            if equity_df.empty or 'equity' not in equity_df.columns:
                return 0.0
            
            equity_series = equity_df['equity']
            running_max = equity_series.expanding().max()
            drawdown_pct = ((equity_series - running_max) / running_max) * 100
            
            # CDR es el promedio del 5% peor de los drawdowns
            worst_5_percent = np.percentile(drawdown_pct, 5)
            conditional_drawdown = drawdown_pct[drawdown_pct <= worst_5_percent].mean()
            
            return abs(conditional_drawdown)
        except:
            return 0.0
    
    def _calculate_max_adverse_excursion(self) -> float:
        """Calcula Maximum Adverse Excursion"""
        try:
            if not self.trades:
                return 0.0
            
            max_adverse = 0.0
            for trade in self.trades:
                if hasattr(trade, 'max_adverse_excursion'):
                    max_adverse = max(max_adverse, abs(trade.max_adverse_excursion))
            
            return max_adverse
        except:
            return 0.0
    
    def _calculate_capture_ratios(self, portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> tuple:
        """Calcula Up/Down Capture Ratios"""
        try:
            if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) < 10:
                return 1.0, 1.0
            
            # Up Capture Ratio
            up_periods = benchmark_returns > 0
            if up_periods.sum() > 0:
                up_capture = portfolio_returns[up_periods].mean() / benchmark_returns[up_periods].mean()
            else:
                up_capture = 1.0
            
            # Down Capture Ratio
            down_periods = benchmark_returns < 0
            if down_periods.sum() > 0:
                down_capture = portfolio_returns[down_periods].mean() / benchmark_returns[down_periods].mean()
            else:
                down_capture = 1.0
            
            return up_capture, down_capture
        except:
            return 1.0, 1.0
    
    def _calculate_return_stability(self, returns: pd.Series) -> float:
        """Calcula la estabilidad de retornos"""
        try:
            if len(returns) < 12:
                return 0.0
            
            # Calculamos retornos mensuales
            monthly_returns = returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
            
            if len(monthly_returns) < 3:
                return 0.0
            
            # Estabilidad como inverso del coeficiente de variación
            mean_return = monthly_returns.mean()
            std_return = monthly_returns.std()
            
            if mean_return != 0 and std_return != 0:
                cv = abs(std_return / mean_return)
                stability = 1 / (1 + cv)
            else:
                stability = 0.0
            
            return stability
        except:
            return 0.0
    
    def _calculate_sharpe_stability(self, returns: pd.Series) -> float:
        """Calcula la estabilidad del Sharpe Ratio"""
        try:
            if len(returns) < 60:  # Necesitamos al menos 60 días
                return 0.0
            
            # Calculamos Sharpe rolling de 30 días
            rolling_sharpe = []
            for i in range(30, len(returns)):
                period_returns = returns.iloc[i-30:i]
                if len(period_returns) > 0 and period_returns.std() != 0:
                    sharpe = (period_returns.mean() - self.risk_free_rate/252) / period_returns.std()
                    rolling_sharpe.append(sharpe)
            
            if len(rolling_sharpe) < 3:
                return 0.0
            
            # Estabilidad como inverso de la desviación estándar del Sharpe rolling
            sharpe_std = np.std(rolling_sharpe)
            stability = 1 / (1 + sharpe_std) if sharpe_std > 0 else 1.0
            
            return stability
        except:
            return 0.0
    
    def _calculate_performance_consistency(self, returns: pd.Series) -> float:
        """Calcula la consistencia de performance"""
        try:
            if len(returns) < 30:
                return 0.0
            
            # Porcentaje de períodos positivos
            positive_periods = (returns > 0).sum()
            total_periods = len(returns)
            
            consistency = positive_periods / total_periods
            return consistency
        except:
            return 0.0
    
    def _calculate_rolling_sharpe_std(self, returns: pd.Series) -> float:
        """Calcula la desviación estándar del Sharpe Ratio rolling"""
        try:
            if len(returns) < 60:
                return 0.0
            
            rolling_sharpe = []
            for i in range(30, len(returns)):
                period_returns = returns.iloc[i-30:i]
                if len(period_returns) > 0 and period_returns.std() != 0:
                    sharpe = (period_returns.mean() - self.risk_free_rate/252) / period_returns.std()
                    rolling_sharpe.append(sharpe)
            
            if len(rolling_sharpe) < 3:
                return 0.0
            
            return np.std(rolling_sharpe)
        except:
            return 0.0
    
    def _get_all_positions(self) -> List[Position]:
        """Obtiene todas las posiciones"""
        # Simplificado - retorna lista vacía
        return []
    
    def _analyze_drawdown_periods(self) -> List[DrawdownPeriod]:
        """Analiza períodos de drawdown"""
        # Simplificado - retorna lista vacía
        return []
    
    def _calculate_daily_returns(self) -> pd.Series:
        """Calcula retornos diarios"""
        try:
            if not self.equity_history:
                return pd.Series()
            
            df = pd.DataFrame(self.equity_history)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
            
            return df['equity'].pct_change().dropna()
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando retornos diarios: {e}")
            return pd.Series()
    
    def _calculate_monthly_returns(self) -> pd.Series:
        """Calcula retornos mensuales"""
        try:
            daily_returns = self._calculate_daily_returns()
            if daily_returns.empty:
                return pd.Series()
            
            # Resample a mensual
            monthly_returns = (1 + daily_returns).resample('M').prod() - 1
            
            return monthly_returns
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando retornos mensuales: {e}")
            return pd.Series()
    
    def _log_summary(self, metrics: BacktestMetrics, advanced_metrics: AdvancedMetrics = None):
        """Log resumen de métricas"""
        self.logger.info("📊 RESUMEN DEL BACKTEST:")
        self.logger.info(f"   💰 Retorno Total: {metrics.total_return:.2%}")
        self.logger.info(f"   📈 Retorno Anualizado: {metrics.annualized_return:.2%}")
        self.logger.info(f"   📉 Máximo Drawdown: {metrics.max_drawdown:.2%}")
        self.logger.info(f"   ⚡ Ratio Sharpe: {metrics.sharpe_ratio:.3f}")
        self.logger.info(f"   🎯 Tasa de Acierto: {metrics.win_rate:.2%}")
        self.logger.info(f"   🔄 Total Trades: {metrics.total_trades}")
        self.logger.info(f"   💸 Comisiones: ${metrics.commission_paid:.2f}")
        
        if advanced_metrics:
            self._log_advanced_metrics(advanced_metrics)
    
    def _log_advanced_metrics(self, advanced_metrics: AdvancedMetrics):
        """Log métricas avanzadas"""
        self.logger.info("\n🔬 MÉTRICAS AVANZADAS:")
        
        # Métricas de retorno ajustadas por riesgo
        self.logger.info("   📊 Retorno Ajustado por Riesgo:")
        self.logger.info(f"      🎯 Treynor Ratio: {advanced_metrics.treynor_ratio:.3f}")
        self.logger.info(f"      🏆 Jensen's Alpha: {advanced_metrics.jensen_alpha:.3f}")
        self.logger.info(f"      📈 Information Ratio: {advanced_metrics.information_ratio:.3f}")
        self.logger.info(f"      🎪 Modigliani Ratio: {advanced_metrics.modigliani_ratio:.3f}")
        
        # Métricas de drawdown avanzadas
        self.logger.info("   📉 Análisis de Drawdown Avanzado:")
        self.logger.info(f"      🩹 Ulcer Index: {advanced_metrics.ulcer_index:.3f}")
        self.logger.info(f"      😣 Pain Index: {advanced_metrics.pain_index:.3f}")
        self.logger.info(f"      🏞️ Lake Ratio: {advanced_metrics.lake_ratio:.3f}")
        self.logger.info(f"      🏗️ Burke Ratio: {advanced_metrics.burke_ratio:.3f}")
        
        # Métricas de consistencia
        self.logger.info("   🎯 Consistencia:")
        self.logger.info(f"      💪 Gain to Pain Ratio: {advanced_metrics.gain_to_pain_ratio:.3f}")
        self.logger.info(f"      🥈 Sterling Ratio: {advanced_metrics.sterling_ratio:.3f}")
        self.logger.info(f"      🔥 Omega Ratio: {advanced_metrics.omega_ratio:.3f}")
        self.logger.info(f"      🎭 Batting Average: {advanced_metrics.batting_average:.2%}")
        
        # Métricas de tail risk
        self.logger.info("   ⚠️ Riesgo de Cola:")
        self.logger.info(f"      🎢 Tail Ratio: {advanced_metrics.tail_ratio:.3f}")
        self.logger.info(f"      💥 Expected Shortfall Ratio: {advanced_metrics.expected_shortfall_ratio:.3f}")
        self.logger.info(f"      🌊 Conditional Drawdown Risk: {advanced_metrics.conditional_drawdown_risk:.3f}")
        
        # Métricas de timing
        self.logger.info("   ⏰ Timing:")
        self.logger.info(f"      📈 Up Capture Ratio: {advanced_metrics.up_capture_ratio:.2%}")
        self.logger.info(f"      📉 Down Capture Ratio: {advanced_metrics.down_capture_ratio:.2%}")
        self.logger.info(f"      ⚖️ Capture Ratio: {advanced_metrics.capture_ratio:.3f}")
        
        # Métricas de estabilidad
        self.logger.info("   🏛️ Estabilidad:")
        self.logger.info(f"      🔒 Return Stability: {advanced_metrics.return_stability:.3f}")
        self.logger.info(f"      📊 Sharpe Stability: {advanced_metrics.sharpe_stability:.3f}")
        self.logger.info(f"      🎯 Performance Consistency: {advanced_metrics.performance_consistency:.2%}")
    
    def run_backtest(self, strategy_func: Callable, start_date: datetime, 
                    end_date: datetime) -> BacktestResult:
        """Ejecuta el backtest con una estrategia dada"""
        try:
            self.logger.info(f"🚀 Iniciando backtest desde {start_date} hasta {end_date}")
            
            # Resetear estado
            self.current_capital = self.initial_capital
            self.current_positions = {}
            self.closed_positions = []
            self.all_trades = []
            self.all_orders = []
            self.equity_history = []
            self.drawdown_history = []
            self.peak_equity = self.initial_capital
            
            # Obtener timestamps únicos de todos los símbolos
            all_timestamps = set()
            for symbol, data in self.market_data.items():
                symbol_timestamps = data[
                    (data['timestamp'] >= start_date) & 
                    (data['timestamp'] <= end_date)
                ]['timestamp']
                all_timestamps.update(symbol_timestamps)
            
            timestamps = sorted(list(all_timestamps))
            
            if not timestamps:
                raise ValueError("No hay datos en el rango de fechas especificado")
            
            self.logger.info(f"📊 Procesando {len(timestamps)} períodos de tiempo")
            
            # Iterar por cada timestamp
            for i, timestamp in enumerate(timestamps):
                self.current_timestamp = timestamp
                
                # Actualizar precios actuales
                self.current_prices = {}
                for symbol, data in self.market_data.items():
                    symbol_data = data[data['timestamp'] == timestamp]
                    if not symbol_data.empty:
                        self.current_prices[symbol] = symbol_data.iloc[0]['close']
                
                # Ejecutar órdenes pendientes
                for order in self.all_orders:
                    if order.status == "pending":
                        self._execute_order(order)
                
                # Ejecutar estrategia
                try:
                    # Preparar datos para la estrategia
                    strategy_data = {}
                    for symbol, data in self.market_data.items():
                        # Datos hasta el timestamp actual
                        historical_data = data[data['timestamp'] <= timestamp]
                        if not historical_data.empty:
                            strategy_data[symbol] = historical_data
                    
                    # Llamar a la estrategia
                    if strategy_data:
                        orders = strategy_func(self, strategy_data, timestamp)
                        
                        # Procesar órdenes devueltas por la estrategia
                        if orders:
                            for order in orders:
                                self._process_order(order, timestamp)
                        
                except Exception as e:
                    self.logger.warning(f"⚠️ Error en estrategia en {timestamp}: {e}")
                
                # Actualizar posiciones
                self._update_positions()
                
                # Progreso cada 10%
                if i % max(1, len(timestamps) // 10) == 0:
                    progress = (i / len(timestamps)) * 100
                    self.logger.info(f"📈 Progreso: {progress:.1f}%")
            
            # Calcular métricas finales
            metrics = self._calculate_metrics()
            
            # Calcular métricas avanzadas
            equity_curve = self._create_equity_curve()
            daily_returns = self._calculate_daily_returns()
            advanced_metrics = self._calculate_advanced_metrics(daily_returns, equity_curve, metrics)
            
            # Crear resultado
            result = BacktestResult(
                metrics=metrics,
                equity_curve=equity_curve,
                trades=self.all_trades.copy(),
                positions=self._get_all_positions(),
                drawdown_periods=self._analyze_drawdown_periods(),
                daily_returns=daily_returns,
                monthly_returns=self._calculate_monthly_returns(),
                advanced_metrics=advanced_metrics,
                success=True,
                message="Backtest completado exitosamente"
            )
            
            self.logger.info("✅ Backtest completado exitosamente")
            self._log_summary(metrics, advanced_metrics)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error en backtest: {e}")
            return BacktestResult(
                metrics=BacktestMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, datetime.now(), datetime.now(), 0, 0),
                equity_curve=pd.DataFrame(),
                trades=[],
                positions=[],
                drawdown_periods=[],
                daily_returns=pd.Series(),
                monthly_returns=pd.Series(),
                success=False,
                message=f"Error en backtest: {e}"
            )
    
    def run_cpcv(self, strategy_func: Callable, start_date: datetime, 
                 end_date: datetime, config: CPCVConfig = None) -> CPCVResult:
        """
        Ejecuta Combinatorial Purged Cross-Validation
        
        Args:
            strategy_func: Función de estrategia a validar
            start_date: Fecha de inicio
            end_date: Fecha de fin
            config: Configuración CPCV
            
        Returns:
            CPCVResult: Resultados de la validación cruzada
        """
        if config is None:
            config = CPCVConfig()
            
        self.logger.info("🔬 Iniciando Combinatorial Purged Cross-Validation (CPCV)")
        self.logger.info(f"📊 Configuración: {config.n_splits} splits, {config.n_combinations} combinaciones")
        
        try:
            # Generar splits temporales con purga
            splits = self._generate_purged_splits(start_date, end_date, config)
            
            # Generar combinaciones de splits para entrenamiento/test
            combinations_list = self._generate_split_combinations(splits, config)
            
            # Ejecutar validación cruzada
            if config.parallel_execution:
                fold_results = self._run_cpcv_parallel(strategy_func, combinations_list, config)
            else:
                fold_results = self._run_cpcv_sequential(strategy_func, combinations_list, config)
            
            # Calcular métricas agregadas
            cpcv_result = self._calculate_cpcv_metrics(fold_results, config)
            
            self.logger.info("✅ CPCV completado exitosamente")
            self._log_cpcv_summary(cpcv_result)
            
            return cpcv_result
            
        except Exception as e:
            self.logger.error(f"❌ Error en CPCV: {e}")
            raise
    
    def _generate_purged_splits(self, start_date: datetime, end_date: datetime, 
                               config: CPCVConfig) -> List[Tuple[datetime, datetime]]:
        """Genera splits temporales con purga entre entrenamiento y test"""
        
        # Obtener todas las fechas disponibles
        all_dates = set()
        for symbol_data in self.market_data.values():
            symbol_dates = symbol_data[
                (symbol_data['timestamp'] >= start_date) & 
                (symbol_data['timestamp'] <= end_date)
            ]['timestamp']
            all_dates.update(symbol_dates)
        
        dates = sorted(list(all_dates))
        total_days = len(dates)
        
        if total_days < config.min_train_length + config.min_test_length:
            raise ValueError(f"Datos insuficientes: {total_days} días, mínimo requerido: {config.min_train_length + config.min_test_length}")
        
        # Calcular tamaños de splits
        test_size = max(config.min_test_length, total_days // (config.n_splits + 1))
        purge_size = max(1, int(total_days * config.purge_pct))
        embargo_size = max(1, int(total_days * config.embargo_pct))
        
        splits = []
        
        for i in range(config.n_splits):
            # Calcular índices para este split
            test_start_idx = i * (test_size + purge_size + embargo_size)
            test_end_idx = test_start_idx + test_size
            
            if test_end_idx >= total_days:
                break
                
            # Fechas de test
            test_start = dates[test_start_idx]
            test_end = dates[min(test_end_idx, total_days - 1)]
            
            # Fechas de entrenamiento (antes del test, con purga)
            train_end_idx = max(0, test_start_idx - purge_size)
            train_start_idx = max(0, train_end_idx - config.min_train_length)
            
            if train_start_idx < train_end_idx:
                train_start = dates[train_start_idx]
                train_end = dates[train_end_idx]
                
                splits.append({
                    'train_start': train_start,
                    'train_end': train_end,
                    'test_start': test_start,
                    'test_end': test_end,
                    'split_id': i
                })
        
        self.logger.info(f"📅 Generados {len(splits)} splits temporales con purga")
        return splits
    
    def _generate_split_combinations(self, splits: List[Dict], config: CPCVConfig) -> List[Dict]:
        """Genera combinaciones de splits para CPCV"""
        
        if len(splits) < 2:
            raise ValueError("Se necesitan al menos 2 splits para CPCV")
        
        # Generar todas las combinaciones posibles de splits
        all_combinations = []
        
        # Combinaciones de diferentes tamaños (2 a n_splits)
        for combo_size in range(2, min(len(splits) + 1, config.n_combinations + 1)):
            for combo in combinations(range(len(splits)), combo_size):
                train_splits = [splits[i] for i in combo[:-1]]  # Todos menos el último para entrenamiento
                test_split = splits[combo[-1]]  # Último para test
                
                all_combinations.append({
                    'train_splits': train_splits,
                    'test_split': test_split,
                    'combo_id': len(all_combinations)
                })
        
        # Limitar número de combinaciones si es necesario
        if len(all_combinations) > config.n_combinations:
            # Seleccionar combinaciones de manera distribuida
            step = len(all_combinations) // config.n_combinations
            all_combinations = all_combinations[::step][:config.n_combinations]
        
        self.logger.info(f"🔄 Generadas {len(all_combinations)} combinaciones de splits")
        return all_combinations
    
    def _run_cpcv_parallel(self, strategy_func: Callable, combinations: List[Dict], 
                          config: CPCVConfig) -> List[BacktestResult]:
        """Ejecuta CPCV en paralelo"""
        
        fold_results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # Enviar tareas
            future_to_combo = {
                executor.submit(self._run_single_fold, strategy_func, combo, config): combo
                for combo in combinations
            }
            
            # Recoger resultados
            for future in concurrent.futures.as_completed(future_to_combo):
                combo = future_to_combo[future]
                try:
                    result = future.result()
                    if result.success:
                        fold_results.append(result)
                        self.logger.info(f"✅ Fold {combo['combo_id']} completado: Sharpe={result.metrics.sharpe_ratio:.3f}")
                    else:
                        self.logger.warning(f"⚠️ Fold {combo['combo_id']} falló: {result.message}")
                except Exception as e:
                    self.logger.error(f"❌ Error en fold {combo['combo_id']}: {e}")
        
        return fold_results
    
    def _run_cpcv_sequential(self, strategy_func: Callable, combinations: List[Dict], 
                            config: CPCVConfig) -> List[BacktestResult]:
        """Ejecuta CPCV secuencialmente"""
        
        fold_results = []
        
        for combo in combinations:
            try:
                result = self._run_single_fold(strategy_func, combo, config)
                if result.success:
                    fold_results.append(result)
                    self.logger.info(f"✅ Fold {combo['combo_id']} completado: Sharpe={result.metrics.sharpe_ratio:.3f}")
                else:
                    self.logger.warning(f"⚠️ Fold {combo['combo_id']} falló: {result.message}")
            except Exception as e:
                self.logger.error(f"❌ Error en fold {combo['combo_id']}: {e}")
        
        return fold_results
    
    def _run_single_fold(self, strategy_func: Callable, combination: Dict, 
                        config: CPCVConfig) -> BacktestResult:
        """Ejecuta un solo fold de CPCV"""
        
        with self._lock:  # Asegurar acceso thread-safe
            # Crear una nueva instancia del backtester para este fold
            fold_backtester = AdvancedBacktester(self.initial_capital, self.commission_rate)
            fold_backtester.load_market_data(self.market_data)
        
        # Ejecutar backtest en el período de test
        test_split = combination['test_split']
        result = fold_backtester.run_backtest(
            strategy_func,
            test_split['test_start'],
            test_split['test_end']
        )
        
        # Agregar información del fold
        if hasattr(result, 'fold_info'):
            result.fold_info = {
                'combo_id': combination['combo_id'],
                'test_period': (test_split['test_start'], test_split['test_end']),
                'train_periods': [(ts['train_start'], ts['train_end']) for ts in combination['train_splits']]
            }
        
        return result
    
    def _calculate_cpcv_metrics(self, fold_results: List[BacktestResult], 
                               config: CPCVConfig) -> CPCVResult:
        """Calcula métricas agregadas de CPCV"""
        
        if not fold_results:
            raise ValueError("No hay resultados válidos de folds")
        
        # Extraer métricas de cada fold
        returns = [r.metrics.total_return for r in fold_results]
        sharpes = [r.metrics.sharpe_ratio for r in fold_results]
        max_drawdowns = [r.metrics.max_drawdown for r in fold_results]
        win_rates = [r.metrics.win_rate for r in fold_results]
        
        # Calcular estadísticas
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        mean_sharpe = np.mean(sharpes)
        std_sharpe = np.std(sharpes)
        mean_max_drawdown = np.mean(max_drawdowns)
        std_max_drawdown = np.std(max_drawdowns)
        avg_win_rate = np.mean(win_rates)
        
        # Calcular intervalo de confianza para retornos
        alpha = 1 - config.confidence_level
        t_critical = 1.96  # Aproximación para 95% de confianza
        margin_error = t_critical * (std_return / np.sqrt(len(returns)))
        confidence_interval = (mean_return - margin_error, mean_return + margin_error)
        
        # Calcular score de robustez (basado en consistencia de resultados)
        sharpe_cv = abs(std_sharpe / mean_sharpe) if mean_sharpe != 0 else float('inf')
        return_cv = abs(std_return / mean_return) if mean_return != 0 else float('inf')
        
        # Score de robustez: menor variabilidad = mayor robustez
        robustness_score = max(0, 1 - (sharpe_cv + return_cv) / 2)
        
        return CPCVResult(
            mean_return=mean_return,
            std_return=std_return,
            mean_sharpe=mean_sharpe,
            std_sharpe=std_sharpe,
            mean_max_drawdown=mean_max_drawdown,
            std_max_drawdown=std_max_drawdown,
            win_rate=avg_win_rate,
            total_folds=len(fold_results),
            successful_folds=len(fold_results),
            fold_results=fold_results,
            confidence_interval_95=confidence_interval,
            robustness_score=robustness_score
        )
    
    def _log_cpcv_summary(self, result: CPCVResult):
        """Log resumen de resultados CPCV"""
        
        self.logger.info("=" * 60)
        self.logger.info("📊 RESUMEN COMBINATORIAL PURGED CROSS-VALIDATION")
        self.logger.info("=" * 60)
        self.logger.info(f"🎯 Folds Exitosos: {result.successful_folds}/{result.total_folds}")
        self.logger.info(f"📈 Retorno Promedio: {result.mean_return:.2%} ± {result.std_return:.2%}")
        self.logger.info(f"⚡ Sharpe Promedio: {result.mean_sharpe:.3f} ± {result.std_sharpe:.3f}")
        self.logger.info(f"📉 Max Drawdown Promedio: {result.mean_max_drawdown:.2%} ± {result.std_max_drawdown:.2%}")
        self.logger.info(f"🎲 Tasa de Acierto: {result.win_rate:.2%}")
        self.logger.info(f"🔒 Intervalo Confianza 95%: [{result.confidence_interval_95[0]:.2%}, {result.confidence_interval_95[1]:.2%}]")
        self.logger.info(f"🛡️ Score de Robustez: {result.robustness_score:.3f}")
        
        # Interpretación del score de robustez
        if result.robustness_score > 0.8:
            self.logger.info("✅ Estrategia MUY ROBUSTA - Resultados consistentes")
        elif result.robustness_score > 0.6:
            self.logger.info("🟡 Estrategia MODERADAMENTE ROBUSTA - Algunos resultados variables")
        else:
            self.logger.info("🔴 Estrategia POCO ROBUSTA - Resultados muy variables")
        
        self.logger.info("=" * 60)

@dataclass
class WalkForwardConfig:
    """Configuración para Walk-Forward Analysis"""
    training_window: int = 252  # Días de entrenamiento (1 año)
    testing_window: int = 63   # Días de testing (3 meses)
    step_size: int = 21        # Días de avance (3 semanas)
    min_training_samples: int = 100  # Mínimo de muestras para entrenar
    reoptimization_frequency: int = 1  # Cada cuántos pasos reoptimizar
    parallel_execution: bool = True
    confidence_level: float = 0.95

@dataclass
class WalkForwardPeriod:
    """Período individual de walk-forward"""
    period_id: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    train_samples: int
    test_samples: int
    backtest_result: Optional[BacktestResult] = None
    optimization_params: Optional[Dict] = None
    is_reoptimized: bool = False

@dataclass
class WalkForwardResult:
    """Resultado completo del Walk-Forward Analysis"""
    periods: List[WalkForwardPeriod]
    aggregated_metrics: BacktestMetrics
    period_metrics: List[BacktestMetrics]
    stability_metrics: Dict[str, float]
    degradation_analysis: Dict[str, float]
    equity_curve: pd.DataFrame
    out_of_sample_performance: Dict[str, float]
    robustness_score: float
    total_periods: int
    successful_periods: int
    config: WalkForwardConfig

class WalkForwardAnalyzer:
    """
    Analizador de Walk-Forward para validación robusta de estrategias
    """
    
    def __init__(self, backtester: AdvancedBacktester):
        self.backtester = backtester
        self.logger = logging.getLogger(__name__)
        
    def run_walk_forward_analysis(self, 
                                strategy_func: Callable,
                                optimization_func: Optional[Callable] = None,
                                config: Optional[WalkForwardConfig] = None) -> WalkForwardResult:
        """
        Ejecuta Walk-Forward Analysis completo
        
        Args:
            strategy_func: Función de estrategia a probar
            optimization_func: Función opcional para optimizar parámetros
            config: Configuración del análisis
        """
        if config is None:
            config = WalkForwardConfig()
            
        try:
            self.logger.info("🚀 Iniciando Walk-Forward Analysis")
            
            # Generar períodos de análisis
            periods = self._generate_walk_forward_periods(config)
            
            if not periods:
                raise ValueError("No se pudieron generar períodos válidos para el análisis")
            
            self.logger.info(f"📊 Generados {len(periods)} períodos para análisis")
            
            # Ejecutar análisis por períodos
            if config.parallel_execution:
                results = self._run_parallel_analysis(periods, strategy_func, optimization_func, config)
            else:
                results = self._run_sequential_analysis(periods, strategy_func, optimization_func, config)
            
            # Agregar resultados a los períodos
            for i, result in enumerate(results):
                if i < len(periods):
                    periods[i].backtest_result = result
            
            # Calcular métricas agregadas
            aggregated_metrics = self._calculate_aggregated_metrics(periods)
            period_metrics = [p.backtest_result.metrics for p in periods if p.backtest_result and p.backtest_result.success]
            
            # Análisis de estabilidad y degradación
            stability_metrics = self._analyze_stability(period_metrics)
            degradation_analysis = self._analyze_degradation(period_metrics)
            
            # Crear curva de equity combinada
            equity_curve = self._create_combined_equity_curve(periods)
            
            # Análisis out-of-sample
            oos_performance = self._analyze_out_of_sample_performance(period_metrics)
            
            # Calcular score de robustez
            robustness_score = self._calculate_robustness_score(period_metrics, stability_metrics)
            
            successful_periods = sum(1 for p in periods if p.backtest_result and p.backtest_result.success)
            
            result = WalkForwardResult(
                periods=periods,
                aggregated_metrics=aggregated_metrics,
                period_metrics=period_metrics,
                stability_metrics=stability_metrics,
                degradation_analysis=degradation_analysis,
                equity_curve=equity_curve,
                out_of_sample_performance=oos_performance,
                robustness_score=robustness_score,
                total_periods=len(periods),
                successful_periods=successful_periods,
                config=config
            )
            
            self.logger.info("✅ Walk-Forward Analysis completado exitosamente")
            self._log_walk_forward_summary(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error en Walk-Forward Analysis: {e}")
            raise
    
    def _generate_walk_forward_periods(self, config: WalkForwardConfig) -> List[WalkForwardPeriod]:
        """Genera los períodos de entrenamiento y testing"""
        periods = []
        
        # Obtener rango de fechas de todos los datos
        all_timestamps = []
        for symbol, data in self.backtester.market_data.items():
            all_timestamps.extend(data['timestamp'].tolist())
        
        if not all_timestamps:
            return periods
        
        start_date = min(all_timestamps)
        end_date = max(all_timestamps)
        
        current_start = start_date
        period_id = 0
        
        while current_start + timedelta(days=config.training_window + config.testing_window) <= end_date:
            train_start = current_start
            train_end = current_start + timedelta(days=config.training_window)
            test_start = train_end
            test_end = test_start + timedelta(days=config.testing_window)
            
            # Contar muestras disponibles
            train_samples = self._count_samples_in_period(train_start, train_end)
            test_samples = self._count_samples_in_period(test_start, test_end)
            
            if train_samples >= config.min_training_samples and test_samples > 0:
                period = WalkForwardPeriod(
                    period_id=period_id,
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end,
                    train_samples=train_samples,
                    test_samples=test_samples,
                    is_reoptimized=(period_id % config.reoptimization_frequency == 0)
                )
                periods.append(period)
                period_id += 1
            
            current_start += timedelta(days=config.step_size)
        
        return periods
    
    def _count_samples_in_period(self, start_date: datetime, end_date: datetime) -> int:
        """Cuenta las muestras disponibles en un período"""
        total_samples = 0
        for symbol, data in self.backtester.market_data.items():
            mask = (data['timestamp'] >= start_date) & (data['timestamp'] <= end_date)
            total_samples += mask.sum()
        return total_samples
    
    def _run_sequential_analysis(self, periods: List[WalkForwardPeriod], 
                               strategy_func: Callable,
                               optimization_func: Optional[Callable],
                               config: WalkForwardConfig) -> List[BacktestResult]:
        """Ejecuta el análisis secuencialmente"""
        results = []
        
        for i, period in enumerate(periods):
            self.logger.info(f"📈 Procesando período {i+1}/{len(periods)}")
            
            try:
                # Optimizar parámetros si es necesario
                if optimization_func and period.is_reoptimized:
                    optimal_params = optimization_func(
                        self.backtester, 
                        period.train_start, 
                        period.train_end
                    )
                    period.optimization_params = optimal_params
                
                # Ejecutar backtest en período de testing
                result = self.backtester.run_backtest(
                    strategy_func, 
                    period.test_start, 
                    period.test_end
                )
                
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"❌ Error en período {i+1}: {e}")
                # Crear resultado fallido
                failed_result = BacktestResult(
                    metrics=BacktestMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, datetime.now(), datetime.now(), 0, 0),
                    equity_curve=pd.DataFrame(),
                    trades=[],
                    positions=[],
                    drawdown_periods=[],
                    daily_returns=pd.Series(),
                    monthly_returns=pd.Series(),
                    success=False,
                    message=f"Error en período: {e}"
                )
                results.append(failed_result)
        
        return results
    
    def _run_parallel_analysis(self, periods: List[WalkForwardPeriod],
                             strategy_func: Callable,
                             optimization_func: Optional[Callable],
                             config: WalkForwardConfig) -> List[BacktestResult]:
        """Ejecuta el análisis en paralelo"""
        results = []
        
        def process_period(period):
            try:
                # Crear una copia del backtester para thread safety
                period_backtester = AdvancedBacktester(
                    initial_capital=self.backtester.initial_capital,
                    commission_rate=self.backtester.commission_rate
                )
                
                # Copiar datos de mercado
                for symbol, data in self.backtester.market_data.items():
                    period_backtester.add_market_data(symbol, data)
                
                # Optimizar parámetros si es necesario
                if optimization_func and period.is_reoptimized:
                    optimal_params = optimization_func(
                        period_backtester,
                        period.train_start,
                        period.train_end
                    )
                    period.optimization_params = optimal_params
                
                # Ejecutar backtest
                result = period_backtester.run_backtest(
                    strategy_func,
                    period.test_start,
                    period.test_end
                )
                
                return result
                
            except Exception as e:
                self.logger.error(f"❌ Error en período paralelo: {e}")
                return BacktestResult(
                    metrics=BacktestMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, datetime.now(), datetime.now(), 0, 0),
                    equity_curve=pd.DataFrame(),
                    trades=[],
                    positions=[],
                    drawdown_periods=[],
                    daily_returns=pd.Series(),
                    monthly_returns=pd.Series(),
                    success=False,
                    message=f"Error en período: {e}"
                )
        
        # Ejecutar en paralelo
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_period = {executor.submit(process_period, period): period for period in periods}
            
            for future in concurrent.futures.as_completed(future_to_period):
                result = future.result()
                results.append(result)
        
        return results
    
    def _calculate_aggregated_metrics(self, periods: List[WalkForwardPeriod]) -> BacktestMetrics:
        """Calcula métricas agregadas de todos los períodos"""
        successful_periods = [p for p in periods if p.backtest_result and p.backtest_result.success]
        
        if not successful_periods:
            return BacktestMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, datetime.now(), datetime.now(), 0, 0)
        
        # Combinar todas las métricas
        all_returns = [p.backtest_result.metrics.total_return for p in successful_periods]
        all_sharpe = [p.backtest_result.metrics.sharpe_ratio for p in successful_periods]
        all_drawdowns = [p.backtest_result.metrics.max_drawdown for p in successful_periods]
        all_win_rates = [p.backtest_result.metrics.win_rate for p in successful_periods]
        
        # Calcular promedios y agregados
        total_return = np.prod([1 + r for r in all_returns]) - 1
        avg_sharpe = np.mean(all_sharpe)
        max_drawdown = max(all_drawdowns) if all_drawdowns else 0
        avg_win_rate = np.mean(all_win_rates)
        
        # Calcular retorno anualizado basado en el período total
        start_date = min(p.test_start for p in successful_periods)
        end_date = max(p.test_end for p in successful_periods)
        total_days = (end_date - start_date).days
        annualized_return = (1 + total_return) ** (365 / total_days) - 1 if total_days > 0 else 0
        
        return BacktestMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=np.std(all_returns) * np.sqrt(252),
            sharpe_ratio=avg_sharpe,
            sortino_ratio=np.mean([p.backtest_result.metrics.sortino_ratio for p in successful_periods]),
            calmar_ratio=annualized_return / max_drawdown if max_drawdown > 0 else 0,
            max_drawdown=max_drawdown,
            avg_drawdown=np.mean(all_drawdowns),
            max_drawdown_duration=max([p.backtest_result.metrics.max_drawdown_duration for p in successful_periods], default=0),
            avg_drawdown_duration=np.mean([p.backtest_result.metrics.avg_drawdown_duration for p in successful_periods]),
            recovery_factor=total_return / max_drawdown if max_drawdown > 0 else 0,
            total_trades=sum(p.backtest_result.metrics.total_trades for p in successful_periods),
            winning_trades=sum(p.backtest_result.metrics.winning_trades for p in successful_periods),
            losing_trades=sum(p.backtest_result.metrics.losing_trades for p in successful_periods),
            win_rate=avg_win_rate,
            avg_win=np.mean([p.backtest_result.metrics.avg_win for p in successful_periods]),
            avg_loss=np.mean([p.backtest_result.metrics.avg_loss for p in successful_periods]),
            profit_factor=np.mean([p.backtest_result.metrics.profit_factor for p in successful_periods]),
            var_95=np.mean([p.backtest_result.metrics.var_95 for p in successful_periods]),
            cvar_95=np.mean([p.backtest_result.metrics.cvar_95 for p in successful_periods]),
            beta=0,  # Simplificado
            alpha=0,  # Simplificado
            information_ratio=0,  # Simplificado
            start_date=start_date,
            end_date=end_date,
            trading_days=total_days,
            commission_paid=sum(p.backtest_result.metrics.commission_paid for p in successful_periods)
        )
    
    def _analyze_stability(self, period_metrics: List[BacktestMetrics]) -> Dict[str, float]:
        """Analiza la estabilidad de las métricas a través de los períodos"""
        if not period_metrics:
            return {}
        
        returns = [m.total_return for m in period_metrics]
        sharpe_ratios = [m.sharpe_ratio for m in period_metrics]
        drawdowns = [m.max_drawdown for m in period_metrics]
        win_rates = [m.win_rate for m in period_metrics]
        
        return {
            'return_stability': 1 - (np.std(returns) / (np.mean(returns) + 1e-8)),
            'sharpe_stability': 1 - (np.std(sharpe_ratios) / (np.mean(sharpe_ratios) + 1e-8)),
            'drawdown_stability': 1 - (np.std(drawdowns) / (np.mean(drawdowns) + 1e-8)),
            'win_rate_stability': 1 - (np.std(win_rates) / (np.mean(win_rates) + 1e-8)),
            'overall_stability': np.mean([
                1 - (np.std(returns) / (np.mean(returns) + 1e-8)),
                1 - (np.std(sharpe_ratios) / (np.mean(sharpe_ratios) + 1e-8)),
                1 - (np.std(drawdowns) / (np.mean(drawdowns) + 1e-8)),
                1 - (np.std(win_rates) / (np.mean(win_rates) + 1e-8))
            ])
        }
    
    def _analyze_degradation(self, period_metrics: List[BacktestMetrics]) -> Dict[str, float]:
        """Analiza la degradación del rendimiento a lo largo del tiempo"""
        if len(period_metrics) < 2:
            return {}
        
        # Dividir en primera y segunda mitad
        mid_point = len(period_metrics) // 2
        first_half = period_metrics[:mid_point]
        second_half = period_metrics[mid_point:]
        
        first_half_return = np.mean([m.total_return for m in first_half])
        second_half_return = np.mean([m.total_return for m in second_half])
        
        first_half_sharpe = np.mean([m.sharpe_ratio for m in first_half])
        second_half_sharpe = np.mean([m.sharpe_ratio for m in second_half])
        
        return {
            'return_degradation': (first_half_return - second_half_return) / (first_half_return + 1e-8),
            'sharpe_degradation': (first_half_sharpe - second_half_sharpe) / (first_half_sharpe + 1e-8),
            'performance_trend': np.corrcoef(range(len(period_metrics)), [m.total_return for m in period_metrics])[0, 1] if len(period_metrics) > 1 else 0
        }
    
    def _create_combined_equity_curve(self, periods: List[WalkForwardPeriod]) -> pd.DataFrame:
        """Crea una curva de equity combinada de todos los períodos"""
        combined_equity = []
        
        for period in periods:
            if period.backtest_result and period.backtest_result.success and not period.backtest_result.equity_curve.empty:
                period_equity = period.backtest_result.equity_curve.copy()
                combined_equity.append(period_equity)
        
        if combined_equity:
            return pd.concat(combined_equity, ignore_index=True).sort_values('timestamp')
        else:
            return pd.DataFrame()
    
    def _analyze_out_of_sample_performance(self, period_metrics: List[BacktestMetrics]) -> Dict[str, float]:
        """Analiza el rendimiento out-of-sample"""
        if not period_metrics:
            return {}
        
        returns = [m.total_return for m in period_metrics]
        positive_periods = sum(1 for r in returns if r > 0)
        
        return {
            'oos_hit_rate': positive_periods / len(period_metrics),
            'oos_avg_return': np.mean(returns),
            'oos_volatility': np.std(returns),
            'oos_sharpe': np.mean(returns) / (np.std(returns) + 1e-8),
            'oos_max_drawdown': max([m.max_drawdown for m in period_metrics], default=0)
        }
    
    def _calculate_robustness_score(self, period_metrics: List[BacktestMetrics], 
                                  stability_metrics: Dict[str, float]) -> float:
        """Calcula un score de robustez general (0-1)"""
        if not period_metrics or not stability_metrics:
            return 0.0
        
        # Componentes del score de robustez
        consistency_score = stability_metrics.get('overall_stability', 0)
        profitability_score = min(1.0, max(0.0, np.mean([m.total_return for m in period_metrics]) * 2))
        risk_score = max(0.0, 1.0 - np.mean([m.max_drawdown for m in period_metrics]) * 2)
        
        # Score combinado
        robustness_score = (consistency_score * 0.4 + profitability_score * 0.3 + risk_score * 0.3)
        
        return max(0.0, min(1.0, robustness_score))
    
    def _log_walk_forward_summary(self, result: WalkForwardResult):
        """Log resumen del Walk-Forward Analysis"""
        self.logger.info("📊 RESUMEN WALK-FORWARD ANALYSIS:")
        self.logger.info(f"   🔄 Períodos Totales: {result.total_periods}")
        self.logger.info(f"   ✅ Períodos Exitosos: {result.successful_periods}")
        self.logger.info(f"   💰 Retorno Agregado: {result.aggregated_metrics.total_return:.2%}")
        self.logger.info(f"   📈 Retorno Anualizado: {result.aggregated_metrics.annualized_return:.2%}")
        self.logger.info(f"   📉 Máximo Drawdown: {result.aggregated_metrics.max_drawdown:.2%}")
        self.logger.info(f"   ⚡ Ratio Sharpe Promedio: {result.aggregated_metrics.sharpe_ratio:.3f}")
        self.logger.info(f"   🎯 Tasa de Acierto Promedio: {result.aggregated_metrics.win_rate:.2%}")
        self.logger.info(f"   🔒 Score de Robustez: {result.robustness_score:.3f}")
        self.logger.info(f"   📊 Estabilidad General: {result.stability_metrics.get('overall_stability', 0):.3f}")

def test_advanced_backtester():
    """Función de prueba del sistema de backtesting avanzado"""
    print("🚀 Iniciando prueba del Sistema de Backtesting Avanzado con datos 2025...")
    
    try:
        # Crear backtester
        backtester = AdvancedBacktester(initial_capital=100000, commission_rate=0.001)
        
        # Cargar datos de mercado de 2025
        print("📊 Cargando datos de mercado 2025...")
        
        try:
            # Intentar cargar datos generados de 2025
            btc_data = pd.read_csv('data/2025/BTCUSDT_2025.csv')
            btc_data['timestamp'] = pd.to_datetime(btc_data['timestamp'])
            
            market_data = {'BTCUSDT': btc_data}
            print(f"✅ Datos de 2025 cargados: {len(btc_data)} períodos desde {btc_data['timestamp'].min()} hasta {btc_data['timestamp'].max()}")
            
        except FileNotFoundError:
            print("⚠️ Datos de 2025 no encontrados, generando datos de prueba...")
            
            # Generar datos de prueba para 2025
            dates = pd.date_range(start='2025-08-01', end='2025-10-31', freq='D')
            
            # Datos sintéticos para BTCUSDT con precios de 2025
            np.random.seed(42)
            btc_prices = []
            price = 85000  # Precio inicial más alto para 2025
            
            for _ in dates:
                change = np.random.normal(0, 0.025)  # 2.5% volatilidad diaria
                price *= (1 + change)
                btc_prices.append(price)
            
            btc_data = pd.DataFrame({
                'timestamp': dates,
                'open': btc_prices,
                'high': [p * 1.02 for p in btc_prices],
                'low': [p * 0.98 for p in btc_prices],
                'close': btc_prices,
                'volume': np.random.uniform(1000000, 5000000, len(dates))
            })
            
            market_data = {'BTCUSDT': btc_data}
        
        # Cargar datos
        backtester.load_market_data(market_data)
        
        # Estrategia simple de prueba
        def simple_strategy(backtester, data, timestamp):
            """Estrategia simple: comprar y mantener con rebalanceo mensual"""
            try:
                # Solo operar el primer día de cada mes
                if timestamp.day == 1:
                    current_equity = backtester.current_capital
                    for symbol, position in backtester.current_positions.items():
                        if symbol in backtester.current_prices:
                            current_equity += position * backtester.current_prices[symbol]
                    
                    # Invertir 50% en BTC
                    target_btc_value = current_equity * 0.5
                    current_btc_value = backtester.current_positions.get('BTCUSDT', 0) * backtester.current_prices.get('BTCUSDT', 0)
                    
                    if target_btc_value > current_btc_value * 1.1:  # Comprar más
                        buy_amount = (target_btc_value - current_btc_value) / backtester.current_prices['BTCUSDT']
                        if buy_amount > 0:
                            backtester.place_order('BTCUSDT', OrderSide.BUY, OrderType.MARKET, buy_amount)
                    
                    elif target_btc_value < current_btc_value * 0.9:  # Vender
                        sell_amount = (current_btc_value - target_btc_value) / backtester.current_prices['BTCUSDT']
                        if sell_amount > 0:
                            backtester.place_order('BTCUSDT', OrderSide.SELL, OrderType.MARKET, sell_amount)
                        
            except Exception as e:
                pass  # Ignorar errores en la estrategia de prueba
        
        # Ejecutar backtest
        start_date = btc_data['timestamp'].min()
        end_date = btc_data['timestamp'].max()
        
        result = backtester.run_backtest(simple_strategy, start_date, end_date)
        
        if result.success:
            print("✅ Backtest completado exitosamente!")
            print(f"📊 Retorno Total: {result.metrics.total_return:.2%}")
            print(f"📈 Retorno Anualizado: {result.metrics.annualized_return:.2%}")
            print(f"📉 Máximo Drawdown: {result.metrics.max_drawdown:.2%}")
            print(f"⚡ Ratio Sharpe: {result.metrics.sharpe_ratio:.3f}")
            print(f"🎯 Tasa de Acierto: {result.metrics.win_rate:.2%}")
            print(f"🔄 Total Trades: {result.metrics.total_trades}")
            print(f"💸 Comisiones Pagadas: ${result.metrics.commission_paid:.2f}")
            
            # Mostrar curva de equity
            if not result.equity_curve.empty:
                print(f"📈 Equity Final: ${result.equity_curve['equity'].iloc[-1]:,.2f}")
                print(f"💰 Equity Inicial: ${result.equity_curve['equity'].iloc[0]:,.2f}")
        else:
            print(f"❌ Error en backtest: {result.message}")
        
    except Exception as e:
        print(f"❌ Error en prueba: {e}")

def test_walk_forward_analysis():
    """Función de prueba del Walk-Forward Analysis"""
    try:
        print("🧪 Iniciando prueba del Walk-Forward Analysis...")
        
        # Crear datos de prueba más extensos (2 años)
        dates = pd.date_range(start='2022-01-01', end='2023-12-31', freq='1H')
        np.random.seed(42)
        
        # Simular precio de BTC con tendencia y volatilidad
        returns = np.random.normal(0.0001, 0.02, len(dates))
        prices = [50000]
        
        for ret in returns[1:]:
            new_price = prices[-1] * (1 + ret)
            prices.append(max(new_price, 1000))
        
        btc_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.uniform(100, 1000, len(dates))
        })
        
        # Crear backtester
        backtester = AdvancedBacktester(initial_capital=100000, commission_rate=0.001)
        backtester.load_market_data({'BTCUSDT': btc_data})
        
        # Crear analizador de Walk-Forward
        wf_analyzer = WalkForwardAnalyzer(backtester)
        
        # Configuración del análisis
        config = WalkForwardConfig(
            training_window=90,  # 3 meses de entrenamiento
            testing_window=30,   # 1 mes de testing
            step_size=15,        # Avanzar cada 2 semanas
            min_training_samples=50,
            reoptimization_frequency=2,  # Reoptimizar cada 2 períodos
            parallel_execution=False  # Secuencial para debugging
        )
        
        # Estrategia simple de momentum
        def momentum_strategy(backtester, market_data, timestamp):
            try:
                if 'BTCUSDT' in backtester.current_prices:
                    # Obtener datos históricos recientes
                    symbol_data = backtester.market_data['BTCUSDT']
                    current_idx = symbol_data[symbol_data['timestamp'] <= timestamp].index
                    
                    if len(current_idx) >= 20:  # Necesitamos al menos 20 períodos
                        recent_data = symbol_data.loc[current_idx[-20:]]
                        
                        # Calcular momentum simple (precio actual vs promedio 10 períodos)
                        current_price = backtester.current_prices['BTCUSDT']
                        avg_price = recent_data['close'].tail(10).mean()
                        
                        momentum = (current_price - avg_price) / avg_price
                        
                        current_equity = backtester.current_capital + sum(
                            pos * backtester.current_prices.get(symbol, 0) 
                            for symbol, pos in backtester.current_positions.items()
                        )
                        
                        current_btc_value = backtester.current_positions.get('BTCUSDT', 0) * current_price
                        
                        # Señal de compra si momentum > 2%
                        if momentum > 0.02 and current_btc_value < current_equity * 0.8:
                            buy_amount = (current_equity * 0.3) / current_price
                            if buy_amount > 0:
                                backtester.place_order('BTCUSDT', OrderSide.BUY, OrderType.MARKET, buy_amount)
                        
                        # Señal de venta si momentum < -2%
                        elif momentum < -0.02 and current_btc_value > current_equity * 0.1:
                            sell_amount = backtester.current_positions.get('BTCUSDT', 0) * 0.5
                            if sell_amount > 0:
                                backtester.place_order('BTCUSDT', OrderSide.SELL, OrderType.MARKET, sell_amount)
                        
            except Exception as e:
                pass  # Ignorar errores en la estrategia
        
        # Ejecutar Walk-Forward Analysis
        print("🚀 Ejecutando Walk-Forward Analysis...")
        wf_result = wf_analyzer.run_walk_forward_analysis(momentum_strategy, config=config)
        
        # Mostrar resultados
        print("\n✅ Walk-Forward Analysis completado!")
        print(f"📊 Períodos Totales: {wf_result.total_periods}")
        print(f"✅ Períodos Exitosos: {wf_result.successful_periods}")
        print(f"💰 Retorno Agregado: {wf_result.aggregated_metrics.total_return:.2%}")
        print(f"📈 Retorno Anualizado: {wf_result.aggregated_metrics.annualized_return:.2%}")
        print(f"📉 Máximo Drawdown: {wf_result.aggregated_metrics.max_drawdown:.2%}")
        print(f"⚡ Ratio Sharpe Promedio: {wf_result.aggregated_metrics.sharpe_ratio:.3f}")
        print(f"🎯 Tasa de Acierto: {wf_result.aggregated_metrics.win_rate:.2%}")
        print(f"🔒 Score de Robustez: {wf_result.robustness_score:.3f}")
        
        # Mostrar métricas de estabilidad
        if wf_result.stability_metrics:
            print(f"📊 Estabilidad General: {wf_result.stability_metrics.get('overall_stability', 0):.3f}")
            print(f"📈 Estabilidad de Retornos: {wf_result.stability_metrics.get('return_stability', 0):.3f}")
            print(f"⚡ Estabilidad de Sharpe: {wf_result.stability_metrics.get('sharpe_stability', 0):.3f}")
        
        # Mostrar análisis de degradación
        if wf_result.degradation_analysis:
            print(f"📉 Degradación de Retornos: {wf_result.degradation_analysis.get('return_degradation', 0):.3f}")
            print(f"📊 Tendencia de Performance: {wf_result.degradation_analysis.get('performance_trend', 0):.3f}")
        
        # Mostrar performance out-of-sample
        if wf_result.out_of_sample_performance:
            print(f"🎯 Hit Rate OOS: {wf_result.out_of_sample_performance.get('oos_hit_rate', 0):.2%}")
            print(f"💰 Retorno Promedio OOS: {wf_result.out_of_sample_performance.get('oos_avg_return', 0):.2%}")
            print(f"📊 Sharpe OOS: {wf_result.out_of_sample_performance.get('oos_sharpe', 0):.3f}")
        
    except Exception as e:
        print(f"❌ Error en prueba de Walk-Forward: {e}")
        import traceback
        traceback.print_exc()

def test_advanced_metrics():
    """Prueba las métricas avanzadas del backtester"""
    print("🧪 PRUEBA DE MÉTRICAS AVANZADAS")
    print("=" * 50)
    
    try:
        # Crear datos de prueba más largos para métricas avanzadas
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2024, 12, 31)
        
        # Generar 2 años de datos diarios de BTC
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        np.random.seed(42)  # Para resultados reproducibles
        
        # Simular precio de BTC con tendencia alcista y volatilidad
        initial_price = 30000
        returns = np.random.normal(0.0008, 0.025, len(dates))  # 0.08% diario promedio, 2.5% volatilidad
        prices = [initial_price]
        
        for ret in returns[1:]:
            new_price = prices[-1] * (1 + ret)
            prices.append(new_price)
        
        # Crear DataFrame
        btc_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.uniform(1000, 5000, len(dates))
        })
        
        # Inicializar backtester
        backtester = AdvancedBacktester(
            initial_capital=100000,
            commission_rate=0.001
        )
        
        # Cargar datos de mercado
        backtester.load_market_data({'BTCUSDT': btc_data})
        
        # Estrategia de momentum mejorada
        def advanced_momentum_strategy(backtester, market_data, current_time):
            if 'BTCUSDT' not in market_data:
                return
            
            data = market_data['BTCUSDT']
            if len(data) < 50:  # Necesitamos al menos 50 períodos
                return
            
            # Calcular indicadores técnicos
            data = data.copy()
            data['sma_20'] = data['close'].rolling(20).mean()
            data['sma_50'] = data['close'].rolling(50).mean()
            data['rsi'] = calculate_rsi(data['close'], 14)
            data['bb_upper'], data['bb_lower'] = calculate_bollinger_bands(data['close'], 20)
            
            current_price = data.iloc[-1]['close']
            sma_20 = data.iloc[-1]['sma_20']
            sma_50 = data.iloc[-1]['sma_50']
            rsi = data.iloc[-1]['rsi']
            bb_upper = data.iloc[-1]['bb_upper']
            bb_lower = data.iloc[-1]['bb_lower']
            
            # Señales de compra/venta
            buy_signal = (current_price > sma_20 > sma_50 and 
                         rsi < 70 and 
                         current_price < bb_upper)
            
            sell_signal = (current_price < sma_20 or 
                          rsi > 80 or 
                          current_price > bb_upper)
            
            current_position = backtester.get_position('BTCUSDT')
            
            if buy_signal and current_position == 0:
                # Comprar con 80% del capital disponible
                size = (backtester.current_capital * 0.8) / current_price
                backtester.place_order('BTCUSDT', 'buy', size, current_price)
                
            elif sell_signal and current_position > 0:
                # Vender toda la posición
                backtester.place_order('BTCUSDT', 'sell', current_position, current_price)
        
        # Ejecutar backtest
        print("🚀 Ejecutando backtest con métricas avanzadas...")
        result = backtester.run_backtest(
            strategy_func=advanced_momentum_strategy,
            start_date=start_date,
            end_date=end_date
        )
        
        # Mostrar resultados básicos
        print(f"\n📊 RESULTADOS BÁSICOS:")
        print(f"💰 Retorno Total: {result.metrics.total_return:.2%}")
        print(f"📈 Retorno Anualizado: {result.metrics.annualized_return:.2%}")
        print(f"⚡ Sharpe Ratio: {result.metrics.sharpe_ratio:.3f}")
        print(f"📉 Max Drawdown: {result.metrics.max_drawdown:.2%}")
        print(f"🎯 Win Rate: {result.metrics.win_rate:.2%}")
        print(f"🔄 Total Trades: {result.metrics.total_trades}")
        
        # Mostrar métricas avanzadas
        if result.advanced_metrics:
            print(f"\n🔬 MÉTRICAS AVANZADAS DETALLADAS:")
            adv = result.advanced_metrics
            
            print(f"\n📊 Retorno Ajustado por Riesgo:")
            print(f"   🎯 Treynor Ratio: {adv.treynor_ratio:.3f}")
            print(f"   🏆 Jensen's Alpha: {adv.jensen_alpha:.3f}")
            print(f"   📈 Information Ratio: {adv.information_ratio:.3f}")
            print(f"   🎪 Modigliani Ratio: {adv.modigliani_ratio:.3f}")
            print(f"   📏 Tracking Error: {adv.tracking_error:.3f}")
            
            print(f"\n📉 Análisis de Drawdown Avanzado:")
            print(f"   🩹 Ulcer Index: {adv.ulcer_index:.3f}")
            print(f"   😣 Pain Index: {adv.pain_index:.3f}")
            print(f"   🏞️ Lake Ratio: {adv.lake_ratio:.3f}")
            print(f"   🏗️ Burke Ratio: {adv.burke_ratio:.3f}")
            
            print(f"\n🎯 Métricas de Consistencia:")
            print(f"   💪 Gain to Pain Ratio: {adv.gain_to_pain_ratio:.3f}")
            print(f"   🥈 Sterling Ratio: {adv.sterling_ratio:.3f}")
            print(f"   🔥 Omega Ratio: {adv.omega_ratio:.3f}")
            print(f"   🎭 Batting Average: {adv.batting_average:.2%}")
            
            print(f"\n⚠️ Análisis de Tail Risk:")
            print(f"   🎢 Tail Ratio: {adv.tail_ratio:.3f}")
            print(f"   💥 Expected Shortfall Ratio: {adv.expected_shortfall_ratio:.3f}")
            print(f"   🌊 Conditional Drawdown Risk: {adv.conditional_drawdown_risk:.3f}")
            print(f"   📊 Maximum Adverse Excursion: {adv.maximum_adverse_excursion:.3f}")
            
            print(f"\n⏰ Métricas de Timing:")
            print(f"   📈 Up Capture Ratio: {adv.up_capture_ratio:.2%}")
            print(f"   📉 Down Capture Ratio: {adv.down_capture_ratio:.2%}")
            print(f"   ⚖️ Capture Ratio: {adv.capture_ratio:.3f}")
            
            print(f"\n🏛️ Métricas de Estabilidad:")
            print(f"   🔒 Return Stability: {adv.return_stability:.3f}")
            print(f"   📊 Sharpe Stability: {adv.sharpe_stability:.3f}")
            print(f"   🎯 Performance Consistency: {adv.performance_consistency:.2%}")
            print(f"   📈 Rolling Sharpe Std: {adv.rolling_sharpe_std:.3f}")
        
        print(f"\n✅ Prueba de métricas avanzadas completada exitosamente!")
        
    except Exception as e:
        print(f"❌ Error en prueba de métricas avanzadas: {e}")
        import traceback
        traceback.print_exc()

def calculate_rsi(prices, period=14):
    """Calcula el RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """Calcula las Bandas de Bollinger"""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    return upper_band, lower_band

if __name__ == "__main__":
    # Ejecutar todas las pruebas
    test_advanced_backtester()
    print("\n" + "="*80 + "\n")
    test_walk_forward_analysis()
    print("\n" + "="*80 + "\n")
    test_advanced_metrics()