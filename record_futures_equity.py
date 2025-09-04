import os
import sys
import csv
import json
import time
import asyncio
from datetime import datetime
from typing import Optional

from binance.client import AsyncClient
from config import settings


def _ensure_dirs(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _load_baseline() -> tuple[float, int]:
    storage_dir = os.path.join(os.getcwd(), 'storage')
    os.makedirs(storage_dir, exist_ok=True)
    baseline_path = os.path.join(storage_dir, 'futures_baseline.json')
    amount: float = 0.0
    t_ms: int = 0
    if os.path.exists(baseline_path):
        try:
            with open(baseline_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                amount = float(data.get('amount', 0) or 0)
                t_ms = int(data.get('time_ms', 0) or 0)
        except Exception:
            pass
    return amount, t_ms


async def _fetch_equity() -> tuple[float, float, float]:
    cli = await AsyncClient.create(api_key=settings.BINANCE_API_KEY, api_secret=settings.BINANCE_SECRET_KEY, testnet=bool(getattr(settings,'BINANCE_USE_TESTNET_FUTURES', False)))
    try:
        acc = await cli.futures_account()
        equity = float(acc.get('totalMarginBalance', 0) or 0)
        wallet = float(acc.get('totalWalletBalance', 0) or 0)
        upnl = float(acc.get('totalUnrealizedProfit', 0) or 0)
        return equity, wallet, upnl
    finally:
        try:
            await cli.close_connection()
        except Exception:
            pass


async def _fetch_realized_since(start_ms: int) -> float:
    if not start_ms:
        return 0.0
    cli = await AsyncClient.create(api_key=settings.BINANCE_API_KEY, api_secret=settings.BINANCE_SECRET_KEY, testnet=bool(getattr(settings,'BINANCE_USE_TESTNET_FUTURES', False)))
    try:
        inc = await cli.futures_income_history(startTime=start_ms, limit=1000)
        realized_types = ('REALIZED_PNL','COMMISSION','FUNDING_FEE')
        realized = [r for r in inc if r.get('incomeType') in realized_types]
        total = sum(float(r.get('income',0) or 0) for r in realized)
        return float(total)
    finally:
        try:
            await cli.close_connection()
        except Exception:
            pass


async def record_once(out_path: str):
    baseline, start_ms = _load_baseline()
    equity, wallet, upnl = await _fetch_equity()
    realized = await _fetch_realized_since(start_ms)
    roi_pct = ((equity - baseline)/baseline*100.0) if baseline else 0.0
    ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    _ensure_dirs(out_path)
    write_header = not os.path.exists(out_path)
    with open(out_path, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(['timestamp','equity','wallet','upnl','realized_since_baseline','baseline','roi_pct'])
        w.writerow([ts, f'{equity:.8f}', f'{wallet:.8f}', f'{upnl:.8f}', f'{realized:.8f}', f'{baseline:.8f}', f'{roi_pct:.6f}'])
    print(f'RECORDED {ts} equity={equity:.8f} roi_pct={roi_pct:.6f}')


async def main():
    out_dir = os.path.join(os.getcwd(), 'logs')
    out_path = os.path.join(out_dir, 'equity_history.csv')
    interval = int(os.getenv('EQUITY_RECORD_INTERVAL_SEC', '300'))
    once = '--once' in sys.argv
    if '--interval' in sys.argv:
        try:
            idx = sys.argv.index('--interval')
            interval = int(sys.argv[idx+1])
        except Exception:
            pass

    if once:
        await record_once(out_path)
        return

    # Loop
    while True:
        try:
            await record_once(out_path)
        except Exception as e:
            # Log to stdout; continue
            print(f'RECORD_ERROR {e}')
        await asyncio.sleep(interval)


if __name__ == '__main__':
    asyncio.run(main())
