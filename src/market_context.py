import requests
from datetime import datetime, timezone

def get_market_context():
    try:
        # Datos de BTC para correlación
        btc_url = 'https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT'
        btc_response = requests.get(btc_url)
        btc_data = btc_response.json()
        
        print("=== CONTEXTO DEL MERCADO ===")
        btc_price = float(btc_data["lastPrice"])
        btc_change = float(btc_data["priceChangePercent"])
        print(f"BTC: ${btc_price:,.0f} ({btc_change:+.2f}%)")
        
        # Dominancia y correlación
        eth_change = -1.98
        correlation = "POSITIVA" if (eth_change > 0 and btc_change > 0) or (eth_change < 0 and btc_change < 0) else "NEGATIVA"
        print(f"Correlación ETH/BTC: {correlation}")
        
        # Horario de trading
        current_hour = datetime.now(timezone.utc).hour
        if 13 <= current_hour <= 16:
            session = "SESIÓN EUROPEA (Alta actividad)"
        elif 20 <= current_hour <= 23:
            session = "SESIÓN AMERICANA (Alta actividad)"
        elif 0 <= current_hour <= 3:
            session = "OVERLAP USA-ASIA (Moderada)"
        else:
            session = "SESIÓN ASIÁTICA (Baja actividad)"
        
        print(f"Sesión actual: {session}")
        time_str = datetime.now(timezone.utc).strftime("%H:%M")
        print(f"Hora UTC: {time_str}")
        
        # Análisis de sentimiento basado en cambios
        if btc_change < -2 and eth_change < -2:
            sentiment = "BEARISH FUERTE"
        elif btc_change < 0 and eth_change < 0:
            sentiment = "BEARISH MODERADO"
        elif btc_change > 2 and eth_change > 2:
            sentiment = "BULLISH FUERTE"
        elif btc_change > 0 and eth_change > 0:
            sentiment = "BULLISH MODERADO"
        else:
            sentiment = "NEUTRAL/MIXTO"
            
        print(f"Sentimiento general: {sentiment}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_market_context()