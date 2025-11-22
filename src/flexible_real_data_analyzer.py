#!/usr/bin/env python3
"""
🚀 SICAR Flexible Real Data Analyzer
==================================================
📊 ANALIZADOR FLEXIBLE CON DATOS REALES DE BINANCE
==================================================

Analiza datos históricos reales con parámetros más flexibles
para detectar oportunidades de breakout que podrían haberse perdido.
"""

import asyncio
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import json

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class FlexibleBreakoutOpportunity:
    """Oportunidad de breakout detectada con parámetros flexibles"""
    timestamp: datetime
    symbol: str
    session: str
    signal_type: str
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    volume_ratio: float
    price_move_pct: float
    spread_pct: float
    confidence: float
    candle_data: Dict

@dataclass
class FlexibleSessionConfig:
    """Configuración flexible de sesión"""
    name: str
    start_hour: int
    duration_minutes: int
    # Parámetros MÁS FLEXIBLES
    min_price_move_pct: float = 0.001  # 0.1% (más flexible)
    min_volume_ratio: float = 0.8      # 80% del volumen promedio (más flexible)
    max_spread_pct: float = 0.05       # 5% spread máximo (más flexible)
    stop_loss_pct: float = 0.02        # 2% stop loss
    take_profit_pct: float = 0.04      # 4% take profit
    position_size_pct: float = 0.1     # 10% del capital

