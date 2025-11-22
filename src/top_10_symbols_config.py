#!/usr/bin/env python3
"""
Configuración de los TOP 10 símbolos validados para backtesting
Basado en pruebas exitosas anteriores con datos reales
"""

import json
from datetime import datetime

# TOP 10 SÍMBOLOS VALIDADOS - Confirmados funcionando con datos reales
TOP_10_SYMBOLS = [
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

# Configuración de backtesting
BACKTEST_CONFIG = {
    'symbols': TOP_10_SYMBOLS,
    'data_sources': ['Binance', 'CoinGecko', 'Coinbase'],
    'excluded_sources': ['yfinance'],
    'intervals': ['1h', '4h', '1d'],
    'default_interval': '1h',
    'historical_days': 30,
    'validation_status': 'confirmed_working'
}

def get_symbols_for_backtesting():
    """
    Obtener lista de símbolos para backtesting
    
    Returns:
        list: Lista de símbolos validados
    """
    return TOP_10_SYMBOLS.copy()

def save_symbols_config():
    """
    Guardar configuración de símbolos
    
    Returns:
        str: Nombre del archivo guardado
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    config_file = f"symbols_config_{timestamp}.json"
    
    config = {
        'timestamp': timestamp,
        'version': '1.0',
        'description': 'TOP 10 símbolos validados para backtesting con datos reales',
        'symbols': TOP_10_SYMBOLS,
        'backtest_config': BACKTEST_CONFIG,
        'validation_notes': [
            'Símbolos confirmados funcionando con sistema de datos reales',
            'APIs utilizadas: Binance, CoinGecko, Coinbase',
            'yfinance excluido por problemas de conectividad',
            'Validado en pruebas anteriores exitosas'
        ]
    }
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Configuración guardada en: {config_file}")
    return config_file

def main():
    """Función principal"""
    print("="*80)
    print("🎯 CONFIGURACIÓN DE SÍMBOLOS TOP PARA BACKTESTING")
    print("="*80)
    print("🔗 APIs utilizadas: Binance, CoinGecko, Coinbase")
    print("🚫 APIs excluidas: yfinance")
    print("✅ Estado: Validados y confirmados funcionando")
    print("="*80)
    
    print("\n📋 TOP 10 SÍMBOLOS PARA BACKTESTING:")
    for i, symbol in enumerate(TOP_10_SYMBOLS, 1):
        print(f"{i:2d}. {symbol}")
    
    # Guardar configuración
    config_file = save_symbols_config()
    
    print(f"\n✅ Configuración completada")
    print(f"📊 Total de símbolos: {len(TOP_10_SYMBOLS)}")
    print(f"📄 Archivo de configuración: {config_file}")
    print("🚀 Listo para ejecutar backtests con datos reales")
    print("="*80)
    
    return TOP_10_SYMBOLS

if __name__ == "__main__":
    main()