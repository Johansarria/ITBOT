"""
SICAR - Analizador Inteligente de OrderBook
==========================================

Módulo especializado para el análisis avanzado de datos de orderbook (depth)
que se integra con el sistema híbrido inteligente existente.

Características:
- Procesamiento de datos de depth de Binance
- Análisis de liquidez y spreads reales
- Detección de anomalías en el orderbook
- Integración con el sistema de logging avanzado
- Métricas de profundidad de mercado
"""

import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import sqlite3
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class OrderBookMetrics:
    """Métricas calculadas del orderbook"""
    symbol: str
    timestamp: datetime
    bid_price: float
    ask_price: float
    spread_absolute: float
    spread_percentage: float
    bid_volume: float
    ask_volume: float
    volume_imbalance: float
    liquidity_score: float
    depth_quality: float
    market_impact_buy: float
    market_impact_sell: float
    weighted_mid_price: float
    
    def to_dict(self):
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'bid_price': self.bid_price,
            'ask_price': self.ask_price,
            'spread_absolute': self.spread_absolute,
            'spread_percentage': self.spread_percentage,
            'bid_volume': self.bid_volume,
            'ask_volume': self.ask_volume,
            'volume_imbalance': self.volume_imbalance,
            'liquidity_score': self.liquidity_score,
            'depth_quality': self.depth_quality,
            'market_impact_buy': self.market_impact_buy,
            'market_impact_sell': self.market_impact_sell,
            'weighted_mid_price': self.weighted_mid_price
        }