class FlexibleRealDataAnalyzer:
    """Analizador flexible de datos reales de Binance"""
    
    def __init__(self, initial_capital: float = 1000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.binance_base_url = "https://api.binance.com/api/v3"
        
        # Configuraciones de sesión MÁS FLEXIBLES
        self.session_configs = {
            'Asian': FlexibleSessionConfig(
                name='Asian',
                start_hour=1,  # 1:00 AM UTC
                duration_minutes=60,
                min_price_move_pct=0.0005,  # 0.05% - MUY FLEXIBLE
                min_volume_ratio=0.5,       # 50% - MUY FLEXIBLE
                max_spread_pct=0.08,        # 8% - MUY FLEXIBLE
                stop_loss_pct=0.015,        # 1.5%
                take_profit_pct=0.03,       # 3%
                position_size_pct=0.08      # 8%
            ),
            'European': FlexibleSessionConfig(
                name='European',
                start_hour=8,  # 8:00 AM UTC
                duration_minutes=60,
                min_price_move_pct=0.0008,  # 0.08% - MUY FLEXIBLE
                min_volume_ratio=0.6,       # 60% - MUY FLEXIBLE
                max_spread_pct=0.06,        # 6% - MUY FLEXIBLE
                stop_loss_pct=0.02,         # 2%
                take_profit_pct=0.04,       # 4%
                position_size_pct=0.1       # 10%
            ),
            'American': FlexibleSessionConfig(
                name='American',
                start_hour=14, # 2:00 PM UTC
                duration_minutes=60,
                min_price_move_pct=0.001,   # 0.1% - MUY FLEXIBLE
                min_volume_ratio=0.7,       # 70% - MUY FLEXIBLE
                max_spread_pct=0.07,        # 7% - MUY FLEXIBLE
                stop_loss_pct=0.025,        # 2.5%
                take_profit_pct=0.05,       # 5%
                position_size_pct=0.12      # 12%
            )
        }
        
        # Símbolos optimizados
        self.symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT',
            'SOLUSDT', 'DOTUSDT', 'LINKUSDT', 'LTCUSDT', 'BCHUSDT',
            'UNIUSDT', 'XLMUSDT', 'VETUSDT', 'FILUSDT', 'TRXUSDT'
        ]
        
        # Fee real de Binance
        self.trading_fee_rate = 0.001  # 0.1% por lado
        
        self.opportunities = []
        self.analysis_results = {}

    async def fetch_flexible_klines(self, session: aiohttp.ClientSession, symbol: str,
                                   start_time: datetime, end_time: datetime,
                                   interval: str = "1m") -> pd.DataFrame:
        """Obtener datos reales de velas de Binance"""
        try:
            start_ms = int(start_time.timestamp() * 1000)
            end_ms = int(end_time.timestamp() * 1000)
            
            url = f"{self.binance_base_url}/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': start_ms,
                'endTime': end_ms,
                'limit': 1000
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if not data:
                        return pd.DataFrame()
                    
                    # Convertir a DataFrame
                    df = pd.DataFrame(data, columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 'volume',
                        'close_time', 'quote_asset_volume', 'number_of_trades',
                        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
                    ])
                    
                    # Convertir tipos de datos
                    numeric_columns = ['open', 'high', 'low', 'close', 'volume']
                    for col in numeric_columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df['symbol'] = symbol
                    
                    logger.info(f"✅ Obtenidos {len(df)} registros para {symbol}")
                    return df[['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
                    
                else:
                    logger.error(f"Error API para {symbol}: {response.status}")
                    return pd.DataFrame()
                    
        except Exception as e:
            logger.error(f"Error obteniendo datos para {symbol}: {e}")
            return pd.DataFrame()

    def detect_flexible_opportunities(self, df: pd.DataFrame, session_config: FlexibleSessionConfig,
                                    analysis_date: datetime) -> List[FlexibleBreakoutOpportunity]:
        """Detectar oportunidades con parámetros flexibles"""
        opportunities = []
        
        try:
            if len(df) < 10:  # Necesitamos al menos 10 velas para análisis
                return opportunities
            
            # Buscar todas las horas de sesión en el día
            for hour_offset in range(0, 24):
                session_start = analysis_date.replace(
                    hour=session_config.start_hour, 
                    minute=0, 
                    second=0, 
                    microsecond=0
                ) + timedelta(hours=hour_offset)
                
                session_end = session_start + timedelta(minutes=session_config.duration_minutes)
                
                # Filtrar datos de la sesión
                session_data = df[
                    (df['timestamp'] >= session_start) & 
                    (df['timestamp'] < session_end)
                ].copy()
                
                if len(session_data) < 3:  # Necesitamos al menos 3 velas
                    continue
                
                # Analizar cada vela como potencial breakout
                for i in range(len(session_data)):
                    candle = session_data.iloc[i]
                    
                    # Calcular métricas de la vela
                    open_price = float(candle['open'])
                    high_price = float(candle['high'])
                    low_price = float(candle['low'])
                    close_price = float(candle['close'])
                    volume = float(candle['volume'])
                    
                    # Calcular movimiento de precio
                    price_move_pct = abs(close_price - open_price) / open_price
                    
                    # Calcular spread
                    spread_pct = (high_price - low_price) / open_price
                    
                    # Calcular ratio de volumen
                    volume_ratio = 1.0
                    if i > 0:
                        prev_volumes = session_data.iloc[:i]['volume']
                        if len(prev_volumes) > 0:
                            avg_prev_volume = prev_volumes.mean()
                            if avg_prev_volume > 0:
                                volume_ratio = volume / avg_prev_volume
                    
                    # Verificar condiciones FLEXIBLES
                    if (price_move_pct >= session_config.min_price_move_pct and
                        volume_ratio >= session_config.min_volume_ratio and
                        spread_pct <= session_config.max_spread_pct):
                        
                        # Determinar tipo de breakout
                        if close_price > open_price:
                            signal_type = 'bullish_breakout'
                            entry_price = high_price
                            stop_loss = entry_price * (1 - session_config.stop_loss_pct)
                            take_profit = entry_price * (1 + session_config.take_profit_pct)
                        else:
                            signal_type = 'bearish_breakout'
                            entry_price = low_price
                            stop_loss = entry_price * (1 + session_config.stop_loss_pct)
                            take_profit = entry_price * (1 - session_config.take_profit_pct)
                        
                        # Calcular tamaño de posición
                        position_size = self.current_capital * session_config.position_size_pct
                        
                        # Calcular confianza
                        confidence = min(1.0, (
                            (price_move_pct / session_config.min_price_move_pct) * 0.4 +
                            (volume_ratio / session_config.min_volume_ratio) * 0.4 +
                            (1 - spread_pct / session_config.max_spread_pct) * 0.2
                        ))
                        
                        opportunity = FlexibleBreakoutOpportunity(
                            timestamp=candle['timestamp'],
                            symbol=candle['symbol'],
                            session=session_config.name,
                            signal_type=signal_type,
                            entry_price=entry_price,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            position_size=position_size,
                            volume_ratio=volume_ratio,
                            price_move_pct=price_move_pct,
                            spread_pct=spread_pct,
                            confidence=confidence,
                            candle_data={
                                'open': open_price,
                                'high': high_price,
                                'low': low_price,
                                'close': close_price,
                                'volume': volume
                            }
                        )
                        
                        opportunities.append(opportunity)
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error detectando oportunidades flexibles: {e}")
            return opportunities

    async def analyze_flexible_period(self, start_date: datetime, end_date: datetime,
                                    period_name: str) -> Dict:
        """Analizar período con parámetros flexibles"""
        logger.info(f"🔍 Analizando período flexible: {period_name}")
        logger.info(f"📅 Desde: {start_date.strftime('%Y-%m-%d')}")
        logger.info(f"📅 Hasta: {end_date.strftime('%Y-%m-%d')}")
        
        all_opportunities = []
        
        async with aiohttp.ClientSession() as session:
            # Analizar cada día
            current_date = start_date
            while current_date <= end_date:
                logger.info(f"📈 Analizando día: {current_date.strftime('%Y-%m-%d')}")
                
                day_start = current_date
                day_end = current_date + timedelta(days=1)
                
                # Analizar cada símbolo
                for symbol in self.symbols:
                    # Obtener datos del día
                    df = await self.fetch_flexible_klines(
                        session, symbol, day_start, day_end
                    )
                    
                    if len(df) == 0:
                        continue
                    
                    # Analizar cada sesión
                    for session_name, session_config in self.session_configs.items():
                        opportunities = self.detect_flexible_opportunities(
                            df, session_config, current_date
                        )
                        all_opportunities.extend(opportunities)
                
                current_date += timedelta(days=1)
        
        # Generar estadísticas
        stats = self.calculate_flexible_stats(all_opportunities, period_name)
        
        return {
            'period_name': period_name,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_opportunities': len(all_opportunities),
            'opportunities_by_session': self.group_by_session(all_opportunities),
            'opportunities_by_symbol': self.group_by_symbol(all_opportunities),
            'statistics': stats,
            'sample_opportunities': [
                {
                    'timestamp': opp.timestamp.isoformat(),
                    'symbol': opp.symbol,
                    'session': opp.session,
                    'signal_type': opp.signal_type,
                    'price_move_pct': round(opp.price_move_pct * 100, 3),
                    'volume_ratio': round(opp.volume_ratio, 2),
                    'confidence': round(opp.confidence, 3),
                    'candle_data': opp.candle_data
                }
                for opp in all_opportunities[:20]  # Primeras 20 oportunidades
            ]
        }

    def calculate_flexible_stats(self, opportunities: List[FlexibleBreakoutOpportunity],
                               period_name: str) -> Dict:
        """Calcular estadísticas de las oportunidades detectadas"""
        if not opportunities:
            return {
                'total_opportunities': 0,
                'avg_confidence': 0,
                'avg_price_move': 0,
                'avg_volume_ratio': 0
            }
        
        return {
            'total_opportunities': len(opportunities),
            'avg_confidence': np.mean([opp.confidence for opp in opportunities]),
            'avg_price_move_pct': np.mean([opp.price_move_pct * 100 for opp in opportunities]),
            'avg_volume_ratio': np.mean([opp.volume_ratio for opp in opportunities]),
            'bullish_count': len([opp for opp in opportunities if opp.signal_type == 'bullish_breakout']),
            'bearish_count': len([opp for opp in opportunities if opp.signal_type == 'bearish_breakout']),
            'sessions_distribution': self.group_by_session(opportunities),
            'symbols_distribution': self.group_by_symbol(opportunities)
        }

    def group_by_session(self, opportunities: List[FlexibleBreakoutOpportunity]) -> Dict:
        """Agrupar oportunidades por sesión"""
        sessions = {}
        for opp in opportunities:
            if opp.session not in sessions:
                sessions[opp.session] = 0
            sessions[opp.session] += 1
        return sessions

    def group_by_symbol(self, opportunities: List[FlexibleBreakoutOpportunity]) -> Dict:
        """Agrupar oportunidades por símbolo"""
        symbols = {}
        for opp in opportunities:
            if opp.symbol not in symbols:
                symbols[opp.symbol] = 0
            symbols[opp.symbol] += 1
        return symbols

    def save_flexible_results(self, results: Dict, filename: str):
        """Guardar resultados del análisis flexible"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"💾 Resultados guardados en: {filename}")
        except Exception as e:
            logger.error(f"Error guardando resultados: {e}")

async def main():
    """Función principal del analizador flexible"""
    print("🚀 SICAR Flexible Real Data Analyzer")
    print("=" * 50)
    print("📊 ANÁLISIS FLEXIBLE CON DATOS REALES DE BINANCE")
    print("=" * 50)
    
    analyzer = FlexibleRealDataAnalyzer(initial_capital=1000.0)
    
    # Definir períodos de análisis
    end_date = datetime.now()
    periods = [
        {
            'name': 'Última Semana Flexible',
            'start': end_date - timedelta(days=7),
            'end': end_date
        },
        {
            'name': '2 Semanas Flexibles',
            'start': end_date - timedelta(days=14),
            'end': end_date
        },
        {
            'name': 'Último Mes Flexible',
            'start': end_date - timedelta(days=30),
            'end': end_date
        }
    ]
    
    all_results = []
    
    # Analizar cada período
    for period in periods:
        print(f"\n🔍 Ejecutando análisis flexible: {period['name']}")
        
        results = await analyzer.analyze_flexible_period(
            period['start'], period['end'], period['name']
        )
        
        all_results.append(results)
        
        # Guardar resultados individuales
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"flexible_analysis_{period['name'].lower().replace(' ', '_')}_{timestamp}.json"
        analyzer.save_flexible_results(results, filename)
        
        # Mostrar resumen
        print(f"✅ {period['name']} completado:")
        print(f"   📊 Oportunidades detectadas: {results['total_opportunities']}")
        if results['total_opportunities'] > 0:
            print(f"   📈 Confianza promedio: {results['statistics']['avg_confidence']:.3f}")
            print(f"   💹 Movimiento promedio: {results['statistics']['avg_price_move_pct']:.3f}%")
            print(f"   📊 Ratio volumen promedio: {results['statistics']['avg_volume_ratio']:.2f}")
    
    # Guardar resumen final
    final_summary = {
        'analysis_timestamp': datetime.now().isoformat(),
        'analyzer_config': 'Flexible Parameters',
        'periods_analyzed': len(periods),
        'total_opportunities_found': sum(r['total_opportunities'] for r in all_results),
        'period_results': all_results
    }
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_filename = f"flexible_analysis_summary_{timestamp}.json"
    analyzer.save_flexible_results(final_summary, summary_filename)
    
    print(f"\n🎯 RESUMEN FINAL DEL ANÁLISIS FLEXIBLE:")
    print(f"📊 Total de oportunidades detectadas: {final_summary['total_opportunities_found']}")
    print(f"💾 Resultados guardados en: {summary_filename}")

if __name__ == "__main__":
    asyncio.run(main())