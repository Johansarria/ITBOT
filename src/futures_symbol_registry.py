SYMBOLS = {
    'NQ': {
        'description': 'E-mini Nasdaq-100 Futures',
        'tick_size': 0.25,
        'tick_value': 5.0,
        'multiplier': 20.0,
        'margin_initial': 17600.0,
        'margin_day': 8000.0
    },
    'MNQ': {
        'description': 'Micro E-mini Nasdaq-100 Futures',
        'tick_size': 0.25,
        'tick_value': 0.5,
        'multiplier': 2.0,
        'margin_initial': 1760.0,
        'margin_day': 800.0
    }
}

def get_info(symbol: str):
    s = symbol.upper()
    if s in SYMBOLS:
        return SYMBOLS[s]
    raise ValueError('Símbolo de futuros no soportado')

def round_to_tick(price: float, symbol: str, mode: str = 'nearest') -> float:
    info = get_info(symbol)
    ts = info['tick_size']
    q = price / ts
    if mode == 'up':
        import math
        return math.ceil(q) * ts
    if mode == 'down':
        import math
        return math.floor(q) * ts
    return round(q) * ts

def estimate_margin(symbol: str, contracts: int = 1, day: bool = False) -> float:
    info = get_info(symbol)
    base = info['margin_day'] if day else info['margin_initial']
    return base * contracts

