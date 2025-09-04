"""
Utilidades de símbolos: normalización y alias para datos históricos.

Objetivo: reducir errores por símbolos no soportados o variantes (USD→USDT, BUSD→USDT, USDC→USDT, separadores como '-', '/').
"""
from __future__ import annotations

from typing import List, Tuple


def _strip_separators(symbol: str) -> str:
    s = symbol.replace("-", "").replace("/", "").upper().strip()
    return s


def split_base_quote(symbol: str) -> Tuple[str, str]:
    s = _strip_separators(symbol)
    # Heurística simple asumiendo sufijos comunes
    for q in ("USDT", "BUSD", "USDC", "USD"):
        if s.endswith(q):
            return s[: -len(q)], q
    # Por defecto, intentar separar últimos 4
    return s[:-4], s[-4:]


def normalize_symbol(symbol: str) -> str:
    """Normaliza a formato preferido BASEUSDT cuando sea posible."""
    s = _strip_separators(symbol)
    base, quote = split_base_quote(s)
    if quote in ("USD", "USDC", "BUSD"):
        return f"{base}USDT"
    return s


def suggest_fetch_symbols(symbol: str) -> List[str]:
    """
    Devuelve una lista ordenada de símbolos candidatos para buscar históricos.
    Prioridad: normalizado → original limpio → alias USDT si quote es USD/USDC/BUSD.
    """
    s = _strip_separators(symbol)
    base, quote = split_base_quote(s)
    candidates: List[str] = []
    preferred = normalize_symbol(s)
    if preferred not in candidates:
        candidates.append(preferred)
    if s not in candidates:
        candidates.append(s)
    # Alias USDT si aplica
    if quote in ("USD", "USDC", "BUSD"):
        usdt = f"{base}USDT"
        if usdt not in candidates:
            candidates.append(usdt)
    return candidates
