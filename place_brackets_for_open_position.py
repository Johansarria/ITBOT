"""
Coloca TP/SL para una posición abierta de Futuros USDT-M usando la precisión correcta de tick.
Uso:
  python place_brackets_for_open_position.py SYMBOL

Ejemplo:
  python place_brackets_for_open_position.py XRPUSDT
"""

import asyncio
import argparse
import time
from typing import Optional

from binance.client import AsyncClient

from config import settings
from micro_futures_autonomy import (
    _get_symbol_filters_futures,
    _round_tick,
    _to_tick_precision,
)


async def place_brackets(symbol: str) -> int:
    api_key = getattr(settings, 'BINANCE_API_KEY', '') or ''
    secret_key = getattr(settings, 'BINANCE_SECRET_KEY', '') or ''
    use_testnet = bool(getattr(settings, 'BINANCE_USE_TESTNET_FUTURES', False))
    client = await AsyncClient.create(api_key=api_key, api_secret=secret_key, testnet=use_testnet)
    try:
        pos = await client.futures_position_information(symbol=symbol)
        if not isinstance(pos, list) or not pos:
            print(f"[ABORT] No se pudo obtener posición para {symbol}")
            return 2
        p = pos[0]
        amt = float(p.get('positionAmt', 0) or 0)
        if abs(amt) == 0:
            print(f"[ABORT] No hay posición abierta en {symbol}")
            return 2
        entry = float(p.get('entryPrice', 0) or 0)
        side = 'LONG' if amt > 0 else 'SHORT'
        close_side = 'SELL' if side == 'LONG' else 'BUY'

        # Filtros para tick
        _, _, tick_size = await _get_symbol_filters_futures(client, symbol)

        tp_pct = float(getattr(settings, 'RISK_PER_TRADE_TAKE_PROFIT_PCT', 4.0))
        sl_pct = float(getattr(settings, 'RISK_PER_TRADE_STOP_LOSS_PCT', 2.0))

        if side == 'LONG':
            sl_price = entry * (1 - sl_pct / 100.0)
            tp_price = entry * (1 + tp_pct / 100.0)
            sl_price = _round_tick(sl_price, tick_size, up=False)
            tp_price = _round_tick(tp_price, tick_size, up=True)
        else:
            sl_price = entry * (1 + sl_pct / 100.0)
            tp_price = entry * (1 - tp_pct / 100.0)
            sl_price = _round_tick(sl_price, tick_size, up=True)
            tp_price = _round_tick(tp_price, tick_size, up=False)

        sl_price = _to_tick_precision(sl_price, tick_size)
        tp_price = _to_tick_precision(tp_price, tick_size)

        # Cancelar órdenes abiertas y colocar nuevas reduce-only
        try:
            await client.futures_cancel_all_open_orders(symbol=symbol)
        except Exception:
            pass
        sl_working = getattr(settings, 'FUTURES_SL_WORKING_TYPE', 'CONTRACT_PRICE')
        tp_working = getattr(settings, 'FUTURES_TP_WORKING_TYPE', 'CONTRACT_PRICE')
        await client.futures_create_order(
            symbol=symbol,
            side=close_side,
            type='STOP_MARKET',
            stopPrice=sl_price,
            closePosition=True,
            workingType=sl_working,
        )
        await client.futures_create_order(
            symbol=symbol,
            side=close_side,
            type='TAKE_PROFIT_MARKET',
            stopPrice=tp_price,
            closePosition=True,
            workingType=tp_working,
        )
        print(f"[OK] Brackets colocados en {symbol}. SL@{sl_price} TP@{tp_price}")
        return 0
    except Exception as e:
        print(f"[ERROR] No se pudieron colocar brackets: {e}")
        return 1
    finally:
        try:
            await client.close_connection()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description='Colocar TP/SL para posición abierta (USDT-M) con precisión de tick')
    parser.add_argument('symbol', help='Símbolo, p.ej. XRPUSDT')
    args = parser.parse_args()
    return asyncio.run(place_brackets(args.symbol.upper()))


if __name__ == '__main__':
    raise SystemExit(main())
