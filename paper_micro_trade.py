"""
Paper micro-trade simulator (Binance USDT-M Futures) without API keys.

Features:
- Uses public REST endpoints (no API keys) to fetch exchange info and prices.
- Computes position size under max_usdt * leverage, respecting filters (tick/step/minNotional).
- Simulates a MARKET entry at current price, with TP/SL triggers (reduce-only semantics).
- Prints live updates (price, unrealized PnL, ROI on margin) until TP/SL or timeout.

Usage (env or CLI):
- Defaults read from config.get_settings() for leverage and max_usdt when available.
"""

import asyncio
import math
import os
import sys
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import aiohttp

try:
    from config import get_settings
except Exception:
    # Allow running without full settings
    def get_settings():  # type: ignore
        class Dummy:
            MICRO_TRADE_LEVERAGE = int(os.getenv("MICRO_TRADE_LEVERAGE", "5"))
            MICRO_TRADE_MAX_USDT = float(os.getenv("MICRO_TRADE_MAX_USDT", "5"))
        return Dummy()


BINANCE_FAPI_BASE = "https://fapi.binance.com"  # Mainnet public Futures API (public endpoints only)


@dataclass
class Filters:
    tick_size: float
    step_size: float
    min_notional: float
    min_qty: float


def _round_step(value: float, step: float, up: bool = False) -> float:
    if step <= 0:
        return value
    steps = value / step
    if up:
        return math.ceil(steps) * step
    return math.floor(steps) * step


async def fetch_exchange_filters(session: aiohttp.ClientSession, symbol: str) -> Filters:
    url = f"{BINANCE_FAPI_BASE}/fapi/v1/exchangeInfo"
    async with session.get(url, timeout=15) as resp:
        resp.raise_for_status()
        data = await resp.json()
    for s in data.get("symbols", []):
        if s.get("symbol") == symbol:
            tick_size = 0.0
            step_size = 0.0
            min_notional = 0.0
            min_qty = 0.0
            for f in s.get("filters", []):
                ft = f.get("filterType")
                if ft == "PRICE_FILTER":
                    tick_size = float(f.get("tickSize", 0))
                elif ft == "LOT_SIZE":
                    step_size = float(f.get("stepSize", 0))
                    min_qty = float(f.get("minQty", 0))
                elif ft == "MIN_NOTIONAL":
                    min_notional = float(f.get("notional", f.get("minNotional", 0)))
            return Filters(tick_size=tick_size, step_size=step_size, min_notional=min_notional, min_qty=min_qty)
    raise ValueError(f"Símbolo no encontrado en exchangeInfo: {symbol}")


async def fetch_price(session: aiohttp.ClientSession, symbol: str) -> float:
    url = f"{BINANCE_FAPI_BASE}/fapi/v1/ticker/price?symbol={symbol}"
    async with session.get(url, timeout=10) as resp:
        resp.raise_for_status()
        data = await resp.json()
    return float(data["price"])


def compute_qty(symbol: str, price: float, leverage: int, max_usdt: float, filters: Filters) -> Tuple[float, float]:
    # Target notional equal to available margin * leverage (full use by default)
    max_notional = leverage * max_usdt
    if filters.min_notional and max_notional < filters.min_notional:
        # If we can't reach minNotional, still allow simulation but warn
        pass
    raw_qty = max_notional / price
    qty = max(raw_qty, filters.min_qty or 0.0)
    qty = _round_step(qty, filters.step_size)
    if qty <= 0:
        raise ValueError("Cantidad calculada es 0 tras redondeo; aumenta max_usdt o apalancamiento.")
    notional = qty * price
    return qty, notional


def fmt(n: float, digits: int = 6) -> str:
    return (f"{n:.{digits}f}")


