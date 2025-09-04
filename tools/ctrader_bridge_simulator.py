#!/usr/bin/env python3
"""
Simulador simple del puente cTrader: pull -> "ejecución" -> ack.
- Realiza polling a /api/ctrader/orders/pull usando X-Internal-Secret
- Para cada orden, genera un fill simulado y llama /api/ctrader/orders/ack

Uso rápido:
  INTERNAL_API_SECRET=local-internal-secret \
  WEB_API_BASE_URL=http://localhost:8080 \
  python tools/ctrader_bridge_simulator.py --interval 1.0

Nota: Es solo un simulador para validar el bridge; reemplaza por tu cBot real.
"""
import os
import time
import json
import random
import argparse
import datetime as dt
import requests

DEFAULT_BASE = os.getenv("WEB_API_BASE_URL", "http://localhost:8080").rstrip("/")
DEFAULT_SECRET = os.getenv("INTERNAL_API_SECRET", "local-internal-secret")


def pull_orders(base: str, secret: str) -> list[dict]:
    url = f"{base}/api/ctrader/orders/pull"
    headers = {"X-Internal-Secret": secret}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("orders", []) if isinstance(data, dict) else []
        else:
            print(f"[pull] HTTP {resp.status_code}: {resp.text}")
            return []
    except Exception as e:
        raise


def ack_order(base: str, secret: str, *, oid: str, status: str, executed_price: float | None, executed_qty: float | None, error: str | None = None):
    url = f"{base}/api/ctrader/orders/ack"
    headers = {"X-Internal-Secret": secret, "Content-Type": "application/json"}
    payload = {
        "id": oid,
        "status": status,
        "executed_price": executed_price,
        "executed_qty": executed_qty,
        "error": error,
        "ts": dt.datetime.utcnow().isoformat()
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code != 200:
            print(f"[ack] HTTP {resp.status_code}: {resp.text}")
        else:
            print(f"[ack] OK: {resp.json()}")
    except Exception as e:
        print(f"[ack] Exception: {e}")


def simulate_execution(order: dict) -> tuple[str, float | None, float | None, str | None]:
    """
    Simula ejecución de una orden cTrader: retorna (status, executed_price, executed_qty, error)
    - status: FILLED / REJECTED / ERROR
    """
    try:
        side = str(order.get("side", "")).upper()
        qty = float(order.get("quantity", 0))
        sym = order.get("symbol", "")
        # Precio simulado: usar 100 con ligera variación
        px = round(100 * (1 + random.uniform(-0.001, 0.001)), 5)
        # Para MARKET, consideramos fill inmediato si qty > 0
        if qty > 0 and side in ("BUY", "SELL"):
            return ("FILLED", px, qty, None)
        return ("REJECTED", None, None, "Invalid side/quantity")
    except Exception as e:
        return ("ERROR", None, None, str(e))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=DEFAULT_BASE, help="Base URL del Web API (default: %(default)s)")
    parser.add_argument("--secret", default=DEFAULT_SECRET, help="Secreto interno (default: %(default)s)")
    parser.add_argument("--interval", type=float, default=1.0, help="Intervalo de polling en segundos (default: %(default)s)")
    args = parser.parse_args()

    print(f"cTrader bridge simulator iniciado -> base={args.base}, interval={args.interval}s")

    # Preflight: esperar a que el web esté listo
    max_wait = 20
    waited = 0
    while waited < max_wait:
        try:
            _ = pull_orders(args.base, args.secret)
            break
        except Exception:
            time.sleep(1)
            waited += 1
    if waited >= max_wait:
        print("[preflight] Web no disponible todavía; continuaré con reintentos en bucle.")

    # Bucle con backoff ante fallos
    failures = 0
    while True:
        try:
            orders = pull_orders(args.base, args.secret)
            failures = 0
            if orders:
                print(f"[pull] {len(orders)} órdenes")
            for o in orders:
                oid = o.get("id")
                status, ex_price, ex_qty, err = simulate_execution(o)
                print(f"[exec] {oid} -> {status} price={ex_price} qty={ex_qty} err={err}")
                ack_order(args.base, args.secret, oid=oid, status=status, executed_price=ex_price, executed_qty=ex_qty, error=err)
            time.sleep(max(0.05, args.interval))
        except Exception as e:
            failures += 1
            if failures <= 3 or failures % 10 == 0:
                print(f"[pull] Exception: {e}")
            # Backoff controlado (hasta 5s)
            time.sleep(min(args.interval * (1 + failures), 5.0))


if __name__ == "__main__":
    main()
