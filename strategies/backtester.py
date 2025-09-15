# strategies/backtester.py

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List, Optional
import asyncio
import inspect

from strategies.base_strategy import BaseStrategy
from strategies.ml_strategy import MLStrategy
from utils.risk_manager import obtener_riesgo_actual, obtener_riesgo_ajustado_por_ml
from utils.order_executor import calcular_cantidad_operar
from config import settings
from utils.feature_pipeline import FeaturePipeline # Import FeaturePipeline

logger = logging.getLogger(__name__)

def generate_mock_data(days=500, initial_price=50000) -> pd.DataFrame:
    """
    Genera un DataFrame con datos de mercado falsos para pruebas.
    """
    logger.info(f"Generando {days} días de datos de mercado falsos.")
    dates = pd.to_datetime(pd.date_range(end=pd.Timestamp.now(), periods=days, freq='h'))
    
    returns = np.random.normal(loc=0.0005, scale=0.02, size=days)
    close_prices = initial_price * (1 + returns).cumprod()
    
    open_prices = close_prices / (1 + np.random.normal(loc=0, scale=0.005, size=days))
    high_prices = np.maximum(open_prices, close_prices) *(1 + np.random.uniform(0, 0.01, size=days))
    low_prices = np.minimum(open_prices, close_prices) * (1 - np.random.uniform(0, 0.01, size=days))
    volumes = np.random.randint(100, 10000, size=days)
    
    df = pd.DataFrame({
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    }, index=dates)
    
    df.index.name = "timestamp"
    return df

