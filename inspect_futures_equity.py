import os
import json
import time
import asyncio
from binance.client import AsyncClient
from config import settings


async def main():
    api_key = getattr(settings, 'BINANCE_API_KEY', '') or ''
    secret_key = getattr(settings, 'BINANCE_SECRET_KEY', '') or ''
    use_testnet = bool(getattr(settings, 'BINANCE_USE_TESTNET_FUTURES', False))

    client = await AsyncClient.create(api_key=api_key, api_secret=secret_key, testnet=use_testnet)
    try:
        acc = await client.futures_account()
        # Campos clave (strings numéricas)
        total_wallet = float(acc.get('totalWalletBalance', 0) or 0)
        total_upnl = float(acc.get('totalUnrealizedProfit', 0) or 0)
        total_margin = float(acc.get('totalMarginBalance', total_wallet + total_upnl))

        # Baseline dinámico: storage/futures_baseline.json
        storage_dir = os.path.join(os.getcwd(), 'storage')
        os.makedirs(storage_dir, exist_ok=True)
        baseline_path = os.path.join(storage_dir, 'futures_baseline.json')

        baseline: float | None = None
        baseline_source = 'env_or_default'
        if os.path.exists(baseline_path):
            try:
                with open(baseline_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    baseline = float(data.get('amount', 0))
                    baseline_source = str(data.get('source', 'file'))
            except Exception:
                baseline = None

        if baseline is None or baseline <= 0:
            # Intentar desde ENV
            env_initial = os.getenv('EQUITY_INITIAL_BALANCE')
            if env_initial:
                try:
                    baseline = float(env_initial)
                    baseline_source = 'env'
                except Exception:
                    baseline = None

        if baseline is None or baseline <= 0:
            # Auto-inicializar al depósito actual (wallet) y persistir
            baseline = float(total_wallet)
            baseline_source = 'auto_wallet'
            payload = {
                'amount': baseline,
                'source': baseline_source,
                'time_ms': int(time.time() * 1000)
            }
            try:
                with open(baseline_path, 'w', encoding='utf-8') as f:
                    json.dump(payload, f)
            except Exception:
                pass

        # PnL contra baseline (equity vs baseline)
        pnl_abs_equity = total_margin - baseline
        pnl_pct_equity = (pnl_abs_equity / baseline * 100.0) if baseline else 0.0

        # También mostrar PnL contra wallet baseline (wallet vs baseline) para contexto
        pnl_abs_wallet = total_wallet - baseline
        pnl_pct_wallet = (pnl_abs_wallet / baseline * 100.0) if baseline else 0.0

        # Salida minimalista para fácil parseo
        print(f"BASELINE={baseline:.8f}")
        print(f"BASELINE_SOURCE={baseline_source}")
        print(f"CURRENT_WALLET={total_wallet:.8f}")
        print(f"CURRENT_EQUITY={total_margin:.8f}")
        print(f"PNL_EQUITY_ABS={pnl_abs_equity:.8f}")
        print(f"PNL_EQUITY_PCT={pnl_pct_equity:.6f}")
        print(f"PNL_WALLET_ABS={pnl_abs_wallet:.8f}")
        print(f"PNL_WALLET_PCT={pnl_pct_wallet:.6f}")
    finally:
        try:
            await client.close_connection()
        except Exception:
            pass


if __name__ == '__main__':
    asyncio.run(main())
