import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

def analyze_btc_correlation():
    try:
        print("🔗 ANÁLISIS DE CORRELACIÓN ETH/BTC - 30 DÍAS")
        print("=" * 50)
        
        # Calcular timestamps para 30 días
        end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
        start_time = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp() * 1000)
        
        # Obtener datos de ETH y BTC
        print("📊 Obteniendo datos ETH y BTC...")
        
        # ETH data
        eth_url = f'https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=1h&startTime={start_time}&endTime={end_time}&limit=1000'
        eth_response = requests.get(eth_url)
        eth_data = eth_response.json()
        
        # BTC data
        btc_url = f'https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&startTime={start_time}&endTime={end_time}&limit=1000'
        btc_response = requests.get(btc_url)
        btc_data = btc_response.json()
        
        # Crear DataFrames
        eth_df = pd.DataFrame(eth_data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])
        
        btc_df = pd.DataFrame(btc_data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])
        
        # Convertir tipos y calcular cambios
        for df in [eth_df, btc_df]:
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Calcular cambios porcentuales
        eth_df['pct_change'] = eth_df['close'].pct_change() * 100
        btc_df['pct_change'] = btc_df['close'].pct_change() * 100
        
        # Merge por timestamp para correlación
        merged_df = pd.merge(eth_df[['timestamp', 'close', 'pct_change', 'volume']], 
                           btc_df[['timestamp', 'close', 'pct_change', 'volume']], 
                           on='timestamp', suffixes=('_eth', '_btc'))
        
        # Eliminar NaN
        merged_df = merged_df.dropna()
        
        print(f"✅ Datos sincronizados: {len(merged_df)} puntos")
        
        # 1. CORRELACIÓN GENERAL
        correlation = merged_df['pct_change_eth'].corr(merged_df['pct_change_btc'])
        print(f"\n📊 CORRELACIÓN ETH/BTC: {correlation:.3f}")
        
        if correlation > 0.7:
            corr_strength = "MUY FUERTE"
        elif correlation > 0.5:
            corr_strength = "FUERTE"
        elif correlation > 0.3:
            corr_strength = "MODERADA"
        else:
            corr_strength = "DÉBIL"
        
        print(f"💪 Fuerza de correlación: {corr_strength}")
        
        # 2. CORRELACIÓN POR PERÍODOS
        print(f"\n📈 CORRELACIÓN POR PERÍODOS:")
        
        # Últimos 7 días
        last_week = merged_df.tail(168)  # 7 días * 24 horas
        corr_7d = last_week['pct_change_eth'].corr(last_week['pct_change_btc'])
        print(f"   Últimos 7 días: {corr_7d:.3f}")
        
        # Últimos 3 días
        last_3d = merged_df.tail(72)  # 3 días * 24 horas
        corr_3d = last_3d['pct_change_eth'].corr(last_3d['pct_change_btc'])
        print(f"   Últimos 3 días: {corr_3d:.3f}")
        
        # Últimas 24 horas
        last_24h = merged_df.tail(24)
        corr_24h = last_24h['pct_change_eth'].corr(last_24h['pct_change_btc'])
        print(f"   Últimas 24 horas: {corr_24h:.3f}")
        
        # 3. ANÁLISIS DE DIVERGENCIAS
        print(f"\n🔄 ANÁLISIS DE DIVERGENCIAS:")
        
        # Detectar momentos donde ETH y BTC se mueven en direcciones opuestas
        merged_df['divergence'] = (
            (merged_df['pct_change_eth'] > 0) & (merged_df['pct_change_btc'] < 0)
        ) | (
            (merged_df['pct_change_eth'] < 0) & (merged_df['pct_change_btc'] > 0)
        )
        
        divergences = merged_df[merged_df['divergence']].copy()
        divergence_rate = (len(divergences) / len(merged_df)) * 100
        
        print(f"📊 Divergencias detectadas: {len(divergences)} ({divergence_rate:.1f}%)")
        
        # Divergencias significativas (>1% diferencia)
        significant_divergences = divergences[
            abs(divergences['pct_change_eth'] - divergences['pct_change_btc']) > 1.0
        ]
        
        print(f"🔥 Divergencias significativas (>1%): {len(significant_divergences)}")
        
        # 4. RATIO ETH/BTC
        print(f"\n⚖️ ANÁLISIS RATIO ETH/BTC:")
        
        merged_df['eth_btc_ratio'] = merged_df['close_eth'] / merged_df['close_btc']
        current_ratio = merged_df['eth_btc_ratio'].iloc[-1]
        avg_ratio = merged_df['eth_btc_ratio'].mean()
        ratio_change = ((current_ratio - avg_ratio) / avg_ratio) * 100
        
        print(f"📊 Ratio actual: {current_ratio:.6f}")
        print(f"📊 Ratio promedio 30d: {avg_ratio:.6f}")
        print(f"📊 Cambio vs promedio: {ratio_change:+.2f}%")
        
        if ratio_change > 5:
            ratio_status = "ETH SOBREPERFORMANDO"
        elif ratio_change < -5:
            ratio_status = "ETH UNDERPERFORMANDO"
        else:
            ratio_status = "ETH EN LÍNEA CON BTC"
        
        print(f"🎯 Status: {ratio_status}")
        
        # 5. ANÁLISIS DE VOLATILIDAD RELATIVA
        print(f"\n📊 VOLATILIDAD RELATIVA:")
        
        eth_volatility = merged_df['pct_change_eth'].std()
        btc_volatility = merged_df['pct_change_btc'].std()
        volatility_ratio = eth_volatility / btc_volatility
        
        print(f"📈 Volatilidad ETH: {eth_volatility:.3f}%")
        print(f"📈 Volatilidad BTC: {btc_volatility:.3f}%")
        print(f"⚖️ Ratio volatilidad: {volatility_ratio:.2f}x")
        
        # 6. PERFORMANCE COMPARATIVA
        print(f"\n🏆 PERFORMANCE 30 DÍAS:")
        
        eth_performance = ((merged_df['close_eth'].iloc[-1] - merged_df['close_eth'].iloc[0]) / 
                          merged_df['close_eth'].iloc[0]) * 100
        btc_performance = ((merged_df['close_btc'].iloc[-1] - merged_df['close_btc'].iloc[0]) / 
                          merged_df['close_btc'].iloc[0]) * 100
        
        print(f"🟢 ETH: {eth_performance:+.2f}%")
        print(f"🟠 BTC: {btc_performance:+.2f}%")
        
        if eth_performance > btc_performance:
            winner = "ETH GANADOR"
        elif btc_performance > eth_performance:
            winner = "BTC GANADOR"
        else:
            winner = "EMPATE"
        
        print(f"🏆 {winner}")
        
        return {
            'correlation': correlation,
            'correlation_strength': corr_strength,
            'correlations': {
                '7d': corr_7d,
                '3d': corr_3d,
                '24h': corr_24h
            },
            'divergences': len(divergences),
            'ratio_status': ratio_status,
            'performance': {
                'eth': eth_performance,
                'btc': btc_performance,
                'winner': winner
            }
        }
        
    except Exception as e:
        print(f"❌ Error en análisis de correlación: {e}")
        return None

if __name__ == "__main__":
    result = analyze_btc_correlation()
    if result:
        print(f"\n✅ ANÁLISIS DE CORRELACIÓN COMPLETADO")