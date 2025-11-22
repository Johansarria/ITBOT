#!/usr/bin/env python3
"""
Script de prueba para el Sistema de Validación de Rupturas Anti-Fakeout
Prueba completa del Optimización #5
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Agregar directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.breakout_validator import BreakoutValidator, BreakoutStatus, BreakoutType
from src.crypto_data_loader import CryptoDataLoader

def generate_test_data(symbol: str = "BTC-USD", days: int = 30) -> pd.DataFrame:
    """Generar datos de prueba simulando diferentes escenarios de ruptura"""
    
    # Generar fechas
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, freq='1h')
    
    # Precio base
    base_price = 50000
    
    # Generar diferentes escenarios de prueba
    scenarios = [
        "valid_breakout",      # Ruptura válida con confirmación
        "fakeout",            # Falsa ruptura
        "pending_breakout",     # Ruptura pendiente
        "near_resistance",     # Cerca de resistencia
        "high_volatility"      # Alta volatilidad
    ]
    
    results = {}
    
    for scenario in scenarios:
        np.random.seed(42)  # Para reproducibilidad
        
        if scenario == "valid_breakout":
            # Simular ruptura válida alcista
            prices = []
            current_price = base_price * 0.95
            
            for i in range(len(dates)):
                if i < len(dates) * 0.8:  # 80% inicial en rango
                    current_price += np.random.normal(0, current_price * 0.002)
                else:  # Último 20% con ruptura
                    if i == int(len(dates) * 0.8):
                        current_price = base_price * 1.02  # Ruptura inicial
                    current_price += np.random.normal(current_price * 0.001, current_price * 0.003)
                
                prices.append(max(current_price, base_price * 0.9))
            
            # Generar OHLCV
            df = pd.DataFrame({
                'timestamp': dates,
                'open': [p * (1 + np.random.normal(0, 0.001)) for p in prices],
                'high': [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
                'close': prices,
                'volume': [np.random.uniform(1000, 5000) * (2 if i > len(dates) * 0.8 else 1) for i in range(len(dates))]
            })
            
        elif scenario == "fakeout":
            # Simular falsa ruptura
            prices = []
            current_price = base_price * 0.98
            
            for i in range(len(dates)):
                if i < len(dates) * 0.85:  # 85% inicial
                    current_price += np.random.normal(0, current_price * 0.002)
                elif i < len(dates) * 0.9:  # Falsa ruptura
                    current_price = base_price * 1.015  # Breve ruptura
                    current_price += np.random.normal(0, current_price * 0.004)
                else:  # Retorno al rango
                    current_price = base_price * 0.99
                    current_price += np.random.normal(-current_price * 0.001, current_price * 0.002)
                
                prices.append(current_price)
            
            df = pd.DataFrame({
                'timestamp': dates,
                'open': [p * (1 + np.random.normal(0, 0.001)) for p in prices],
                'high': [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
                'close': prices,
                'volume': [np.random.uniform(1000, 3000) for _ in range(len(dates))]
            })
            
        else:
            # Datos genéricos para otros escenarios
            prices = []
            current_price = base_price * 0.95
            
            for i in range(len(dates)):
                current_price += np.random.normal(0, current_price * 0.003)
                prices.append(current_price)
            
            df = pd.DataFrame({
                'timestamp': dates,
                'open': [p * (1 + np.random.normal(0, 0.001)) for p in prices],
                'high': [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
                'close': prices,
                'volume': [np.random.uniform(1000, 3000) for _ in range(len(dates))]
            })
        
        results[scenario] = df
    
    return results

def test_breakout_validator():
    """Probar el validador de rupturas con diferentes escenarios"""
    
    print("🚀 Iniciando pruebas del Sistema de Validación de Rupturas Anti-Fakeout")
    print("=" * 80)
    
    # Crear validador
    validator = BreakoutValidator()
    
    # Generar datos de prueba
    test_data = generate_test_data()
    
    # Definir niveles de prueba
    test_levels = {
        "valid_breakout": 51000,    # Nivel que debería ser roto válidamente
        "fakeout": 50800,           # Nivel con falsa ruptura
        "pending_breakout": 51500,  # Nivel pendiente
        "near_resistance": 50500,  # Cerca de resistencia
        "high_volatility": 52000   # En alta volatilidad
    }
    
    # Probar cada escenario
    for scenario, data in test_data.items():
        print(f"\n📊 Probando escenario: {scenario.upper()}")
        print("-" * 50)
        
        level_price = test_levels[scenario]
        current_price = data['close'].iloc[-1]
        
        print(f"💰 Precio actual: ${current_price:,.2f}")
        print(f"🎯 Nivel a validar: ${level_price:,.2f}")
        
        # Determinar tipo de ruptura
        if current_price > level_price:
            breakout_type = BreakoutType.BULLISH
        else:
            breakout_type = BreakoutType.BEARISH
        
        # Validar ruptura
        validation = validator.validate_breakout(
            data=data,
            level_price=level_price,
            breakout_type=breakout_type,
            lookback_periods=20,
            confirmation_periods=3
        )
        
        # Mostrar resultados
        print(f"\n{validator.get_validation_summary(validation)}")
        
        # Análisis adicional
        if validation.status == BreakoutStatus.VALID:
            print("✅ Ruptura VÁLIDA - Señal puede proceder")
        elif validation.status == BreakoutStatus.FAKEOUT:
            print("🚨 Ruptura FALSA - EVITAR señal")
        elif validation.status == BreakoutStatus.PENDING:
            print("⏳ Ruptura PENDIENTE - Esperar confirmación")
        
        print("\n" + "=" * 80)

def test_real_data(symbol: str = "BTC-USD"):
    """Probar con datos reales de Binance"""
    
    print(f"\n🔄 Probando con datos reales: {symbol}")
    print("=" * 80)
    
    try:
        # Obtener datos reales
        loader = CryptoDataLoader(symbol, "1h")
        real_data = loader.get_binance_data(limit=200)
        
        if real_data.empty:
            print("❌ No se pudieron obtener datos reales")
            return
        
        validator = BreakoutValidator()
        
        # Calcular niveles de soporte/resistencia simples
        recent_high = real_data['high'].tail(48).max()
        recent_low = real_data['low'].tail(48).min()
        current_price = real_data['close'].iloc[-1]
        
        # Usar máximos/mínimos recientes como niveles
        test_levels = [
            (recent_high, "Resistencia reciente"),
            (recent_low, "Soporte reciente"),
            ((recent_high + recent_low) / 2, "Punto medio")
        ]
        
        for level_price, level_name in test_levels:
            print(f"\n🎯 Validando {level_name}: ${level_price:,.2f}")
            
            # Determinar tipo de ruptura
            if current_price > level_price:
                breakout_type = BreakoutType.BULLISH
            else:
                breakout_type = BreakoutType.BEARISH
            
            # Validar
            validation = validator.validate_breakout(
                data=real_data,
                level_price=level_price,
                breakout_type=breakout_type,
                lookback_periods=20,
                confirmation_periods=3
            )
            
            print(f"\n{validator.get_validation_summary(validation)}")
            
    except Exception as e:
        print(f"❌ Error con datos reales: {e}")

if __name__ == "__main__":
    # Configurar logging
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Pruebas con datos simulados
    test_breakout_validator()
    
    # Pruebas con datos reales (opcional)
    print("\n" + "="*80)
    test_real_data("BTC-USD")