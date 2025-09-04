"""
Script para ejecutar un backtest histórico utilizando los datos de la base de datos.

Este script simula el comportamiento del bot sobre un período de tiempo pasado
para evaluar el rendimiento de la estrategia y obtener métricas clave.

Uso:
    python run_backtest.py --symbol BTCUSDT --days 365
"""
import asyncio
import pandas as pd
import argparse
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import Optional

# Cargar variables de entorno desde .env
load_dotenv()

# --- Pre-configuración para Backtesting ---
# Añadir el directorio raíz al path ANTES de cualquier otra importación del proyecto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Si las variables de entorno de Postgres no están completas,
# forzamos el uso de SQLite para que Pydantic no falle al cargar settings.
# Esto permite que el backtester se ejecute de forma independiente sin una DB live.
if os.getenv("DB_TYPE") == "postgresql" and not all(os.getenv(k) for k in ["POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"]):
    print("Advertencia: Faltan variables de entorno para PostgreSQL. Forzando DB_TYPE=sqlite para el backtest.")
    os.environ["DB_TYPE"] = "sqlite"

# Importar módulos del proyecto DESPUÉS de la pre-configuración
from strategies.backtester import Backtester
from strategies.ml_strategy import MLStrategy
from strategies.ma_cross_strategy import MACrossStrategy # Import for testing
from utils.technical_analysis import get_historical_klines
from config import settings, reload_settings

# Ajuste rápido para ejecución local: si se requiere Postgres pero falta host, intentar localhost
try:
    if hasattr(settings, 'DB_TYPE') and settings.DB_TYPE == 'postgresql':
        os.environ.setdefault('POSTGRES_HOST', os.getenv('POSTGRES_HOST', 'localhost'))
        # Recargar settings por si cambiaron variables
        _ = reload_settings()
except Exception:
    pass

