import asyncio
from typing import List

from binance.client import AsyncClient

from config import settings


async def main():
    api_key = getattr(settings, 'BINANCE_API_KEY', '') or ''
    secret_key = getattr(settings, 'BINANCE_SECRET_KEY', '') or ''
    use_testnet = bool(getattr(settings, 'BINANCE_USE_TESTNET_FUTURES', False))
    client = await AsyncClient.create(api_key=api_key, api_secret=secret_key, testnet=use_testnet)
    try:
        positions = await client.futures_position_information()
        open_positions = [p for p in positions if abs(float(p.get('positionAmt', 0) or 0)) > 0]
        if not open_positions:
            print("NO_OPEN_POSITIONS")
            return
        for p in open_positions:
            sym = p.get('symbol')
            amt = float(p.get('positionAmt', 0) or 0)
            side = 'LONG' if amt > 0 else 'SHORT'
            entry = float(p.get('entryPrice', 0) or 0)
            upnl = float(p.get('unRealizedProfit', 0) or 0)
            ticker = await client.futures_symbol_ticker(symbol=sym)
            mark = float(ticker.get('price', 0) or 0)
            print(f"POS {sym} {side} qty={abs(amt)} entry={entry} mark={mark} upnl={upnl}")
            try:
                orders = await client.futures_get_open_orders(symbol=sym)
            except Exception:
                orders = []
            if not orders:
                print(f"ORDERS {sym} NONE")
            else:
                for o in orders:
                    t = o.get('type')
                    s = o.get('side')
                    sp = o.get('stopPrice') or o.get('price')
                    cp = o.get('closePosition')
                    st = o.get('status')
                    print(f"ORDER {sym} {t} {s} stop/price={sp} closePos={cp} status={st}")
    finally:
        try:
            await client.close_connection()
        except Exception:
            pass


if __name__ == '__main__':
    asyncio.run(main())
