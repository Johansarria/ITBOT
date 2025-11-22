#!/usr/bin/env python3
"""
Evaluador de Disponibilidad Multi-Asset para SICAR
Evalúa la disponibilidad de índices, forex y commodities en el sistema de datos reales
"""

import sys
import os
import json
from datetime import datetime, timedelta
import pandas as pd

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from real_data_system import RealDataSystem

class MultiAssetEvaluator:
    def __init__(self):
        self.data_system = RealDataSystem()
        self.results = {
            'evaluation_timestamp': datetime.now().isoformat(),
            'indices': {},
            'forex_majors': {},
            'commodities': {},
            'summary': {
                'total_tested': 0,
                'available': 0,
                'unavailable': 0,
                'success_rate': 0.0
            }
        }
        
        # Definir instrumentos a evaluar
        self.test_instruments = {
            'indices': {
                'NAS100': 'NAS100',  # NASDAQ 100
                'SPX500': 'SPX500',  # S&P 500
                'GER40': 'GER40',    # DAX
                'UK100': 'UK100',    # FTSE 100
                'JPN225': 'JPN225',  # Nikkei 225
                'AUS200': 'AUS200',  # ASX 200
                'FRA40': 'FRA40',    # CAC 40
                'ESP35': 'ESP35'     # IBEX 35
            },
            'forex_majors': {
                'EURUSD': 'EURUSD',
                'GBPUSD': 'GBPUSD', 
                'USDJPY': 'USDJPY',
                'AUDUSD': 'AUDUSD',
                'USDCAD': 'USDCAD',
                'USDCHF': 'USDCHF',
                'NZDUSD': 'NZDUSD',
                'EURGBP': 'EURGBP'
            },
            'commodities': {
                'XAUUSD': 'XAUUSD',  # Oro
                'XAGUSD': 'XAGUSD',  # Plata
                'USOIL': 'USOIL',    # Petróleo WTI
                'UKOIL': 'UKOIL',    # Petróleo Brent
                'NATGAS': 'NATGAS',  # Gas Natural
                'COPPER': 'COPPER',  # Cobre
                'WHEAT': 'WHEAT',    # Trigo
                'CORN': 'CORN'       # Maíz
            }
        }

    def evaluate_instrument_availability(self, symbol, category):
        """Evalúa la disponibilidad de un instrumento específico"""
        print(f"🔍 Evaluando {symbol} ({category})...")
        
        result = {
            'symbol': symbol,
            'category': category,
            'available': False,
            'current_price': None,
            'historical_data_points': 0,
            'last_update': None,
            'data_sources': [],
            'errors': []
        }
        
        try:
            # Intentar obtener precio actual
            current_price = self.data_system.get_current_price(symbol)
            if current_price and current_price > 0:
                result['current_price'] = current_price
                result['available'] = True
                print(f"✅ {symbol}: Precio actual = ${current_price:.4f}")
            else:
                result['errors'].append("No se pudo obtener precio actual")
                print(f"❌ {symbol}: No se pudo obtener precio actual")
                
        except Exception as e:
            result['errors'].append(f"Error precio actual: {str(e)}")
            print(f"❌ {symbol}: Error precio actual - {str(e)}")
        
        try:
            # Intentar obtener datos históricos (últimas 24 horas)
            historical_data = self.data_system.get_historical_data(
                symbol=symbol,
                interval='1h',
                limit=24  # Últimas 24 horas
            )
            
            if historical_data is not None and not historical_data.empty:
                result['historical_data_points'] = len(historical_data)
                result['last_update'] = historical_data.index[-1].isoformat() if len(historical_data) > 0 else None
                print(f"📊 {symbol}: {len(historical_data)} puntos de datos históricos")
            else:
                result['errors'].append("No se pudieron obtener datos históricos")
                print(f"📊 {symbol}: Sin datos históricos")
                
        except Exception as e:
            result['errors'].append(f"Error datos históricos: {str(e)}")
            print(f"📊 {symbol}: Error datos históricos - {str(e)}")
        
        # Determinar disponibilidad final
        if result['current_price'] and result['historical_data_points'] > 0:
            result['available'] = True
            result['data_sources'] = ['Binance', 'CoinGecko', 'Coinbase']  # APIs disponibles
        else:
            result['available'] = False
            
        return result

    def evaluate_all_instruments(self):
        """Evalúa todos los instrumentos definidos"""
        print("🚀 Iniciando evaluación de disponibilidad multi-asset...")
        print("=" * 60)
        
        total_instruments = 0
        available_instruments = 0
        
        # Evaluar cada categoría
        for category, instruments in self.test_instruments.items():
            print(f"\n📈 Evaluando {category.upper()}:")
            print("-" * 40)
            
            category_results = {}
            
            for name, symbol in instruments.items():
                result = self.evaluate_instrument_availability(symbol, category)
                category_results[name] = result
                
                total_instruments += 1
                if result['available']:
                    available_instruments += 1
                    
            self.results[category] = category_results
        
        # Calcular estadísticas finales
        self.results['summary'] = {
            'total_tested': total_instruments,
            'available': available_instruments,
            'unavailable': total_instruments - available_instruments,
            'success_rate': (available_instruments / total_instruments * 100) if total_instruments > 0 else 0.0
        }
        
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE EVALUACIÓN:")
        print(f"Total instrumentos evaluados: {total_instruments}")
        print(f"Instrumentos disponibles: {available_instruments}")
        print(f"Instrumentos no disponibles: {total_instruments - available_instruments}")
        print(f"Tasa de éxito: {self.results['summary']['success_rate']:.1f}%")

    def generate_availability_report(self):
        """Genera reporte detallado de disponibilidad"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"multi_asset_availability_report_{timestamp}.json"
        
        # Guardar reporte JSON
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Reporte guardado: {report_filename}")
        
        # Generar reporte de texto legible
        text_report = f"""
