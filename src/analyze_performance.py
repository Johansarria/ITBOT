#!/usr/bin/env python3
"""
Análisis de Rendimiento del Sistema Paper Trading SICAR
Evalúa ROI y Win Rate de backtests y simulaciones
"""

import json
import pandas as pd
from datetime import datetime
import os

def analyze_ensemble_results():
    """Analiza resultados del sistema ensemble"""
    try:
        if not os.path.exists('ensemble_sicar_results.csv'):
            print("❌ No se encontró ensemble_sicar_results.csv")
            return
            
        df = pd.read_csv('ensemble_sicar_results.csv')
        
        # Calcular métricas básicas
        trades = df[df['type'].str.contains('CLOSE')].copy()
        if len(trades) > 0:
            total_pnl = trades['pnl'].sum()
            winning_trades = len(trades[trades['pnl'] > 0])
            total_trades = len(trades)
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            # Capital inicial estimado (500)
            initial_capital = 500
            roi = (total_pnl / initial_capital) * 100
            
            print(f'=== ANÁLISIS SISTEMA ENSEMBLE SICAR ===')
            print(f'📊 Total Trades: {total_trades}')
            print(f'🏆 Win Rate: {win_rate:.1f}%')
            print(f'💰 PnL Total: ${total_pnl:.2f}')
            print(f'📈 ROI: {roi:.2f}%')
            print(f'💵 Capital Final Estimado: ${initial_capital + total_pnl:.2f}')
            
            # Análisis por símbolo
            print(f'\n=== ANÁLISIS POR SÍMBOLO ===')
            for symbol in trades['symbol'].unique():
                symbol_trades = trades[trades['symbol'] == symbol]
                symbol_pnl = symbol_trades['pnl'].sum()
                symbol_wins = len(symbol_trades[symbol_trades['pnl'] > 0])
                symbol_total = len(symbol_trades)
                symbol_wr = (symbol_wins / symbol_total) * 100 if symbol_total > 0 else 0
                print(f'{symbol}: {symbol_total} trades, WR: {symbol_wr:.1f}%, PnL: ${symbol_pnl:.2f}')
        else:
            print('❌ No hay trades cerrados para analizar en ensemble')
            
    except Exception as e:
        print(f'❌ Error analizando ensemble: {e}')

def analyze_paper_trading():
    """Analiza resultados del paper trading actual"""
    try:
        if not os.path.exists('test_final_integration_results.json'):
            print("❌ No se encontró test_final_integration_results.json")
            return
            
        with open('test_final_integration_results.json', 'r') as f:
            data = json.load(f)
        
        pt_data = data.get('DRL + Paper Trading', {}).get('result', {})
        print(f'\n=== SISTEMA PAPER TRADING ACTUAL ===')
        print(f'💰 Capital Inicial: ${pt_data.get("initial_capital", 0):.2f}')
        print(f'💵 Capital Actual: ${pt_data.get("current_capital", 0):.2f}')
        print(f'📊 Total Trades: {pt_data.get("total_trades", 0)}')
        print(f'🏆 Win Rate: {pt_data.get("win_rate", 0):.1f}%')
        print(f'📈 ROI: {pt_data.get("total_return_pct", 0):.2f}%')
        print(f'💰 PnL Total: ${pt_data.get("total_pnl", 0):.2f}')
        
        # Análisis DRL
        drl_data = pt_data.get('drl_performance', {})
        print(f'\n=== RENDIMIENTO DRL ===')
        print(f'🤖 DRL Trades: {drl_data.get("total_drl_trades", 0)}')
        print(f'🎯 DRL Win Rate: {drl_data.get("drl_win_rate", 0):.1f}%')
        print(f'💰 DRL PnL: ${drl_data.get("drl_total_pnl", 0):.2f}')
        print(f'🔮 DRL Confidence: {drl_data.get("drl_confidence_avg", 0):.2f}')
        
    except Exception as e:
        print(f'❌ Error analizando paper trading: {e}')

def analyze_multi_capital():
    """Analiza resultados de multi capital testing"""
    try:
        if not os.path.exists('multi_capital_test_report_20251018_011317.json'):
            print("❌ No se encontró reporte de multi capital")
            return
            
        with open('multi_capital_test_report_20251018_011317.json', 'r') as f:
            data = json.load(f)
        
        results = data.get('results_by_capital', {})
        print(f'\n=== ANÁLISIS MULTI CAPITAL ===')
        
        for capital, result in results.items():
            roi = result.get('total_return_pct', 0)
            win_rate = result.get('win_rate', 0)
            trades = result.get('total_trades', 0)
            final_capital = result.get('final_capital', 0)
            
            print(f'💰 Capital ${capital}: ROI {roi:.2f}%, WR {win_rate:.1f}%, Trades {trades}, Final ${final_capital:.2f}')
            
    except Exception as e:
        print(f'❌ Error analizando multi capital: {e}')

def analyze_recent_performance():
    """Analiza reportes de rendimiento recientes"""
    try:
        performance_files = [
            'reports/performance/performance_report_20251018_004410.json',
            'reports/performance/performance_report_20251018_003527.json',
            'reports/performance/performance_report_20251018_002758.json'
        ]
        
        print(f'\n=== REPORTES DE RENDIMIENTO RECIENTES ===')
        
        for file_path in performance_files:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                pt_perf = data.get('paper_trading_performance', {})
                timestamp = data.get('timestamp', 'N/A')
                
                print(f'\n📅 Reporte: {timestamp}')
                print(f'💰 Capital: ${pt_perf.get("current_capital", 0):.2f}')
                print(f'📊 Trades: {pt_perf.get("total_trades", 0)}')
                print(f'🏆 Win Rate: {pt_perf.get("win_rate", 0):.1f}%')
                print(f'📈 ROI: {pt_perf.get("roi_percentage", 0):.2f}%')
                print(f'💰 PnL: ${pt_perf.get("total_pnl", 0):.2f}')
                
    except Exception as e:
        print(f'❌ Error analizando reportes recientes: {e}')

def main():
    """Función principal de análisis"""
    print("🔍 ANÁLISIS COMPLETO DE RENDIMIENTO SICAR")
    print("=" * 50)
    
    analyze_ensemble_results()
    analyze_paper_trading()
    analyze_multi_capital()
    analyze_recent_performance()
    
    print(f'\n📊 RESUMEN EJECUTIVO:')
    print(f'• El sistema está en fase de pruebas con capital limitado')
    print(f'• Los resultados muestran rendimiento conservador')
    print(f'• Se requiere más tiempo de operación para métricas definitivas')
    print(f'• El sistema DRL está integrado pero aún en entrenamiento')

if __name__ == "__main__":
    main()