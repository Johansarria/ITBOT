#!/usr/bin/env python3
"""
Script de Diagnóstico de APIs de Datos
Prueba conectividad con múltiples fuentes de datos para identificar problemas
"""

import yfinance as yf
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging
import warnings
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_connectivity_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class APIConnectivityTester:
    def __init__(self):
        """Inicializar tester de conectividad"""
        self.results = {}
        
        # Símbolos para probar
        self.crypto_symbols = ['BTC-USD', 'ETH-USD', 'ADA-USD', 'SOL-USD', 'XRP-USD']
        self.stock_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
        self.forex_symbols = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X']
        
        logger.info("Tester de conectividad inicializado")

    def test_yfinance_basic(self):
        """Probar funcionalidad básica de yfinance"""
        logger.info("=== Probando yfinance básico ===")
        
        results = {
            'success': False,
            'errors': [],
            'working_symbols': [],
            'failed_symbols': [],
            'data_samples': {}
        }
        
        try:
            # Probar con un símbolo simple primero
            logger.info("Probando con AAPL...")
            ticker = yf.Ticker("AAPL")
            info = ticker.info
            
            if info and 'symbol' in info:
                logger.info(f"✅ Info básica obtenida: {info.get('symbol', 'N/A')}")
                results['working_symbols'].append('AAPL')
            else:
                logger.warning("❌ No se pudo obtener info básica")
                results['failed_symbols'].append('AAPL')
            
            # Probar datos históricos
            logger.info("Probando datos históricos...")
            hist = ticker.history(period="5d")
            
            if not hist.empty:
                logger.info(f"✅ Datos históricos obtenidos: {len(hist)} registros")
                results['data_samples']['AAPL_hist'] = {
                    'rows': len(hist),
                    'columns': list(hist.columns),
                    'date_range': f"{hist.index[0]} to {hist.index[-1]}",
                    'sample_close': float(hist['Close'].iloc[-1])
                }
                results['success'] = True
            else:
                logger.warning("❌ No se pudieron obtener datos históricos")
                results['errors'].append("No historical data for AAPL")
            
        except Exception as e:
            logger.error(f"Error en test básico yfinance: {e}")
            results['errors'].append(str(e))
        
        self.results['yfinance_basic'] = results
        return results

    def test_yfinance_crypto(self):
        """Probar yfinance con criptomonedas"""
        logger.info("=== Probando yfinance con criptomonedas ===")
        
        results = {
            'success': False,
            'working_symbols': [],
            'failed_symbols': [],
            'errors': [],
            'data_samples': {}
        }
        
        for symbol in self.crypto_symbols:
            try:
                logger.info(f"Probando {symbol}...")
                ticker = yf.Ticker(symbol)
                
                # Probar diferentes períodos
                for period in ['1d', '5d', '1mo']:
                    try:
                        hist = ticker.history(period=period)
                        if not hist.empty:
                            logger.info(f"✅ {symbol} - {period}: {len(hist)} registros")
                            results['working_symbols'].append(f"{symbol}_{period}")
                            results['data_samples'][f"{symbol}_{period}"] = {
                                'rows': len(hist),
                                'last_close': float(hist['Close'].iloc[-1]),
                                'date_range': f"{hist.index[0]} to {hist.index[-1]}"
                            }
                            results['success'] = True
                            break
                        else:
                            logger.warning(f"❌ {symbol} - {period}: Sin datos")
                    except Exception as e:
                        logger.warning(f"❌ {symbol} - {period}: {e}")
                        continue
                
                if not any(symbol in s for s in results['working_symbols']):
                    results['failed_symbols'].append(symbol)
                
                # Pausa para evitar rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error con {symbol}: {e}")
                results['failed_symbols'].append(symbol)
                results['errors'].append(f"{symbol}: {str(e)}")
        
        self.results['yfinance_crypto'] = results
        return results

    def test_alternative_crypto_apis(self):
        """Probar APIs alternativas para criptomonedas"""
        logger.info("=== Probando APIs alternativas ===")
        
        results = {
            'coingecko': {'success': False, 'error': None, 'data': None},
            'coinbase': {'success': False, 'error': None, 'data': None},
            'binance_public': {'success': False, 'error': None, 'data': None}
        }
        
        # Test CoinGecko
        try:
            logger.info("Probando CoinGecko API...")
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': 'bitcoin,ethereum,cardano,solana,ripple',
                'vs_currencies': 'usd',
                'include_24hr_change': 'true'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ CoinGecko: {len(data)} precios obtenidos")
                results['coingecko']['success'] = True
                results['coingecko']['data'] = data
            else:
                logger.warning(f"❌ CoinGecko: Status {response.status_code}")
                results['coingecko']['error'] = f"HTTP {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error CoinGecko: {e}")
            results['coingecko']['error'] = str(e)
        
        # Test Coinbase
        try:
            logger.info("Probando Coinbase API...")
            url = "https://api.coinbase.com/v2/exchange-rates"
            params = {'currency': 'BTC'}
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Coinbase: Datos obtenidos")
                results['coinbase']['success'] = True
                results['coinbase']['data'] = data.get('data', {})
            else:
                logger.warning(f"❌ Coinbase: Status {response.status_code}")
                results['coinbase']['error'] = f"HTTP {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error Coinbase: {e}")
            results['coinbase']['error'] = str(e)
        
        # Test Binance Public API
        try:
            logger.info("Probando Binance Public API...")
            url = "https://api.binance.com/api/v3/ticker/24hr"
            params = {'symbol': 'BTCUSDT'}
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Binance: Datos obtenidos")
                results['binance_public']['success'] = True
                results['binance_public']['data'] = data
            else:
                logger.warning(f"❌ Binance: Status {response.status_code}")
                results['binance_public']['error'] = f"HTTP {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error Binance: {e}")
            results['binance_public']['error'] = str(e)
        
        self.results['alternative_apis'] = results
        return results

    def test_network_connectivity(self):
        """Probar conectividad de red básica"""
        logger.info("=== Probando conectividad de red ===")
        
        results = {
            'dns_resolution': False,
            'internet_access': False,
            'yahoo_finance_reachable': False,
            'errors': []
        }
        
        try:
            # Test DNS resolution
            import socket
            socket.gethostbyname('google.com')
            results['dns_resolution'] = True
            logger.info("✅ Resolución DNS funcionando")
        except Exception as e:
            logger.error(f"❌ Error DNS: {e}")
            results['errors'].append(f"DNS: {str(e)}")
        
        try:
            # Test internet access
            response = requests.get('https://httpbin.org/ip', timeout=5)
            if response.status_code == 200:
                results['internet_access'] = True
                logger.info("✅ Acceso a internet funcionando")
            else:
                logger.warning(f"❌ Internet: Status {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Error internet: {e}")
            results['errors'].append(f"Internet: {str(e)}")
        
        try:
            # Test Yahoo Finance specifically
            response = requests.get('https://finance.yahoo.com', timeout=10)
            if response.status_code == 200:
                results['yahoo_finance_reachable'] = True
                logger.info("✅ Yahoo Finance accesible")
            else:
                logger.warning(f"❌ Yahoo Finance: Status {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Error Yahoo Finance: {e}")
            results['errors'].append(f"Yahoo Finance: {str(e)}")
        
        self.results['network'] = results
        return results

    def test_data_quality(self):
        """Probar calidad de datos obtenidos"""
        logger.info("=== Probando calidad de datos ===")
        
        results = {
            'completeness': {},
            'consistency': {},
            'timeliness': {},
            'errors': []
        }
        
        try:
            # Probar con múltiples símbolos
            test_symbols = ['AAPL', 'BTC-USD', 'ETH-USD']
            
            for symbol in test_symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="1mo", interval="1d")
                    
                    if not hist.empty:
                        # Completeness
                        missing_data = hist.isnull().sum().sum()
                        total_data = hist.size
                        completeness = 1 - (missing_data / total_data)
                        
                        # Consistency
                        price_consistency = (hist['High'] >= hist['Low']).all()
                        volume_consistency = (hist['Volume'] >= 0).all()
                        
                        # Timeliness
                        last_date = hist.index[-1].date()
                        today = datetime.now().date()
                        days_old = (today - last_date).days
                        
                        results['completeness'][symbol] = completeness
                        results['consistency'][symbol] = {
                            'price_logic': price_consistency,
                            'volume_positive': volume_consistency
                        }
                        results['timeliness'][symbol] = days_old
                        
                        logger.info(f"✅ {symbol}: Completeness {completeness:.2%}, "
                                  f"Consistent: {price_consistency and volume_consistency}, "
                                  f"Days old: {days_old}")
                    else:
                        logger.warning(f"❌ {symbol}: Sin datos para análisis de calidad")
                        
                except Exception as e:
                    logger.error(f"Error analizando {symbol}: {e}")
                    results['errors'].append(f"{symbol}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error en test de calidad: {e}")
            results['errors'].append(str(e))
        
        self.results['data_quality'] = results
        return results

    def run_comprehensive_test(self):
        """Ejecutar todas las pruebas"""
        logger.info("🚀 Iniciando pruebas comprehensivas de APIs...")
        
        # Ejecutar todas las pruebas
        self.test_network_connectivity()
        self.test_yfinance_basic()
        self.test_yfinance_crypto()
        self.test_alternative_crypto_apis()
        self.test_data_quality()
        
        return self.results

    def generate_diagnostic_report(self):
        """Generar reporte de diagnóstico"""
        logger.info("📊 Generando reporte de diagnóstico...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'network_ok': self.results.get('network', {}).get('internet_access', False),
                'yfinance_basic_ok': self.results.get('yfinance_basic', {}).get('success', False),
                'yfinance_crypto_ok': self.results.get('yfinance_crypto', {}).get('success', False),
                'alternative_apis_available': any(
                    api.get('success', False) 
                    for api in self.results.get('alternative_apis', {}).values()
                ),
                'data_quality_acceptable': len(self.results.get('data_quality', {}).get('completeness', {})) > 0
            },
            'detailed_results': self.results,
            'recommendations': []
        }
        
        # Generar recomendaciones
        if not report['summary']['network_ok']:
            report['recommendations'].append("Verificar conexión a internet y configuración de proxy/firewall")
        
        if not report['summary']['yfinance_basic_ok']:
            report['recommendations'].append("Actualizar yfinance: pip install --upgrade yfinance")
        
        if not report['summary']['yfinance_crypto_ok']:
            report['recommendations'].append("Usar APIs alternativas para criptomonedas (CoinGecko, Binance)")
        
        if report['summary']['alternative_apis_available']:
            report['recommendations'].append("Implementar sistema de fallback con APIs alternativas")
        
        return report

