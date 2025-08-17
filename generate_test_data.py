import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

ALL_OPERATION_COLUMNS = [
    "operation_id", "timestamp_open", "timestamp_close", "symbol", "side",
    "entry_price", "exit_price", "take_profit", "stop_loss", "size_usdt",
    "risk_percent", "mode", "pnl_usdt", "pnl_percent", "reason_open",
    "reason_close", "market_score_open", "market_score_close", "version_bot", "notes",
    "balance_usdt_al_abrir", "escudo_activo_al_abrir", "tipo_escudo_al_abrir", "riesgo_forzado_al_abrir",
    "cantidad_token_operada", "min_notional_filter", "step_size_filter", "price_tick_size_filter",
    "slippage_apertura_pct", "order_id_binance", "order_status_binance"
]

def generate_random_operations(num_records=50, start_date_str="2025-08-01", end_date_str="2025-08-11"):
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT"]
    sides = ["BUY", "SELL"]
    reason_opens = ["ML_SIGNAL", "TECHNICAL_ANALYSIS", "MANUAL_ENTRY"]
    reason_closes = ["TAKE_PROFIT", "STOP_LOSS", "MANUAL_CLOSE", "TIME_EXPIRATION", "N/A"]

    data = []
    for i in range(num_records):
        row_data = {col: np.nan for col in ALL_OPERATION_COLUMNS} # Initialize all columns with NaN

        row_data["operation_id"] = i + 1
        
        # Random timestamp within the range
        time_delta = end_date - start_date
        random_seconds = random.randint(0, int(time_delta.total_seconds()))
        row_data["timestamp_open"] = start_date + timedelta(seconds=random_seconds)

        row_data["symbol"] = random.choice(symbols)
        row_data["side"] = random.choice(sides)
        
        row_data["entry_price"] = round(random.uniform(1000, 70000), 2) # Wide range for crypto
        
        # 20% chance of being an open position (N/A exit_price)
        if random.random() < 0.2:
            row_data["exit_price"] = np.nan 
            row_data["pnl_percent"] = np.nan
            row_data["reason_close"] = "N/A"
        else:
            # Generate pnl_percent first, then calculate exit_price
            row_data["pnl_percent"] = round(random.uniform(-10, 10), 2) # -10% to +10%
            row_data["exit_price"] = round(row_data["entry_price"] * (1 + row_data["pnl_percent"] / 100), 2)
            row_data["reason_close"] = random.choice([r for r in reason_closes if r != "N/A"]) # Ensure not N/A if closed

        row_data["reason_open"] = random.choice(reason_opens)
        row_data["version_bot"] = "1.0.0_test"
        row_data["mode"] = "test_mode"
        row_data["risk_percent"] = round(random.uniform(0.5, 5.0), 2)
        row_data["size_usdt"] = round(random.uniform(10, 1000), 2)
        
        # Calculate pnl_usdt if pnl_percent is not NaN
        if pd.notna(row_data["pnl_percent"]):
            row_data["pnl_usdt"] = round(row_data["size_usdt"] * (row_data["pnl_percent"] / 100), 2)
        else:
            row_data["pnl_usdt"] = np.nan

        # Add some random values for other relevant columns
        row_data["timestamp_close"] = row_data["timestamp_open"] + timedelta(minutes=random.randint(30, 1440)) if pd.notna(row_data["exit_price"]) else np.nan
        row_data["take_profit"] = round(row_data["entry_price"] * (1 + random.uniform(0.01, 0.05)), 2)
        row_data["stop_loss"] = round(row_data["entry_price"] * (1 - random.uniform(0.01, 0.05)), 2)
        row_data["market_score_open"] = round(random.uniform(0.1, 0.9), 2)
        row_data["market_score_close"] = round(random.uniform(0.1, 0.9), 2) if pd.notna(row_data["exit_price"]) else np.nan
        row_data["balance_usdt_al_abrir"] = round(random.uniform(10000, 50000), 2)
        row_data["escudo_activo_al_abrir"] = random.choice([True, False])
        row_data["tipo_escudo_al_abrir"] = random.choice(["volatilidad_alta", "extremo", np.nan]) if row_data["escudo_activo_al_abrir"] else np.nan
        row_data["riesgo_forzado_al_abrir"] = random.choice([True, False])
        row_data["cantidad_token_operada"] = round(row_data["size_usdt"] / row_data["entry_price"], 5)
        row_data["min_notional_filter"] = 10.0
        row_data["step_size_filter"] = 0.00001
        row_data["price_tick_size_filter"] = 0.01
        row_data["slippage_apertura_pct"] = round(random.uniform(0.001, 0.01), 4)
        row_data["order_id_binance"] = f"order_{row_data['operation_id']}"
        row_data["order_status_binance"] = random.choice(["FILLED", "PARTIALLY_FILLED"]) if pd.notna(row_data["exit_price"]) else "NEW"

        data.append([row_data[col] for col in ALL_OPERATION_COLUMNS])

    df = pd.DataFrame(data, columns=ALL_OPERATION_COLUMNS)
    
    # Ensure timestamp_open and timestamp_close are datetime type for proper CSV saving and later parsing
    df['timestamp_open'] = pd.to_datetime(df['timestamp_open'])
    df['timestamp_close'] = pd.to_datetime(df['timestamp_close']) # Convert to datetime

    output_path = "data/operaciones/operaciones.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Generated {num_records} random operations to {output_path}")

# Call the function to generate the data
generate_random_operations()