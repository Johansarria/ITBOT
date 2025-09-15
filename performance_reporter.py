import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from trade_executor import TradingSimulator, TradeResult, Position
from trading_signals import StrategyType, SignalType
from portfolio_manager import PortfolioManager

logger = logging.getLogger(__name__)

class ReportType(Enum):
    """Tipos de reportes"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    REAL_TIME = "real_time"
    TRADE_ANALYSIS = "trade_analysis"
    STRATEGY_PERFORMANCE = "strategy_performance"
    RISK_ANALYSIS = "risk_analysis"

@dataclass
class PerformanceSnapshot:
    """Snapshot de performance en un momento específico"""
    timestamp: datetime
    total_capital: float
    available_capital: float
    invested_capital: float
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    total_return_pct: float
    daily_return_pct: float
    open_positions: int
    total_trades: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown_pct: float
    current_drawdown_pct: float
    risk_exposure_pct: float
    
@dataclass
class StrategyMetrics:
    """Métricas por estrategia"""
    strategy_type: StrategyType
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    average_win: float
    average_loss: float
    profit_factor: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    average_trade_duration: timedelta
    best_trade: float
    worst_trade: float
    total_commission: float
    
class PerformanceReporter:
    """Sistema de reportes de performance en tiempo real"""
    
    def __init__(self, simulator: TradingSimulator, portfolio_manager: PortfolioManager, 
                 output_dir: str = "reports"):
        self.simulator = simulator
        self.portfolio_manager = portfolio_manager
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Historial de snapshots
        self.performance_history: List[PerformanceSnapshot] = []
        self.last_snapshot_time = datetime.now()
        
        # Configuración de reportes
        self.snapshot_interval = timedelta(minutes=5)  # Snapshot cada 5 minutos
        self.auto_report_interval = timedelta(hours=1)  # Reporte automático cada hora
        self.last_auto_report = datetime.now()
        
        # Métricas acumuladas
        self.daily_snapshots: Dict[str, PerformanceSnapshot] = {}  # Por fecha
        self.strategy_metrics: Dict[StrategyType, StrategyMetrics] = {}
        
    def update_performance_snapshot(self, current_prices: Dict[str, float]):
        """Actualiza snapshot de performance"""
        now = datetime.now()
        
        # Verificar si es tiempo de crear nuevo snapshot
        if now - self.last_snapshot_time < self.snapshot_interval:
            return
            
        try:
            # Calcular métricas actuales
            total_capital = self.simulator._calculate_total_portfolio_value(current_prices)
            available_capital = self.simulator.current_capital
            invested_capital = total_capital - available_capital
            
            # PnL no realizado de posiciones abiertas
            unrealized_pnl = sum(
                pos.unrealized_pnl for pos in self.simulator.positions.values() 
                if pos.status.value == 'open'
            )
            
            # PnL realizado de trades cerrados
            realized_pnl = sum(trade.net_pnl for trade in self.simulator.closed_trades)
            total_pnl = unrealized_pnl + realized_pnl
            
            # Retornos
            total_return_pct = ((total_capital - self.simulator.initial_capital) / 
                              self.simulator.initial_capital) * 100
            
            # Retorno diario
            daily_return_pct = 0.0
            if self.performance_history:
                yesterday_capital = self.performance_history[-1].total_capital
                daily_return_pct = ((total_capital - yesterday_capital) / yesterday_capital) * 100
                
            # Métricas de trading
            metrics = self.simulator.get_performance_metrics()
            
            # Exposición al riesgo
            risk_exposure_pct = self.simulator._calculate_current_risk() * 100
            
            # Drawdown actual
            current_drawdown_pct = 0.0
            if self.simulator.peak_capital > 0:
                current_drawdown_pct = ((self.simulator.peak_capital - total_capital) / 
                                      self.simulator.peak_capital) * 100
                
            # Crear snapshot
            snapshot = PerformanceSnapshot(
                timestamp=now,
                total_capital=total_capital,
                available_capital=available_capital,
                invested_capital=invested_capital,
                unrealized_pnl=unrealized_pnl,
                realized_pnl=realized_pnl,
                total_pnl=total_pnl,
                total_return_pct=total_return_pct,
                daily_return_pct=daily_return_pct,
                open_positions=len([p for p in self.simulator.positions.values() if p.status.value == 'open']),
                total_trades=metrics['total_trades'],
                win_rate=metrics['win_rate'],
                profit_factor=metrics['profit_factor'],
                sharpe_ratio=metrics['sharpe_ratio'],
                max_drawdown_pct=metrics['max_drawdown'],
                current_drawdown_pct=current_drawdown_pct,
                risk_exposure_pct=risk_exposure_pct
            )
            
            self.performance_history.append(snapshot)
            self.last_snapshot_time = now
            
            # Guardar snapshot diario
            date_key = now.strftime('%Y-%m-%d')
            self.daily_snapshots[date_key] = snapshot
            
            # Actualizar métricas por estrategia
            self._update_strategy_metrics()
            
            # Verificar si es tiempo de reporte automático
            if now - self.last_auto_report >= self.auto_report_interval:
                self.generate_real_time_report()
                self.last_auto_report = now
                
        except Exception as e:
            logger.error(f"Error actualizando snapshot de performance: {e}")
            
    def _update_strategy_metrics(self):
        """Actualiza métricas por estrategia"""
        strategy_trades = {}
        
        # Agrupar trades por estrategia
        for trade in self.simulator.closed_trades:
            if trade.strategy_type not in strategy_trades:
                strategy_trades[trade.strategy_type] = []
            strategy_trades[trade.strategy_type].append(trade)
            
        # Calcular métricas para cada estrategia
        for strategy_type, trades in strategy_trades.items():
            if not trades:
                continue
                
            winning_trades = [t for t in trades if t.net_pnl > 0]
            losing_trades = [t for t in trades if t.net_pnl < 0]
            
            # Calcular rachas consecutivas
            max_consecutive_wins = self._calculate_max_consecutive(trades, True)
            max_consecutive_losses = self._calculate_max_consecutive(trades, False)
            
            # Duración promedio
            avg_duration = np.mean([t.duration.total_seconds() for t in trades])
            avg_duration_td = timedelta(seconds=avg_duration)
            
            # Profit factor
            gross_profit = sum(t.net_pnl for t in winning_trades)
            gross_loss = abs(sum(t.net_pnl for t in losing_trades))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            metrics = StrategyMetrics(
                strategy_type=strategy_type,
                total_trades=len(trades),
                winning_trades=len(winning_trades),
                losing_trades=len(losing_trades),
                win_rate=(len(winning_trades) / len(trades)) * 100,
                total_pnl=sum(t.net_pnl for t in trades),
                average_win=np.mean([t.net_pnl for t in winning_trades]) if winning_trades else 0,
                average_loss=np.mean([t.net_pnl for t in losing_trades]) if losing_trades else 0,
                profit_factor=profit_factor,
                max_consecutive_wins=max_consecutive_wins,
                max_consecutive_losses=max_consecutive_losses,
                average_trade_duration=avg_duration_td,
                best_trade=max(t.net_pnl for t in trades),
                worst_trade=min(t.net_pnl for t in trades),
                total_commission=sum(t.commission for t in trades)
            )
            
            self.strategy_metrics[strategy_type] = metrics
            
    def _calculate_max_consecutive(self, trades: List[TradeResult], wins: bool) -> int:
        """Calcula máximo número de trades consecutivos ganadores/perdedores"""
        if not trades:
            return 0
            
        max_consecutive = 0
        current_consecutive = 0
        
        for trade in sorted(trades, key=lambda x: x.exit_timestamp):
            is_win = trade.net_pnl > 0
            
            if (wins and is_win) or (not wins and not is_win):
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
                
        return max_consecutive
        
    def generate_real_time_report(self) -> Dict[str, Any]:
        """Genera reporte en tiempo real"""
        try:
            if not self.performance_history:
                return {}
                
            current_snapshot = self.performance_history[-1]
            
            # Reporte básico
            report = {
                'timestamp': current_snapshot.timestamp.isoformat(),
                'report_type': ReportType.REAL_TIME.value,
                'summary': {
                    'total_capital': current_snapshot.total_capital,
                    'total_return_pct': current_snapshot.total_return_pct,
                    'daily_return_pct': current_snapshot.daily_return_pct,
                    'unrealized_pnl': current_snapshot.unrealized_pnl,
                    'realized_pnl': current_snapshot.realized_pnl,
                    'open_positions': current_snapshot.open_positions,
                    'win_rate': current_snapshot.win_rate,
                    'profit_factor': current_snapshot.profit_factor,
                    'max_drawdown_pct': current_snapshot.max_drawdown_pct,
                    'current_drawdown_pct': current_snapshot.current_drawdown_pct,
                    'risk_exposure_pct': current_snapshot.risk_exposure_pct
                },
                'positions': self.simulator.get_open_positions_summary(),
                'recent_trades': self.simulator.get_trade_history(limit=10),
                'strategy_performance': self._get_strategy_performance_summary(),
                'risk_metrics': self._calculate_risk_metrics(),
                'alerts': self._generate_alerts(current_snapshot)
            }
            
            # Guardar reporte
            filename = f"real_time_report_{current_snapshot.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            filepath = self.output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
                
            logger.info(f"Reporte en tiempo real generado: {filepath}")
            return report
            
        except Exception as e:
            logger.error(f"Error generando reporte en tiempo real: {e}")
            return {}
            
    def _get_strategy_performance_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de performance por estrategia"""
        summary = {}
        
        for strategy_type, metrics in self.strategy_metrics.items():
            summary[strategy_type.value] = {
                'total_trades': metrics.total_trades,
                'win_rate': metrics.win_rate,
                'total_pnl': metrics.total_pnl,
                'profit_factor': metrics.profit_factor,
                'average_win': metrics.average_win,
                'average_loss': metrics.average_loss,
                'best_trade': metrics.best_trade,
                'worst_trade': metrics.worst_trade,
                'avg_duration_hours': metrics.average_trade_duration.total_seconds() / 3600
            }
            
        return summary
        
    def _calculate_risk_metrics(self) -> Dict[str, float]:
        """Calcula métricas de riesgo"""
        if len(self.performance_history) < 2:
            return {}
            
        # Calcular volatilidad de retornos
        returns = []
        for i in range(1, len(self.performance_history)):
            prev_capital = self.performance_history[i-1].total_capital
            curr_capital = self.performance_history[i].total_capital
            daily_return = (curr_capital - prev_capital) / prev_capital
            returns.append(daily_return)
            
        if not returns:
            return {}
            
        volatility = np.std(returns) * np.sqrt(252)  # Anualizada
        
        # VaR (Value at Risk) al 95%
        var_95 = np.percentile(returns, 5) * self.performance_history[-1].total_capital
        
        # Calmar Ratio (retorno anual / max drawdown)
        annual_return = np.mean(returns) * 252
        calmar_ratio = annual_return / (self.performance_history[-1].max_drawdown_pct / 100) if self.performance_history[-1].max_drawdown_pct > 0 else 0
        
        return {
            'volatility_annual': volatility,
            'var_95_daily': var_95,
            'calmar_ratio': calmar_ratio,
            'current_risk_exposure': self.performance_history[-1].risk_exposure_pct,
            'max_drawdown': self.performance_history[-1].max_drawdown_pct,
            'current_drawdown': self.performance_history[-1].current_drawdown_pct
        }
        
    def _generate_alerts(self, snapshot: PerformanceSnapshot) -> List[Dict[str, str]]:
        """Genera alertas basadas en métricas actuales"""
        alerts = []
        
        # Alerta de drawdown alto
        if snapshot.current_drawdown_pct > 10:
            alerts.append({
                'type': 'WARNING',
                'message': f'Drawdown actual alto: {snapshot.current_drawdown_pct:.2f}%',
                'severity': 'HIGH' if snapshot.current_drawdown_pct > 15 else 'MEDIUM'
            })
            
        # Alerta de exposición al riesgo alta
        if snapshot.risk_exposure_pct > 8:
            alerts.append({
                'type': 'WARNING',
                'message': f'Exposición al riesgo alta: {snapshot.risk_exposure_pct:.2f}%',
                'severity': 'HIGH' if snapshot.risk_exposure_pct > 12 else 'MEDIUM'
            })
            
        # Alerta de muchas posiciones abiertas
        if snapshot.open_positions > 8:
            alerts.append({
                'type': 'INFO',
                'message': f'Muchas posiciones abiertas: {snapshot.open_positions}',
                'severity': 'LOW'
            })
            
        # Alerta de retorno diario extremo
        if abs(snapshot.daily_return_pct) > 5:
            alerts.append({
                'type': 'INFO',
                'message': f'Retorno diario extremo: {snapshot.daily_return_pct:.2f}%',
                'severity': 'MEDIUM'
            })
            
        # Alerta de win rate bajo
        if snapshot.total_trades > 10 and snapshot.win_rate < 40:
            alerts.append({
                'type': 'WARNING',
                'message': f'Win rate bajo: {snapshot.win_rate:.1f}%',
                'severity': 'MEDIUM'
            })
            
        return alerts
        
    def generate_daily_report(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Genera reporte diario"""
        if date is None:
            date = datetime.now()
            
        date_key = date.strftime('%Y-%m-%d')
        
        if date_key not in self.daily_snapshots:
            logger.warning(f"No hay datos para la fecha {date_key}")
            return {}
            
        snapshot = self.daily_snapshots[date_key]
        
        # Trades del día
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        daily_trades = [
            trade for trade in self.simulator.closed_trades
            if day_start <= trade.exit_timestamp < day_end
        ]
        
        # Métricas del día
        daily_pnl = sum(trade.net_pnl for trade in daily_trades)
        daily_commission = sum(trade.commission for trade in daily_trades)
        daily_wins = len([t for t in daily_trades if t.net_pnl > 0])
        daily_losses = len([t for t in daily_trades if t.net_pnl < 0])
        
        report = {
            'date': date_key,
            'report_type': ReportType.DAILY.value,
            'summary': {
                'total_capital': snapshot.total_capital,
                'daily_return_pct': snapshot.daily_return_pct,
                'daily_pnl': daily_pnl,
                'trades_count': len(daily_trades),
                'winning_trades': daily_wins,
                'losing_trades': daily_losses,
                'win_rate': (daily_wins / len(daily_trades)) * 100 if daily_trades else 0,
                'commission_paid': daily_commission,
                'open_positions_eod': snapshot.open_positions
            },
            'trades': [
                {
                    'symbol': trade.symbol,
                    'strategy': trade.strategy_type.value if trade.strategy_type else None,
                    'pnl': trade.net_pnl,
                    'return_pct': trade.return_pct,
                    'duration_hours': trade.duration.total_seconds() / 3600,
                    'exit_reason': trade.exit_reason
                }
                for trade in daily_trades
            ],
            'performance_metrics': {
                'total_return_pct': snapshot.total_return_pct,
                'max_drawdown_pct': snapshot.max_drawdown_pct,
                'sharpe_ratio': snapshot.sharpe_ratio,
                'profit_factor': snapshot.profit_factor
            }
        }
        
        # Guardar reporte
        filename = f"daily_report_{date_key}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            
        return report
        
    def generate_strategy_analysis_report(self) -> Dict[str, Any]:
        """Genera análisis detallado por estrategia"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'report_type': ReportType.STRATEGY_PERFORMANCE.value,
            'strategies': {}
        }
        
        for strategy_type, metrics in self.strategy_metrics.items():
            # Trades de esta estrategia
            strategy_trades = [
                trade for trade in self.simulator.closed_trades
                if trade.strategy_type == strategy_type
            ]
            
            if not strategy_trades:
                continue
                
            # Análisis de distribución de retornos
            returns = [trade.return_pct for trade in strategy_trades]
            
            # Análisis temporal
            monthly_performance = self._analyze_monthly_performance(strategy_trades)
            
            strategy_analysis = {
                'basic_metrics': asdict(metrics),
                'return_distribution': {
                    'mean': np.mean(returns),
                    'std': np.std(returns),
                    'min': np.min(returns),
                    'max': np.max(returns),
                    'percentile_25': np.percentile(returns, 25),
                    'percentile_75': np.percentile(returns, 75)
                },
                'monthly_performance': monthly_performance,
                'symbol_performance': self._analyze_symbol_performance(strategy_trades),
                'time_analysis': self._analyze_trade_timing(strategy_trades)
            }
            
            report['strategies'][strategy_type.value] = strategy_analysis
            
        # Guardar reporte
        filename = f"strategy_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            
        return report
        
    def _analyze_monthly_performance(self, trades: List[TradeResult]) -> Dict[str, Any]:
        """Analiza performance mensual"""
        monthly_data = {}
        
        for trade in trades:
            month_key = trade.exit_timestamp.strftime('%Y-%m')
            
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'trades': 0,
                    'pnl': 0,
                    'wins': 0,
                    'losses': 0
                }
                
            monthly_data[month_key]['trades'] += 1
            monthly_data[month_key]['pnl'] += trade.net_pnl
            
            if trade.net_pnl > 0:
                monthly_data[month_key]['wins'] += 1
            else:
                monthly_data[month_key]['losses'] += 1
                
        # Calcular métricas mensuales
        for month_key, data in monthly_data.items():
            data['win_rate'] = (data['wins'] / data['trades']) * 100 if data['trades'] > 0 else 0
            
        return monthly_data
        
    def _analyze_symbol_performance(self, trades: List[TradeResult]) -> Dict[str, Any]:
        """Analiza performance por símbolo"""
        symbol_data = {}
        
        for trade in trades:
            symbol = trade.symbol
            
            if symbol not in symbol_data:
                symbol_data[symbol] = {
                    'trades': 0,
                    'pnl': 0,
                    'wins': 0,
                    'losses': 0,
                    'total_return_pct': 0
                }
                
            symbol_data[symbol]['trades'] += 1
            symbol_data[symbol]['pnl'] += trade.net_pnl
            symbol_data[symbol]['total_return_pct'] += trade.return_pct
            
            if trade.net_pnl > 0:
                symbol_data[symbol]['wins'] += 1
            else:
                symbol_data[symbol]['losses'] += 1
                
        # Calcular métricas por símbolo
        for symbol, data in symbol_data.items():
            data['win_rate'] = (data['wins'] / data['trades']) * 100 if data['trades'] > 0 else 0
            data['avg_return_pct'] = data['total_return_pct'] / data['trades'] if data['trades'] > 0 else 0
            
        return symbol_data
        
    def _analyze_trade_timing(self, trades: List[TradeResult]) -> Dict[str, Any]:
        """Analiza timing de trades"""
        if not trades:
            return {}
            
        # Análisis por hora del día
        hourly_performance = {}
        
        for trade in trades:
            hour = trade.entry_timestamp.hour
            
            if hour not in hourly_performance:
                hourly_performance[hour] = {
                    'trades': 0,
                    'pnl': 0,
                    'wins': 0
                }
                
            hourly_performance[hour]['trades'] += 1
            hourly_performance[hour]['pnl'] += trade.net_pnl
            
            if trade.net_pnl > 0:
                hourly_performance[hour]['wins'] += 1
                
        # Calcular win rate por hora
        for hour, data in hourly_performance.items():
            data['win_rate'] = (data['wins'] / data['trades']) * 100 if data['trades'] > 0 else 0
            
        # Duración promedio de trades
        durations = [trade.duration.total_seconds() / 3600 for trade in trades]  # En horas
        
        return {
            'hourly_performance': hourly_performance,
            'average_duration_hours': np.mean(durations),
            'median_duration_hours': np.median(durations),
            'min_duration_hours': np.min(durations),
            'max_duration_hours': np.max(durations)
        }
        
    def get_current_status(self) -> Dict[str, Any]:
        """Obtiene estado actual del sistema"""
        if not self.performance_history:
            return {'status': 'No data available'}
            
        current = self.performance_history[-1]
        
        return {
            'timestamp': current.timestamp.isoformat(),
            'status': 'ACTIVE',
            'capital': {
                'total': current.total_capital,
                'available': current.available_capital,
                'invested': current.invested_capital,
                'initial': self.simulator.initial_capital
            },
            'performance': {
                'total_return_pct': current.total_return_pct,
                'daily_return_pct': current.daily_return_pct,
                'unrealized_pnl': current.unrealized_pnl,
                'realized_pnl': current.realized_pnl
            },
            'trading': {
                'open_positions': current.open_positions,
                'total_trades': current.total_trades,
                'win_rate': current.win_rate,
                'profit_factor': current.profit_factor
            },
            'risk': {
                'current_drawdown_pct': current.current_drawdown_pct,
                'max_drawdown_pct': current.max_drawdown_pct,
                'risk_exposure_pct': current.risk_exposure_pct
            }
        }
        
    def export_performance_data(self, format: str = 'csv') -> str:
        """Exporta datos de performance"""
        if not self.performance_history:
            return ""
            
        # Convertir a DataFrame
        df = pd.DataFrame([asdict(snapshot) for snapshot in self.performance_history])
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format.lower() == 'csv':
            filename = f"performance_data_{timestamp}.csv"
            filepath = self.output_dir / filename
            df.to_csv(filepath, index=False)
        elif format.lower() == 'excel':
            filename = f"performance_data_{timestamp}.xlsx"
            filepath = self.output_dir / filename
            df.to_excel(filepath, index=False)
        else:
            raise ValueError(f"Formato no soportado: {format}")
            
        logger.info(f"Datos de performance exportados: {filepath}")
        return str(filepath)

if __name__ == "__main__":
    # Ejemplo de uso
    from trade_executor import TradingSimulator
    from portfolio_manager import PortfolioManager
    
    # Inicializar componentes
    simulator = TradingSimulator(initial_capital=10000.0)
    portfolio_manager = PortfolioManager()
    reporter = PerformanceReporter(simulator, portfolio_manager)
    
    # Simular algunos datos
    current_prices = {
        'BTCUSDT': 45000.0,
        'ETHUSDT': 2500.0,
        'BNBUSDT': 300.0
    }
    
    # Actualizar snapshot
    reporter.update_performance_snapshot(current_prices)
    
    # Generar reportes
    real_time_report = reporter.generate_real_time_report()
    print(f"Reporte en tiempo real generado con {len(real_time_report)} secciones")
    
    # Mostrar estado actual
    status = reporter.get_current_status()
    print(f"\nEstado actual:")
    print(f"Capital total: ${status['capital']['total']:.2f}")
    print(f"Retorno total: {status['performance']['total_return_pct']:.2f}%")
    print(f"Posiciones abiertas: {status['trading']['open_positions']}")