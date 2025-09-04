import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import List, Tuple

from binance.client import AsyncClient

# Ensure project root on path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import reload_settings


def _pgrep_loop() -> List[Tuple[int, str]]:
    try:
        out = subprocess.check_output(["bash", "-lc", "pgrep -af 'micro_futures_autonomy.py --loop' || true"]).decode().strip()
        rows = []
        for line in out.splitlines():
            parts = line.split(maxsplit=1)
            if not parts:
                continue
            try:
                pid = int(parts[0])
            except Exception:
                continue
            cmd = parts[1] if len(parts) > 1 else ""
            rows.append((pid, cmd))
        return rows
    except Exception:
        return []


def _start_loop(interval: int = 180) -> int:
    env = os.environ.copy()
    env["ENABLE_MICRO_TRADE"] = "True"
    env["MICRO_TRADE_USE_FUTURES"] = "True"
    env["BINANCE_USE_TESTNET_FUTURES"] = "False"
    log_path = os.path.join(PROJECT_ROOT, "runtime_autonomy.log")
    with open(log_path, "a") as logf:
        proc = subprocess.Popen([
            os.path.join(PROJECT_ROOT, ".venv", "bin", "python"),
            os.path.join(PROJECT_ROOT, "micro_futures_autonomy.py"),
            "--loop",
            "--interval",
            str(interval),
        ], stdout=logf, stderr=logf, cwd=PROJECT_ROOT, env=env)
    return proc.pid


async def _snapshot_equity(client: AsyncClient) -> float:
    try:
        acc = await client.futures_account()
        return float(acc.get("totalMarginBalance", 0) or 0)
    except Exception:
        return 0.0


async def _open_positions(client: AsyncClient) -> List[Tuple[str, float]]:
    try:
        ps = await client.futures_position_information()
        out: List[Tuple[str, float]] = []
        for p in ps:
            sym = p.get("symbol")
            amt = float(p.get("positionAmt") or 0)
            if abs(amt) > 0:
                out.append((sym, amt))
        return out
    except Exception:
        return []


def _load_day_state(equity_now: float) -> Tuple[str, float]:
    storage_dir = os.path.join(PROJECT_ROOT, "storage")
    os.makedirs(storage_dir, exist_ok=True)
    day_path = os.path.join(storage_dir, "daily_state.json")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if os.path.exists(day_path):
        try:
            day = json.load(open(day_path, "r", encoding="utf-8"))
            if day.get("date") == today:
                return today, float(day.get("equity_open", equity_now) or equity_now)
        except Exception:
            pass
    try:
        json.dump({"date": today, "equity_open": equity_now}, open(day_path, "w", encoding="utf-8"))
    except Exception:
        pass
    return today, equity_now


def _load_baseline(equity_now: float) -> float:
    storage_dir = os.path.join(PROJECT_ROOT, "storage")
    os.makedirs(storage_dir, exist_ok=True)
    base_path = os.path.join(storage_dir, "futures_baseline.json")
    if os.path.exists(base_path):
        try:
            data = json.load(open(base_path, "r", encoding="utf-8"))
            return float(data.get("amount", equity_now) or equity_now)
        except Exception:
            return equity_now
    try:
        json.dump({"amount": equity_now, "source": "watchdog_init", "time_ms": int(time.time()*1000)}, open(base_path, "w", encoding="utf-8"))
    except Exception:
        pass
    return equity_now


