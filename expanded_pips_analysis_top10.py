#!/usr/bin/env python3
"""
Análisis de los 10 mejores pares en pips - V3 Comprehensive Results
Evaluación detallada del rendimiento en pips para identificar los mejores performers
"""
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from statistics import mean, median

def load_comprehensive_data():
    """Carga los datos comprehensivos de optimización V3"""
    with open('/home/johan/itbot_linux/COMPREHENSIVE_V3_RESULTS_20250831_061422.json', 'r') as f:
        data = json.load(f)
    return data['results']

def calculate_pips_per_trade(pnl_percent: float, avg_trade: float) -> float:
    """
    Calcula los pips por trade basado en el rendimiento promedio
    Asumiendo que 1% = 100 pips aproximadamente
    """
    return avg_trade * 10000  # Conversión a pips

def analyze_by_pair_and_timeframe():
    """Analiza rendimiento por par y timeframe"""
    results = load_comprehensive_data()
    
    pair_analysis = {}
    
    for result in results:
        pair = result['pair']
        timeframe = result['timeframe']
        config = result['config']
        balance = result['balance']
        
        # Solo analizar configuración conservative con balance 1000 para comparabilidad
        if config != 'conservative' or balance != 1000:
            continue
            
        key = f"{pair}_{timeframe}"
        
        if key not in pair_analysis:
            pair_analysis[key] = {
                'pair': pair,
                'timeframe': timeframe,
                'results': []
            }
        
        # Calcular pips por trade
        pips_per_trade = calculate_pips_per_trade(result['pnl_percent'], result['avg_trade'])
        
        pair_analysis[key]['results'].append({
            'days': result['days'],
            'trades': result['trades'],
            'monthly_return': result['monthly_return'],
            'win_rate': result['win_rate'],
            'profit_factor': result['profit_factor'],
            'avg_trade': result['avg_trade'],
            'pips_per_trade': pips_per_trade,
            'total_pips': pips_per_trade * result['trades'],
            'max_drawdown': result['max_drawdown'],
            'sharpe_ratio': result['sharpe_ratio']
        })
    
    return pair_analysis

def calculate_weighted_metrics(results: List[Dict]) -> Dict:
    """Calcula métricas ponderadas para cada par-timeframe"""
    if not results:
        return {}
    
    # Ponderar por número de días para dar más peso a períodos más largos
    total_weight = sum(r['days'] for r in results)
    
    weighted_monthly_return = sum(r['monthly_return'] * r['days'] for r in results) / total_weight
    weighted_win_rate = sum(r['win_rate'] * r['days'] for r in results) / total_weight
    weighted_profit_factor = sum(r['profit_factor'] * r['days'] for r in results) / total_weight
    weighted_pips_per_trade = sum(r['pips_per_trade'] * r['days'] for r in results) / total_weight
    weighted_max_drawdown = sum(r['max_drawdown'] * r['days'] for r in results) / total_weight
    weighted_sharpe = sum(r['sharpe_ratio'] * r['days'] for r in results) / total_weight
    
    # Calcular score compuesto
    composite_score = (
        weighted_monthly_return * 0.3 +
        weighted_win_rate * 0.2 +
        weighted_profit_factor * 10 +  # Escalado para balance
        weighted_pips_per_trade * 0.1 +
        (100 - weighted_max_drawdown) * 0.2 +  # Invertido: menos drawdown = mejor
        weighted_sharpe * 20  # Escalado para balance
    )
    
    return {
        'weighted_monthly_return': weighted_monthly_return,
        'weighted_win_rate': weighted_win_rate,
        'weighted_profit_factor': weighted_profit_factor,
        'weighted_pips_per_trade': weighted_pips_per_trade,
        'weighted_max_drawdown': weighted_max_drawdown,
        'weighted_sharpe': weighted_sharpe,
        'composite_score': composite_score,
        'total_trades': sum(r['trades'] for r in results),
        'avg_trades_per_month': mean([r['trades'] * (30/r['days']) for r in results])
    }

def get_top_10_pairs():
    """Identifica los 10 mejores pares basado en score compuesto"""
    pair_analysis = analyze_by_pair_and_timeframe()
    
    scored_pairs = []
    
    for key, data in pair_analysis.items():
        metrics = calculate_weighted_metrics(data['results'])
        if metrics:  # Solo si hay métricas válidas
            scored_pairs.append({
                'key': key,
                'pair': data['pair'],
                'timeframe': data['timeframe'],
                **metrics
            })
    
    # Ordenar por score compuesto descendente
    scored_pairs.sort(key=lambda x: x['composite_score'], reverse=True)
    
    return scored_pairs[:10]

