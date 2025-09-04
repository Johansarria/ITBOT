#!/usr/bin/env python3
"""
CONFIGURACIÓN PERSONALIZADA PARA ESTRATEGIAS AUTÓNOMAS
Generado el: 2025-08-31 05:07:51
"""

# IMPORTAR TU CONFIGURACIÓN ACTUAL
try:
    from config import *  # Tu configuración existente
    print("✅ Configuración actual importada correctamente")
except ImportError:
    print("⚠️  No se pudo importar config.py - usando configuración por defecto")

# CONFIGURACIÓN DE ESTRATEGIAS AUTÓNOMAS
AUTONOMOUS_CONFIG = {
    # CAPITAL Y RIESGO
    'capital_inicial': 1000,
    'modo_demo': True,
    'riesgo_por_trade': 0.02,
    'max_posiciones_simultaneas': 5,
    'stop_loss_diario': 0.05,
    
    # PARES DE TRADING
    'pares_favoritos': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT', 'XRPUSDT', 'DOTUSDT', 'LINKUSDT'],
    
    # TIMEFRAMES
    'timeframes_principales': ['5m', '15m', '30m'],
    'timeframes_scalping': ['1m', '3m'],
    
    # ESTRATEGIAS
    'estrategias_activas': {'scalping_auto': True, 'mean_reversion': True, 'breakout_momentum': True, 'arbitrage_temporal': False, 'volatility_trading': False},
    
    # DISTRIBUCIÓN DE CAPITAL POR ESTRATEGIA
    'distribucion_capital': {
        'scalping_auto': 0.40,      # 40% para scalping
        'mean_reversion': 0.30,     # 30% para mean reversion
        'breakout_momentum': 0.20,  # 20% para breakouts
        'arbitrage_temporal': 0.05, # 5% para arbitraje
        'volatility_trading': 0.05  # 5% para volatilidad
    },
    
    # CONFIGURACIÓN AVANZADA
    'filtros_calidad': {
        'rsi_oversold': 25,         # RSI oversold level
        'rsi_overbought': 75,       # RSI overbought level
        'volumen_spike_factor': 1.5, # Factor para detectar spikes de volumen
        'min_confianza': 0.6,       # Confianza mínima para ejecutar señal
        'max_correlacion': 0.7      # Máxima correlación entre trades
    },
    
    # ALERTAS Y NOTIFICACIONES
    'telegram_alerts': {
        'chat_id': None,
        'alertas_trades': True,
        'alertas_pnl': True,
        'alertas_riesgo': True
    }
}

# FUNCIÓN DE INTEGRACIÓN RÁPIDA
def get_autonomous_config():
    """
    Obtener configuración para estrategias autónomas
    """
    return AUTONOMOUS_CONFIG

# FUNCIÓN DE VALIDACIÓN
def validate_config():
    """
    Validar que la configuración es correcta
    """
    config = AUTONOMOUS_CONFIG
    errors = []
    
    # Validar capital
    if config['capital_inicial'] <= 0:
        errors.append("Capital inicial debe ser mayor a 0")
    
    # Validar riesgo
    if config['riesgo_por_trade'] <= 0 or config['riesgo_por_trade'] > 0.1:
        errors.append("Riesgo por trade debe estar entre 0.1% y 10%")
    
    # Validar distribución de capital
    total_distribucion = sum(config['distribucion_capital'].values())
    if abs(total_distribucion - 1.0) > 0.01:
        errors.append(f"Distribución de capital no suma 100% (suma: {total_distribucion:.1%})")
    
    # Validar pares
    if not config['pares_favoritos']:
        errors.append("Debe configurar al menos un par de trading")
    
    if errors:
        print("❌ Errores en configuración:")
        for error in errors:
            print(f"   - {error}")
        return False
    else:
        print("✅ Configuración válida")
        return True

if __name__ == "__main__":
    print("🔧 Validando configuración autónoma...")
    validate_config()
    print("\n📊 Configuración actual:")
    print(f"   Capital inicial: ${AUTONOMOUS_CONFIG['capital_inicial']:,}")
    print(f"   Modo: {'Demo' if AUTONOMOUS_CONFIG['modo_demo'] else 'Real Trading'}")
    print(f"   Estrategias activas: {sum(AUTONOMOUS_CONFIG['estrategias_activas'].values())}")
    print(f"   Pares configurados: {len(AUTONOMOUS_CONFIG['pares_favoritos'])}")
