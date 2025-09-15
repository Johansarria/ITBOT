#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extractor de Rentabilidad por Simbolo
Analiza archivos de resultados para extraer rentabilidad especifica por simbolo
"""

import os
import re
from datetime import datetime
from typing import Dict, List

class SymbolProfitabilityExtractor:
    """Extractor de rentabilidad por simbolo"""
    
    def __init__(self, results_directory: str = "."):
        self.results_directory = results_directory
        self.symbol_data = {}
        
    def extract_from_real_binance_results(self, filepath: str) -> Dict:
        """Extrae datos de archivos real_binance_results"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            print(f"\nAnalizando: {os.path.basename(filepath)}")
            
            # Extraer informacion del periodo
            period_match = re.search(r'(\d+)days', filepath)
            period_days = int(period_match.group(1)) if period_match else 30
            
            # Buscar trades individuales con simbolos
            trades_data = {}
            
            # Patron para trades con simbolo, fecha, precio, PnL
            trade_patterns = [
                r'(\w+USDT).*?Entrada: ([\d.-]+).*?Salida: ([\d.-]+).*?PnL: ([\d.-]+)%.*?\$([\d.-]+)',
                r'(\w+USDT).*?Entry: ([\d.-]+).*?Exit: ([\d.-]+).*?PnL: ([\d.-]+)%.*?\$([\d.-]+)',
                r'Trade (\w+USDT).*?PnL: ([\d.-]+)%.*?\$([\d.-]+)',
                r'(\w+USDT).*?PnL: ([\d.-]+)%.*?Amount: \$([\d.-]+)',
                r'Symbol: (\w+USDT).*?PnL: ([\d.-]+)%.*?\$([\d.-]+)'
            ]
            
            for pattern in trade_patterns:
                matches = re.findall(pattern, content, re.DOTALL)
                for match in matches:
                    if len(match) >= 3:
                        symbol = match[0]
                        if len(match) == 5:  # Patron completo
                            pnl_pct = float(match[3])
                            pnl_amount = float(match[4])
                        else:  # Patron simplificado
                            pnl_pct = float(match[1])
                            pnl_amount = float(match[2])
                            
                        if symbol not in trades_data:
                            trades_data[symbol] = {
                                'trades': [],
                                'total_pnl_pct': 0.0,
                                'total_pnl_amount': 0.0,
                                'winning_trades': 0,
                                'total_trades': 0
                            }
                            
                        trades_data[symbol]['trades'].append({
                            'pnl_pct': pnl_pct,
                            'pnl_amount': pnl_amount
                        })
                        trades_data[symbol]['total_pnl_pct'] += pnl_pct
                        trades_data[symbol]['total_pnl_amount'] += pnl_amount
                        trades_data[symbol]['total_trades'] += 1
                        
                        if pnl_pct > 0:
                            trades_data[symbol]['winning_trades'] += 1
                            
            # Si no encontramos trades individuales, buscar resumen por simbolo
            if not trades_data:
                summary_patterns = [
                    r'(\w+USDT):.*?([\d.-]+)%.*?\$([\d.-]+)',
                    r'(\w+USDT).*?Total: ([\d.-]+)%.*?\$([\d.-]+)',
                    r'Simbolo: (\w+USDT).*?Rentabilidad: ([\d.-]+)%.*?Monto: \$([\d.-]+)'
                ]
                
                for pattern in summary_patterns:
                    matches = re.findall(pattern, content)
                    for symbol, pnl_pct, pnl_amount in matches:
                        if symbol not in trades_data:
                            trades_data[symbol] = {
                                'trades': [],
                                'total_pnl_pct': float(pnl_pct),
                                'total_pnl_amount': float(pnl_amount),
                                'winning_trades': 1 if float(pnl_pct) > 0 else 0,
                                'total_trades': 1
                            }
                            
            print(f"  Simbolos encontrados: {len(trades_data)}")
            for symbol, data in trades_data.items():
                print(f"    {symbol}: {data['total_trades']} trades, {data['total_pnl_pct']:.2f}% PnL")
                
            return {
                'file': filepath,
                'period_days': period_days,
                'symbols': trades_data
            }
            
        except Exception as e:
            print(f"Error procesando {filepath}: {e}")
            return None
            
    def extract_from_backtest_results(self, filepath: str) -> Dict:
        """Extrae datos de archivos de backtest"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            print(f"\nAnalizando: {os.path.basename(filepath)}")
            
            # Extraer periodo
            period_match = re.search(r'(\d+) dias', filepath)
            period_days = int(period_match.group(1)) if period_match else 90
            
            trades_data = {}
            
            # Buscar seccion de simbolos rentables
            rentable_section = re.search(r'RANKING SIMBOLOS RENTABLES:(.*?)(?=\n\n|DETALLE|$)', content, re.DOTALL)
            if rentable_section:
                lines = rentable_section.group(1).strip().split('\n')
                for line in lines:
                    # Patron: BTCUSDT - PnL: $23.60 (1.18%) | Win Rate: 100.0% | Trades: 1
                    symbol_match = re.search(r'(\w+USDT).*?PnL: \$([\d.-]+).*?\(([\d.-]+)%\).*?Win Rate: ([\d.]+)%.*?Trades: (\d+)', line)
                    if symbol_match:
                        symbol, pnl_amount, pnl_pct, win_rate, trades = symbol_match.groups()
                        trades_data[symbol] = {
                            'total_pnl_amount': float(pnl_amount),
                            'total_pnl_pct': float(pnl_pct),
                            'win_rate': float(win_rate),
                            'total_trades': int(trades),
                            'winning_trades': int(int(trades) * float(win_rate) / 100)
                        }
                        
            # Buscar trades individuales en detalle
            detail_section = re.search(r'DETALLE DE TRADES:(.*?)(?=\n\n|$)', content, re.DOTALL)
            if detail_section:
                detail_lines = detail_section.group(1).strip().split('\n')
                current_symbol = None
                
                for line in detail_lines:
                    # Detectar simbolo
                    symbol_header = re.search(r'^(\w+USDT):', line)
                    if symbol_header:
                        current_symbol = symbol_header.group(1)
                        if current_symbol not in trades_data:
                            trades_data[current_symbol] = {
                                'total_pnl_amount': 0.0,
                                'total_pnl_pct': 0.0,
                                'total_trades': 0,
                                'winning_trades': 0
                            }
                    
                    # Detectar trade individual
                    elif current_symbol and 'PnL:' in line:
                        trade_match = re.search(r'PnL: ([\d.-]+)%.*?\$([\d.-]+)', line)
                        if trade_match:
                            pnl_pct, pnl_amount = trade_match.groups()
                            trades_data[current_symbol]['total_pnl_pct'] += float(pnl_pct)
                            trades_data[current_symbol]['total_pnl_amount'] += float(pnl_amount)
                            trades_data[current_symbol]['total_trades'] += 1
                            
                            if float(pnl_pct) > 0:
                                trades_data[current_symbol]['winning_trades'] += 1
                                
            print(f"  Simbolos encontrados: {len(trades_data)}")
            for symbol, data in trades_data.items():
                print(f"    {symbol}: {data['total_trades']} trades, ${data['total_pnl_amount']:.2f} PnL")
                
            return {
                'file': filepath,
                'period_days': period_days,
                'symbols': trades_data
            }
            
        except Exception as e:
            print(f"Error procesando {filepath}: {e}")
            return None
            
    def calculate_monthly_profitability_by_symbol(self) -> Dict:
        """Calcula rentabilidad mensual por simbolo"""
        # Buscar archivos relevantes
        relevant_files = []
        
        for file in os.listdir(self.results_directory):
            if any(pattern in file for pattern in ['real_binance_results', 'backtest', 'independent']):
                if file.endswith('.txt'):
                    relevant_files.append(file)
                    
        print(f"Archivos relevantes encontrados: {len(relevant_files)}")
        
        all_symbol_data = {}
        
        for file in relevant_files:
            filepath = os.path.join(self.results_directory, file)
            
            result = None
            if 'real_binance_results' in file:
                result = self.extract_from_real_binance_results(filepath)
            elif 'backtest' in file or 'independent' in file:
                result = self.extract_from_backtest_results(filepath)
                
            if result and result['symbols']:
                for symbol, data in result['symbols'].items():
                    if symbol not in all_symbol_data:
                        all_symbol_data[symbol] = {
                            'total_pnl_amount': 0.0,
                            'total_pnl_pct': 0.0,
                            'total_trades': 0,
                            'winning_trades': 0,
                            'strategies': [],
                            'periods': []
                        }
                        
                    all_symbol_data[symbol]['total_pnl_amount'] += data.get('total_pnl_amount', 0)
                    all_symbol_data[symbol]['total_pnl_pct'] += data.get('total_pnl_pct', 0)
                    all_symbol_data[symbol]['total_trades'] += data.get('total_trades', 0)
                    all_symbol_data[symbol]['winning_trades'] += data.get('winning_trades', 0)
                    all_symbol_data[symbol]['strategies'].append(os.path.basename(file))
                    all_symbol_data[symbol]['periods'].append(result['period_days'])
                    
        # Calcular rentabilidad mensual
        monthly_profitability = {}
        
        for symbol, data in all_symbol_data.items():
            if data['total_trades'] > 0:
                # Calcular rentabilidad mensual promedio
                avg_period = sum(data['periods']) / len(data['periods']) if data['periods'] else 30
                monthly_pnl_pct = (data['total_pnl_pct'] / avg_period) * 30
                monthly_pnl_amount = (data['total_pnl_amount'] / avg_period) * 30
                
                win_rate = (data['winning_trades'] / data['total_trades']) * 100
                
                monthly_profitability[symbol] = {
                    'monthly_pnl_pct': monthly_pnl_pct,
                    'monthly_pnl_amount': monthly_pnl_amount,
                    'total_trades': data['total_trades'],
                    'win_rate': win_rate,
                    'strategies_count': len(set(data['strategies'])),
                    'avg_period_days': avg_period
                }
                
        return monthly_profitability
        
    def generate_symbol_profitability_report(self) -> str:
        """Genera reporte de rentabilidad por simbolo"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"symbol_monthly_profitability_{timestamp}.txt"
        
        monthly_data = self.calculate_monthly_profitability_by_symbol()
        
        # Ordenar por rentabilidad mensual
        sorted_symbols = sorted(monthly_data.items(), 
                              key=lambda x: x[1]['monthly_pnl_pct'], 
                              reverse=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("RENTABILIDAD MENSUAL POR SIMBOLO PROBADO\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"RESUMEN EJECUTIVO:\n")
            f.write(f"Simbolos analizados: {len(monthly_data)}\n")
            
            if monthly_data:
                profitable_symbols = len([s for s in monthly_data.values() if s['monthly_pnl_pct'] > 0])
                f.write(f"Simbolos rentables: {profitable_symbols}/{len(monthly_data)} ({profitable_symbols/len(monthly_data)*100:.1f}%)\n")
                
                total_monthly_pnl = sum(s['monthly_pnl_amount'] for s in monthly_data.values())
                f.write(f"PnL mensual total estimado: ${total_monthly_pnl:.2f}\n")
                f.write(f"Total trades analizados: {sum(s['total_trades'] for s in monthly_data.values())}\n\n")
                
                f.write("RANKING DE RENTABILIDAD MENSUAL:\n")
                f.write("=" * 60 + "\n\n")
                
                for i, (symbol, data) in enumerate(sorted_symbols, 1):
                    f.write(f"{i:2d}. {symbol}\n")
                    f.write(f"    Rentabilidad Mensual: {data['monthly_pnl_pct']:+.2f}% (${data['monthly_pnl_amount']:+.2f})\n")
                    f.write(f"    Total Trades: {data['total_trades']}\n")
                    f.write(f"    Win Rate: {data['win_rate']:.1f}%\n")
                    f.write(f"    Estrategias Probadas: {data['strategies_count']}\n")
                    f.write(f"    Periodo Promedio: {data['avg_period_days']:.0f} dias\n\n")
                    
                # Top 5 mas rentables
                f.write("TOP 5 SIMBOLOS MAS RENTABLES (MENSUAL):\n")
                f.write("=" * 50 + "\n")
                
                for i, (symbol, data) in enumerate(sorted_symbols[:5], 1):
                    f.write(f"{i}. {symbol}: {data['monthly_pnl_pct']:+.2f}% mensual\n")
                    
                # Bottom 5 menos rentables
                f.write("\nSIMBOLOS MENOS RENTABLES:\n")
                f.write("=" * 40 + "\n")
                
                for i, (symbol, data) in enumerate(sorted_symbols[-5:], 1):
                    f.write(f"{i}. {symbol}: {data['monthly_pnl_pct']:+.2f}% mensual\n")
                    
                f.write("\nCONCLUSIONES Y RECOMENDACIONES:\n")
                f.write("=" * 50 + "\n")
                
                best_symbol = sorted_symbols[0]
                worst_symbol = sorted_symbols[-1]
                
                f.write(f"1. Simbolo mas rentable: {best_symbol[0]} ({best_symbol[1]['monthly_pnl_pct']:+.2f}% mensual)\n")
                f.write(f"2. Simbolo menos rentable: {worst_symbol[0]} ({worst_symbol[1]['monthly_pnl_pct']:+.2f}% mensual)\n")
                f.write(f"3. Rango de rentabilidad: {worst_symbol[1]['monthly_pnl_pct']:.2f}% a {best_symbol[1]['monthly_pnl_pct']:.2f}%\n")
                
                avg_monthly_return = sum(s['monthly_pnl_pct'] for s in monthly_data.values()) / len(monthly_data)
                f.write(f"4. Rentabilidad mensual promedio: {avg_monthly_return:.2f}%\n")
                
                high_performers = [s for s in monthly_data.values() if s['monthly_pnl_pct'] > 5]
                f.write(f"5. Simbolos con >5% mensual: {len(high_performers)} simbolos\n")
                
            else:
                f.write("No se encontraron datos de simbolos para analizar.\n")
                
        return filename

def main():
    """Funcion principal"""
    print("=" * 80)
    print("EXTRACTOR DE RENTABILIDAD MENSUAL POR SIMBOLO")
    print("=" * 80)
    
    extractor = SymbolProfitabilityExtractor()
    report_file = extractor.generate_symbol_profitability_report()
    
    print(f"\n\nReporte generado: {report_file}")
    print("\nAnalisis completado exitosamente!")
    
if __name__ == "__main__":
    main()