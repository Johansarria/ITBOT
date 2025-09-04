"""
Runner de micro‑autonomía para Futuros USDT‑M (mainnet o testnet).

Objetivo:
- Seleccionar candidato usando el selector dinámico de pares (spot data para ranking).
- Aplicar gates operativos de coste y spread (según config.py).
- Validar filtros de Futuros (minNotional/step/tick) y tamaño mínimo factible con apalancamiento.
- Ejecutar 1 micro‑operación de mercado con TP/SL (closePosition) respetando tick/step.

Notas:
- Mantiene aislado el flujo de micro‑prueba; no toca el ejecutor de producción.
- Usa AsyncClient (python‑binance) y cierra conexiones correctamente.
- Lógica de dirección simple: si trend_strength del selector > 0 → BUY, si < 0 → SELL (override por CLI opcional).

Uso (ejemplos):
- python micro_futures_autonomy.py                      # Ejecuta con selección y dirección automática
- python micro_futures_autonomy.py ADAUSDT BUY         # Forzar símbolo y lado
- python micro_futures_autonomy.py DOGEUSDT SELL
"""

from __future__ import annotations

import asyncio
import sys
import math
from typing import Dict, Optional, Tuple, List
import json
import os
import argparse
import time
import socket

import aiohttp

from binance.client import AsyncClient
from binance.exceptions import BinanceAPIException, BinanceRequestException

from config import settings
from dynamic_pair_selector import DynamicPairSelector
from utils.binance_client import close_binance_client
from utils.technical_analysis import analyze_market


# ------------------- Utilidades Futuros -------------------
async def _create_client_with_retry(api_key: str, secret_key: str, testnet: bool, attempts: int = 3, base_delay: float = 5.0) -> AsyncClient:
    """Crea AsyncClient con reintentos exponenciales ante fallos de red/DNS."""
    last_err: Optional[Exception] = None
    for i in range(max(1, attempts)):
        try:
            client = await AsyncClient.create(api_key=api_key, api_secret=secret_key, testnet=testnet)
            return client
        except (aiohttp.ClientConnectorError, aiohttp.ClientOSError, asyncio.TimeoutError, socket.gaierror, BinanceRequestException) as e:
            last_err = e
            delay = base_delay * (2 ** i)
            print(f"[NET] Fallo creando cliente Binance ({type(e).__name__}: {e}). Reintentando en {delay:.1f}s… [{i+1}/{attempts}]")
            await asyncio.sleep(delay)
        except Exception as e:
            last_err = e
            # Para errores no de red, no insistir
            break
    if last_err:
        raise last_err
    # fallback improbable
    raise RuntimeError("No se pudo crear cliente de Binance y no se capturó error")
async def _get_symbol_filters_futures(client: AsyncClient, symbol: str) -> Tuple[float, float, float]:
    """Devuelve (min_notional, step_size, tick_size) para Futuros USDT‑M."""
    info = await client.futures_exchange_info()
    for s in info.get("symbols", []) or []:
        if s.get("symbol") == symbol:
            min_notional = 0.0
            step_size = 0.0
            tick_size = 0.0
            for f in s.get("filters", []) or []:
                ftype = f.get("filterType")
                if ftype in ("NOTIONAL", "MIN_NOTIONAL"):
                    val = f.get("minNotional") or f.get("notional") or 0
                    min_notional = float(val)
                elif ftype in ("LOT_SIZE", "MARKET_LOT_SIZE"):
                    step_size = float(f.get("stepSize") or 0)
                elif ftype == "PRICE_FILTER":
                    tick_size = float(f.get("tickSize") or 0)
            return min_notional, step_size, tick_size
    raise ValueError(f"Símbolo de Futuros no encontrado: {symbol}")


def _round_step(value: float, step: float, up: bool = False) -> float:
    if step <= 0:
        return value
    steps = value / step
    k = math.ceil(steps) if up else math.floor(steps)
    return k * step


def _round_tick(value: float, tick: float, up: bool = False) -> float:
    if tick <= 0:
        return value
    steps = value / tick
    k = math.ceil(steps) if up else math.floor(steps)
    return k * tick

def _tick_decimals(tick: float) -> int:
    if tick <= 0:
        return 8
    s = ("%.12f" % tick).rstrip('0')
    if '.' in s:
        return max(0, len(s.split('.')[1]))
    return 0

def _to_tick_precision(value: float, tick: float) -> float:
    """Redondea value a múltiplo de tick y limita decimales al de tick."""
    v = _round_tick(value, tick, up=False)
    dec = _tick_decimals(tick)
    return float(f"{v:.{dec}f}")


# ------------------- Gates de coste/spread -------------------
async def _spread_info(client: AsyncClient, symbol: str) -> Tuple[float, float, float, float]:
    """(bid, ask, spread_abs, spread_pct). Usa orderbookTicker de Futuros."""
    bt = await client.futures_orderbook_ticker(symbol=symbol)
    bid = float(bt.get("bidPrice", 0) or 0)
    ask = float(bt.get("askPrice", 0) or 0)
    spread_abs = max(ask - bid, 0.0)
    spread_pct = (spread_abs / ask * 100.0) if ask > 0 else 0.0
    return bid, ask, spread_abs, spread_pct

async def _get_funding_rate(client: AsyncClient, symbol: str) -> Optional[float]:
    try:
        fr = await client.futures_funding_rate(symbol=symbol, limit=1)
        if isinstance(fr, list) and fr:
            val = float(fr[0].get('fundingRate', 0) or 0) * 100.0  # a %
            return val
    except Exception:
        return None
    return None


def _cost_model_check(spread_pct: float, taker_fee_per_side_pct: float, tp_gross_pct: float) -> Tuple[bool, float]:
    """Valida ratio ganancia/coste y retorna (ok, ratio)."""
    total_fees_pct = taker_fee_per_side_pct * 2.0
    total_cost_pct = spread_pct + total_fees_pct
    ratio = (tp_gross_pct / total_cost_pct) if total_cost_pct > 0 else float('inf')
    ok = ratio >= float(getattr(settings, 'PROFIT_TO_COST_RATIO', 3.0))
    return ok, ratio