async def _load_klines_with_fallback(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    """Intenta cargar klines vía util normal; si falla (sin DB/settings), cae a CSV estándar."""
    try:
        return await get_historical_klines(symbol=symbol, interval=interval, limit=limit)
    except Exception as e:
        print(f"Fallo al obtener klines desde DB/cliente para {symbol}-{interval}: {e}. Intentando CSV...")
        try:
            csv_path = os.path.join('data', 'analisis', f'historical_klines_{symbol}_{interval}_1_Jan_2022_now.csv')
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', format='mixed')
                    df = df.dropna(subset=['timestamp'])
                    df = df.sort_values('timestamp')
                    df.set_index('timestamp', inplace=True)
                for col in ['open','high','low','close','volume']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                if limit and len(df) > limit:
                    df = df.tail(limit)
                print(f"✅ Cargado CSV {csv_path} ({len(df)} filas)")
                return df
            else:
                print(f"CSV no encontrado: {csv_path}")
        except Exception as e2:
            print(f"Error leyendo CSV de fallback: {e2}")
    return pd.DataFrame()


async def run_single_backtest(symbol: str, days: int, initial_balance: float, report_last_days: Optional[int] = None) -> Optional[dict]:
    """
    Ejecuta un backtest para un único símbolo y devuelve las métricas.
    """
    interval = "1h"
    print(f"\n--- Iniciando Backtest para {symbol} en intervalo {interval} ---")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    historical_data_df = await _load_klines_with_fallback(symbol=symbol, interval=interval, limit=days * 24)

    if historical_data_df is None or historical_data_df.empty:
        print(f"No se encontraron datos históricos para {symbol}. Omitiendo.")
        return None

    print(f"Datos cargados para {symbol}: {len(historical_data_df)} velas de 1h.")

    # --- SELECCIÓN DE ESTRATEGIA PARA EL TEST ---
    # strategy = MLStrategy()
    strategy = MACrossStrategy() # Import for testing
    # -------------------------------------------

    strategy.set_parameters({"symbol": symbol, "interval": interval})
    
    # El warmup debe ser adecuado para la estrategia
    if isinstance(strategy, MLStrategy):
        warmup = getattr(settings, 'ML_MIN_DATA_POINTS', 2000)
    else:
        warmup = 50 # Warmup genérico para estrategias técnicas

    bt = Backtester(
        historical_data=historical_data_df,
        initial_balance=initial_balance,
        warmup_period=warmup,
        symbol=symbol,
        interval=interval
    )
    metrics = await bt.run(strategy)

    # Guardar historial de predicciones si es MLStrategy
    if isinstance(strategy, MLStrategy) and metrics and "prediction_history" in metrics:
        pred_df = pd.DataFrame(metrics["prediction_history"])
        output_path = f"backtest_predictions_{symbol}.csv"
        pred_df.to_csv(output_path, index=False)
        print(f"  - Historial de predicciones guardado en: {output_path}")

    if report_last_days and report_last_days > 0:
        try:
            trades_summ = metrics.get('trades', []) or []
            cutoff = datetime.now() - timedelta(days=report_last_days)
            last_trades = 0
            for t in trades_summ:
                ts = t.get('timestamp')
                if ts:
                    try:
                        dt = pd.to_datetime(ts)
                        if dt >= cutoff:
                            last_trades += 1
                    except Exception:
                        pass
            metrics['last_period_days'] = report_last_days
            metrics['last_period_closed_trades'] = last_trades
            metrics['last_period_avg_trades_per_day'] = round(last_trades / report_last_days, 4)
        except Exception:
            pass
    
    total_trades = metrics.get('total_trades', 0)
    trades_per_day = (total_trades / days) if total_trades > 0 else 0
    print(f"Resultados para {strategy.name} en {symbol}:")
    print(f"  - Operaciones Totales: {total_trades} ({trades_per_day:.2f}/día)")
    print(f"  - Rendimiento: {metrics.get('total_return_pct', 0):.2f}%")
    print(f"  - Tasa de Acierto: {metrics.get('win_rate_pct', 0):.2f}%")
    if metrics.get('last_period_days'):
        print(f"  - Operaciones cerradas últimos {metrics['last_period_days']} días: {metrics.get('last_period_closed_trades', 0)} ({metrics.get('last_period_avg_trades_per_day', 0):.2f}/día)")
    
    return metrics

async def main(symbols: list, days: int, initial_balance: float, report_last_days: Optional[int] = None):
    """
    Función principal para ejecutar el backtest sobre una lista de símbolos.
    """
    print(f"--- Iniciando Backtest Histórico para Múltiples Activos ---")
    print(f"Activos a analizar: {', '.join(symbols)}")
    print(f"Período: Últimos {days} días")
    print(f"Balance Inicial por Símbolo: ${initial_balance:,.2f}")
    print("-" * 50)

    all_metrics = []
    for symbol in symbols:
        stable_exclusions = {"USDCUSDT", "FDUSDUSDT"}
        if symbol in stable_exclusions:
            print(f"\n--- Omitiendo Stablecoin {symbol} ---")
            continue
        metrics = await run_single_backtest(symbol, days, initial_balance, report_last_days)
        if metrics:
            all_metrics.append(metrics)

    if not all_metrics:
        print("\nNo se pudo completar el backtest para ningún activo.")
        return

    print("\n\n--- Resultados Consolidados del Portafolio Dinámico ---")
    
    total_trades_portfolio = sum(m.get('total_trades', 0) for m in all_metrics)
    
    if total_trades_portfolio > 0:
        avg_trades_per_day_portfolio = total_trades_portfolio / days
    else:
        avg_trades_per_day_portfolio = 0

    # Evitar división por cero si no hay métricas
    if all_metrics:
        avg_return_pct = sum(m.get('total_return_pct', 0) for m in all_metrics) / len(all_metrics)
        avg_win_rate_pct = sum(m.get('win_rate_pct', 0) for m in all_metrics) / len(all_metrics)
    else:
        avg_return_pct = 0
        avg_win_rate_pct = 0

    print(f"Período Analizado:             {days} días")
    print(f"Activos Analizados con Éxito:  {len(all_metrics)}")
    print(f"Total de Operaciones (Todo el portafolio): {total_trades_portfolio}")
    print(f"Promedio de Operaciones/Día (Todo el portafolio): {avg_trades_per_day_portfolio:.2f}")
    if report_last_days and report_last_days > 0:
        last_closed = sum(m.get('last_period_closed_trades', 0) for m in all_metrics)
        avg_last = last_closed / report_last_days if report_last_days else 0
        print(f"Operaciones cerradas últimos {report_last_days} días (portafolio): {last_closed}")
        print(f"Promedio de Operaciones/Día últimos {report_last_days} días (portafolio): {avg_last:.2f}")
    print("-" * 50)
    print(f"Rendimiento Total Promedio:    {avg_return_pct:.2f}%")
    print(f"Tasa de Acierto Promedio:      {avg_win_rate_pct:.2f}%")
    print("-" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ejecutar backtest histórico para ITBOT.")
    
    DEFAULT_SYMBOLS = "USDCUSDT,FDUSDUSDT,BTCUSDT,TRXUSDT,BNBUSDT,ADAUSDT,ETHUSDT,SOLUSDT"
    
    parser.add_argument("--symbols", type=str, default=DEFAULT_SYMBOLS, help=f"Lista de símbolos separados por comas. Default: {DEFAULT_SYMBOLS}")
    parser.add_argument("--days", type=int, default=365, help="Número de días hacia atrás para el backtest.")
    parser.add_argument("--balance", type=float, default=10000.0, help="Balance inicial para la simulación por símbolo.")
    parser.add_argument("--report_last_days", type=int, default=None, help="Reportar métricas de los últimos N días dentro del período cargado.")
    
    args = parser.parse_args()
    
    symbol_list = [s.strip().upper() for s in args.symbols.split(',')]

    try:
        asyncio.run(main(symbol_list, args.days, args.balance, args.report_last_days))
    except KeyboardInterrupt:
        print("\nBacktest interrumpido por el usuario.")
    except Exception as e:
        print(f"\nOcurrió un error durante el backtest: {e}")
