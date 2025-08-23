# utils/kpi_calculator.py
import os
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

# Importar la función de conexión desde el módulo de auditoría
from utils.audit_operations_db import get_db_connection

logger = logging.getLogger(__name__)

def get_operations_df(days: int = 30) -> pd.DataFrame:
    """
    Obtiene el historial de operaciones desde la base de datos de auditoría (PostgreSQL)
    y lo devuelve como un DataFrame de pandas.

    Args:
        days (int): El número de días de historial a obtener.

    Returns:
        pd.DataFrame: Un DataFrame con el historial de operaciones.
                      Las columnas de fecha se convierten a datetime.
                      Retorna un DataFrame vacío si no hay datos o hay un error.
    """
    logger.info(f"Obteniendo historial de operaciones de los últimos {days} días...")
    
    query = """
        SELECT * FROM audit_operations
        WHERE timestamp_open >= %s;
    """
    
    start_date = datetime.now() - timedelta(days=days)

    try:
        with get_db_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(start_date,))
            
            if df.empty:
                logger.warning("No se encontraron operaciones en el rango de fechas especificado.")
                return pd.DataFrame()

            # Convertir columnas de fecha/hora a objetos datetime de pandas
            for col in ['timestamp_open', 'timestamp_close']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            # Asegurar que las columnas numéricas sean del tipo correcto
            numeric_cols = ['pnl_usdt', 'pnl_percent', 'size_usdt']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            logger.info(f"Se obtuvieron {len(df)} registros de operaciones.")
            return df

    except Exception as e:
        logger.error(f"Error al obtener el historial de operaciones desde la base de datos: {e}", exc_info=True)
        return pd.DataFrame()

def calculate_pnl(operations_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcula el PnL total y diario a partir de un DataFrame de operaciones.

    Args:
        operations_df (pd.DataFrame): DataFrame obtenido de get_operations_df.

    Returns:
        Dict[str, Any]: Un diccionario con 'total_pnl_usdt' y 'daily_pnl_df'.
    """
    if operations_df.empty:
        return {"total_pnl_usdt": 0, "daily_pnl_df": pd.DataFrame()}

    df = operations_df.copy()

    # Calcular pnl_usdt si no existe o es nulo, a partir de pnl_percent y size_usdt
    if 'pnl_usdt' not in df.columns:
        df['pnl_usdt'] = df['size_usdt'] * (df['pnl_percent'] / 100)
    else:
        df['pnl_usdt'] = df['pnl_usdt'].fillna(df['size_usdt'] * (df['pnl_percent'] / 100))
    
    total_pnl_usdt = df['pnl_usdt'].fillna(0).sum()

    # Calcular PnL diario
    daily_pnl_df = pd.DataFrame()
    if not df.empty and 'timestamp_open' in df.columns:
        daily_pnl_df = df.resample('D', on='timestamp_open')['pnl_usdt'].sum().reset_index()
        daily_pnl_df.rename(columns={'pnl_usdt': 'daily_pnl'}, inplace=True)

    return {
        "total_pnl_usdt": total_pnl_usdt,
        "daily_pnl_df": daily_pnl_df
    }

def calculate_trade_stats(operations_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcula estadísticas clave de trading como Win Rate, Profit Factor y Expectancy.

    Args:
        operations_df (pd.DataFrame): DataFrame de operaciones.

    Returns:
        Dict[str, Any]: Diccionario con las estadísticas calculadas.
    """
    if operations_df.empty:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "profit_factor": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "expectancy": 0.0
        }

    df = operations_df.copy()

    # Asegurar que pnl_usdt esté calculado
    if 'pnl_usdt' not in df.columns or df['pnl_usdt'].isnull().all():
        df['pnl_usdt'] = df['size_usdt'] * (df['pnl_percent'] / 100)

    total_trades = len(df)
    winning_trades = df[df['pnl_usdt'] > 0]
    losing_trades = df[df['pnl_usdt'] < 0]

    winning_trades_count = len(winning_trades)
    losing_trades_count = len(losing_trades)

    win_rate = (winning_trades_count / total_trades * 100) if total_trades > 0 else 0.0

    gross_profit = winning_trades['pnl_usdt'].sum()
    gross_loss = losing_trades['pnl_usdt'].sum()

    profit_factor = gross_profit / abs(gross_loss) if gross_loss != 0 else float('inf')

    average_win = gross_profit / winning_trades_count if winning_trades_count > 0 else 0.0
    average_loss = gross_loss / losing_trades_count if losing_trades_count > 0 else 0.0

    # Expectancy = (Win Rate * Average Win) - (Loss Rate * Average Loss)
    loss_rate = 100 - win_rate
    expectancy = ((win_rate / 100) * average_win) + ((loss_rate / 100) * average_loss) # average_loss ya es negativo

    return {
        "total_trades": total_trades,
        "winning_trades": winning_trades_count,
        "losing_trades": losing_trades_count,
        "win_rate": win_rate,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "average_win": average_win,
        "average_loss": average_loss,
        "expectancy": expectancy
    }

