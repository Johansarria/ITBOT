#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Descargador de Datos Reales NAS100
Obtiene datos históricos reales de NAS100 para backtesting
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from typing import Dict, Any, Optional
import warnings
warnings.filterwarnings('ignore')

class NAS100DataDownloader:
    """
    Descargador de datos históricos reales de NAS100
    """
    
    def __init__(self):
        # Símbolos disponibles para NAS100
        self.symbols = {
            'NQ=F': 'NASDAQ 100 Futures',
            'QQQ': 'Invesco QQQ Trust ETF',
            '^NDX': 'NASDAQ 100 Index',
            'TQQQ': '3x Leveraged NASDAQ ETF'
        }
        
        self.data_dir = "data/nas100_real"
        os.makedirs(self.data_dir, exist_ok=True)
        
    def download_data(self, symbol: str = 'QQQ', period: str = '2y', 
                     interval: str = '15m') -> pd.DataFrame:
        """
        Descarga datos históricos reales
        
        Args:
            symbol: Símbolo a descargar
            period: Período (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Intervalo (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        """
        print(f"📊 Descargando datos de {symbol} ({self.symbols.get(symbol, 'Unknown')})")
        print(f"   Período: {period}, Intervalo: {interval}")
        
        try:
            # Descargar datos
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                print(f"❌ No se pudieron obtener datos para {symbol}")
                return pd.DataFrame()
            
            # Limpiar y preparar datos
            data = data.dropna()
            data.columns = [col.lower() for col in data.columns]
            
            # Renombrar columnas si es necesario
            column_mapping = {
                'adj close': 'adj_close',
                'stock splits': 'stock_splits'
            }
            data = data.rename(columns=column_mapping)
            
            # Asegurar que tenemos las columnas necesarias
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in data.columns:
                    print(f"⚠️ Columna faltante: {col}")
            
            print(f"✅ Descargados {len(data)} registros")
            print(f"   Rango: {data.index[0]} a {data.index[-1]}")
            
            return data
            
        except Exception as e:
            print(f"❌ Error descargando {symbol}: {e}")
            return pd.DataFrame()
    
    def save_data(self, data: pd.DataFrame, symbol: str, interval: str) -> str:
        """
        Guarda datos en archivo
        """
        if data.empty:
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{symbol}_{interval}_{timestamp}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        data.to_csv(filepath)
        print(f"💾 Datos guardados en: {filepath}")
        
        return filepath
    
    def get_multiple_timeframes(self, symbol: str = 'QQQ') -> Dict[str, pd.DataFrame]:
        """
        Descarga múltiples timeframes para análisis completo
        """
        timeframes = {
            '15m': '2y',   # 15 minutos, 2 años
            '1h': '5y',    # 1 hora, 5 años
            '1d': 'max'    # Diario, máximo disponible
        }
        
        results = {}
        
        for interval, period in timeframes.items():
            print(f"\n📈 Descargando timeframe {interval}...")
            data = self.download_data(symbol, period, interval)
            
            if not data.empty:
                filepath = self.save_data(data, symbol, interval)
                results[interval] = {
                    'data': data,
                    'filepath': filepath,
                    'records': len(data)
                }
            
        return results
    
    def validate_data_quality(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Valida la calidad de los datos descargados
        """
        if data.empty:
            return {'valid': False, 'reason': 'No data'}
        
        issues = []
        
        # Verificar valores faltantes
        missing_data = data.isnull().sum()
        if missing_data.any():
            issues.append(f"Datos faltantes: {missing_data.to_dict()}")
        
        # Verificar precios negativos
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in data.columns and (data[col] <= 0).any():
                issues.append(f"Precios negativos/cero en {col}")
        
        # Verificar consistencia OHLC
        if all(col in data.columns for col in price_columns):
            # High debe ser >= Open, Close
            if ((data['high'] < data['open']) | (data['high'] < data['close'])).any():
                issues.append("High menor que Open/Close")
            
            # Low debe ser <= Open, Close
            if ((data['low'] > data['open']) | (data['low'] > data['close'])).any():
                issues.append("Low mayor que Open/Close")
        
        # Verificar gaps extremos (>10%)
        if 'close' in data.columns:
            price_changes = data['close'].pct_change().abs()
            extreme_gaps = (price_changes > 0.1).sum()
            if extreme_gaps > 0:
                issues.append(f"Gaps extremos (>10%): {extreme_gaps}")
        
        # Verificar volumen
        if 'volume' in data.columns:
            zero_volume = (data['volume'] == 0).sum()
            if zero_volume > len(data) * 0.05:  # Más del 5%
                issues.append(f"Demasiados períodos sin volumen: {zero_volume}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'total_records': len(data),
            'date_range': f"{data.index[0]} to {data.index[-1]}",
            'columns': list(data.columns)
        }
    
    def create_summary_report(self, results: Dict[str, Any]) -> str:
        """
        Crea reporte resumen de los datos descargados
        """
        report = []
        report.append("📊 REPORTE DE DATOS NAS100 DESCARGADOS")
        report.append("=" * 50)
        report.append(f"Fecha de descarga: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        for timeframe, info in results.items():
            report.append(f"⏰ TIMEFRAME: {timeframe}")
            report.append("-" * 30)
            report.append(f"Registros: {info['records']:,}")
            report.append(f"Archivo: {info['filepath']}")
            
            # Validar calidad
            validation = self.validate_data_quality(info['data'])
            report.append(f"Calidad: {'✅ Válido' if validation['valid'] else '❌ Problemas'}")
            
            if not validation['valid']:
                for issue in validation['issues']:
                    report.append(f"  - {issue}")
            
            report.append(f"Rango: {validation['date_range']}")
            report.append("")
        
        return "\n".join(report)


def download_nas100_data():
    """
    Función principal para descargar datos de NAS100
    """
    print("🚀 Iniciando descarga de datos reales NAS100")
    print("=" * 50)
    
    downloader = NAS100DataDownloader()
    
    # Probar diferentes símbolos
    symbols_to_try = ['QQQ', 'NQ=F', '^NDX']
    
    for symbol in symbols_to_try:
        print(f"\n🔍 Probando símbolo: {symbol}")
        
        # Descargar datos de prueba primero
        test_data = downloader.download_data(symbol, '5d', '1h')
        
        if not test_data.empty:
            print(f"✅ {symbol} funciona, descargando datos completos...")
            
            # Descargar múltiples timeframes
            results = downloader.get_multiple_timeframes(symbol)
            
            if results:
                # Crear reporte
                report = downloader.create_summary_report(results)
                print("\n" + report)
                
                # Guardar reporte
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_file = f"data/nas100_real/download_report_{timestamp}.txt"
                
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(report)
                
                print(f"\n📄 Reporte guardado en: {report_file}")
                
                # Retornar el mejor dataset para backtesting
                best_data = None
                best_timeframe = None
                
                # Preferir 15m si tiene suficientes datos
                if '15m' in results and results['15m']['records'] > 1000:
                    best_data = results['15m']['data']
                    best_timeframe = '15m'
                elif '1h' in results:
                    best_data = results['1h']['data']
                    best_timeframe = '1h'
                elif '1d' in results:
                    best_data = results['1d']['data']
                    best_timeframe = '1d'
                
                if best_data is not None:
                    print(f"\n🎯 Mejor dataset para backtesting: {best_timeframe}")
                    print(f"   Registros: {len(best_data):,}")
                    print(f"   Rango: {best_data.index[0]} a {best_data.index[-1]}")
                    
                    return best_data, best_timeframe, symbol
                
                break
        else:
            print(f"❌ {symbol} no funcionó")
    
    print("\n❌ No se pudieron descargar datos de ningún símbolo")
    return None, None, None


if __name__ == "__main__":
    try:
        data, timeframe, symbol = download_nas100_data()
        
        if data is not None:
            print(f"\n🎉 Descarga exitosa!")
            print(f"Símbolo: {symbol}")
            print(f"Timeframe: {timeframe}")
            print(f"Registros: {len(data):,}")
            print("\nPrimeros 5 registros:")
            print(data.head())
            print("\nÚltimos 5 registros:")
            print(data.tail())
        else:
            print("\n❌ No se pudieron descargar datos")
            print("\n💡 Soluciones posibles:")
            print("1. Verificar conexión a internet")
            print("2. Instalar yfinance: pip install yfinance")
            print("3. Probar con otros símbolos")
            
    except ImportError:
        print("❌ Error: yfinance no está instalado")
        print("Ejecuta: pip install yfinance")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")