class OrderBookAnalyzer:
    """Analizador inteligente de orderbook"""
    
    def __init__(self, db_path: str = "orderbook_analysis.db"):
        self.db_path = db_path
        self.init_database()
        
        # Parámetros de análisis
        self.depth_levels = 20  # Niveles de profundidad a analizar
        self.volume_threshold = 1000  # Umbral mínimo de volumen USD
        self.spread_alert_threshold = 0.005  # 0.5% spread alert
        
        logger.info("🔍 OrderBook Analyzer inicializado")
    
    def init_database(self):
        """Inicializar base de datos para métricas de orderbook"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orderbook_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    bid_price REAL NOT NULL,
                    ask_price REAL NOT NULL,
                    spread_absolute REAL NOT NULL,
                    spread_percentage REAL NOT NULL,
                    bid_volume REAL NOT NULL,
                    ask_volume REAL NOT NULL,
                    volume_imbalance REAL NOT NULL,
                    liquidity_score REAL NOT NULL,
                    depth_quality REAL NOT NULL,
                    market_impact_buy REAL NOT NULL,
                    market_impact_sell REAL NOT NULL,
                    weighted_mid_price REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orderbook_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error inicializando base de datos: {e}")
    
    def analyze_depth_data(self, symbol: str, depth_data: Dict) -> Optional[OrderBookMetrics]:
        """
        Analizar datos de depth y calcular métricas avanzadas
        
        Args:
            symbol: Símbolo del par de trading
            depth_data: Datos de depth de Binance API
            
        Returns:
            OrderBookMetrics con todas las métricas calculadas
        """
        try:
            if not depth_data or 'bids' not in depth_data or 'asks' not in depth_data:
                logger.warning(f"Datos de depth inválidos para {symbol}")
                return None
            
            bids = [[float(price), float(qty)] for price, qty in depth_data['bids'][:self.depth_levels]]
            asks = [[float(price), float(qty)] for price, qty in depth_data['asks'][:self.depth_levels]]
            
            if not bids or not asks:
                logger.warning(f"OrderBook vacío para {symbol}")
                return None
            
            # Precios bid/ask principales
            best_bid = bids[0][0]
            best_ask = asks[0][0]
            
            # Cálculos básicos de spread
            spread_absolute = best_ask - best_bid
            spread_percentage = (spread_absolute / best_bid) * 100
            
            # Volúmenes acumulados
            bid_volume = sum(price * qty for price, qty in bids)
            ask_volume = sum(price * qty for price, qty in asks)
            
            # Imbalance de volumen
            total_volume = bid_volume + ask_volume
            volume_imbalance = (bid_volume - ask_volume) / total_volume if total_volume > 0 else 0
            
            # Score de liquidez
            liquidity_score = self._calculate_liquidity_score(bids, asks)
            
            # Calidad de profundidad
            depth_quality = self._calculate_depth_quality(bids, asks)
            
            # Impacto de mercado
            market_impact_buy = self._calculate_market_impact(asks, 'buy')
            market_impact_sell = self._calculate_market_impact(bids, 'sell')
            
            # Precio medio ponderado
            weighted_mid_price = self._calculate_weighted_mid_price(bids, asks)
            
            metrics = OrderBookMetrics(
                symbol=symbol,
                timestamp=datetime.now(timezone.utc),
                bid_price=best_bid,
                ask_price=best_ask,
                spread_absolute=spread_absolute,
                spread_percentage=spread_percentage,
                bid_volume=bid_volume,
                ask_volume=ask_volume,
                volume_imbalance=volume_imbalance,
                liquidity_score=liquidity_score,
                depth_quality=depth_quality,
                market_impact_buy=market_impact_buy,
                market_impact_sell=market_impact_sell,
                weighted_mid_price=weighted_mid_price
            )
            
            # Guardar métricas en base de datos
            self._save_metrics(metrics)
            
            # Verificar alertas
            self._check_alerts(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error analizando depth data para {symbol}: {e}")
            return None
    
    def _calculate_liquidity_score(self, bids: List[List[float]], asks: List[List[float]]) -> float:
        """Calcular score de liquidez basado en volumen y distribución"""
        try:
            # Volumen total en los primeros 5 niveles
            bid_vol_5 = sum(qty for price, qty in bids[:5])
            ask_vol_5 = sum(qty for price, qty in asks[:5])
            
            # Volumen total en todos los niveles
            bid_vol_total = sum(qty for price, qty in bids)
            ask_vol_total = sum(qty for price, qty in asks)
            
            # Concentración de liquidez (mayor concentración = menor score)
            bid_concentration = bid_vol_5 / bid_vol_total if bid_vol_total > 0 else 1
            ask_concentration = ask_vol_5 / ask_vol_total if ask_vol_total > 0 else 1
            
            avg_concentration = (bid_concentration + ask_concentration) / 2
            
            # Score inverso a la concentración (más distribuido = mejor)
            distribution_score = 1 - avg_concentration
            
            # Score de volumen absoluto
            total_volume = (bid_vol_total + ask_vol_total) * bids[0][0]  # En USD aproximado
            volume_score = min(1.0, total_volume / 100000)  # Normalizar a 100k USD
            
            # Score combinado
            liquidity_score = (distribution_score * 0.4 + volume_score * 0.6) * 100
            
            return round(liquidity_score, 2)
            
        except Exception as e:
            logger.error(f"Error calculando liquidity score: {e}")
            return 0.0
    
    def _calculate_depth_quality(self, bids: List[List[float]], asks: List[List[float]]) -> float:
        """Calcular calidad de profundidad basada en consistencia de precios"""
        try:
            # Verificar consistencia de spreads entre niveles
            bid_spreads = []
            ask_spreads = []
            
            for i in range(1, min(10, len(bids))):
                bid_spread = (bids[i-1][0] - bids[i][0]) / bids[i][0]
                bid_spreads.append(bid_spread)
            
            for i in range(1, min(10, len(asks))):
                ask_spread = (asks[i][0] - asks[i-1][0]) / asks[i-1][0]
                ask_spreads.append(ask_spread)
            
            # Calcular variabilidad de spreads (menor variabilidad = mejor calidad)
            bid_std = np.std(bid_spreads) if bid_spreads else 0
            ask_std = np.std(ask_spreads) if ask_spreads else 0
            
            avg_std = (bid_std + ask_std) / 2
            
            # Score inverso a la variabilidad
            quality_score = max(0, 100 - (avg_std * 10000))  # Escalar apropiadamente
            
            return round(quality_score, 2)
            
        except Exception as e:
            logger.error(f"Error calculando depth quality: {e}")
            return 0.0
    
    def _calculate_market_impact(self, orders: List[List[float]], side: str) -> float:
        """Calcular impacto de mercado para una orden de tamaño estándar"""
        try:
            # Simular orden de $10,000 USD
            target_value = 10000
            cumulative_value = 0
            weighted_price = 0
            
            for price, qty in orders:
                order_value = price * qty
                
                if cumulative_value + order_value >= target_value:
                    # Orden parcial en este nivel
                    remaining_value = target_value - cumulative_value
                    remaining_qty = remaining_value / price
                    weighted_price += price * remaining_qty
                    break
                else:
                    # Orden completa en este nivel
                    weighted_price += price * qty
                    cumulative_value += order_value
            
            if cumulative_value > 0:
                avg_execution_price = weighted_price / (target_value / orders[0][0])
                market_impact = abs(avg_execution_price - orders[0][0]) / orders[0][0] * 100
                return round(market_impact, 4)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculando market impact: {e}")
            return 0.0
    
    def _calculate_weighted_mid_price(self, bids: List[List[float]], asks: List[List[float]]) -> float:
        """Calcular precio medio ponderado por volumen"""
        try:
            # Tomar los primeros 5 niveles para el cálculo
            bid_levels = bids[:5]
            ask_levels = asks[:5]
            
            bid_weighted_sum = sum(price * qty for price, qty in bid_levels)
            ask_weighted_sum = sum(price * qty for price, qty in ask_levels)
            
            bid_total_qty = sum(qty for price, qty in bid_levels)
            ask_total_qty = sum(qty for price, qty in ask_levels)
            
            if bid_total_qty > 0 and ask_total_qty > 0:
                bid_weighted_price = bid_weighted_sum / bid_total_qty
                ask_weighted_price = ask_weighted_sum / ask_total_qty
                
                weighted_mid = (bid_weighted_price + ask_weighted_price) / 2
                return round(weighted_mid, 8)
            
            return (bids[0][0] + asks[0][0]) / 2
            
        except Exception as e:
            logger.error(f"Error calculando weighted mid price: {e}")
            return 0.0
    
    def _save_metrics(self, metrics: OrderBookMetrics):
        """Guardar métricas en base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO orderbook_metrics (
                    symbol, timestamp, bid_price, ask_price, spread_absolute,
                    spread_percentage, bid_volume, ask_volume, volume_imbalance,
                    liquidity_score, depth_quality, market_impact_buy,
                    market_impact_sell, weighted_mid_price
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.symbol, metrics.timestamp.isoformat(), metrics.bid_price,
                metrics.ask_price, metrics.spread_absolute, metrics.spread_percentage,
                metrics.bid_volume, metrics.ask_volume, metrics.volume_imbalance,
                metrics.liquidity_score, metrics.depth_quality, metrics.market_impact_buy,
                metrics.market_impact_sell, metrics.weighted_mid_price
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error guardando métricas: {e}")
    
    def _check_alerts(self, metrics: OrderBookMetrics):
        """Verificar condiciones de alerta"""
        try:
            alerts = []
            
            # Alerta de spread alto
            if metrics.spread_percentage > self.spread_alert_threshold * 100:
                alerts.append({
                    'type': 'HIGH_SPREAD',
                    'message': f'Spread alto detectado: {metrics.spread_percentage:.3f}%',
                    'severity': 'WARNING'
                })
            
            # Alerta de imbalance extremo
            if abs(metrics.volume_imbalance) > 0.7:
                alerts.append({
                    'type': 'VOLUME_IMBALANCE',
                    'message': f'Imbalance de volumen extremo: {metrics.volume_imbalance:.3f}',
                    'severity': 'HIGH'
                })
            
            # Alerta de baja liquidez
            if metrics.liquidity_score < 30:
                alerts.append({
                    'type': 'LOW_LIQUIDITY',
                    'message': f'Liquidez baja detectada: {metrics.liquidity_score:.1f}',
                    'severity': 'WARNING'
                })
            
            # Alerta de alta calidad de profundidad
            if metrics.depth_quality > 90:
                alerts.append({
                    'type': 'HIGH_QUALITY_DEPTH',
                    'message': f'Excelente calidad de orderbook: {metrics.depth_quality:.1f}',
                    'severity': 'INFO'
                })
            
            # Guardar alertas
            for alert in alerts:
                self._save_alert(metrics.symbol, alert, metrics.timestamp)
                
        except Exception as e:
            logger.error(f"Error verificando alertas: {e}")
    
    def _save_alert(self, symbol: str, alert: Dict, timestamp: datetime):
        """Guardar alerta en base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO orderbook_alerts (symbol, alert_type, message, severity, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (symbol, alert['type'], alert['message'], alert['severity'], timestamp.isoformat()))
            
            conn.commit()
            conn.close()
            
            # Log de la alerta
            severity_emoji = {'INFO': '💡', 'WARNING': '⚠️', 'HIGH': '🚨'}
            emoji = severity_emoji.get(alert['severity'], '📊')
            logger.info(f"{emoji} {symbol}: {alert['message']}")
            
        except Exception as e:
            logger.error(f"Error guardando alerta: {e}")
    
    def get_recent_metrics(self, symbol: str = None, hours: int = 24) -> List[Dict]:
        """Obtener métricas recientes"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if symbol:
                cursor.execute('''
                    SELECT * FROM orderbook_metrics 
                    WHERE symbol = ? AND datetime(timestamp) > datetime('now', '-{} hours')
                    ORDER BY timestamp DESC
                '''.format(hours), (symbol,))
            else:
                cursor.execute('''
                    SELECT * FROM orderbook_metrics 
                    WHERE datetime(timestamp) > datetime('now', '-{} hours')
                    ORDER BY timestamp DESC
                '''.format(hours))
            
            columns = [description[0] for description in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Error obteniendo métricas recientes: {e}")
            return []
    
    def get_summary_stats(self, symbol: str, hours: int = 24) -> Dict:
        """Obtener estadísticas resumidas"""
        try:
            metrics = self.get_recent_metrics(symbol, hours)
            
            if not metrics:
                return {}
            
            df = pd.DataFrame(metrics)
            
            summary = {
                'symbol': symbol,
                'period_hours': hours,
                'total_samples': len(metrics),
                'avg_spread_pct': df['spread_percentage'].mean(),
                'max_spread_pct': df['spread_percentage'].max(),
                'min_spread_pct': df['spread_percentage'].min(),
                'avg_liquidity_score': df['liquidity_score'].mean(),
                'avg_depth_quality': df['depth_quality'].mean(),
                'avg_volume_imbalance': df['volume_imbalance'].mean(),
                'avg_market_impact_buy': df['market_impact_buy'].mean(),
                'avg_market_impact_sell': df['market_impact_sell'].mean()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error calculando estadísticas: {e}")
            return {}

# Función de integración con el sistema existente
def integrate_with_market_conditions(depth_data: Dict, symbol: str) -> Dict:
    """
    Función de integración que procesa depth data y retorna métricas
    para ser usadas en el sistema de condiciones de mercado existente
    """
    try:
        analyzer = OrderBookAnalyzer()
        metrics = analyzer.analyze_depth_data(symbol, depth_data)
        
        if metrics:
            return {
                'bid_price': metrics.bid_price,
                'ask_price': metrics.ask_price,
                'spread_pct': metrics.spread_percentage,
                'liquidity_score': metrics.liquidity_score,
                'volume_imbalance': metrics.volume_imbalance,
                'depth_quality': metrics.depth_quality,
                'market_impact': (metrics.market_impact_buy + metrics.market_impact_sell) / 2,
                'weighted_mid_price': metrics.weighted_mid_price
            }
        
        return {}
        
    except Exception as e:
        logger.error(f"Error en integración: {e}")
        return {}

if __name__ == "__main__":
    # Test del analizador
    analyzer = OrderBookAnalyzer()
    logger.info("🚀 OrderBook Analyzer listo para integración")