# ------------------- Selección de candidato -------------------
async def _pick_candidate(symbol_cli: Optional[str]) -> List[Tuple[str, Dict]]:
    """Devuelve lista ordenada [(symbol, metrics), ...] de candidatos tras selección dinámica.
    Si symbol_cli está definido, se prioriza al inicio (siempre que esté permitido).
    """
    selector = DynamicPairSelector()
    metrics_map: Dict[str, Dict] = {}

    # 1) Cargar métricas dinámicas
    # Cache simple en memoria para evitar análisis costoso en cada ciclo
    global _SELECTION_CACHE
    now = time.time()
    ts = _SELECTION_CACHE.get('ts')
    reevaluate_after = float(getattr(settings, 'DYNAMIC_REEVALUATION_INTERVAL_SECONDS', 1800))
    if isinstance(ts, (int, float)) and (now - float(ts)) < reevaluate_after:
        metrics_map = _SELECTION_CACHE.get('metrics') or {}
    else:
        try:
            metrics_map = await selector.evaluate_all_pairs(max_concurrent=10)
        except Exception:
            metrics_map = {}
        _SELECTION_CACHE = {'ts': now, 'metrics': metrics_map}

    # 2) Base de candidatos por score, intersectando con permitidos en micro‑trade
    allowed = set(settings.MICRO_TRADE_ALLOWED_SYMBOLS or [])

    def default_rank_pairs() -> List[Tuple[str, Dict]]:
        if not metrics_map:
            # Fallback si no hay métricas
            fallbacks = [s for s in ["XRPUSDT", "ADAUSDT", "DOGEUSDT", "SOLUSDT", "BNBUSDT"] if s in allowed]
            return [(s, {"composite_score": 0, "trend_strength": 0, "price_change_24h_pct": 0}) for s in fallbacks]
        # Ordenar por score
        items = [(s, m) for s, m in metrics_map.items() if s in allowed]
        return sorted(items, key=lambda kv: kv[1].get("composite_score", 0), reverse=True)

    ranked = default_rank_pairs()

    # Si se fuerza símbolo por CLI, colócalo al frente (si está permitido); si no está, añádelo para validarlo igual
    if symbol_cli:
        symbol_cli = symbol_cli.upper()
        if settings.MICRO_TRADE_ALLOWED_SYMBOLS and symbol_cli not in allowed:
            raise SystemExit(f"[ABORT] {symbol_cli} no está en MICRO_TRADE_ALLOWED_SYMBOLS: {sorted(allowed)}")
        m = metrics_map.get(symbol_cli, {"composite_score": 0, "trend_strength": 0, "price_change_24h_pct": 0})
        ranked = [(symbol_cli, m)] + [x for x in ranked if x[0] != symbol_cli]

    if not ranked:
        raise SystemExit("[ABORT] No hay candidatos disponibles tras la selección dinámica y filtros.")
    return ranked

_LAST_EXIT_TS: Dict[str, float] = {}
_LAST_ENTRY_TS: Dict[str, float] = {}

def _cooldown_ok(symbol: str) -> bool:
    cd_min = int(getattr(settings, 'REENTRY_COOLDOWN_MINUTES', 30))
    ts = _LAST_EXIT_TS.get(symbol, 0)
    if ts <= 0:
        return True
    return (time.time() - ts) >= cd_min * 60

