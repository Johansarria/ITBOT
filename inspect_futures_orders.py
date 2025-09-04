import asyncio
import argparse
from binance.client import AsyncClient
from config import settings

async def main(symbol: str, baseline_tp: float | None, baseline_sl: float | None):
    api_key = getattr(settings, 'BINANCE_API_KEY', '') or ''
    secret_key = getattr(settings, 'BINANCE_SECRET_KEY', '') or ''
    use_testnet = bool(getattr(settings, 'BINANCE_USE_TESTNET_FUTURES', False))
    client = await AsyncClient.create(api_key=api_key, api_secret=secret_key, testnet=use_testnet)
    try:
        orders = await client.futures_get_open_orders(symbol=symbol)
        pos_info = await client.futures_position_information(symbol=symbol)
        pos = pos_info[0] if isinstance(pos_info, list) and pos_info else None
        entry = float(pos.get('entryPrice', 0) or 0) if pos else 0.0
        amt = float(pos.get('positionAmt', 0) or 0) if pos else 0.0

        print(f"[POSITION] symbol={symbol} entry={entry} amt={amt}")
        found_tp = found_sl = None
        for o in orders:
            t = o.get('type')
            side = o.get('side')
            stop_price = float(o.get('stopPrice') or 0)
            wp = o.get('workingType')
            print(f"[OPEN_ORDER] id={o.get('orderId')} type={t} side={side} stopPrice={stop_price} workingType={wp}")
            if t == 'TAKE_PROFIT_MARKET' and side in ('SELL','BUY'):
                found_tp = stop_price
            if t == 'STOP_MARKET' and side in ('SELL','BUY'):
                found_sl = stop_price
        if baseline_tp is not None:
            if found_tp is None:
                print(f"[CHECK] TP actual: NONE vs baseline {baseline_tp} -> NO TP ABIERTO")
            else:
                diff = found_tp - baseline_tp
                changed = abs(diff) >= 1e-8
                print(f"[CHECK] TP actual: {found_tp} vs baseline {baseline_tp} -> {'CORREGIDO' if changed else 'SIN CAMBIO'} (Δ={diff})")
        if baseline_sl is not None:
            if found_sl is None:
                print(f"[CHECK] SL actual: NONE vs baseline {baseline_sl} -> NO SL ABIERTO")
            else:
                diff = found_sl - baseline_sl
                changed = abs(diff) >= 1e-8
                print(f"[CHECK] SL actual: {found_sl} vs baseline {baseline_sl} -> {'CORREGIDO' if changed else 'SIN CAMBIO'} (Δ={diff})")
    finally:
        try:
            await client.close_connection()
        except Exception:
            pass

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('symbol', nargs='?', default='BNBUSDT')
    p.add_argument('--baseline-tp', type=float, default=None)
    p.add_argument('--baseline-sl', type=float, default=None)
    args = p.parse_args()
    asyncio.run(main(args.symbol, args.baseline_tp, args.baseline_sl))
