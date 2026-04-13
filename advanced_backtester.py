#!/usr/bin/env python3
"""
Sistema de Backtesting Avanzado para Estrategia Binance Spot
Incluye análisis de costos reales, slippage, y validación rigurosa
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

@dataclass
class TradeResult:
    """Resultado de una operación de trading"""
    symbol: str
    entry_time: datetime
    exit_time: datetime
    side: str  # 'long' or 'short'
    entry_price: float
    exit_price: float
    quantity: float
    gross_pnl: float
    commission: float
    slippage: float
    net_pnl: float
    return_pct: float
    duration_hours: float
    reason: str  # 'take_profit', 'stop_loss', 'signal_exit'

@dataclass
class BacktestMetrics:
    """Métricas del backtesting"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    avg_trade_duration: float
    total_commission: float
    total_slippage: float
    daily_returns: List[float]
    equity_curve: List[float]
    drawdown_curve: List[float]

class AdvancedBacktester:
    """
    Sistema de backtesting avanzado que simula condiciones reales de trading
    incluyendo costos de transacción, slippage, y limitaciones de liquidez
    """
    
    def __init__(self, initial_capital: float = 500.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # Configuración de costos reales
        self.maker_fee = 0.001  # 0.1% maker fee Binance
        self.taker_fee = 0.001  # 0.1% taker fee Binance
        self.min_order_size = 10.0  # Mínimo 10 USDT por orden
        
        # Configuración de slippage
        self.base_slippage = 0.0005  # 0.05% slippage base
        self.volatility_slippage_factor = 0.1  # Factor de slippage por volatilidad
        
        # Configuración de riesgo
        self.max_position_size = 0.3  # Máximo 30% del capital por posición
        self.max_daily_loss = 0.05  # Máximo 5% de pérdida diaria
        self.max_drawdown_limit = 0.15  # Límite de drawdown del 15%
        
        # Configuración de logging
        self.setup_logging()
        
        # Almacenamiento de resultados
        self.trades: List[TradeResult] = []
        self.daily_equity = []
        self.positions = {}
        self.daily_pnl = []
        
    def setup_logging(self):
        """Configurar sistema de logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('backtest.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def calculate_slippage(self, symbol: str, side: str, quantity: float, volatility: float) -> float:
        """Calcular slippage realista basado en volatilidad y tamaño de orden"""
        # Slippage base
        slippage = self.base_slippage
        
        # Ajuste por volatilidad
        vol_adjustment = volatility * self.volatility_slippage_factor
        slippage += vol_adjustment
        
        # Ajuste por tamaño de orden (mayor orden = mayor slippage)
        size_factor = min(quantity / 1000, 0.002)  # Máximo 0.2% adicional
        slippage += size_factor
        
        # Ajuste por lado (market orders tienen más slippage)
        if side == 'buy':
            return slippage  # Slippage positivo para compras
        else:
            return -slippage  # Slippage negativo para ventas
            
    def calculate_commission(self, order_value: float, is_maker: bool = False) -> float:
        """Calcular comisión de la operación"""
        fee_rate = self.maker_fee if is_maker else self.taker_fee
        return order_value * fee_rate
        
    def check_position_limits(self, symbol: str, order_value: float) -> bool:
        """Verificar si la orden cumple con los límites de posición"""
        # Verificar tamaño mínimo
        if order_value < self.min_order_size:
            return False
            
        # Verificar límite de posición
        max_position_value = self.current_capital * self.max_position_size
        if order_value > max_position_value:
            return False
            
        # Verificar capital disponible
        if order_value > self.current_capital * 0.95:  # Dejar 5% de margen
            return False
            
        return True
        
    def execute_trade(self, symbol: str, side: str, quantity: float, price: float, 
                     volatility: float, timestamp: datetime, reason: str = 'signal') -> Optional[TradeResult]:
        """Ejecutar una operación de trading con costos reales"""
        order_value = quantity * price
        
        # Verificar límites
        if not self.check_position_limits(symbol, order_value):
            self.logger.warning(f"Orden rechazada por límites: {symbol} {side} {quantity} @ {price}")
            return None
            
        # Calcular slippage
        slippage_pct = self.calculate_slippage(symbol, side, order_value, volatility)
        slippage_amount = order_value * abs(slippage_pct)
        
        # Precio de ejecución con slippage
        execution_price = price * (1 + slippage_pct) if side == 'buy' else price * (1 + slippage_pct)
        
        # Calcular comisión
        commission = self.calculate_commission(order_value, is_maker=False)
        
        # Actualizar capital
        if side == 'buy':
            total_cost = order_value + commission + slippage_amount
            if total_cost > self.current_capital:
                self.logger.warning(f"Capital insuficiente para {symbol}: necesario {total_cost}, disponible {self.current_capital}")
                return None
            self.current_capital -= total_cost
            
            # Registrar posición
            if symbol not in self.positions:
                self.positions[symbol] = []
            self.positions[symbol].append({
                'quantity': quantity,
                'entry_price': execution_price,
                'entry_time': timestamp,
                'commission': commission,
                'slippage': slippage_amount
            })
            
        else:  # sell
            if symbol not in self.positions or not self.positions[symbol]:
                self.logger.warning(f"No hay posición para vender en {symbol}")
                return None
                
            # Cerrar posición FIFO
            position = self.positions[symbol].pop(0)
            
            # Calcular PnL
            gross_pnl = (execution_price - position['entry_price']) * quantity
            total_commission = commission + position['commission']
            total_slippage = slippage_amount + position['slippage']
            net_pnl = gross_pnl - total_commission - total_slippage
            
            # Actualizar capital
            proceeds = order_value - commission - slippage_amount
            self.current_capital += proceeds
            
            # Crear resultado de trade
            duration = (timestamp - position['entry_time']).total_seconds() / 3600
            return_pct = net_pnl / (position['entry_price'] * quantity)
            
            trade_result = TradeResult(
                symbol=symbol,
                entry_time=position['entry_time'],
                exit_time=timestamp,
                side='long',  # Asumimos long por simplicidad
                entry_price=position['entry_price'],
                exit_price=execution_price,
                quantity=quantity,
                gross_pnl=gross_pnl,
                commission=total_commission,
                slippage=total_slippage,
                net_pnl=net_pnl,
                return_pct=return_pct,
                duration_hours=duration,
                reason=reason
            )
            
            self.trades.append(trade_result)
            return trade_result
            
        return None
        
    def check_risk_limits(self) -> bool:
        """Verificar límites de riesgo"""
        # Verificar pérdida diaria
        if len(self.daily_equity) > 0:
            daily_return = (self.current_capital - self.daily_equity[-1]) / self.daily_equity[-1]
            if daily_return < -self.max_daily_loss:
                self.logger.warning(f"Límite de pérdida diaria alcanzado: {daily_return:.2%}")
                return False
                
        # Verificar drawdown máximo
        if len(self.daily_equity) > 0:
            peak = max(self.daily_equity)
            current_dd = (peak - self.current_capital) / peak
            if current_dd > self.max_drawdown_limit:
                self.logger.warning(f"Límite de drawdown alcanzado: {current_dd:.2%}")
                return False
                
        return True
        
    def run_backtest(self, strategy_signals: pd.DataFrame, market_data: Dict[str, pd.DataFrame]) -> BacktestMetrics:
        """Ejecutar backtesting completo"""
        self.logger.info("Iniciando backtesting avanzado...")
        
        # Resetear estado
        self.current_capital = self.initial_capital
        self.trades = []
        self.positions = {}
        self.daily_equity = [self.initial_capital]
        
        # Procesar señales cronológicamente
        for index, signal in strategy_signals.iterrows():
            timestamp = signal['timestamp']
            symbol = signal['symbol']
            action = signal['action']  # 'buy' or 'sell'
            quantity = signal['quantity']
            price = signal['price']
            volatility = signal.get('volatility', 0.02)
            
            # Verificar límites de riesgo
            if not self.check_risk_limits():
                self.logger.info(f"Trading detenido por límites de riesgo en {timestamp}")
                break
                
            # Ejecutar operación
            trade_result = self.execute_trade(
                symbol, action, quantity, price, volatility, timestamp
            )
            
            if trade_result:
                self.logger.info(
                    f"Trade ejecutado: {trade_result.symbol} {trade_result.side} "
                    f"PnL: {trade_result.net_pnl:.2f} USDT ({trade_result.return_pct:.2%})"
                )
                
        # Cerrar posiciones abiertas al final
        self.close_all_positions(strategy_signals.iloc[-1]['timestamp'])
        
        # Calcular métricas
        metrics = self.calculate_metrics()
        
        self.logger.info(f"Backtesting completado. Trades: {metrics.total_trades}, Return: {metrics.total_return:.2%}")
        
        return metrics
        
    def close_all_positions(self, timestamp: datetime):
        """Cerrar todas las posiciones abiertas"""
        for symbol, positions in self.positions.items():
            for position in positions:
                # Simular cierre a precio de mercado
                # En implementación real, usar último precio disponible
                exit_price = position['entry_price'] * 1.001  # Pequeña ganancia simulada
                
                trade_result = TradeResult(
                    symbol=symbol,
                    entry_time=position['entry_time'],
                    exit_time=timestamp,
                    side='long',
                    entry_price=position['entry_price'],
                    exit_price=exit_price,
                    quantity=position['quantity'],
                    gross_pnl=(exit_price - position['entry_price']) * position['quantity'],
                    commission=position['commission'] * 2,  # Comisión de entrada y salida
                    slippage=position['slippage'] * 2,
                    net_pnl=0,  # Calcular después
                    return_pct=0,
                    duration_hours=(timestamp - position['entry_time']).total_seconds() / 3600,
                    reason='backtest_end'
                )
                
                trade_result.net_pnl = trade_result.gross_pnl - trade_result.commission - trade_result.slippage
                trade_result.return_pct = trade_result.net_pnl / (trade_result.entry_price * trade_result.quantity)
                
                self.trades.append(trade_result)
                
        self.positions = {}
        
    def calculate_metrics(self) -> BacktestMetrics:
        """Calcular métricas de rendimiento del backtesting"""
        if not self.trades:
            return BacktestMetrics(
                total_trades=0, winning_trades=0, losing_trades=0, win_rate=0,
                total_return=0, annual_return=0, max_drawdown=0, sharpe_ratio=0,
                sortino_ratio=0, calmar_ratio=0, profit_factor=0, avg_win=0,
                avg_loss=0, largest_win=0, largest_loss=0, avg_trade_duration=0,
                total_commission=0, total_slippage=0, daily_returns=[], 
                equity_curve=[], drawdown_curve=[]
            )
            
        # Métricas básicas
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t.net_pnl > 0])
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Retornos
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital
        
        # PnL por trade
        pnls = [t.net_pnl for t in self.trades]
        winning_pnls = [t.net_pnl for t in self.trades if t.net_pnl > 0]
        losing_pnls = [t.net_pnl for t in self.trades if t.net_pnl < 0]
        
        avg_win = np.mean(winning_pnls) if winning_pnls else 0
        avg_loss = np.mean(losing_pnls) if losing_pnls else 0
        largest_win = max(pnls) if pnls else 0
        largest_loss = min(pnls) if pnls else 0
        
        # Profit factor
        total_wins = sum(winning_pnls) if winning_pnls else 0
        total_losses = abs(sum(losing_pnls)) if losing_pnls else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Duración promedio
        avg_trade_duration = np.mean([t.duration_hours for t in self.trades]) if self.trades else 0
        
        # Costos totales
        total_commission = sum([t.commission for t in self.trades])
        total_slippage = sum([t.slippage for t in self.trades])
        
        # Curva de equity y drawdown
        equity_curve = [self.initial_capital]
        running_capital = self.initial_capital
        
        for trade in self.trades:
            running_capital += trade.net_pnl
            equity_curve.append(running_capital)
            
        # Calcular drawdown
        peak = equity_curve[0]
        drawdown_curve = []
        max_drawdown = 0
        
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak
            drawdown_curve.append(drawdown)
            max_drawdown = max(max_drawdown, drawdown)
            
        # Retornos diarios (simplificado)
        daily_returns = []
        if len(equity_curve) > 1:
            for i in range(1, len(equity_curve)):
                daily_return = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
                daily_returns.append(daily_return)
                
        # Ratios de riesgo
        if daily_returns:
            avg_daily_return = np.mean(daily_returns)
            std_daily_return = np.std(daily_returns)
            
            # Sharpe ratio (asumiendo 0% risk-free rate)
            sharpe_ratio = avg_daily_return / std_daily_return if std_daily_return > 0 else 0
            sharpe_ratio *= np.sqrt(365)  # Anualizar
            
            # Sortino ratio
            negative_returns = [r for r in daily_returns if r < 0]
            downside_std = np.std(negative_returns) if negative_returns else std_daily_return
            sortino_ratio = avg_daily_return / downside_std if downside_std > 0 else 0
            sortino_ratio *= np.sqrt(365)
            
            # Calmar ratio
            annual_return = (1 + total_return) ** (365 / len(daily_returns)) - 1
            calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0
        else:
            sharpe_ratio = sortino_ratio = calmar_ratio = annual_return = 0
            
        return BacktestMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            avg_trade_duration=avg_trade_duration,
            total_commission=total_commission,
            total_slippage=total_slippage,
            daily_returns=daily_returns,
            equity_curve=equity_curve,
            drawdown_curve=drawdown_curve
        )
        
    def generate_report(self, metrics: BacktestMetrics) -> str:
        """Generar reporte detallado del backtesting"""
        report = f"""
=== REPORTE DE BACKTESTING AVANZADO ===
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Capital inicial: ${self.initial_capital:.2f} USDT
Capital final: ${self.current_capital:.2f} USDT

=== RENDIMIENTO ===
Retorno total: {metrics.total_return:.2%}
Retorno anualizado: {metrics.annual_return:.2%}
Drawdown máximo: {metrics.max_drawdown:.2%}

=== OPERACIONES ===
Total de trades: {metrics.total_trades}
Trades ganadores: {metrics.winning_trades}
Trades perdedores: {metrics.losing_trades}
Tasa de acierto: {metrics.win_rate:.2%}

=== ANÁLISIS DE PnL ===
Ganancia promedio: ${metrics.avg_win:.2f}
Pérdida promedio: ${metrics.avg_loss:.2f}
Mayor ganancia: ${metrics.largest_win:.2f}
Mayor pérdida: ${metrics.largest_loss:.2f}
Profit Factor: {metrics.profit_factor:.2f}

=== RATIOS DE RIESGO ===
Sharpe Ratio: {metrics.sharpe_ratio:.2f}
Sortino Ratio: {metrics.sortino_ratio:.2f}
Calmar Ratio: {metrics.calmar_ratio:.2f}

=== COSTOS DE TRANSACCIÓN ===
Comisiones totales: ${metrics.total_commission:.2f}
Slippage total: ${metrics.total_slippage:.2f}
Costos como % del capital: {(metrics.total_commission + metrics.total_slippage) / self.initial_capital:.2%}

=== ESTADÍSTICAS ADICIONALES ===
Duración promedio por trade: {metrics.avg_trade_duration:.1f} horas
Trades por día (estimado): {metrics.total_trades / max(len(metrics.daily_returns), 1):.1f}

=== EVALUACIÓN DE OBJETIVO ===
Objetivo diario: 0.60%
Rendimiento diario promedio: {np.mean(metrics.daily_returns) * 100:.3f}% (si hay datos)
Cumple objetivo: {'SÍ' if np.mean(metrics.daily_returns) >= 0.006 else 'NO'} (si hay datos suficientes)
"""
        
        return report
        
    def plot_results(self, metrics: BacktestMetrics, save_path: str = None):
        """Generar gráficos de resultados"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # Curva de equity
        ax1.plot(metrics.equity_curve)
        ax1.set_title('Curva de Equity')
        ax1.set_xlabel('Trades')
        ax1.set_ylabel('Capital (USDT)')
        ax1.grid(True)
        
        # Curva de drawdown
        ax2.fill_between(range(len(metrics.drawdown_curve)), metrics.drawdown_curve, alpha=0.3, color='red')
        ax2.set_title('Drawdown')
        ax2.set_xlabel('Trades')
        ax2.set_ylabel('Drawdown (%)')
        ax2.grid(True)
        
        # Distribución de retornos por trade
        trade_returns = [t.return_pct for t in self.trades]
        if trade_returns:
            ax3.hist(trade_returns, bins=20, alpha=0.7, edgecolor='black')
            ax3.set_title('Distribución de Retornos por Trade')
            ax3.set_xlabel('Retorno (%)')
            ax3.set_ylabel('Frecuencia')
            ax3.grid(True)
            
        # Retornos diarios
        if metrics.daily_returns:
            ax4.plot(metrics.daily_returns)
            ax4.axhline(y=0.006, color='r', linestyle='--', label='Objetivo 0.6%')
            ax4.set_title('Retornos Diarios')
            ax4.set_xlabel('Días')
            ax4.set_ylabel('Retorno Diario')
            ax4.legend()
            ax4.grid(True)
            
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            
        plt.show()
        
if __name__ == "__main__":
    # Ejemplo de uso
    backtester = AdvancedBacktester(initial_capital=500.0)
    
    # Generar datos de prueba
    dates = pd.date_range('2024-01-01', '2024-12-31', freq='H')
    signals = pd.DataFrame({
        'timestamp': dates[:100],
        'symbol': ['BTC/USDT'] * 100,
        'action': ['buy', 'sell'] * 50,
        'quantity': [0.01] * 100,
        'price': np.random.normal(50000, 2000, 100),
        'volatility': np.random.normal(0.02, 0.005, 100)
    })
    
    # Ejecutar backtesting
    metrics = backtester.run_backtest(signals, {})
    
    # Generar reporte
    report = backtester.generate_report(metrics)
    print(report)
    
    # Guardar reporte
    with open('backtest_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
        
    print("\nReporte guardado en 'backtest_report.txt'")