async def run_simulation(
    symbol: str,
    side: str,
    leverage: int,
    max_usdt: float,
    tp_pct: float,
    sl_pct: float,
    duration_sec: int,
) -> int:
    side = side.upper()
    if side not in ("BUY", "SELL"):
        raise ValueError("side debe ser BUY o SELL")

    async with aiohttp.ClientSession() as session:
        filters = await fetch_exchange_filters(session, symbol)
        entry_price = await fetch_price(session, symbol)

        qty, notional = compute_qty(symbol, entry_price, leverage, max_usdt, filters)

        # Define TP/SL absolute prices
        if side == "BUY":
            tp_price = entry_price * (1 + tp_pct / 100.0)
            sl_price = entry_price * (1 - sl_pct / 100.0)
        else:
            tp_price = entry_price * (1 - tp_pct / 100.0)
            sl_price = entry_price * (1 + sl_pct / 100.0)

        # Round TP/SL to tick size
        tp_price = _round_step(tp_price, filters.tick_size, up=(side == "BUY"))
        sl_price = _round_step(sl_price, filters.tick_size, up=(side == "SELL"))

        est_taker_fee = 0.0004  # 0.04% taker (each fill)
        est_round_trip_fee = 2 * est_taker_fee * notional

        print("--- PAPER MICRO TRADE (FUTURES) ---")
        print(f"Símbolo: {symbol}  Lado: {side}  Leverage: x{leverage}")
        print(f"Margen disponible: {max_usdt} USDT  Notional simulado: {fmt(notional, 4)} USDT  Qty: {qty}")
        print(f"Entrada: {fmt(entry_price, 6)}  TP: {fmt(tp_price, 6)}  SL: {fmt(sl_price, 6)}")
        print(f"Fees estimadas ida/vuelta: {fmt(est_round_trip_fee, 6)} USDT (~{est_taker_fee*100:.4f}% por ejecución)")
        print("Monitoreando precio... (Ctrl+C para salir)\n")

        start = time.time()
        last_print = 0.0
        hit: Optional[str] = None
        hit_price: Optional[float] = None

        try:
            while True:
                now = time.time()
                if now - start >= duration_sec:
                    print("Tiempo máximo alcanzado, cerrando simulación sin TP/SL.")
                    break
                price = await fetch_price(session, symbol)

                # Check triggers
                if side == "BUY":
                    if price >= tp_price:
                        hit, hit_price = "TP", price
                        break
                    if price <= sl_price:
                        hit, hit_price = "SL", price
                        break
                else:
                    if price <= tp_price:
                        hit, hit_price = "TP", price
                        break
                    if price >= sl_price:
                        hit, hit_price = "SL", price
                        break

                # Periodic status each ~2s
                if now - last_print > 2.0:
                    # Unrealized PnL for linear USDT-M futures
                    pnl = (price - entry_price) * qty * (1 if side == "BUY" else -1)
                    roi = (pnl / max(1e-9, max_usdt)) * 100.0
                    print(f"Precio: {fmt(price,6)}  PnL: {fmt(pnl,6)} USDT  ROI: {fmt(roi,3)}%  Elapsed: {int(now-start)}s")
                    last_print = now

                await asyncio.sleep(1.0)
        except KeyboardInterrupt:
            print("Interrumpido por el usuario.")

        # Finalization and summary
        exit_code = 0
        if hit and hit_price is not None:
            pnl_gross = (hit_price - entry_price) * qty * (1 if side == "BUY" else -1)
            pnl_net = pnl_gross - est_round_trip_fee
            roi_net = (pnl_net / max(1e-9, max_usdt)) * 100.0
            print("\n--- RESULTADO ---")
            print(f"Trigger: {hit} @ {fmt(hit_price,6)}  PnL bruto: {fmt(pnl_gross,6)}  PnL neto: {fmt(pnl_net,6)} USDT  ROI neto: {fmt(roi_net,3)}%")
            exit_code = 0 if hit == "TP" else 1
        else:
            # Mark-to-market at last price
            try:
                last_price = await fetch_price(session, symbol)
            except Exception:
                last_price = entry_price
            pnl_gross = (last_price - entry_price) * qty * (1 if side == "BUY" else -1)
            pnl_net = pnl_gross - est_round_trip_fee
            roi_net = (pnl_net / max(1e-9, max_usdt)) * 100.0
            print("\n--- RESUMEN PARCIAL ---")
            print(f"Último precio: {fmt(last_price,6)}  PnL neto estimado: {fmt(pnl_net,6)} USDT  ROI neto: {fmt(roi_net,3)}%")
            exit_code = 2

        return exit_code


def parse_args(argv: list[str]):
    import argparse
    s = get_settings()
    parser = argparse.ArgumentParser(description="Paper micro-trade (Futures) sin API keys")
    parser.add_argument("--symbol", default=os.getenv("SYMBOL", "XRPUSDT"))
    parser.add_argument("--side", default=os.getenv("SIDE", "BUY"), help="BUY o SELL")
    parser.add_argument("--leverage", type=int, default=int(os.getenv("MICRO_TRADE_LEVERAGE", getattr(s, "MICRO_TRADE_LEVERAGE", 5))))
    parser.add_argument("--max-usdt", type=float, default=float(os.getenv("MICRO_TRADE_MAX_USDT", getattr(s, "MICRO_TRADE_MAX_USDT", 5.0))))
    parser.add_argument("--tp", type=float, default=float(os.getenv("TP_PCT", "0.8")), help="Take profit %")
    parser.add_argument("--sl", type=float, default=float(os.getenv("SL_PCT", "0.5")), help="Stop loss %")
    parser.add_argument("--duration", type=int, default=int(os.getenv("DURATION", "900")), help="Duración máxima en segundos (default 15min)")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    try:
        code = asyncio.run(
            run_simulation(
                symbol=args.symbol.upper(),
                side=args.side.upper(),
                leverage=args.leverage,
                max_usdt=args.max_usdt,
                tp_pct=args.tp,
                sl_pct=args.sl,
                duration_sec=args.duration,
            )
        )
    except Exception as e:
        print(f"Error en simulación: {e}")
        code = 3
    sys.exit(code)
