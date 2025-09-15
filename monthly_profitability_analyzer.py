#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analizador de Rentabilidad Mensual por Simbolo
Analiza todos los archivos de resultados para calcular rentabilidad mensual
"""

import os
import re
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json

class MonthlyProfitabilityAnalyzer:
    """Analizador de rentabilidad mensual por simbolo"""
    
    def __init__(self, results_directory: str = "."):
        self.results_directory = results_directory
        self.symbol_data = {}
        self.strategy_results = {}
        
    def find_result_files(self) -> List[str]:
        """Encuentra todos los archivos de resultados"""
        result_files = []
        
        # Patrones de archivos de resultados
        patterns = [
            r'.*_results_.*\.txt$',
            r'.*_backtest_.*\.txt$',
            r'.*_analysis_.*\.txt$',
            r'real_binance_results_.*\.txt$',
            r'nas100_results_.*\.txt$'
        ]
        
        for file in os.listdir(self.results_directory):
            for pattern in patterns:
                if re.match(pattern, file):
                    result_files.append(file)
                    break
                    
        return sorted(result_files)
        
    def parse_real_binance_results(self, filepath: str) -> Dict:
        """Parsea archivos de resultados de Binance reales"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Extraer informacion basica
            strategy_match = re.search(r'Estrategia: (.+)', content)
            period_match = re.search(r'Periodo: (\d+) dias', content)
            return_match = re.search(r'Retorno total: ([\d.-]+)%', content)
            trades_match = re.search(r'Total trades: (\d+)', content)
            
            strategy_name = strategy_match.group(1) if strategy_match else "Unknown"
            period_days = int(period_match.group(1)) if period_match else 30
            total_return = float(return_match.group(1)) if return_match else 0.0
            total_trades = int(trades_match.group(1)) if trades_match else 0
            
            # Extraer trades por simbolo
            symbol_trades = {}
            trade_pattern = r'(\w+USDT).*?PnL: ([\d.-]+)%.*?\$([\d.-]+)'
            trades = re.findall(trade_pattern, content)
            
            for symbol, pnl_pct, pnl_amount in trades:
                if symbol not in symbol_trades:
                    symbol_trades[symbol] = {
                        'trades': 0,
                        'total_pnl_pct': 0.0,
                        'total_pnl_amount': 0.0,
                        'winning_trades': 0
                    }
                    
                symbol_trades[symbol]['trades'] += 1
                symbol_trades[symbol]['total_pnl_pct'] += float(pnl_pct)
                symbol_trades[symbol]['total_pnl_amount'] += float(pnl_amount)
                
                if float(pnl_pct) > 0:
                    symbol_trades[symbol]['winning_trades'] += 1
                    
            # Calcular rentabilidad mensual
            monthly_return = (total_return / period_days) * 30
            
            return {
                'strategy': strategy_name,
                'period_days': period_days,
                'total_return': total_return,
                'monthly_return': monthly_return,
                'total_trades': total_trades,
                'symbol_trades': symbol_trades,
                'file': filepath
            }
            
        except Exception as e:
            print(f"Error parseando {filepath}: {e}")
            return None
            
    def parse_backtest_results(self, filepath: str) -> Dict:
        """Parsea archivos de backtesting"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Extraer informacion de simbolos rentables
            symbol_data = {}
            
            # Buscar seccion de simbolos rentables
            rentable_section = re.search(r'RANKING SIMBOLOS RENTABLES:(.*?)(?=\n\n|$)', content, re.DOTALL)
            if rentable_section:
                lines = rentable_section.group(1).strip().split('\n')
                for line in lines:
                    symbol_match = re.search(r'(\w+USDT).*?PnL: \$([\d.-]+).*?Win Rate: ([\d.]+)%.*?Trades: (\d+)', line)
                    if symbol_match:
                        symbol, pnl, win_rate, trades = symbol_match.groups()
                        symbol_data[symbol] = {
                            'pnl_amount': float(pnl),
                            'win_rate': float(win_rate),
                            'trades': int(trades)
                        }
                        
            # Extraer periodo
            period_match = re.search(r'(\d+) dias', filepath)
            period_days = int(period_match.group(1)) if period_match else 90
            
            return {
                'strategy': 'Independent Backtest',
                'period_days': period_days,
                'symbol_data': symbol_data,
                'file': filepath
            }
            
        except Exception as e:
            print(f"Error parseando {filepath}: {e}")
            return None
            
    def parse_strategy_results(self, filepath: str) -> Dict:
        """Parsea archivos de resultados de estrategias"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Extraer nombre de estrategia del archivo
            strategy_name = filepath.replace('_results_', '_').replace('.txt', '')
            strategy_name = re.sub(r'_\d{8}_\d{6}', '', strategy_name)
            
            # Buscar metricas generales
            return_match = re.search(r'Retorno total: ([\d.-]+)%', content)
            trades_match = re.search(r'Total trades: (\d+)', content)
            win_rate_match = re.search(r'Win rate: ([\d.]+)%', content)
            
            total_return = float(return_match.group(1)) if return_match else 0.0
            total_trades = int(trades_match.group(1)) if trades_match else 0
            win_rate = float(win_rate_match.group(1)) if win_rate_match else 0.0
            
            # Asumir periodo de 30 dias si no se especifica
            period_days = 30
            monthly_return = total_return  # Ya es mensual
            
            return {
                'strategy': strategy_name,
                'period_days': period_days,
                'total_return': total_return,
                'monthly_return': monthly_return,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'file': filepath
            }
            
        except Exception as e:
            print(f"Error parseando {filepath}: {e}")
            return None
            
    def analyze_all_results(self) -> Dict:
        """Analiza todos los archivos de resultados"""
        result_files = self.find_result_files()
        print(f"Encontrados {len(result_files)} archivos de resultados")
        
        all_results = []
        symbol_summary = {}
        
        for file in result_files:
            filepath = os.path.join(self.results_directory, file)
            print(f"\nAnalizando: {file}")
            
            result = None
            
            # Determinar tipo de archivo y parsear apropiadamente
            if 'real_binance_results' in file:
                result = self.parse_real_binance_results(filepath)
            elif 'backtest' in file:
                result = self.parse_backtest_results(filepath)
            elif '_results_' in file:
                result = self.parse_strategy_results(filepath)
                
            if result:
                all_results.append(result)
                
                # Agregar a resumen por simbolo
                if 'symbol_trades' in result:
                    for symbol, data in result['symbol_trades'].items():
                        if symbol not in symbol_summary:
                            symbol_summary[symbol] = {
                                'total_trades': 0,
                                'total_pnl': 0.0,
                                'strategies': [],
                                'monthly_returns': []
                            }
                            
                        symbol_summary[symbol]['total_trades'] += data['trades']
                        symbol_summary[symbol]['total_pnl'] += data['total_pnl_amount']
                        symbol_summary[symbol]['strategies'].append(result['strategy'])
                        
                        # Calcular rentabilidad mensual del simbolo
                        if data['trades'] > 0:
                            monthly_pnl = (data['total_pnl_pct'] / result['period_days']) * 30
                            symbol_summary[symbol]['monthly_returns'].append(monthly_pnl)
                            
                elif 'symbol_data' in result:
                    for symbol, data in result['symbol_data'].items():
                        if symbol not in symbol_summary:
                            symbol_summary[symbol] = {
                                'total_trades': 0,
                                'total_pnl': 0.0,
                                'strategies': [],
                                'monthly_returns': []
                            }
                            
                        symbol_summary[symbol]['total_trades'] += data['trades']
                        symbol_summary[symbol]['total_pnl'] += data['pnl_amount']
                        symbol_summary[symbol]['strategies'].append(result['strategy'])
                        
                        # Calcular rentabilidad mensual estimada
                        if data['trades'] > 0:
                            monthly_pnl = (data['pnl_amount'] / 1000) * 100 * (30 / result['period_days'])
                            symbol_summary[symbol]['monthly_returns'].append(monthly_pnl)
                            
        return {
            'all_results': all_results,
            'symbol_summary': symbol_summary,
            'total_files': len(result_files)
        }
        
    def calculate_monthly_profitability(self, analysis_results: Dict) -> pd.DataFrame:
        """Calcula rentabilidad mensual por simbolo"""
        symbol_summary = analysis_results['symbol_summary']
        
        monthly_data = []
        
        for symbol, data in symbol_summary.items():
            if data['monthly_returns']:
                avg_monthly_return = np.mean(data['monthly_returns'])
                max_monthly_return = max(data['monthly_returns'])
                min_monthly_return = min(data['monthly_returns'])
                
                monthly_data.append({
                    'Simbolo': symbol,
                    'Rentabilidad_Mensual_Promedio': f"{avg_monthly_return:.2f}%",
                    'Rentabilidad_Mensual_Maxima': f"{max_monthly_return:.2f}%",
                    'Rentabilidad_Mensual_Minima': f"{min_monthly_return:.2f}%",
                    'Total_Trades': data['total_trades'],
                    'PnL_Total': f"${data['total_pnl']:.2f}",
                    'Estrategias_Probadas': len(set(data['strategies'])),
                    'Estrategias': ', '.join(set(data['strategies'])[:3])  # Primeras 3
                })
                
        df = pd.DataFrame(monthly_data)
        
        # Ordenar por rentabilidad promedio
        if not df.empty:
            df['Sort_Value'] = df['Rentabilidad_Mensual_Promedio'].str.replace('%', '').astype(float)
            df = df.sort_values('Sort_Value', ascending=False).drop('Sort_Value', axis=1)
            
        return df
        
    def generate_monthly_report(self) -> str:
        """Genera reporte de rentabilidad mensual"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"monthly_profitability_report_{timestamp}.txt"
        
        # Analizar todos los resultados
        analysis_results = self.analyze_all_results()
        monthly_df = self.calculate_monthly_profitability(analysis_results)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("REPORTE DE RENTABILIDAD MENSUAL POR SIMBOLO\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"RESUMEN EJECUTIVO:\n")
            f.write(f"Archivos analizados: {analysis_results['total_files']}\n")
            f.write(f"Simbolos encontrados: {len(analysis_results['symbol_summary'])}\n")
            f.write(f"Estrategias analizadas: {len(analysis_results['all_results'])}\n\n")
            
            if not monthly_df.empty:
                f.write("RENTABILIDAD MENSUAL POR SIMBOLO:\n")
                f.write("=" * 60 + "\n")
                
                for i, row in monthly_df.iterrows():
                    f.write(f"\n{i+1:2d}. {row['Simbolo']:10s}\n")
                    f.write(f"    Rentabilidad Mensual Promedio: {row['Rentabilidad_Mensual_Promedio']}\n")
                    f.write(f"    Rentabilidad Mensual Maxima:   {row['Rentabilidad_Mensual_Maxima']}\n")
                    f.write(f"    Rentabilidad Mensual Minima:   {row['Rentabilidad_Mensual_Minima']}\n")
                    f.write(f"    Total Trades: {row['Total_Trades']}\n")
                    f.write(f"    PnL Total: {row['PnL_Total']}\n")
                    f.write(f"    Estrategias Probadas: {row['Estrategias_Probadas']}\n")
                    f.write(f"    Principales Estrategias: {row['Estrategias']}\n")
                    
                # Top 5 simbolos
                f.write(f"\nTOP 5 SIMBOLOS MAS RENTABLES (MENSUAL):\n")
                f.write("=" * 50 + "\n")
                
                for i, row in monthly_df.head(5).iterrows():
                    f.write(f"{i+1}. {row['Simbolo']} - {row['Rentabilidad_Mensual_Promedio']} promedio\n")
                    
            # Detalle por estrategia
            f.write(f"\nDETALLE POR ESTRATEGIA:\n")
            f.write("=" * 40 + "\n")
            
            for result in analysis_results['all_results']:
                f.write(f"\n{result['strategy']}:\n")
                f.write(f"  Archivo: {result['file']}\n")
                f.write(f"  Periodo: {result['period_days']} dias\n")
                
                if 'monthly_return' in result:
                    f.write(f"  Rentabilidad Mensual: {result['monthly_return']:.2f}%\n")
                if 'total_trades' in result:
                    f.write(f"  Total Trades: {result['total_trades']}\n")
                if 'win_rate' in result:
                    f.write(f"  Win Rate: {result['win_rate']:.1f}%\n")
                    
            f.write(f"\nCONCLUSIONES:\n")
            f.write("=" * 30 + "\n")
            
            if not monthly_df.empty:
                best_symbol = monthly_df.iloc[0]
                f.write(f"1. Simbolo mas rentable: {best_symbol['Simbolo']} ({best_symbol['Rentabilidad_Mensual_Promedio']})\n")
                f.write(f"2. Total de simbolos analizados: {len(monthly_df)}\n")
                f.write(f"3. Rango de rentabilidad: {monthly_df.iloc[-1]['Rentabilidad_Mensual_Promedio']} a {monthly_df.iloc[0]['Rentabilidad_Mensual_Promedio']}\n")
                
                profitable_symbols = len(monthly_df[monthly_df['Rentabilidad_Mensual_Promedio'].str.replace('%', '').astype(float) > 0])
                f.write(f"4. Simbolos rentables: {profitable_symbols}/{len(monthly_df)} ({profitable_symbols/len(monthly_df)*100:.1f}%)\n")
            else:
                f.write("No se encontraron datos suficientes para calcular rentabilidad mensual.\n")
                
        return filename

def main():
    """Funcion principal"""
    print("=" * 80)
    print("ANALIZADOR DE RENTABILIDAD MENSUAL POR SIMBOLO")
    print("=" * 80)
    
    analyzer = MonthlyProfitabilityAnalyzer()
    report_file = analyzer.generate_monthly_report()
    
    print(f"\nReporte generado: {report_file}")
    print("\nAnalisis completado exitosamente!")
    
if __name__ == "__main__":
    main()