async def main():
    s = reload_settings()
    interval = int(getattr(s, "ANALYSIS_INTERVAL_SECONDS", 180))
    watch_period = int(os.getenv("WATCHDOG_INTERVAL_SECONDS", "120"))
    core = set(s.MICRO_TRADE_ALLOWED_SYMBOLS or [])
    storage_dir = os.path.join(PROJECT_ROOT, "storage")
    os.makedirs(storage_dir, exist_ok=True)
    status_path = os.path.join(storage_dir, "monitor_status.json")
    hist_path = os.path.join(storage_dir, "monitor_history.jsonl")

    client = await AsyncClient.create(api_key=s.BINANCE_API_KEY, api_secret=s.BINANCE_SECRET_KEY, testnet=bool(s.BINANCE_USE_TESTNET_FUTURES))
    try:
        last_summary_ts = 0
        summary_every = int(os.getenv("WATCHDOG_SUMMARY_SECONDS", str(3*60*60)))  # 3h por defecto
        while True:
            # Ensure loop
            procs = _pgrep_loop()
            if len(procs) == 0:
                pid = _start_loop(interval)
                loop_status = f"restarted pid={pid}"
            elif len(procs) > 1:
                # Kill extras, keep the oldest
                procs_sorted = sorted(procs, key=lambda x: x[0])
                keep = procs_sorted[0][0]
                for pid, _ in procs_sorted[1:]:
                    try:
                        os.kill(pid, 9)
                    except Exception:
                        pass
                loop_status = f"dedup keep={keep} killed={len(procs_sorted)-1}"
            else:
                loop_status = f"ok pid={procs[0][0]}"

            # Equity / PnL
            equity = await _snapshot_equity(client)
            today, day_open = _load_day_state(equity)
            baseline = _load_baseline(equity)
            daily_pnl = equity - day_open
            daily_pct = (daily_pnl / day_open * 100.0) if day_open > 0 else 0.0
            base_diff = equity - baseline
            base_pct = (base_diff / baseline * 100.0) if baseline > 0 else 0.0

            # Thresholds
            lock_abs = 0.0
            pl_pct = float(getattr(s, 'DAILY_PROFIT_LOCK_PCT', 0.0))
            pl_abs = float(getattr(s, 'DAILY_PROFIT_LOCK_USDT', 0.0))
            if pl_pct and pl_pct > 0:
                lock_abs = max(lock_abs, day_open * (pl_pct/100.0))
            if pl_abs and pl_abs > 0:
                lock_abs = max(lock_abs, pl_abs)
            loss_abs = 0.0
            dl_pct = float(getattr(s, 'DAILY_MAX_LOSS_PCT', 0.0))
            dl_abs = float(getattr(s, 'DAILY_MAX_LOSS_USDT', 0.0))
            if dl_pct and dl_pct > 0:
                loss_abs = max(loss_abs, day_open * (dl_pct/100.0))
            if dl_abs and dl_abs > 0:
                loss_abs = max(loss_abs, dl_abs)

            # Positions
            pos = await _open_positions(client)
            non_core = [sym for sym, amt in pos if sym not in core]

            # Save status
            ts = int(time.time())
            status = {
                "ts": ts,
                "loop": loop_status,
                "equity": equity,
                "day_open": day_open,
                "daily_pnl": daily_pnl,
                "daily_pct": daily_pct,
                "baseline": baseline,
                "baseline_diff": base_diff,
                "baseline_pct": base_pct,
                "profit_lock_abs": lock_abs,
                "max_loss_abs": loss_abs,
                "open_positions": pos,
                "non_core_positions": non_core,
            }
            try:
                json.dump(status, open(status_path, "w", encoding="utf-8"))
                with open(hist_path, "a", encoding="utf-8") as hf:
                    hf.write(json.dumps(status) + "\n")
            except Exception:
                pass

            # Periodic summary every summary_every seconds
            now_ts = int(time.time())
            if now_ts - last_summary_ts >= summary_every:
                notes: List[str] = []
                if len(procs) > 1:
                    notes.append("Doble loop detectado y corregido")
                if daily_pnl >= lock_abs > 0:
                    notes.append("Objetivo diario alcanzado (profit lock activo)")
                if (-daily_pnl) >= loss_abs > 0:
                    notes.append("Cerca del límite de pérdida diaria (revisar exposición)")
                if non_core:
                    notes.append(f"Posiciones no-core presentes: {non_core}")
                if not notes:
                    notes.append("Operación dentro de parámetros")

                summary = {
                    "at": datetime.now(timezone.utc).isoformat(),
                    "equity": equity,
                    "daily_pct": daily_pct,
                    "baseline_pct": base_pct,
                    "open_positions": pos,
                    "notes": notes,
                }
                try:
                    json.dump(summary, open(os.path.join(storage_dir, "last_summary.json"), "w", encoding="utf-8"))
                    with open(os.path.join(storage_dir, "daily_summary.txt"), "a", encoding="utf-8") as sf:
                        sf.write(
                            f"[{summary['at']}] daily={daily_pct:.2f}% base={base_pct:.2f}% eq={equity:.4f} pos={len(pos)} notes={'; '.join(notes)}\n"
                        )
                except Exception:
                    pass
                last_summary_ts = now_ts

            # Console heartbeat
            print(f"[WATCHDOG] loop={loop_status} daily={daily_pct:.2f}% base={base_pct:.2f}% pos={len(pos)} non_core={non_core}")

            await asyncio.sleep(watch_period)
    finally:
        try:
            await client.close_connection()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