def calculate_max_drawdown(operations_df: pd.DataFrame, initial_balance: float = 1000.0) -> float:
    """
    Calcula el Max Drawdown (MDD) a partir de un DataFrame de operaciones.
    El MDD es la mayor caída porcentual desde un pico hasta un valle subsiguiente.

    Args:
        operations_df (pd.DataFrame): DataFrame de operaciones.
        initial_balance (float): Balance inicial para calcular la curva de capital.

    Returns:
        float: El Max Drawdown como porcentaje (valor positivo). Retorna 0.0 si no hay operaciones.
    """
    if operations_df.empty:
        return 0.0

    df = operations_df.copy()

    # Asegurar que pnl_usdt esté calculado
    if 'pnl_usdt' not in df.columns or df['pnl_usdt'].isnull().all():
        df['pnl_usdt'] = df['size_usdt'] * (df['pnl_percent'] / 100)

    # Calcular la curva de capital
    # Asegurarse de que el DataFrame esté ordenado por tiempo
    df = df.sort_values(by='timestamp_open')
    
    # Calcular el PnL acumulado
    cumulative_pnl = df['pnl_usdt'].cumsum()
    
    # Calcular la curva de capital (equity curve)
    equity_curve = initial_balance + cumulative_pnl
    
    # Calcular los picos (running maximum)
    running_max = equity_curve.cummax()
    
    # Calcular el drawdown
    drawdown = (equity_curve - running_max) / running_max
    
    # El Max Drawdown es el valor más negativo del drawdown
    max_drawdown = drawdown.min() * 100 # Convertir a porcentaje
    
    return abs(max_drawdown) # Retornar como valor positivo

