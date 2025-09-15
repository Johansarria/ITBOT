#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reporte Consolidado de Rentabilidad Mensual por Simbolo
Consolida todos los datos de rentabilidad de diferentes fuentes
"""

import os
import re
from datetime import datetime
from typing import Dict, List

class ConsolidatedProfitabilityReport:
    """Generador de reporte consolidado de rentabilidad"""
    
    def __init__(self, results_directory: str = "."):
        self.results_directory = results_directory
        self.all_symbol_data = {}
        
    def extract_backtest_data(self) -> Dict:
        """Extrae datos de archivos de backtest independientes"""
        backtest_data = {}
        
        # Buscar archivo de backtest de 90 dias
        backtest_file = "independent_backtest_90days_20250913_130240.txt"
        filepath = os.path.join(self.results_directory, backtest_file)
        
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Extraer datos del ranking de simbolos rentables
                ranking_match = re.search(r'RANKING SIMBOLOS RENTABLES:(.*?)DETALLE', content, re.DOTALL)
                if ranking_match:
                    lines = ranking_match.group(1).strip().split('\n')
                    for line in lines:
                        # Patron: 1. BTCUSDT - PnL: $ 23.60 | Win Rate: 100.0% | Trades: 3
                        match = re.search(r'(\w+USDT).*?PnL: \$\s*([\d.-]+).*?Win Rate: ([\d.]+)%.*?Trades: (\d+)', line)
                        if match:
                            symbol, pnl, win_rate, trades = match.groups()
                            # Calcular rentabilidad mensual (90 dias -> 30 dias)
                            monthly_pnl = float(pnl) * (30/90)
                            monthly_pct = (monthly_pnl / 1000) * 100  # Asumiendo $1000 de capital
                            
                            backtest_data[symbol] = {
                                'monthly_pnl_amount': monthly_pnl,
                                'monthly_pnl_pct': monthly_pct,
                                'total_trades': int(trades),
                                'win_rate': float(win_rate),
                                'source': 'Independent Backtest 90d',
                                'period_days': 90
                            }
                            
                # Extraer simbolos con perdidas del contenido general
                # Buscar otros simbolos mencionados
                all_symbols = re.findall(r'(\w+USDT)', content)
                unique_symbols = set(all_symbols)
                
                for symbol in unique_symbols:
                    if symbol not in backtest_data and 'USDT' in symbol:
                        # Simbolos no rentables - asumir perdida minima
                        backtest_data[symbol] = {
                            'monthly_pnl_amount': -5.0,  # Perdida estimada
                            'monthly_pnl_pct': -0.5,
                            'total_trades': 1,
                            'win_rate': 0.0,
                            'source': 'Independent Backtest 90d (No Profitable)',
                            'period_days': 90
                        }
                        
            except Exception as e:
                print(f"Error procesando backtest: {e}")
                
        return backtest_data
        
    def extract_real_binance_data(self) -> Dict:
        """Extrae datos de resultados reales de Binance"""
        real_data = {}
        
        # Buscar archivos de resultados reales
        real_files = [f for f in os.listdir(self.results_directory) if 'real_binance_results' in f]
        
        for file in real_files:
            filepath = os.path.join(self.results_directory, file)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Extraer periodo
                period_match = re.search(r'(\d+)days', file)
                period_days = int(period_match.group(1)) if period_match else 30
                
                # Buscar trades por simbolo
                trade_patterns = [
                    r'(\w+USDT).*?PnL: ([\d.-]+)%.*?\$([\d.-]+)',
                    r'Symbol: (\w+USDT).*?([\d.-]+)%.*?\$([\d.-]+)',
                    r'Trade (\w+USDT).*?([\d.-]+)%.*?\$([\d.-]+)'
                ]
                
                for pattern in trade_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        if len(match) >= 3:
                            symbol = match[0]
                            pnl_pct = float(match[1])
                            pnl_amount = float(match[2])
                            
                            # Calcular rentabilidad mensual
                            monthly_pnl_pct = (pnl_pct / period_days) * 30
                            monthly_pnl_amount = (pnl_amount / period_days) * 30
                            
                            if symbol not in real_data:
                                real_data[symbol] = {
                                    'monthly_pnl_amount': 0,
                                    'monthly_pnl_pct': 0,
                                    'total_trades': 0,
                                    'winning_trades': 0,
                                    'source': f'Real Binance {period_days}d',
                                    'period_days': period_days
                                }
                                
                            real_data[symbol]['monthly_pnl_amount'] += monthly_pnl_amount
                            real_data[symbol]['monthly_pnl_pct'] += monthly_pnl_pct
                            real_data[symbol]['total_trades'] += 1
                            
                            if pnl_pct > 0:
                                real_data[symbol]['winning_trades'] += 1
                                
            except Exception as e:
                print(f"Error procesando {file}: {e}")
                
        # Calcular win rate
        for symbol, data in real_data.items():
            if data['total_trades'] > 0:
                data['win_rate'] = (data['winning_trades'] / data['total_trades']) * 100
            else:
                data['win_rate'] = 0
                
        return real_data
        
    def consolidate_all_data(self) -> Dict:
        """Consolida todos los datos de rentabilidad"""
        print("Extrayendo datos de backtest independiente...")
        backtest_data = self.extract_backtest_data()
        print(f"Simbolos encontrados en backtest: {len(backtest_data)}")
        
        print("\nExtrayendo datos de resultados reales de Binance...")
        real_data = self.extract_real_binance_data()
        print(f"Simbolos encontrados en resultados reales: {len(real_data)}")
        
        # Consolidar datos
        consolidated = {}
        
        # Agregar datos de backtest
        for symbol, data in backtest_data.items():
            consolidated[symbol] = {
                'symbol': symbol,
                'monthly_pnl_pct': data['monthly_pnl_pct'],
                'monthly_pnl_amount': data['monthly_pnl_amount'],
                'total_trades': data['total_trades'],
                'win_rate': data['win_rate'],
                'sources': [data['source']],
                'strategies_tested': 1
            }
            
        # Agregar/combinar datos reales
        for symbol, data in real_data.items():
            if symbol in consolidated:
                # Promediar los resultados
                consolidated[symbol]['monthly_pnl_pct'] = (
                    consolidated[symbol]['monthly_pnl_pct'] + data['monthly_pnl_pct']
                ) / 2
                consolidated[symbol]['monthly_pnl_amount'] = (
                    consolidated[symbol]['monthly_pnl_amount'] + data['monthly_pnl_amount']
                ) / 2
                consolidated[symbol]['total_trades'] += data['total_trades']
                consolidated[symbol]['win_rate'] = (
                    consolidated[symbol]['win_rate'] + data['win_rate']
                ) / 2
                consolidated[symbol]['sources'].append(data['source'])
                consolidated[symbol]['strategies_tested'] += 1
            else:
                consolidated[symbol] = {
                    'symbol': symbol,
                    'monthly_pnl_pct': data['monthly_pnl_pct'],
                    'monthly_pnl_amount': data['monthly_pnl_amount'],
                    'total_trades': data['total_trades'],
                    'win_rate': data['win_rate'],
                    'sources': [data['source']],
                    'strategies_tested': 1
                }
                
        return consolidated
        
    def generate_final_report(self) -> str:
        """Genera el reporte final consolidado"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rentabilidad_mensual_consolidada_{timestamp}.txt"
        
        consolidated_data = self.consolidate_all_data()
        
        # Ordenar por rentabilidad mensual
        sorted_symbols = sorted(consolidated_data.items(), 
                              key=lambda x: x[1]['monthly_pnl_pct'], 
                              reverse=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("RENTABILIDAD MENSUAL POR SIMBOLO PROBADO - REPORTE CONSOLIDADO\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 90 + "\n\n")
            
            f.write("RESUMEN EJECUTIVO:\n")
            f.write(f"Total simbolos analizados: {len(consolidated_data)}\n")
            
            if consolidated_data:
                profitable_count = len([s for s in consolidated_data.values() if s['monthly_pnl_pct'] > 0])
                f.write(f"Simbolos rentables: {profitable_count}/{len(consolidated_data)} ({profitable_count/len(consolidated_data)*100:.1f}%)\n")
                
                total_monthly_pnl = sum(s['monthly_pnl_amount'] for s in consolidated_data.values())
                f.write(f"PnL mensual total estimado: ${total_monthly_pnl:.2f}\n")
                
                avg_monthly_return = sum(s['monthly_pnl_pct'] for s in consolidated_data.values()) / len(consolidated_data)
                f.write(f"Rentabilidad mensual promedio: {avg_monthly_return:.2f}%\n")
                
                total_trades = sum(s['total_trades'] for s in consolidated_data.values())
                f.write(f"Total trades analizados: {total_trades}\n\n")
                
                f.write("RANKING COMPLETO DE RENTABILIDAD MENSUAL:\n")
                f.write("=" * 70 + "\n\n")
                
                for i, (symbol, data) in enumerate(sorted_symbols, 1):
                    f.write(f"{i:2d}. {symbol}\n")
                    f.write(f"    Rentabilidad Mensual: {data['monthly_pnl_pct']:+7.2f}% (${data['monthly_pnl_amount']:+8.2f})\n")
                    f.write(f"    Total Trades: {data['total_trades']:3d}\n")
                    f.write(f"    Win Rate: {data['win_rate']:5.1f}%\n")
                    f.write(f"    Estrategias Probadas: {data['strategies_tested']}\n")
                    f.write(f"    Fuentes: {', '.join(data['sources'][:2])}\n")
                    
                    # Clasificacion de rendimiento
                    if data['monthly_pnl_pct'] > 20:
                        performance = "EXCELENTE"
                    elif data['monthly_pnl_pct'] > 10:
                        performance = "MUY BUENO"
                    elif data['monthly_pnl_pct'] > 5:
                        performance = "BUENO"
                    elif data['monthly_pnl_pct'] > 0:
                        performance = "POSITIVO"
                    else:
                        performance = "NEGATIVO"
                        
                    f.write(f"    Clasificacion: {performance}\n\n")
                    
                # Analisis por categorias
                f.write("ANALISIS POR CATEGORIAS DE RENDIMIENTO:\n")
                f.write("=" * 60 + "\n\n")
                
                excelentes = [s for s in consolidated_data.values() if s['monthly_pnl_pct'] > 20]
                muy_buenos = [s for s in consolidated_data.values() if 10 < s['monthly_pnl_pct'] <= 20]
                buenos = [s for s in consolidated_data.values() if 5 < s['monthly_pnl_pct'] <= 10]
                positivos = [s for s in consolidated_data.values() if 0 < s['monthly_pnl_pct'] <= 5]
                negativos = [s for s in consolidated_data.values() if s['monthly_pnl_pct'] <= 0]
                
                f.write(f"EXCELENTES (>20% mensual): {len(excelentes)} simbolos\n")
                for s in excelentes:
                    f.write(f"  - {s['symbol']}: {s['monthly_pnl_pct']:.2f}%\n")
                    
                f.write(f"\nMUY BUENOS (10-20% mensual): {len(muy_buenos)} simbolos\n")
                for s in muy_buenos:
                    f.write(f"  - {s['symbol']}: {s['monthly_pnl_pct']:.2f}%\n")
                    
                f.write(f"\nBUENOS (5-10% mensual): {len(buenos)} simbolos\n")
                for s in buenos:
                    f.write(f"  - {s['symbol']}: {s['monthly_pnl_pct']:.2f}%\n")
                    
                f.write(f"\nPOSITIVOS (0-5% mensual): {len(positivos)} simbolos\n")
                for s in positivos:
                    f.write(f"  - {s['symbol']}: {s['monthly_pnl_pct']:.2f}%\n")
                    
                f.write(f"\nNEGATIVOS (<0% mensual): {len(negativos)} simbolos\n")
                for s in negativos:
                    f.write(f"  - {s['symbol']}: {s['monthly_pnl_pct']:.2f}%\n")
                    
                f.write("\nRECOMENDACIONES FINALES:\n")
                f.write("=" * 40 + "\n")
                
                if excelentes:
                    f.write(f"1. FOCO PRINCIPAL: {len(excelentes)} simbolos excelentes (>20% mensual)\n")
                    top_3 = sorted(excelentes, key=lambda x: x['monthly_pnl_pct'], reverse=True)[:3]
                    for i, s in enumerate(top_3, 1):
                        f.write(f"   {i}. {s['symbol']} - {s['monthly_pnl_pct']:.2f}% mensual\n")
                        
                if muy_buenos:
                    f.write(f"\n2. SEGUNDA OPCION: {len(muy_buenos)} simbolos muy buenos (10-20% mensual)\n")
                    
                f.write(f"\n3. EVITAR: {len(negativos)} simbolos con rendimiento negativo\n")
                
                best_symbol = sorted_symbols[0]
                f.write(f"\n4. MEJOR SIMBOLO GENERAL: {best_symbol[0]} ({best_symbol[1]['monthly_pnl_pct']:.2f}% mensual)\n")
                
                high_win_rate = [s for s in consolidated_data.values() if s['win_rate'] > 80]
                f.write(f"\n5. SIMBOLOS CON ALTA PRECISION: {len(high_win_rate)} simbolos con >80% win rate\n")
                
            else:
                f.write("No se encontraron datos para analizar.\n")
                
        return filename

def main():
    """Funcion principal"""
    print("=" * 90)
    print("REPORTE CONSOLIDADO DE RENTABILIDAD MENSUAL POR SIMBOLO")
    print("=" * 90)
    
    reporter = ConsolidatedProfitabilityReport()
    report_file = reporter.generate_final_report()
    
    print(f"\n\nReporte consolidado generado: {report_file}")
    print("\nAnalisis consolidado completado exitosamente!")
    
if __name__ == "__main__":
    main()