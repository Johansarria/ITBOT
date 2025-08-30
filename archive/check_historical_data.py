#!/usr/bin/env python3
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

def analyze_historical_data():
    """Analiza la cantidad y calidad de datos históricos disponibles"""
    
    try:
        conn = sqlite3.connect('storage/itbot.db')
        
        # 1. Datos básicos BTCUSDT 1h
        query = """
        SELECT COUNT(*) as total_klines, 
               MIN(open_time) as oldest, 
               MAX(open_time) as newest,
               MIN(close) as min_price,
               MAX(close) as max_price
        FROM klines 
        WHERE symbol='BTCUSDT' AND interval='1h'
        """
        
        df_basic = pd.read_sql_query(query, conn)
        
        if df_basic.iloc[0]['total_klines'] > 0:
            print('📊 DATOS HISTÓRICOS BTCUSDT (1h):')
            print(f'Total registros: {df_basic.iloc[0]["total_klines"]:,}')
            print(f'Período: {df_basic.iloc[0]["oldest"]} → {df_basic.iloc[0]["newest"]}')
            print(f'Rango precios: ${df_basic.iloc[0]["min_price"]:,.2f} - ${df_basic.iloc[0]["max_price"]:,.2f}')
            
            # Calcular días de datos
            oldest = pd.to_datetime(df_basic.iloc[0]["oldest"])
            newest = pd.to_datetime(df_basic.iloc[0]["newest"])
            days_span = (newest - oldest).days
            print(f'Duración: {days_span} días ({days_span/30:.1f} meses)')
            
        else:
            print('❌ NO HAY DATOS BTCUSDT EN LA BASE DE DATOS')
            conn.close()
            return
            
        # 2. Distribución temporal reciente
        query2 = """
        SELECT DATE(open_time) as date, COUNT(*) as daily_count
        FROM klines 
        WHERE symbol='BTCUSDT' AND interval='1h'
        GROUP BY DATE(open_time)
        ORDER BY date DESC
        LIMIT 15
        """
        
        df_daily = pd.read_sql_query(query2, conn)
        print(f'\n📅 ÚLTIMOS 15 DÍAS CON DATOS:')
        for _, row in df_daily.iterrows():
            status = "✅" if row["daily_count"] >= 20 else "⚠️" if row["daily_count"] >= 10 else "❌"
            print(f'{row["date"]}: {row["daily_count"]:2d} registros {status}')
        
        # 3. Análisis de gaps y continuidad
        query3 = """
        SELECT open_time, 
               LAG(open_time) OVER (ORDER BY open_time) as prev_time,
               close, volume
        FROM klines 
        WHERE symbol='BTCUSDT' AND interval='1h'
        ORDER BY open_time DESC
        LIMIT 1000
        """
        
        df_gaps = pd.read_sql_query(query3, conn)
        df_gaps['open_time'] = pd.to_datetime(df_gaps['open_time'])
        df_gaps['prev_time'] = pd.to_datetime(df_gaps['prev_time'])
        df_gaps['gap_hours'] = (df_gaps['open_time'] - df_gaps['prev_time']).dt.total_seconds() / 3600
        
        gaps = df_gaps[df_gaps['gap_hours'] > 1.5]  # Gaps > 1.5 horas
        print(f'\n🕳️ ANÁLISIS DE CONTINUIDAD (últimas 1000 velas):')
        print(f'Gaps encontrados: {len(gaps)}')
        if len(gaps) > 0:
            print('Gaps principales:')
            for _, gap in gaps.head(5).iterrows():
                print(f'  {gap["prev_time"]} → {gap["open_time"]} ({gap["gap_hours"]:.1f}h)')
        
        # 4. Análisis estadístico de precios
        df_prices = pd.read_sql_query("""
            SELECT close, volume, open_time
            FROM klines 
            WHERE symbol='BTCUSDT' AND interval='1h'
            ORDER BY open_time DESC
            LIMIT 2000
        """, conn)
        
        if len(df_prices) > 0:
            returns = df_prices['close'].pct_change().dropna()
            print(f'\n📈 ESTADÍSTICAS DE PRECIOS (últimas 2000 velas):')
            print(f'Precio promedio: ${df_prices["close"].mean():,.2f}')
            print(f'Volatilidad diaria: {returns.std() * np.sqrt(24) * 100:.2f}%')
            print(f'Retorno máximo: {returns.max() * 100:.2f}%')
            print(f'Retorno mínimo: {returns.min() * 100:.2f}%')
            print(f'Volumen promedio: {df_prices["volume"].mean():,.0f}')
        
        # 5. Evaluación de suficiencia para ML
        total_records = df_basic.iloc[0]['total_klines']
        print(f'\n🤖 EVALUACIÓN PARA ML:')
        
        # Criterios para ML efectivo
        min_for_basic_ml = 1000      # Mínimo básico
        min_for_good_ml = 5000       # Buena cantidad
        min_for_excellent_ml = 20000 # Excelente cantidad
        
        if total_records < min_for_basic_ml:
            ml_rating = "❌ INSUFICIENTE"
            ml_comment = f"Se necesitan al menos {min_for_basic_ml:,} registros para ML básico"
        elif total_records < min_for_good_ml:
            ml_rating = "⚠️ BÁSICO"
            ml_comment = f"Suficiente para ML básico, ideal serían {min_for_good_ml:,}+ registros"
        elif total_records < min_for_excellent_ml:
            ml_rating = "✅ BUENO"
            ml_comment = f"Buena cantidad para ML, excelente serían {min_for_excellent_ml:,}+ registros"
        else:
            ml_rating = "🎯 EXCELENTE"
            ml_comment = "Cantidad excelente para ML avanzado"
            
        print(f'Cantidad de datos: {ml_rating}')
        print(f'Comentario: {ml_comment}')
        
        # Análisis de períodos de mercado
        if len(df_prices) >= 1000:
            recent_prices = df_prices.head(168)['close']  # Última semana
            older_prices = df_prices.tail(168)['close']   # Hace tiempo
            
            recent_volatility = recent_prices.pct_change().std() * np.sqrt(24) * 100
            older_volatility = older_prices.pct_change().std() * np.sqrt(24) * 100
            
            print(f'\n📊 DIVERSIDAD DE CONDICIONES DE MERCADO:')
            print(f'Volatilidad reciente: {recent_volatility:.2f}%')
            print(f'Volatilidad histórica: {older_volatility:.2f}%')
            
            volatility_ratio = recent_volatility / older_volatility if older_volatility > 0 else 1
            if 0.7 <= volatility_ratio <= 1.3:
                market_diversity = "✅ EQUILIBRADA"
            elif volatility_ratio > 2 or volatility_ratio < 0.5:
                market_diversity = "⚠️ EXTREMA"
            else:
                market_diversity = "📊 MODERADA"
            
            print(f'Diversidad de mercado: {market_diversity}')
            
        conn.close()
        
    except Exception as e:
        print(f'❌ Error analizando datos: {e}')

if __name__ == "__main__":
    analyze_historical_data()