def _log_event(event: Dict) -> None:
    path = getattr(settings, 'EVENT_LOG_PATH', None)
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ------------------- Flujo principal -------------------
async def main_async(symbol_cli: Optional[str], side_cli: Optional[str]) -> int:
    """Ejecuta un ciclo único de decisión/ejecución."""
    if not settings.ENABLE_MICRO_TRADE:
        print("[ABORT] ENABLE_MICRO_TRADE=False en config. Actívalo para usar este runner.")
        return 2
    if not settings.MICRO_TRADE_USE_FUTURES:
        print("[ABORT] MICRO_TRADE_USE_FUTURES=False. Este runner opera solo en Futuros USDT‑M.")
        return 2

    ranked = await _pick_candidate(symbol_cli)

    # Crear cliente Futures (usa flag de testnet de Futuros)
    api_key = getattr(settings, 'BINANCE_API_KEY', '') or ''
    secret_key = getattr(settings, 'BINANCE_SECRET_KEY', '') or ''
    use_testnet = bool(getattr(settings, 'BINANCE_USE_TESTNET_FUTURES', False))
    client = await _create_client_with_retry(api_key=api_key, secret_key=secret_key, testnet=use_testnet)

    try:
        # Apalancamiento / parámetros
        leverage = int(settings.MICRO_TRADE_LEVERAGE)
        max_usdt = float(settings.MICRO_TRADE_MAX_USDT)
        max_concurrent = int(getattr(settings, 'RISK_MAX_CONCURRENT_TRADES', 1))
        # Detectar símbolos ya abiertos para permitir entradas paralelas en otros pares
        try:
            positions = await client.futures_position_information()
            open_symbols = {p.get('symbol') for p in positions if abs(float(p.get('positionAmt', 0) or 0)) > 0}
        except Exception:
            open_symbols = set()
        try:
            # Se ajusta al primer símbolo luego de decidirlo (se hará más abajo por símbolo)
            pass
        except Exception as e:
            print(f"[WARN] No se pudo cambiar apalancamiento: {e}")
        # Intentar candidatos en orden hasta que uno cumpla todos los filtros/gates
        for symbol, metrics in ranked:
            # Si ya estamos en el símbolo, sáltalo para no duplicar posición en el mismo par
            if symbol in open_symbols:
                print(f"[SKIP] {symbol} ya tiene posición abierta. Buscando paralela en otro par…")
                continue

            # Respetar límite máximo de posiciones abiertas en paralelo
            if len(open_symbols) >= max_concurrent:
                print(f"[ABORT] Máximo de posiciones concurrentes alcanzado ({len(open_symbols)}/{max_concurrent}).")
                return 2
            # Spread y precio
            bid, ask, spread_abs, spread_pct = await _spread_info(client, symbol)
            if ask <= 0 or bid <= 0:
                ticker = await client.futures_symbol_ticker(symbol=symbol)
                px = float(ticker.get("price", 0) or 0)
            else:
                px = (bid + ask) / 2.0

            # Gate de spread absoluto en %
            if spread_pct > float(getattr(settings, 'MAX_SPREAD_PERCENTAGE', 0.07)):
                print(f"[SKIP] {symbol} spread {spread_pct:.4f}% > max {getattr(settings, 'MAX_SPREAD_PERCENTAGE', 0.07)}%")
                continue

            # Funding filter
            max_abs_funding = float(getattr(settings, 'FUTURES_MAX_ABS_FUNDING_PCT', 0.05))
            fr = await _get_funding_rate(client, symbol)
            if fr is not None and abs(fr) > max_abs_funding:
                print(f"[SKIP] {symbol} funding {fr:.4f}% > max {max_abs_funding}%")
                continue

            # Filtros Futuros
            min_notional, step_size, tick_size = await _get_symbol_filters_futures(client, symbol)
            max_notional_by_margin = max_usdt * leverage
            if min_notional > max_notional_by_margin:
                print(f"[SKIP] {symbol} minNotional({min_notional}) > margen({max_notional_by_margin})")
                continue

            # Cantidad mínima que cumple minNotional, ajustada por step
            qty_min = min_notional / max(px, 1e-12)
            qty_min = _round_step(qty_min, step_size, up=True)
            qty_max = _round_step(max_notional_by_margin / max(px, 1e-12), step_size, up=False)
            if qty_min <= 0 or qty_max <= 0 or qty_min > qty_max:
                print(f"[SKIP] {symbol} qty_min={qty_min} qty_max={qty_max} incompatibles")
                continue
            qty = qty_min

            # Modelo de costes vs TP esperado
            taker_fee_per_side = float(getattr(settings, 'FUTURES_TAKER_FEE_PCT', 0.04))  # %
            tp_target_pct = float(getattr(settings, 'RISK_PER_TRADE_TAKE_PROFIT_PCT', 4.0))
            ok_ratio, ratio = _cost_model_check(spread_pct, taker_fee_per_side, tp_target_pct)
            if not ok_ratio:
                print(f"[SKIP] {symbol} Profit/Cost {ratio:.2f}x < mínimo {getattr(settings, 'PROFIT_TO_COST_RATIO', 3.0)}x")
                continue

            # Gate técnico: ADX (confluencia básica)
            if bool(getattr(settings, 'ML_REQUIRE_TECH_CONFLUENCE', True)):
                adx_min = float(getattr(settings, 'ML_CONFLUENCE_ADX_MIN', 20.0))
                adx_val = await _compute_adx(client, symbol, interval='5m', length=14, limit=100)
                if adx_val is None:
                    print(f"[SKIP] {symbol} ADX no disponible")
                    continue
                if adx_val < adx_min:
                    print(f"[SKIP] {symbol} ADX {adx_val:.2f} < min {adx_min}")
                    continue

            # Gate ML opcional y dirección: CLI > ML > tendencia
            ml_decision = None
            ml_score = 0.0
            if bool(getattr(settings, 'AUTONOMY_USE_ML', True)):
                try:
                    ml_interval = str(getattr(settings, 'ML_AUTONOMY_INTERVAL', '5m'))
                    ml_limit = int(getattr(settings, 'ML_AUTONOMY_LIMIT', 300))
                    ml = await analyze_market(symbol=symbol, interval=ml_interval, limit=ml_limit, export=False)
                    ml_decision = ml.get('decision')
                    ml_score = float(ml.get('score', 0) or 0)
                    print(f"[ML] {symbol} decision={ml_decision} score={ml_score:.1f} buy={ml.get('ml_buy_probability')} sell={ml.get('ml_sell_probability')}")
                    # Filtrar por score mínimo
                    min_score = float(getattr(settings, 'ML_MIN_SCORE_FOR_ENTRY', 60.0))
                    if ml_decision in ("COMPRAR","VENDER") and ml_score < min_score:
                        print(f"[SKIP] {symbol} ML score {ml_score:.1f} < min {min_score}")
                        continue
                    if ml_decision in ("COMPRAR_BAJO","VENDER_ALTO") and not bool(getattr(settings,'ML_ENABLE_MODERATE_SIGNALS',False)):
                        print(f"[SKIP] {symbol} ML moderada {ml_decision} no permitida")
                        continue
                except Exception as e:
                    print(f"[WARN] ML gate falló para {symbol}: {e}")

            if side_cli:
                side = side_cli.upper()
                if side not in ("BUY", "SELL"):
                    print("[ABORT] Side inválido. Usa BUY o SELL.")
                    return 2
            else:
                if bool(getattr(settings, 'ML_SIDE_OVERRIDE', True)) and ml_decision in ("COMPRAR","COMPRAR_BAJO","VENDER","VENDER_ALTO"):
                    side = "BUY" if ml_decision.startswith("COMPRAR") else "SELL"
                else:
                    trend_strength = float(metrics.get("trend_strength", 0) or 0)
                    side = "BUY" if trend_strength >= 0 else "SELL"

            # Ajustar apalancamiento ahora que tenemos símbolo final
            try:
                await client.futures_change_leverage(symbol=symbol, leverage=leverage)
            except Exception as e:
                print(f"[WARN] No se pudo cambiar apalancamiento en {symbol}: {e}")

            # Bloqueo diario por símbolo (p.ej., pausar XRPUSDT hoy)
            try:
                bl = (getattr(settings, 'DAILY_BLOCKLIST', '') or '').strip()
                if bl:
                    blocked = {s.strip().upper() for s in bl.split(',') if s.strip()}
                    if symbol.upper() in blocked:
                        print(f"[SKIP] {symbol} está en DAILY_BLOCKLIST. Se omite hoy.")
                        continue
            except Exception:
                pass

            # Info y ROI sobre margen
            notional = px * qty
            margin_used = notional / max(leverage, 1)
            total_fees_pct = taker_fee_per_side * 2.0
            net_tp_pct = tp_target_pct - total_fees_pct - spread_pct
            net_tp_usdt = notional * (net_tp_pct / 100.0)
            roi_tp_pct_on_margin = (net_tp_usdt / margin_used * 100.0) if margin_used > 0 else 0.0
            print(f"[CANDIDATE] {symbol} px={px:.8f} score={metrics.get('composite_score', 0):.1f} trend={metrics.get('trend_strength', 0):.4f}")
            print(f"[FILTERS] minNotional={min_notional} step={step_size} tick={tick_size} qty={qty}")
            print(f"[COST] spread={spread_pct:.4f}% taker(round‑trip)≈{total_fees_pct:.4f}% → Profit/Cost={ratio:.2f}x")
            print(f"[ROI] TP Neto≈{net_tp_pct:.4f}% ({net_tp_usdt:.4f} USDT) sobre margen≈{margin_used:.4f} → {roi_tp_pct_on_margin:.2f}%")

            # Circuit breaker diario: no abrir si superamos pérdida diaria
            try:
                # Cargar baseline dinámico y equity actual para calcular pérdida de hoy vs baseline inicial del día
                # Usamos un archivo simple de estado diario en storage
                storage_dir = os.path.join(os.getcwd(), 'storage')
                os.makedirs(storage_dir, exist_ok=True)
                day_state_path = os.path.join(storage_dir, 'daily_state.json')
                from datetime import datetime, timezone
                # Obtener equity actual de la cuenta de futuros
                try:
                    acc_cb = await client.futures_account()
                    total_equity = float(acc_cb.get('totalMarginBalance', 0) or 0)
                except Exception as _e_acc:
                    print(f"[WARN] No se pudo leer equity para circuit breaker: {_e_acc}")
                    total_equity = 0.0
                today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                day_state = {}
                if os.path.exists(day_state_path):
                    try:
                        import json as _json
                        day_state = _json.load(open(day_state_path, 'r', encoding='utf-8'))
                    except Exception:
                        day_state = {}
                if day_state.get('date') != today:
                    # Inicializar nuevo día con equity actual como baseline diario
                    day_state = {'date': today, 'equity_open': total_equity}
                    try:
                        import json as _json
                        _json.dump(day_state, open(day_state_path, 'w', encoding='utf-8'))
                    except Exception:
                        pass
                daily_open = float(day_state.get('equity_open', total_equity) or total_equity)
                daily_loss = daily_open - total_equity
                d_pct = float(getattr(settings, 'DAILY_MAX_LOSS_PCT', 0.0))
                d_abs = float(getattr(settings, 'DAILY_MAX_LOSS_USDT', 0.0))
                limit_abs = 0.0
                if d_pct and d_pct > 0:
                    limit_abs = max(limit_abs, daily_open * (d_pct / 100.0))
                if d_abs and d_abs > 0:
                    limit_abs = max(limit_abs, d_abs)
                if limit_abs > 0 and daily_loss >= limit_abs:
                    print(f"[CIRCUIT] Pérdida diaria {daily_loss:.4f} >= límite {limit_abs:.4f}. No se abrirán nuevas entradas hoy.")
                    continue
                # Profit lock: si ganancia diaria supera umbral, pausar nuevas entradas
                daily_profit = total_equity - daily_open
                lock_abs = 0.0
                pl_pct = float(getattr(settings, 'DAILY_PROFIT_LOCK_PCT', 0.0))
                pl_abs = float(getattr(settings, 'DAILY_PROFIT_LOCK_USDT', 0.0))
                if pl_pct and pl_pct > 0:
                    lock_abs = max(lock_abs, daily_open * (pl_pct / 100.0))
                if pl_abs and pl_abs > 0:
                    lock_abs = max(lock_abs, pl_abs)
                if lock_abs > 0 and daily_profit >= lock_abs:
                    print(f"[LOCK] Ganancia diaria {daily_profit:.4f} >= objetivo {lock_abs:.4f}. Pausando nuevas entradas (solo gestión).")
                    continue
            except Exception as _e:
                print(f"[WARN] Circuit breaker diario no disponible: {_e}")

            # Frecuencia de entradas: 1 por hora por símbolo, salvo oportunidad excepcional
            last_ent = _LAST_ENTRY_TS.get(symbol, 0)
            since_last_min = (time.time() - last_ent) / 60.0 if last_ent else None
            exceptional = False
            # Evaluar excepcional más adelante tras calcular ADX/ROI

            # Gate: ROI mínimo sobre margen (e.g., ≥ 13%)
            min_roi_margin = float(getattr(settings, 'MIN_ROI_ON_MARGIN_FOR_ENTRY_PCT', 13.0))
            if roi_tp_pct_on_margin < min_roi_margin:
                print(f"[SKIP] {symbol} ROI sobre margen {roi_tp_pct_on_margin:.2f}% < mínimo {min_roi_margin:.2f}%")
                continue

            # Oportunidad excepcional: ROI>=22% y ADX>=30
            try:
                exceptional = (roi_tp_pct_on_margin >= 22.0) and (adx_val is not None and adx_val >= 30.0)
            except Exception:
                exceptional = False

            if since_last_min is not None and since_last_min < 60.0 and not exceptional:
                print(f"[SKIP] {symbol} cooldown de entrada ({since_last_min:.1f}m < 60m) y no es oportunidad excepcional")
                continue

            # Ejecutar orden: maker-limit opcional cuando spread muy bajo
            order = None
            enable_maker = bool(getattr(settings, 'ENABLE_MAKER_ENTRY', True))
            maker_spread_max = float(getattr(settings, 'LIMIT_MAKER_SPREAD_MAX_PCT', 0.02))
            # Offset maker por símbolo (BTC/ETH=2, SOL=1; fallback a config)
            default_offset = int(getattr(settings, 'LIMIT_MAKER_OFFSET_TICKS', 2))
            maker_offset_ticks = 2 if symbol in ("BTCUSDT","ETHUSDT") else (1 if symbol=="SOLUSDT" else default_offset)
            maker_max_retries = int(getattr(settings, 'LIMIT_MAKER_MAX_RETRIES', 2))
            maker_retry_delay_ms = int(getattr(settings, 'LIMIT_MAKER_RETRY_DELAY_MS', 150))
            if enable_maker and spread_pct <= maker_spread_max:
                # Precio base hacia el lado pasivo y aplicar offset de ticks para aumentar aceptación
                base_price = _round_tick(px, tick_size, up=(side=="BUY"))
                base_price = _to_tick_precision(base_price, tick_size)
                # Calcular precio con offset: en BUY bajar, en SELL subir
                def _shift(p: float, ticks: int) -> float:
                    return _to_tick_precision(p - ticks * tick_size if side=="BUY" else p + ticks * tick_size, tick_size)
                attempts = 0
                last_err = None
                while attempts <= maker_max_retries:
                    price = _shift(base_price, maker_offset_ticks if attempts > 0 else 0)
                    print(f"[INFO] Enviando LIMIT_MAKER {side} {symbol} qty={qty} px={price} (try {attempts+1}/{maker_max_retries+1}, testnet={use_testnet})")
                    try:
                        order = await client.futures_create_order(
                            symbol=symbol,
                            side=side,
                            type="LIMIT",
                            timeInForce='GTX',
                            quantity=qty,
                            price=price
                        )
                        last_err = None
                        break
                    except Exception as e:
                        last_err = e
                        attempts += 1
                        if attempts <= maker_max_retries:
                            await asyncio.sleep(maker_retry_delay_ms / 1000.0)
                if order is None and last_err is not None:
                    print(f"[WARN] LIMIT_MAKER falló ({attempts} intentos): {last_err}. Enviando MARKET…")
            if order is None:
                print(f"[INFO] Enviando MARKET {side} {symbol} qty={qty} (testnet={use_testnet})")
                order = await client.futures_create_order(symbol=symbol, side=side, type="MARKET", quantity=qty)
            print(f"[OK] Entrada ejecutada. orderId={order.get('orderId')}")
            _LAST_ENTRY_TS[symbol] = time.time()
            _log_event({"type":"ENTRY","symbol":symbol,"side":side,"qty":qty,"px":px,"ts":time.time()})

            # Calcular SL/TP por lado y redondear a tick
            sl_pct = float(getattr(settings, 'RISK_PER_TRADE_STOP_LOSS_PCT', 2.0))
            tp_pct = tp_target_pct
            if side == "BUY":
                sl_price = _round_tick(px * (1 - sl_pct / 100), tick_size, up=False)
                tp_price = _round_tick(px * (1 + tp_pct / 100), tick_size, up=True)
                close_side = "SELL"
            else:
                sl_price = _round_tick(px * (1 + sl_pct / 100), tick_size, up=True)
                tp_price = _round_tick(px * (1 - tp_pct / 100), tick_size, up=False)
                close_side = "BUY"

            # Ajuste final de precisión a tick
            sl_price = _to_tick_precision(sl_price, tick_size)
            tp_price = _to_tick_precision(tp_price, tick_size)

            try:
                sl_working = getattr(settings, 'FUTURES_SL_WORKING_TYPE', 'CONTRACT_PRICE')
                tp_working = getattr(settings, 'FUTURES_TP_WORKING_TYPE', 'CONTRACT_PRICE')
                await client.futures_create_order(
                    symbol=symbol,
                    side=close_side,
                    type="STOP_MARKET",
                    stopPrice=sl_price,
                    closePosition=True,
                    workingType=sl_working,
                )
                await client.futures_create_order(
                    symbol=symbol,
                    side=close_side,
                    type="TAKE_PROFIT_MARKET",
                    stopPrice=tp_price,
                    closePosition=True,
                    workingType=tp_working,
                )
                print(f"[OK] TP/SL colocados. SL@{sl_price:.8f}, TP@{tp_price:.8f}")
                _log_event({"type":"BRACKETS","symbol":symbol,"sl":sl_price,"tp":tp_price,"sl_work":sl_working,"tp_work":tp_working,"ts":time.time()})
            except Exception as e:
                print(f"[WARN] No se pudieron colocar TP/SL reduce‑only: {e}")

            return 0

        # Si ninguno pasó filtros
        print("[ABORT] Ningún candidato cumplió minNotional/spread/ratio con los parámetros actuales.")
        return 2

    except (BinanceAPIException, BinanceRequestException) as e:
        print(f"[ERROR] Binance API: {e}")
        return 1
    except SystemExit as se:
        print(str(se))
        return 2
    except Exception as e:
        print(f"[ERROR] Excepción inesperada: {e}")
        return 1
    finally:
        try:
            await client.close_connection()
        except Exception:
            pass
        # Cerrar el cliente global usado por el selector para evitar sesiones sin cerrar
        try:
            await close_binance_client()
        except Exception:
            pass


