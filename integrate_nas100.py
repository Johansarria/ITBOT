#!/usr/bin/env python3
"""
Script de Integración NAS100 Strategy (Versión Simplificada)
Integra la estrategia optimizada de NAS100 sin dependencias complejas
"""

import sys
import os
from datetime import datetime
import json
import pandas as pd
import numpy as np

# Configuraciones optimizadas por condición de mercado
NAS100_CONFIGS = {
    'TRENDING_BULL': {
        'momentum_period_short': 3,
        'momentum_period_long': 15,
        'momentum_threshold': 0.01,
        'breakout_threshold': 0.015,
        'session_multiplier': 2.0,
        'volatility_multiplier': 1.8
    },
    'TRENDING_BEAR': {
        'momentum_period_short': 5,
        'momentum_period_long': 25,
        'momentum_threshold': 0.015,
        'breakout_threshold': 0.02,
        'session_multiplier': 1.5,
        'volatility_multiplier': 1.3
    },
    'SIDEWAYS_LOW_VOL': {
        'momentum_period_short': 7,
        'momentum_period_long': 30,
        'momentum_threshold': 0.025,
        'breakout_threshold': 0.03,
        'session_multiplier': 1.2,
        'volatility_multiplier': 1.0
    },
    'HIGH_VOLATILITY': {
        'momentum_period_short': 5,
        'momentum_period_long': 20,
        'momentum_threshold': 0.02,
        'breakout_threshold': 0.025,
        'session_multiplier': 1.3,
        'volatility_multiplier': 1.5
    },
    'BALANCED': {
        'momentum_period_short': 5,
        'momentum_period_long': 20,
        'momentum_threshold': 0.015,
        'breakout_threshold': 0.02,
        'session_multiplier': 1.5,
        'volatility_multiplier': 1.3
    }
}

# Configuración óptima global (Score: 1.8077)
BEST_GLOBAL_CONFIG = {
    'momentum_period_short': 5,
    'momentum_period_long': 20,
    'momentum_threshold': 0.01,
    'breakout_period': 10,
    'breakout_threshold': 0.03,
    'session_multiplier': 1.5,
    'volatility_multiplier': 1.8
}

class SimpleNAS100Strategy:
    """
    Versión simplificada de la estrategia NAS100 para integración
    """
    
    def __init__(self, **params):
        self.momentum_period_short = params.get('momentum_period_short', 5)
        self.momentum_period_long = params.get('momentum_period_long', 20)
        self.momentum_threshold = params.get('momentum_threshold', 0.015)
        self.breakout_threshold = params.get('breakout_threshold', 0.02)
        self.session_multiplier = params.get('session_multiplier', 1.5)
        self.volatility_multiplier = params.get('volatility_multiplier', 1.3)
        
    def calculate_momentum(self, data):
        """Calcula el momentum usando medias móviles"""
        if len(data) < self.momentum_period_long:
            return 0
        
        short_ma = data['close'].rolling(self.momentum_period_short).mean().iloc[-1]
        long_ma = data['close'].rolling(self.momentum_period_long).mean().iloc[-1]
        
        return (short_ma - long_ma) / long_ma
    
    def detect_breakout(self, data):
        """Detecta breakouts usando volatilidad"""
        if len(data) < 20:
            return False
        
        recent_volatility = data['close'].pct_change().rolling(10).std().iloc[-1]
        avg_volatility = data['close'].pct_change().rolling(20).std().mean()
        
        return recent_volatility > avg_volatility * (1 + self.breakout_threshold)
    
    def is_ny_session(self):
        """Verifica si estamos en la sesión de NY (simplificado)"""
        current_hour = datetime.now().hour
        return 14 <= current_hour <= 21  # UTC
    
    def generate_signal(self, data):
        """Genera señal de trading"""
        try:
            momentum = self.calculate_momentum(data)
            breakout = self.detect_breakout(data)
            ny_session = self.is_ny_session()
            
            # Ajustar threshold por sesión
            effective_threshold = self.momentum_threshold
            if ny_session:
                effective_threshold /= self.session_multiplier
            
            # Lógica de señales
            if momentum > effective_threshold and breakout:
                return 'BUY'
            elif momentum < -effective_threshold and breakout:
                return 'SELL'
            else:
                return 'HOLD'
                
        except Exception as e:
            print(f"Error generando señal: {e}")
            return 'HOLD'

