#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis Rápido de Pares - Datos de Hoy
Obtiene datos actuales de Binance para determinar mejores pares
"""

import requests
import json
from datetime import datetime
import time

def get_binance_24h_stats():
    """Obtiene estadísticas de 24h de Binance"""
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error obteniendo datos: {e}")
        return []

def analyze_top_pairs():
    """Analiza los mejores pares basado en datos actuales"""
    print("🔍 ANÁLISIS RÁPIDO DE PARES - DATOS DE HOY")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Pares que han mostrado buen rendimiento histórico
    target_pairs = ['SOLUSDT', 'BNBUSDT', 'ADAUSDT', 'ETHUSDT', 'BTCUSDT']
    
    data = get_binance_24h_stats()
    
    if not data:
        print("❌ No se pudieron obtener datos")
        return
    
    # Filtrar solo nuestros pares objetivo
    filtered_data = [item for item in data if item['symbol'] in target_pairs]
    
    # Ordenar por cambio de precio 24h
    filtered_data.sort(key=lambda x: float(x['priceChangePercent']), reverse=True)
    
    print("\n🏆 TOP PARES PARA HOY (basado en datos actuales):")
    print("=" * 50)
    
    results = []
    
    for i, pair in enumerate(filtered_data, 1):
        symbol = pair['symbol']
        price = float(pair['lastPrice'])
        change_24h = float(pair['priceChangePercent'])
        volume = float(pair['volume'])
        quote_volume = float(pair['quoteVolume'])
        high = float(pair['highPrice'])
        low = float(pair['lowPrice'])
        
        # Calcular volatilidad del día
        volatility = ((high - low) / price) * 100
        
        # Score simple basado en múltiples factores
        score = 0
        
        # Cambio positivo suma puntos
        if change_24h > 0:
            score += min(change_24h * 2, 10)
        
        # Volatilidad controlada (2-8% es ideal)
        if 2 <= volatility <= 8:
            score += 5
        elif volatility > 8:
            score += 2
        
        # Volumen alto suma puntos
        if quote_volume > 100000000:  # >100M
            score += 3
        elif quote_volume > 50000000:  # >50M
            score += 2
        
        result = {
            'rank': i,
            'symbol': symbol,
            'price': price,
            'change_24h': change_24h,
            'volatility': volatility,
            'volume_24h': quote_volume,
            'score': round(score, 2)
        }
        
        results.append(result)
        
        print(f"\n#{i} {symbol}")
        print(f"   💰 Precio: ${price:,.4f}")
        print(f"   📈 Cambio 24h: {change_24h:+.2f}%")
        print(f"   📊 Volatilidad: {volatility:.2f}%")
        print(f"   💹 Volumen: ${quote_volume:,.0f}")
        print(f"   🎯 Score: {score:.2f}/20")
    
    # Reordenar por score
    results.sort(key=lambda x: x['score'], reverse=True)
    
    print("\n\n🎯 RECOMENDACIÓN FINAL (por score):")
    print("=" * 40)
    
    for i, result in enumerate(results[:3], 1):
        print(f"{i}. {result['symbol']} - Score: {result['score']}/20")
    
    # Guardar resultados
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"analisis_rapido_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Resultados guardados en: {filename}")
    
    # Recomendación específica
    print("\n💡 RECOMENDACIÓN PARA OBJETIVO 20-30% MENSUAL:")
    print("=" * 50)
    
    top_3 = results[:3]
    
    print(f"🥇 Principal: {top_3[0]['symbol']} (Score: {top_3[0]['score']})")
    print(f"🥈 Secundario: {top_3[1]['symbol']} (Score: {top_3[1]['score']})")
    print(f"🥉 Terciario: {top_3[2]['symbol']} (Score: {top_3[2]['score']})")
    
    print("\n📋 Distribución sugerida:")
    print(f"   • 50% en {top_3[0]['symbol']}")
    print(f"   • 30% en {top_3[1]['symbol']}")
    print(f"   • 20% en {top_3[2]['symbol']}")
    
    return results

def main():
    """Función principal"""
    try:
        results = analyze_top_pairs()
        print("\n🏁 Análisis completado exitosamente")
    except Exception as e:
        print(f"❌ Error en análisis: {e}")

if __name__ == "__main__":
    main()