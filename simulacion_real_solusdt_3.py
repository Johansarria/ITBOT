#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulación SOLUSDT con datos reales de Binance - Terminal 3
"""

import sys
import os

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simulacion_real_binance import BinanceRealDataSimulator

def main():
    print("🚀 Iniciando simulación SOLUSDT con datos reales de Binance")
    print("📊 Terminal: 3")
    print("💰 Capital inicial: $1,000")
    print("⏰ Duración: 24 horas")
    print("📡 Fuente: API Binance en tiempo real")
    
    # Crear simulador
    simulator = BinanceRealDataSimulator(
        symbol="SOLUSDT",
        initial_capital=1000.0,
        terminal_id=3
    )
    
    # Ejecutar simulación indefinidamente
    simulator.run_simulation()

if __name__ == "__main__":
    main()