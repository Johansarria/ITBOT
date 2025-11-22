"""
SICAR Indices Backtester
Backtester especializado para índices con datos históricos
Sistema avanzado de backtesting para estrategias de índices
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Union, Callable
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import dataclass, field
import warnings
import logging
from pathlib import Path
import json
import pickle

# Importar módulos del proyecto
from indices_data_provider import IndicesDataProvider, create_indices_provider
from indices_config import IndicesConfigManager, get_index_config
from indices_indicators import IndicesIndicators
from market_hours_system import MarketHoursSystem, MarketSession

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Trade:
    """Representa una operación de trading"""
    entry_time: datetime
    exit_time: Optional[datetime] = None
    symbol: str = ""
    side: str = "long"  # long/short
    entry_price: float = 0.0
    exit_price: float = 0.0
    quantity: int = 0
    commission: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    max_profit: float = 0.0
    max_loss: float = 0.0
    duration_minutes: int = 0
    exit_reason: str = ""
    strategy_name: str = ""
    
    def __post_init__(self):
        if self.exit_time and self.entry_time:
            self.duration_minutes = int((self.exit_time - self.entry_time).total_seconds() / 60)

@dataclass
class BacktestResults:
    """Resultados del backtesting"""
    # Métricas básicas
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # P&L
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    
    # Drawdown
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_duration: int = 0
    
    # Ratios
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Estadísticas adicionales
    avg_trade_duration: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    
    # Datos para análisis
    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=pd.Series)
    daily_returns: pd.Series = field(default_factory=pd.Series)
    
    # Métricas por período
    monthly_returns: pd.Series = field(default_factory=pd.Series)
    yearly_returns: pd.Series = field(default_factory=pd.Series)

class IndicesBacktester:
    """
    Backtester especializado para índices
    Incluye manejo de horarios de mercado, comisiones y análisis avanzado
    """
    
    def __init__(self, 
                 initial_capital: float = 100000,
                 commission_rate: float = 0.001,  # 0.1%
                 slippage: float = 0.0005,  # 0.05%
                 data_provider: Optional[IndicesDataProvider] = None):
        
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        
        # Componentes del sistema
        self.data_provider = data_provider or create_indices_provider()
        self.config_manager = IndicesConfigManager()
        self.indicators = IndicesIndicators()
        self.market_hours = MarketHoursSystem()
        
        # Estado del backtesting
        self.current_capital = initial_capital
        self.positions = {}  # symbol -> quantity
        self.trades = []
        self.equity_history = []
        self.daily_pnl = []
        
        # Cache de datos
        self.data_cache = {}
        
        # Configuración de análisis
        self.risk_free_rate = 0.02  # 2% anual
        
    def load_data(self, 
                  symbol: str, 
                  start_date: Union[str, datetime], 
                  end_date: Union[str, datetime],
                  timeframe: str = '1d') -> pd.DataFrame:
        """
        Carga datos históricos para un símbolo
        
        Args:
            symbol: Símbolo del índice (ej: 'SPY')
            start_date: Fecha de inicio
            end_date: Fecha de fin
            timeframe: Timeframe de los datos
        
        Returns:
            DataFrame con datos OHLCV
        """
        
        # Convertir fechas si es necesario
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Verificar cache
        cache_key = f"{symbol}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_{timeframe}"
        if cache_key in self.data_cache:
            return self.data_cache[cache_key].copy()
        
        try:
            # Cargar datos usando el data provider
            data = self.data_provider.get_historical_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval=timeframe
            )
            
            if data is not None and not data.empty:
                # Asegurar que tenemos las columnas necesarias
                required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                if all(col in data.columns for col in required_columns):
                    # Filtrar solo días de trading
                    data = self._filter_trading_days(data)
                    
                    # Guardar en cache
                    self.data_cache[cache_key] = data.copy()
                    
                    logger.info(f"Datos cargados para {symbol}: {len(data)} registros")
                    return data
                else:
                    logger.error(f"Columnas faltantes en datos de {symbol}")
                    return pd.DataFrame()
            else:
                logger.error(f"No se pudieron cargar datos para {symbol}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error cargando datos para {symbol}: {e}")
            return pd.DataFrame()
    
    def _filter_trading_days(self, data: pd.DataFrame) -> pd.DataFrame:
        """Filtra solo los días de trading válidos"""
        
        if data.empty:
            return data
        
        # Filtrar fines de semana y feriados
        trading_days = []
        
        for idx, row in data.iterrows():
            if isinstance(idx, str):
                date_obj = datetime.strptime(idx, '%Y-%m-%d').date()
            else:
                date_obj = idx.date() if hasattr(idx, 'date') else idx
            
            market_day = self.market_hours.get_market_day_info(date_obj)
            if market_day.is_trading_day:
                trading_days.append(idx)
        
        return data.loc[trading_days]
    
    def add_indicators(self, data: pd.DataFrame, config: Dict) -> pd.DataFrame:
        """
        Agrega indicadores técnicos a los datos
        
        Args:
            data: DataFrame con datos OHLCV
            config: Configuración de indicadores
        
        Returns:
            DataFrame con indicadores agregados
        """
        
        if data.empty:
            return data
        
        try:
            # Indicadores de momentum
            if 'rsi_period' in config:
                data['RSI'] = self.indicators.rsi(data['Close'], config['rsi_period'])
            
            if 'macd_fast' in config and 'macd_slow' in config:
                macd_data = self.indicators.macd(
                    data['Close'], 
                    config['macd_fast'], 
                    config['macd_slow'], 
                    config.get('macd_signal', 9)
                )
                data = pd.concat([data, macd_data], axis=1)
            
            # Indicadores de tendencia
            if 'ema_fast' in config:
                data['EMA_Fast'] = self.indicators.ema(data['Close'], config['ema_fast'])
            
            if 'ema_slow' in config:
                data['EMA_Slow'] = self.indicators.ema(data['Close'], config['ema_slow'])
            
            if 'sma_period' in config:
                data['SMA'] = self.indicators.sma(data['Close'], config['sma_period'])
            
            # Indicadores de volatilidad
            if 'atr_period' in config:
                data['ATR'] = self.indicators.atr(
                    data['High'], data['Low'], data['Close'], config['atr_period']
                )
            
            if 'bb_period' in config:
                bb_data = self.indicators.bollinger_bands(
                    data['Close'], 
                    config['bb_period'], 
                    config.get('bb_std', 2)
                )
                data = pd.concat([data, bb_data], axis=1)
            
            # Indicadores de volumen
            if 'volume_sma_period' in config:
                data['Volume_SMA'] = self.indicators.sma(data['Volume'], config['volume_sma_period'])
                data['Volume_Ratio'] = data['Volume'] / data['Volume_SMA']
            
            # Indicadores específicos de índices
            data['Session_Effect'] = self.indicators.session_effect(data.index)
            data['Weekend_Effect'] = self.indicators.weekend_effect(data.index)
            
            # Régimen de mercado
            if len(data) >= 50:
                data['Market_Regime'] = self.indicators.market_regime(data['Close'])
            
            logger.info(f"Indicadores agregados: {len(data.columns)} columnas totales")
            return data
            
        except Exception as e:
            logger.error(f"Error agregando indicadores: {e}")
            return data
    
    def run_backtest(self, 
                     strategy_func: Callable,
                     symbol: str,
                     start_date: Union[str, datetime],
                     end_date: Union[str, datetime],
                     strategy_config: Dict = None,
                     timeframe: str = '1d') -> BacktestResults:
        """
        Ejecuta un backtesting completo
        
        Args:
            strategy_func: Función de estrategia que genera señales
            symbol: Símbolo a testear
            start_date: Fecha de inicio
            end_date: Fecha de fin
            strategy_config: Configuración de la estrategia
            timeframe: Timeframe de los datos
        
        Returns:
            Resultados del backtesting
        """
        
        logger.info(f"Iniciando backtesting para {symbol} desde {start_date} hasta {end_date}")
        
        # Resetear estado
        self._reset_state()
        
        # Cargar datos
        data = self.load_data(symbol, start_date, end_date, timeframe)
        if data.empty:
            logger.error("No se pudieron cargar datos para el backtesting")
            return BacktestResults()
        
        # Obtener configuración del índice
        index_config = get_index_config(symbol)
        if strategy_config:
            index_config.update(strategy_config)
        
        # Agregar indicadores
        data = self.add_indicators(data, index_config)
        
        # Ejecutar estrategia
        signals = strategy_func(data, index_config)
        
        if signals is None or signals.empty:
            logger.warning("No se generaron señales de trading")
            return BacktestResults()
        
        # Procesar señales y ejecutar trades
        self._process_signals(data, signals, symbol, index_config)
        
        # Calcular métricas
        results = self._calculate_results()
        
        logger.info(f"Backtesting completado: {results.total_trades} trades, Win Rate: {results.win_rate:.2%}")
        
        return results
    
    def _reset_state(self):
        """Resetea el estado del backtester"""
        self.current_capital = self.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_history = []
        self.daily_pnl = []
    
    def _process_signals(self, data: pd.DataFrame, signals: pd.DataFrame, 
                        symbol: str, config: Dict):
        """Procesa las señales de trading y ejecuta las operaciones"""
        
        current_position = 0
        current_trade = None
        
        for idx, row in signals.iterrows():
            if idx not in data.index:
                continue
            
            price_data = data.loc[idx]
            signal = row.get('Signal', 0)
            
            # Verificar horarios de mercado
            if not self._is_trading_allowed(idx):
                continue
            
            # Procesar señal de entrada
            if signal != 0 and current_position == 0:
                current_trade = self._enter_position(
                    timestamp=idx,
                    symbol=symbol,
                    side='long' if signal > 0 else 'short',
                    price=price_data['Close'],
                    config=config
                )
                current_position = signal
            
            # Procesar señal de salida o stop loss/take profit
            elif current_position != 0:
                exit_signal = self._check_exit_conditions(
                    current_trade, price_data, row, config
                )
                
                if exit_signal:
                    self._exit_position(
                        trade=current_trade,
                        timestamp=idx,
                        price=price_data['Close'],
                        reason=exit_signal
                    )
                    current_position = 0
                    current_trade = None
            
            # Actualizar equity
            self._update_equity(idx, price_data)
    
    def _is_trading_allowed(self, timestamp) -> bool:
        """Verifica si se permite trading en el timestamp dado"""
        
        # Convertir timestamp a datetime si es necesario
        if isinstance(timestamp, str):
            dt = datetime.strptime(timestamp, '%Y-%m-%d')
        else:
            dt = timestamp
        
        # Para datos diarios, verificar solo si es día de trading
        market_day = self.market_hours.get_market_day_info(dt.date())
        return market_day.is_trading_day
    
    def _enter_position(self, timestamp, symbol: str, side: str, 
                       price: float, config: Dict) -> Trade:
        """Entra en una posición"""
        
        # Calcular tamaño de posición
        position_size = self._calculate_position_size(price, config)
        
        # Aplicar slippage
        entry_price = price * (1 + self.slippage if side == 'long' else 1 - self.slippage)
        
        # Calcular comisión
        commission = position_size * entry_price * self.commission_rate
        
        # Crear trade
        trade = Trade(
            entry_time=timestamp,
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            quantity=position_size,
            commission=commission,
            strategy_name="indices_strategy"
        )
        
        # Actualizar capital
        self.current_capital -= (position_size * entry_price + commission)
        
        logger.debug(f"Entrada {side}: {symbol} @ {entry_price:.2f}, Cantidad: {position_size}")
        
        return trade
    
    def _calculate_position_size(self, price: float, config: Dict) -> int:
        """Calcula el tamaño de la posición basado en el riesgo"""
        
        # Usar un porcentaje fijo del capital por defecto
        risk_per_trade = config.get('risk_per_trade', 0.02)  # 2%
        
        # Capital disponible para el trade
        available_capital = self.current_capital * risk_per_trade
        
        # Calcular cantidad de acciones
        position_size = int(available_capital / price)
        
        # Asegurar que no exceda el capital disponible
        max_position = int(self.current_capital * 0.95 / price)  # 95% del capital máximo
        
        return min(position_size, max_position, 1000)  # Máximo 1000 acciones por trade
    
    def _check_exit_conditions(self, trade: Trade, price_data: pd.Series, 
                              signal_data: pd.Series, config: Dict) -> Optional[str]:
        """Verifica condiciones de salida"""
        
        current_price = price_data['Close']
        
        # Stop Loss
        stop_loss_pct = config.get('stop_loss_pct', 0.05)  # 5%
        if trade.side == 'long':
            stop_price = trade.entry_price * (1 - stop_loss_pct)
            if current_price <= stop_price:
                return "stop_loss"
        else:
            stop_price = trade.entry_price * (1 + stop_loss_pct)
            if current_price >= stop_price:
                return "stop_loss"
        
        # Take Profit
        take_profit_pct = config.get('take_profit_pct', 0.10)  # 10%
        if trade.side == 'long':
            tp_price = trade.entry_price * (1 + take_profit_pct)
            if current_price >= tp_price:
                return "take_profit"
        else:
            tp_price = trade.entry_price * (1 - take_profit_pct)
            if current_price <= tp_price:
                return "take_profit"
        
        # Señal de salida
        exit_signal = signal_data.get('Exit_Signal', 0)
        if exit_signal != 0:
            return "signal_exit"
        
        # Máximo tiempo en posición
        max_hold_days = config.get('max_hold_days', 30)
        if hasattr(trade.entry_time, 'date'):
            entry_date = trade.entry_time.date()
        else:
            entry_date = trade.entry_time
        
        if hasattr(price_data.name, 'date'):
            current_date = price_data.name.date()
        else:
            current_date = price_data.name
        
        if (current_date - entry_date).days >= max_hold_days:
            return "max_hold"
        
        return None
    
    def _exit_position(self, trade: Trade, timestamp, price: float, reason: str):
        """Sale de una posición"""
        
        # Aplicar slippage
        exit_price = price * (1 - self.slippage if trade.side == 'long' else 1 + self.slippage)
        
        # Calcular comisión de salida
        exit_commission = trade.quantity * exit_price * self.commission_rate
        
        # Calcular P&L
        if trade.side == 'long':
            pnl = (exit_price - trade.entry_price) * trade.quantity
        else:
            pnl = (trade.entry_price - exit_price) * trade.quantity
        
        pnl -= (trade.commission + exit_commission)
        pnl_pct = pnl / (trade.entry_price * trade.quantity) * 100
        
        # Actualizar trade
        trade.exit_time = timestamp
        trade.exit_price = exit_price
        trade.pnl = pnl
        trade.pnl_pct = pnl_pct
        trade.exit_reason = reason
        trade.commission += exit_commission
        
        # Actualizar capital
        self.current_capital += (trade.quantity * exit_price - exit_commission)
        
        # Agregar a lista de trades
        self.trades.append(trade)
        
        logger.debug(f"Salida {trade.side}: {trade.symbol} @ {exit_price:.2f}, P&L: ${pnl:.2f}")
    
    def _update_equity(self, timestamp, price_data: pd.Series):
        """Actualiza la curva de equity"""
        
        # Calcular valor actual del portafolio
        portfolio_value = self.current_capital
        
        # Agregar valor de posiciones abiertas (si las hay)
        # Para simplificar, asumimos que no hay posiciones abiertas al final del día
        
        self.equity_history.append({
            'timestamp': timestamp,
            'equity': portfolio_value,
            'daily_return': (portfolio_value - self.initial_capital) / self.initial_capital
        })
    
    def _calculate_results(self) -> BacktestResults:
        """Calcula las métricas de rendimiento del backtesting"""
        
        if not self.trades:
            return BacktestResults()
        
        # Convertir trades a DataFrame para análisis
        trades_df = pd.DataFrame([
            {
                'entry_time': t.entry_time,
                'exit_time': t.exit_time,
                'symbol': t.symbol,
                'side': t.side,
                'pnl': t.pnl,
                'pnl_pct': t.pnl_pct,
                'duration': t.duration_minutes,
                'exit_reason': t.exit_reason
            }
            for t in self.trades
        ])
        
        # Métricas básicas
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t.pnl > 0])
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # P&L
        total_pnl = sum(t.pnl for t in self.trades)
        total_pnl_pct = (self.current_capital - self.initial_capital) / self.initial_capital * 100
        
        wins = [t.pnl for t in self.trades if t.pnl > 0]
        losses = [t.pnl for t in self.trades if t.pnl < 0]
        
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        
        profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else 0
        
        # Crear equity curve
        equity_df = pd.DataFrame(self.equity_history)
        if not equity_df.empty:
            equity_df.set_index('timestamp', inplace=True)
            equity_curve = equity_df['equity']
            daily_returns = equity_df['daily_return'].diff().dropna()
        else:
            equity_curve = pd.Series()
            daily_returns = pd.Series()
        
        # Drawdown
        if not equity_curve.empty:
            running_max = equity_curve.expanding().max()
            drawdown = (equity_curve - running_max) / running_max
            max_drawdown = drawdown.min()
            max_drawdown_pct = max_drawdown * 100
        else:
            max_drawdown = 0
            max_drawdown_pct = 0
        
        # Ratios de riesgo
        if not daily_returns.empty and len(daily_returns) > 1:
            sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)
            sortino_ratio = self._calculate_sortino_ratio(daily_returns)
        else:
            sharpe_ratio = 0
            sortino_ratio = 0
        
        calmar_ratio = (total_pnl_pct / 100) / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Estadísticas adicionales
        avg_trade_duration = np.mean([t.duration_minutes for t in self.trades]) if self.trades else 0
        
        # Rachas consecutivas
        consecutive_wins = 0
        consecutive_losses = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        
        for trade in self.trades:
            if trade.pnl > 0:
                consecutive_wins += 1
                consecutive_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
            else:
                consecutive_losses += 1
                consecutive_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        
        return BacktestResults(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            avg_trade_duration=avg_trade_duration,
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses,
            trades=self.trades,
            equity_curve=equity_curve,
            daily_returns=daily_returns
        )
    
    def _calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """Calcula el ratio de Sharpe"""
        if len(returns) == 0 or returns.std() == 0:
            return 0
        
        excess_returns = returns - (self.risk_free_rate / 252)  # Daily risk-free rate
        return excess_returns.mean() / returns.std() * np.sqrt(252)
    
    def _calculate_sortino_ratio(self, returns: pd.Series) -> float:
        """Calcula el ratio de Sortino"""
        if len(returns) == 0:
            return 0
        
        excess_returns = returns - (self.risk_free_rate / 252)
        downside_returns = returns[returns < 0]
        
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0
        
        return excess_returns.mean() / downside_returns.std() * np.sqrt(252)
    
    def plot_results(self, results: BacktestResults, save_path: Optional[str] = None):
        """
        Genera gráficos de los resultados del backtesting
        
        Args:
            results: Resultados del backtesting
            save_path: Ruta para guardar el gráfico
        """
        
        if results.total_trades == 0:
            logger.warning("No hay trades para graficar")
            return
        
        # Configurar el estilo
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Resultados del Backtesting - Índices SICAR', fontsize=16, fontweight='bold')
        
        # 1. Curva de Equity
        if not results.equity_curve.empty:
            axes[0, 0].plot(results.equity_curve.index, results.equity_curve.values, 
                           linewidth=2, color='blue', label='Equity')
            axes[0, 0].axhline(y=self.initial_capital, color='red', linestyle='--', 
                              alpha=0.7, label='Capital Inicial')
            axes[0, 0].set_title('Curva de Equity')
            axes[0, 0].set_ylabel('Valor del Portafolio ($)')
            axes[0, 0].legend()
            axes[0, 0].grid(True, alpha=0.3)
        
        # 2. Distribución de P&L
        pnl_values = [t.pnl for t in results.trades]
        axes[0, 1].hist(pnl_values, bins=20, alpha=0.7, color='green', edgecolor='black')
        axes[0, 1].axvline(x=0, color='red', linestyle='--', alpha=0.7)
        axes[0, 1].set_title('Distribución de P&L por Trade')
        axes[0, 1].set_xlabel('P&L ($)')
        axes[0, 1].set_ylabel('Frecuencia')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. Drawdown
        if not results.equity_curve.empty:
            running_max = results.equity_curve.expanding().max()
            drawdown = (results.equity_curve - running_max) / running_max * 100
            axes[1, 0].fill_between(drawdown.index, drawdown.values, 0, 
                                   alpha=0.7, color='red', label='Drawdown')
            axes[1, 0].set_title('Drawdown (%)')
            axes[1, 0].set_ylabel('Drawdown (%)')
            axes[1, 0].legend()
            axes[1, 0].grid(True, alpha=0.3)
        
        # 4. Métricas resumen
        axes[1, 1].axis('off')
        metrics_text = f"""
        MÉTRICAS DE RENDIMIENTO
        
        Total Trades: {results.total_trades}
        Win Rate: {results.win_rate:.2%}
        
        Total P&L: ${results.total_pnl:,.2f}
        Total Return: {results.total_pnl_pct:.2f}%
        
        Avg Win: ${results.avg_win:.2f}
        Avg Loss: ${results.avg_loss:.2f}
        Profit Factor: {results.profit_factor:.2f}
        
        Max Drawdown: {results.max_drawdown_pct:.2f}%
        Sharpe Ratio: {results.sharpe_ratio:.2f}
        Sortino Ratio: {results.sortino_ratio:.2f}
        
        Avg Trade Duration: {results.avg_trade_duration:.0f} min
        Max Consecutive Wins: {results.max_consecutive_wins}
        Max Consecutive Losses: {results.max_consecutive_losses}
        """
        
        axes[1, 1].text(0.1, 0.9, metrics_text, transform=axes[1, 1].transAxes,
                        fontsize=10, verticalalignment='top', fontfamily='monospace',
                        bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Gráfico guardado en: {save_path}")
        
        plt.show()
    
    def save_results(self, results: BacktestResults, filepath: str):
        """Guarda los resultados en un archivo"""
        
        # Preparar datos para serialización
        results_dict = {
            'metrics': {
                'total_trades': results.total_trades,
                'winning_trades': results.winning_trades,
                'losing_trades': results.losing_trades,
                'win_rate': results.win_rate,
                'total_pnl': results.total_pnl,
                'total_pnl_pct': results.total_pnl_pct,
                'avg_win': results.avg_win,
                'avg_loss': results.avg_loss,
                'profit_factor': results.profit_factor,
                'max_drawdown': results.max_drawdown,
                'max_drawdown_pct': results.max_drawdown_pct,
                'sharpe_ratio': results.sharpe_ratio,
                'sortino_ratio': results.sortino_ratio,
                'calmar_ratio': results.calmar_ratio,
                'avg_trade_duration': results.avg_trade_duration,
                'max_consecutive_wins': results.max_consecutive_wins,
                'max_consecutive_losses': results.max_consecutive_losses
            },
            'trades': [
                {
                    'entry_time': t.entry_time.isoformat() if t.entry_time else None,
                    'exit_time': t.exit_time.isoformat() if t.exit_time else None,
                    'symbol': t.symbol,
                    'side': t.side,
                    'entry_price': t.entry_price,
                    'exit_price': t.exit_price,
                    'quantity': t.quantity,
                    'pnl': t.pnl,
                    'pnl_pct': t.pnl_pct,
                    'duration_minutes': t.duration_minutes,
                    'exit_reason': t.exit_reason
                }
                for t in results.trades
            ]
        }
        
        # Guardar como JSON
        with open(filepath, 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        logger.info(f"Resultados guardados en: {filepath}")

# Función de utilidad para crear un backtester
def create_indices_backtester(initial_capital: float = 100000,
                             commission_rate: float = 0.001) -> IndicesBacktester:
    """Crea una instancia del backtester de índices"""
    return IndicesBacktester(
        initial_capital=initial_capital,
        commission_rate=commission_rate
    )

if __name__ == "__main__":
    # Ejemplo de uso básico
    backtester = create_indices_backtester()
    
    # Cargar datos de ejemplo
    data = backtester.load_data('SPY', '2023-01-01', '2023-12-31')
    print(f"Datos cargados: {len(data)} registros")
    
    if not data.empty:
        print(f"Rango de fechas: {data.index[0]} a {data.index[-1]}")
        print(f"Columnas disponibles: {list(data.columns)}")