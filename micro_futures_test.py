"""
Script de micro-prueba en Binance Futuros USDT-M (mainnet o testnet) usando python-binance AsyncClient.

Objetivo: Ejecutar una orden de mercado mínima (respetando minNotional) con
apalancamiento controlado y colocar órdenes de cierre (TP/SL) reduce-only.

Configuración (config.py / variables de entorno):
- BINANCE_USE_TESTNET_FUTURES: True para testnet, False para mainnet.
- ENABLE_MICRO_TRADE, MICRO_TRADE_LEVERAGE, MICRO_TRADE_MAX_USDT, MICRO_TRADE_ALLOWED_SYMBOLS.
- BINANCE_API_KEY / BINANCE_SECRET_KEY: claves con permiso de Futuros.

Uso:
- python micro_futures_test.py                 # BTCUSDT BUY por defecto
- python micro_futures_test.py XRPUSDT BUY     # Recomendada por minNotional bajo
- python micro_futures_test.py ETHUSDT SELL
"""

from __future__ import annotations

import sys
from typing import Optional, Tuple
from config import settings
from binance.client import AsyncClient
from binance.exceptions import BinanceAPIException, BinanceRequestException
import asyncio
import math


async def _get_symbol_filters_futures(client: AsyncClient, symbol: str) -> Tuple[float, float, float]:
    """Obtiene (min_notional, step_size, tick_size) para un símbolo de Futuros USDT-M."""
    info = await client.futures_exchange_info()
    symbols = info.get("symbols", []) if isinstance(info, dict) else []
    for s in symbols:
        if s.get("symbol") == symbol:
            min_notional = 0.0
            step_size = 0.0
            tick_size = 0.0
            for f in s.get("filters", []):
                ftype = f.get("filterType")
                if ftype in ("NOTIONAL", "MIN_NOTIONAL"):
                    val = f.get("minNotional") or f.get("notional") or 0
                    min_notional = float(val)
                elif ftype in ("LOT_SIZE", "MARKET_LOT_SIZE"):
                    val = f.get("stepSize") or 0
                    step_size = float(val)
                elif ftype == "PRICE_FILTER":
                    val = f.get("tickSize") or 0
                    tick_size = float(val)
            return min_notional, step_size, tick_size
    raise ValueError(f"Símbolo de Futuros no encontrado: {symbol}")


def _round_step(value: float, step: float) -> float:
    if step <= 0:
        return value
    # Redondeo hacia abajo al múltiplo de step
    return (math.floor(value / step)) * step

def _round_tick(value: float, tick: float, up: bool = False) -> float:
    if tick <= 0:
        return value
    steps = value / tick
    k = math.ceil(steps) if up else math.floor(steps)
    return k * tick

