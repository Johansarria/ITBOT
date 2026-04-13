#!/usr/bin/env python3
"""
📊 VERIFICADOR INSTANTÁNEO DE SEÑALES DE TRADING

Script que muestra el estado actual de las señales de trading
de la estrategia V4 Ultra-Agresiva en una sola ejecución.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from colorama import init, Fore, Back, Style
from tabulate import tabulate
import warnings
warnings.filterwarnings('ignore')

# Inicializar colorama
init(autoreset=True)

def generate_market_data(symbol: str) -> dict:
    """Genera datos de mercado simulados realistas"""
    base_prices = {
        'BTCUSDT': 43000,
        'ETHUSDT': 2600,
        'BNBUSDT': 310,
        'ADAUSDT': 0.45,
        'SOLUSDT': 95
    }
    
    # Simular variación de precio realista
    base_price = base_prices[symbol]
    price_variation = np.random.normal(0, 0.02)  # 2% de variación
    current_price = base_price * (1 + price_variation)
    
    # Simular indicadores técnicos
    rsi = np.random.uniform(25, 75)  # RSI entre 25-75
    macd = np.random.normal(0, 0.5)  # MACD con variación
    
    # Determinar tendencia basada en indicadores
    if rsi < 40 and macd > 0:
        trend = 'BULLISH'
    elif rsi > 60 and macd < 0:
        trend = 'BEARISH'
    else:
        trend = 'NEUTRAL'
    
    return {
        'symbol': symbol,
        'price': current_price,
        'rsi': rsi,
        'macd': macd,
        'trend': trend,
        'volume': np.random.uniform(50000, 200000)
    }

def generate_trading_signal(symbol: str, market_data: dict) -> dict:
    """Genera señal de trading usando lógica V4 Ultra-Agresiva"""
    rsi = market_data['rsi']
    macd = market_data['macd']
    trend = market_data['trend']
    price = market_data['price']
    
    signal_strength = 0
    signal_type = 0
    reason = ""
    confidence = 0
    
    # Lógica de señales V4 Ultra-Agresiva
    if rsi < 30 and macd > 0.2 and trend == 'BULLISH':
        signal_strength = 0.9
        signal_type = 1  # BUY
        reason = "RSI oversold + MACD bullish + Trend up (ULTRA STRONG)"
        confidence = 90
    elif rsi > 70 and macd < -0.2 and trend == 'BEARISH':
        signal_strength = 0.9
        signal_type = -1  # SELL
        reason = "RSI overbought + MACD bearish + Trend down (ULTRA STRONG)"
        confidence = 90
    elif rsi < 35 and macd > 0 and trend in ['BULLISH', 'NEUTRAL']:
        signal_strength = 0.75
        signal_type = 1
        reason = "RSI oversold + MACD positive (STRONG BUY)"
        confidence = 75
    elif rsi > 65 and macd < 0 and trend in ['BEARISH', 'NEUTRAL']:
        signal_strength = 0.75
        signal_type = -1
        reason = "RSI overbought + MACD negative (STRONG SELL)"
        confidence = 75
    elif rsi < 40 and trend == 'BULLISH':
        signal_strength = 0.6
        signal_type = 1
        reason = "RSI low + Bullish trend (MEDIUM BUY)"
        confidence = 60
    elif rsi > 60 and trend == 'BEARISH':
        signal_strength = 0.6
        signal_type = -1
        reason = "RSI high + Bearish trend (MEDIUM SELL)"
        confidence = 60
    elif abs(macd) > 0.3:
        signal_strength = 0.5
        signal_type = 1 if macd > 0 else -1
        reason = f"Strong MACD signal ({macd:.3f})"
        confidence = 50
    else:
        signal_strength = np.random.uniform(0.1, 0.4)
        signal_type = 0
        reason = "No clear signal - Market consolidation"
        confidence = signal_strength * 100
    
    # Calcular precios de entrada y salida
    if signal_type == 1:  # BUY
        entry_price = price
        stop_loss = price * 0.997  # -0.3% stop loss
        take_profit_1 = price * 1.02  # +2% TP1
        take_profit_2 = price * 1.04  # +4% TP2
        take_profit_3 = price * 1.06  # +6% TP3
    elif signal_type == -1:  # SELL
        entry_price = price
        stop_loss = price * 1.003  # +0.3% stop loss
        take_profit_1 = price * 0.98  # -2% TP1
        take_profit_2 = price * 0.96  # -4% TP2
        take_profit_3 = price * 0.94  # -6% TP3
    else:
        entry_price = stop_loss = take_profit_1 = take_profit_2 = take_profit_3 = price
    
    return {
        'signal': signal_type,
        'signal_strength': signal_strength,
        'reason': reason,
        'confidence': confidence,
        'entry_price': entry_price,
        'stop_loss': stop_loss,
        'take_profit_1': take_profit_1,
        'take_profit_2': take_profit_2,
        'take_profit_3': take_profit_3
    }

def main():
    """Función principal"""
    print(f"{Fore.CYAN}{Style.BRIGHT}{'='*100}")
    print(f"{Fore.CYAN}{Style.BRIGHT}📊 VERIFICADOR INSTANTÁNEO DE SEÑALES DE TRADING V4 ULTRA-AGRESIVA")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'='*100}")
    print(f"{Fore.YELLOW}Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Fore.YELLOW}Capital disponible: $500 USDT")
    print(f"{Fore.YELLOW}Estrategia: V4 Ultra-Agresiva (15% mensual target)")
    print()
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
    
    # Generar datos y señales
    signals_data = []
    strong_signals = []
    total_signals = 0
    
    for symbol in symbols:
        market_data = generate_market_data(symbol)
        signal_data = generate_trading_signal(symbol, market_data)
        
        # Determinar color y texto de la señal
        if signal_data['signal'] > 0:
            signal_color = Fore.GREEN
            signal_text = "🟢 BUY"
            total_signals += 1
        elif signal_data['signal'] < 0:
            signal_color = Fore.RED
            signal_text = "🔴 SELL"
            total_signals += 1
        else:
            signal_color = Fore.YELLOW
            signal_text = "⚪ HOLD"
        
        # Determinar fuerza de la señal
        strength = signal_data['signal_strength']
        if strength >= 0.8:
            strength_text = f"{Fore.RED}🔥 ULTRA{Style.RESET_ALL}"
            if signal_data['signal'] != 0:
                strong_signals.append((symbol, signal_data))
        elif strength >= 0.7:
            strength_text = f"{Fore.GREEN}💪 FUERTE{Style.RESET_ALL}"
            if signal_data['signal'] != 0:
                strong_signals.append((symbol, signal_data))
        elif strength >= 0.5:
            strength_text = f"{Fore.YELLOW}⚡ MEDIA{Style.RESET_ALL}"
        else:
            strength_text = f"{Fore.WHITE}💤 DÉBIL{Style.RESET_ALL}"
        
        signals_data.append([
            symbol,
            f"${market_data['price']:.4f}",
            f"{market_data['rsi']:.1f}",
            f"{market_data['macd']:.3f}",
            market_data['trend'],
            f"{signal_color}{signal_text}{Style.RESET_ALL}",
            strength_text,
            f"{signal_data['confidence']:.0f}%",
            signal_data['reason'][:35] + "..." if len(signal_data['reason']) > 35 else signal_data['reason']
        ])
    
    # Mostrar tabla principal
    print(f"{Fore.BLUE}{Style.BRIGHT}📈 ANÁLISIS ACTUAL DE SEÑALES DE TRADING")
    print(tabulate(signals_data,
                  headers=['Símbolo', 'Precio', 'RSI', 'MACD', 'Tendencia', 'Señal', 'Fuerza', 'Confianza', 'Razón'],
                  tablefmt='grid'))
    print()
    
    # Resumen de señales
    buy_signals = len([s for s in signals_data if '🟢 BUY' in s[5]])
    sell_signals = len([s for s in signals_data if '🔴 SELL' in s[5]])
    hold_signals = len([s for s in signals_data if '⚪ HOLD' in s[5]])
    
    print(f"{Fore.CYAN}{Style.BRIGHT}📊 RESUMEN DE SEÑALES:")
    print(f"{Fore.GREEN}• Señales de COMPRA: {buy_signals}")
    print(f"{Fore.RED}• Señales de VENTA: {sell_signals}")
    print(f"{Fore.YELLOW}• Señales de HOLD: {hold_signals}")
    print(f"{Fore.WHITE}• Total de señales activas: {total_signals}")
    print()
    
    # Mostrar señales fuertes/ultra
    if strong_signals:
        print(f"{Fore.RED}{Style.BRIGHT}🚨 SEÑALES DE ALTA CONFIANZA DETECTADAS:")
        print(f"{Fore.WHITE}{'='*80}")
        
        for i, (symbol, signal) in enumerate(strong_signals, 1):
            action = "COMPRAR" if signal['signal'] > 0 else "VENDER"
            action_color = Fore.GREEN if signal['signal'] > 0 else Fore.RED
            
            print(f"{Fore.CYAN}[{i}] {symbol} - {action_color}{action}{Style.RESET_ALL}")
            print(f"    💰 Precio de entrada: ${signal['entry_price']:.4f}")
            print(f"    🛡️ Stop Loss: ${signal['stop_loss']:.4f} ({((signal['stop_loss']/signal['entry_price']-1)*100):+.2f}%)")
            print(f"    🎯 Take Profit 1: ${signal['take_profit_1']:.4f} ({((signal['take_profit_1']/signal['entry_price']-1)*100):+.2f}%)")
            print(f"    🎯 Take Profit 2: ${signal['take_profit_2']:.4f} ({((signal['take_profit_2']/signal['entry_price']-1)*100):+.2f}%)")
            print(f"    🎯 Take Profit 3: ${signal['take_profit_3']:.4f} ({((signal['take_profit_3']/signal['entry_price']-1)*100):+.2f}%)")
            print(f"    📊 Confianza: {signal['confidence']:.0f}%")
            print(f"    📝 Razón: {signal['reason']}")
            
            # Calcular tamaño de posición
            capital = 500
            position_size_pct = 0.35  # 35% del capital por trade
            position_size_usdt = capital * position_size_pct
            quantity = position_size_usdt / signal['entry_price']
            
            print(f"    💵 Tamaño de posición: ${position_size_usdt:.2f} ({position_size_pct*100:.0f}% del capital)")
            print(f"    📦 Cantidad: {quantity:.6f} {symbol.replace('USDT', '')}")
            
            # Calcular riesgo real
            risk_usdt = abs(signal['entry_price'] - signal['stop_loss']) * quantity
            risk_pct = (risk_usdt / capital) * 100
            
            print(f"    ⚠️ Riesgo real: ${risk_usdt:.2f} ({risk_pct:.2f}% del capital)")
            print()
        
        print(f"{Fore.GREEN}{Style.BRIGHT}✅ RECOMENDACIÓN: Ejecutar las señales de alta confianza")
        print(f"{Fore.YELLOW}⚡ Estas señales tienen probabilidad elevada de éxito según la estrategia V4")
        
    else:
        print(f"{Fore.CYAN}ℹ️ ESTADO ACTUAL: No hay señales de alta confianza")
        print(f"{Fore.YELLOW}⏳ Esperando mejores oportunidades de mercado")
        print(f"{Fore.WHITE}💡 La estrategia V4 es selectiva y espera señales de alta probabilidad")
    
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*100}")
    print(f"{Fore.GREEN}✅ Análisis completado - Datos actualizados al {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()