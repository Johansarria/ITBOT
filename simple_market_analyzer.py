#!/usr/bin/env python3
"""
Análisis simplificado de mercado para micro-trading
- Usa métodos estándar de Binance API
- Evalúa BTCUSDT y ETHUSDT para nuevas posiciones
"""

from binance import Client
import os
from datetime import datetime
import json

def analyze_market_opportunity():
    """Análisis rápido de oportunidades"""
    
    client = Client(
        api_key=os.getenv('BINANCE_API_KEY'),
        api_secret=os.getenv('BINANCE_SECRET_KEY')
    )
    
    print("🔍 ANÁLISIS RÁPIDO DE OPORTUNIDADES")
    print("="*50)
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    
    try:
        # Estado de cuenta
        account_info = client.futures_account()
        available_balance = float(account_info['availableBalance'])
        
        print(f"\n💰 Balance disponible: ${available_balance:.2f}")
        print(f"🎯 Límite micro-trading: $0.75")
        print(f"💡 Margen utilizable: ${min(0.75, available_balance * 0.9):.2f}")
        
        # Posiciones actuales
        positions = client.futures_position_information()
        active_positions = [pos['symbol'] for pos in positions if float(pos['positionAmt']) != 0]
        
        print(f"\n📊 Posiciones actuales: {len(active_positions)}")
        if active_positions:
            print(f"   Activas: {', '.join(active_positions)}")
        
        # Símbolos disponibles
        allowed_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        available_symbols = [s for s in allowed_symbols if s not in active_positions]
        
        print(f"\n🎯 Símbolos disponibles: {', '.join(available_symbols)}")
        
        if not available_symbols:
            print("\n⚠️ No hay símbolos disponibles para nuevas posiciones")
            return
        
        # Análisis básico para cada símbolo
        print(f"\n📈 ANÁLISIS DE MERCADO:")
        
        opportunities = []
        
        for symbol in available_symbols:
            try:
                # Datos básicos usando métodos estándar
                ticker = client.get_ticker(symbol=symbol)
                klines = client.get_klines(symbol=symbol, interval='1h', limit=24)
                
                current_price = float(ticker['lastPrice'])
                price_change = float(ticker['priceChangePercent'])
                volume = float(ticker['quoteVolume'])
                
                # Calcular volatilidad simple (rango 24h)
                high_24h = float(ticker['highPrice'])
                low_24h = float(ticker['lowPrice'])
                volatility = ((high_24h - low_24h) / current_price) * 100
                
                # Análisis de tendencia simple (últimas 24 velas)
                closes = [float(k[4]) for k in klines]  # Precios de cierre
                if len(closes) >= 12:
                    recent_avg = sum(closes[-12:]) / 12  # Promedio últimas 12h
                    older_avg = sum(closes[-24:-12]) / 12  # Promedio 12h anteriores
                    trend = "ALCISTA" if recent_avg > older_avg else "BAJISTA"
                else:
                    trend = "INDEFINIDA"
                
                # Scoring simple
                score = 0
                details = []
                
                # Volumen (30 puntos)
                if volume > 1000000000:  # >$1B
                    score += 30
                    details.append("✅ Volumen alto")
                elif volume > 500000000:  # >$500M
                    score += 20
                    details.append("⚠️ Volumen medio")
                else:
                    details.append("❌ Volumen bajo")
                
                # Volatilidad (25 puntos)
                if 2 <= volatility <= 6:  # 2-6% rango óptimo
                    score += 25
                    details.append("✅ Volatilidad óptima")
                elif 1 <= volatility <= 8:  # Rango aceptable
                    score += 15
                    details.append("⚠️ Volatilidad aceptable")
                else:
                    details.append("❌ Volatilidad extrema")
                
                # Cambio precio 24h (20 puntos)
                if -2 <= price_change <= 5:  # Rango estable/positivo
                    score += 20
                    details.append("✅ Movimiento saludable")
                elif -5 <= price_change <= 8:
                    score += 10
                    details.append("⚠️ Movimiento moderado")
                else:
                    details.append("❌ Movimiento extremo")
                
                # Tendencia (25 puntos)
                if trend == "ALCISTA":
                    score += 25
                    details.append("✅ Tendencia alcista")
                elif trend == "BAJISTA":
                    score += 10
                    details.append("⚠️ Tendencia bajista")
                else:
                    details.append("❓ Tendencia indefinida")
                
                opportunity = {
                    'symbol': symbol,
                    'score': score,
                    'price': current_price,
                    'change_24h': price_change,
                    'volume_24h': volume,
                    'volatility': volatility,
                    'trend': trend,
                    'details': details,
                    'viable': score >= 60  # Mínimo 60 puntos
                }
                
                opportunities.append(opportunity)
                
                print(f"\n   📊 {symbol}:")
                print(f"      Precio: ${current_price:.4f} ({price_change:+.2f}%)")
                print(f"      Volumen: ${volume/1e6:.0f}M")
                print(f"      Volatilidad: {volatility:.1f}%")
                print(f"      Tendencia: {trend}")
                print(f"      Score: {score}/100")
                for detail in details:
                    print(f"      {detail}")
                
            except Exception as e:
                print(f"   ❌ {symbol}: Error - {e}")
        
        # Recomendación final
        viable_opportunities = [op for op in opportunities if op['viable']]
        
        print(f"\n" + "="*50)
        print("🎯 RECOMENDACIÓN FINAL")
        print("="*50)
        
        if viable_opportunities:
            # Ordenar por score
            best = max(viable_opportunities, key=lambda x: x['score'])
            
            print(f"✅ MEJOR OPORTUNIDAD: {best['symbol']}")
            print(f"📊 Score: {best['score']}/100")
            print(f"💰 Precio actual: ${best['price']:.4f}")
            print(f"📈 Cambio 24h: {best['change_24h']:+.2f}%")
            print(f"🎯 Tendencia: {best['trend']}")
            
            # Cálculo de posición básico
            max_usdt = min(0.75, available_balance * 0.9)
            suggested_leverage = 5  # Conservador
            position_value = max_usdt * suggested_leverage
            quantity = position_value / best['price']
            
            print(f"\n💡 SUGERENCIA DE POSICIÓN:")
            print(f"   Símbolo: {best['symbol']}")
            print(f"   Lado: LONG (basado en tendencia)")
            print(f"   Apalancamiento: {suggested_leverage}x")
            print(f"   Margen: ${max_usdt:.2f}")
            print(f"   Cantidad aprox: {quantity:.6f}")
            print(f"   Valor posición: ${position_value:.2f}")
            print(f"   Stop Loss: -2% (${position_value * 0.02:.2f})")
            print(f"   Take Profit: +3% (${position_value * 0.03:.2f})")
            
        else:
            print("⏸️ ESPERAR")
            print("Sin oportunidades de calidad suficiente.")
            print("Sugerencia: Revisar mercado en 15-30 minutos.")
            
            if opportunities:
                best_score = max(op['score'] for op in opportunities)
                print(f"Mejor score disponible: {best_score}/100 (mínimo: 60)")
        
    except Exception as e:
        print(f"❌ Error en análisis: {e}")

if __name__ == "__main__":
    analyze_market_opportunity()
