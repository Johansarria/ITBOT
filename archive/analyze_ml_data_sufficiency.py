#!/usr/bin/env python3
"""
Análisis completo de suficiencia de datos para ML en trading
Evalúa cantidad, calidad y diversidad de datos históricos necesarios
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import os
from binance.exceptions import BinanceAPIException

# Setup básico de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def analyze_data_sufficiency():
    """
    Analiza si tenemos suficientes datos históricos para ML confiable
    """
    print("🔍 ANÁLISIS DE SUFICIENCIA DE DATOS PARA ML TRADING")
    print("=" * 60)
    
    # Importar después de setup de logging
    from utils.binance_client import get_binance_client
    
    try:
        client = get_binance_client()
        
        # 1. OBTENER DATOS HISTÓRICOS DE PRUEBA
        print("\n📊 1. DESCARGANDO DATOS HISTÓRICOS DE PRUEBA...")
        
        # Descargar 6 meses de datos (aprox. 4,320 horas)
        klines = await client.get_historical_klines(
            "BTCUSDT", 
            "1h", 
            "6 months ago UTC"
        )
        
        await client.close_connection()
        
        # Convertir a DataFrame
        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Convertir tipos
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        
        print(f"✅ Datos descargados: {len(df):,} registros")
        print(f"📅 Período: {df['open_time'].min()} → {df['open_time'].max()}")
        print(f"💰 Rango precios: ${df['close'].min():,.2f} - ${df['close'].max():,.2f}")
        
        # 2. ANÁLISIS DE CANTIDAD
        print(f"\n📈 2. ANÁLISIS DE CANTIDAD DE DATOS")
        
        total_hours = len(df)
        days = total_hours / 24
        weeks = days / 7
        months = days / 30
        
        print(f"Total horas: {total_hours:,}")
        print(f"Días equivalentes: {days:.1f}")
        print(f"Semanas equivalentes: {weeks:.1f}")
        print(f"Meses equivalentes: {months:.1f}")
        
        # Criterios de suficiencia
        print(f"\n🎯 CRITERIOS DE SUFICIENCIA PARA ML:")
        
        criteria = [
            ("Mínimo básico", 1000, "⚠️ Riesgo alto"),
            ("Recomendado", 5000, "✅ Aceptable"),  
            ("Óptimo", 15000, "🎯 Bueno"),
            ("Excelente", 30000, "🚀 Excelente"),
            ("Enterprise", 50000, "💎 Enterprise")
        ]
        
        for name, threshold, status in criteria:
            if total_hours >= threshold:
                print(f"{status} {name}: {threshold:,}+ horas ✅")
            else:
                print(f"⏳ {name}: {threshold:,}+ horas (faltan {threshold - total_hours:,})")
        
        # 3. ANÁLISIS DE CALIDAD Y DIVERSIDAD
        print(f"\n📊 3. ANÁLISIS DE CALIDAD DE DATOS")
        
        # Volatilidad
        returns = df['close'].pct_change().dropna()
        daily_vol = returns.std() * np.sqrt(24) * 100
        print(f"Volatilidad diaria promedio: {daily_vol:.2f}%")
        
        # Distribución de retornos
        extreme_moves = returns[(returns.abs() > returns.std() * 2)]
        print(f"Movimientos extremos (>2σ): {len(extreme_moves)} ({len(extreme_moves)/len(returns)*100:.2f}%)")
        
        # Análisis de rangos de precios
        price_ranges = []
        window = 168  # 1 semana
        for i in range(0, len(df) - window, window):
            week_data = df.iloc[i:i+window]
            price_range = (week_data['high'].max() - week_data['low'].min()) / week_data['close'].mean()
            price_ranges.append(price_range)
        
        avg_weekly_range = np.mean(price_ranges)
        print(f"Rango semanal promedio: {avg_weekly_range*100:.2f}%")
        
        # 4. DIVERSIDAD DE CONDICIONES DE MERCADO
        print(f"\n🌊 4. DIVERSIDAD DE CONDICIONES DE MERCADO")
        
        # Calcular períodos alcistas/bajistas
        ma_20 = df['close'].rolling(20).mean()
        ma_50 = df['close'].rolling(50).mean()
        
        bullish_periods = (ma_20 > ma_50).sum()
        bearish_periods = (ma_20 <= ma_50).sum()
        
        print(f"Períodos alcistas: {bullish_periods:,} ({bullish_periods/len(df)*100:.1f}%)")
        print(f"Períodos bajistas: {bearish_periods:,} ({bearish_periods/len(df)*100:.1f}%)")
        
        # Balance
        balance = min(bullish_periods, bearish_periods) / max(bullish_periods, bearish_periods)
        if balance > 0.7:
            market_balance = "🎯 MUY EQUILIBRADO"
        elif balance > 0.5:
            market_balance = "✅ EQUILIBRADO"
        elif balance > 0.3:
            market_balance = "⚠️ DESBALANCEADO"
        else:
            market_balance = "❌ MUY DESBALANCEADO"
        
        print(f"Balance de mercado: {market_balance} (ratio: {balance:.2f})")
        
        # 5. ANÁLISIS DE PERIODICIDAD Y ESTACIONALIDAD
        print(f"\n📅 5. ANÁLISIS TEMPORAL")
        
        df['hour'] = df['open_time'].dt.hour
        df['day_of_week'] = df['open_time'].dt.dayofweek
        df['day_of_month'] = df['open_time'].dt.day
        
        # Volatilidad por hora del día
        hourly_vol = df.groupby('hour')['close'].pct_change().std() * 100
        print(f"Hora más volátil: {hourly_vol.idxmax()}:00 ({hourly_vol.max():.3f}%)")
        print(f"Hora menos volátil: {hourly_vol.idxmin()}:00 ({hourly_vol.min():.3f}%)")
        
        # 6. EVALUACIÓN FINAL
        print(f"\n🎯 6. EVALUACIÓN FINAL PARA ACERTIVIDAD ML")
        
        score = 0
        factors = []
        
        # Factor cantidad (40% del score)
        if total_hours >= 30000:
            quantity_score = 40
            factors.append("✅ Cantidad excelente (40/40)")
        elif total_hours >= 15000:
            quantity_score = 32
            factors.append("🎯 Cantidad buena (32/40)")
        elif total_hours >= 5000:
            quantity_score = 24
            factors.append("⚠️ Cantidad aceptable (24/40)")
        else:
            quantity_score = 12
            factors.append("❌ Cantidad insuficiente (12/40)")
        score += quantity_score
        
        # Factor diversidad (25% del score)
        if balance > 0.7:
            diversity_score = 25
            factors.append("✅ Diversidad excelente (25/25)")
        elif balance > 0.5:
            diversity_score = 20
            factors.append("🎯 Diversidad buena (20/25)")
        elif balance > 0.3:
            diversity_score = 15
            factors.append("⚠️ Diversidad regular (15/25)")
        else:
            diversity_score = 5
            factors.append("❌ Diversidad pobre (5/25)")
        score += diversity_score
        
        # Factor volatilidad (20% del score)
        if 1.5 <= daily_vol <= 4.0:  # Rango ideal para trading
            volatility_score = 20
            factors.append("✅ Volatilidad óptima (20/20)")
        elif 1.0 <= daily_vol <= 6.0:  # Aceptable
            volatility_score = 15
            factors.append("🎯 Volatilidad aceptable (15/20)")
        else:
            volatility_score = 10
            factors.append("⚠️ Volatilidad subóptima (10/20)")
        score += volatility_score
        
        # Factor calidad (15% del score)
        missing_data = df.isnull().sum().sum()
        if missing_data == 0:
            quality_score = 15
            factors.append("✅ Calidad perfecta (15/15)")
        else:
            quality_score = 10
            factors.append(f"⚠️ Algunos datos faltantes (10/15)")
        score += quality_score
        
        print(f"\n📊 PUNTUACIÓN FINAL: {score}/100")
        for factor in factors:
            print(f"  {factor}")
        
        # Recomendación final
        if score >= 90:
            recommendation = "🚀 EXCELENTE - Alta confianza en acertividad ML"
        elif score >= 75:
            recommendation = "✅ BUENO - Confianza sólida en acertividad ML"
        elif score >= 60:
            recommendation = "⚠️ ACEPTABLE - Cuidado con overfitting, validación cruzada crítica"
        elif score >= 45:
            recommendation = "🔴 RIESGOSO - Acertividad ML cuestionable, más datos recomendados"
        else:
            recommendation = "❌ INSUFICIENTE - No recomendado para trading real"
            
        print(f"\n🎯 RECOMENDACIÓN: {recommendation}")
        
        # Sugerencias específicas
        print(f"\n💡 SUGERENCIAS PARA MEJORAR ACERTIVIDAD:")
        
        if total_hours < 15000:
            months_needed = (15000 - total_hours) / (24 * 30)
            print(f"  📈 Aumentar datos históricos: faltan ~{months_needed:.1f} meses")
        
        if balance < 0.5:
            print(f"  🌊 Incluir más datos de diferentes condiciones de mercado")
        
        if daily_vol < 1.5 or daily_vol > 4.0:
            print(f"  📊 Buscar períodos con volatilidad 1.5-4.0% (actual: {daily_vol:.2f}%)")
        
        print(f"  🔄 Implementar validación cruzada temporal robusta")
        print(f"  📊 Usar walk-forward analysis para backtesting")
        print(f"  ⚡ Reentrenar modelo cada 1-2 semanas con datos frescos")
        
        # Guardar resumen
        summary = {
            'total_records': int(total_hours),
            'period_days': float(days),
            'score': int(score),
            'recommendation': recommendation,
            'daily_volatility': float(daily_vol),
            'market_balance': float(balance),
            'analysis_date': datetime.now().isoformat()
        }
        
        import json
        with open('data/ml_data_sufficiency_analysis.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n💾 Análisis guardado en: data/ml_data_sufficiency_analysis.json")
        
    except Exception as e:
        logger.error(f"Error en análisis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(analyze_data_sufficiency())
