import requests
import json
from datetime import datetime, timezone

def get_binance_data():
    try:
        print("🔍 VALIDANDO DATOS CON BINANCE API...")
        
        # Ticker 24h para volumen
        ticker_url = 'https://api.binance.com/api/v3/ticker/24hr?symbol=ETHUSDT'
        ticker_response = requests.get(ticker_url)
        ticker_data = ticker_response.json()
        
        # Klines para análisis de velas (5m últimas 100 velas)
        klines_url = 'https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=5m&limit=100'
        klines_response = requests.get(klines_url)
        klines_data = klines_response.json()
        
        # Datos actuales
        current_price = float(ticker_data['lastPrice'])
        volume_24h = float(ticker_data['volume'])
        price_change_24h = float(ticker_data['priceChangePercent'])
        
        print("\n=== DATOS BINANCE ETHUSDT ===")
        print(f"Precio actual: ${current_price:,.2f}")
        print(f"Cambio 24h: {price_change_24h:+.2f}%")
        print(f"Volumen 24h: {volume_24h:,.0f} ETH")
        timestamp_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        print(f"Timestamp: {timestamp_str}")
        
        # Análisis de velas recientes
        recent_candles = klines_data[-20:]  # Últimas 20 velas de 5m
        volumes = [float(candle[5]) for candle in recent_candles]
        avg_volume = sum(volumes) / len(volumes)
        max_volume = max(volumes)
        
        print("\n=== ANÁLISIS VOLUMEN (5M) ===")
        print(f"Volumen promedio (20 velas): {avg_volume:,.0f}")
        print(f"Volumen máximo reciente: {max_volume:,.0f}")
        print(f"Ratio máx/promedio: {max_volume/avg_volume:.2f}x")
        
        # Niveles clave del gráfico
        prices = [float(candle[4]) for candle in recent_candles]  # Close prices
        resistance_3880 = 3880
        support_3840 = 3840
        support_3825 = 3825
        
        print("\n=== VALIDACIÓN NIVELES TÉCNICOS ===")
        status_3880 = "ACTIVA" if current_price < resistance_3880 else "ROTA"
        status_3840 = "MANTENIDO" if current_price > support_3840 else "ROTO"
        status_3825 = "LEJANO" if current_price > support_3825 + 20 else "CERCANO"
        
        print(f"Resistencia 3,880: {status_3880}")
        print(f"Soporte 3,840: {status_3840}")
        print(f"Soporte 3,825: {status_3825}")
        
        # Análisis de momentum
        print("\n=== ANÁLISIS DE MOMENTUM ===")
        last_5_prices = [float(candle[4]) for candle in klines_data[-5:]]
        momentum = ((last_5_prices[-1] - last_5_prices[0]) / last_5_prices[0]) * 100
        print(f"Momentum 5 velas: {momentum:+.2f}%")
        
        # Validación de breakout
        print("\n=== VALIDACIÓN BREAKOUT ===")
        if current_price > resistance_3880:
            print("✅ BREAKOUT CONFIRMADO - Precio por encima de 3,880")
            print(f"   Distancia del breakout: +{((current_price - resistance_3880) / resistance_3880) * 100:.2f}%")
        else:
            print("❌ SIN BREAKOUT - Precio aún bajo resistencia")
            print(f"   Distancia a resistencia: {((resistance_3880 - current_price) / current_price) * 100:.2f}%")
        
        # Análisis de volumen vs promedio
        current_volume = float(klines_data[-1][5])  # Última vela
        volume_ratio = current_volume / avg_volume
        
        print(f"\n=== CONFIRMACIÓN VOLUMEN ===")
        print(f"Volumen actual: {current_volume:,.0f}")
        print(f"Ratio vs promedio: {volume_ratio:.2f}x")
        
        if volume_ratio > 1.5:
            print("✅ VOLUMEN ELEVADO - Confirma movimiento")
        elif volume_ratio > 1.2:
            print("⚠️ VOLUMEN MODERADO - Movimiento débil")
        else:
            print("❌ VOLUMEN BAJO - Sin confirmación")
            
        return True
        
    except Exception as e:
        print(f"❌ Error obteniendo datos: {e}")
        return False

if __name__ == "__main__":
    get_binance_data()