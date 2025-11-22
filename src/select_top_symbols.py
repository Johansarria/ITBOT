#!/usr/bin/env python3
"""
Script para seleccionar los mejores 10 símbolos de criptomonedas para backtesting
Usando ÚNICAMENTE Binance y APIs alternativas (CoinGecko, Coinbase)
SIN yfinance - Solo datos reales validados
"""

import json
import logging
from datetime import datetime
from real_data_system import RealDataSystem

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TopSymbolSelector:
    def __init__(self):
        """Inicializar el selector de símbolos top"""
        self.real_data_system = RealDataSystem()
        
        # TOP 10 SÍMBOLOS VALIDADOS - Basados en pruebas exitosas anteriores
        # Estos símbolos han sido probados y funcionan con nuestro sistema de datos reales
        self.top_10_symbols = [
            'BTCUSDT',   # Bitcoin - Líder del mercado, máxima liquidez
            'ETHUSDT',   # Ethereum - Segunda criptomoneda más importante
            'BNBUSDT',   # Binance Coin - Nativa de Binance, excelente liquidez
            'ADAUSDT',   # Cardano - Validado en pruebas anteriores
            'SOLUSDT',   # Solana - Alto volumen y volatilidad
            'XRPUSDT',   # Ripple - Amplia adopción institucional
            'DOTUSDT',   # Polkadot - Ecosistema sólido
            'DOGEUSDT',  # Dogecoin - Alta volatilidad, buen para trading
            'AVAXUSDT',  # Avalanche - Blockchain rápida y eficiente
            'MATICUSDT'  # Polygon - Solución de escalabilidad popular
        ]
        
    def validate_symbol_availability(self, symbol):
        """
        Validar que un símbolo esté disponible en nuestras APIs reales
        
        Args:
            symbol (str): Símbolo a validar
            
        Returns:
            dict: Información de validación del símbolo
        """
        logger.info(f"Validando disponibilidad de {symbol}...")
        
        try:
            # Intentar obtener precio actual
            current_price = self.real_data_system.get_current_price(symbol)
            if not current_price:
                return {
                    'symbol': symbol,
                    'available': False,
                    'error': 'No se pudo obtener precio actual'
                }
            
            # Intentar obtener datos históricos básicos
            historical_data = self.real_data_system.get_historical_data(
                symbol=symbol,
                interval='1h',
                limit=24  # Solo últimas 24 horas para validación rápida
            )
            
            if not historical_data or len(historical_data) < 10:
                return {
                    'symbol': symbol,
                    'available': False,
                    'error': 'Datos históricos insuficientes'
                }
            
            # Calcular métricas básicas
            volumes = [float(candle['volume']) for candle in historical_data]
            avg_volume = sum(volumes) / len(volumes)
            
            return {
                'symbol': symbol,
                'available': True,
                'current_price': current_price,
                'data_points': len(historical_data),
                'avg_volume_24h': avg_volume,
                'validation_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error validando {symbol}: {str(e)}")
            return {
                'symbol': symbol,
                'available': False,
                'error': str(e)
            }
    
    def get_validated_top_symbols(self):
        """
        Obtener los símbolos top validados con nuestras APIs reales
        
        Returns:
            list: Lista de símbolos validados y disponibles
        """
        logger.info("=== VALIDANDO TOP 10 SÍMBOLOS CON APIS REALES ===")
        
        validated_symbols = []
        
        for symbol in self.top_10_symbols:
            validation_result = self.validate_symbol_availability(symbol)
            
            if validation_result['available']:
                validated_symbols.append(validation_result)
                logger.info(f"✅ {symbol}: DISPONIBLE - Precio: ${validation_result['current_price']:.2f}")
            else:
                logger.warning(f"❌ {symbol}: NO DISPONIBLE - {validation_result['error']}")
        
        logger.info(f"Símbolos validados: {len(validated_symbols)}/{len(self.top_10_symbols)}")
        return validated_symbols
    
    def save_validation_report(self, validated_symbols):
        """
        Guardar reporte de validación de símbolos
        
        Args:
            validated_symbols (list): Lista de símbolos validados
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"validated_symbols_report_{timestamp}.json"
        
        report = {
            'timestamp': timestamp,
            'data_sources': ['Binance', 'CoinGecko', 'Coinbase'],
            'excluded_sources': ['yfinance'],
            'total_candidates': len(self.top_10_symbols),
            'validated_count': len(validated_symbols),
            'success_rate': len(validated_symbols) / len(self.top_10_symbols) * 100,
            'validated_symbols': validated_symbols,
            'symbol_list': [s['symbol'] for s in validated_symbols]
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Reporte de validación guardado en: {report_file}")
        return report_file

def main():
    """Función principal"""
    logger.info("=== SELECTOR DE SÍMBOLOS TOP CON DATOS REALES ===")
    logger.info("🚫 SIN yfinance - Solo Binance y APIs alternativas")
    
    try:
        # Crear selector
        selector = TopSymbolSelector()
        
        # Validar símbolos top
        validated_symbols = selector.get_validated_top_symbols()
        
        if not validated_symbols:
            logger.error("❌ No se pudieron validar símbolos")
            return
        
        # Mostrar resultados
        print("\n" + "="*80)
        print("🎯 SÍMBOLOS VALIDADOS PARA BACKTESTING CON DATOS REALES")
        print("="*80)
        print(f"{'#':<3} {'Símbolo':<10} {'Precio Actual':<15} {'Datos 24h':<12} {'Volumen Avg':<15}")
        print("-" * 80)
        
        for i, symbol_data in enumerate(validated_symbols, 1):
            print(f"{i:<3} {symbol_data['symbol']:<10} "
                  f"${symbol_data['current_price']:<14.2f} "
                  f"{symbol_data['data_points']:<12} "
                  f"{symbol_data['avg_volume_24h']:<15,.0f}")
        
        # Guardar reporte
        report_file = selector.save_validation_report(validated_symbols)
        
        print("\n" + "="*80)
        print("✅ VALIDACIÓN COMPLETADA EXITOSAMENTE")
        print(f"📊 Símbolos validados: {len(validated_symbols)}/10")
        print(f"📈 Tasa de éxito: {len(validated_symbols)/10*100:.1f}%")
        print(f"🔗 APIs utilizadas: Binance, CoinGecko, Coinbase")
        print(f"🚫 APIs excluidas: yfinance")
        print(f"📄 Reporte guardado: {report_file}")
        print("="*80)
        
        # Lista final para backtesting
        final_symbols = [s['symbol'] for s in validated_symbols]
        print(f"\n🎯 SÍMBOLOS PARA BACKTESTING: {final_symbols}")
        
        return validated_symbols
        
    except Exception as e:
        logger.error(f"Error en validación de símbolos: {str(e)}")
        raise

if __name__ == "__main__":
    main()