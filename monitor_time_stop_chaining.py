import os
import json
import time
from collections import defaultdict, deque


def main():
    path = os.path.join(os.getcwd(), 'storage', 'trade_events.jsonl')
    if not os.path.exists(path):
        print('NO_EVENT_LOG')
        return
    window_min = int(os.getenv('TIME_STOP_MONITOR_WINDOW_MIN', '240'))  # 4h por defecto
    now = time.time()
    cutoff = now - window_min * 60

    counts = defaultdict(int)
    recent = defaultdict(lambda: deque(maxlen=10))
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if ev.get('type') != 'TIME_STOP':
                continue
            ts = float(ev.get('ts', 0) or 0)
            if ts < cutoff:
                continue
            sym = str(ev.get('symbol'))
            counts[sym] += 1
            recent[sym].append({'ts': ts, 'age_min': ev.get('age_min')})

    any_warn = False
    for sym, cnt in counts.items():
        if cnt >= 3:
            any_warn = True
            series = list(recent[sym])
            series.sort(key=lambda x: x['ts'])
            print(f"WARN_CHAINED_TIME_STOP {sym} count={cnt} in_last_min={window_min}")
            for it in series:
                t_local = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(it['ts']))
                print(f"  - {t_local} age_min={it.get('age_min')}")

    if not any_warn:
        print('NO_CHAINED_TIME_STOP')


if __name__ == '__main__':
    main()