REPORTE DE DISPONIBILIDAD MULTI-ASSET - SICAR
============================================
Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

RESUMEN EJECUTIVO:
- Total instrumentos evaluados: {self.results['summary']['total_tested']}
- Instrumentos disponibles: {self.results['summary']['available']}
- Tasa de éxito: {self.results['summary']['success_rate']:.1f}%

ÍNDICES DISPONIBLES:
"""
        
        for category in ['indices', 'forex_majors', 'commodities']:
            if category in self.results:
                category_name = {
                    'indices': 'ÍNDICES',
                    'forex_majors': 'FOREX MAJORS', 
                    'commodities': 'COMMODITIES'
                }[category]
                
                text_report += f"\n{category_name}:\n"
                text_report += "-" * len(category_name) + ":\n"
                
                for name, data in self.results[category].items():
                    status = "✅ DISPONIBLE" if data['available'] else "❌ NO DISPONIBLE"
                    price = f"${data['current_price']:.4f}" if data['current_price'] else "N/A"
                    points = data['historical_data_points']
                    
                    text_report += f"  {name} ({data['symbol']}): {status}\n"
                    text_report += f"    Precio actual: {price}\n"
                    text_report += f"    Datos históricos: {points} puntos\n"
                    
                    if data['errors']:
                        text_report += f"    Errores: {', '.join(data['errors'])}\n"
                    text_report += "\n"
        
        text_report_filename = f"multi_asset_availability_report_{timestamp}.txt"
        with open(text_report_filename, 'w', encoding='utf-8') as f:
            f.write(text_report)
        
        print(f"📄 Reporte de texto guardado: {text_report_filename}")
        
        return report_filename, text_report_filename

    def get_recommended_instruments(self):
        """Obtiene lista de instrumentos recomendados basada en disponibilidad"""
        recommended = {
            'indices': [],
            'forex_majors': [],
            'commodities': []
        }
        
        for category in ['indices', 'forex_majors', 'commodities']:
            if category in self.results:
                for name, data in self.results[category].items():
                    if data['available'] and data['current_price'] and data['historical_data_points'] > 10:
                        recommended[category].append({
                            'name': name,
                            'symbol': data['symbol'],
                            'current_price': data['current_price'],
                            'data_points': data['historical_data_points']
                        })
        
        return recommended

def main():
    """Función principal"""
    print("🌟 EVALUADOR DE DISPONIBILIDAD MULTI-ASSET - SICAR 2025")
    print("=" * 60)
    
    evaluator = MultiAssetEvaluator()
    
    try:
        # Evaluar todos los instrumentos
        evaluator.evaluate_all_instruments()
        
        # Generar reportes
        json_report, text_report = evaluator.generate_availability_report()
        
        # Obtener recomendaciones
        recommended = evaluator.get_recommended_instruments()
        
        print("\n🎯 INSTRUMENTOS RECOMENDADOS PARA BACKTESTING:")
        print("=" * 50)
        
        for category, instruments in recommended.items():
            if instruments:
                category_name = {
                    'indices': 'ÍNDICES',
                    'forex_majors': 'FOREX MAJORS',
                    'commodities': 'COMMODITIES'
                }[category]
                
                print(f"\n{category_name}:")
                for instrument in instruments:
                    print(f"  ✅ {instrument['name']} ({instrument['symbol']}) - ${instrument['current_price']:.4f}")
        
        print(f"\n✅ Evaluación completada exitosamente!")
        print(f"📊 Reportes generados: {json_report}, {text_report}")
        
    except Exception as e:
        print(f"❌ Error durante la evaluación: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)