async def main_async(symbol: str, side: str) -> int:
    if not settings.ENABLE_MICRO_TRADE:
        print("[ABORT] ENABLE_MICRO_TRADE=False en config. Actívalo para usar este script.")
        return 2
    if not settings.MICRO_TRADE_USE_FUTURES:
        print("[ABORT] MICRO_TRADE_USE_FUTURES=False. Este script solo trabaja con Futuros USDT-M.")
        return 2

    symbol = symbol.upper()
    side = side.upper()
    if side not in ("BUY", "SELL"):
        print("[ABORT] Side inválido. Usa BUY o SELL.")
        return 2
    if settings.MICRO_TRADE_ALLOWED_SYMBOLS and symbol not in settings.MICRO_TRADE_ALLOWED_SYMBOLS:
        print(f"[ABORT] {symbol} no está en MICRO_TRADE_ALLOWED_SYMBOLS: {settings.MICRO_TRADE_ALLOWED_SYMBOLS}")
        return 2

    # Crear AsyncClient (python-binance)
    api_key = getattr(settings, 'BINANCE_API_KEY', '') or ''
    secret_key = getattr(settings, 'BINANCE_SECRET_KEY', '') or ''
    use_testnet = bool(getattr(settings, 'BINANCE_USE_TESTNET_FUTURES', False))
    client = await AsyncClient.create(api_key=api_key, api_secret=secret_key, testnet=use_testnet)
    leverage = int(settings.MICRO_TRADE_LEVERAGE)
    max_usdt = float(settings.MICRO_TRADE_MAX_USDT)

    # Setear apalancamiento
    try:
        await client.futures_change_leverage(symbol=symbol, leverage=leverage)
    except Exception as e:
        print(f"[WARN] No se pudo cambiar apalancamiento: {e}")

    # Precio actual y spread (book ticker)
    bt = await client.futures_orderbook_ticker(symbol=symbol)
    bid = float(bt.get("bidPrice", 0) or 0)
    ask = float(bt.get("askPrice", 0) or 0)
    if ask <= 0 or bid <= 0:
        tpx = await client.futures_symbol_ticker(symbol=symbol)
        px = float(tpx.get("price", 0) or 0)
        spread_pct = 0.0
    else:
        px = (bid + ask) / 2.0
        spread = max(ask - bid, 0.0)
        spread_pct = (spread / ask) * 100 if ask > 0 else 0.0
    # Filtros
    min_notional, step_size, tick_size = await _get_symbol_filters_futures(client, symbol)

    # Notional que podemos abrir con el margen disponible (max_usdt) y leverage
    max_notional_by_margin = max_usdt * leverage
    if min_notional > max_notional_by_margin:
        print(
            f"[ABORT] minNotional({min_notional}) > margen permitido({max_notional_by_margin}).\n"
            f"        Sube leverage o MICRO_TRADE_MAX_USDT, u usa otro símbolo."
        )
        return 2

    # Calcular cantidad mínima por minNotional y máxima por margen
    qty_min = min_notional / px
    qty_max = max_notional_by_margin / px
    # Ajustar por step size (ceil para mínimo, floor para máximo)
    if step_size > 0:
        # ceil to step
        qty_min = ((int(qty_min / step_size) + (0 if abs(qty_min % step_size) < 1e-12 else 1)) * step_size)
        # floor to step
        qty_max = (int(qty_max / step_size) * step_size)
    if qty_min <= 0 or qty_max <= 0 or qty_min > qty_max:
        print(f"[ABORT] No se puede cumplir minNotional dentro del margen. qty_min={qty_min}, qty_max={qty_max}")
        return 2
    qty = qty_min

    print(f"[INFO] Precio={px}, minNotional={min_notional}, step={step_size}, qty={qty}")
    # Estimación de costes y margen neto
    taker_fee_per_side = float(getattr(settings, 'FUTURES_TAKER_FEE_PCT', 0.04))  # % por lado
    total_fees_pct = taker_fee_per_side * 2.0  # entrada + salida
    tp_pct = float(getattr(settings, 'RISK_PER_TRADE_TAKE_PROFIT_PCT', 4.0))
    sl_pct = float(getattr(settings, 'RISK_PER_TRADE_STOP_LOSS_PCT', 2.0))
    net_tp_pct = tp_pct - total_fees_pct - spread_pct
    net_sl_pct = sl_pct + total_fees_pct  # pérdida incluye fees
    notional = px * qty
    # ROI sobre margen (notional / leverage ≈ margen)
    margin_used = notional / max(leverage, 1)
    net_tp_usdt = notional * (net_tp_pct / 100.0)
    net_sl_usdt = notional * (net_sl_pct / 100.0)
    roi_tp_pct_on_margin = (net_tp_usdt / margin_used * 100.0) if margin_used > 0 else 0.0
    roi_sl_pct_on_margin = (net_sl_usdt / margin_used * 100.0) if margin_used > 0 else 0.0
    print(f"[COST] spread={spread_pct:.4f}%  fees(round-trip)≈{total_fees_pct:.4f}%  takerSide≈{taker_fee_per_side:.4f}%")
    print(f"[MARGIN] Neto TP≈{net_tp_pct:.4f}% ({net_tp_usdt:.4f} USDT), Neto SL≈-{net_sl_pct:.4f}% (-{net_sl_usdt:.4f} USDT)")
    print(f"[ROI] Sobre margen usado≈{margin_used:.4f} USDT → TP≈{roi_tp_pct_on_margin:.2f}%  SL≈-{roi_sl_pct_on_margin:.2f}%")
    print(f"[INFO] Enviando orden de mercado {side} {symbol} qty={qty} (testnet={settings.BINANCE_USE_TESTNET_FUTURES})")

    try:
        order = await client.futures_create_order(symbol=symbol, side=side, type="MARKET", quantity=qty)
        print(f"[OK] Entrada ejecutada. orderId={order.get('orderId')}")
    except (BinanceAPIException, BinanceRequestException) as e:
        print(f"[ERROR] Binance API: {e}")
        try:
            await client.close_connection()
        except Exception:
            pass
        return 1
    except Exception as e:
        print(f"[ERROR] Excepción inesperada: {e}")
        try:
            await client.close_connection()
        except Exception:
            pass
        return 1

    # TP/SL
    sl_pct = float(getattr(settings, 'RISK_PER_TRADE_STOP_LOSS_PCT', 2.0))
    tp_pct = float(getattr(settings, 'RISK_PER_TRADE_TAKE_PROFIT_PCT', 4.0))
    # Para BUY: SL por debajo, TP por arriba. Para SELL, inverso. Redondear a tick_size válido.
    if side == "BUY":
        sl_price = _round_tick(px * (1 - sl_pct / 100), tick_size, up=False)
        tp_price = _round_tick(px * (1 + tp_pct / 100), tick_size, up=True)
    else:
        sl_price = _round_tick(px * (1 + sl_pct / 100), tick_size, up=True)
        tp_price = _round_tick(px * (1 - tp_pct / 100), tick_size, up=False)

    try:
        # STOP (reduce-only)
        await client.futures_create_order(
            symbol=symbol,
            side=("SELL" if side == "BUY" else "BUY"),
            type="STOP_MARKET",
            stopPrice=sl_price,
            closePosition=True,
            workingType="CONTRACT_PRICE",
        )
        # TAKE PROFIT (reduce-only)
        await client.futures_create_order(
            symbol=symbol,
            side=("SELL" if side == "BUY" else "BUY"),
            type="TAKE_PROFIT_MARKET",
            stopPrice=tp_price,
            closePosition=True,
            workingType="CONTRACT_PRICE",
        )
        print(f"[OK] TP/SL colocados. SL@{sl_price:.6f}, TP@{tp_price:.6f}")
    except Exception as e:
        print(f"[WARN] No se pudieron colocar TP/SL reduce-only: {e}")

    try:
        await client.close_connection()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sym = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
    sd = sys.argv[2] if len(sys.argv) > 2 else "BUY"
    raise SystemExit(asyncio.run(main_async(sym, sd)))
