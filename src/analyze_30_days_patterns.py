import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
import json

def get_30_day_analysis():
    try:
        print("🔍 ANALIZANDO PATRONES ETHUSDT - ÚLTIMOS 30 DÍAS")
        print("=" * 60)
        
        # Calcular timestamps para 30 días
        end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
        start_time = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp() * 1000)
        
        # 1. OBTENER DATOS HISTÓRICOS (1h para mejor análisis)
        print("\n📊 OBTENIENDO DATOS HISTÓRICOS...")
        klines_url = f'https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=1h&startTime={start_time}&endTime={end_time}&limit=1000'
        response = requests.get(klines_url)
        klines_data = response.json()
        
        # Convertir a DataFrame
        df = pd.DataFrame(klines_data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])
        
        # Convertir tipos
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['date'] = df['datetime'].dt.date
        df['hour'] = df['datetime'].dt.hour
        df['day_of_week'] = df['datetime'].dt.dayofweek  # 0=Monday, 6=Sunday
        
        print(f"✅ Datos obtenidos: {len(df)} velas de 1h")
        print(f"📅 Período: {df['datetime'].min()} a {df['datetime'].max()}")
        
        # 2. ANÁLISIS DE RANGOS Y NIVELES
        print("\n🎯 ANÁLISIS DE NIVELES CLAVE...")
        
        # Niveles de soporte y resistencia
        max_price = df['high'].max()
        min_price = df['low'].min()
        current_price = df['close'].iloc[-1]
        
        # Calcular niveles psicológicos
        psychological_levels = []
        for level in range(int(min_price//100)*100, int(max_price//100)*100 + 200, 50):
            if level > 0:
                psychological_levels.append(level)
        
        print(f"💰 Rango 30 días: ${min_price:,.0f} - ${max_price:,.0f}")
        print(f"📈 Amplitud total: {((max_price - min_price) / min_price) * 100:.1f}%")
        print(f"🎯 Precio actual: ${current_price:,.0f}")
        
        # 3. ANÁLISIS DE VOLATILIDAD POR DÍAS
        print("\n📊 ANÁLISIS DE VOLATILIDAD DIARIA...")
        
        daily_stats = df.groupby('date').agg({
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'open': 'first'
        }).reset_index()
        
        daily_stats['daily_range'] = daily_stats['high'] - daily_stats['low']
        daily_stats['daily_change_pct'] = ((daily_stats['close'] - daily_stats['open']) / daily_stats['open']) * 100
        daily_stats['volatility'] = (daily_stats['daily_range'] / daily_stats['open']) * 100
        
        avg_volatility = daily_stats['volatility'].mean()
        max_volatility = daily_stats['volatility'].max()
        
        print(f"📊 Volatilidad promedio diaria: {avg_volatility:.2f}%")
        print(f"📊 Volatilidad máxima: {max_volatility:.2f}%")
        
        # Días más volátiles
        top_volatile_days = daily_stats.nlargest(5, 'volatility')[['date', 'volatility', 'daily_change_pct']]
        print(f"\n🔥 TOP 5 DÍAS MÁS VOLÁTILES:")
        for _, row in top_volatile_days.iterrows():
            print(f"   {row['date']}: {row['volatility']:.2f}% (cambio: {row['daily_change_pct']:+.2f}%)")
        
        # 4. ANÁLISIS POR HORARIOS
        print("\n⏰ ANÁLISIS DE PATRONES HORARIOS...")
        
        hourly_stats = df.groupby('hour').agg({
            'volume': 'mean',
            'high': 'mean',
            'low': 'mean',
            'close': 'mean'
        }).reset_index()
        
        hourly_stats['hourly_range'] = hourly_stats['high'] - hourly_stats['low']
        hourly_stats['volatility'] = (hourly_stats['hourly_range'] / hourly_stats['close']) * 100
        
        # Horarios más activos
        top_volume_hours = hourly_stats.nlargest(5, 'volume')[['hour', 'volume', 'volatility']]
        print(f"📈 HORARIOS DE MAYOR VOLUMEN (UTC):")
        for _, row in top_volume_hours.iterrows():
            hour_int = int(row['hour'])
            print(f"   {hour_int:02d}:00 - Vol: {row['volume']:,.0f} - Volatilidad: {row['volatility']:.3f}%")
        
        # Horarios más volátiles
        top_volatile_hours = hourly_stats.nlargest(5, 'volatility')[['hour', 'volatility', 'volume']]
        print(f"\n🔥 HORARIOS MÁS VOLÁTILES (UTC):")
        for _, row in top_volatile_hours.iterrows():
            hour_int = int(row['hour'])
            print(f"   {hour_int:02d}:00 - Volatilidad: {row['volatility']:.3f}% - Vol: {row['volume']:,.0f}")
        
        # 5. ANÁLISIS DE TENDENCIAS
        print("\n📈 ANÁLISIS DE TENDENCIAS...")
        
        # Calcular medias móviles
        df['sma_24'] = df['close'].rolling(window=24).mean()  # 24h
        df['sma_168'] = df['close'].rolling(window=168).mean()  # 7 días
        
        current_sma24 = df['sma_24'].iloc[-1]
        current_sma168 = df['sma_168'].iloc[-1]
        
        trend_24h = "ALCISTA" if current_price > current_sma24 else "BAJISTA"
        trend_7d = "ALCISTA" if current_price > current_sma168 else "BAJISTA"
        
        print(f"📊 Tendencia 24h (vs SMA24): {trend_24h}")
        print(f"📊 Tendencia 7d (vs SMA168): {trend_7d}")
        print(f"💹 SMA 24h: ${current_sma24:,.0f}")
        print(f"💹 SMA 7d: ${current_sma168:,.0f}")
        
        # 6. ANÁLISIS DE BREAKOUTS HISTÓRICOS
        print("\n🚀 ANÁLISIS DE BREAKOUTS HISTÓRICOS...")
        
        # Detectar breakouts significativos (>2% en 4h)
        df['price_change_4h'] = df['close'].pct_change(4) * 100
        breakouts = df[abs(df['price_change_4h']) > 2.0].copy()
        
        if len(breakouts) > 0:
            print(f"📊 Breakouts detectados (>2% en 4h): {len(breakouts)}")
            
            # Breakouts alcistas vs bajistas
            bullish_breakouts = breakouts[breakouts['price_change_4h'] > 2.0]
            bearish_breakouts = breakouts[breakouts['price_change_4h'] < -2.0]
            
            print(f"🟢 Breakouts alcistas: {len(bullish_breakouts)}")
            print(f"🔴 Breakouts bajistas: {len(bearish_breakouts)}")
            
            if len(bullish_breakouts) > 0:
                avg_bullish = bullish_breakouts['price_change_4h'].mean()
                print(f"   Promedio alcista: +{avg_bullish:.2f}%")
            
            if len(bearish_breakouts) > 0:
                avg_bearish = bearish_breakouts['price_change_4h'].mean()
                print(f"   Promedio bajista: {avg_bearish:.2f}%")
        
        # 7. NIVELES DE SOPORTE Y RESISTENCIA RECURRENTES
        print("\n🎯 NIVELES TÉCNICOS RECURRENTES...")
        
        # Encontrar niveles donde el precio rebotó múltiples veces
        price_levels = {}
        tolerance = 20  # $20 de tolerancia
        
        for _, row in df.iterrows():
            low_level = int(row['low'] / tolerance) * tolerance
            high_level = int(row['high'] / tolerance) * tolerance
            
            if low_level not in price_levels:
                price_levels[low_level] = {'touches': 0, 'type': 'support'}
            if high_level not in price_levels:
                price_levels[high_level] = {'touches': 0, 'type': 'resistance'}
            
            price_levels[low_level]['touches'] += 1
            price_levels[high_level]['touches'] += 1
        
        # Filtrar niveles con múltiples toques
        significant_levels = {k: v for k, v in price_levels.items() 
                            if v['touches'] >= 10 and k > min_price and k < max_price}
        
        # Ordenar por número de toques
        sorted_levels = sorted(significant_levels.items(), key=lambda x: x[1]['touches'], reverse=True)
        
        print(f"🎯 NIVELES MÁS SIGNIFICATIVOS (≥10 toques):")
        for level, data in sorted_levels[:8]:
            distance_from_current = ((level - current_price) / current_price) * 100
            print(f"   ${level:,.0f} - {data['touches']} toques ({distance_from_current:+.1f}% del precio actual)")
        
        return {
            'total_candles': len(df),
            'price_range': {'min': min_price, 'max': max_price, 'current': current_price},
            'volatility': {'avg': avg_volatility, 'max': max_volatility},
            'trends': {'24h': trend_24h, '7d': trend_7d},
            'breakouts': len(breakouts) if 'breakouts' in locals() else 0,
            'significant_levels': sorted_levels[:5]
        }
        
    except Exception as e:
        print(f"❌ Error en análisis: {e}")
        return None

if __name__ == "__main__":
    result = get_30_day_analysis()
    if result:
        print(f"\n✅ ANÁLISIS COMPLETADO")
        print(f"📊 Datos procesados: {result['total_candles']} velas")