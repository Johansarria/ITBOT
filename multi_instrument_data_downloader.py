#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Descargador de Datos Multi-Instrumento
Obtiene datos históricos para Forex, Índices y Metales
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from typing import Dict, Any, Optional, List
import warnings
warnings.filterwarnings('ignore')

class MultiInstrumentDataDownloader:
    """
    Descargador de datos para múltiples instrumentos financieros
    """
    
    def __init__(self):
        # Configuración de instrumentos
        self.instruments = {
            # FOREX
            'EURUSD': {
                'symbol': 'EURUSD=X',
                'name': 'Euro/US Dollar',
                'type': 'forex',
                'pip_value': 0.0001,
                'typical_spread': 0.00015
            },
            'AUDCAD': {
                'symbol': 'AUDCAD=X',
                'name': 'Australian Dollar/Canadian Dollar',
                'type': 'forex',
                'pip_value': 0.0001,
                'typical_spread': 0.0002
            },
            
            # ÍNDICES
            'NAS100': {
                'symbol': 'QQQ',  # ETF que replica NASDAQ 100
                'name': 'NASDAQ 100 Index',
                'type': 'index',
                'pip_value': 0.01,
                'typical_spread': 0.02
            },
            'NAS100_FUTURES': {
                'symbol': 'NQ=F',  # Futuros NASDAQ
                'name': 'NASDAQ 100 Futures',
                'type': 'index',
                'pip_value': 0.25,
                'typical_spread': 0.5
            },
            
            # METALES
            'XAUUSD': {
                'symbol': 'GC=F',  # Gold Futures
                'name': 'Gold/US Dollar',
                'type': 'metal',
                'pip_value': 0.1,
                'typical_spread': 0.3
            },
            'GOLD_ETF': {
                'symbol': 'GLD',  # Gold ETF
                'name': 'SPDR Gold Trust',
                'type': 'metal',
                'pip_value': 0.01,
                'typical_spread': 0.02
            }
        }
        
        self.data_dir = "data/multi_instrument"
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Crear subdirectorios por tipo
        for instrument_type in ['forex', 'index', 'metal']:
            os.makedirs(f"{self.data_dir}/{instrument_type}", exist_ok=True)
    
    def download_instrument_data(self, instrument_key: str, period: str = '2y', 
                               interval: str = '15m') -> pd.DataFrame:
        """
        Descarga datos para un instrumento específico
        """
        if instrument_key not in self.instruments:
            print(f"❌ Instrumento {instrument_key} no encontrado")
            return pd.DataFrame()
        
        instrument = self.instruments[instrument_key]
        symbol = instrument['symbol']
        
        print(f"📊 Descargando {instrument_key} ({instrument['name']})")
        print(f"   Símbolo: {symbol}, Tipo: {instrument['type']}")
        print(f"   Período: {period}, Intervalo: {interval}")
        
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                print(f"❌ No se pudieron obtener datos para {instrument_key}")
                return pd.DataFrame()
            
            # Limpiar datos
            data = data.dropna()
            data.columns = [col.lower().replace(' ', '_') for col in data.columns]
            
            # Añadir información del instrumento
            data['instrument'] = instrument_key
            data['instrument_type'] = instrument['type']
            data['pip_value'] = instrument['pip_value']
            data['spread'] = instrument['typical_spread']
            
            # Calcular métricas adicionales
            data['true_range'] = np.maximum(
                data['high'] - data['low'],
                np.maximum(
                    abs(data['high'] - data['close'].shift()),
                    abs(data['low'] - data['close'].shift())
                )
            )
            data['atr_14'] = data['true_range'].rolling(14).mean()
            data['volatility'] = data['close'].rolling(20).std() / data['close'].rolling(20).mean()
            
            print(f"✅ Descargados {len(data)} registros para {instrument_key}")
            print(f"   Rango: {data.index[0]} a {data.index[-1]}")
            
            return data
            
        except Exception as e:
            print(f"❌ Error descargando {instrument_key}: {e}")
            return pd.DataFrame()
    
    def download_all_instruments(self, period: str = '2y', interval: str = '15m') -> Dict[str, pd.DataFrame]:
        """
        Descarga datos para todos los instrumentos
        """
        print("🚀 Descargando datos para todos los instrumentos")
        print("=" * 60)
        
        results = {}
        
        for instrument_key in self.instruments.keys():
            print(f"\n📈 Procesando {instrument_key}...")
            
            data = self.download_instrument_data(instrument_key, period, interval)
            
            if not data.empty:
                # Guardar datos
                instrument_type = self.instruments[instrument_key]['type']
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{instrument_key}_{interval}_{timestamp}.csv"
                filepath = os.path.join(self.data_dir, instrument_type, filename)
                
                data.to_csv(filepath)
                print(f"💾 Guardado en: {filepath}")
                
                results[instrument_key] = {
                    'data': data,
                    'filepath': filepath,
                    'records': len(data),
                    'instrument_info': self.instruments[instrument_key]
                }
            else:
                print(f"⚠️ No se pudieron obtener datos para {instrument_key}")
        
        return results
    
    def analyze_instrument_characteristics(self, data: pd.DataFrame, instrument_key: str) -> Dict[str, Any]:
        """
        Analiza características específicas del instrumento
        """
        if data.empty:
            return {}
        
        instrument = self.instruments[instrument_key]
        
        # Calcular estadísticas básicas
        price_changes = data['close'].pct_change().dropna()
        
        analysis = {
            'instrument': instrument_key,
            'type': instrument['type'],
            'total_records': len(data),
            'date_range': f"{data.index[0]} to {data.index[-1]}",
            
            # Volatilidad
            'avg_volatility': data['volatility'].mean(),
            'max_volatility': data['volatility'].max(),
            'min_volatility': data['volatility'].min(),
            
            # Movimientos de precio
            'avg_price_change': price_changes.mean(),
            'std_price_change': price_changes.std(),
            'max_daily_move_up': price_changes.max(),
            'max_daily_move_down': price_changes.min(),
            
            # ATR
            'avg_atr': data['atr_14'].mean(),
            'atr_as_pct_of_price': (data['atr_14'] / data['close']).mean(),
            
            # Volumen (si está disponible)
            'has_volume': 'volume' in data.columns,
            'avg_volume': data['volume'].mean() if 'volume' in data.columns else None,
            
            # Gaps y continuidad
            'gaps_count': self._count_gaps(data),
            'trading_hours_coverage': self._analyze_trading_hours(data)
        }
        
        # Análisis específico por tipo de instrumento
        if instrument['type'] == 'forex':
            analysis.update(self._analyze_forex_specific(data, instrument))
        elif instrument['type'] == 'index':
            analysis.update(self._analyze_index_specific(data, instrument))
        elif instrument['type'] == 'metal':
            analysis.update(self._analyze_metal_specific(data, instrument))
        
        return analysis
    
    def _analyze_forex_specific(self, data: pd.DataFrame, instrument: Dict) -> Dict[str, Any]:
        """Análisis específico para Forex"""
        price_changes = data['close'].pct_change().dropna()
        
        return {
            'pip_movements': {
                'avg_pips_per_period': (price_changes.abs() / instrument['pip_value']).mean(),
                'max_pips_move': (price_changes.abs().max() / instrument['pip_value']),
                'pips_std': (price_changes.std() / instrument['pip_value'])
            },
            'spread_impact': {
                'spread_as_pct': instrument['typical_spread'] / data['close'].mean(),
                'spread_vs_avg_move': instrument['typical_spread'] / price_changes.abs().mean()
            }
        }
    
    def _analyze_index_specific(self, data: pd.DataFrame, instrument: Dict) -> Dict[str, Any]:
        """Análisis específico para Índices"""
        return {
            'index_characteristics': {
                'trend_strength': self._calculate_trend_strength(data),
                'momentum_periods': self._identify_momentum_periods(data),
                'support_resistance_levels': self._find_key_levels(data)
            }
        }
    
    def _analyze_metal_specific(self, data: pd.DataFrame, instrument: Dict) -> Dict[str, Any]:
        """Análisis específico para Metales"""
        return {
            'metal_characteristics': {
                'volatility_clusters': self._identify_volatility_clusters(data),
                'safe_haven_periods': self._identify_safe_haven_periods(data),
                'correlation_with_dollar': self._estimate_dollar_correlation(data)
            }
        }
    
    def _count_gaps(self, data: pd.DataFrame) -> int:
        """Cuenta gaps en los datos"""
        if len(data) < 2:
            return 0
        
        gaps = 0
        for i in range(1, len(data)):
            prev_close = data.iloc[i-1]['close']
            current_open = data.iloc[i]['open']
            gap_pct = abs(current_open - prev_close) / prev_close
            
            if gap_pct > 0.005:  # Gap mayor al 0.5%
                gaps += 1
        
        return gaps
    
    def _analyze_trading_hours(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analiza cobertura de horas de trading"""
        if data.empty:
            return {}
        
        hours = data.index.hour
        hour_counts = hours.value_counts().sort_index()
        
        return {
            'hours_covered': len(hour_counts),
            'most_active_hour': hour_counts.idxmax(),
            'least_active_hour': hour_counts.idxmin(),
            'weekend_data': any(data.index.weekday >= 5)
        }
    
    def _calculate_trend_strength(self, data: pd.DataFrame) -> float:
        """Calcula fuerza de tendencia"""
        if len(data) < 50:
            return 0.0
        
        ema_20 = data['close'].ewm(span=20).mean()
        ema_50 = data['close'].ewm(span=50).mean()
        
        trend_alignment = (ema_20 > ema_50).sum() / len(data)
        return trend_alignment
    
    def _identify_momentum_periods(self, data: pd.DataFrame) -> int:
        """Identifica períodos de momentum fuerte"""
        if len(data) < 20:
            return 0
        
        momentum = data['close'].pct_change(10)
        strong_momentum = (momentum.abs() > momentum.std() * 2).sum()
        return strong_momentum
    
    def _find_key_levels(self, data: pd.DataFrame) -> Dict[str, float]:
        """Encuentra niveles clave de soporte y resistencia"""
        if data.empty:
            return {}
        
        return {
            'support': data['low'].rolling(50).min().iloc[-1],
            'resistance': data['high'].rolling(50).max().iloc[-1],
            'current_level': data['close'].iloc[-1]
        }
    
    def _identify_volatility_clusters(self, data: pd.DataFrame) -> int:
        """Identifica clusters de volatilidad"""
        if len(data) < 20:
            return 0
        
        vol_threshold = data['volatility'].quantile(0.8)
        clusters = (data['volatility'] > vol_threshold).sum()
        return clusters
    
    def _identify_safe_haven_periods(self, data: pd.DataFrame) -> int:
        """Identifica períodos de refugio seguro"""
        # Simplificado: períodos de alta volatilidad seguidos de estabilidad
        if len(data) < 30:
            return 0
        
        vol_spikes = data['volatility'] > data['volatility'].quantile(0.9)
        safe_haven_periods = 0
        
        for i in range(10, len(data)-10):
            if vol_spikes.iloc[i-5:i].any() and not vol_spikes.iloc[i:i+10].any():
                safe_haven_periods += 1
        
        return safe_haven_periods
    
    def _estimate_dollar_correlation(self, data: pd.DataFrame) -> float:
        """Estima correlación con el dólar (simplificado)"""
        # En una implementación real, esto requeriría datos del DXY
        # Por ahora, usamos una aproximación basada en volatilidad
        if len(data) < 50:
            return 0.0
        
        price_changes = data['close'].pct_change().dropna()
        # Correlación inversa aproximada basada en patrones de volatilidad
        return -0.3 + (data['volatility'].mean() * 10)  # Aproximación
    
    def create_comprehensive_report(self, results: Dict[str, Any]) -> str:
        """
        Crea reporte comprehensivo de todos los instrumentos
        """
        report = []
        report.append("📊 REPORTE MULTI-INSTRUMENTO PARA TRADING 15%+")
        report.append("=" * 60)
        report.append(f"Fecha de análisis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Resumen por categoría
        categories = {'forex': [], 'index': [], 'metal': []}
        
        for instrument_key, info in results.items():
            if 'data' in info:
                analysis = self.analyze_instrument_characteristics(info['data'], instrument_key)
                categories[analysis['type']].append((instrument_key, analysis))
        
        # Reporte por categoría
        for category, instruments in categories.items():
            if not instruments:
                continue
                
            report.append(f"\n🏷️ {category.upper()}")
            report.append("-" * 30)
            
            for instrument_key, analysis in instruments:
                report.append(f"\n📈 {instrument_key} ({analysis['instrument']})")
                report.append(f"   Registros: {analysis['total_records']:,}")
                report.append(f"   Rango: {analysis['date_range']}")
                report.append(f"   Volatilidad promedio: {analysis['avg_volatility']:.4f}")
                report.append(f"   ATR como % del precio: {analysis['atr_as_pct_of_price']:.4f}")
                report.append(f"   Movimiento máximo: +{analysis['max_daily_move_up']:.4f} / {analysis['max_daily_move_down']:.4f}")
                report.append(f"   Gaps detectados: {analysis['gaps_count']}")
                
                # Información específica por tipo
                if category == 'forex' and 'pip_movements' in analysis:
                    pip_info = analysis['pip_movements']
                    report.append(f"   Pips promedio por período: {pip_info['avg_pips_per_period']:.1f}")
                    report.append(f"   Movimiento máximo en pips: {pip_info['max_pips_move']:.1f}")
                
                elif category == 'index' and 'index_characteristics' in analysis:
                    idx_info = analysis['index_characteristics']
                    report.append(f"   Fuerza de tendencia: {idx_info['trend_strength']:.2f}")
                    report.append(f"   Períodos de momentum: {idx_info['momentum_periods']}")
                
                elif category == 'metal' and 'metal_characteristics' in analysis:
                    metal_info = analysis['metal_characteristics']
                    report.append(f"   Clusters de volatilidad: {metal_info['volatility_clusters']}")
                    report.append(f"   Períodos refugio seguro: {metal_info['safe_haven_periods']}")
        
        # Recomendaciones para trading
        report.append("\n\n🎯 RECOMENDACIONES PARA 15%+ MENSUAL")
        report.append("=" * 50)
        
        # Ranking por potencial de rentabilidad
        volatility_ranking = []
        for instrument_key, info in results.items():
            if 'data' in info:
                analysis = self.analyze_instrument_characteristics(info['data'], instrument_key)
                volatility_score = analysis['avg_volatility'] * analysis['atr_as_pct_of_price']
                volatility_ranking.append((instrument_key, volatility_score, analysis))
        
        volatility_ranking.sort(key=lambda x: x[1], reverse=True)
        
        report.append("\n🏆 RANKING POR POTENCIAL DE RENTABILIDAD:")
        for i, (instrument, score, analysis) in enumerate(volatility_ranking[:5], 1):
            report.append(f"{i}. {instrument} - Score: {score:.6f}")
            report.append(f"   Volatilidad: {analysis['avg_volatility']:.4f}")
            report.append(f"   ATR%: {analysis['atr_as_pct_of_price']:.4f}")
        
        report.append("\n💡 ESTRATEGIAS RECOMENDADAS POR INSTRUMENTO:")
        report.append("-" * 45)
        
        for instrument_key, info in results.items():
            if 'data' in info:
                analysis = self.analyze_instrument_characteristics(info['data'], instrument_key)
                strategy_rec = self._get_strategy_recommendation(analysis)
                report.append(f"\n{instrument_key}: {strategy_rec}")
        
        return "\n".join(report)
    
    def _get_strategy_recommendation(self, analysis: Dict[str, Any]) -> str:
        """Genera recomendación de estrategia basada en características"""
        vol = analysis['avg_volatility']
        atr_pct = analysis['atr_as_pct_of_price']
        
        if vol > 0.02 and atr_pct > 0.015:
            return "Scalping agresivo - Alta volatilidad, stops ajustados"
        elif vol > 0.015:
            return "Swing trading - Volatilidad media, targets amplios"
        elif analysis['type'] == 'forex':
            return "Carry trade + breakouts - Forex estable"
        elif analysis['type'] == 'index':
            return "Trend following - Seguimiento de tendencias"
        else:
            return "Position trading - Movimientos a largo plazo"


def download_and_analyze_all_instruments():
    """
    Función principal para descargar y analizar todos los instrumentos
    """
    print("🌍 Iniciando descarga multi-instrumento para 15%+ mensual")
    print("=" * 70)
    
    downloader = MultiInstrumentDataDownloader()
    
    # Descargar datos para todos los instrumentos
    results = downloader.download_all_instruments(period='2y', interval='15m')
    
    if not results:
        print("❌ No se pudieron descargar datos de ningún instrumento")
        return None
    
    print(f"\n✅ Descarga completada para {len(results)} instrumentos")
    
    # Crear reporte comprehensivo
    report = downloader.create_comprehensive_report(results)
    
    # Guardar reporte
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"data/multi_instrument/comprehensive_analysis_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📄 Reporte completo guardado en: {report_file}")
    print("\n" + "=" * 50)
    print(report)
    
    return results, report_file


if __name__ == "__main__":
    try:
        results, report_file = download_and_analyze_all_instruments()
        
        if results:
            print(f"\n🎉 Análisis completado exitosamente!")
            print(f"Instrumentos analizados: {len(results)}")
            print(f"Reporte guardado en: {report_file}")
            
            # Mostrar resumen rápido
            print("\n📊 RESUMEN RÁPIDO:")
            for instrument_key, info in results.items():
                if 'data' in info:
                    data = info['data']
                    print(f"{instrument_key}: {len(data):,} registros, Vol: {data['volatility'].mean():.4f}")
        else:
            print("\n❌ No se pudieron analizar instrumentos")
            print("\n💡 Soluciones:")
            print("1. Verificar conexión a internet")
            print("2. Instalar yfinance: pip install yfinance")
            print("3. Verificar símbolos de instrumentos")
            
    except ImportError:
        print("❌ Error: yfinance no está instalado")
        print("Ejecuta: pip install yfinance")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")