#!/usr/bin/env python3
"""
SELECTOR DINÁMICO DE PARES DE TRADING
Sistema que analiza automáticamente todos los pares disponibles y selecciona
los mejores basado en métricas de performance, liquidez y estabilidad
"""

import asyncio
import pandas as pd
import numpy as np
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import aiohttp
from concurrent.futures import ThreadPoolExecutor

from utils.binance_client import get_binance_client
from utils.logger_setup import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

class DynamicPairSelector:
    def __init__(self):
        self.output_path = "data/dynamic_pair_analysis/"
        os.makedirs(self.output_path, exist_ok=True)
        
        # Criterios de evaluación
        self.evaluation_criteria = {
            "min_volume_24h": 1000000,  # Mínimo $1M volumen 24h
            "min_price_stability": 0.1,  # Mínima estabilidad de precio
            "max_spread": 0.005,         # Máximo 0.5% spread
            "min_market_cap_rank": 100,  # Top 100 cryptos
            "min_age_days": 365,         # Mínimo 1 año en el mercado
            "trend_analysis_period": 30, # Análisis de tendencia últimos 30 días
        }
        
        # Pares candidatos (universo completo USDT)
        self.candidate_pairs = []
        self.pair_metrics = {}
        self.selected_pairs = []
        
    async def discover_all_usdt_pairs(self) -> List[str]:
        """Descubrir todos los pares USDT disponibles en Binance"""
        try:
            client = await get_binance_client()
            
            # Obtener información de todos los símbolos
            exchange_info = await client.get_exchange_info()
            
            usdt_pairs = []
            for symbol_info in exchange_info['symbols']:
                symbol = symbol_info['symbol']
                status = symbol_info['status']
                quote_asset = symbol_info['quoteAsset']
                
                # Solo pares USDT activos
                if quote_asset == 'USDT' and status == 'TRADING':
                    usdt_pairs.append(symbol)
            
            logger.info(f"📊 Descubiertos {len(usdt_pairs)} pares USDT activos")
            return sorted(usdt_pairs)
            
        except Exception as e:
            logger.error(f"❌ Error descubriendo pares: {e}")
            # Fallback a lista conocida
            return [
                "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT",
                "SOLUSDT", "DOTUSDT", "AVAXUSDT", "MATICUSDT", "LINKUSDT",
                "LTCUSDT", "UNIUSDT", "ATOMUSDT", "FILUSDT", "TRXUSDT"
            ]
    
    async def analyze_pair_performance(self, symbol: str) -> Optional[Dict]:
        """Analizar performance de un par específico"""
        try:
            client = await get_binance_client()
            
            # 1. Estadísticas 24h
            ticker_24h = await client.get_ticker(symbol=symbol)
            
            # 2. Datos históricos recientes (últimos 30 días)
            end_time = datetime.now()
            start_time = end_time - timedelta(days=self.evaluation_criteria["trend_analysis_period"])
            
            klines = await client.get_historical_klines(
                symbol=symbol,
                interval="1d",  # Datos diarios para análisis
                start_str=int(start_time.timestamp() * 1000),
                end_str=int(end_time.timestamp() * 1000)
            )
            
            if not klines or len(klines) < 7:  # Mínimo 7 días
                return None
            
            # Procesar datos
            df = pd.DataFrame(klines, columns=[
                "timestamp", "open", "high", "low", "close", "volume",
                "close_time", "quote_asset_volume", "number_of_trades",
                "taker_buy_base_volume", "taker_buy_quote_volume", "ignore"
            ])
            
            df[["open", "high", "low", "close", "volume", "quote_asset_volume"]] = \
                df[["open", "high", "low", "close", "volume", "quote_asset_volume"]].astype(float)
            
            # Calcular métricas
            metrics = await self.calculate_pair_metrics(symbol, ticker_24h, df)
            
            return metrics
            
        except Exception as e:
            logger.debug(f"⚠️ Error analizando {symbol}: {e}")
            return None
    
    async def calculate_pair_metrics(self, symbol: str, ticker_24h: Dict, df: pd.DataFrame) -> Dict:
        """Calcular métricas comprehensivas para un par"""
        
        # Métricas básicas del ticker
        volume_24h = float(ticker_24h['quoteVolume'])  # Volumen en USDT
        price_change_pct = float(ticker_24h['priceChangePercent'])
        current_price = float(ticker_24h['lastPrice'])
        
        # Métricas de liquidez
        bid_price = float(ticker_24h.get('bidPrice', 0))
        ask_price = float(ticker_24h.get('askPrice', 0))
        spread = ((ask_price - bid_price) / current_price) if current_price > 0 else float('inf')
        
        # Métricas de volatilidad y tendencia
        closes = df['close'].astype(float)
        volumes = df['quote_asset_volume'].astype(float)
        
        # Volatilidad (desviación estándar de retornos diarios)
        returns = closes.pct_change().dropna()
        volatility = returns.std() * np.sqrt(365)  # Volatilidad anualizada
        
        # Tendencia (pendiente de regresión lineal)
        x = np.arange(len(closes))
        if len(closes) > 1:
            trend_slope = np.polyfit(x, closes, 1)[0]
            trend_strength = abs(trend_slope) / current_price  # Normalizado
        else:
            trend_slope = 0
            trend_strength = 0
        
        # Estabilidad de precio (inverso de volatilidad)
        price_stability = 1 / (1 + volatility) if volatility > 0 else 0
        
        # Consistencia de volumen
        volume_cv = volumes.std() / volumes.mean() if volumes.mean() > 0 else float('inf')
        volume_consistency = 1 / (1 + volume_cv)
        
        # Momentum (retorno acumulado últimos 7 días)
        if len(closes) >= 7:
            momentum_7d = (closes.iloc[-1] / closes.iloc[-7] - 1) * 100
        else:
            momentum_7d = 0
        
        # Score compuesto
        liquidity_score = min(100, volume_24h / 1000000)  # Escala hasta 100M = score 100
        stability_score = price_stability * 100
        spread_score = max(0, 100 - (spread * 10000))  # Penalizar spreads altos
        trend_score = min(100, trend_strength * 1000)  # Normalizado
        
        # Score ponderado final
        composite_score = (
            liquidity_score * 0.35 +    # 35% liquidez
            stability_score * 0.25 +    # 25% estabilidad  
            spread_score * 0.20 +       # 20% spread
            trend_score * 0.20          # 20% tendencia
        )
        
        metrics = {
            "symbol": symbol,
            "current_price": current_price,
            "volume_24h_usdt": volume_24h,
            "price_change_24h_pct": price_change_pct,
            "spread_pct": spread * 100,
            "volatility_annual": volatility,
            "price_stability": price_stability,
            "volume_consistency": volume_consistency,
            "trend_slope": trend_slope,
            "trend_strength": trend_strength,
            "momentum_7d_pct": momentum_7d,
            "data_points": len(df),
            
            # Scores individuales
            "liquidity_score": liquidity_score,
            "stability_score": stability_score,
            "spread_score": spread_score,
            "trend_score": trend_score,
            
            # Score final
            "composite_score": composite_score,
            
            # Evaluación de criterios
            "meets_volume_criteria": volume_24h >= self.evaluation_criteria["min_volume_24h"],
            "meets_stability_criteria": price_stability >= self.evaluation_criteria["min_price_stability"],
            "meets_spread_criteria": spread <= self.evaluation_criteria["max_spread"],
            
            "timestamp": datetime.now().isoformat()
        }
        
        return metrics
    
    async def evaluate_all_pairs(self, max_concurrent: int = 10) -> Dict[str, Dict]:
        """Evaluar todos los pares candidatos"""
        logger.info("🔍 INICIANDO EVALUACIÓN DINÁMICA DE PARES")
        logger.info("=" * 60)
        
        # Descubrir pares disponibles
        self.candidate_pairs = await self.discover_all_usdt_pairs()
        logger.info(f"📊 Analizando {len(self.candidate_pairs)} pares USDT")
        
        # Evaluar pares en lotes para evitar rate limits
        results = {}
        batch_size = max_concurrent
        total_batches = (len(self.candidate_pairs) + batch_size - 1) // batch_size
        
        for batch_idx in range(0, len(self.candidate_pairs), batch_size):
            batch = self.candidate_pairs[batch_idx:batch_idx + batch_size]
            batch_num = (batch_idx // batch_size) + 1
            
            logger.info(f"📥 Procesando lote {batch_num}/{total_batches}: {len(batch)} pares")
            
            # Procesar batch concurrentemente
            tasks = [self.analyze_pair_performance(symbol) for symbol in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Procesar resultados del batch
            for symbol, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.debug(f"⚠️ Error en {symbol}: {result}")
                    continue
                
                if result is not None:
                    results[symbol] = result
                    logger.debug(f"✅ {symbol}: Score {result['composite_score']:.1f}")
            
            # Pausa entre batches
            if batch_num < total_batches:
                await asyncio.sleep(2)
        
        logger.info(f"✅ Evaluación completada: {len(results)}/{len(self.candidate_pairs)} pares analizados")
        
        self.pair_metrics = results
        return results
    
    def select_best_pairs(self, target_count: int = 8, diversification: bool = True) -> List[str]:
        """Seleccionar los mejores pares basado en scores y diversificación"""
        if not self.pair_metrics:
            logger.error("❌ No hay métricas de pares disponibles")
            return []
        
        logger.info(f"🎯 SELECCIONANDO TOP {target_count} PARES")
        logger.info("=" * 50)
        
        # Filtrar pares que cumplen criterios mínimos
        qualified_pairs = {}
        for symbol, metrics in self.pair_metrics.items():
            meets_criteria = (
                metrics["meets_volume_criteria"] and
                metrics["meets_stability_criteria"] and
                metrics["meets_spread_criteria"] and
                metrics["composite_score"] >= 20  # Score mínimo
            )
            
            if meets_criteria:
                qualified_pairs[symbol] = metrics
        
        logger.info(f"📊 Pares calificados: {len(qualified_pairs)}")
        
        if not qualified_pairs:
            logger.warning("⚠️ No hay pares que cumplan los criterios")
            return []
        
        # Ordenar por score compuesto
        sorted_pairs = sorted(qualified_pairs.items(), 
                            key=lambda x: x[1]['composite_score'], 
                            reverse=True)
        
        if not diversification:
            # Selección simple por score
            selected = [pair[0] for pair in sorted_pairs[:target_count]]
        else:
            # Selección diversificada
            selected = self.diversified_selection(sorted_pairs, target_count)
        
        # Guardar selección
        self.selected_pairs = selected
        
        # Mostrar resultados
        logger.info(f"🏆 PARES SELECCIONADOS:")
        for i, symbol in enumerate(selected, 1):
            metrics = self.pair_metrics[symbol]
            logger.info(f"   {i}. {symbol}: Score {metrics['composite_score']:.1f} "
                       f"(Vol: ${metrics['volume_24h_usdt']:,.0f})")
        
        return selected
    
    def diversified_selection(self, sorted_pairs: List[Tuple], target_count: int) -> List[str]:
        """Selección diversificada considerando correlaciones y sectores"""
        
        # Categorización básica por símbolo
        categories = {
            "major": ["BTC", "ETH"],
            "defi": ["UNI", "SUSHI", "CAKE", "COMP", "AAVE", "CRV"],
            "layer1": ["ADA", "SOL", "AVAX", "DOT", "ATOM", "NEAR", "FTM"],
            "exchange": ["BNB", "FTT", "CRO", "KCS"],
            "payments": ["XRP", "LTC", "BCH", "XLM"],
            "oracle": ["LINK", "BAND"],
            "storage": ["FIL", "AR"],
            "gaming": ["AXS", "SAND", "MANA", "ENJ"],
            "meme": ["DOGE", "SHIB"],
            "other": []
        }
        
        def get_category(symbol):
            base = symbol.replace("USDT", "")
            for category, tokens in categories.items():
                if base in tokens:
                    return category
            return "other"
        
        selected = []
        category_counts = {}
        
        # Selección diversificada
        for symbol, metrics in sorted_pairs:
            if len(selected) >= target_count:
                break
            
            category = get_category(symbol)
            current_count = category_counts.get(category, 0)
            
            # Límites por categoría
            category_limits = {
                "major": 2,      # Máximo 2 majors (BTC, ETH)
                "layer1": 3,     # Máximo 3 Layer 1
                "defi": 2,       # Máximo 2 DeFi
                "exchange": 1,   # Máximo 1 exchange token
                "other": 3       # Resto sin límite estricto
            }
            
            limit = category_limits.get(category, 2)
            
            if current_count < limit:
                selected.append(symbol)
                category_counts[category] = current_count + 1
        
        # Si no tenemos suficientes, agregar los mejores restantes
        if len(selected) < target_count:
            remaining_needed = target_count - len(selected)
            for symbol, metrics in sorted_pairs:
                if symbol not in selected and remaining_needed > 0:
                    selected.append(symbol)
                    remaining_needed -= 1
        
        return selected[:target_count]
    
    def generate_selection_report(self):
        """Generar reporte de la selección de pares"""
        if not self.selected_pairs or not self.pair_metrics:
            logger.error("❌ No hay datos para generar reporte")
            return
        
        logger.info("")
        logger.info("📊 REPORTE DE SELECCIÓN DINÁMICA DE PARES")
        logger.info("=" * 60)
        
        # Estadísticas generales
        total_analyzed = len(self.pair_metrics)
        total_selected = len(self.selected_pairs)
        
        avg_score = np.mean([m['composite_score'] for m in self.pair_metrics.values()])
        selected_avg_score = np.mean([self.pair_metrics[s]['composite_score'] for s in self.selected_pairs])
        
        total_volume = sum(self.pair_metrics[s]['volume_24h_usdt'] for s in self.selected_pairs)
        
        logger.info(f"📈 ESTADÍSTICAS GENERALES:")
        logger.info(f"   • Total pares analizados: {total_analyzed}")
        logger.info(f"   • Pares seleccionados: {total_selected}")
        logger.info(f"   • Score promedio general: {avg_score:.1f}")
        logger.info(f"   • Score promedio seleccionados: {selected_avg_score:.1f}")
        logger.info(f"   • Volumen total 24h: ${total_volume:,.0f}")
        logger.info("")
        
        # Detalles por par seleccionado
        logger.info(f"💰 DETALLES DE PARES SELECCIONADOS:")
        logger.info("─" * 60)
        
        for i, symbol in enumerate(self.selected_pairs, 1):
            metrics = self.pair_metrics[symbol]
            
            logger.info(f"{i}. {symbol}:")
            logger.info(f"   • Score: {metrics['composite_score']:.1f}/100")
            logger.info(f"   • Precio: ${metrics['current_price']:.4f}")
            logger.info(f"   • Volumen 24h: ${metrics['volume_24h_usdt']:,.0f}")
            logger.info(f"   • Cambio 24h: {metrics['price_change_24h_pct']:.2f}%")
            logger.info(f"   • Spread: {metrics['spread_pct']:.3f}%")
            logger.info(f"   • Estabilidad: {metrics['price_stability']:.3f}")
            logger.info("")
        
        # Comparación con top performers no seleccionados
        all_sorted = sorted(self.pair_metrics.items(), 
                          key=lambda x: x[1]['composite_score'], 
                          reverse=True)
        
        logger.info(f"🔍 TOP 5 PARES NO SELECCIONADOS:")
        logger.info("─" * 40)
        
        not_selected = [(s, m) for s, m in all_sorted if s not in self.selected_pairs][:5]
        for i, (symbol, metrics) in enumerate(not_selected, 1):
            logger.info(f"   {i}. {symbol}: Score {metrics['composite_score']:.1f} "
                       f"(Vol: ${metrics['volume_24h_usdt']:,.0f})")
        
        # Guardar configuración
        config_data = {
            "selection_timestamp": datetime.now().isoformat(),
            "selection_criteria": self.evaluation_criteria,
            "selected_pairs": self.selected_pairs,
            "pair_metrics": {s: self.pair_metrics[s] for s in self.selected_pairs},
            "total_pairs_analyzed": total_analyzed,
            "selection_stats": {
                "avg_score_all": avg_score,
                "avg_score_selected": selected_avg_score,
                "total_volume_24h": total_volume
            }
        }
        
        config_file = f"{self.output_path}dynamic_pair_selection.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        logger.info(f"📝 Configuración guardada en: {config_file}")
        logger.info("")
        logger.info("🎯 PRÓXIMO PASO: Usar estos pares para descarga multi-par")
        logger.info("   Ejecutar: python download_multi_pair_data.py --dynamic")

async def main():
    """Función principal"""
    selector = DynamicPairSelector()
    
    try:
        # Evaluar todos los pares
        metrics = await selector.evaluate_all_pairs()
        
        if not metrics:
            logger.error("❌ No se pudieron obtener métricas de pares")
            return
        
        # Seleccionar mejores pares
        selected_pairs = selector.select_best_pairs(target_count=8, diversification=True)
        
        if selected_pairs:
            selector.generate_selection_report()
            logger.info("🎉 Selección dinámica de pares completada exitosamente")
        else:
            logger.error("❌ No se pudieron seleccionar pares")
        
    except Exception as e:
        logger.error(f"❌ Error en selección dinámica: {e}")

if __name__ == "__main__":
    asyncio.run(main())