# ------------------- ADX y utilidades de gestión -------------------
async def _fetch_klines(client: AsyncClient, symbol: str, interval: str, limit: int = 100):
    try:
        k = await client.futures_klines(symbol=symbol, interval=interval, limit=limit)
        return k
    except Exception:
        return []


def _compute_adx_from_klines(klines: List[List], length: int = 14) -> Optional[float]:
    import pandas as pd
    if not klines or len(klines) < length + 2:
        return None
    df = pd.DataFrame(klines, columns=[
        'open_time','open','high','low','close','volume','close_time','qav','trades','tbbav','tbqav','ignore'
    ])
    high = pd.to_numeric(df['high'], errors='coerce')
    low = pd.to_numeric(df['low'], errors='coerce')
    close = pd.to_numeric(df['close'], errors='coerce')
    pd.options.mode.chained_assignment = None
    up = high.diff().astype(float)
    down = (-low.diff()).astype(float)
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    tr1 = (high - low)
    tr2 = (high - close.shift())
    tr3 = (close.shift() - low)
    tr = pd.concat([tr1, tr2.abs(), tr3.abs()], axis=1).max(axis=1)
    atr = tr.rolling(window=length).mean()
    plus_di = 100 * (plus_dm.rolling(window=length).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=length).mean() / atr)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)).replace([float('inf'), -float('inf')], 0) * 100
    adx = dx.rolling(window=length).mean()
    val = adx.iloc[-1]
    return float(val) if pd.notna(val) else None


