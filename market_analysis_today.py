#!/usr/bin/env python3
"""
Análisis completo del mercado actual con proyecciones para hoy
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta
sys.path.insert(0, os.path.abspath('.'))

import config
from utils.binance_client import get_binance_client
from utils.risk_manager import cargar_umbrales_optimizado

async def market_analysis_today():
    print("📊 ANÁLISIS DEL MERCADO ACTUAL - PROYECCIÓN HOY")
    print("=" * 70)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Configuración del sistema
    print(f"\n🎯 CONFIGURACIÓN ACTUAL:")
    max_usdt = config.settings.MICRO_TRADE_MAX_USDT
    leverage = config.settings.MICRO_TRADE_LEVERAGE
    tp_pct = config.settings.RISK_PER_TRADE_TAKE_PROFIT_PCT
    sl_pct = config.settings.RISK_PER_TRADE_STOP_LOSS_PCT
    min_roi = config.settings.MIN_ROI_ON_MARGIN_FOR_ENTRY_PCT
    ml_threshold_high = config.settings.ML_THRESHOLD_HIGH
    ml_threshold_low = config.settings.ML_THRESHOLD_LOW
    
    print(f"   💰 Capital por trade: ${max_usdt}")
    print(f"   📈 Leverage: {leverage}x")
    print(f"   🎯 Take Profit: {tp_pct}%")
    print(f"   🛑 Stop Loss: {sl_pct}%")
    print(f"   📊 ROI Mínimo: {min_roi}%")
    print(f"   🤖 ML Umbral Alto: {ml_threshold_high}")
    print(f"   🤖 ML Umbral Bajo: {ml_threshold_low}")
    
    # Calcular ROI real
    margin_used = max_usdt / leverage
    tp_gain_usdt = max_usdt * (tp_pct / 100)
    sl_loss_usdt = max_usdt * (sl_pct / 100)
    roi_tp = (tp_gain_usdt / margin_used * 100.0)
    roi_sl = (sl_loss_usdt / margin_used * 100.0)
    
    print(f"   💚 ROI si gana: +{roi_tp:.1f}%")
    print(f"   🔴 ROI si pierde: -{roi_sl:.1f}%")
    print(f"   📊 Risk/Reward: 1:{tp_pct/sl_pct:.1f}")
    
    # 2. Análisis de pares principales
    symbols = config.settings.ASSETS_TO_TRADE
    print(f"\n📈 ANÁLISIS DE PARES PRINCIPALES:")
    
    try:
        client = await get_binance_client()
        market_analysis = {}
        
        for symbol in symbols:
            try:
                print(f"\n🔍 {symbol}:")
                
                # Obtener precio actual
                ticker = await client.get_symbol_ticker(symbol=symbol)
                current_price = float(ticker['price'])
                print(f"   💲 Precio actual: ${current_price:,.2f}")
                
                # Obtener estadísticas 24h
                stats_24h = await client.get_ticker(symbol=symbol)
                price_change_24h = float(stats_24h['priceChangePercent'])
                volume_24h = float(stats_24h['volume'])
                high_24h = float(stats_24h['highPrice'])
                low_24h = float(stats_24h['lowPrice'])
                
                print(f"   📊 Cambio 24h: {price_change_24h:+.2f}%")
                print(f"   📦 Volumen 24h: {volume_24h:,.0f}")
                print(f"   ⬆️  Alto 24h: ${high_24h:,.2f}")
                print(f"   ⬇️  Bajo 24h: ${low_24h:,.2f}")
                
                # Calcular volatilidad
                volatility = ((high_24h - low_24h) / current_price) * 100
                print(f"   🌊 Volatilidad: {volatility:.2f}%")
                
                # Análisis técnico básico
                range_position = ((current_price - low_24h) / (high_24h - low_24h)) * 100
                print(f"   📍 Posición en rango: {range_position:.1f}%")
                
                # Clasificar señal
                if price_change_24h > 2:
                    trend_signal = "🟢 FUERTE ALCISTA"
                    signal_strength = "ALTA"
                elif price_change_24h > 0.5:
                    trend_signal = "🔵 ALCISTA"  
                    signal_strength = "MEDIA"
                elif price_change_24h > -0.5:
                    trend_signal = "⚪ LATERAL"
                    signal_strength = "BAJA"
                elif price_change_24h > -2:
                    trend_signal = "🔴 BAJISTA"
                    signal_strength = "MEDIA"
                else:
                    trend_signal = "⚫ FUERTE BAJISTA"
                    signal_strength = "ALTA"
                
                print(f"   📡 Señal: {trend_signal}")
                
                # Evaluar oportunidad para nuestro sistema
                opportunity_score = 0
                
                # Factor 1: Volatilidad (necesitamos movimiento para TP)
                if volatility >= 3:
                    opportunity_score += 30
                elif volatility >= 2:
                    opportunity_score += 20
                elif volatility >= 1:
                    opportunity_score += 10
                
                # Factor 2: Volumen (liquidez)
                if volume_24h >= 100000:
                    opportunity_score += 25
                elif volume_24h >= 50000:
                    opportunity_score += 15
                elif volume_24h >= 10000:
                    opportunity_score += 10
                
                # Factor 3: Tendencia clara
                if abs(price_change_24h) >= 1:
                    opportunity_score += 20
                elif abs(price_change_24h) >= 0.5:
                    opportunity_score += 10
                
                # Factor 4: Posición en rango
                if range_position > 80 or range_position < 20:
                    opportunity_score += 15  # Posible reversión
                elif 40 <= range_position <= 60:
                    opportunity_score += 10  # Posición neutral
                
                # Factor 5: Momentum
                if signal_strength == "ALTA":
                    opportunity_score += 10
                
                opportunity_score = min(opportunity_score, 100)
                
                print(f"   🎯 Score Oportunidad: {opportunity_score}/100")
                
                # Clasificar oportunidad
                if opportunity_score >= 70:
                    opportunity_level = "🟢 EXCELENTE"
                elif opportunity_score >= 50:
                    opportunity_level = "🔵 BUENA"
                elif opportunity_score >= 30:
                    opportunity_level = "🟡 MODERADA"
                else:
                    opportunity_level = "🔴 BAJA"
                
                print(f"   📊 Nivel: {opportunity_level}")
                
                market_analysis[symbol] = {
                    'price': current_price,
                    'change_24h': price_change_24h,
                    'volume': volume_24h,
                    'volatility': volatility,
                    'range_position': range_position,
                    'signal': trend_signal,
                    'signal_strength': signal_strength,
                    'opportunity_score': opportunity_score,
                    'opportunity_level': opportunity_level
                }
                
            except Exception as e:
                print(f"   ❌ Error analizando {symbol}: {e}")
                
    except Exception as e:
        print(f"❌ Error conectando a Binance: {e}")
        return
    
    # 3. Proyección para hoy
    print(f"\n🔮 PROYECCIÓN PARA HOY:")
    print("=" * 50)
    
    # Calcular promedios
    total_scores = [data['opportunity_score'] for data in market_analysis.values()]
    avg_opportunity = sum(total_scores) / len(total_scores) if total_scores else 0
    
    high_volatility_pairs = [s for s, data in market_analysis.items() if data['volatility'] >= 2]
    trending_pairs = [s for s, data in market_analysis.items() if abs(data['change_24h']) >= 1]
    excellent_opportunities = [s for s, data in market_analysis.items() if data['opportunity_score'] >= 70]
    
    print(f"📊 Score Promedio del Mercado: {avg_opportunity:.1f}/100")
    print(f"🌊 Pares con Alta Volatilidad: {len(high_volatility_pairs)} ({high_volatility_pairs})")
    print(f"📈 Pares con Tendencia Fuerte: {len(trending_pairs)} ({trending_pairs})")
    print(f"🎯 Oportunidades Excelentes: {len(excellent_opportunities)} ({excellent_opportunities})")
    
    # Calcular probabilidades basadas en nuestro sistema
    base_accuracy = 65  # Asumiendo 65% de precisión base del ML
    
    # Ajustar por condiciones de mercado
    if avg_opportunity >= 70:
        market_boost = 15
        market_condition = "🟢 FAVORABLE"
    elif avg_opportunity >= 50:
        market_boost = 8
        market_condition = "🔵 NEUTRAL-POSITIVO"
    elif avg_opportunity >= 30:
        market_boost = 0
        market_condition = "🟡 NEUTRAL"
    else:
        market_boost = -10
        market_condition = "🔴 DESAFIANTE"
    
    projected_accuracy = min(base_accuracy + market_boost, 85)  # Máximo 85%
    
    print(f"\n🎯 PROYECCIONES PARA HOY:")
    print(f"   📈 Condición del Mercado: {market_condition}")
    print(f"   🎯 Precisión Proyectada: {projected_accuracy}%")
    print(f"   📊 Confianza del Sistema: {min(avg_opportunity, 90):.0f}%")
    
    # Calcular escenarios de ganancia/pérdida
    num_trades_possible = min(len(symbols), 5)  # Máximo 5 trades por día
    
    print(f"\n💰 ESCENARIOS DE TRADING (hasta {num_trades_possible} trades):")
    
    # Escenario Optimista (70% win rate)
    optimistic_wins = int(num_trades_possible * 0.7)
    optimistic_losses = num_trades_possible - optimistic_wins
    optimistic_gain = (optimistic_wins * roi_tp) - (optimistic_losses * roi_sl)
    optimistic_usdt = (optimistic_wins * tp_gain_usdt) - (optimistic_losses * sl_loss_usdt)
    
    # Escenario Realista (projected accuracy)
    realistic_wins = int(num_trades_possible * (projected_accuracy / 100))
    realistic_losses = num_trades_possible - realistic_wins
    realistic_gain = (realistic_wins * roi_tp) - (realistic_losses * roi_sl)
    realistic_usdt = (realistic_wins * tp_gain_usdt) - (realistic_losses * sl_loss_usdt)
    
    # Escenario Conservador (50% win rate)
    conservative_wins = int(num_trades_possible * 0.5)
    conservative_losses = num_trades_possible - conservative_wins
    conservative_gain = (conservative_wins * roi_tp) - (conservative_losses * roi_sl)
    conservative_usdt = (conservative_wins * tp_gain_usdt) - (conservative_losses * sl_loss_usdt)
    
    print(f"\n📊 ESCENARIO OPTIMISTA (70% acierto):")
    print(f"   🎯 {optimistic_wins} trades ganados, {optimistic_losses} perdidos")
    print(f"   💚 ROI: +{optimistic_gain:.1f}% sobre margen")
    print(f"   💰 Ganancia: ${optimistic_usdt:+.2f} USDT")
    
    print(f"\n📊 ESCENARIO REALISTA ({projected_accuracy}% acierto):")
    print(f"   🎯 {realistic_wins} trades ganados, {realistic_losses} perdidos")
    print(f"   💚 ROI: {realistic_gain:+.1f}% sobre margen")
    print(f"   💰 Ganancia: ${realistic_usdt:+.2f} USDT")
    
    print(f"\n📊 ESCENARIO CONSERVADOR (50% acierto):")
    print(f"   🎯 {conservative_wins} trades ganados, {conservative_losses} perdidos")
    print(f"   💚 ROI: {conservative_gain:+.1f}% sobre margen")
    print(f"   💰 Ganancia: ${conservative_usdt:+.2f} USDT")
    
    # Recomendaciones
    print(f"\n💡 RECOMENDACIONES PARA HOY:")
    
    if len(excellent_opportunities) >= 2:
        print("   ✅ Día favorable para trading activo")
        print(f"   🎯 Enfocar en: {', '.join(excellent_opportunities)}")
    elif len(high_volatility_pairs) >= 2:
        print("   ⚠️  Volatilidad alta - oportunidades pero mayor riesgo")
        print(f"   🎯 Monitorear: {', '.join(high_volatility_pairs)}")
    else:
        print("   📊 Día tranquilo - trading selectivo recomendado")
        print("   🎯 Esperar señales ML muy fuertes (>0.7)")
    
    if avg_opportunity >= 60:
        print("   🚀 Condiciones favorables para alcanzar ROI >= 13%")
    elif avg_opportunity >= 40:
        print("   📊 Condiciones neutrales - mantener disciplina")
    else:
        print("   ⚠️  Condiciones desafiantes - máxima selectividad")
    
    print(f"\n⏰ Próxima actualización recomendada: {(datetime.now() + timedelta(hours=4)).strftime('%H:%M')}")
    print("=" * 70)
    print("✅ Análisis completado!")

if __name__ == "__main__":
    asyncio.run(market_analysis_today())