def main():
    """Función principal"""
    print("=== DIAGNÓSTICO DE CONECTIVIDAD DE APIS ===")
    print("Probando múltiples fuentes de datos...\n")
    
    tester = APIConnectivityTester()
    
    # Ejecutar pruebas
    results = tester.run_comprehensive_test()
    
    # Generar reporte
    report = tester.generate_diagnostic_report()
    
    # Mostrar resumen
    print("\n=== RESUMEN DE RESULTADOS ===")
    summary = report['summary']
    
    print(f"🌐 Conectividad de red: {'✅' if summary['network_ok'] else '❌'}")
    print(f"📈 yfinance básico: {'✅' if summary['yfinance_basic_ok'] else '❌'}")
    print(f"₿ yfinance crypto: {'✅' if summary['yfinance_crypto_ok'] else '❌'}")
    print(f"🔄 APIs alternativas: {'✅' if summary['alternative_apis_available'] else '❌'}")
    print(f"📊 Calidad de datos: {'✅' if summary['data_quality_acceptable'] else '❌'}")
    
    # Mostrar recomendaciones
    if report['recommendations']:
        print("\n=== RECOMENDACIONES ===")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"{i}. {rec}")
    
    # Guardar reporte detallado
    import json
    with open('api_diagnostic_report.json', 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n📄 Reporte detallado guardado en: api_diagnostic_report.json")
    print("📋 Log detallado en: api_connectivity_test.log")

if __name__ == "__main__":
    main()