async def _compute_adx(client: AsyncClient, symbol: str, interval: str = '5m', length: int = 14, limit: int = 100) -> Optional[float]:
    kl = await _fetch_klines(client, symbol, interval=interval, limit=limit)
    if not isinstance(kl, list):
        return None
    return _compute_adx_from_klines(kl, length=length)


_OPEN_START_TS: Dict[str, float] = {}
from typing import Any
_SELECTION_CACHE: Dict[str, Any] = {'ts': 0.0, 'metrics': {}}


def _load_entry_ts_from_log(symbol: str) -> Optional[float]:
    """Intenta cargar el ts de la última entrada (ENTRY) para el símbolo desde el EVENT_LOG_PATH.
    Retorna None si no hay log o evento.
    """
    path = getattr(settings, 'EVENT_LOG_PATH', None)
    if not path or not os.path.exists(path):
        return None
    try:
        last_ts = None
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    ev = json.loads(line.strip())
                except Exception:
                    continue
                if not isinstance(ev, dict):
                    continue
                if ev.get('type') == 'ENTRY' and ev.get('symbol') == symbol:
                    last_ts = float(ev.get('ts', 0) or 0)
        return last_ts if last_ts and last_ts > 0 else None
    except Exception:
        return None


async def _manage_open_position(client: AsyncClient, symbol: str) -> None:
    """Trailing/time-stop simple para posición abierta en symbol."""
    # Params con defaults
    trail_activate = float(getattr(settings, 'TRAIL_ACTIVATE_PCT', 1.0))  # %
    trail_distance = float(getattr(settings, 'TRAIL_DISTANCE_PCT', 0.6))  # %
    time_stop_min = int(getattr(settings, 'TIME_STOP_MINUTES', 180))
    be_activate = float(getattr(settings, 'BREAK_EVEN_ACTIVATE_PCT', 0.5))  # % de ganancia para activar break-even
    be_offset_ticks = float(getattr(settings, 'BREAK_EVEN_OFFSET_TICKS', 1.0))  # ticks de margen sobre entry
    tp_pct = float(getattr(settings, 'RISK_PER_TRADE_TAKE_PROFIT_PCT', 4.0))
    sl_pct = float(getattr(settings, 'RISK_PER_TRADE_STOP_LOSS_PCT', 2.0))

    # Info posición
    pos = await client.futures_position_information(symbol=symbol)
    p = pos[0] if isinstance(pos, list) and pos else None
    if not p:
        return
    amt = float(p.get('positionAmt', 0) or 0)
    if abs(amt) == 0:
        # Si no hay posición, limpiar timestamp de apertura previo para evitar edades infladas
        try:
            _OPEN_START_TS.pop(symbol, None)
        except Exception:
            pass
        return
    entry = float(p.get('entryPrice', 0) or 0)
    side = 'LONG' if amt > 0 else 'SHORT'

    # Precios y filtros
    ticker = await client.futures_symbol_ticker(symbol=symbol)
    px = float(ticker.get('price', 0) or 0)
    ex = await client.futures_exchange_info()
    step = tick = 0.0
    for s in ex.get('symbols', []) or []:
        if s.get('symbol') == symbol:
            for f in s.get('filters', []) or []:
                if f.get('filterType') in ('LOT_SIZE','MARKET_LOT_SIZE'):
                    step = float(f.get('stepSize', 0) or 0)
                elif f.get('filterType') == 'PRICE_FILTER':
                    tick = float(f.get('tickSize', 0) or 0)
            break
    qty = _round_step(abs(amt), step, up=False)
    if qty <= 0:
        return

    # Inicializar tiempo de apertura si no existe
    if symbol not in _OPEN_START_TS:
        persisted = _load_entry_ts_from_log(symbol)
        _OPEN_START_TS[symbol] = persisted if persisted else time.time()

    # Time‑stop
    age_min = (time.time() - _OPEN_START_TS.get(symbol, time.time())) / 60.0
    if age_min >= time_stop_min:
        try:
            await client.futures_cancel_all_open_orders(symbol=symbol)
        except Exception:
            pass
        try:
            await client.futures_create_order(symbol=symbol, side=('SELL' if side=='LONG' else 'BUY'), type='MARKET', reduceOnly=True, quantity=qty)
            print(f"[MANAGER] Time‑stop ejecutado en {symbol} (edad {age_min:.1f}m)")
            _LAST_EXIT_TS[symbol] = time.time()
            _log_event({"type":"TIME_STOP","symbol":symbol,"age_min":age_min,"ts":time.time()})
            # Reiniciar el timestamp de apertura tras cierre por tiempo
            try:
                _OPEN_START_TS.pop(symbol, None)
            except Exception:
                pass
        except Exception as e:
            print(f"[MANAGER] Error en time‑stop {symbol}: {e}")
        return

    # Calcular ganancia actual
    gain_pct = (px - entry) / entry * 100.0 if side=='LONG' else (entry - px) / entry * 100.0

    # Candidatos de SL/TP a aplicar
    be_sl = None
    trail_sl = None
    new_tp = None

    # Break-even si supera umbral
    if gain_pct >= be_activate and be_offset_ticks > 0 and tick > 0:
        if side == 'LONG':
            be_target = entry + be_offset_ticks * tick
            be_sl = _round_tick(be_target, tick, up=False)
        else:
            be_target = entry - be_offset_ticks * tick
            be_sl = _round_tick(be_target, tick, up=True)
        be_sl = _to_tick_precision(be_sl, tick)

    # Trailing si en ganancia
    if gain_pct >= trail_activate:
        if side == 'LONG':
            trail_sl = max(entry, px * (1 - trail_distance/100.0))
            new_tp = entry * (1 + tp_pct/100.0)
        else:
            trail_sl = min(entry, px * (1 + trail_distance/100.0))
            new_tp = entry * (1 - tp_pct/100.0)
        trail_sl = _round_tick(trail_sl, tick, up=(side=='SHORT'))
        new_tp = _round_tick(new_tp, tick, up=(side=='LONG'))
        trail_sl = _to_tick_precision(trail_sl, tick)
        new_tp = _to_tick_precision(new_tp, tick)

    # Elegir SL más protector entre BE y trailing
    new_sl = None
    if be_sl is not None and trail_sl is not None:
        new_sl = max(be_sl, trail_sl) if side=='LONG' else min(be_sl, trail_sl)
    elif be_sl is not None:
        new_sl = be_sl
    elif trail_sl is not None:
        new_sl = trail_sl

    # Aplicar si hay cambio
    if new_sl is not None:
        close_side = 'SELL' if side=='LONG' else 'BUY'
        try:
            await client.futures_cancel_all_open_orders(symbol=symbol)
        except Exception:
            pass
        try:
            sl_working = getattr(settings, 'FUTURES_SL_WORKING_TYPE', 'CONTRACT_PRICE')
            tp_working = getattr(settings, 'FUTURES_TP_WORKING_TYPE', 'CONTRACT_PRICE')
            await client.futures_create_order(symbol=symbol, side=close_side, type='STOP_MARKET', stopPrice=new_sl, closePosition=True, workingType=sl_working)
            if new_tp is None:
                # si no había trailing, mantener un TP relativo al entry
                if side == 'LONG':
                    new_tp_calc = _round_tick(entry * (1 + tp_pct/100.0), tick, up=True)
                else:
                    new_tp_calc = _round_tick(entry * (1 - tp_pct/100.0), tick, up=False)
                new_tp = _to_tick_precision(new_tp_calc, tick)
            await client.futures_create_order(symbol=symbol, side=close_side, type='TAKE_PROFIT_MARKET', stopPrice=new_tp, closePosition=True, workingType=tp_working)
            label = "BREAKEVEN" if be_sl is not None and (trail_sl is None or (side=='LONG' and be_sl>=trail_sl) or (side=='SHORT' and be_sl<=trail_sl)) else "TRAIL"
            print(f"[MANAGER] {label} SL actualizado {symbol}: SL@{new_sl:.8f} TP@{new_tp:.8f} (gain {gain_pct:.2f}%)")
            _log_event({"type":label,"symbol":symbol,"new_sl":new_sl,"new_tp":new_tp,"gain_pct":gain_pct,"ts":time.time()})
        except Exception as e:
            print(f"[MANAGER] Error actualizando SL/TP {symbol}: {e}")


