# /src/test_detector_rupturas.py

import pandas as pd
import numpy as np
from datetime import datetime
from binance_data_provider import BinanceDataProvider

def test_detector_rupturas():
    """Probar el detector de rupturas de forma simplificada"""
    print("🔥" * 60)
    print("🚀 PRUEBA DEL DETECTOR DE RUPTURAS DE VELAS 🚀".center(60))
    print("🔥" * 60)
    print()
    
    # Inicializar proveedor de datos
    data_provider = BinanceDataProvider()
    simbolos = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
    
    print("📊 ANÁLISIS DE RUPTURAS POR SÍMBOLO:")
    print("─" * 60)
    
    for simbolo in simbolos:
        try:
            # Obtener datos
            df = data_provider.get_historical_data(simbolo, '1h', limit=50)
            
            if df is None or len(df) < 20:
                print(f"❌ {simbolo}: Sin datos suficientes")
                continue
                
            # Análisis básico
            precio_actual = df['close'].iloc[-1]
            precio_anterior = df['close'].iloc[-2]
            cambio_pct = ((precio_actual - precio_anterior) / precio_anterior) * 100
            
            # Calcular niveles básicos
            max_20 = df['high'].tail(20).max()
            min_20 = df['low'].tail(20).min()
            
            # Detectar proximidad a niveles
            dist_max = abs(precio_actual - max_20) / max_20 * 100
            dist_min = abs(precio_actual - min_20) / min_20 * 100
            
            # Volumen
            volumen_actual = df['volume'].iloc[-1]
            volumen_promedio = df['volume'].tail(20).mean()
            vol_ratio = volumen_actual / volumen_promedio
            
            # RSI básico
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_actual = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
            
            # Determinar estado
            estado = "⚪ NEUTRAL"
            if dist_max < 1 and cambio_pct > 0.5 and vol_ratio > 1.2:
                estado = "🚀 POSIBLE RUPTURA ALCISTA"
            elif dist_min < 1 and cambio_pct < -0.5 and vol_ratio > 1.2:
                estado = "📉 POSIBLE RUPTURA BAJISTA"
            elif precio_actual > max_20 and vol_ratio > 1.5:
                estado = "✅ RUPTURA ALCISTA CONFIRMADA"
            elif precio_actual < min_20 and vol_ratio > 1.5:
                estado = "❌ RUPTURA BAJISTA CONFIRMADA"
            
            print(f"{simbolo:<10} ${precio_actual:<10.4f} {cambio_pct:+6.2f}% "
                  f"RSI:{rsi_actual:5.1f} Vol:{vol_ratio:4.1f}x {estado}")
                  
        except Exception as e:
            print(f"❌ {simbolo}: Error - {e}")
    
    print("─" * 60)
    print(f"🕒 Análisis completado: {datetime.now().strftime('%H:%M:%S')}")
    print("─" * 60)

if __name__ == "__main__":
    test_detector_rupturas()