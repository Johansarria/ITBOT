#!/usr/bin/env python3
"""
Sistema de Descarga Multi-Par para Trading Institucional
Descarga datos históricos para múltiples pares de criptomonedas
"""

import asyncio
import pandas as pd
import os
from binance.exceptions import BinanceAPIException
import logging
from datetime import datetime
import json
from concurrent.futures import ThreadPoolExecutor
import time

from utils.binance_client import get_binance_client
from utils.logger_setup import setup_logging
from database.database_manager import add_klines
from config import settings

setup_logging()
logger = logging.getLogger(__name__)

class MultiPairDataDownloader:
    def __init__(self):
        # Lista de pares principales para trading institucional
        self.trading_pairs = [
            "BTCUSDT",   # Bitcoin - Par principal
            "ETHUSDT",   # Ethereum - Segundo más líquido
            "BNBUSDT",   # Binance Coin - Nativo del exchange
            "ADAUSDT",   # Cardano - Alt coin sólida
            "XRPUSDT",   # Ripple - Diversificación
            "SOLUSDT",   # Solana - Layer 1 moderno
            "DOTUSDT",   # Polkadot - Interoperabilidad
            "AVAXUSDT"   # Avalanche - DeFi ecosystem
        ]
        
        self.interval = "1h"
        self.start_str = "1 Jan, 2017"  # Desde que la mayoría de pares están disponibles
        self.output_path = "data/multi_pair_historical/"
        
        # Crear directorio
        os.makedirs(self.output_path, exist_ok=True)
        
        # Estadísticas de descarga
        self.download_stats = {}
        
    async def download_all_pairs(self):
        """Descargar datos históricos para todos los pares"""
        logger.info("🚀 INICIANDO DESCARGA MULTI-PAR")
        logger.info("📊 Sistema de Trading Institucional Diversificado")
        logger.info("="*70)
        
        logger.info(f"💰 Pares a descargar: {len(self.trading_pairs)}")
        for i, pair in enumerate(self.trading_pairs, 1):
            logger.info(f"   {i}. {pair}")
        logger.info("")
        
        start_time = time.time()
        
        # Descargar cada par secuencialmente para evitar rate limits
        successful_downloads = 0
        total_records = 0
        
        for pair in self.trading_pairs:
            logger.info(f"📥 Descargando {pair}...")
            success, records = await self.download_pair_data(pair)
            
            if success:
                successful_downloads += 1
                total_records += records
                logger.info(f"✅ {pair}: {records:,} registros descargados")
            else:
                logger.error(f"❌ {pair}: Error en descarga")
            
            # Pausa entre descargas para respetar rate limits
            await asyncio.sleep(1)
        
        total_time = time.time() - start_time
        
        # Generar reporte final
        await self.generate_multi_pair_report(successful_downloads, total_records, total_time)
        
        return successful_downloads > 0
    
    async def download_pair_data(self, symbol):
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
                logger.warning(f"⚠️ No se obtuvieron datos para {symbol}")
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
            
            # Validar datos
            if df.empty:
                return False, 0
            
            # Calcular estadísticas
            records_count = len(df)
            date_range = (df.index[-1] - df.index[0]).days
            years_covered = date_range / 365.25
            data_completeness = min(100.0, (records_count / (date_range * 24)) * 100) if date_range > 0 else 0
            
            # Guardar estadísticas
            self.download_stats[symbol] = {
                "records": records_count,
                "start_date": df.index[0].strftime("%Y-%m-%d"),
                "end_date": df.index[-1].strftime("%Y-%m-%d"),
                "years_covered": round(years_covered, 1),
                "completeness": round(data_completeness, 1),
                "avg_volume": round(df['volume'].mean(), 2)
            }
            
            # Guardar en CSV
            csv_file = f"{self.output_path}{symbol.lower()}_{self.interval}_historical.csv"
            df.to_csv(csv_file)
            
            # Guardar en base de datos
            try:
                df_to_db = df.copy()
                df_to_db["timestamp"] = df_to_db.index.astype(int) // 10**6
                df_to_db["close_time"] = df_to_db["close_time"].astype(int)
                add_klines(df_to_db, symbol, self.interval)
            except Exception as e:
                logger.warning(f"⚠️ Error BD para {symbol}: {e}")
            
            return True, records_count
            
        except BinanceAPIException as e:
            logger.error(f"❌ Error API Binance para {symbol}: {e}")
            return False, 0
        except Exception as e:
            logger.error(f"❌ Error inesperado para {symbol}: {e}")
            return False, 0
    
    async def generate_multi_pair_report(self, successful_downloads, total_records, total_time):
        """Generar reporte detallado de la descarga multi-par"""
        logger.info("="*80)
        logger.info("🎉 DESCARGA MULTI-PAR COMPLETADA")
        logger.info("="*80)
        
        logger.info(f"📊 Resumen de descarga:")
        logger.info(f"   • Pares exitosos: {successful_downloads}/{len(self.trading_pairs)}")
        logger.info(f"   • Total registros: {total_records:,}")
        logger.info(f"   • Tiempo total: {total_time/60:.1f} minutos")
        logger.info(f"   • Velocidad promedio: {total_records/total_time:.0f} registros/segundo")
        logger.info("")
        
        # Detalles por par
        logger.info("📈 DETALLES POR PAR:")
        logger.info("─" * 80)
        
        if self.download_stats:
            # Ordenar por cantidad de registros
            sorted_pairs = sorted(self.download_stats.items(), key=lambda x: x[1]['records'], reverse=True)
            
            for symbol, stats in sorted_pairs:
                logger.info(f"💰 {symbol}:")
                logger.info(f"   📊 Registros: {stats['records']:,}")
                logger.info(f"   📅 Período: {stats['start_date']} a {stats['end_date']}")
                logger.info(f"   ⏰ Años: {stats['years_covered']}")
                logger.info(f"   📈 Completitud: {stats['completeness']}%")
                logger.info(f"   📊 Vol. promedio: {stats['avg_volume']:,.0f}")
                logger.info("")
        
        # Análisis de diversificación
        self.analyze_diversification()
        
        # Generar archivo de configuración
        self.generate_pair_config()
        
        logger.info("🚀 SISTEMA MULTI-PAR LISTO PARA TRADING INSTITUCIONAL")
        logger.info("="*80)
    
    def analyze_diversification(self):
        """Analizar la diversificación del portafolio de pares"""
        logger.info("🔍 ANÁLISIS DE DIVERSIFICACIÓN:")
        logger.info("─" * 50)
        
        if not self.download_stats:
            logger.info("⚠️ No hay datos para analizar")
            return
        
        # Categorizar pares por sector/función
        categories = {
            "Store of Value": ["BTCUSDT"],
            "Smart Contracts": ["ETHUSDT", "ADAUSDT", "SOLUSDT", "AVAXUSDT"],
            "Exchange Tokens": ["BNBUSDT"],
            "Payments": ["XRPUSDT"],
            "Interoperability": ["DOTUSDT"]
        }
        
        total_pairs = len(self.download_stats)
        total_records = sum(stats['records'] for stats in self.download_stats.values())
        
        logger.info(f"📊 Total pares activos: {total_pairs}")
        logger.info(f"📈 Total registros: {total_records:,}")
        logger.info("")
        
        logger.info("🏷️ DIVERSIFICACIÓN POR CATEGORÍA:")
        for category, pairs in categories.items():
            active_pairs = [p for p in pairs if p in self.download_stats]
            if active_pairs:
                category_records = sum(self.download_stats[p]['records'] for p in active_pairs)
                percentage = (category_records / total_records) * 100
                logger.info(f"   • {category}: {len(active_pairs)} pares ({percentage:.1f}% datos)")
        
        logger.info("")
        
        # Análisis de correlación potencial
        logger.info("🔗 ANÁLISIS DE CORRELACIÓN POTENCIAL:")
        logger.info("   • BTC-ETH: Alta correlación esperada (>0.7)")
        logger.info("   • Layer 1 (ETH,SOL,AVAX): Correlación media (0.5-0.7)")
        logger.info("   • Exchange tokens (BNB): Correlación baja-media")
        logger.info("   • Payments (XRP): Correlación variable por regulación")
        logger.info("")
    
    def generate_pair_config(self):
        """Generar archivo de configuración para los pares"""
        config_data = {
            "multi_pair_config": {
                "last_update": datetime.now().isoformat(),
                "total_pairs": len(self.download_stats),
                "pairs": self.download_stats,
                "recommended_weights": self.calculate_recommended_weights(),
                "risk_tiers": self.classify_risk_tiers()
            }
        }
        
        config_file = f"{self.output_path}multi_pair_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        logger.info(f"📝 Configuración guardada en: {config_file}")
    
    def calculate_recommended_weights(self):
        """Calcular pesos recomendados para cada par"""
        if not self.download_stats:
            return {}
        
        # Pesos basados en capitalización de mercado y estabilidad
        base_weights = {
            "BTCUSDT": 35,  # Bitcoin - Peso mayor por estabilidad
            "ETHUSDT": 25,  # Ethereum - Segundo activo
            "BNBUSDT": 10,  # Binance - Exchange token
            "ADAUSDT": 8,   # Cardano - Proof of stake
            "SOLUSDT": 8,   # Solana - Competencia directa
            "XRPUSDT": 7,   # Ripple - Pagos
            "AVAXUSDT": 4,  # Avalanche - Menor por volatilidad
            "DOTUSDT": 3    # Polkadot - Menor peso
        }
        
        # Ajustar pesos basado en datos disponibles
        available_pairs = set(self.download_stats.keys())
        adjusted_weights = {}
        
        total_weight = 0
        for pair, weight in base_weights.items():
            if pair in available_pairs:
                adjusted_weights[pair] = weight
                total_weight += weight
        
        # Normalizar a 100%
        if total_weight > 0:
            for pair in adjusted_weights:
                adjusted_weights[pair] = round((adjusted_weights[pair] / total_weight) * 100, 1)
        
        return adjusted_weights
    
    def classify_risk_tiers(self):
        """Clasificar pares por nivel de riesgo"""
        return {
            "Low Risk": ["BTCUSDT", "ETHUSDT"],
            "Medium Risk": ["BNBUSDT", "ADAUSDT", "XRPUSDT"],
            "High Risk": ["SOLUSDT", "AVAXUSDT", "DOTUSDT"]
        }

async def main():
    """Función principal"""
    downloader = MultiPairDataDownloader()
    success = await downloader.download_all_pairs()
    
    if success:
        logger.info("🎉 Descarga multi-par completada exitosamente")
        logger.info("💡 Próximo paso: Entrenar modelos ML para cada par")
        logger.info("📊 Comando: python train_multi_pair_models.py")
    else:
        logger.error("❌ Error en descarga multi-par")

if __name__ == "__main__":
    asyncio.run(main())
