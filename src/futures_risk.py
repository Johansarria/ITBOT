from futures_symbol_registry import get_info, round_to_tick

def plan(symbol: str, direction: str, entry: float, vol: float,
         support: float | None = None, resistance: float | None = None,
         rr_targets: tuple = (1.0, 1.5, 2.0)):
    info = get_info(symbol)
    tick = info['tick_size']
    entry = round_to_tick(entry, symbol, 'nearest')
    vol = max(0.001, vol)
    if direction.upper() == 'BUY':
        if resistance is None or resistance <= entry:
            resistance = entry * (1 + vol)
        if support is None or support >= entry:
            support = entry * (1 - vol)
        sl = min(support, entry * (1 - vol))
        sl = round_to_tick(sl, symbol, 'down')
        risk = max(1e-6, entry - sl)
        tps = []
        for r in rr_targets:
            tp = round_to_tick(entry + r * risk, symbol, 'up')
            tps.append(tp)
        rr = [(tp - entry) / risk for tp in tps]
    else:
        if support is None or support >= entry:
            support = entry * (1 - vol)
        if resistance is None or resistance <= entry:
            resistance = entry * (1 + vol)
        sl = max(resistance, entry * (1 + vol))
        sl = round_to_tick(sl, symbol, 'up')
        risk = max(1e-6, sl - entry)
        tps = []
        for r in rr_targets:
            tp = round_to_tick(entry - r * risk, symbol, 'down')
            tps.append(tp)
        rr = [(entry - tp) / risk for tp in tps]
    return {
        'entry': float(entry),
        'sl': float(sl),
        'tp1': float(tps[0]),
        'tp2': float(tps[1]),
        'tp3': float(tps[2]),
        'rr_tp1': float(rr[0]),
        'rr_tp2': float(rr[1]),
        'rr_tp3': float(rr[2])
    }

