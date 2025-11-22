#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIMULACIÓN DE ANÁLISIS PERDIDO
==============================
Simula qué habría pasado en el análisis de las 08:00 UTC de hoy
"""

import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

def load_config():
    """Carga la configuración"""
    try:
        with open('first_candle_strategy_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error cargando configuración: {e}")
        return None

def get_binance_klines(symbol, interval='1h', limit=100):
    """Obtiene datos históricos de Binance"""
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Convertir a DataFrame
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Convertir tipos de datos
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        
        # Convertir timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df.set_index('timestamp', inplace=True)
        
        return df
        
    except Exception as e:
        print(f"Error obteniendo datos para {symbol}: {e}")
        return None

def calculate_indicators(df):
    """Calcula indicadores técnicos básicos"""
    try:
        # Volumen promedio
        df['volume_avg'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_avg']
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        
        # Bandas de Bollinger
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # Momentum
        df['momentum'] = df['close'] / df['close'].shift(14) - 1
        
        return df
        
    except Exception as e:
        print(f"Error calculando indicadores: {e}")
        return df

def analyze_missed_opportunity():
    """Analiza qué habría pasado a las 08:00 UTC de hoy"""
    config = load_config()
    if not config:
        return
    
    print("="*70)
    print("SIMULACIÓN DE ANÁLISIS PERDIDO - 19 OCTUBRE 2025, 08:00 UTC")
    print("="*70)
    
    # Hora del análisis perdido
    today_utc = datetime.now(pytz.UTC).replace(hour=8, minute=0, second=0, microsecond=0)
    print(f"Analizando condiciones a las: {today_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    symbols = config['symbols']
    breakout_threshold = config['strategy_parameters']['breakout_threshold']
    volume_multiplier = config['strategy_parameters']['volume_multiplier']
    
    print(f"Símbolos a analizar: {symbols}")
    print(f"Umbral de breakout: {breakout_threshold*100:.1f}%")
    print(f"Multiplicador de volumen: {volume_multiplier}x")
    
    signals_found = []
    
    for symbol in symbols:
        print(f"\n📊 Analizando {symbol}...")
        
        # Obtener datos
        df = get_binance_klines(symbol, interval='1h', limit=50)
        if df is None:
            continue
        
        # Calcular indicadores
        df = calculate_indicators(df)
        
        # Encontrar la vela de las 08:00 UTC
        target_time = today_utc
        
        # Buscar la vela más cercana a las 08:00 UTC
        time_diffs = abs(df.index - target_time)
        closest_idx = df.index[time_diffs.argmin()]
        
        if closest_idx not in df.index:
            print(f"  ❌ No se encontró vela para {target_time}")
            continue
        
        # Obtener datos de la vela
        current_row = df.loc[closest_idx]
        prev_idx = df.index.get_loc(closest_idx) - 1
        
        if prev_idx < 0:
            print(f"  ❌ No hay vela anterior para comparar")
            continue
        
        prev_row = df.iloc[prev_idx]
        
        # Calcular cambio de precio
        price_change = (current_row['close'] - prev_row['close']) / prev_row['close']
        
        print(f"  🕐 Vela encontrada: {closest_idx.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"  💰 Precio anterior: ${prev_row['close']:.4f}")
        print(f"  💰 Precio actual: ${current_row['close']:.4f}")
        print(f"  📈 Cambio de precio: {price_change*100:.2f}%")
        
        # Verificar condiciones de breakout
        breakout_condition = abs(price_change) >= breakout_threshold
        
        # Verificar volumen
        volume_condition = False
        if not pd.isna(current_row['volume_ratio']):
            volume_condition = current_row['volume_ratio'] >= volume_multiplier
            print(f"  📊 Ratio de volumen: {current_row['volume_ratio']:.2f}x")
        else:
            print(f"  📊 Ratio de volumen: N/A")
        
        # Verificar indicadores técnicos
        rsi_ok = not pd.isna(current_row['rsi'])
        macd_ok = not pd.isna(current_row['macd'])
        
        if rsi_ok:
            print(f"  📊 RSI: {current_row['rsi']:.1f}")
        if macd_ok:
            print(f"  📊 MACD: {current_row['macd']:.6f}")
        
        # Determinar si habría señal
        if breakout_condition and volume_condition and rsi_ok and macd_ok:
            signal_type = "BULLISH" if price_change > 0 else "BEARISH"
            signals_found.append({
                'symbol': symbol,
                'type': signal_type,
                'price_change': price_change,
                'volume_ratio': current_row['volume_ratio'],
                'rsi': current_row['rsi'],
                'price': current_row['close']
            })
            print(f"  ✅ SEÑAL DETECTADA: {signal_type} BREAKOUT")
        else:
            reasons = []
            if not breakout_condition:
                reasons.append(f"Cambio insuficiente ({abs(price_change)*100:.2f}% < {breakout_threshold*100:.1f}%)")
            if not volume_condition:
                reasons.append(f"Volumen insuficiente")
            if not rsi_ok or not macd_ok:
                reasons.append("Indicadores técnicos inválidos")
            
            print(f"  ❌ Sin señal: {', '.join(reasons)}")
    
    print("\n" + "="*70)
    print("RESUMEN DE ANÁLISIS")
    print("="*70)
    
    if signals_found:
        print(f"🎯 SEÑALES ENCONTRADAS: {len(signals_found)}")
        for signal in signals_found:
            print(f"  • {signal['symbol']}: {signal['type']} ({signal['price_change']*100:+.2f}%)")
            print(f"    Precio: ${signal['price']:.4f}, Volumen: {signal['volume_ratio']:.2f}x, RSI: {signal['rsi']:.1f}")
        
        print(f"\n💡 CONCLUSIÓN: El sistema HABRÍA GENERADO {len(signals_found)} trade(s) a las 08:00 UTC")
    else:
        print("❌ NO SE ENCONTRARON SEÑALES VÁLIDAS")
        print("💡 CONCLUSIÓN: El sistema NO habría generado trades a las 08:00 UTC")
        print("   Las condiciones de mercado no cumplían con los criterios de la estrategia")
    
    print(f"\n⚠️  IMPORTANTE: Para capturar estas oportunidades, el sistema debe estar")
    print(f"   ejecutándose continuamente, especialmente a las 08:00 UTC")

if __name__ == "__main__":
    analyze_missed_opportunity()