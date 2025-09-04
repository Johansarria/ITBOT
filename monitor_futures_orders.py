import asyncio
import argparse
import datetime as dt
from typing import Optional
from binance.client import AsyncClient
from config import settings

async def fetch_state(client: AsyncClient, symbol: str):
    orders = await client.futures_get_open_orders(symbol=symbol)
    pos_info = await client.futures_position_information(symbol=symbol)
    pos = pos_info[0] if isinstance(pos_info, list) and pos_info else None
    entry = float(pos.get('entryPrice', 0) or 0) if pos else 0.0
    amt = float(pos.get('positionAmt', 0) or 0) if pos else 0.0
    tp = sl = None
    for o in orders:
        t = o.get('type')
        stop_price = float(o.get('stopPrice') or 0)
        if t == 'TAKE_PROFIT_MARKET':
            tp = stop_price
        elif t == 'STOP_MARKET':
            sl = stop_price
    return amt, entry, tp, sl

async def monitor(symbol: str, interval: int):
    api_key = getattr(settings, 'BINANCE_API_KEY', '') or ''
    secret_key = getattr(settings, 'BINANCE_SECRET_KEY', '') or ''
    use_testnet = bool(getattr(settings, 'BINANCE_USE_TESTNET_FUTURES', False))
    client = await AsyncClient.create(api_key=api_key, api_secret=secret_key, testnet=use_testnet)
    try:
        last_tp: Optional[float] = None
        last_sl: Optional[float] = None
        last_amt: Optional[float] = None
        print(f"[MONITOR] Iniciado {symbol} cada {interval}s (testnet={use_testnet})")
        while True:
            try:
                amt, entry, tp, sl = await fetch_state(client, symbol)
                ts = dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                # Cierre detectado
                if last_amt is not None and last_amt != 0 and abs(amt) == 0:
                    print(f"[{ts}] [EVENT] CIERRE detectado en {symbol} (entry={entry})")
                    break
                # Primer muestreo
                if last_tp is None and tp is not None:
                    print(f"[{ts}] [BASE] TP={tp}")
                    last_tp = tp
                if last_sl is None and sl is not None:
                    print(f"[{ts}] [BASE] SL={sl}")
                    last_sl = sl
                # Cambios
                if tp is not None and last_tp is not None and abs(tp - last_tp) >= 1e-8:
                    print(f"[{ts}] [EVENT] TP actualizado: {last_tp} -> {tp}")
                    last_tp = tp
                if sl is not None and last_sl is not None and abs(sl - last_sl) >= 1e-8:
                    print(f"[{ts}] [EVENT] SL actualizado: {last_sl} -> {sl}")
                    last_sl = sl
                last_amt = amt
            except Exception as e:
                ts = dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{ts}] [WARN] monitor error: {e}")
            await asyncio.sleep(interval)
    finally:
        try:
            await client.close_connection()
        except Exception:
            pass

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('symbol', nargs='?', default='BNBUSDT')
    p.add_argument('--interval', type=int, default=60)
    args = p.parse_args()
    asyncio.run(monitor(args.symbol, args.interval))