class Backtester:
    """
    Realiza una simulación de trading (backtesting) para una estrategia dada
    utilizando datos históricos.
    """
    def __init__(self, historical_data: pd.DataFrame, initial_balance: float = 1000.0, warmup_period: int = 50, symbol: Optional[str] = None, interval: Optional[str] = None, commission: Optional[float] = None):
        self.historical_data = historical_data
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.position = 0.0
        self.avg_cost_price = 0.0
        self.trades: List[Dict[str, Any]] = []
        self.balance_history: List[float] = []
        self.prediction_history: List[Dict[str, Any]] = []
        self.warmup_period = warmup_period
        self.symbol = symbol
        self.interval = interval
        # Comisión opcional: si se proporciona, se aplicará como porcentaje (e.g., 0.001 = 0.1%)
        self.commission = commission

    async def run(self, strategy: BaseStrategy) -> Dict[str, Any]:
        """
        Ejecuta el backtest para la estrategia proporcionada.
        """
        logger.info(f"Iniciando backtest para la estrategia: {strategy.name} con modelo de costes: {settings.COST_MODEL}")

        if len(self.historical_data) < self.warmup_period:
            logger.warning(f"No hay suficientes datos históricos para el backtesting (se necesitan {self.warmup_period}).")
            return {}

        # Enriquecer los datos históricos con features antes de pasarlos a las estrategias
        feature_pipeline = FeaturePipeline()
        self.historical_data = feature_pipeline.transform(self.historical_data.copy())

        for i in range(self.warmup_period, len(self.historical_data)):
            # --- Inicio: Llamada dinámica y flexible a la estrategia ---
            analyze_sig = inspect.signature(strategy.analyze)
            kwargs = {}
            df_slice = self.historical_data.iloc[:i]

            # Iterate through expected parameters and fill kwargs
            for param_name, param in analyze_sig.parameters.items():
                if param_name == 'self':
                    continue
                elif param_name in ['historical_data', 'df', 'df_klines', 'data']:
                    kwargs[param_name] = df_slice
                elif param_name == 'current_index':
                    kwargs[param_name] = i
                elif param_name == 'symbol' and self.symbol:
                    kwargs[param_name] = self.symbol
                elif param_name == 'interval' and self.interval:
                    kwargs[param_name] = self.interval
                # Add other specific parameters if strategies require them and they are available in Backtester
                # For now, this covers the known cases.

            analysis_result = strategy.analyze(**kwargs)
            if inspect.isawaitable(analysis_result):
                analysis_result = await analysis_result
            # --- Fin: Llamada dinámica ---
            
            decision = analysis_result.get("decision", "MANTENER")
            score = analysis_result.get("score", 0.0)

            if isinstance(strategy, MLStrategy):
                prob_buy = analysis_result.get("ml_buy_probability")
                prob_sell = analysis_result.get("ml_sell_probability")
                self.prediction_history.append({
                    "timestamp": self.historical_data.index[i],
                    "buy_probability": prob_buy,
                    "sell_probability": prob_sell,
                    "decision": decision,
                    "score": score
                })
            
            current_price = self.historical_data.iloc[i]["close"]

            riesgo_base_pct = obtener_riesgo_actual()
            riesgo_pct = riesgo_base_pct
            if decision != "MANTENER" and isinstance(strategy, MLStrategy):
                riesgo_pct = obtener_riesgo_ajustado_por_ml(score, riesgo_base_pct)

            cantidad_usdt_a_operar = calcular_cantidad_operar(self.balance, riesgo_pct)

            # Señales brutas
            is_buy_signal = decision in ("COMPRAR", "COMPRAR_BAJO")
            is_sell_signal = decision in ("VENDER", "VENDER_ALTO")

            # Políticas ML: moderadas opcionales y confluencia técnica
            if isinstance(strategy, MLStrategy):
                # 1) Desactivar señales moderadas si la política no las permite
                if not getattr(settings, 'ML_ENABLE_MODERATE_SIGNALS', False):
                    if decision in ("COMPRAR_BAJO", "VENDER_ALTO"):
                        is_buy_signal = False
                        is_sell_signal = False

                # 2) Confluencia técnica (MACD y ADX) para ejecutar
                if getattr(settings, 'ML_REQUIRE_TECH_CONFLUENCE', False) and i >= self.warmup_period:
                    try:
                        last_row = self.historical_data.iloc[i]
                        adx_min = float(getattr(settings, 'ML_CONFLUENCE_ADX_MIN', 20.0))
                        macd = last_row.get('macd')
                        macd_signal = last_row.get('macd_signal')
                        adx = last_row.get('adx')
                        macd_ok_buy = (pd.notna(macd) and pd.notna(macd_signal) and macd > macd_signal)
                        macd_ok_sell = (pd.notna(macd) and pd.notna(macd_signal) and macd < macd_signal)
                        adx_ok = (pd.notna(adx) and adx >= adx_min)
                        if is_buy_signal and decision.startswith("COMPRAR") and not (macd_ok_buy and adx_ok):
                            is_buy_signal = False
                        if is_sell_signal and decision.startswith("VENDER") and not (macd_ok_sell and adx_ok):
                            is_sell_signal = False
                    except Exception:
                        # Si falla la lectura de features, no bloquear por confluencia
                        pass

            if is_buy_signal and self.balance > 0 and cantidad_usdt_a_operar > 0:
                investment = min(self.balance, cantidad_usdt_a_operar)
                
                ask_price = current_price * (1 + settings.BACKTEST_AVERAGE_SPREAD_PCT / 100.0)
                amount_to_buy = investment / ask_price
                
                commission_cost = 0
                if settings.COST_MODEL == "RAW":
                    commission_cost = investment * (settings.COMMISSION_PER_LOT / 100000.0)
                elif self.commission is not None:
                    commission_cost = investment * self.commission
                
                self.balance -= (investment + commission_cost)

                if self.position > 0:
                    total_cost = (self.position * self.avg_cost_price) + (amount_to_buy * ask_price)
                    self.position += amount_to_buy
                    self.avg_cost_price = total_cost / self.position
                else:
                    self.position = amount_to_buy
                    self.avg_cost_price = ask_price

                self.trades.append({
                    "type": "BUY", "price": ask_price, "amount": amount_to_buy,
                    "timestamp": self.historical_data.index[i],
                    "portfolio_value": self.get_portfolio_value(current_price)
                })

            elif is_sell_signal and self.position > 0:
                amount_to_sell = self.position
                
                bid_price = current_price * (1 - settings.BACKTEST_AVERAGE_SPREAD_PCT / 100.0)
                received_usdt = amount_to_sell * bid_price
                
                commission_cost = 0
                if settings.COST_MODEL == "RAW":
                    commission_cost = received_usdt * (settings.COMMISSION_PER_LOT / 100000.0)
                elif self.commission is not None:
                    commission_cost = received_usdt * self.commission

                net_received_usdt = received_usdt - commission_cost
                
                cost_of_sold_position = amount_to_sell * self.avg_cost_price
                profit_loss = net_received_usdt - cost_of_sold_position

                self.balance += net_received_usdt
                self.position = 0
                self.avg_cost_price = 0.0
                self.trades.append({
                    "type": "SELL", "price": bid_price, "amount": amount_to_sell,
                    "timestamp": self.historical_data.index[i], "profit_loss": profit_loss,
                    "portfolio_value": self.get_portfolio_value(current_price)
                })

            self.balance_history.append(self.get_portfolio_value(current_price))

        if self.position > 0:
            last_price = self.historical_data.iloc[-1]["close"]
            bid_price = last_price * (1 - settings.BACKTEST_AVERAGE_SPREAD_PCT / 100.0)
            received_usdt = self.position * bid_price
            
            commission_cost = 0
            if settings.COST_MODEL == "RAW":
                commission_cost = received_usdt * (settings.COMMISSION_PER_LOT / 100000.0)
            elif self.commission is not None:
                commission_cost = received_usdt * self.commission
            
            net_received_usdt = received_usdt - commission_cost
            cost_of_sold_position = self.position * self.avg_cost_price
            profit_loss = net_received_usdt - cost_of_sold_position

            self.trades.append({
                "type": "SELL_FINAL", "price": bid_price, "amount": self.position,
                "timestamp": self.historical_data.index[-1], "profit_loss": profit_loss,
                "portfolio_value": self.get_portfolio_value(last_price)
            })
            self.balance_history.append(self.get_portfolio_value(last_price))

        return self.calculate_metrics()

    def get_portfolio_value(self, current_price: float) -> float:
        return self.balance + (self.position * current_price)

    def calculate_metrics(self) -> Dict[str, Any]:
        final_balance = self.get_portfolio_value(self.historical_data.iloc[-1]["close"])
        total_return = ((final_balance - self.initial_balance) / self.initial_balance) * 100
        total_trades = len(self.trades)
        
        winning_trades = 0
        losing_trades = 0
        for trade in self.trades:
            if trade["type"].startswith("SELL") and "profit_loss" in trade:
                if trade["profit_loss"] > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1

        win_rate = (winning_trades / (winning_trades + losing_trades)) * 100 if (winning_trades + losing_trades) > 0 else 0

        if not self.balance_history:
            max_drawdown, sharpe_ratio = 0.0, 0.0
        else:
            portfolio_values = np.array(self.balance_history)
            if portfolio_values.size == 0:
                max_drawdown, sharpe_ratio = 0.0, 0.0
            else:
                peak = np.maximum.accumulate(portfolio_values)
                drawdown = (peak - portfolio_values) / peak
                max_drawdown = round(np.max(drawdown) * 100, 2)

                returns = np.diff(portfolio_values) / portfolio_values[:-1]
                returns = returns[~np.isnan(returns) & ~np.isinf(returns)]

                if len(returns) > 0:
                    annualization_factor = np.sqrt(365 * 6)
                    avg_daily_return = np.mean(returns)
                    std_daily_return = np.std(returns)
                    sharpe_ratio = round((avg_daily_return * annualization_factor) / std_daily_return, 2) if std_daily_return > 0 else 0.0
                else:
                    sharpe_ratio = 0.0

        equity_series = []
        if self.balance_history:
            base = self.balance_history[0] if self.balance_history[0] != 0 else 1.0
            equity_series = [round((v / base) * 100, 2) for v in self.balance_history]

        trade_summ = [
            {"timestamp": str(t["timestamp"]), "pnl": round(float(t["profit_loss"]), 4), "price": round(float(t["price"]), 6)}
            for t in self.trades if t["type"].startswith("SELL") and "profit_loss" in t
        ]

        return {
            "total_return_pct": round(total_return, 2), "total_trades": total_trades,
            "winning_trades": winning_trades, "losing_trades": losing_trades,
            "win_rate_pct": round(win_rate, 2), "initial_balance": self.initial_balance,
            "final_balance": round(final_balance, 2), "max_drawdown_pct": max_drawdown,
            "sharpe_ratio": sharpe_ratio, "equity": equity_series, "trades": trade_summ,
            "prediction_history": self.prediction_history
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    async def main_backtest():
        data_path = "data/analisis/historical_klines_BTCUSDT_4h_1_Jan_2022_now.csv"
        try:
            historical_data = pd.read_csv(data_path, index_col="timestamp", parse_dates=True)
        except FileNotFoundError:
            logger.error(f"Archivo de datos históricos no encontrado en {data_path}.")
            return

        # Instanciar la estrategia de ML para prueba
        strategy_to_test = MLStrategy()
        backtester = Backtester(historical_data, initial_balance=1000.0, warmup_period=2000, symbol="BTCUSDT", interval="4h")
        metrics = await backtester.run(strategy_to_test)

        logger.info("\n--- Resultados del Backtest ---")
        for key, value in metrics.items():
            if isinstance(value, list):
                logger.info(f"{key}: (lista de {len(value)} elementos)")
            else:
                logger.info(f"{key}: {value}")

    asyncio.run(main_backtest())
