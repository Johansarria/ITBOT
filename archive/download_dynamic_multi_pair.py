#!/usr/bin/env python3
"""
SISTEMA MULTI-PAR DINÁMICO MEJORADO
Usa automáticamente los mejores pares seleccionados por el análisis dinámico
"""

import asyncio
import pandas as pd
import os
import json
import logging
from datetime import datetime
import time
from typing import Dict, List, Optional

from utils.binance_client import get_binance_client
from utils.logger_setup import setup_logging
from database.database_manager import add_klines

setup_logging()
logger = logging.getLogger(__name__)

class DynamicMultiPairDownloader:
    def __init__(self):
        # Cargar pares seleccionados dinámicamente
        self.load_dynamic_selection()
        
        self.interval = "1h"
        self.start_str = "1 Jan, 2017"
        self.output_path = "data/dynamic_multi_pair/"
        
        # Crear directorio
        os.makedirs(self.output_path, exist_ok=True)
        
        # Estadísticas
        self.download_stats = {}
        
    def load_dynamic_selection(self):
        """Cargar pares seleccionados dinámicamente"""
        selection_file = "data/dynamic_pair_analysis/dynamic_pair_selection.json"
        
        try:
            with open(selection_file, 'r') as f:
                selection_data = json.load(f)
                self.trading_pairs = selection_data['selected_pairs']
                self.pair_metrics = selection_data['pair_metrics']
                self.selection_timestamp = selection_data['selection_timestamp']
            
            logger.info(f"✅ Pares dinámicos cargados: {len(self.trading_pairs)}")
            logger.info(f"   Selección del: {self.selection_timestamp}")
            
        except Exception as e:
            logger.warning(f"⚠️ No se pudo cargar selección dinámica: {e}")
            # Fallback a pares por defecto
            self.trading_pairs = [
                "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", 
                "SOLUSDT", "TRXUSDT", "XRPUSDT", "LINKUSDT"
            ]
            self.pair_metrics = {}
            logger.info("🔄 Usando pares por defecto")
    
    def filter_crypto_pairs(self):
        """Filtrar solo pares de criptomonedas (excluir stablecoins)"""
        # Lista de stablecoins conocidas
        stablecoins = ["USDC", "FDUSD", "TUSD", "BUSD", "DAI", "USDT"]
        
        # Filtrar pares que no sean stablecoin-to-stablecoin
        crypto_pairs = []
        for pair in self.trading_pairs:
            base_asset = pair.replace("USDT", "")
            if base_asset not in stablecoins:
                crypto_pairs.append(pair)
            else:
                logger.info(f"⚠️ Excluyendo stablecoin: {pair}")
        
        self.trading_pairs = crypto_pairs
        logger.info(f"📊 Pares de criptomonedas finales: {len(self.trading_pairs)}")
    
    async def download_all_pairs(self):
        """Descargar datos históricos para todos los pares seleccionados"""
        logger.info("🚀 DESCARGA MULTI-PAR DINÁMICO")
        logger.info("🎯 Usando selección automática de mejores pares")
        logger.info("="*70)
        
        # Filtrar solo criptomonedas
        self.filter_crypto_pairs()
        
        if not self.trading_pairs:
            logger.error("❌ No hay pares de criptomonedas para descargar")
            return False
        
        logger.info(f"💰 Pares seleccionados dinámicamente:")
        for i, pair in enumerate(self.trading_pairs, 1):
            score = "N/A"
            volume = "N/A"
            if pair in self.pair_metrics:
                score = f"{self.pair_metrics[pair]['composite_score']:.1f}"
                volume = f"${self.pair_metrics[pair]['volume_24h_usdt']:,.0f}"
            
            logger.info(f"   {i}. {pair} (Score: {score}, Vol 24h: {volume})")
        logger.info("")
        
        start_time = time.time()
        successful_downloads = 0
        total_records = 0
        
        # Descargar cada par
        for pair in self.trading_pairs:
            logger.info(f"📥 Descargando {pair}...")
            success, records = await self.download_pair_data(pair)
            
            if success:
                successful_downloads += 1
                total_records += records
                logger.info(f"✅ {pair}: {records:,} registros descargados")
            else:
                logger.error(f"❌ {pair}: Error en descarga")
            
            # Pausa entre descargas
            await asyncio.sleep(1)
        
        total_time = time.time() - start_time
        
        # Generar reporte
        await self.generate_dynamic_report(successful_downloads, total_records, total_time)
        
        return successful_downloads > 0
    
    async def download_pair_data(self, symbol: str) -> tuple[bool, int]:
        """Descargar datos para un par específico"""
        try:
            client = await get_binance_client()
            
            # Descargar datos históricos
            klines = await client.get_historical_klines(
                symbol=symbol,
                interval=self.interval,
                start_str=self.start_str,
                end_str=None
            )
            
            if not klines:
                return False, 0
            
            # Procesar datos
            df = pd.DataFrame(klines, columns=[
                "timestamp", "open", "high", "low", "close", "volume",
                "close_time", "quote_asset_volume", "number_of_trades",
                "taker_buy_base_volume", "taker_buy_quote_volume", "ignore"
            ])
            
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].apply(pd.to_numeric)
            
            if df.empty:
                return False, 0
            
            # Calcular estadísticas
            records_count = len(df)
            date_range = (df.index[-1] - df.index[0]).days
            years_covered = date_range / 365.25
            
            # Guardar estadísticas
            self.download_stats[symbol] = {
                "records": records_count,
                "start_date": df.index[0].strftime("%Y-%m-%d"),
                "end_date": df.index[-1].strftime("%Y-%m-%d"),
                "years_covered": round(years_covered, 1),
                "avg_volume": round(df['volume'].mean(), 2),
                "dynamic_score": self.pair_metrics.get(symbol, {}).get('composite_score', 0),
                "selection_rank": self.trading_pairs.index(symbol) + 1
            }
            
            # Guardar CSV
            csv_file = f"{self.output_path}{symbol.lower()}_1h_dynamic.csv"
            df.to_csv(csv_file)
            
            # Guardar en BD
            try:
                df_to_db = df.copy()
                df_to_db["timestamp"] = df_to_db.index.astype(int) // 10**6
                df_to_db["close_time"] = df_to_db["close_time"].astype(int)
                add_klines(df_to_db, symbol, self.interval)
            except Exception as e:
                logger.debug(f"⚠️ Error BD para {symbol}: {e}")
            
            return True, records_count
            
        except Exception as e:
            logger.error(f"❌ Error descargando {symbol}: {e}")
            return False, 0
    
    async def generate_dynamic_report(self, successful_downloads: int, total_records: int, total_time: float):
        """Generar reporte de la descarga dinámica"""
        logger.info("="*80)
        logger.info("🎉 DESCARGA MULTI-PAR DINÁMICO COMPLETADA")
        logger.info("="*80)
        
        logger.info(f"📊 Resumen:")
        logger.info(f"   • Pares descargados: {successful_downloads}/{len(self.trading_pairs)}")
        logger.info(f"   • Total registros: {total_records:,}")
        logger.info(f"   • Tiempo total: {total_time/60:.1f} minutos")
        logger.info("")
        
        if not self.download_stats:
            logger.warning("⚠️ No hay estadísticas para mostrar")
            return
        
        # Ordenar por ranking de selección dinámica
        sorted_pairs = sorted(self.download_stats.items(), 
                            key=lambda x: x[1]['selection_rank'])
        
        logger.info("📈 DETALLES POR PAR (Ordenado por score dinámico):")
        logger.info("─" * 80)
        
        for symbol, stats in sorted_pairs:
            logger.info(f"#{stats['selection_rank']} {symbol}:")
            logger.info(f"   📊 Registros: {stats['records']:,}")
            logger.info(f"   📅 Período: {stats['start_date']} a {stats['end_date']}")
            logger.info(f"   ⏰ Años: {stats['years_covered']}")
            logger.info(f"   🎯 Score dinámico: {stats['dynamic_score']:.1f}/100")
            logger.info(f"   📊 Vol. promedio: {stats['avg_volume']:,.0f}")
            logger.info("")
        
        # Análisis comparativo
        self.analyze_dynamic_performance()
        
        # Guardar configuración dinámica
        self.save_dynamic_config()
        
        logger.info("🚀 SISTEMA DINÁMICO MULTI-PAR LISTO")
        logger.info("💡 Próximo paso: Entrenar modelos con selección dinámica")
        logger.info("="*80)
    
    def analyze_dynamic_performance(self):
        """Analizar performance de la selección dinámica"""
        logger.info("🔍 ANÁLISIS DE PERFORMANCE DINÁMICA:")
        logger.info("─" * 50)
        
        if not self.download_stats:
            return
        
        total_records = sum(stats['records'] for stats in self.download_stats.values())
        avg_score = sum(stats['dynamic_score'] for stats in self.download_stats.values()) / len(self.download_stats)
        
        # Top 3 por score
        top_by_score = sorted(self.download_stats.items(), 
                            key=lambda x: x[1]['dynamic_score'], reverse=True)[:3]
        
        logger.info(f"📊 Métricas generales:")
        logger.info(f"   • Score promedio: {avg_score:.1f}/100")
        logger.info(f"   • Total registros: {total_records:,}")
        logger.info("")
        
        logger.info(f"🏆 TOP 3 por score dinámico:")
        for i, (symbol, stats) in enumerate(top_by_score, 1):
            logger.info(f"   {i}. {symbol}: {stats['dynamic_score']:.1f} "
                       f"({stats['records']:,} registros)")
        
        logger.info("")
        
        # Distribución de años de historia
        year_distribution = {}
        for stats in self.download_stats.values():
            years = int(stats['years_covered'])
            year_distribution[years] = year_distribution.get(years, 0) + 1
        
        logger.info(f"📅 Distribución de historial:")
        for years in sorted(year_distribution.keys(), reverse=True):
            count = year_distribution[years]
            logger.info(f"   • {years} años: {count} pares")
        
        logger.info("")
    
    def save_dynamic_config(self):
        """Guardar configuración de la descarga dinámica"""
        config_data = {
            "download_timestamp": datetime.now().isoformat(),
            "selection_timestamp": getattr(self, 'selection_timestamp', 'N/A'),
            "selected_pairs": self.trading_pairs,
            "download_stats": self.download_stats,
            "total_pairs": len(self.trading_pairs),
            "total_records": sum(stats['records'] for stats in self.download_stats.values()),
            "avg_dynamic_score": sum(stats['dynamic_score'] for stats in self.download_stats.values()) / len(self.download_stats) if self.download_stats else 0,
            "selection_criteria": "Automatic dynamic selection based on volume, stability, spread, and trend analysis"
        }
        
        config_file = f"{self.output_path}dynamic_multi_pair_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        logger.info(f"📝 Configuración dinámica guardada: {config_file}")

async def main():
    """Función principal"""
    downloader = DynamicMultiPairDownloader()
    success = await downloader.download_all_pairs()
    
    if success:
        logger.info("🎉 Descarga multi-par dinámico completada exitosamente")
        logger.info("🎯 El sistema usó automáticamente los mejores pares disponibles")
    else:
        logger.error("❌ Error en descarga multi-par dinámico")

if __name__ == "__main__":
    asyncio.run(main())
