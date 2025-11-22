#!/usr/bin/env python3
"""
Evaluador de Criptomonedas y Activos Alternativos para SICAR
Evalúa la disponibilidad de diferentes criptomonedas y tokens en el sistema de datos reales
"""

import sys
import os
import json
from datetime import datetime, timedelta
import pandas as pd

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from real_data_system import RealDataSystem

class CryptoAlternativesEvaluator:
    def __init__(self):
        self.data_system = RealDataSystem()
        self.results = {
            'evaluation_timestamp': datetime.now().isoformat(),
            'major_cryptos': {},
            'defi_tokens': {},
            'layer1_blockchains': {},
            'stablecoins': {},
            'meme_coins': {},
            'summary': {
                'total_tested': 0,
                'available': 0,
                'unavailable': 0,
                'success_rate': 0.0
            }
        }
        
        # Definir criptomonedas y tokens a evaluar (disponibles en Binance)
        self.test_instruments = {
            'major_cryptos': {
                'Bitcoin': 'BTCUSDT',
                'Ethereum': 'ETHUSDT', 
                'BNB': 'BNBUSDT',
                'XRP': 'XRPUSDT',
                'Cardano': 'ADAUSDT',
                'Solana': 'SOLUSDT',
                'Dogecoin': 'DOGEUSDT',
                'Polygon': 'MATICUSDT',
                'Litecoin': 'LTCUSDT',
                'Bitcoin_Cash': 'BCHUSDT'
            },
            'defi_tokens': {
                'Uniswap': 'UNIUSDT',
                'Chainlink': 'LINKUSDT',
                'Aave': 'AAVEUSDT',
                'Compound': 'COMPUSDT',
                'SushiSwap': 'SUSHIUSDT',
                'PancakeSwap': 'CAKEUSDT',
                'Curve': 'CRVUSDT',
                'Yearn_Finance': 'YFIUSDT'
            },
            'layer1_blockchains': {
                'Avalanche': 'AVAXUSDT',
                'Polkadot': 'DOTUSDT',
                'Cosmos': 'ATOMUSDT',
                'Algorand': 'ALGOUSDT',
                'Tezos': 'XTZUSDT',
                'Near_Protocol': 'NEARUSDT',
                'Fantom': 'FTMUSDT',
                'Harmony': 'ONEUSDT'
            },
            'stablecoins': {
                'USDC': 'USDCUSDT',
                'Binance_USD': 'BUSDUSDT',
                'DAI': 'DAIUSDT',
                'TrueUSD': 'TUSDUSDT',
                'Pax_Dollar': 'USDPUSDT'
            },
            'meme_coins': {
                'Dogecoin': 'DOGEUSDT',
                'Shiba_Inu': 'SHIBUSDT',
                'Floki': 'FLOKIUSDT',
                'SafeMoon': 'SAFEMOONUSDT',
                'Baby_Doge': 'BABYDOGEUSDT'
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
            'errors': [],
            'volume_24h': None,
            'price_change_24h': None
        }
        
        try:
            # Intentar obtener precio actual
            current_price = self.data_system.get_current_price(symbol)
            if current_price and current_price > 0:
                result['current_price'] = current_price
                result['available'] = True
                print(f"✅ {symbol}: Precio actual = ${current_price:.6f}")
            else:
                result['errors'].append("No se pudo obtener precio actual")
                print(f"❌ {symbol}: No se pudo obtener precio actual")
                
        except Exception as e:
            result['errors'].append(f"Error precio actual: {str(e)}")
            print(f"❌ {symbol}: Error precio actual - {str(e)}")
        
        try:
            # Intentar obtener datos históricos
            historical_data = self.data_system.get_historical_data(
                symbol=symbol,
                interval='1h',
                limit=24  # Últimas 24 horas
            )
            
            if historical_data is not None and not historical_data.empty:
                result['historical_data_points'] = len(historical_data)
                result['last_update'] = historical_data.index[-1].isoformat() if len(historical_data) > 0 else None
                
                # Calcular métricas adicionales
                if len(historical_data) >= 2:
                    latest_price = historical_data['close'].iloc[-1]
                    previous_price = historical_data['close'].iloc[-2]
                    result['price_change_24h'] = ((latest_price - previous_price) / previous_price * 100)
                    
                    if 'volume' in historical_data.columns:
                        result['volume_24h'] = historical_data['volume'].sum()
                
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
            result['data_sources'] = ['Binance', 'CoinGecko', 'Coinbase']
        else:
            result['available'] = False
            
        return result

    def evaluate_all_instruments(self):
        """Evalúa todos los instrumentos definidos"""
        print("🚀 Iniciando evaluación de criptomonedas y activos alternativos...")
        print("=" * 70)
        
        total_instruments = 0
        available_instruments = 0
        
        # Evaluar cada categoría
        for category, instruments in self.test_instruments.items():
            print(f"\n📈 Evaluando {category.upper().replace('_', ' ')}:")
            print("-" * 50)
            
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
        
        print("\n" + "=" * 70)
        print("📊 RESUMEN DE EVALUACIÓN:")
        print(f"Total instrumentos evaluados: {total_instruments}")
        print(f"Instrumentos disponibles: {available_instruments}")
        print(f"Instrumentos no disponibles: {total_instruments - available_instruments}")
        print(f"Tasa de éxito: {self.results['summary']['success_rate']:.1f}%")

    def generate_availability_report(self):
        """Genera reporte detallado de disponibilidad"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"crypto_alternatives_availability_{timestamp}.json"
        
        # Guardar reporte JSON
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Reporte guardado: {report_filename}")
        
        # Generar reporte de texto legible
        text_report = f"""
REPORTE DE DISPONIBILIDAD CRYPTO & ALTERNATIVAS - SICAR
======================================================
Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

RESUMEN EJECUTIVO:
- Total instrumentos evaluados: {self.results['summary']['total_tested']}
- Instrumentos disponibles: {self.results['summary']['available']}
- Tasa de éxito: {self.results['summary']['success_rate']:.1f}%

ANÁLISIS POR CATEGORÍAS:
"""
        
        for category in ['major_cryptos', 'defi_tokens', 'layer1_blockchains', 'stablecoins', 'meme_coins']:
            if category in self.results:
                category_name = {
                    'major_cryptos': 'CRIPTOMONEDAS PRINCIPALES',
                    'defi_tokens': 'TOKENS DEFI',
                    'layer1_blockchains': 'BLOCKCHAINS LAYER 1',
                    'stablecoins': 'STABLECOINS',
                    'meme_coins': 'MEME COINS'
                }[category]
                
                text_report += f"\n{category_name}:\n"
                text_report += "-" * len(category_name) + "\n"
                
                for name, data in self.results[category].items():
                    status = "✅ DISPONIBLE" if data['available'] else "❌ NO DISPONIBLE"
                    price = f"${data['current_price']:.6f}" if data['current_price'] else "N/A"
                    points = data['historical_data_points']
                    change = f"{data['price_change_24h']:.2f}%" if data['price_change_24h'] else "N/A"
                    
                    text_report += f"  {name} ({data['symbol']}): {status}\n"
                    text_report += f"    Precio actual: {price}\n"
                    text_report += f"    Cambio 24h: {change}\n"
                    text_report += f"    Datos históricos: {points} puntos\n"
                    
                    if data['errors']:
                        text_report += f"    Errores: {', '.join(data['errors'])}\n"
                    text_report += "\n"
        
        text_report_filename = f"crypto_alternatives_availability_{timestamp}.txt"
        with open(text_report_filename, 'w', encoding='utf-8') as f:
            f.write(text_report)
        
        print(f"📄 Reporte de texto guardado: {text_report_filename}")
        
        return report_filename, text_report_filename

    def get_top_performers(self, min_data_points=20):
        """Obtiene los mejores instrumentos basado en disponibilidad y calidad de datos"""
        top_performers = []
        
        for category in ['major_cryptos', 'defi_tokens', 'layer1_blockchains', 'stablecoins']:
            if category in self.results:
                for name, data in self.results[category].items():
                    if (data['available'] and 
                        data['current_price'] and 
                        data['historical_data_points'] >= min_data_points):
                        
                        top_performers.append({
                            'name': name,
                            'symbol': data['symbol'],
                            'category': category,
                            'current_price': data['current_price'],
                            'data_points': data['historical_data_points'],
                            'price_change_24h': data.get('price_change_24h', 0),
                            'volume_24h': data.get('volume_24h', 0)
                        })
        
        # Ordenar por calidad de datos y disponibilidad
        top_performers.sort(key=lambda x: x['data_points'], reverse=True)
        
        return top_performers

def main():
    """Función principal"""
    print("🌟 EVALUADOR DE CRIPTOMONEDAS Y ACTIVOS ALTERNATIVOS - SICAR 2025")
    print("=" * 70)
    
    evaluator = CryptoAlternativesEvaluator()
    
    try:
        # Evaluar todos los instrumentos
        evaluator.evaluate_all_instruments()
        
        # Generar reportes
        json_report, text_report = evaluator.generate_availability_report()
        
        # Obtener top performers
        top_performers = evaluator.get_top_performers()
        
        print("\n🏆 TOP INSTRUMENTOS RECOMENDADOS PARA BACKTESTING:")
        print("=" * 60)
        
        if top_performers:
            for i, instrument in enumerate(top_performers[:15], 1):  # Top 15
                change_emoji = "📈" if instrument['price_change_24h'] > 0 else "📉"
                print(f"{i:2d}. {change_emoji} {instrument['name']} ({instrument['symbol']})")
                print(f"     Precio: ${instrument['current_price']:.6f} | "
                      f"Cambio 24h: {instrument['price_change_24h']:.2f}% | "
                      f"Datos: {instrument['data_points']} puntos")
        else:
            print("❌ No se encontraron instrumentos disponibles")
        
        print(f"\n✅ Evaluación completada exitosamente!")
        print(f"📊 Reportes generados: {json_report}, {text_report}")
        
        return top_performers
        
    except Exception as e:
        print(f"❌ Error durante la evaluación: {str(e)}")
        return []

if __name__ == "__main__":
    top_performers = main()
    if not top_performers:
        sys.exit(1)