class NAS100Integration:
    """
    Clase para integrar la estrategia NAS100 al sistema principal
    """
    
    def __init__(self):
        self.current_config = 'BALANCED'
        self.strategy = None
        
    def initialize_strategy(self, config_name='BALANCED'):
        """Inicializa la estrategia NAS100 con la configuración especificada"""
        try:
            if config_name not in NAS100_CONFIGS:
                print(f"Configuración {config_name} no encontrada, usando BALANCED")
                config_name = 'BALANCED'
            
            config = NAS100_CONFIGS[config_name]
            self.strategy = SimpleNAS100Strategy(**config)
            self.current_config = config_name
            
            print(f"✅ Estrategia NAS100 inicializada con configuración: {config_name}")
            print(f"📊 Parámetros: {config}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error inicializando estrategia NAS100: {e}")
            return False
    
    def detect_market_condition(self, data):
        """Detecta la condición actual del mercado"""
        try:
            if len(data) < 50:
                return 'BALANCED'
            
            # Calcular indicadores básicos
            recent_data = data.tail(20)
            volatility = recent_data['close'].pct_change().std() * 100
            
            # Tendencia
            sma_short = data['close'].rolling(10).mean().iloc[-1]
            sma_long = data['close'].rolling(50).mean().iloc[-1]
            
            # Momentum
            momentum = (data['close'].iloc[-1] / data['close'].iloc[-10] - 1) * 100
            
            # Lógica de detección
            if volatility > 3.0:
                return 'HIGH_VOLATILITY'
            elif sma_short > sma_long * 1.02 and momentum > 2:
                return 'TRENDING_BULL'
            elif sma_short < sma_long * 0.98 and momentum < -2:
                return 'TRENDING_BEAR'
            elif abs(momentum) < 0.5 and volatility < 1.5:
                return 'SIDEWAYS_LOW_VOL'
            else:
                return 'BALANCED'
                
        except Exception as e:
            print(f"Error detectando condición de mercado: {e}")
            return 'BALANCED'
    
    def get_signal(self, data):
        """Obtiene señal de trading de la estrategia NAS100"""
        try:
            if self.strategy is None:
                self.initialize_strategy()
            
            # Detectar condición de mercado
            new_condition = self.detect_market_condition(data)
            
            # Cambiar configuración si es necesario
            if new_condition != self.current_config:
                print(f"🔄 Cambiando configuración de {self.current_config} a {new_condition}")
                self.initialize_strategy(new_condition)
            
            # Obtener señal
            signal = self.strategy.generate_signal(data)
            
            if signal != 'HOLD':
                print(f"🎯 Señal NAS100: {signal} (Config: {self.current_config})")
            
            return signal
            
        except Exception as e:
            print(f"Error generando señal NAS100: {e}")
            return 'HOLD'
    
    def get_current_config(self):
        """Retorna la configuración actual"""
        return {
            'config_name': self.current_config,
            'parameters': NAS100_CONFIGS.get(self.current_config, {})
        }
    
    def save_config_log(self):
        """Guarda un log de la configuración actual"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_data = {
                'timestamp': timestamp,
                'config_name': self.current_config,
                'parameters': NAS100_CONFIGS.get(self.current_config, {})
            }
            
            filename = f"nas100_config_log_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            print(f"💾 Configuración guardada en: {filename}")
            
        except Exception as e:
            print(f"Error guardando configuración: {e}")

def test_integration_with_sample_data():
    """Prueba la integración con datos de muestra"""
    print("\n🧪 PROBANDO INTEGRACIÓN CON DATOS DE MUESTRA")
    
    # Crear datos de muestra
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
    np.random.seed(42)
    
    # Simular datos de NAS100
    base_price = 15000
    returns = np.random.normal(0.0001, 0.02, 100)
    prices = [base_price]
    
    for ret in returns:
        prices.append(prices[-1] * (1 + ret))
    
    data = pd.DataFrame({
        'timestamp': dates,
        'open': prices[:-1],
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices[:-1]],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices[:-1]],
        'close': prices[1:],
        'volume': np.random.randint(1000, 10000, 100)
    })
    
    # Probar integración
    integration = NAS100Integration()
    
    # Probar diferentes configuraciones
    for config in ['BALANCED', 'TRENDING_BULL', 'HIGH_VOLATILITY']:
        print(f"\n📋 Probando configuración: {config}")
        integration.initialize_strategy(config)
        
        # Generar algunas señales
        for i in range(3):
            sample_data = data.iloc[:50+i*10]
            signal = integration.get_signal(sample_data)
            print(f"  Señal {i+1}: {signal}")
    
    return integration

def integrate_nas100_to_main_bot():
    """Función principal para integrar NAS100 al bot principal"""
    try:
        print("=== 🚀 INICIANDO INTEGRACIÓN NAS100 ===")
        
        # Crear instancia de integración
        nas100_integration = NAS100Integration()
        
        # Inicializar con configuración balanceada
        if nas100_integration.initialize_strategy('BALANCED'):
            print("\n✅ ESTRATEGIA NAS100 INTEGRADA EXITOSAMENTE")
            
            # Guardar configuración inicial
            nas100_integration.save_config_log()
            
            # Mostrar configuraciones disponibles
            print("\n📋 CONFIGURACIONES DISPONIBLES:")
            for config_name in NAS100_CONFIGS.keys():
                print(f"  ✓ {config_name}")
            
            print("\n🎯 CONFIGURACIÓN ÓPTIMA GLOBAL (Score: 1.8077):")
            for key, value in BEST_GLOBAL_CONFIG.items():
                print(f"  {key}: {value}")
            
            return nas100_integration
        else:
            print("❌ Error en la integración de NAS100")
            return None
            
    except Exception as e:
        print(f"Error en integración principal: {e}")
        return None

if __name__ == "__main__":
    # Ejecutar integración
    integration = integrate_nas100_to_main_bot()
    
    if integration:
        print("\n" + "="*60)
        print("🎉 INTEGRACIÓN NAS100 COMPLETADA EXITOSAMENTE")
        print("="*60)
        print(f"📊 Configuración actual: {integration.current_config}")
        print("📖 Consulta NAS100_TRADING_GUIDE.md para detalles completos")
        print("\n💡 CÓMO USAR EN EL BOT PRINCIPAL:")
        print("   from integrate_nas100 import NAS100Integration")
        print("   nas100 = NAS100Integration()")
        print("   signal = nas100.get_signal(data)")
        
        # Ejecutar prueba con datos de muestra
        test_integration = test_integration_with_sample_data()
        
        print("\n🔧 ARCHIVOS CREADOS:")
        print("  ✓ strategies/nas100_strategy.py")
        print("  ✓ nas100_test.py")
        print("  ✓ nas100_optimization_guide.py")
        print("  ✓ NAS100_TRADING_GUIDE.md")
        print("  ✓ integrate_nas100.py")
        
    else:
        print("❌ Error en la integración")