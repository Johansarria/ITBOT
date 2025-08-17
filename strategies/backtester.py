# strategies/backtester.py

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List
import asyncio
import inspect

from strategies.base_strategy import BaseStrategy
from strategies.ml_strategy import MLStrategy # Importar MLStrategy
from utils.risk_manager import obtener_riesgo_actual, obtener_riesgo_ajustado_por_ml
from utils.order_executor import calcular_cantidad_operar # Para calcular la cantidad a operar

logger = logging.getLogger(__name__)

def generate_mock_data(days=500, initial_price=50000) -> pd.DataFrame:
    """
    Genera un DataFrame con datos de mercado falsos para pruebas.
    """
    logger.info(f"Generando {days} días de datos de mercado falsos.")
    dates = pd.to_datetime(pd.date_range(end=pd.Timestamp.now(), periods=days, freq='h'))
    
    # Generar una caminata aleatoria para el precio de cierre
    returns = np.random.normal(loc=0.0005, scale=0.02, size=days)
    close_prices = initial_price * (1 + returns).cumprod()
    
    # Crear las otras columnas (open, high, low) basadas en el cierre
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
    def __init__(self, historical_data: pd.DataFrame, initial_balance: float = 1000.0, commission: float = 0.001, warmup_period: int = 50):
        self.historical_data = historical_data
        self.initial_balance = initial_balance
        self.commission = commission
        self.balance = initial_balance
        self.position = 0.0  # Cantidad de activo que se posee
        self.avg_cost_price = 0.0 # Precio promedio de costo de la posición actual
        self.trades: List[Dict[str, Any]] = []
        self.balance_history: List[float] = [] # Historial del valor de la cartera
        self.warmup_period = warmup_period

    async def run(self, strategy: BaseStrategy) -> Dict[str, Any]:
        """
        Ejecuta el backtest para la estrategia proporcionada.
        """
        logger.info(f"Iniciando backtest para la estrategia: {strategy.name}")

        if len(self.historical_data) < self.warmup_period:
            logger.warning(f"No hay suficientes datos históricos para el backtesting (se necesitan {self.warmup_period}).")
            return {}

        # Iterar solo después del período de calentamiento
        for i in range(self.warmup_period, len(self.historical_data)):
            # La estrategia analiza el histórico HASTA el punto actual, pasando el DataFrame completo y el índice
            # Asegurarse de que el slice no esté vacío (aunque con warmup_period > 0, no debería estarlo)
            if i == 0: # Should not happen with warmup_period > 0, but as a safeguard
                self.balance_history.append(self.get_portfolio_value(self.historical_data.iloc[i]["close"]))
                continue

            # Manejar dinámicamente estrategias síncronas y asíncronas
            analysis_result = strategy.analyze(self.historical_data, i)
            if inspect.isawaitable(analysis_result):
                decision_analysis = await analysis_result
            else:
                decision_analysis = analysis_result

            decision = decision_analysis.get("decision", "MANTENER")
            score = decision_analysis.get("score", 0.0)
            
            current_price = self.historical_data.iloc[i]["close"]

            # Obtener riesgo base y ajustado por ML
            riesgo_base_pct = obtener_riesgo_actual() # Asume un riesgo base por defecto o configurado
            riesgo_pct = riesgo_base_pct
            if decision != "MANTENER":
                riesgo_pct = obtener_riesgo_ajustado_por_ml(score, riesgo_base_pct)

            # Calcular cantidad a operar en USDT
            cantidad_usdt_a_operar = calcular_cantidad_operar(self.balance, riesgo_pct)

            if decision == "COMPRAR" and self.balance > 0 and cantidad_usdt_a_operar > 0:
                # Asegurarse de no comprar más de lo que se tiene en balance
                investment = min(self.balance, cantidad_usdt_a_operar)
                amount_to_buy = (investment / current_price) * (1 - self.commission)
                
                # Actualizar posición y costo promedio
                if self.position > 0: # Si ya tenemos una posición abierta
                    total_cost = (self.position * self.avg_cost_price) + (amount_to_buy * current_price)
                    self.position += amount_to_buy
                    self.avg_cost_price = total_cost / self.position
                else: # Primera compra o después de cerrar una posición
                    self.position = amount_to_buy
                    self.avg_cost_price = current_price

                self.balance -= investment
                self.trades.append({
                    "type": "BUY",
                    "price": current_price,
                    "amount": amount_to_buy,
                    "timestamp": self.historical_data.index[i],
                    "portfolio_value": self.get_portfolio_value(current_price)
                })
                logger.info(f"BUY: {amount_to_buy:.4f} @ {current_price:.2f}. Balance: {self.balance:.2f}, Posición: {self.position:.4f}")

            elif decision == "VENDER" and self.position > 0:
                # Vender toda la posición
                amount_to_sell = self.position
                received_usdt = amount_to_sell * current_price * (1 - self.commission)
                
                # Calcular ganancia/pérdida de esta operación
                cost_of_sold_position = amount_to_sell * self.avg_cost_price
                profit_loss = received_usdt - cost_of_sold_position

                self.balance += received_usdt
                self.position = 0
                self.avg_cost_price = 0.0 # Resetear costo promedio al cerrar posición
                self.trades.append({
                    "type": "SELL",
                    "price": current_price,
                    "amount": amount_to_sell,
                    "timestamp": self.historical_data.index[i],
                    "profit_loss": profit_loss, # Almacenar la ganancia/pérdida
                    "portfolio_value": self.get_portfolio_value(current_price)
                })
                logger.info(f"SELL: {amount_to_sell:.4f} @ {current_price:.2f}. Balance: {self.balance:.2f}, Posición: {self.position:.4f}. P/L: {profit_loss:.2f}")
            else:
                logger.debug(f"MANTENER o no hay suficiente balance/posición. Decisión: {decision}")

            # Registrar el valor de la cartera al final de cada paso
            self.balance_history.append(self.get_portfolio_value(current_price))

        # Al final del backtest, si todavía hay una posición abierta, la cerramos al último precio
        if self.position > 0:
            last_price = self.historical_data.iloc[-1]["close"]
            received_usdt = self.position * last_price * (1 - self.commission)
            cost_of_sold_position = self.position * self.avg_cost_price
            profit_loss = received_usdt - cost_of_sold_position

            self.balance += received_usdt
            self.position = 0
            self.avg_cost_price = 0.0
            self.trades.append({
                "type": "SELL_FINAL", # Marcar como cierre final
                "price": last_price,
                "amount": self.position,
                "timestamp": self.historical_data.index[-1],
                "profit_loss": profit_loss,
                "portfolio_value": self.get_portfolio_value(last_price)
            })
            logger.info(f"Cerrando posición final. Balance: {self.balance:.2f}. P/L: {profit_loss:.2f}")
            self.balance_history.append(self.get_portfolio_value(last_price)) # Registrar valor final

        return self.calculate_metrics()

    def get_portfolio_value(self, current_price: float) -> float:
        """
        Calcula el valor total de la cartera (balance en USDT + valor de la posición).
        """
        return self.balance + (self.position * current_price)

    def calculate_metrics(self) -> Dict[str, Any]:
        """
        Calcula las métricas de rendimiento del backtest.
        """
        final_balance = self.get_portfolio_value(self.historical_data.iloc[-1]["close"])

        total_return = ((final_balance - self.initial_balance) / self.initial_balance) * 100
        total_trades = len(self.trades)
        
        # Calcular winning_trades y losing_trades usando profit_loss
        winning_trades = 0
        losing_trades = 0
        for trade in self.trades:
            if trade["type"].startswith("SELL") and "profit_loss" in trade:
                if trade["profit_loss"] > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1

        win_rate = (winning_trades / (winning_trades + losing_trades)) * 100 if (winning_trades + losing_trades) > 0 else 0

        # Calcular Drawdown Máximo
        if not self.balance_history:
            max_drawdown = 0.0
            sharpe_ratio = 0.0
        else:
            portfolio_values = np.array(self.balance_history)
            if portfolio_values.size == 0: # Manejar caso de array vacío
                max_drawdown = 0.0
                sharpe_ratio = 0.0
            else:
                # Calcular Drawdown Máximo
                peak = np.maximum.accumulate(portfolio_values)
                drawdown = (peak - portfolio_values) / peak
                max_drawdown = round(np.max(drawdown) * 100, 2)

                # Calcular retornos periódicos
                # Evitar división por cero si el valor anterior es 0
                returns = np.diff(portfolio_values) / portfolio_values[:-1]
                returns = returns[~np.isnan(returns)] # Eliminar NaN si los hay
                returns = returns[~np.isinf(returns)] # Eliminar Inf si los hay

                if len(returns) > 0:
                    # Asumimos que los datos son 4-horarios, 6 períodos por día, 365 días al año
                    annualization_factor = np.sqrt(365 * 6) 
                    
                    # Retorno promedio por período
                    avg_daily_return = np.mean(returns)
                    
                    # Desviación estándar de los retornos por período
                    std_daily_return = np.std(returns)

                    if std_daily_return > 0:
                        sharpe_ratio = (avg_daily_return * annualization_factor) / std_daily_return
                        sharpe_ratio = round(sharpe_ratio, 2)
                    else:
                        sharpe_ratio = 0.0 # Si no hay riesgo, Sharpe es indefinido o muy alto
                else:
                    sharpe_ratio = 0.0

        logger.info(f"Backtest completado. Retorno Total: {total_return:.2f}%")

        return {
            "total_return_pct": round(total_return, 2),
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate_pct": round(win_rate, 2),
            "initial_balance": self.initial_balance,
            "final_balance": round(final_balance, 2),
            "max_drawdown_pct": max_drawdown,
            "sharpe_ratio": sharpe_ratio
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    async def main_backtest():
        # Cargar datos históricos reales
        data_path = "data/analisis/historical_klines_BTCUSDT_4h_1_Jan_2022_now.csv"
        try:
            historical_data = pd.read_csv(data_path, index_col="timestamp", parse_dates=True)
            logger.info(f"Datos históricos cargados desde {data_path}. Filas: {len(historical_data)}")
        except FileNotFoundError:
            logger.error(f"Archivo de datos históricos no encontrado en {data_path}. Por favor, descarga los datos primero.")
            return

        # Instanciar la estrategia de ML
        ml_strategy = MLStrategy()

        # Instanciar el Backtester
        backtester = Backtester(historical_data, initial_balance=1000.0, commission=0.001, warmup_period=100) # Aumentar warmup

        # Ejecutar el backtest
        metrics = await backtester.run(ml_strategy)

        # Imprimir resultados
        logger.info("\n--- Resultados del Backtest ---")
        for key, value in metrics.items():
            logger.info(f"{key}: {value}")

    asyncio.run(main_backtest())