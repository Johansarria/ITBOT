#!/usr/bin/env python3
"""
Sistema Avanzado de Gestión de Riesgos
Optimizado para estrategia Binance Spot con objetivo de 0.6% diario
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

@dataclass
class RiskMetrics:
    """Métricas de riesgo calculadas"""
    var_95: float  # Value at Risk 95%
    var_99: float  # Value at Risk 99%
    cvar_95: float  # Conditional VaR 95%
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    volatility: float
    skewness: float
    kurtosis: float
    beta: float
    alpha: float
    information_ratio: float
    tracking_error: float
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    consecutive_wins: int
    consecutive_losses: int
    recovery_factor: float
    ulcer_index: float
    
@dataclass
class PositionRisk:
    """Riesgo de una posición específica"""
    symbol: str
    position_size: float
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    unrealized_pnl: float
    risk_amount: float
    risk_percentage: float
    position_value: float
    leverage: float = 1.0
    correlation_risk: float = 0.0
    liquidity_risk: float = 0.0
    volatility_risk: float = 0.0
    
@dataclass
class PortfolioRisk:
    """Riesgo del portfolio completo"""
    total_value: float
    total_risk: float
    risk_percentage: float
    concentration_risk: float
    correlation_risk: float
    liquidity_risk: float
    var_portfolio: float
    expected_return: float
    sharpe_ratio: float
    max_positions: int
    current_positions: int
    available_capital: float
    margin_used: float
    margin_available: float
    
@dataclass
class RiskLimits:
    """Límites de riesgo configurables"""
    max_risk_per_trade: float = 0.02  # 2% máximo por operación
    max_portfolio_risk: float = 0.10  # 10% máximo del portfolio
    max_daily_loss: float = 0.05      # 5% pérdida máxima diaria
    max_drawdown: float = 0.15        # 15% drawdown máximo
    max_correlation: float = 0.7      # Correlación máxima entre posiciones
    max_positions: int = 5            # Máximo 5 posiciones simultáneas
    min_liquidity: float = 100000     # Liquidez mínima en USDT
    max_position_size: float = 0.25   # 25% máximo en una posición
    stop_loss_multiplier: float = 1.5 # Multiplicador ATR para stop loss
    take_profit_multiplier: float = 2.5 # Multiplicador ATR para take profit
    
class RiskManager:
    """
    Sistema avanzado de gestión de riesgos que controla:
    - Riesgo por operación
    - Riesgo de portfolio
    - Drawdown máximo
    - Correlaciones
    - Liquidez
    - Volatilidad
    """
    
    def __init__(self, initial_capital: float = 500.0, target_daily_return: float = 0.006):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.target_daily_return = target_daily_return
        
        # Configuración de límites
        self.limits = RiskLimits()
        
        # Historial de operaciones
        self.trade_history: List[Dict] = []
        self.daily_pnl: List[float] = []
        self.equity_curve: List[float] = [initial_capital]
        
        # Posiciones actuales
        self.current_positions: Dict[str, PositionRisk] = {}
        
        # Métricas de riesgo
        self.risk_metrics: Optional[RiskMetrics] = None
        
        # Configuración de logging
        self.logger = logging.getLogger(__name__)
        
        # Estado del sistema
        self.is_trading_halted = False
        self.halt_reason = ""
        self.last_risk_check = datetime.now()
        
        # Correlaciones históricas
        self.correlation_matrix = pd.DataFrame()
        self.price_history: Dict[str, List[float]] = {}
        
    def calculate_position_size(self, symbol: str, entry_price: float, 
                              stop_loss: float, signal_strength: float = 1.0) -> float:
        """Calcular tamaño óptimo de posición basado en riesgo"""
        
        # Riesgo por operación basado en stop loss
        risk_per_share = abs(entry_price - stop_loss)
        risk_amount = self.current_capital * self.limits.max_risk_per_trade
        
        # Ajustar por fuerza de señal
        risk_amount *= (signal_strength / 100.0)
        
        # Calcular tamaño base
        base_position_size = risk_amount / risk_per_share
        
        # Aplicar límites adicionales
        max_position_value = self.current_capital * self.limits.max_position_size
        max_shares_by_value = max_position_value / entry_price
        
        # Tomar el menor
        position_size = min(base_position_size, max_shares_by_value)
        
        # Verificar liquidez disponible
        position_value = position_size * entry_price
        if position_value > self.get_available_capital():
            position_size = self.get_available_capital() / entry_price
            
        # Verificar límites de concentración
        if len(self.current_positions) > 0:
            position_size = self.adjust_for_concentration(symbol, position_size, entry_price)
            
        return max(0, position_size)
        
    def adjust_for_concentration(self, symbol: str, position_size: float, 
                               entry_price: float) -> float:
        """Ajustar tamaño por riesgo de concentración"""
        position_value = position_size * entry_price
        
        # Calcular concentración actual
        total_portfolio_value = self.calculate_portfolio_value()
        concentration = position_value / total_portfolio_value
        
        if concentration > self.limits.max_position_size:
            # Reducir posición para cumplir límite
            max_value = total_portfolio_value * self.limits.max_position_size
            position_size = max_value / entry_price
            
        return position_size
        
    def validate_trade(self, symbol: str, signal_type: str, entry_price: float,
                      stop_loss: float, take_profit: float, position_size: float) -> Tuple[bool, str]:
        """Validar si una operación cumple con los límites de riesgo"""
        
        # Verificar si el trading está detenido
        if self.is_trading_halted:
            return False, f"Trading detenido: {self.halt_reason}"
            
        # Verificar límite de posiciones
        if len(self.current_positions) >= self.limits.max_positions:
            return False, "Límite máximo de posiciones alcanzado"
            
        # Calcular riesgo de la operación
        risk_amount = abs(entry_price - stop_loss) * position_size
        risk_percentage = risk_amount / self.current_capital
        
        if risk_percentage > self.limits.max_risk_per_trade:
            return False, f"Riesgo por operación excede límite: {risk_percentage:.3f} > {self.limits.max_risk_per_trade}"
            
        # Verificar riesgo total del portfolio
        total_risk = self.calculate_total_portfolio_risk()
        new_total_risk = total_risk + risk_percentage
        
        if new_total_risk > self.limits.max_portfolio_risk:
            return False, f"Riesgo total del portfolio excede límite: {new_total_risk:.3f} > {self.limits.max_portfolio_risk}"
            
        # Verificar capital disponible
        position_value = position_size * entry_price
        if position_value > self.get_available_capital():
            return False, "Capital insuficiente para la operación"
            
        # Verificar correlación con posiciones existentes
        correlation_risk = self.calculate_correlation_risk(symbol)
        if correlation_risk > self.limits.max_correlation:
            return False, f"Riesgo de correlación excede límite: {correlation_risk:.3f} > {self.limits.max_correlation}"
            
        # Verificar drawdown actual
        current_drawdown = self.calculate_current_drawdown()
        if current_drawdown > self.limits.max_drawdown:
            return False, f"Drawdown actual excede límite: {current_drawdown:.3f} > {self.limits.max_drawdown}"
            
        # Verificar pérdida diaria
        daily_loss = self.calculate_daily_loss()
        if daily_loss > self.limits.max_daily_loss:
            return False, f"Pérdida diaria excede límite: {daily_loss:.3f} > {self.limits.max_daily_loss}"
            
        return True, "Operación validada"
        
    def add_position(self, symbol: str, signal_type: str, entry_price: float,
                    stop_loss: float, take_profit: float, position_size: float) -> bool:
        """Agregar nueva posición al portfolio"""
        
        # Validar operación
        is_valid, message = self.validate_trade(symbol, signal_type, entry_price, 
                                               stop_loss, take_profit, position_size)
        
        if not is_valid:
            self.logger.warning(f"Operación rechazada para {symbol}: {message}")
            return False
            
        # Crear posición
        position = PositionRisk(
            symbol=symbol,
            position_size=position_size if signal_type == 'BUY' else -position_size,
            entry_price=entry_price,
            current_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            unrealized_pnl=0.0,
            risk_amount=abs(entry_price - stop_loss) * position_size,
            risk_percentage=abs(entry_price - stop_loss) * position_size / self.current_capital,
            position_value=position_size * entry_price
        )
        
        # Calcular riesgos adicionales
        position.correlation_risk = self.calculate_correlation_risk(symbol)
        position.volatility_risk = self.calculate_volatility_risk(symbol)
        position.liquidity_risk = self.calculate_liquidity_risk(symbol)
        
        # Agregar al portfolio
        self.current_positions[symbol] = position
        
        # Registrar operación
        trade_record = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'action': 'OPEN',
            'signal_type': signal_type,
            'price': entry_price,
            'size': position_size,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_amount': position.risk_amount,
            'risk_percentage': position.risk_percentage
        }
        
        self.trade_history.append(trade_record)
        
        self.logger.info(f"Posición abierta: {symbol} {signal_type} {position_size:.6f} @ {entry_price:.2f}")
        return True
        
    def update_positions(self, price_data: Dict[str, float]):
        """Actualizar posiciones con precios actuales"""
        
        for symbol, position in self.current_positions.items():
            if symbol in price_data:
                old_price = position.current_price
                new_price = price_data[symbol]
                
                # Actualizar precio y PnL
                position.current_price = new_price
                
                if position.position_size > 0:  # Long
                    position.unrealized_pnl = (new_price - position.entry_price) * position.position_size
                else:  # Short
                    position.unrealized_pnl = (position.entry_price - new_price) * abs(position.position_size)
                    
                # Actualizar valor de posición
                position.position_value = abs(position.position_size) * new_price
                
                # Actualizar historial de precios
                if symbol not in self.price_history:
                    self.price_history[symbol] = []
                self.price_history[symbol].append(new_price)
                
                # Mantener solo últimos 100 precios
                if len(self.price_history[symbol]) > 100:
                    self.price_history[symbol] = self.price_history[symbol][-100:]
                    
        # Verificar stops y targets
        self.check_stop_loss_take_profit()
        
        # Actualizar capital actual
        self.update_current_capital()
        
        # Verificar límites de riesgo
        self.check_risk_limits()
        
    def check_stop_loss_take_profit(self):
        """Verificar stop loss y take profit"""
        
        positions_to_close = []
        
        for symbol, position in self.current_positions.items():
            current_price = position.current_price
            
            # Verificar stop loss
            if position.position_size > 0:  # Long
                if current_price <= position.stop_loss:
                    positions_to_close.append((symbol, 'STOP_LOSS', current_price))
                elif current_price >= position.take_profit:
                    positions_to_close.append((symbol, 'TAKE_PROFIT', current_price))
            else:  # Short
                if current_price >= position.stop_loss:
                    positions_to_close.append((symbol, 'STOP_LOSS', current_price))
                elif current_price <= position.take_profit:
                    positions_to_close.append((symbol, 'TAKE_PROFIT', current_price))
                    
        # Cerrar posiciones
        for symbol, reason, price in positions_to_close:
            self.close_position(symbol, price, reason)
            
    def close_position(self, symbol: str, exit_price: float, reason: str = 'MANUAL'):
        """Cerrar posición"""
        
        if symbol not in self.current_positions:
            self.logger.warning(f"Intento de cerrar posición inexistente: {symbol}")
            return
            
        position = self.current_positions[symbol]
        
        # Calcular PnL realizado
        if position.position_size > 0:  # Long
            realized_pnl = (exit_price - position.entry_price) * position.position_size
        else:  # Short
            realized_pnl = (position.entry_price - exit_price) * abs(position.position_size)
            
        # Registrar operación de cierre
        trade_record = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'action': 'CLOSE',
            'reason': reason,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'size': abs(position.position_size),
            'realized_pnl': realized_pnl,
            'return_pct': realized_pnl / (position.entry_price * abs(position.position_size))
        }
        
        self.trade_history.append(trade_record)
        
        # Actualizar capital
        self.current_capital += realized_pnl
        self.equity_curve.append(self.current_capital)
        
        # Remover posición
        del self.current_positions[symbol]
        
        self.logger.info(f"Posición cerrada: {symbol} {reason} PnL: {realized_pnl:.2f} USDT")
        
    def calculate_portfolio_value(self) -> float:
        """Calcular valor total del portfolio"""
        total_value = self.current_capital
        
        for position in self.current_positions.values():
            total_value += position.unrealized_pnl
            
        return total_value
        
    def calculate_total_portfolio_risk(self) -> float:
        """Calcular riesgo total del portfolio"""
        total_risk = 0.0
        
        for position in self.current_positions.values():
            total_risk += position.risk_percentage
            
        return total_risk
        
    def get_available_capital(self) -> float:
        """Obtener capital disponible para nuevas operaciones"""
        used_capital = 0.0
        
        for position in self.current_positions.values():
            used_capital += position.position_value
            
        return max(0, self.current_capital - used_capital)
        
    def calculate_correlation_risk(self, symbol: str) -> float:
        """Calcular riesgo de correlación con posiciones existentes"""
        if not self.current_positions or symbol not in self.price_history:
            return 0.0
            
        max_correlation = 0.0
        
        for existing_symbol in self.current_positions.keys():
            if existing_symbol == symbol or existing_symbol not in self.price_history:
                continue
                
            # Calcular correlación entre series de precios
            if len(self.price_history[symbol]) > 10 and len(self.price_history[existing_symbol]) > 10:
                min_length = min(len(self.price_history[symbol]), len(self.price_history[existing_symbol]))
                
                prices1 = np.array(self.price_history[symbol][-min_length:])
                prices2 = np.array(self.price_history[existing_symbol][-min_length:])
                
                if len(prices1) > 1 and len(prices2) > 1:
                    returns1 = np.diff(prices1) / prices1[:-1]
                    returns2 = np.diff(prices2) / prices2[:-1]
                    
                    if len(returns1) > 1 and len(returns2) > 1:
                        correlation = np.corrcoef(returns1, returns2)[0, 1]
                        if not np.isnan(correlation):
                            max_correlation = max(max_correlation, abs(correlation))
                            
        return max_correlation
        
    def calculate_volatility_risk(self, symbol: str) -> float:
        """Calcular riesgo de volatilidad"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 10:
            return 0.5  # Riesgo medio por defecto
            
        prices = np.array(self.price_history[symbol][-30:])  # Últimos 30 períodos
        
        if len(prices) > 1:
            returns = np.diff(prices) / prices[:-1]
            volatility = np.std(returns) * np.sqrt(24)  # Anualizada para datos horarios
            
            # Normalizar a escala 0-1
            normalized_vol = min(volatility / 0.5, 1.0)  # 50% vol anual = máximo
            return normalized_vol
            
        return 0.5
        
    def calculate_liquidity_risk(self, symbol: str) -> float:
        """Calcular riesgo de liquidez (simplificado)"""
        # En implementación real, usar datos de order book
        # Por ahora, riesgo bajo para pares principales
        major_pairs = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOTUSDT']
        
        if any(pair in symbol for pair in major_pairs):
            return 0.1  # Riesgo bajo
        else:
            return 0.3  # Riesgo medio
            
    def calculate_current_drawdown(self) -> float:
        """Calcular drawdown actual"""
        if len(self.equity_curve) < 2:
            return 0.0
            
        peak = max(self.equity_curve)
        current = self.equity_curve[-1]
        
        drawdown = (peak - current) / peak
        return max(0, drawdown)
        
    def calculate_daily_loss(self) -> float:
        """Calcular pérdida del día actual"""
        if len(self.equity_curve) < 2:
            return 0.0
            
        # Simplificado: comparar con valor de ayer
        start_of_day = self.equity_curve[-24] if len(self.equity_curve) >= 24 else self.equity_curve[0]
        current = self.equity_curve[-1]
        
        if current < start_of_day:
            return (start_of_day - current) / start_of_day
        else:
            return 0.0
            
    def update_current_capital(self):
        """Actualizar capital actual con PnL no realizado"""
        # El capital base no cambia hasta cerrar posiciones
        # Pero podemos calcular el valor total del portfolio
        pass
        
    def check_risk_limits(self):
        """Verificar límites de riesgo y detener trading si es necesario"""
        
        # Verificar drawdown máximo
        current_drawdown = self.calculate_current_drawdown()
        if current_drawdown > self.limits.max_drawdown:
            self.halt_trading(f"Drawdown máximo excedido: {current_drawdown:.3f}")
            return
            
        # Verificar pérdida diaria máxima
        daily_loss = self.calculate_daily_loss()
        if daily_loss > self.limits.max_daily_loss:
            self.halt_trading(f"Pérdida diaria máxima excedida: {daily_loss:.3f}")
            return
            
        # Verificar riesgo total del portfolio
        total_risk = self.calculate_total_portfolio_risk()
        if total_risk > self.limits.max_portfolio_risk:
            self.halt_trading(f"Riesgo total del portfolio excedido: {total_risk:.3f}")
            return
            
        # Si todo está bien, reanudar trading
        if self.is_trading_halted:
            self.resume_trading()
            
    def halt_trading(self, reason: str):
        """Detener el trading"""
        self.is_trading_halted = True
        self.halt_reason = reason
        self.logger.warning(f"TRADING DETENIDO: {reason}")
        
    def resume_trading(self):
        """Reanudar el trading"""
        self.is_trading_halted = False
        self.halt_reason = ""
        self.logger.info("Trading reanudado")
        
    def calculate_risk_metrics(self) -> RiskMetrics:
        """Calcular métricas completas de riesgo"""
        
        if len(self.equity_curve) < 10:
            # Métricas por defecto si no hay suficientes datos
            return RiskMetrics(
                var_95=0.0, var_99=0.0, cvar_95=0.0, max_drawdown=0.0,
                sharpe_ratio=0.0, sortino_ratio=0.0, calmar_ratio=0.0,
                volatility=0.0, skewness=0.0, kurtosis=0.0, beta=0.0,
                alpha=0.0, information_ratio=0.0, tracking_error=0.0,
                win_rate=0.0, profit_factor=0.0, avg_win=0.0, avg_loss=0.0,
                largest_win=0.0, largest_loss=0.0, consecutive_wins=0,
                consecutive_losses=0, recovery_factor=0.0, ulcer_index=0.0
            )
            
        # Calcular retornos
        equity_series = pd.Series(self.equity_curve)
        returns = equity_series.pct_change().dropna()
        
        if len(returns) == 0:
            returns = pd.Series([0.0])
            
        # Métricas básicas
        volatility = returns.std() * np.sqrt(252)  # Anualizada
        mean_return = returns.mean() * 252  # Anualizada
        
        # Sharpe Ratio
        sharpe_ratio = mean_return / volatility if volatility > 0 else 0
        
        # Sortino Ratio
        downside_returns = returns[returns < 0]
        downside_vol = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else volatility
        sortino_ratio = mean_return / downside_vol if downside_vol > 0 else 0
        
        # Drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = abs(drawdown.min())
        
        # Calmar Ratio
        calmar_ratio = mean_return / max_drawdown if max_drawdown > 0 else 0
        
        # VaR y CVaR
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)
        cvar_95 = returns[returns <= var_95].mean() if len(returns[returns <= var_95]) > 0 else var_95
        
        # Skewness y Kurtosis
        skewness = stats.skew(returns) if len(returns) > 2 else 0
        kurtosis = stats.kurtosis(returns) if len(returns) > 3 else 0
        
        # Métricas de trading
        closed_trades = [t for t in self.trade_history if t.get('action') == 'CLOSE']
        
        if closed_trades:
            pnls = [t['realized_pnl'] for t in closed_trades]
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]
            
            win_rate = len(wins) / len(pnls) if pnls else 0
            avg_win = np.mean(wins) if wins else 0
            avg_loss = np.mean(losses) if losses else 0
            largest_win = max(wins) if wins else 0
            largest_loss = min(losses) if losses else 0
            
            profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else 0
            
            # Rachas consecutivas
            consecutive_wins = self.calculate_consecutive_wins(pnls)
            consecutive_losses = self.calculate_consecutive_losses(pnls)
        else:
            win_rate = avg_win = avg_loss = largest_win = largest_loss = 0
            profit_factor = consecutive_wins = consecutive_losses = 0
            
        # Recovery Factor
        total_return = (equity_series.iloc[-1] - equity_series.iloc[0]) / equity_series.iloc[0]
        recovery_factor = total_return / max_drawdown if max_drawdown > 0 else 0
        
        # Ulcer Index
        ulcer_index = np.sqrt(np.mean(drawdown ** 2))
        
        self.risk_metrics = RiskMetrics(
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            volatility=volatility,
            skewness=skewness,
            kurtosis=kurtosis,
            beta=0.0,  # Requiere benchmark
            alpha=0.0,  # Requiere benchmark
            information_ratio=0.0,  # Requiere benchmark
            tracking_error=0.0,  # Requiere benchmark
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses,
            recovery_factor=recovery_factor,
            ulcer_index=ulcer_index
        )
        
        return self.risk_metrics
        
    def calculate_consecutive_wins(self, pnls: List[float]) -> int:
        """Calcular máxima racha de ganancias consecutivas"""
        max_consecutive = 0
        current_consecutive = 0
        
        for pnl in pnls:
            if pnl > 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
                
        return max_consecutive
        
    def calculate_consecutive_losses(self, pnls: List[float]) -> int:
        """Calcular máxima racha de pérdidas consecutivas"""
        max_consecutive = 0
        current_consecutive = 0
        
        for pnl in pnls:
            if pnl < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
                
        return max_consecutive
        
    def get_portfolio_summary(self) -> PortfolioRisk:
        """Obtener resumen del riesgo del portfolio"""
        
        total_value = self.calculate_portfolio_value()
        total_risk = self.calculate_total_portfolio_risk()
        available_capital = self.get_available_capital()
        
        # Calcular concentración
        if self.current_positions:
            position_values = [pos.position_value for pos in self.current_positions.values()]
            max_position_value = max(position_values)
            concentration_risk = max_position_value / total_value
        else:
            concentration_risk = 0.0
            
        # Calcular correlación promedio
        correlation_risk = 0.0
        if len(self.current_positions) > 1:
            correlations = []
            symbols = list(self.current_positions.keys())
            for i, symbol1 in enumerate(symbols):
                for symbol2 in symbols[i+1:]:
                    corr = self.calculate_correlation_risk(symbol1)
                    correlations.append(corr)
            correlation_risk = np.mean(correlations) if correlations else 0.0
            
        # Riesgo de liquidez promedio
        if self.current_positions:
            liquidity_risks = [pos.liquidity_risk for pos in self.current_positions.values()]
            liquidity_risk = np.mean(liquidity_risks)
        else:
            liquidity_risk = 0.0
            
        return PortfolioRisk(
            total_value=total_value,
            total_risk=total_risk,
            risk_percentage=total_risk,
            concentration_risk=concentration_risk,
            correlation_risk=correlation_risk,
            liquidity_risk=liquidity_risk,
            var_portfolio=0.0,  # Requiere cálculo más complejo
            expected_return=self.target_daily_return,
            sharpe_ratio=self.risk_metrics.sharpe_ratio if self.risk_metrics else 0.0,
            max_positions=self.limits.max_positions,
            current_positions=len(self.current_positions),
            available_capital=available_capital,
            margin_used=total_value - self.current_capital,
            margin_available=available_capital
        )
        
    def generate_risk_report(self) -> Dict:
        """Generar reporte completo de riesgo"""
        
        # Calcular métricas
        risk_metrics = self.calculate_risk_metrics()
        portfolio_risk = self.get_portfolio_summary()
        
        # Crear reporte
        report = {
            'timestamp': datetime.now(),
            'capital_inicial': self.initial_capital,
            'capital_actual': self.current_capital,
            'valor_portfolio': portfolio_risk.total_value,
            'retorno_total': (portfolio_risk.total_value - self.initial_capital) / self.initial_capital,
            'posiciones_actuales': len(self.current_positions),
            'operaciones_totales': len([t for t in self.trade_history if t.get('action') == 'CLOSE']),
            'trading_detenido': self.is_trading_halted,
            'razon_detencion': self.halt_reason,
            
            # Métricas de riesgo
            'riesgo_total': portfolio_risk.total_risk,
            'riesgo_concentracion': portfolio_risk.concentration_risk,
            'riesgo_correlacion': portfolio_risk.correlation_risk,
            'riesgo_liquidez': portfolio_risk.liquidity_risk,
            'drawdown_actual': self.calculate_current_drawdown(),
            'perdida_diaria': self.calculate_daily_loss(),
            
            # Métricas de rendimiento
            'sharpe_ratio': risk_metrics.sharpe_ratio,
            'sortino_ratio': risk_metrics.sortino_ratio,
            'calmar_ratio': risk_metrics.calmar_ratio,
            'win_rate': risk_metrics.win_rate,
            'profit_factor': risk_metrics.profit_factor,
            'max_drawdown': risk_metrics.max_drawdown,
            
            # Límites
            'limites': {
                'max_risk_per_trade': self.limits.max_risk_per_trade,
                'max_portfolio_risk': self.limits.max_portfolio_risk,
                'max_daily_loss': self.limits.max_daily_loss,
                'max_drawdown': self.limits.max_drawdown,
                'max_positions': self.limits.max_positions
            },
            
            # Estado de posiciones
            'posiciones': {
                symbol: {
                    'size': pos.position_size,
                    'entry_price': pos.entry_price,
                    'current_price': pos.current_price,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'risk_amount': pos.risk_amount,
                    'risk_percentage': pos.risk_percentage
                }
                for symbol, pos in self.current_positions.items()
            }
        }
        
        return report
        
if __name__ == "__main__":
    # Ejemplo de uso
    risk_manager = RiskManager(initial_capital=500.0, target_daily_return=0.006)
    
    # Simular algunas operaciones
    risk_manager.add_position('BTCUSDT', 'BUY', 50000, 49000, 52000, 0.01)
    risk_manager.add_position('ETHUSDT', 'BUY', 3000, 2900, 3200, 0.1)
    
    # Actualizar precios
    risk_manager.update_positions({
        'BTCUSDT': 50500,
        'ETHUSDT': 3050
    })
    
    # Generar reporte
    report = risk_manager.generate_risk_report()
    
    print("=== REPORTE DE RIESGO ===")
    print(f"Capital inicial: {report['capital_inicial']:.2f} USDT")
    print(f"Capital actual: {report['capital_actual']:.2f} USDT")
    print(f"Valor portfolio: {report['valor_portfolio']:.2f} USDT")
    print(f"Retorno total: {report['retorno_total']:.2%}")
    print(f"Posiciones actuales: {report['posiciones_actuales']}")
    print(f"Riesgo total: {report['riesgo_total']:.2%}")
    print(f"Win rate: {report['win_rate']:.2%}")
    print(f"Sharpe ratio: {report['sharpe_ratio']:.3f}")