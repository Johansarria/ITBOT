import requests
import json
from datetime import datetime, timedelta

def get_binance_price(symbol):
    try:
        url = f'https://api.binance.com/api/v3/ticker/price?symbol={symbol}'
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return float(response.json()['price'])
    except:
        pass
    return None

def get_24h_data(symbol):
    try:
        url = f'https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}'
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

# Análisis de las posiciones fallidas
symbols = ['ADAUSDT', 'AVAXUSDT']
entry_prices = {'ADAUSDT': 0.64, 'AVAXUSDT': 19.36}
entry_time = '2025-10-21 22:23:00'  # Aproximado

print('=== ANÁLISIS DE OPERACIONES FALLIDAS ===')
print(f'Hora de entrada: {entry_time}')
print()

for symbol in symbols:
    print(f'--- {symbol} ---')
    current_price = get_binance_price(symbol)
    entry_price = entry_prices[symbol]
    
    if current_price:
        # Para posiciones SELL
        pnl_pct = ((entry_price - current_price) / entry_price) * 100
        stop_loss = entry_price * 1.02  # +2% para SELL
        take_profit = entry_price * 0.96  # -4% para SELL
        
        print(f'Precio entrada: ${entry_price:.4f}')
        print(f'Precio actual: ${current_price:.4f}')
        print(f'PnL: {pnl_pct:.2f}%')
        print(f'Stop Loss: ${stop_loss:.4f} (+2%)')
        print(f'Take Profit: ${take_profit:.4f} (-4%)')
        
        # Análisis del movimiento
        if current_price > stop_loss:
            price_change = ((current_price - entry_price) / entry_price) * 100
            print(f'❌ STOP LOSS ACTIVADO - Precio subió {price_change:.2f}%')
        elif current_price < take_profit:
            price_change = ((entry_price - current_price) / entry_price) * 100
            print(f'✅ TAKE PROFIT ALCANZADO - Precio bajó {price_change:.2f}%')
        else:
            print(f'⏳ Posición aún activa')
        
        # Datos de 24h para contexto
        data_24h = get_24h_data(symbol)
        if data_24h:
            price_change_24h = float(data_24h['priceChangePercent'])
            volume_24h = float(data_24h['volume'])
            high_24h = float(data_24h['highPrice'])
            low_24h = float(data_24h['lowPrice'])
            
            print(f'Cambio 24h: {price_change_24h:.2f}%')
            print(f'Volumen 24h: {volume_24h:,.0f}')
            print(f'Máximo 24h: ${high_24h:.4f}')
            print(f'Mínimo 24h: ${low_24h:.4f}')
    
    print()

print('=== ANÁLISIS DE FALLAS ===')
print('1. TIMING INCORRECTO: Las señales se ejecutaron en un momento de reversión alcista')
print('2. ANÁLISIS TÉCNICO DEFICIENTE: No se consideró el momentum alcista del mercado')
print('3. GESTIÓN DE RIESGO: Stop loss muy ajustado (2%) para la volatilidad del mercado')
print('4. CONTEXTO DE MERCADO: No se evaluó la tendencia general del mercado crypto')
print('5. CONFIRMACIÓN INSUFICIENTE: Se ejecutaron señales sin confirmación de múltiples timeframes')
print()
print('=== RECOMENDACIONES ===')
print('1. Implementar filtros de tendencia de mercado general')
print('2. Usar confirmación de múltiples timeframes (1h, 4h, 1d)')
print('3. Ajustar stop loss según volatilidad histórica del activo')
print('4. Añadir filtros de volumen y momentum')
print('5. Implementar análisis de correlación con BTC/ETH')