async def has_open_position(client: AsyncClient, symbols_allowlist: List[str]) -> Optional[str]:
    """Devuelve el símbolo de una posición abierta (no cero) dentro del allowlist, o None."""
    try:
        positions = await client.futures_position_information()
        for p in positions:
            sym = p.get('symbol')
            if symbols_allowlist and sym not in symbols_allowlist:
                continue
            amt = float(p.get('positionAmt', 0) or 0)
            if abs(amt) > 0:
                return sym
    except Exception:
        return None
    return None


async def run_loop(interval_seconds: int, symbol_cli: Optional[str], side_cli: Optional[str]) -> int:
    """Modo autónomo: itera continuamente, permitiendo entradas paralelas hasta RISK_MAX_CONCURRENT_TRADES."""
    print(f"[LOOP] Iniciando modo autónomo. Intervalo={interval_seconds}s")
    while True:
        try:
            # Estado actual de posiciones abiertas
            api_key = getattr(settings, 'BINANCE_API_KEY', '') or ''
            secret_key = getattr(settings, 'BINANCE_SECRET_KEY', '') or ''
            use_testnet = bool(getattr(settings, 'BINANCE_USE_TESTNET_FUTURES', False))
            open_syms: List[str] = []  # asegura definición incluso si hay excepciones dentro del try
            # Crear cliente con reintentos; si falla, dormir y continuar siguiente ciclo
            try:
                client = await _create_client_with_retry(api_key=api_key, secret_key=secret_key, testnet=use_testnet)
            except (aiohttp.ClientConnectorError, aiohttp.ClientOSError, asyncio.TimeoutError, socket.gaierror, BinanceRequestException) as e:
                print(f"[LOOP][NET] No se pudo inicializar cliente por error de red: {e}. Esperando {interval_seconds}s…")
                await asyncio.sleep(interval_seconds)
                continue
            try:
                positions = await client.futures_position_information()
                allow = set(settings.MICRO_TRADE_ALLOWED_SYMBOLS or [])
                # Gestionar TODAS las posiciones abiertas, aunque no estén en allowlist (p.ej., relictos de un cambio de config)
                open_syms_all = [p.get('symbol') for p in positions if abs(float(p.get('positionAmt', 0) or 0))>0]
                open_syms = open_syms_all  # para gestión y ocupación del slot
                # Circuit breaker diario: si el límite se excede, cerrar todas las posiciones
                try:
                    from datetime import datetime, timezone
                    acc_cb = await client.futures_account()
                    current_equity = float(acc_cb.get('totalMarginBalance', 0) or 0)
                    storage_dir = os.path.join(os.getcwd(), 'storage')
                    os.makedirs(storage_dir, exist_ok=True)
                    day_state_path = os.path.join(storage_dir, 'daily_state.json')
                    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                    day_state = {}
                    if os.path.exists(day_state_path):
                        try:
                            import json as _json
                            day_state = _json.load(open(day_state_path, 'r', encoding='utf-8'))
                        except Exception:
                            day_state = {}
                    if day_state.get('date') != today:
                        day_state = {'date': today, 'equity_open': current_equity}
                        try:
                            import json as _json
                            _json.dump(day_state, open(day_state_path, 'w', encoding='utf-8'))
                        except Exception:
                            pass
                    daily_open = float(day_state.get('equity_open', current_equity) or current_equity)
                    daily_loss = daily_open - current_equity
                    d_pct = float(getattr(settings, 'DAILY_MAX_LOSS_PCT', 0.0))
                    d_abs = float(getattr(settings, 'DAILY_MAX_LOSS_USDT', 0.0))
                    limit_abs = 0.0
                    if d_pct and d_pct > 0:
                        limit_abs = max(limit_abs, daily_open * (d_pct / 100.0))
                    if d_abs and d_abs > 0:
                        limit_abs = max(limit_abs, d_abs)
                    if limit_abs > 0 and daily_loss >= limit_abs and open_syms:
                        print(f"[CIRCUIT] Límite diario alcanzado ({daily_loss:.4f} >= {limit_abs:.4f}). Cerrando posiciones: {open_syms}")
                        try:
                            for osym in open_syms:
                                try:
                                    await client.futures_cancel_all_open_orders(symbol=osym)
                                except Exception:
                                    pass
                                try:
                                    # cerrar reduceOnly por el tamaño actual
                                    pinfo = [p for p in positions if p.get('symbol') == osym]
                                    if pinfo:
                                        amt = float(pinfo[0].get('positionAmt', 0) or 0)
                                        if abs(amt) > 0:
                                            side_close = 'SELL' if amt > 0 else 'BUY'
                                            qty_close = abs(amt)
                                            await client.futures_create_order(symbol=osym, side=side_close, type='MARKET', reduceOnly=True, quantity=qty_close)
                                except Exception:
                                    pass
                            print("[CIRCUIT] Todas las posiciones cerradas por límite diario.")
                        except Exception as _eclose:
                            print(f"[CIRCUIT] Error cerrando posiciones: {_eclose}")
                        # Evitar nuevas entradas en este ciclo
                        await asyncio.sleep(interval_seconds)
                        continue
                    # Profit lock diario: si ganancia >= objetivo, no abrir nuevas entradas (mantener gestión)
                    daily_profit = current_equity - daily_open
                    lock_abs = 0.0
                    pl_pct = float(getattr(settings, 'DAILY_PROFIT_LOCK_PCT', 0.0))
                    pl_abs = float(getattr(settings, 'DAILY_PROFIT_LOCK_USDT', 0.0))
                    if pl_pct and pl_pct > 0:
                        lock_abs = max(lock_abs, daily_open * (pl_pct / 100.0))
                    if pl_abs and pl_abs > 0:
                        lock_abs = max(lock_abs, pl_abs)
                    if lock_abs > 0 and daily_profit >= lock_abs:
                        print(f"[LOCK] Objetivo diario alcanzado ({daily_profit:.4f} >= {lock_abs:.4f}). Bloqueando nuevas entradas por hoy.")
                        # Si hay posiciones, solo gestionar; si no, dormir
                        if open_syms:
                            # gestión se hace más abajo; evitamos nuevas entradas tras gestión
                            pass
                        else:
                            await asyncio.sleep(interval_seconds)
                            continue
                except Exception as _ecb:
                    print(f"[WARN] Fallo evaluando circuit breaker diario en loop: {_ecb}")
            finally:
                try:
                    await client.close_connection()
                except Exception:
                    pass
        except Exception as e:
            # Cualquier error inesperado en el ciclo no debe tumbar el loop
            print(f"[LOOP][ERROR] Ciclo falló por excepción no controlada: {e}")
            await asyncio.sleep(interval_seconds)
            continue
        max_concurrent = int(getattr(settings, 'RISK_MAX_CONCURRENT_TRADES', 1))
        if open_syms:
            print(f"[LOOP] Posiciones abiertas: {open_syms} ({len(open_syms)}/{max_concurrent}). Gestionando y evaluando nuevas entradas…")
            # Gestionar todas las posiciones abiertas (trailing/time‑stop)
            try:
                mclient = await _create_client_with_retry(api_key=api_key, secret_key=secret_key, testnet=use_testnet)
            except (aiohttp.ClientConnectorError, aiohttp.ClientOSError, asyncio.TimeoutError, socket.gaierror, BinanceRequestException) as e:
                print(f"[LOOP][NET] No se pudo crear cliente para gestión por error de red: {e}. Saltando gestión este ciclo.")
                await asyncio.sleep(interval_seconds)
                continue
            try:
                for osym in open_syms:
                    await _manage_open_position(mclient, osym)
            finally:
                try:
                    await mclient.close_connection()
                except Exception:
                    pass
            # Si alcanzamos el máximo, no abrimos nuevas; solo esperar
            if len(open_syms) >= max_concurrent:
                await asyncio.sleep(interval_seconds)
                continue

        # Ejecuta un ciclo de decisión/ejecución
        code = await main_async(symbol_cli, side_cli)
        # Espera antes del próximo intento
        await asyncio.sleep(interval_seconds)
    # no llega
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Runner de micro‑autonomía Futuros USDT‑M")
    parser.add_argument("symbol", nargs="?", help="Símbolo opcional a forzar (e.g., ADAUSDT)")
    parser.add_argument("side", nargs="?", help="BUY o SELL opcional")
    parser.add_argument("--loop", action="store_true", help="Ejecutar en modo autónomo continuo")
    parser.add_argument("--interval", type=int, default=int(getattr(settings, 'ANALYSIS_INTERVAL_SECONDS', 300)), help="Intervalo entre ciclos en segundos")
    args = parser.parse_args()

    if args.loop:
        raise SystemExit(asyncio.run(run_loop(args.interval, args.symbol, args.side)))
    else:
        raise SystemExit(asyncio.run(main_async(args.symbol, args.side)))