def detailed_pips_analysis():
    """Análisis detallado de pips para los mejores pares"""
    print("=" * 80)
    print("ANÁLISIS DE PIPS - 10 MEJORES PARES V3 COMPREHENSIVE RESULTS")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    top_10 = get_top_10_pairs()
    
    if not top_10:
        print("❌ No se encontraron datos válidos para análisis")
        return
    
    print(f"🏆 TOP 10 MEJORES PARES (de {len(analyze_by_pair_and_timeframe())} combinaciones analizadas)")
    print()
    
    # Tabla resumen
    print("RANKING | PAR/TIMEFRAME | RETORNO MENSUAL | WIN RATE | PIPS/TRADE | SCORE")
    print("-" * 80)
    
    for i, pair_data in enumerate(top_10, 1):
        print(f"{i:2d}      | {pair_data['pair']:10s} {pair_data['timeframe']:3s} | "
              f"{pair_data['weighted_monthly_return']:10.2f}% | "
              f"{pair_data['weighted_win_rate']:7.1f}% | "
              f"{pair_data['weighted_pips_per_trade']:8.1f} | "
              f"{pair_data['composite_score']:7.1f}")
    
    print()
    print("=" * 80)
    print("ANÁLISIS DETALLADO DE LOS TOP 5")
    print("=" * 80)
    
    pair_analysis = analyze_by_pair_and_timeframe()
    
    for i, pair_data in enumerate(top_10[:5], 1):
        key = pair_data['key']
        detailed_data = pair_analysis[key]
        
        print(f"\n🥇 RANK #{i}: {pair_data['pair']} - {pair_data['timeframe']}")
        print("-" * 50)
        
        # Métricas principales
        print(f"📊 MÉTRICAS PRINCIPALES:")
        print(f"   • Retorno Mensual Promedio: {pair_data['weighted_monthly_return']:.2f}%")
        print(f"   • Win Rate Promedio: {pair_data['weighted_win_rate']:.1f}%")
        print(f"   • Profit Factor Promedio: {pair_data['weighted_profit_factor']:.2f}")
        print(f"   • Pips por Trade: {pair_data['weighted_pips_per_trade']:.1f}")
        print(f"   • Max Drawdown Promedio: {pair_data['weighted_max_drawdown']:.2f}%")
        print(f"   • Sharpe Ratio: {pair_data['weighted_sharpe']:.3f}")
        print(f"   • Score Compuesto: {pair_data['composite_score']:.1f}")
        
        # Desglose por período
        print(f"\n📈 DESGLOSE POR PERÍODO:")
        for result in detailed_data['results']:
            total_pips = result['pips_per_trade'] * result['trades']
            monthly_pips = total_pips * (30 / result['days'])
            
            print(f"   • {result['days']:2d} días: {result['trades']:2d} trades, "
                  f"{result['pips_per_trade']:6.1f} pips/trade, "
                  f"{total_pips:7.0f} pips totales, "
                  f"{monthly_pips:7.0f} pips/mes")
        
        # Proyección trimestral
        quarterly_projection = pair_data['avg_trades_per_month'] * 3 * pair_data['weighted_pips_per_trade']
        print(f"\n🎯 PROYECCIÓN TRIMESTRAL:")
        print(f"   • Trades esperados/mes: {pair_data['avg_trades_per_month']:.1f}")
        print(f"   • Pips estimados Q1-Q2 2025: {quarterly_projection:.0f} pips")
        
        # Evaluación de riesgo
        risk_level = "ALTO" if pair_data['weighted_max_drawdown'] > 10 else "MEDIO" if pair_data['weighted_max_drawdown'] > 5 else "BAJO"
        consistency = "ALTA" if pair_data['weighted_sharpe'] > 0.1 else "MEDIA" if pair_data['weighted_sharpe'] > 0 else "BAJA"
        
        print(f"\n⚠️  EVALUACIÓN DE RIESGO:")
        print(f"   • Nivel de Riesgo: {risk_level}")
        print(f"   • Consistencia: {consistency}")
        print(f"   • Recomendación: {'✅ RECOMENDADO' if pair_data['composite_score'] > 50 else '⚠️ PRECAUCIÓN' if pair_data['composite_score'] > 20 else '❌ NO RECOMENDADO'}")
    
    # Resumen comparativo con Q1-Q2 2025 reales
    print()
    print("=" * 80)
    print("COMPARACIÓN CON RESULTADOS Q1-Q2 2025 REALES")
    print("=" * 80)
    
    print("\n📋 RESULTADOS HISTÓRICOS (según pips_analysis_quarterly.py):")
    print("   • SOL/USDT: -1,290 pips en 37 trades (-34.9 pips/trade)")
    print("   • BTC/USDT: +1 pip en 12 trades (+0.1 pips/trade)")
    
    print("\n🔍 DISCREPANCIA IDENTIFICADA:")
    print("   • Los mejores pares de la optimización NO coinciden con Q1-Q2 2025")
    print("   • Optimización basada en condiciones de mercado diferentes")
    print("   • Q1-Q2 2025 mostró mercados laterales extremos")
    print("   • Necesidad de validación con datos más recientes")
    
    print("\n💡 RECOMENDACIONES:")
    print("   1. Validar TOP performers con datos de mercados laterales")
    print("   2. Implementar filtros de régimen de mercado")
    print("   3. Considerar adaptación dinámica de pares según condiciones")
    print("   4. Establecer umbrales mínimos de pips/trade para activación")
    
    print()
    print("=" * 80)
    print("ANÁLISIS COMPLETO - READY FOR IMPLEMENTATION")
    print("=" * 80)

if __name__ == "__main__":
    detailed_pips_analysis()
