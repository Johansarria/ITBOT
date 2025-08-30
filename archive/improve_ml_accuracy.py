#!/usr/bin/env python3
"""
Script para descargar datos históricos completos y mejorar la acertividad ML
Implementa las recomendaciones del análisis de suficiencia de datos
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import os
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def download_comprehensive_historical_data():
    """
    Descarga datos históricos completos para ML confiable
    """
    print("📥 DESCARGA DE DATOS HISTÓRICOS PARA ML CONFIABLE")
    print("=" * 60)
    
    try:
        # Importar solo lo necesario
        import sys
        sys.path.append('/home/johan/itbot_linux/.venv/lib/python3.12/site-packages')
        
        from binance import AsyncClient
        from database.database_manager import add_klines
        
        print("\n🔗 Conectando a Binance API...")
        
        # Obtener credenciales del ambiente (sin usar config que da error)
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_SECRET_KEY')
        
        if not api_key or not api_secret:
            print("⚠️ Credenciales Binance no encontradas, usando modo público")
            client = AsyncClient()
        else:
            client = AsyncClient(api_key, api_secret)
        
        # Configuración de descarga
        symbol = "BTCUSDT" 
        interval = "1h"
        
        # Descargar 6 meses de datos (recomendación mínima)
        periods = [
            ("6 months ago", "4 months ago", "Período 1: 6-4 meses atrás"),
            ("4 months ago", "2 months ago", "Período 2: 4-2 meses atrás"), 
            ("2 months ago", "now", "Período 3: 2 meses atrás - presente")
        ]
        
        all_klines = []
        total_downloaded = 0
        
        for start_time, end_time, description in periods:
            print(f"\n📊 {description}")
            
            try:
                klines = await client.get_historical_klines(
                    symbol=symbol,
                    interval=interval,
                    start_str=start_time,
                    end_str=end_time
                )
                
                if klines:
                    all_klines.extend(klines)
                    total_downloaded += len(klines)
                    print(f"✅ Descargado: {len(klines):,} registros")
                else:
                    print("⚠️ Sin datos para este período")
                    
            except Exception as e:
                print(f"❌ Error descargando {description}: {e}")
                continue
        
        await client.close_connection()
        
        if not all_klines:
            print("❌ No se pudieron descargar datos históricos")
            return False
        
        print(f"\n📈 TOTAL DESCARGADO: {total_downloaded:,} registros")
        
        # Convertir a DataFrame
        df = pd.DataFrame(all_klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Limpiar y convertir tipos
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        df = df.drop_duplicates(subset=['open_time']).sort_values('open_time')
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Análisis de calidad
        print(f"\n🔍 ANÁLISIS DE CALIDAD:")
        print(f"Registros únicos: {len(df):,}")
        print(f"Período: {df['open_time'].min()} → {df['open_time'].max()}")
        print(f"Rango precios: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
        
        # Detectar gaps
        df['time_diff'] = df['open_time'].diff()
        gaps = df[df['time_diff'] > pd.Timedelta(hours=2)]
        print(f"Gaps detectados: {len(gaps)}")
        
        if len(gaps) > 0:
            print("⚠️ Gaps principales:")
            for _, gap in gaps.head(3).iterrows():
                print(f"   {gap['open_time']}: gap de {gap['time_diff']}")
        
        # Análisis estadístico
        returns = df['close'].pct_change().dropna()
        daily_vol = returns.std() * np.sqrt(24) * 100
        
        print(f"\n📊 ESTADÍSTICAS:")
        print(f"Volatilidad diaria promedio: {daily_vol:.2f}%")
        print(f"Retorno máximo: {returns.max() * 100:.2f}%")
        print(f"Retorno mínimo: {returns.min() * 100:.2f}%")
        
        # Guardar en base de datos
        print(f"\n💾 Guardando en base de datos...")
        
        success_count = 0
        error_count = 0
        
        for _, row in df.iterrows():
            try:
                kline_data = {
                    'symbol': symbol,
                    'interval': interval,
                    'open_time': row['open_time'].isoformat(),
                    'close_time': pd.to_datetime(row['close_time'], unit='ms').isoformat(),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': float(row['volume']),
                    'quote_asset_volume': float(row['quote_asset_volume']),
                    'number_of_trades': int(row['number_of_trades']),
                    'taker_buy_base_asset_volume': float(row['taker_buy_base_asset_volume']),
                    'taker_buy_quote_asset_volume': float(row['taker_buy_quote_asset_volume'])
                }
                
                add_klines([kline_data])
                success_count += 1
                
                if success_count % 1000 == 0:
                    print(f"   Guardados: {success_count:,}")
                    
            except Exception as e:
                error_count += 1
                if error_count < 5:  # Solo mostrar primeros errores
                    logger.warning(f"Error guardando registro: {e}")
        
        print(f"✅ Guardado completo: {success_count:,} registros exitosos, {error_count} errores")
        
        # Guardar también como CSV backup
        csv_path = f"data/historical_complete_{symbol}_{interval}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(csv_path, index=False)
        print(f"💾 Backup CSV guardado: {csv_path}")
        
        # Crear reporte final
        report = {
            "download_date": datetime.now().isoformat(),
            "symbol": symbol,
            "interval": interval,
            "total_records": len(df),
            "period_start": df['open_time'].min().isoformat(),
            "period_end": df['open_time'].max().isoformat(),
            "daily_volatility": float(daily_vol),
            "gaps_detected": len(gaps),
            "data_quality_score": max(0, 100 - (len(gaps) * 5) - (error_count / len(df) * 100)),
            "ml_readiness": "READY" if len(df) >= 2000 else "INSUFFICIENT",
            "recommendation": "Datos suficientes para ML confiable" if len(df) >= 2000 else "Necesita más datos históricos"
        }
        
        with open('data/historical_download_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n🎯 EVALUACIÓN FINAL:")
        print(f"Registros descargados: {len(df):,}")
        print(f"Calidad de datos: {report['data_quality_score']:.1f}/100")
        print(f"Estado ML: {report['ml_readiness']}")
        print(f"💡 {report['recommendation']}")
        
        if len(df) >= 2000:
            print(f"\n✅ SISTEMA LISTO PARA ML CONFIABLE")
            print(f"   Puedes proceder con entrenamientos y trading automático")
        else:
            print(f"\n⚠️ NECESITAS MÁS DATOS HISTÓRICOS")
            print(f"   Actual: {len(df):,}, Recomendado: 2,000+")
        
        return True
        
    except Exception as e:
        logger.error(f"Error en descarga: {e}")
        import traceback
        traceback.print_exc()
        return False

async def verify_data_sufficiency():
    """
    Verifica si los datos actuales son suficientes para ML confiable
    """
    try:
        from database.database_manager import get_klines
        
        df = get_klines("BTCUSDT", "1h")
        
        if df.empty:
            print("❌ NO HAY DATOS EN LA BASE DE DATOS")
            return False
        
        print(f"\n📊 DATOS ACTUALES EN BD:")
        print(f"Total registros: {len(df):,}")
        print(f"Período: {df.index.min()} → {df.index.max()}")
        
        # Evaluar suficiencia según nuevos estándares
        if len(df) >= 8760:  # 1 año
            print("🚀 EXCELENTE: Datos suficientes para ML de alta confianza")
            return True
        elif len(df) >= 2000:  # 3 meses aprox
            print("✅ BUENO: Datos suficientes para ML confiable")
            return True
        elif len(df) >= 500:   # 3 semanas aprox
            print("⚠️ BÁSICO: Datos mínimos para ML con supervisión")
            return False
        else:
            print("❌ INSUFICIENTE: Necesitas descargar más datos históricos")
            return False
            
    except Exception as e:
        logger.error(f"Error verificando datos: {e}")
        return False

if __name__ == "__main__":
    print("🎯 MEJORA DE ACERTIVIDAD ML - DESCARGA DE DATOS HISTÓRICOS")
    print("=" * 70)
    
    # Verificar estado actual
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    print("1️⃣ Verificando datos actuales...")
    current_sufficient = loop.run_until_complete(verify_data_sufficiency())
    
    if not current_sufficient:
        print("\n2️⃣ Descargando datos históricos completos...")
        success = loop.run_until_complete(download_comprehensive_historical_data())
        
        if success:
            print("\n3️⃣ Re-verificando tras descarga...")
            loop.run_until_complete(verify_data_sufficiency())
    else:
        print("\n✅ Datos actuales son suficientes para ML confiable")
    
    loop.close()
    print("\n🏁 Proceso completado")
