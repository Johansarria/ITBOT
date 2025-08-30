#!/usr/bin/env python3
"""
Script de Descarga de 100,000 Datos Históricos - CORREGIDO
Optimizado para configuración de sistema de trading institucional
"""

import asyncio
import pandas as pd
import os
from binance.exceptions import BinanceAPIException
import logging
from datetime import datetime, timedelta
import time

from utils.binance_client import get_binance_client
from utils.logger_setup import setup_logging
from database.database_manager import add_klines

# Configurar logging
setup_logging()
logger = logging.getLogger(__name__)

class DataDownloader100K:
    def __init__(self):
        self.target_records = 100000
        self.symbol = "BTCUSDT"
        self.interval = "1h"
        self.batch_size = 1000  # Registros por lote
        self.data_dir = "data/100k_historical/"
        self.csv_file = f"{self.data_dir}btcusdt_100k_historical.csv"
        
        # Crear directorio si no existe
        os.makedirs(self.data_dir, exist_ok=True)
    
    def calculate_time_periods(self):
        """Calcular períodos de tiempo para 100K registros de 1h"""
        hours_needed = self.target_records  # 100,000 horas
        days_needed = hours_needed / 24
        years_needed = days_needed / 365.25
        
        # Fecha final: ahora
        end_date = datetime.now()
        # Fecha inicial: restar las horas necesarias
        start_date = end_date - timedelta(hours=hours_needed)
        
        logger.info(f"📊 Calculando períodos para {self.target_records:,} registros:")
        logger.info(f"📊 Período total: {years_needed:.1f} años ({days_needed:.0f} días)")
        logger.info(f"📅 Desde: {start_date.strftime('%Y-%m-%d %H:%M')} hasta: {end_date.strftime('%Y-%m-%d %H:%M')}")
        
        return start_date, end_date
    
    async def download_batch(self, start_time, limit=1000):
        """Descargar un lote de datos"""
        try:
            client = get_binance_client()
            start_ts = int(start_time.timestamp() * 1000)
            
            # Usar asyncio.to_thread para la llamada sincrónica
            klines = await asyncio.to_thread(
                client.get_historical_klines,
                symbol=self.symbol,
                interval=self.interval,
                start_str=start_ts,
                limit=limit
            )
            
            if not klines:
                return pd.DataFrame()
            
            # Convertir a DataFrame
            df = pd.DataFrame(klines, columns=[
                "timestamp", "open", "high", "low", "close", "volume",
                "close_time", "quote_asset_volume", "number_of_trades",
                "taker_buy_base_volume", "taker_buy_quote_volume", "ignore"
            ])
            
            # Procesar datos
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].apply(pd.to_numeric)
            
            return df
            
        except BinanceAPIException as e:
            logger.error(f"Error API Binance: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error en lote: {e}")
            return pd.DataFrame()
    
    async def download_100k_data(self):
        """Descargar 100,000 registros históricos"""
        logger.info("🚀 INICIANDO DESCARGA DE 100,000 DATOS HISTÓRICOS")
        logger.info(f"📊 Símbolo: {self.symbol}")
        logger.info(f"📊 Intervalo: {self.interval}")
        logger.info(f"📊 Registros objetivo: {self.target_records:,}")
        
        start_date, end_date = self.calculate_time_periods()
        
        # Calcular número de lotes
        total_batches = (self.target_records + self.batch_size - 1) // self.batch_size
        logger.info(f"📥 Descargando en {total_batches} lotes de {self.batch_size} registros")
        
        all_data = []
        current_time = start_date
        records_downloaded = 0
        
        start_download = time.time()
        
        for batch_num in range(1, total_batches + 1):
            batch_start = time.time()
            
            # Calcular final del lote
            next_time = current_time + timedelta(hours=self.batch_size)
            
            logger.info(f"Lote {batch_num}/{total_batches} - {current_time.strftime('%Y-%m-%d %H:%M')} a {next_time.strftime('%Y-%m-%d %H:%M')}")
            
            # Descargar lote
            batch_df = await self.download_batch(current_time, self.batch_size)
            
            if not batch_df.empty:
                all_data.append(batch_df)
                records_downloaded += len(batch_df)
                
                batch_time = time.time() - batch_start
                logger.info(f"✅ Lote {batch_num} completado: {len(batch_df)} registros en {batch_time:.2f}s")
                
                # Actualizar tiempo para siguiente lote
                if not batch_df.empty:
                    current_time = batch_df.index[-1] + timedelta(hours=1)
                else:
                    current_time = next_time
            else:
                logger.warning(f"⚠️ Lote {batch_num} vacío")
                current_time = next_time
            
            # Pausa entre lotes para no sobrecargar la API
            await asyncio.sleep(0.1)
            
            # Verificar si hemos alcanzado el objetivo
            if records_downloaded >= self.target_records:
                logger.info(f"🎯 Objetivo alcanzado: {records_downloaded:,} registros")
                break
        
        if not all_data:
            logger.error("❌ No se pudieron descargar datos")
            return False
        
        # Combinar todos los datos
        logger.info("🔄 Consolidando datos...")
        final_df = pd.concat(all_data, axis=0)
        final_df = final_df.drop_duplicates()
        final_df.sort_index(inplace=True)
        
        # Limitar a exactamente 100K registros si tenemos más
        if len(final_df) > self.target_records:
            final_df = final_df.tail(self.target_records)
            logger.info(f"✂️ Datos limitados a {self.target_records:,} registros más recientes")
        
        # Guardar en CSV
        logger.info(f"💾 Guardando en {self.csv_file}")
        final_df.to_csv(self.csv_file)
        
        # Guardar en base de datos
        try:
            logger.info("💾 Guardando en base de datos...")
            df_to_db = final_df.copy()
            df_to_db["timestamp"] = df_to_db.index.astype(int) // 10**6
            df_to_db["close_time"] = df_to_db["close_time"].astype(int)
            add_klines(df_to_db, self.symbol, self.interval)
            logger.info("✅ Datos guardados en base de datos")
        except Exception as e:
            logger.warning(f"⚠️ Error guardando en BD: {e}")
        
        # Estadísticas finales
        total_time = time.time() - start_download
        
        logger.info("="*60)
        logger.info("🎉 DESCARGA COMPLETADA")
        logger.info(f"📊 Registros totales: {len(final_df):,}")
        logger.info(f"📅 Período: {final_df.index[0]} a {final_df.index[-1]}")
        logger.info(f"⏱️ Tiempo total: {total_time:.2f} segundos")
        logger.info(f"📈 Velocidad: {len(final_df)/total_time:.0f} registros/segundo")
        logger.info(f"💾 Archivo: {self.csv_file}")
        logger.info("="*60)
        
        return True

async def main():
    """Función principal"""
    downloader = DataDownloader100K()
    success = await downloader.download_100k_data()
    
    if success:
        logger.info("🚀 Sistema listo para operar con 100K datos históricos")
    else:
        logger.error("❌ Error en la descarga de 100K datos")

if __name__ == "__main__":
    asyncio.run(main())
