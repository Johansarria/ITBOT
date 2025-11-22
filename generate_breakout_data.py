#!/usr/bin/env python3
"""
Generar datos de validación de rupturas para pruebas del frontend
"""

import json
import os
from datetime import datetime

def generate_breakout_validation_data():
    """Generar datos de ejemplo para validación de rupturas"""
    
    # Datos de ejemplo para diferentes símbolos
    symbols = ["BTC-USD", "ETH-USD", "LINK-USD", "SOL-USD"]
    
    for symbol in symbols:
        # Generar datos diferentes para cada símbolo
        if symbol == "BTC-USD":
            data = {
                "status": "VALID",
                "confidence": 0.82,
                "factors": {
                    "volume": 0.85,
                    "momentum": 0.78,
                    "time": 0.90,
                    "proximity": 0.95,
                    "volatility": 0.75,
                    "sentiment": 0.80
                },
                "warnings": ["Volumen ligeramente bajo en últimas 2h"],
                "recommendations": ["Confirmar con 1-2 velas adicionales", "Monitorear volumen"],
                "breakout_factor": 0.82,
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "level_tested": 95000,
                "current_price": 96500,
                "breakout_type": "BULLISH"
            }
        elif symbol == "ETH-USD":
            data = {
                "status": "PENDING",
                "confidence": 0.65,
                "factors": {
                    "volume": 0.60,
                    "momentum": 0.70,
                    "time": 0.50,
                    "proximity": 0.80,
                    "volatility": 0.85,
                    "sentiment": 0.65
                },
                "warnings": ["Confirmación temporal insuficiente", "Volumen bajo"],
                "recommendations": ["Esperar 2-3 velas de confirmación", "Aumento de volumen necesario"],
                "breakout_factor": 0.65,
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "level_tested": 3500,
                "current_price": 3520,
                "breakout_type": "BULLISH"
            }
        elif symbol == "LINK-USD":
            data = {
                "status": "FAKEOUT",
                "confidence": 0.35,
                "factors": {
                    "volume": 0.40,
                    "momentum": 0.20,
                    "time": 0.30,
                    "proximity": 0.90,
                    "volatility": 0.95,
                    "sentiment": 0.25
                },
                "warnings": ["Momentum débil", "Volumen insuficiente", "Confirmación temporal baja", "Sentimiento bajista"],
                "recommendations": ["EVITAR señal", "Esperar confirmación más clara", "Revisar niveles clave"],
                "breakout_factor": 0.35,
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "level_tested": 15.50,
                "current_price": 15.45,
                "breakout_type": "BEARISH"
            }
        else:  # SOL-USD
            data = {
                "status": "INSUFFICIENT_DATA",
                "confidence": 0.20,
                "factors": {
                    "volume": 0.30,
                    "momentum": 0.15,
                    "time": 0.10,
                    "proximity": 0.40,
                    "volatility": 0.80,
                    "sentiment": 0.25
                },
                "warnings": ["Datos insuficientes para validación confiable"],
                "recommendations": ["Esperar más datos", "Usar análisis adicional"],
                "breakout_factor": 0.20,
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "level_tested": 180,
                "current_price": 182,
                "breakout_type": "NEUTRAL"
            }
        
        # Guardar archivo específico para el símbolo
        reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        filename = f"breakout_validation_{symbol.replace('-', '_')}.json"
        filepath = os.path.join(reports_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Generado: {filepath}")
    
    # También generar archivo por defecto
    default_data = {
        "status": "PENDING",
        "confidence": 0.70,
        "factors": {
            "volume": 0.65,
            "momentum": 0.75,
            "time": 0.80,
            "proximity": 0.85,
            "volatility": 0.90,
            "sentiment": 0.60
        },
        "warnings": ["Esperando confirmación de volumen"],
        "recommendations": ["Espere 1-2 velas de confirmación"],
        "breakout_factor": 0.75,
        "symbol": "DEFAULT",
        "timestamp": datetime.now().isoformat(),
        "level_tested": 50000,
        "current_price": 51000,
        "breakout_type": "BULLISH"
    }
    
    default_filepath = os.path.join(reports_dir, 'breakout_validation.json')
    with open(default_filepath, 'w') as f:
        json.dump(default_data, f, indent=2)
    
    print(f"✅ Generado: {default_filepath}")
    print("🎉 Datos de validación de rupturas generados exitosamente")

if __name__ == "__main__":
    generate_breakout_validation_data()