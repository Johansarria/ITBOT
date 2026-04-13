#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtest de 30 días con configuraciones actuales (tal cual)
- Selecciona en tiempo real los 3 mejores pares desde Binance
- Usa el backtester de datos reales existente (estrategias tal cual)
"""

from datetime import datetime
from typing import List, Dict, Tuple
import json

from analisis_pares_actuales import BinanceCurrentAnalyzer
from strategies.real_data_backtester import RealDataBacktester
import pandas as pd


def _to_ccxt_symbol(symbol: str) -> str:
    """Convierte 'BTCUSDT' -> 'BTC/USDT' para ccxt"""
    if '/' in symbol:
        return symbol
    if symbol.endswith('USDT'):
        return f"{symbol[:-4]}/USDT"
    return symbol


def seleccionar_top3() -> Tuple[List[str], List[Dict]]:
    analyzer = BinanceCurrentAnalyzer()
    results = analyzer.analyze_all_pairs()
    ranked = analyzer.rank_pairs_for_trading(results)
    top3 = [r['symbol'] for r in ranked[:3]]
    return top3, ranked


def analizar_trades(trades: List[Dict], initial_capital: float, days: int) -> Dict:
    """Analiza resultados (versión segura sin escribir archivos externos)."""
    if not trades:
        print("❌ No hay trades para analizar")
        return {}

    df_trades = pd.DataFrame(trades)
    total_trades = len(df_trades)
    winning_trades = (df_trades['pnl_amount'] > 0).sum()
    losing_trades = (df_trades['pnl_amount'] < 0).sum()
    win_rate = (winning_trades / total_trades) * 100 if total_trades else 0.0

    total_pnl = float(df_trades['pnl_amount'].sum())
    total_return = (total_pnl / initial_capital) * 100 if initial_capital else 0.0

    avg_win = float(df_trades.loc[df_trades['pnl_amount'] > 0, 'pnl_amount'].mean() or 0)
    avg_loss = float(df_trades.loc[df_trades['pnl_amount'] < 0, 'pnl_amount'].mean() or 0)
    profit_factor = (
        abs(avg_win * winning_trades) / abs(avg_loss * losing_trades)
        if losing_trades > 0 and avg_loss != 0 else float('inf')
    )

    # Drawdown aproximado usando PnL acumulado
    df_sorted = df_trades.sort_values('entry_time')
    cum_pnl = df_sorted['pnl_amount'].cumsum()
    running_max = cum_pnl.cummax()
    drawdown = (cum_pnl - running_max) / initial_capital * 100 if initial_capital else pd.Series([0])
    max_drawdown = float(drawdown.min()) if not drawdown.empty else 0.0

    daily_return = total_return / days if days else 0.0
    monthly_return = daily_return * 30

    print("\n" + "="*80)
    print("📊 RESULTADOS DEL BACKTEST - DATOS REALES BINANCE (30 DÍAS)")
    print("="*80)
    print(f"\n💰 RENDIMIENTO GENERAL:")
    print(f"  Capital Inicial:      ${initial_capital:,.2f}")
    print(f"  Capital Final:        ${initial_capital + total_pnl:,.2f}")
    print(f"  Ganancia Total:       ${total_pnl:,.2f}")
    print(f"  Retorno Total:        {total_return:.2f}%")
    print(f"  Retorno Mensual Prom: {monthly_return:.2f}%")

    print(f"\n📈 MÉTRICAS DE TRADING:")
    print(f"  Total Trades:         {total_trades}")
    print(f"  Trades Ganadores:     {winning_trades}")
    print(f"  Trades Perdedores:    {losing_trades}")
    print(f"  Win Rate:             {win_rate:.1f}%")
    print(f"  Ganancia Promedio:    ${avg_win:.2f}")
    print(f"  Pérdida Promedio:     ${avg_loss:.2f}")
    print(f"  Profit Factor:        {profit_factor:.2f}")
    print(f"  Drawdown Máximo:      {max_drawdown:.2f}%")

    summary = {
        'period_days': days,
        'initial_capital': initial_capital,
        'final_capital': initial_capital + total_pnl,
        'total_pnl': total_pnl,
        'total_return_pct': total_return,
        'monthly_return_pct': monthly_return,
        'total_trades': total_trades,
        'win_rate_pct': win_rate,
        'profit_factor': profit_factor,
        'max_drawdown_pct': max_drawdown,
    }
    return summary


def run(days: int = 30, initial_capital: float = 10000):
    top3, ranked = seleccionar_top3()
    ccxt_pairs = [_to_ccxt_symbol(s) for s in top3]
    print("\n🏆 TOP 3 pares seleccionados (datos actuales Binance):", ccxt_pairs)

    bt = RealDataBacktester(initial_capital=initial_capital)

    all_trades = []
    for pair in ccxt_pairs:
        print(f"\n📊 Procesando {pair} (30 días)...")
        for strat_name, cfg in bt.strategies_config.items():
            timeframe = cfg['timeframe']
            df = bt.fetch_historical_data(pair, timeframe, days=days)
            if df is None or len(df) < 100:
                print(f"  ⚠️ Datos insuficientes para {pair} en {timeframe}")
                continue
            df = bt.calculate_technical_indicators(df)
            trades = bt.execute_strategy(pair, df, strat_name)
            all_trades.extend(trades)
            if trades:
                total_pnl = sum(t['pnl_amount'] for t in trades)
                win_rate = len([t for t in trades if t['pnl_amount'] > 0]) / len(trades) * 100
                print(f"  ✅ {strat_name}: {len(trades)} trades, PnL: ${total_pnl:.2f}, WR: {win_rate:.1f}%")
            else:
                print(f"  ⚪ {strat_name}: Sin trades")

    summary = analizar_trades(all_trades, initial_capital, days)

    # Guardar un pequeño resumen + selección
    reporte = {
        'timestamp': datetime.now().isoformat(),
        'top3_symbols_raw': top3,
        'top3_ccxt': ccxt_pairs,
        'summary': summary,
    }
    try:
        with open('reports/TOP3_ACTUAL_30D.json', 'w', encoding='utf-8') as f:
            json.dump(reporte, f, indent=2, ensure_ascii=False, default=str)
        print("\n💾 Resumen guardado en reports/TOP3_ACTUAL_30D.json")
    except Exception as e:
        print(f"\n⚠️ No se pudo guardar el reporte local: {e}")


if __name__ == '__main__':
    run(days=30, initial_capital=10000)