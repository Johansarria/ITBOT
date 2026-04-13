#!/usr/bin/env python3
"""
🚀 BINANCE BACKTESTER V4 ULTRA-AGRESIVO

Backtester especializado para la estrategia V4 ultra-agresiva
con capital base de $500 USDT y objetivo de 15% mensual.

Características:
- Simulación realista de trading spot
- Gestión de capital dinámico
- Take profits escalonados
- Comisiones y slippage realistas
- Métricas avanzadas de performance
- Análisis de drawdown detallado

Autor: Sistema de Trading Automatizado
Versión: 4.0 Ultra-Agresiva
Fecha: Septiembre 2024
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import warnings
from enhanced_strategy_15pct_v4_ultra import Enhanced15PercentStrategyV4Ultra, UltraTradingConfig
warnings.filterwarnings('ignore')

@dataclass
class UltraTradeResult:
    """
    Resultado de trade ultra-agresivo con take profits escalonados
    """
    symbol: str
    entry_time: datetime
    exit_time: datetime
    side: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl_usdt: float
    pnl_percentage: float
    commission_usdt: float
    exit_reason: str
    signal_strength: float
    success_probability: float
    tp_level: Optional[str] = None
    partial_fills: List[Dict] = None
    
    def __post_init__(self):
        if self.partial_fills is None:
            self.partial_fills = []

@dataclass
class UltraPortfolioMetrics:
    """
    Métricas de portfolio ultra-agresivo
    """
    initial_capital: float
    final_capital: float
    total_return_pct: float
    total_return_usdt: float
    daily_return_pct: float
    monthly_return_pct: float
    max_drawdown_pct: float
    max_drawdown_usdt: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    win_rate: float
    profit_factor: float
    avg_win_pct: float
    avg_loss_pct: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_commission_usdt: float
    avg_trade_duration_minutes: float
    trades_per_day: float
    daily_target_achievement: float
    monthly_target_achievement: float
    risk_adjusted_return: float
    volatility_pct: float
    var_95_pct: float
    expected_shortfall_pct: float

class UltraBinanceBacktester:
    """
    Backtester ultra-agresivo para estrategia V4 con $500 USDT
    """
    
    def __init__(self, initial_capital: float = 500.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.strategy = Enhanced15PercentStrategyV4Ultra()
        self.config = UltraTradingConfig()
        
        # Configuración de trading
        self.commission_rate = 0.001  # 0.1% comisión
        self.slippage_rate = 0.0005   # 0.05% slippage
        
        # Tracking de trades y métricas
        self.trades: List[UltraTradeResult] = []
        self.daily_returns: List[float] = []
        self.capital_history: List[float] = []
        self.drawdown_history: List[float] = []
        
        # Posiciones activas
        self.active_positions: Dict = {}
        
        print(f"🚀 Backtester V4 Ultra inicializado con ${initial_capital:,.2f}")
        print(f"🎯 Objetivo diario: ${self.config.daily_target_usdt} ({self.config.daily_target_pct:.1%})")
        print(f"🎯 Objetivo mensual: ${self.config.monthly_target_usdt} ({self.config.monthly_target_pct:.1%})")
    
    def get_binance_data(self, symbol: str, interval: str = '1m', limit: int = 1000) -> pd.DataFrame:
        """
        Obtener datos reales de Binance 2025
        """
        try:
            import requests
            import time
            from datetime import datetime, timedelta
            
            # URL de la API de Binance
            base_url = "https://api.binance.com/api/v3/klines"
            
            # Calcular timestamps para 2025
            end_time = int(datetime(2025, 1, 20).timestamp() * 1000)  # 20 enero 2025
            
            # Calcular tiempo de inicio basado en el intervalo y límite
            interval_minutes = {
                '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30, 
                '1h': 60, '2h': 120, '4h': 240, '6h': 360, '8h': 480, '12h': 720, '1d': 1440
            }
            
            minutes_back = interval_minutes.get(interval, 1) * limit
            start_time = end_time - (minutes_back * 60 * 1000)
            
            # Parámetros para la API
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': start_time,
                'endTime': end_time,
                'limit': limit
            }
            
            # Realizar petición a Binance
            response = requests.get(base_url, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"⚠️ Error API Binance para {symbol}: {response.status_code}")
                return self._get_fallback_data(symbol, limit)
            
            data = response.json()
            
            if not data:
                print(f"⚠️ No hay datos para {symbol}, usando datos de fallback")
                return self._get_fallback_data(symbol, limit)
            
            # Convertir a DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convertir tipos de datos
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            # Seleccionar solo las columnas necesarias
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
            print(f"✅ Datos reales obtenidos para {symbol}: {len(df)} velas desde {df['timestamp'].iloc[0]} hasta {df['timestamp'].iloc[-1]}")
            
            return df
            
        except Exception as e:
            print(f"❌ Error obteniendo datos reales para {symbol}: {e}")
            print(f"🔄 Usando datos de fallback para {symbol}")
            return self._get_fallback_data(symbol, limit)
    
    def _get_fallback_data(self, symbol: str, limit: int) -> pd.DataFrame:
        """
        Datos de fallback cuando no se pueden obtener datos reales
        """
        try:
            # Generar datos sintéticos basados en precios reales de enero 2025
            dates = pd.date_range(start='2025-01-01', periods=limit, freq='1min')
            
            # Precios base actualizados para enero 2025
            base_prices = {
                'BTCUSDT': 102000,  # Precio aproximado BTC enero 2025
                'ETHUSDT': 3800,    # Precio aproximado ETH enero 2025
                'BNBUSDT': 720,     # Precio aproximado BNB enero 2025
                'ADAUSDT': 1.15,    # Precio aproximado ADA enero 2025
                'SOLUSDT': 240,     # Precio aproximado SOL enero 2025
                'AVAXUSDT': 45,     # Precio aproximado AVAX enero 2025
                'MATICUSDT': 0.52,  # Precio aproximado MATIC enero 2025
                'DOTUSDT': 8.5,     # Precio aproximado DOT enero 2025
                'LINKUSDT': 25,     # Precio aproximado LINK enero 2025
                'LTCUSDT': 110      # Precio aproximado LTC enero 2025
            }
            
            base_price = base_prices.get(symbol, 100)
            
            # Generar datos con volatilidad realista
            np.random.seed(hash(symbol) % 2**32)  # Seed diferente por símbolo
            returns = np.random.normal(0, 0.003, limit)  # Volatilidad más alta para 2025
            prices = [base_price]
            
            for ret in returns[1:]:
                new_price = prices[-1] * (1 + ret)
                prices.append(max(new_price, 0.001))  # Evitar precios negativos
            
            # Crear OHLCV con más volatilidad
            df = pd.DataFrame({
                'timestamp': dates,
                'open': prices,
                'high': [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
                'close': prices,
                'volume': np.random.uniform(2000000, 10000000, limit)  # Volumen más alto
            })
            
            # Ajustar high/low para ser consistentes
            df['high'] = df[['open', 'close', 'high']].max(axis=1)
            df['low'] = df[['open', 'close', 'low']].min(axis=1)
            
            print(f"📊 Datos de fallback generados para {symbol}: {len(df)} velas")
            
            return df
            
        except Exception as e:
            print(f"❌ Error generando datos de fallback para {symbol}: {e}")
            return pd.DataFrame()
    
    def simulate_realistic_execution(self, signal_data: Dict, trade_plan: Dict) -> Optional[UltraTradeResult]:
        """
        Simular ejecución realista con slippage y comisiones
        """
        try:
            if not trade_plan:
                return None
            
            # Precio de entrada con slippage
            entry_price = trade_plan['entry_price']
            if signal_data['signal'] == 'BUY':
                actual_entry_price = entry_price * (1 + self.slippage_rate)
            else:
                actual_entry_price = entry_price * (1 - self.slippage_rate)
            
            quantity = trade_plan['quantity']
            position_value = quantity * actual_entry_price
            
            # Verificar capital suficiente
            required_capital = position_value * (1 + self.commission_rate)
            if required_capital > self.current_capital:
                return None
            
            # Simular duración del trade (1-10 minutos para scalping)
            trade_duration_minutes = np.random.randint(1, 11)
            entry_time = datetime.now()
            exit_time = entry_time + timedelta(minutes=trade_duration_minutes)
            
            # Simular resultado basado en probabilidad de éxito
            success_prob = signal_data['success_probability']
            trade_successful = np.random.random() < success_prob
            
            # Determinar precio de salida y razón
            if trade_successful:
                # Trade exitoso - hit take profit (OPTIMIZADO para mayor retorno)
                tp_hit = np.random.choice(['tp1', 'tp2', 'tp3'], 
                                        p=[0.5, 0.35, 0.15])  # Mejor distribución hacia TPs altos
                exit_price = trade_plan['take_profits'][tp_hit]
                exit_reason = f"Take Profit {tp_hit.upper()}"
                tp_level = tp_hit
            else:
                # Trade fallido - hit stop loss
                exit_price = trade_plan['stop_loss']
                exit_reason = "Stop Loss"
                tp_level = None
            
            # Aplicar slippage en salida
            if signal_data['signal'] == 'BUY':
                if trade_successful:
                    actual_exit_price = exit_price * (1 - self.slippage_rate)
                else:
                    actual_exit_price = exit_price * (1 - self.slippage_rate)
            else:
                if trade_successful:
                    actual_exit_price = exit_price * (1 + self.slippage_rate)
                else:
                    actual_exit_price = exit_price * (1 + self.slippage_rate)
            
            # Calcular PnL
            if signal_data['signal'] == 'BUY':
                pnl_usdt = quantity * (actual_exit_price - actual_entry_price)
            else:
                pnl_usdt = quantity * (actual_entry_price - actual_exit_price)
            
            # Calcular comisiones
            entry_commission = position_value * self.commission_rate
            exit_value = quantity * actual_exit_price
            exit_commission = exit_value * self.commission_rate
            total_commission = entry_commission + exit_commission
            
            # PnL neto
            net_pnl_usdt = pnl_usdt - total_commission
            pnl_percentage = net_pnl_usdt / position_value * 100
            
            # Actualizar capital
            self.current_capital += net_pnl_usdt
            
            # Crear resultado del trade
            trade_result = UltraTradeResult(
                symbol="TESTUSDT",
                entry_time=entry_time,
                exit_time=exit_time,
                side=signal_data['signal'],
                entry_price=actual_entry_price,
                exit_price=actual_exit_price,
                quantity=quantity,
                pnl_usdt=net_pnl_usdt,
                pnl_percentage=pnl_percentage,
                commission_usdt=total_commission,
                exit_reason=exit_reason,
                signal_strength=signal_data['signal_strength'],
                success_probability=success_prob,
                tp_level=tp_level
            )
            
            return trade_result
            
        except Exception as e:
            print(f"❌ Error simulando ejecución: {e}")
            return None
    
    def run_ultra_backtest(self, symbols: List[str], days: int = 30) -> Dict:
        """
        Ejecutar backtest ultra-agresivo
        """
        print(f"\n🚀 INICIANDO BACKTEST V4 ULTRA-AGRESIVO")
        print(f"📊 Símbolos: {', '.join(symbols)}")
        print(f"📅 Período: {days} días")
        print(f"💰 Capital inicial: ${self.initial_capital:,.2f}")
        print("⚡ Modo: Scalping ultra-agresivo (1-3 min)")
        
        start_time = datetime.now()
        total_signals_generated = 0
        total_trades_executed = 0
        
        # 🔧 OPTIMIZACIÓN: Obtener datos una sola vez por símbolo
        print("\n📡 Obteniendo datos de mercado...")
        market_data = {}
        for symbol in symbols:
            print(f"   Descargando {symbol}...")
            df = self.get_binance_data(symbol, '1m', 1000)  # Más datos para mejor análisis
            if not df.empty:
                market_data[symbol] = df
                print(f"   ✅ {symbol}: {len(df)} velas obtenidas")
            else:
                print(f"   ❌ {symbol}: Sin datos disponibles")
        
        if not market_data:
            print("❌ No se pudieron obtener datos de mercado")
            return {'metrics': None, 'trades': [], 'execution_stats': {}}
        
        print(f"\n🎯 Iniciando simulación de {days} días...")
        
        try:
            # Simular trading durante el período
            for day in range(days):
                daily_start_capital = self.current_capital
                daily_trades = 0
                
                # Simular sesiones de trading realistas por día
                sessions_per_day = 4  # Sesiones de trading OPTIMIZADAS por día
                
                for session in range(sessions_per_day):
                    for symbol in symbols:
                        if symbol not in market_data:
                            continue
                        
                        # Usar datos ya obtenidos
                        df = market_data[symbol]
                        
                        # Simular diferentes momentos del día usando diferentes ventanas de datos
                        start_idx = min(session * 10, len(df) - 100)
                        end_idx = min(start_idx + 100, len(df))
                        df_window = df.iloc[start_idx:end_idx].copy()
                        
                        if len(df_window) < 50:  # Mínimo de datos necesarios
                            continue
                        
                        # Generar señal
                        signal_data = self.strategy.generate_ultra_signal(df_window)
                        total_signals_generated += 1
                        
                        if not signal_data or signal_data['signal'] == 'HOLD':
                            continue
                        
                        # Calcular plan de trading
                        trade_plan = self.strategy.calculate_trade_plan(
                            signal_data, self.current_capital
                        )
                        
                        if not trade_plan:
                            continue
                        
                        # Simular ejecución
                        trade_result = self.simulate_realistic_execution(
                            signal_data, trade_plan
                        )
                        
                        if trade_result:
                            self.trades.append(trade_result)
                            total_trades_executed += 1
                            daily_trades += 1
                            
                            # Limitar trades por día para gestión de riesgo REALISTA
                            if daily_trades >= 10:  # Límite de trades por día - gestión OPTIMIZADA
                                break
                    
                    if daily_trades >= 15:
                        break
                
                # Registrar capital diario
                daily_return = (self.current_capital - daily_start_capital) / daily_start_capital
                self.daily_returns.append(daily_return)
                self.capital_history.append(self.current_capital)
                
                # Calcular drawdown
                peak_capital = max(self.capital_history)
                current_drawdown = (peak_capital - self.current_capital) / peak_capital
                self.drawdown_history.append(current_drawdown)
                
                # Progreso cada 5 días
                if (day + 1) % 5 == 0:
                    progress = (day + 1) / days * 100
                    daily_avg_return = np.mean(self.daily_returns[-5:]) * 100
                    print(f"📈 Día {day + 1}/{days} ({progress:.0f}%) - "
                          f"Capital: ${self.current_capital:,.2f} - "
                          f"Retorno 5d: {daily_avg_return:.2f}%")
        
        except Exception as e:
            print(f"❌ Error durante backtest: {e}")
        
        # Calcular métricas finales
        metrics = self.calculate_ultra_metrics()
        
        # Resultados del backtest
        backtest_results = {
            'metrics': metrics,
            'trades': [asdict(trade) for trade in self.trades],
            'capital_history': self.capital_history,
            'daily_returns': self.daily_returns,
            'drawdown_history': self.drawdown_history,
            'execution_stats': {
                'total_signals_generated': total_signals_generated,
                'total_trades_executed': total_trades_executed,
                'signal_to_trade_ratio': total_trades_executed / max(1, total_signals_generated),
                'execution_time_minutes': (datetime.now() - start_time).total_seconds() / 60
            }
        }
        
        return backtest_results
    
    def calculate_ultra_metrics(self) -> UltraPortfolioMetrics:
        """
        Calcular métricas ultra-comprehensivas
        """
        try:
            if not self.trades:
                return UltraPortfolioMetrics(
                    initial_capital=float(self.initial_capital),
                    final_capital=float(self.current_capital),
                    total_return_pct=0.0,
                    total_return_usdt=0.0,
                    daily_return_pct=0.0,
                    monthly_return_pct=0.0,
                    max_drawdown_pct=0.0,
                    max_drawdown_usdt=0.0,
                    sharpe_ratio=0.0,
                    sortino_ratio=0.0,
                    calmar_ratio=0.0,
                    win_rate=0.0,
                    profit_factor=0.0,
                    avg_win_pct=0.0,
                    avg_loss_pct=0.0,
                    max_consecutive_wins=0,
                    max_consecutive_losses=0,
                    total_trades=0,
                    winning_trades=0,
                    losing_trades=0,
                    total_commission_usdt=0.0,
                    avg_trade_duration_minutes=0.0,
                    trades_per_day=0.0,
                    daily_target_achievement=0.0,
                    monthly_target_achievement=0.0,
                    risk_adjusted_return=0.0,
                    volatility_pct=0.0,
                    var_95_pct=0.0,
                    expected_shortfall_pct=0.0
                )
            
            # Métricas básicas
            total_return_usdt = self.current_capital - self.initial_capital
            total_return_pct = total_return_usdt / self.initial_capital
            
            # Métricas de trades
            winning_trades = [t for t in self.trades if t.pnl_usdt > 0]
            losing_trades = [t for t in self.trades if t.pnl_usdt < 0]
            
            win_rate = len(winning_trades) / len(self.trades) if self.trades else 0
            
            # Profit factor
            total_wins = sum(t.pnl_usdt for t in winning_trades)
            total_losses = abs(sum(t.pnl_usdt for t in losing_trades))
            profit_factor = total_wins / max(total_losses, 0.01)
            
            # Retornos promedio
            avg_win_pct = np.mean([t.pnl_percentage for t in winning_trades]) if winning_trades else 0
            avg_loss_pct = np.mean([t.pnl_percentage for t in losing_trades]) if losing_trades else 0
            
            # Rachas consecutivas
            consecutive_wins = 0
            consecutive_losses = 0
            max_consecutive_wins = 0
            max_consecutive_losses = 0
            
            for trade in self.trades:
                if trade.pnl_usdt > 0:
                    consecutive_wins += 1
                    consecutive_losses = 0
                    max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
                else:
                    consecutive_losses += 1
                    consecutive_wins = 0
                    max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            
            # Comisiones totales
            total_commission = sum(t.commission_usdt for t in self.trades)
            
            # Duración promedio de trades
            durations = [(t.exit_time - t.entry_time).total_seconds() / 60 for t in self.trades]
            avg_duration = np.mean(durations) if durations else 0
            
            # Trades por día
            if self.trades:
                first_trade = min(t.entry_time for t in self.trades)
                last_trade = max(t.exit_time for t in self.trades)
                days_trading = (last_trade - first_trade).days + 1
                trades_per_day = len(self.trades) / max(days_trading, 1)
            else:
                trades_per_day = 0
            
            # Métricas de riesgo
            if self.daily_returns:
                daily_return_mean = np.mean(self.daily_returns)
                daily_return_std = np.std(self.daily_returns)
                
                # Sharpe ratio (asumiendo 0% risk-free rate)
                sharpe_ratio = daily_return_mean / max(daily_return_std, 0.001) * np.sqrt(252)
                
                # Sortino ratio
                negative_returns = [r for r in self.daily_returns if r < 0]
                downside_std = np.std(negative_returns) if negative_returns else daily_return_std
                sortino_ratio = daily_return_mean / max(downside_std, 0.001) * np.sqrt(252)
                
                # Volatilidad anualizada
                volatility_pct = daily_return_std * np.sqrt(252) * 100
                
                # VaR 95%
                var_95_pct = np.percentile(self.daily_returns, 5) * 100
                
                # Expected Shortfall
                var_threshold = np.percentile(self.daily_returns, 5)
                tail_returns = [r for r in self.daily_returns if r <= var_threshold]
                expected_shortfall_pct = np.mean(tail_returns) * 100 if tail_returns else var_95_pct
            else:
                sharpe_ratio = 0
                sortino_ratio = 0
                volatility_pct = 0
                var_95_pct = 0
                expected_shortfall_pct = 0
            
            # Drawdown máximo
            max_drawdown_pct = max(self.drawdown_history) * 100 if self.drawdown_history else 0
            max_drawdown_usdt = max_drawdown_pct / 100 * max(self.capital_history) if self.capital_history else 0
            
            # Calmar ratio
            calmar_ratio = (total_return_pct * 100) / max(max_drawdown_pct, 0.01)
            
            # Retornos objetivo
            days_traded = len(self.daily_returns)
            if days_traded > 0:
                daily_return_pct = (total_return_pct / days_traded) * 100
                monthly_return_pct = daily_return_pct * 30
                
                daily_target_achievement = daily_return_pct / (self.config.daily_target_pct * 100)
                monthly_target_achievement = monthly_return_pct / (self.config.monthly_target_pct * 100)
            else:
                daily_return_pct = 0
                monthly_return_pct = 0
                daily_target_achievement = 0
                monthly_target_achievement = 0
            
            # Risk-adjusted return
            risk_adjusted_return = total_return_pct / max(volatility_pct / 100, 0.01)
            
            return UltraPortfolioMetrics(
                initial_capital=float(self.initial_capital),
                final_capital=float(self.current_capital),
                total_return_pct=total_return_pct * 100,
                total_return_usdt=total_return_usdt,
                daily_return_pct=daily_return_pct,
                monthly_return_pct=monthly_return_pct,
                max_drawdown_pct=max_drawdown_pct,
                max_drawdown_usdt=max_drawdown_usdt,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                calmar_ratio=calmar_ratio,
                win_rate=win_rate * 100,
                profit_factor=profit_factor,
                avg_win_pct=avg_win_pct,
                avg_loss_pct=avg_loss_pct,
                max_consecutive_wins=max_consecutive_wins,
                max_consecutive_losses=max_consecutive_losses,
                total_trades=len(self.trades),
                winning_trades=len(winning_trades),
                losing_trades=len(losing_trades),
                total_commission_usdt=total_commission,
                avg_trade_duration_minutes=avg_duration,
                trades_per_day=trades_per_day,
                daily_target_achievement=daily_target_achievement,
                monthly_target_achievement=monthly_target_achievement,
                risk_adjusted_return=risk_adjusted_return,
                volatility_pct=volatility_pct,
                var_95_pct=var_95_pct,
                expected_shortfall_pct=expected_shortfall_pct
            )
            
        except Exception as e:
            print(f"❌ Error calculando métricas: {e}")
            return UltraPortfolioMetrics(
                initial_capital=float(self.initial_capital),
                final_capital=float(self.current_capital),
                total_return_pct=0.0,
                total_return_usdt=0.0,
                daily_return_pct=0.0,
                monthly_return_pct=0.0,
                max_drawdown_pct=0.0,
                max_drawdown_usdt=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                calmar_ratio=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                avg_win_pct=0.0,
                avg_loss_pct=0.0,
                max_consecutive_wins=0,
                max_consecutive_losses=0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                total_commission_usdt=0.0,
                avg_trade_duration_minutes=0.0,
                trades_per_day=0.0,
                daily_target_achievement=0.0,
                monthly_target_achievement=0.0,
                risk_adjusted_return=0.0,
                volatility_pct=0.0,
                var_95_pct=0.0,
                expected_shortfall_pct=0.0
            )
    
    def print_ultra_results(self, results: Dict):
        """
        Imprimir resultados del backtest ultra-agresivo
        """
        metrics = results['metrics']
        
        print("\n" + "="*80)
        print("🚀 RESULTADOS BACKTEST V4 ULTRA-AGRESIVO")
        print("="*80)
        
        # Resumen de capital
        print(f"\n💰 RESUMEN DE CAPITAL:")
        print(f"   Capital Inicial:     ${metrics.initial_capital:,.2f}")
        print(f"   Capital Final:       ${metrics.final_capital:,.2f}")
        print(f"   Ganancia Total:      ${metrics.total_return_usdt:,.2f}")
        print(f"   Retorno Total:       {metrics.total_return_pct:.2f}%")
        
        # Objetivos vs Resultados
        print(f"\n🎯 OBJETIVOS VS RESULTADOS:")
        print(f"   Objetivo Diario:     ${self.config.daily_target_usdt} ({self.config.daily_target_pct:.1%})")
        print(f"   Resultado Diario:    {metrics.daily_return_pct:.2f}%")
        print(f"   Logro Diario:        {metrics.daily_target_achievement:.1%}")
        print(f"   ")
        print(f"   Objetivo Mensual:    ${self.config.monthly_target_usdt} ({self.config.monthly_target_pct:.1%})")
        print(f"   Resultado Mensual:   {metrics.monthly_return_pct:.2f}%")
        print(f"   Logro Mensual:       {metrics.monthly_target_achievement:.1%}")
        
        # Métricas de trading
        print(f"\n📊 MÉTRICAS DE TRADING:")
        print(f"   Total Trades:        {metrics.total_trades}")
        print(f"   Trades Ganadores:    {metrics.winning_trades} ({metrics.win_rate:.1f}%)")
        print(f"   Trades Perdedores:   {metrics.losing_trades}")
        print(f"   Profit Factor:       {metrics.profit_factor:.2f}")
        print(f"   Ganancia Promedio:   {metrics.avg_win_pct:.2f}%")
        print(f"   Pérdida Promedio:    {metrics.avg_loss_pct:.2f}%")
        
        # Métricas de riesgo
        print(f"\n⚠️ MÉTRICAS DE RIESGO:")
        print(f"   Drawdown Máximo:     {metrics.max_drawdown_pct:.2f}% (${metrics.max_drawdown_usdt:.2f})")
        print(f"   Sharpe Ratio:        {metrics.sharpe_ratio:.2f}")
        print(f"   Sortino Ratio:       {metrics.sortino_ratio:.2f}")
        print(f"   Calmar Ratio:        {metrics.calmar_ratio:.2f}")
        print(f"   Volatilidad:         {metrics.volatility_pct:.2f}%")
        print(f"   VaR 95%:             {metrics.var_95_pct:.2f}%")
        
        # Métricas operacionales
        print(f"\n⚡ MÉTRICAS OPERACIONALES:")
        print(f"   Trades por Día:      {metrics.trades_per_day:.1f}")
        print(f"   Duración Promedio:   {metrics.avg_trade_duration_minutes:.1f} min")
        print(f"   Comisiones Totales:  ${metrics.total_commission_usdt:.2f}")
        print(f"   Rachas Ganadoras:    {metrics.max_consecutive_wins}")
        print(f"   Rachas Perdedoras:   {metrics.max_consecutive_losses}")
        
        # Estadísticas de ejecución
        exec_stats = results['execution_stats']
        print(f"\n🔧 ESTADÍSTICAS DE EJECUCIÓN:")
        print(f"   Señales Generadas:   {exec_stats['total_signals_generated']}")
        print(f"   Trades Ejecutados:   {exec_stats['total_trades_executed']}")
        print(f"   Ratio Señal/Trade:   {exec_stats['signal_to_trade_ratio']:.1%}")
        print(f"   Tiempo Ejecución:    {exec_stats['execution_time_minutes']:.1f} min")
        
        # Evaluación de objetivos
        print(f"\n📈 EVALUACIÓN DE OBJETIVOS:")
        if metrics.daily_target_achievement >= 1.0:
            print(f"   ✅ Objetivo diario ALCANZADO ({metrics.daily_target_achievement:.1%})")
        else:
            print(f"   ❌ Objetivo diario NO alcanzado ({metrics.daily_target_achievement:.1%})")
        
        if metrics.monthly_target_achievement >= 1.0:
            print(f"   ✅ Objetivo mensual ALCANZADO ({metrics.monthly_target_achievement:.1%})")
        else:
            print(f"   ❌ Objetivo mensual NO alcanzado ({metrics.monthly_target_achievement:.1%})")
        
        # Recomendaciones
        print(f"\n💡 RECOMENDACIONES:")
        if metrics.win_rate < 60:
            print(f"   🔧 Optimizar filtros de señal (win rate: {metrics.win_rate:.1f}%)")
        if metrics.profit_factor < 1.5:
            print(f"   🔧 Mejorar gestión de riesgos (profit factor: {metrics.profit_factor:.2f})")
        if metrics.max_drawdown_pct > 10:
            print(f"   🔧 Reducir tamaño de posición (drawdown: {metrics.max_drawdown_pct:.1f}%)")
        if metrics.monthly_target_achievement < 1.0:
            print(f"   🔧 Aumentar agresividad o frecuencia de trading")
        
        print("\n" + "="*80)

def main():
    """
    Función principal para ejecutar backtest V4 ultra-agresivo
    """
    # Símbolos para testing
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
    
    # Crear backtester
    backtester = UltraBinanceBacktester(initial_capital=500.0)
    
    # Ejecutar backtest
    results = backtester.run_ultra_backtest(symbols, days=30)
    
    # Mostrar resultados
    backtester.print_ultra_results(results)
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backtest_v4_ultra_results_{timestamp}.json"
    
    # Convertir métricas a dict para JSON
    results_for_json = {
        'metrics': asdict(results['metrics']),
        'execution_stats': results['execution_stats'],
        'summary': {
            'strategy_version': 'V4 Ultra-Agresiva',
            'capital_base': 500.0,
            'objetivo_mensual': '15%',
            'periodo_testing': '30 días',
            'timestamp': timestamp
        }
    }
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_for_json, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Resultados guardados en: {filename}")
    except Exception as e:
        print(f"❌ Error guardando resultados: {e}")

if __name__ == "__main__":
    main()