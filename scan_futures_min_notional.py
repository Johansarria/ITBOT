"""
Escanea Futuros USDT-M (testnet o live) y lista símbolos cuyo minNotional
sea <= (MICRO_TRADE_MAX_USDT * MICRO_TRADE_LEVERAGE).

Uso:
  python scan_futures_min_notional.py            # usa valores de config
  python scan_futures_min_notional.py 25         # umbral notional manual (USDT)

No requiere claves para exchangeInfo, pero respeta base_url de testnet si está activo.
"""
from __future__ import annotations

import sys
import requests
from config import settings


def get_exchange_info(testnet: bool) -> dict:
    base = "https://testnet.binancefuture.com" if testnet else "https://fapi.binance.com"
    url = f"{base}/fapi/v1/exchangeInfo"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


def main() -> int:
    testnet = bool(getattr(settings, 'BINANCE_USE_TESTNET_FUTURES', False))
    max_usdt = float(getattr(settings, 'MICRO_TRADE_MAX_USDT', 5.0))
    leverage = int(getattr(settings, 'MICRO_TRADE_LEVERAGE', 5))
    threshold = float(sys.argv[1]) if len(sys.argv) > 1 else max_usdt * leverage

    data = get_exchange_info(testnet)
    symbols = data.get("symbols", [])
    eligible = []
    for s in symbols:
        if s.get("status") != "TRADING":
            continue
        sym = s.get("symbol")
        min_notional = None
        for f in s.get("filters", []):
            ft = f.get("filterType")
            if ft in ("MIN_NOTIONAL", "NOTIONAL"):
                v = f.get("minNotional") or f.get("notional")
                if v is not None:
                    min_notional = float(v)
                    break
        if min_notional is None:
            continue
        if min_notional <= threshold:
            eligible.append((sym, min_notional))

    eligible.sort(key=lambda x: x[1])
    print(f"Testnet={testnet}  Threshold={threshold} USDT  (max_usdt={max_usdt}, leverage={leverage})")
    for sym, mn in eligible[:50]:
        print(f"{sym:12s}  minNotional={mn}")
    print(f"Total elegibles: {len(eligible)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
