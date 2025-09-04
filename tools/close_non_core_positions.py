import asyncio
import os
import sys
from typing import Dict, Tuple

from binance.client import AsyncClient

# Asegura que el proyecto raíz esté en sys.path para importar config
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import reload_settings


def _round_step(value: float, step: float) -> float:
    if step <= 0:
        return value
    k = int(value / step)
    return k * step


async def _get_step_sizes(client: AsyncClient) -> Dict[str, Tuple[float, float]]:
    """Devuelve {symbol: (step_size, tick_size)} para Futuros USDT-M."""
    info = await client.futures_exchange_info()
    out: Dict[str, Tuple[float, float]] = {}
    for s in info.get("symbols", []) or []:
        sym = s.get("symbol")
        step = tick = 0.0
        for f in s.get("filters", []) or []:
            if f.get("filterType") in ("LOT_SIZE", "MARKET_LOT_SIZE"):
                step = float(f.get("stepSize") or 0)
            elif f.get("filterType") == "PRICE_FILTER":
                tick = float(f.get("tickSize") or 0)
        out[sym] = (step, tick)
    return out


async def close_non_core_positions():
    s = reload_settings()
    core = set(s.MICRO_TRADE_ALLOWED_SYMBOLS or [])
    client = await AsyncClient.create(api_key=s.BINANCE_API_KEY, api_secret=s.BINANCE_SECRET_KEY, testnet=bool(s.BINANCE_USE_TESTNET_FUTURES))
    try:
        steps = await _get_step_sizes(client)
        positions = await client.futures_position_information()
        to_close = []
        for p in positions:
            sym = p.get("symbol")
            amt = float(p.get("positionAmt", 0) or 0)
            if abs(amt) > 0 and sym not in core:
                to_close.append((sym, amt))

        if not to_close:
            print("No hay posiciones no-core para cerrar.")
            return

        print(f"Cerrando posiciones no-core: {to_close}")
        for sym, amt in to_close:
            side = 'SELL' if amt > 0 else 'BUY'
            qty = abs(amt)
            step = steps.get(sym, (0.0, 0.0))[0]
            if step and step > 0:
                qty = _round_step(qty, step)
            if qty <= 0:
                print(f"[SKIP] {sym} qty calculada no válida: {qty}")
                continue
            try:
                await client.futures_cancel_all_open_orders(symbol=sym)
            except Exception:
                pass
            try:
                order = await client.futures_create_order(symbol=sym, side=side, type='MARKET', reduceOnly=True, quantity=qty)
                print(f"[OK] Cerrado {sym} {side} qty={qty}. orderId={order.get('orderId')}")
            except Exception as e:
                print(f"[ERR] Fallo cerrando {sym}: {e}")
    finally:
        try:
            await client.close_connection()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(close_non_core_positions())
