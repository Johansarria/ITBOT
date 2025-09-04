import os, json, sys, time

# Usage: python set_futures_baseline.py [amount]
# If amount not provided, uses CURRENT wallet amount requires running inspect_futures_equity.py first.

storage_dir = os.path.join(os.getcwd(), 'storage')
os.makedirs(storage_dir, exist_ok=True)
path = os.path.join(storage_dir, 'futures_baseline.json')

amount = None
if len(sys.argv) > 1:
    try:
        amount = float(sys.argv[1])
    except Exception:
        print("ERROR_INVALID_AMOUNT")
        sys.exit(1)

payload = {
    'amount': amount if amount is not None else 0.0,
    'source': 'manual' if amount is not None else 'manual_zero',
    'time_ms': int(time.time() * 1000)
}

with open(path, 'w', encoding='utf-8') as f:
    json.dump(payload, f)

print(f"BASELINE_SET={payload['amount']}")
