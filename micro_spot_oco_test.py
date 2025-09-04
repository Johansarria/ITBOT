"""
Micro-prueba Spot en vivo con OCO (TP/SL) usando python-binance (sync Client).

Flujo:
- Valida filtros (tickSize, stepSize, minQty, minNotional) del símbolo.
- Calcula qty a partir de MAX_USDT (sin apalancamiento, Spot) y precio actual.
- Ejecuta compra a mercado.
- Espera FILLED y coloca OCO de venta (limit TP + stop-loss limit).

Requiere:
- BINANCE_API_KEY / BINANCE_SECRET_KEY con permiso "Enable Spot & Margin Trading".
- BINANCE_USE_TESTNET_SPOT=False para mainnet (o True para testnet si se desea).
"""

from __future__ import annotations

import os
import sys
import time
import math
from typing import Tuple

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from config import get_settings


def _round_step(value: float, step: float, up: bool = False) -> float:
    if step <= 0:
        return value
    steps = value / step
    return (math.ceil(steps) if up else math.floor(steps)) * step


def _get_spot_filters(client: Client, symbol: str) -> Tuple[float, float, float, float]:
    info = client.get_exchange_info()
    for s in info.get("symbols", []):
        if s.get("symbol") == symbol:
            tick_size = step_size = min_qty = min_notional = 0.0
            for f in s.get("filters", []):
                ft = f.get("filterType")
                if ft == "PRICE_FILTER":
                    tick_size = float(f.get("tickSize", 0))
                elif ft == "LOT_SIZE":
                    step_size = float(f.get("stepSize", 0))
                    min_qty = float(f.get("minQty", 0))
                elif ft in ("MIN_NOTIONAL", "NOTIONAL"):
                    v = f.get("minNotional") or f.get("notional")
                    if v is not None:
                        min_notional = float(v)
            return tick_size, step_size, min_qty, min_notional
    raise ValueError(f"Símbolo Spot no encontrado: {symbol}")


def main() -> int:
    s = get_settings()
    symbol = (sys.argv[1] if len(sys.argv) > 1 else os.getenv("SYMBOL", "XRPUSDT")).upper()
    tp_pct = float(os.getenv("TP_PCT", "0.8"))
    sl_pct = float(os.getenv("SL_PCT", "0.5"))
    max_usdt = float(os.getenv("MAX_USDT", getattr(s, "MICRO_TRADE_MAX_USDT", 5.0)))

    use_testnet = bool(getattr(s, "BINANCE_USE_TESTNET_SPOT", False))
    api_key = getattr(s, "BINANCE_API_KEY", "")
    secret_key = getattr(s, "BINANCE_SECRET_KEY", "")
    client = Client(api_key=api_key, api_secret=secret_key, testnet=use_testnet)

    # Filtros y precio
    tick, step, min_qty, min_notional = _get_spot_filters(client, symbol)
    t = client.get_ticker(symbol=symbol)
    price = float(t.get("lastPrice") or t.get("weightedAvgPrice") or 0.0)
    if price <= 0:
        raise RuntimeError("No se pudo obtener precio válido")

    # Cálculo de qty por presupuesto
    raw_qty = max_usdt / price
    qty = max(raw_qty, min_qty)
    qty = _round_step(qty, step)
    notional = qty * price
    if notional < min_notional:
        print(f"[ABORT] Spot requiere minNotional≈{min_notional:.4f} USDT; con {max_usdt} USDT no alcanza en {symbol}.")
        print("        Sube MAX_USDT o elige un símbolo con minNotional menor.")
        return 2

    print(f"--- MICRO SPOT OCO ---")
    print(f"Símbolo: {symbol}  Precio≈{price:.8f}  Qty={qty}  Notional≈{notional:.4f} USDT  (minNotional={min_notional})")

    # Compra a mercado
    try:
        order = client.order_market_buy(symbol=symbol, quantity=str(qty))
        buy_order_id = order.get("orderId")
        print(f"[OK] BUY MARKET enviado. orderId={buy_order_id}")
    except (BinanceAPIException, BinanceRequestException) as e:
        print(f"[ERROR] Binance API BUY: {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] BUY inesperado: {e}")
        return 1

    # Esperar a que la compra esté FILLED
    for _ in range(20):
        o = client.get_order(symbol=symbol, orderId=buy_order_id)
        status = o.get("status")
        if status == "FILLED":
            break
        time.sleep(0.5)
    else:
        print("[WARN] BUY no confirmado FILLED a tiempo; continuando con OCO con qty comprada.")

    # Determinar precios TP/SL
    tp_price = _round_step(price * (1 + tp_pct / 100.0), tick, up=True)
    sl_trigger = _round_step(price * (1 - sl_pct / 100.0), tick)
    # stopLimitPrice ligeramente bajo el trigger para asegurar colocación
    stop_limit_price = _round_step(sl_trigger * 0.999, tick)

    # Colocar OCO SELL
    try:
        oco = client.create_oco_order(
            symbol=symbol,
            side=Client.SIDE_SELL,
            quantity=str(qty),
            price=f"{tp_price:.8f}",
            stopPrice=f"{sl_trigger:.8f}",
            stopLimitPrice=f"{stop_limit_price:.8f}",
            stopLimitTimeInForce=Client.TIME_IN_FORCE_GTC,
        )
        print("[OK] OCO SELL colocado:")
        print(f"     TP limit @ {tp_price:.8f} | SL stop @ {sl_trigger:.8f} (stopLimit {stop_limit_price:.8f})")
    except (BinanceAPIException, BinanceRequestException) as e:
        print(f"[ERROR] Binance API OCO: {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] OCO inesperado: {e}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
