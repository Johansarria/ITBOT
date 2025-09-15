#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor Simple de 3 Símbolos de Trading - Estado de Procesos (con PID) + Métricas en vivo
"""

import os
import re
import time
import json
import subprocess
from datetime import datetime
from typing import Dict, Tuple, List

def clear_screen():
    """Limpia la pantalla"""
    os.system('cls' if os.name == 'nt' else 'clear')


def _collect_windows_python_processes():
    """Devuelve lista de tuplas (pid:int, cmd:str) de procesos Python en Windows.
    Maneja el formato típico de WMIC donde CommandLine y ProcessId pueden venir en líneas separadas.
    """
    output = ''
    for exe_name in ("python.exe", "py.exe", "pythonw.exe"):
        try:
            res = subprocess.run(
                ['wmic', 'process', 'where', f'name="{exe_name}"', 'get', 'ProcessId,CommandLine'],
                capture_output=True,
                text=True,
                shell=False
            )
            if res.returncode == 0 and res.stdout:
                output += res.stdout
        except Exception:
            continue
    processes: List[Tuple[int, str]] = []
    last_cmd: str = None
    for raw in (output or '').splitlines():
        line = raw.strip()
        if not line:
            continue
        lcl = line.lower()
        if lcl.startswith('commandline') or lcl.startswith('processid'):
            # encabeceras de WMIC
            continue
        # Si la línea es solo el PID (numérico), emparejar con el último commandline
        if re.fullmatch(r"\d+", line):
            if last_cmd:
                try:
                    processes.append((int(line), last_cmd))
                except Exception:
                    pass
            continue
        # Si la línea incluye CommandLine (con o sin PID al final), intentar extraer PID inline
        m = re.search(r"(.*)\s(\d+)$", line)
        if m:
            cmd = m.group(1).strip()
            try:
                pid = int(m.group(2))
                processes.append((pid, cmd))
                last_cmd = None
                continue
            except Exception:
                pass
        # Si no hay PID en la misma línea, guardar como último commandline para emparejar con la próxima línea de PID
        last_cmd = line
    return processes


def _collect_unix_python_processes():
    """Devuelve lista de tuplas (pid:int, cmd:str) de procesos Python en Unix."""
    try:
        res = subprocess.run(['ps', '-eo', 'pid,command'], capture_output=True, text=True, shell=False)
        lines = (res.stdout or '').splitlines()
        processes = []
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            try:
                pid_str, cmd = line.split(' ', 1)
                processes.append((int(pid_str), cmd.strip()))
            except Exception:
                continue
        return processes
    except Exception:
        return []


def get_python_process_map() -> Dict[str, List[int]]:
    """Devuelve un dict: script_lower -> list[pid] para procesos Python actuales."""
    processes = _collect_windows_python_processes() if os.name == 'nt' else _collect_unix_python_processes()
    proc_map: Dict[str, List[int]] = {}
    for pid, cmd in processes:
        cmd_lower = (cmd or '').lower()
        # extraer nombre del script .py si existe
        script = None
        m = re.search(r'\b([^\\/\s]+\.py)\b', cmd_lower)
        if m:
            script = m.group(1)
        if not script:
            continue
        proc_map.setdefault(script, []).append(pid)
    return proc_map


def check_python_process(script_name: str) -> Tuple[str, List[int]]:
    """Verifica si un script de Python está ejecutándose. Retorna (status:str, pids:list[int])."""
    try:
        proc_map = get_python_process_map()
        pids = proc_map.get(script_name.lower(), [])
        if pids:
            return "🟢 Ejecutándose", pids
        return "🔴 Detenido", []
    except Exception:
        return "❓ Desconocido", []


def parse_live_metrics(log_path: str) -> Dict[str, float]:
    """Lee el log JSONL y calcula métricas vivas avanzadas.
    Retorna dict con todas las métricas solicitadas.
    """
    metrics = {
        # Métricas básicas
        'trades': 0,
        'wins': 0,
        'losses': 0,
        'win_rate': 0.0,
        'capital': None,
        'initial_capital': None,
        'total_pnl': 0.0,
        'total_return_pct': 0.0,
        'last_price': None,
        'last_return': None,
        
        # Métricas avanzadas solicitadas
        'max_drawdown': 0.0,
        'current_drawdown': 0.0,
        'profit_factor': 0.0,
        'expectancy': 0.0,
        'avg_return_per_trade': 0.0,
        'std_return_per_trade': 0.0,
        'avg_latency_ms': 0.0,
        'trades_per_hour': 0.0,
        'avg_pips_per_trade': 0.0,
        'total_pips': 0.0,
    }
    
    if not os.path.exists(log_path):
        return metrics

    try:
        # Leer líneas (últimas 5000 para cálculos estadísticos)
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if len(lines) > 5000:
            lines = lines[-5000:]

        # Encontrar último simulation_start
        last_start_idx = -1
        for i, line in enumerate(lines):
            try:
                obj = json.loads(line)
                if obj.get('event_type') == 'simulation_start':
                    last_start_idx = i
            except Exception:
                continue

        # Datos para cálculos estadísticos
        returns = []
        pnls = []
        latencies = []
        trades_data = []
        
        # Procesar trades desde último start
        peak_capital = None
        current_capital = None
        first_trade_time = None
        last_trade_time = None
        
        for line in lines[last_start_idx + 1:]:
            try:
                obj = json.loads(line)
            except Exception:
                continue

            etype = obj.get('event_type')
            data = obj.get('data') or {}

            if etype == 'simulation_start':
                metrics['initial_capital'] = float(data.get('initial_capital', 1000.0))
                peak_capital = metrics['initial_capital']
                current_capital = metrics['initial_capital']
                
            elif etype == 'trade_executed':
                metrics['trades'] += 1
                
                # Datos básicos
                pnl = float(data.get('pnl', 0.0))
                pnls.append(pnl)
                
                is_winner = data.get('is_winner', False)
                if is_winner:
                    metrics['wins'] += 1
                else:
                    metrics['losses'] += 1
                
                # Retorno y precio
                ret = float(data.get('return_pct', 0.0))
                returns.append(ret)
                
                # Capital tracking
                cap_after = data.get('capital_after')
                if cap_after is not None:
                    current_capital = float(cap_after)
                    if peak_capital is None or current_capital > peak_capital:
                        peak_capital = current_capital
                
                # Latencia
                latency = data.get('execution_latency_ms')
                if latency:
                    latencies.append(float(latency))
                
                # Pips
                pips = data.get('pips')
                if pips:
                    metrics['total_pips'] += float(pips)
                
                # Timestamps para trades por hora
                ts_str = data.get('timestamp')
                if ts_str:
                    ts = datetime.fromisoformat(ts_str)
                    if first_trade_time is None:
                        first_trade_time = ts
                    last_trade_time = ts
                
                # Guardar datos del trade
                trades_data.append({
                    'pnl': pnl,
                    'return_pct': ret,
                    'is_winner': is_winner
                })

        # Cálculos finales
        if metrics['initial_capital'] is None:
            metrics['initial_capital'] = 1000.0
            
        if metrics['trades'] > 0:
            # Win rate
            metrics['win_rate'] = (metrics['wins'] / metrics['trades']) * 100.0
            
            # Retorno y P&L totales
            if current_capital is not None:
                metrics['capital'] = current_capital
                metrics['total_pnl'] = current_capital - metrics['initial_capital']
                metrics['total_return_pct'] = (metrics['total_pnl'] / metrics['initial_capital']) * 100.0
            
            # Drawdown
            if peak_capital is not None and current_capital is not None:
                metrics['current_drawdown'] = ((peak_capital - current_capital) / peak_capital) * 100.0
                
                # Max drawdown (buscar en todo el historial)
                max_dd = 0.0
                running_peak = metrics['initial_capital']
                for line in lines[last_start_idx + 1:]:
                    try:
                        obj = json.loads(line)
                        if obj.get('event_type') == 'trade_executed':
                            data = obj.get('data', {})
                            cap_after = data.get('capital_after')
                            if cap_after:
                                running_cap = float(cap_after)
                                if running_cap > running_peak:
                                    running_peak = running_cap
                                dd = ((running_peak - running_cap) / running_peak) * 100.0
                                if dd > max_dd:
                                    max_dd = dd
                    except Exception:
                        continue
                metrics['max_drawdown'] = max_dd
            
            # Profit factor y expectancy
            gross_profit = sum(pnl for pnl in pnls if pnl > 0)
            gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0))
            
            if gross_loss > 0:
                metrics['profit_factor'] = gross_profit / gross_loss
            else:
                metrics['profit_factor'] = float('inf') if gross_profit > 0 else 0.0
            
            if metrics['trades'] > 0:
                metrics['expectancy'] = metrics['total_pnl'] / metrics['trades']
            
            # Promedio y desviación estándar de retornos
            if returns:
                metrics['avg_return_per_trade'] = sum(returns) / len(returns)
                if len(returns) > 1:
                    mean = metrics['avg_return_per_trade']
                    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
                    metrics['std_return_per_trade'] = variance ** 0.5
            
            # Latencia promedio
            if latencies:
                metrics['avg_latency_ms'] = sum(latencies) / len(latencies)
            
            # Trades por hora
            if first_trade_time and last_trade_time and first_trade_time != last_trade_time:
                duration_hours = (last_trade_time - first_trade_time).total_seconds() / 3600.0
                if duration_hours > 0:
                    metrics['trades_per_hour'] = metrics['trades'] / duration_hours
            
            # Pips promedio por trade
            if metrics['total_pips'] > 0 and metrics['trades'] > 0:
                metrics['avg_pips_per_trade'] = metrics['total_pips'] / metrics['trades']

    except Exception as e:
        # En caso de error, mantener valores por defecto
        pass

    return metrics


def monitor_symbols():
    """Monitorea los símbolos con métricas avanzadas."""
    entries = {
        'BNBUSDT': {
            'script': 'simulacion_real_bnbusdt_1.py',
            'log': 'simulacion_bnbusdt_1.jsonl'
        },
        'ADAUSDT': {
            'script': 'simulacion_real_adausdt_2.py',
            'log': 'simulacion_adausdt_2.jsonl'
        },
        'SOLUSDT': {
            'script': 'simulacion_real_solusdt_3.py',
            'log': 'simulacion_solusdt_3.jsonl'
        },
    }
    total_symbols = len(entries)
    
    # Registrar hora de inicio del monitor
    monitor_start_time = datetime.now()

    print("🚀 Iniciando Monitor de 3 Símbolos de Trading (Métricas Avanzadas)")
    print(f"📅 Inicio del Monitor: {monitor_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("Presiona Ctrl+C para salir\n")

    try:
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')  # Limpiar pantalla
            print("                    MONITOR DE SIMULACIONES DE TRADING ALGORÍTMICO")
            print("="*150)
            
            # Calcular tiempo transcurrido
            current_time = datetime.now()
            elapsed_time = current_time - monitor_start_time
            hours, remainder = divmod(int(elapsed_time.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            print(f"📅 Inicio del Monitor: {monitor_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⏱️  Tiempo Transcurrido: {hours:02d}:{minutes:02d}:{seconds:02d} (sin interrupciones)")
            print(f"🔄 Actualización: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print()

            # Tabla principal con KPIs básicos
            print("📈 KPIs BÁSICOS:")
            print("-"*150)
            print(f"{'SÍMBOLO':<8} {'ESTADO':<10} {'PID(s)':<12} {'TRADES':>6} {'WIN%':>6} {'CAPITAL':>12} {'RETORNO':>8} {'P&L':>10} {'PIPS':>8}")
            print("-"*150)

            active_count = 0
            symbols_data = {}

            for symbol, cfg in entries.items():
                script = cfg['script']
                log_path = cfg['log']

                status, pids = check_python_process(script)
                if "🟢" in status:
                    active_count += 1
                pid_text = ", ".join(str(p) for p in pids) if pids else "—"

                # Métricas en vivo
                m = parse_live_metrics(log_path)
                symbols_data[symbol] = m
                
                trades = m['trades']
                winp = f"{m['win_rate']:.1f}%" if trades > 0 else "—"
                capital = f"${m['capital']:,.0f}" if m['capital'] is not None else "—"
                retorno = f"{m['total_return_pct']:+.1f}%" if m['capital'] is not None else "—"
                pnl = f"${m['total_pnl']:+.1f}" if trades > 0 else "—"
                pips = f"{m['total_pips']:+.1f}" if m['total_pips'] != 0 else "—"

                print(f"{symbol:<8} {status:<10} {pid_text:<12} {trades:>6} {winp:>6} {capital:>12} {retorno:>8} {pnl:>10} {pips:>8}")

            print("-"*150)

            # KPIs AVANZADOS
            print("\n📊 KPIs AVANZADOS:")
            print("-"*150)
            print(f"{'SÍMBOLO':<8} {'MAX DD':>8} {'CURR DD':>9} {'PF':>6} {'EXPECT':>8} {'AVG RET':>9} {'STD RET':>9} {'LAT(ms)':>9} {'TR/H':>6}")
            print("-"*150)

            for symbol in entries.keys():
                m = symbols_data[symbol]
                
                max_dd = f"{m['max_drawdown']:.1f}%" if m['max_drawdown'] > 0 else "—"
                curr_dd = f"{m['current_drawdown']:.1f}%" if m['current_drawdown'] > 0 else "—"
                pf = f"{m['profit_factor']:.2f}" if m['profit_factor'] < 999 else "∞"
                expectancy = f"${m['expectancy']:+.2f}" if m['expectancy'] != 0 else "—"
                avg_ret = f"{m['avg_return_per_trade']:+.2f}%" if m['avg_return_per_trade'] != 0 else "—"
                std_ret = f"{m['std_return_per_trade']:.2f}%" if m['std_return_per_trade'] > 0 else "—"
                latency = f"{m['avg_latency_ms']:.0f}" if m['avg_latency_ms'] > 0 else "—"
                trades_h = f"{m['trades_per_hour']:.1f}" if m['trades_per_hour'] > 0 else "—"

                print(f"{symbol:<8} {max_dd:>8} {curr_dd:>9} {pf:>6} {expectancy:>8} {avg_ret:>9} {std_ret:>9} {latency:>9} {trades_h:>6}")

            print("-"*150)
            print(f"✅ Simulaciones activas: {active_count}/{total_symbols}")
            print()

            # Leyenda
            print("ℹ️  LEYENDA:")
            print("  MAX DD: Máximo drawdown histórico")
            print("  CURR DD: Drawdown actual")
            print("  PF: Profit Factor")
            print("  EXPECT: Expectancy por trade ($)")
            print("  AVG RET: Retorno promedio por trade")
            print("  STD RET: Desviación estándar de retornos")
            print("  LAT: Latencia promedio de ejecución (ms)")
            print("  TR/H: Trades por hora")
            print()
            print(f"• Monitor PID: {os.getpid()}")
            print("• Actualización cada 15 segundos")
            print("Presiona Ctrl+C para salir")

            time.sleep(15)

    except KeyboardInterrupt:
        print("\n\n✅ Monitor detenido")

if __name__ == "__main__":
    monitor_symbols()