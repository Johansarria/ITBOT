import asyncio
from datetime import datetime
import uuid
import random

# Simular la clase Bot de aiogram
class MockBot:
    async def send_message(self, chat_id, text, parse_mode=None, reply_markup=None):
        print(f"[MockBot] Mensaje a {chat_id}: {text}")

# Importar la función real de registro
from utils.order_executor import registrar_operacion
from utils.shield_manager import escudo_activo
from utils.risk_manager import riesgo_forzado_activo

async def log_dummy_operation():
    dummy_bot = MockBot()
    dummy_chat_id = 123456789 # Un ID de chat ficticio

    # Datos de ejemplo para una operación
    operation_id = str(uuid.uuid4())
    timestamp_open = datetime(2025, 8, 5, 10, 30, 0).isoformat() # Fixed date for testing
    timestamp_close = None # Aún no cerrada
    symbol = "BTCUSDT"
    side = random.choice(["BUY", "SELL"])
    entry_price = round(random.uniform(50000, 70000), 2)
    exit_price = None
    take_profit = round(entry_price * 1.02, 2)
    stop_loss = round(entry_price * 0.98, 2)
    size_usdt = round(random.uniform(100, 500), 2)
    risk_percent = round(random.uniform(0.5, 2.0), 2)
    mode = random.choice(["REAL", "SIMULATED"])
    pnl_usdt = None
    pnl_percent = None
    reason_open = random.choice(["IA_SIGNAL", "MANUAL_ENTRY", "TECHNICAL_SIGNAL"])
    reason_close = None
    market_score_open = round(random.uniform(0.6, 0.9), 2)
    market_score_close = None
    version_bot = "1.0.0-dummy"
    notes = "Operación de prueba generada por script."
    balance_usdt_al_abrir = round(random.uniform(10000, 20000), 2)
    escudo_activo_al_abrir = escudo_activo() != "ninguno"
    tipo_escudo_al_abrir = escudo_activo()
    riesgo_forzado_al_abrir = riesgo_forzado_activo()
    cantidad_token_operada = size_usdt / entry_price
    min_notional_filter = 10.0
    step_size_filter = 0.0001
    price_tick_size_filter = 0.01
    slippage_apertura_pct = round(random.uniform(-0.05, 0.05), 2)
    order_id_binance = str(uuid.uuid4()) if mode == "REAL" else None
    order_status_binance = "FILLED" if mode == "REAL" else None

    log_data = {
        "operation_id": operation_id,
        "timestamp_open": timestamp_open,
        "timestamp_close": timestamp_close,
        "symbol": symbol,
        "side": side,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "size_usdt": size_usdt,
        "risk_percent": risk_percent,
        "mode": mode,
        "pnl_usdt": pnl_usdt,
        "pnl_percent": pnl_percent,
        "reason_open": reason_open,
        "reason_close": reason_close,
        "market_score_open": market_score_open,
        "market_score_close": market_score_close,
        "version_bot": version_bot,
        "notes": notes,
        "balance_usdt_al_abrir": balance_usdt_al_abrir,
        "escudo_activo_al_abrir": escudo_activo_al_abrir,
        "tipo_escudo_al_abrir": tipo_escudo_al_abrir,
        "riesgo_forzado_al_abrir": riesgo_forzado_al_abrir,
        "cantidad_token_operada": cantidad_token_operada,
        "min_notional_filter": min_notional_filter,
        "step_size_filter": step_size_filter,
        "price_tick_size_filter": price_tick_size_filter,
        "slippage_apertura_pct": slippage_apertura_pct,
        "order_id_binance": order_id_binance,
        "order_status_binance": order_status_binance
    }

    await registrar_operacion(dummy_bot, dummy_chat_id, log_data)
    print("Operación dummy registrada exitosamente.")

if __name__ == "__main__":
    asyncio.run(log_dummy_operation())