def calculate_trade_frequency_and_duration(operations_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcula la frecuencia de trades (trades por día) y la duración media de los trades.

    Args:
        operations_df (pd.DataFrame): DataFrame de operaciones.

    Returns:
        Dict[str, Any]: Diccionario con 'trades_per_day' y 'avg_trade_duration_minutes'.
    """
    if operations_df.empty:
        return {
            "trades_per_day": 0.0,
            "avg_trade_duration_minutes": 0.0
        }

    df = operations_df.copy()

    # Asegurar que las columnas necesarias existan y normalizar
    required_cols = ['timestamp_open', 'timestamp_close']
    if not all(col in df.columns for col in required_cols):
        logger.warning(f"Columnas {required_cols} no encontradas para cálculo de frecuencia/duración.")
        return {"trades_per_day": 0.0, "avg_trade_duration_minutes": 0.0}

    df['timestamp_open'] = pd.to_datetime(df['timestamp_open'], errors='coerce', utc=True)
    df['timestamp_close'] = pd.to_datetime(df['timestamp_close'], errors='coerce', utc=True)
    
    # Filtrar trades cerrados para cálculos
    closed_trades = df[df['timestamp_open'].notna() & df['timestamp_close'].notna() & (df['timestamp_close'] > df['timestamp_open'])].copy()

    # Cálculo de Duración Media
    avg_trade_duration_minutes = 0.0
    if not closed_trades.empty:
        durations = (closed_trades['timestamp_close'] - closed_trades['timestamp_open']).dt.total_seconds() / 60
        avg_trade_duration_minutes = durations.mean()

    # Cálculo de Trades por Día
    trades_per_day = 0.0
    valid_open_timestamps = closed_trades['timestamp_open'].dropna()
    if not valid_open_timestamps.empty:
        unique_days = valid_open_timestamps.dt.date.nunique()
        if unique_days > 0:
            trades_per_day = len(closed_trades) / unique_days

    return {
        "trades_per_day": trades_per_day,
        "avg_trade_duration_minutes": avg_trade_duration_minutes
    }

def get_today_summary(operations_path: str) -> Dict[str, Any]:
    """
    Calcula un resumen de las operaciones del día actual.
    Args:
        operations_path (str): Ruta al archivo CSV de operaciones.
    Returns:
        Dict[str, Any]: Diccionario con 'pnl_sum', 'ops_count', 'wins', 'losses'.
    """
    try:
        print(f"DEBUG: os is {os}")
        if not os.path.exists(operations_path):
            logger.warning(f"Archivo de operaciones no encontrado en {operations_path}. Retornando resumen vacío.")
            return {"pnl_sum": 0.0, "ops_count": 0, "wins": 0, "losses": 0}

        df = pd.read_csv(operations_path)
        df['timestamp_open'] = pd.to_datetime(df['timestamp_open'])

        today = datetime.now().date()
        df_today = df[df['timestamp_open'].dt.date == today]

        if df_today.empty:
            return {"pnl_sum": 0.0, "ops_count": 0, "wins": 0, "losses": 0}

        pnl_sum = df_today['pnl_percent'].sum()
        ops_count = len(df_today)
        wins = len(df_today[df_today['pnl_percent'] > 0])
        losses = len(df_today[df_today['pnl_percent'] < 0])

        return {
            "pnl_sum": pnl_sum,
            "ops_count": ops_count,
            "wins": wins,
            "losses": losses
        }
    except Exception as e:
        logger.error(f"Error al calcular el resumen de hoy: {e}", exc_info=True)
        return {"pnl_sum": 0.0, "ops_count": 0, "wins": 0, "losses": 0}

if __name__ == '__main__':
    # Bloque para pruebas manuales
    print("Realizando una prueba de lectura y cálculo de KPIs...")
    
    # Para que el logger funcione en la prueba
    from utils.logger_setup import setup_logging
    setup_logging()

    # --- Probar cálculos con datos de ejemplo ---
    print("\n--- Probando cálculos con datos de ejemplo ---")
    dummy_data = {
        'timestamp_open': [pd.to_datetime('2025-08-10 10:00:00'), pd.to_datetime('2025-08-11 11:00:00'), pd.to_datetime('2025-08-12 12:00:00'), pd.to_datetime('2025-08-13 13:00:00')],
        'timestamp_close': [pd.to_datetime('2025-08-10 11:00:00'), pd.to_datetime('2025-08-11 12:30:00'), pd.to_datetime('2025-08-12 13:00:00'), pd.to_datetime('2025-08-13 13:15:00')],
        'size_usdt': [100.0, 100.0, 100.0, 100.0],
        'pnl_percent': [10.0, -5.0, 20.0, -2.0] # 2 wins, 2 losses
    }
    dummy_df = pd.DataFrame(dummy_data)
    
    print("--- Calculando PnL (Datos de Ejemplo) ---")
    pnl_data_dummy = calculate_pnl(dummy_df)
    print(f"PnL Acumulado: {pnl_data_dummy['total_pnl_usdt']:.2f} USDT")
    print("\nPnL Diario:")
    if not pnl_data_dummy['daily_pnl_df'].empty:
        print(pnl_data_dummy['daily_pnl_df'].to_string(index=False))
    else:
        print("No hay datos de PnL diario.")
    
    print("\n--- Calculando Estadísticas de Trade (Datos de Ejemplo) ---")
    trade_stats_dummy = calculate_trade_stats(dummy_df)
    for key, value in trade_stats_dummy.items():
        if isinstance(value, float):
            print(f"{key.replace('_', ' ').title()}: {value:.2f}")
        else:
            print(f"{key.replace('_', ' ').title()}: {value}")

    print("\n--- Calculando Max Drawdown (Datos de Ejemplo) ---")
    mdd_dummy = calculate_max_drawdown(dummy_df)
    print(f"Max Drawdown: {mdd_dummy:.2f}%\n")

    print("--- Calculando Frecuencia y Duración de Trades (Datos de Ejemplo) ---")
    freq_duration_dummy = calculate_trade_frequency_and_duration(dummy_df)
    print(f"Trades por Día: {freq_duration_dummy['trades_per_day']:.2f}")
    print(f"Duración Media por Trade: {freq_duration_dummy['avg_trade_duration_minutes']:.2f} minutos\n")

    # --- Ejecutar con datos reales de la BD ---
    print("\n--- Ejecutando con datos reales de la BD ---")
    operations_df = get_operations_df(days=90)
    
    if not operations_df.empty:
        print(f"\nSe encontraron {len(operations_df)} operaciones.\n")
        print("Primeras 5 filas:")
        print(operations_df.head())
        
        # --- Probar cálculo de PnL ---
        print("\n--- Calculando PnL (Datos Reales) ---")
        pnl_data_real = calculate_pnl(operations_df)
        print(f"PnL Acumulado: {pnl_data_real['total_pnl_usdt']:.2f} USDT")
        print("\nPnL Diario:")
        if not pnl_data_real['daily_pnl_df'].empty:
            print(pnl_data_real['daily_pnl_df'].to_string(index=False))
        else:
            print("No hay datos de PnL diario.")

        print("\n--- Calculando Estadísticas de Trade (Datos Reales) ---")
        trade_stats_real = calculate_trade_stats(operations_df)
        for key, value in trade_stats_real.items():
            if isinstance(value, float):
                print(f"{key.replace('_', ' ').title()}: {value:.2f}")
            else:
                print(f"{key.replace('_', ' ').title()}: {value}")

        print("\n--- Calculando Max Drawdown (Datos Reales) ---")
        mdd_real = calculate_max_drawdown(operations_df)
        print(f"Max Drawdown: {mdd_real:.2f}%\n")

        print("--- Calculando Frecuencia y Duración de Trades (Datos Reales) ---")
        freq_duration_real = calculate_trade_frequency_and_duration(operations_df)
        print(f"Trades por Día: {freq_duration_real['trades_per_day']:.2f}")
        print(f"Duración Media por Trade: {freq_duration_real['avg_trade_duration_minutes']:.2f} minutos\n")

    else:
        print("No se encontraron operaciones en los últimos 90 días.\n")
