#!/usr/bin/env python3
"""
Sistema Multi-Asset para SICAR
==============================

Sistema avanzado de datos que maneja múltiples clases de activos:
- Criptomonedas (Binance, CoinGecko, Coinbase)
- Forex (APIs tradicionales + crypto proxies)
- Índices (APIs tradicionales + ETFs)
- Commodities (APIs tradicionales + crypto proxies)

Características:
- Fallback automático entre APIs
- Cache inteligente por clase de activo
- Gestión de horarios de mercado
- Validación de calidad de datos
- Métricas de rendimiento

Año: 2025
"""

import pandas as pd
import numpy as np
import requests
import time
import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Tuple, Any
import os
from dotenv import load_dotenv
from real_data_system import RealDataSystem

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiAssetDataSystem(RealDataSystem):
    """
    Sistema de datos multi-asset que extiende RealDataSystem
    para manejar crypto, forex, índices y commodities
    """
    
    def __init__(self, config_file: str = None):
        """Inicializar sistema multi-asset"""
        super().__init__()
        
        # Cargar configuración multi-asset
        self.config = self._load_multi_asset_config(config_file)
        
        # APIs adicionales para activos tradicionales
        self.traditional_apis = {
            'alpha_vantage': {
                'base_url': 'https://www.alphavantage.co/query',
                'api_key': os.getenv('ALPHA_VANTAGE_API_KEY'),
                'priority': 1,
                'working': bool(os.getenv('ALPHA_VANTAGE_API_KEY')),
                'rate_limit': 5.0,  # 5 requests/minute for free tier
                'supports': ['forex', 'indices', 'commodities']
            },
            'finhub': {
                'base_url': 'https://finnhub.io/api/v1',
                'api_key': os.getenv('FINNHUB_API_KEY'),
                'priority': 2,
                'working': bool(os.getenv('FINNHUB_API_KEY')),
                'rate_limit': 1.0,
                'supports': ['forex', 'indices', 'commodities']
            },
            'twelve_data': {
                'base_url': 'https://api.twelvedata.com',
                'api_key': os.getenv('TWELVE_DATA_API_KEY'),
                'priority': 3,
                'working': bool(os.getenv('TWELVE_DATA_API_KEY')),
                'rate_limit': 1.0,
                'supports': ['forex', 'indices', 'commodities']
            }
        }
        
        # Mapeo extendido de símbolos por clase de activo
        self.extended_symbol_mapping = self._build_extended_symbol_mapping()
        
        # Horarios de mercado por clase de activo
        self.market_hours = self._configure_market_hours()
        
        # Cache especializado por clase de activo
        self.asset_cache = {
            'cryptocurrencies': {},
            'forex': {},
            'indices': {},
            'commodities': {}
        }
        
        # Estadísticas extendidas
        self.extended_stats = {
            'requests_by_asset_class': {
                'cryptocurrencies': 0,
                'forex': 0,
                'indices': 0,
                'commodities': 0
            },
            'success_rate_by_asset_class': {
                'cryptocurrencies': 0.0,
                'forex': 0.0,
                'indices': 0.0,
                'commodities': 0.0
            },
            'api_usage_traditional': {api: 0 for api in self.traditional_apis.keys()}
        }
        
        logger.info("🌐 Sistema Multi-Asset inicializado")
        logger.info(f"📊 Clases de activos: {list(self.config['asset_classes'].keys())}")
        logger.info(f"🔌 APIs tradicionales: {list(self.traditional_apis.keys())}")
        
    def _load_multi_asset_config(self, config_file: str = None) -> Dict:
        """Cargar configuración multi-asset"""
        if config_file is None:
            # Buscar el archivo de configuración más reciente
            config_files = [f for f in os.listdir('.') if f.startswith('multi_asset_config_') and f.endswith('.json')]
            if config_files:
                config_file = sorted(config_files)[-1]
            else:
                raise FileNotFoundError("No se encontró archivo de configuración multi-asset")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"✅ Configuración cargada desde: {config_file}")
            return config
        except Exception as e:
            logger.error(f"❌ Error cargando configuración: {e}")
            raise
            
    def _build_extended_symbol_mapping(self) -> Dict:
        """Construir mapeo extendido de símbolos"""
        mapping = {}
        
        # Agregar criptomonedas existentes
        mapping.update(self.symbol_mapping)
        
        # Agregar forex
        forex_mapping = {
            'EURUSD': {
                'alpha_vantage': 'EUR/USD',
                'finhub': 'OANDA:EUR_USD',
                'twelve_data': 'EUR/USD',
                'binance': 'EURUSDT'  # Proxy usando USDT
            },
            'GBPUSD': {
                'alpha_vantage': 'GBP/USD',
                'finhub': 'OANDA:GBP_USD',
                'twelve_data': 'GBP/USD',
                'binance': 'GBPUSDT'
            },
            'USDJPY': {
                'alpha_vantage': 'USD/JPY',
                'finhub': 'OANDA:USD_JPY',
                'twelve_data': 'USD/JPY'
            },
            'AUDUSD': {
                'alpha_vantage': 'AUD/USD',
                'finhub': 'OANDA:AUD_USD',
                'twelve_data': 'AUD/USD',
                'binance': 'AUDUSDT'
            }
        }
        mapping.update(forex_mapping)
        
        # Agregar índices
        indices_mapping = {
            'SPX500': {
                'alpha_vantage': 'SPX',
                'finhub': 'INDEXSP:.INX',
                'twelve_data': 'SPX'
            },
            'NAS100': {
                'alpha_vantage': 'IXIC',
                'finhub': 'INDEXNASDAQ:.IXIC',
                'twelve_data': 'IXIC'
            },
            'DAX': {
                'alpha_vantage': 'DAX',
                'finhub': 'INDEXDB:DAX',
                'twelve_data': 'DAX'
            }
        }
        mapping.update(indices_mapping)
        
        # Agregar commodities
        commodities_mapping = {
            'XAUUSD': {
                'alpha_vantage': 'XAU/USD',
                'finhub': 'OANDA:XAU_USD',
                'twelve_data': 'XAU/USD'
            },
            'XAGUSD': {
                'alpha_vantage': 'XAG/USD',
                'finhub': 'OANDA:XAG_USD',
                'twelve_data': 'XAG/USD'
            },
            'USOIL': {
                'alpha_vantage': 'WTI',
                'finhub': 'OANDA:WTICO_USD',
                'twelve_data': 'WTI'
            }
        }
        mapping.update(commodities_mapping)
        
        return mapping
        
    def _configure_market_hours(self) -> Dict:
        """Configurar horarios de mercado"""
        return {
            'cryptocurrencies': {
                'always_open': True,
                'timezone': 'UTC'
            },
            'forex': {
                'always_open': False,
                'sessions': {
                    'sydney': {'start': '22:00', 'end': '07:00'},
                    'tokyo': {'start': '00:00', 'end': '09:00'},
                    'london': {'start': '08:00', 'end': '17:00'},
                    'new_york': {'start': '13:00', 'end': '22:00'}
                },
                'timezone': 'UTC',
                'closed_weekends': True
            },
            'indices': {
                'always_open': False,
                'regional_hours': {
                    'us': {'start': '14:30', 'end': '21:00'},
                    'europe': {'start': '08:00', 'end': '16:30'},
                    'asia': {'start': '00:00', 'end': '06:00'}
                },
                'timezone': 'UTC',
                'closed_weekends': True
            },
            'commodities': {
                'always_open': False,
                'trading_hours': {'start': '00:00', 'end': '23:00'},
                'timezone': 'UTC',
                'closed_weekends': True
            }
        }
        
    def get_asset_class(self, symbol: str) -> str:
        """Determinar la clase de activo de un símbolo"""
        for asset_class, config in self.config['asset_classes'].items():
            for asset_symbol in config['symbols']:
                if asset_symbol['symbol'] == symbol:
                    return asset_class
        return 'unknown'
        
    def is_market_open(self, asset_class: str) -> bool:
        """Verificar si el mercado está abierto para una clase de activo"""
        market_config = self.market_hours.get(asset_class, {})
        
        if market_config.get('always_open', False):
            return True
            
        now = datetime.now(timezone.utc)
        
        # Verificar si es fin de semana
        if market_config.get('closed_weekends', False) and now.weekday() >= 5:
            return False
            
        # Para forex, verificar si alguna sesión está abierta
        if asset_class == 'forex':
            current_time = now.strftime('%H:%M')
            for session, hours in market_config.get('sessions', {}).items():
                start = hours['start']
                end = hours['end']
                
                # Manejar sesiones que cruzan medianoche
                if start > end:
                    if current_time >= start or current_time <= end:
                        return True
                else:
                    if start <= current_time <= end:
                        return True
            return False
            
        # Para otros activos, verificar horarios regionales o generales
        if 'regional_hours' in market_config:
            current_time = now.strftime('%H:%M')
            for region, hours in market_config['regional_hours'].items():
                if hours['start'] <= current_time <= hours['end']:
                    return True
            return False
            
        if 'trading_hours' in market_config:
            current_time = now.strftime('%H:%M')
            hours = market_config['trading_hours']
            return hours['start'] <= current_time <= hours['end']
            
        return True  # Default: abierto
        
    def get_multi_asset_data(self, symbol: str, interval: str = '4h', 
                           limit: int = 500) -> Optional[pd.DataFrame]:
        """
        Obtener datos para cualquier clase de activo
        
        Args:
            symbol: Símbolo del activo
            interval: Intervalo de tiempo
            limit: Número de velas
            
        Returns:
            DataFrame con datos OHLCV o None si falla
        """
        asset_class = self.get_asset_class(symbol)
        
        logger.info(f"📊 Obteniendo datos para {symbol} (clase: {asset_class})")
        
        # Actualizar estadísticas
        self.extended_stats['requests_by_asset_class'][asset_class] += 1
        
        # Verificar si el mercado está abierto (solo para validación)
        market_open = self.is_market_open(asset_class)
        if not market_open:
            logger.warning(f"⚠️ Mercado cerrado para {asset_class}, obteniendo datos históricos")
        
        # Verificar cache específico de la clase de activo
        cache_key = f"{symbol}_{interval}_{limit}"
        if self._is_asset_cache_valid(asset_class, cache_key):
            logger.info("💾 Datos obtenidos del cache especializado")
            return self.asset_cache[asset_class][cache_key]['data']
        
        data = None
        
        # Estrategia de obtención de datos según la clase de activo
        if asset_class == 'cryptocurrencies':
            data = self.get_historical_data(symbol, interval, limit)
        else:
            data = self._get_traditional_asset_data(symbol, asset_class, interval, limit)
            
        # Si no se obtuvieron datos tradicionales, intentar proxies crypto
        if data is None and asset_class in ['forex', 'commodities']:
            logger.info(f"🔄 Intentando proxy crypto para {symbol}")
            data = self._get_crypto_proxy_data(symbol, interval, limit)
            
        if data is not None:
            self._cache_asset_data(asset_class, cache_key, data)
            logger.info(f"✅ Datos obtenidos para {symbol}: {len(data)} velas")
            return data
        else:
            logger.error(f"❌ No se pudieron obtener datos para {symbol}")
            return None
            
    def _get_traditional_asset_data(self, symbol: str, asset_class: str, 
                                  interval: str, limit: int) -> Optional[pd.DataFrame]:
        """Obtener datos de activos tradicionales (forex, índices, commodities)"""
        
        # Ordenar APIs por prioridad
        apis_sorted = sorted(
            [(name, config) for name, config in self.traditional_apis.items() 
             if config['working'] and asset_class in config['supports']],
            key=lambda x: x[1]['priority']
        )
        
        for api_name, api_config in apis_sorted:
            try:
                logger.info(f"🔄 Intentando {api_name.upper()} para {symbol}")
                
                data = None
                if api_name == 'alpha_vantage':
                    data = self._get_alpha_vantage_data(symbol, interval, limit)
                elif api_name == 'finhub':
                    data = self._get_finnhub_data(symbol, interval, limit)
                elif api_name == 'twelve_data':
                    data = self._get_twelve_data(symbol, interval, limit)
                    
                if data is not None and len(data) >= 10:
                    self.extended_stats['api_usage_traditional'][api_name] += 1
                    return data
                    
            except Exception as e:
                logger.error(f"❌ Error con {api_name}: {e}")
                continue
                
        return None
        
    def _get_crypto_proxy_data(self, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """Obtener datos usando proxies de crypto (ej: EURUSDT para EURUSD)"""
        
        # Mapeo de proxies crypto
        crypto_proxies = {
            'EURUSD': 'EURUSDT',
            'GBPUSD': 'GBPUSDT',
            'AUDUSD': 'AUDUSDT',
            'USDCAD': 'USDCUSDT'
        }
        
        proxy_symbol = crypto_proxies.get(symbol)
        if proxy_symbol:
            logger.info(f"🔄 Usando proxy crypto {proxy_symbol} para {symbol}")
            return self.get_historical_data(proxy_symbol, interval, limit)
            
        return None
        
    def _get_alpha_vantage_data(self, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """Obtener datos de Alpha Vantage"""
        if not self.traditional_apis['alpha_vantage']['working']:
            return None
            
        # Implementación placeholder - requiere API key válida
        logger.info("⚠️ Alpha Vantage requiere configuración de API key")
        return None
        
    def _get_finnhub_data(self, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """Obtener datos de Finnhub"""
        if not self.traditional_apis['finhub']['working']:
            return None
            
        # Implementación placeholder - requiere API key válida
        logger.info("⚠️ Finnhub requiere configuración de API key")
        return None
        
    def _get_twelve_data(self, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """Obtener datos de Twelve Data"""
        if not self.traditional_apis['twelve_data']['working']:
            return None
            
        # Implementación placeholder - requiere API key válida
        logger.info("⚠️ Twelve Data requiere configuración de API key")
        return None
        
    def _is_asset_cache_valid(self, asset_class: str, cache_key: str) -> bool:
        """Verificar si el cache de una clase de activo es válido"""
        if cache_key not in self.asset_cache[asset_class]:
            return False
            
        cache_time = self.asset_cache[asset_class][cache_key]['timestamp']
        return (time.time() - cache_time) < self.cache_duration
        
    def _cache_asset_data(self, asset_class: str, cache_key: str, data: pd.DataFrame):
        """Cachear datos por clase de activo"""
        self.asset_cache[asset_class][cache_key] = {
            'data': data.copy(),
            'timestamp': time.time()
        }
        
    def get_available_symbols(self, asset_class: str = None) -> List[str]:
        """Obtener símbolos disponibles por clase de activo"""
        if asset_class is None:
            # Retornar todos los símbolos
            symbols = []
            for ac, config in self.config['asset_classes'].items():
                symbols.extend([s['symbol'] for s in config['symbols']])
            return symbols
        else:
            # Retornar símbolos de una clase específica
            if asset_class in self.config['asset_classes']:
                return [s['symbol'] for s in self.config['asset_classes'][asset_class]['symbols']]
            return []
            
    def get_validated_symbols(self, asset_class: str = None) -> List[str]:
        """Obtener símbolos validados por clase de activo"""
        symbols = []
        
        if asset_class is None:
            # Todos los símbolos validados
            for ac, config in self.config['asset_classes'].items():
                symbols.extend([s['symbol'] for s in config['symbols'] if s.get('validated', False)])
        else:
            # Símbolos validados de una clase específica
            if asset_class in self.config['asset_classes']:
                symbols = [s['symbol'] for s in self.config['asset_classes'][asset_class]['symbols'] 
                          if s.get('validated', False)]
                          
        return symbols
        
    def get_system_stats(self) -> Dict:
        """Obtener estadísticas del sistema multi-asset"""
        total_requests = sum(self.extended_stats['requests_by_asset_class'].values())
        
        stats = {
            'total_requests': total_requests,
            'requests_by_asset_class': self.extended_stats['requests_by_asset_class'].copy(),
            'available_symbols': {
                ac: len(self.get_available_symbols(ac)) 
                for ac in self.config['asset_classes'].keys()
            },
            'validated_symbols': {
                ac: len(self.get_validated_symbols(ac)) 
                for ac in self.config['asset_classes'].keys()
            },
            'market_status': {
                ac: self.is_market_open(ac) 
                for ac in self.config['asset_classes'].keys()
            },
            'api_usage': {
                'crypto_apis': self.stats['api_usage'].copy(),
                'traditional_apis': self.extended_stats['api_usage_traditional'].copy()
            }
        }
        
        return stats
        
    def print_system_summary(self):
        """Imprimir resumen del sistema multi-asset"""
        stats = self.get_system_stats()
        
        print("\n" + "="*60)
        print("🌐 RESUMEN SISTEMA MULTI-ASSET SICAR")
        print("="*60)
        
        print(f"\n📊 ESTADÍSTICAS GENERALES:")
        print(f"   • Total requests: {stats['total_requests']}")
        
        print(f"\n📈 SÍMBOLOS POR CLASE DE ACTIVO:")
        for asset_class, count in stats['available_symbols'].items():
            validated = stats['validated_symbols'][asset_class]
            print(f"   • {asset_class.title()}: {count} total, {validated} validados")
            
        print(f"\n🕐 ESTADO DE MERCADOS:")
        for asset_class, is_open in stats['market_status'].items():
            status = "🟢 ABIERTO" if is_open else "🔴 CERRADO"
            print(f"   • {asset_class.title()}: {status}")
            
        print(f"\n🔌 USO DE APIs:")
        print("   Crypto APIs:")
        for api, usage in stats['api_usage']['crypto_apis'].items():
            print(f"     - {api}: {usage} requests")
        print("   Traditional APIs:")
        for api, usage in stats['api_usage']['traditional_apis'].items():
            print(f"     - {api}: {usage} requests")
            
        print("\n" + "="*60)

def main():
    """Función principal de demostración"""
    print("🚀 Iniciando Sistema Multi-Asset SICAR...")
    
    try:
        # Inicializar sistema
        system = MultiAssetDataSystem()
        
        # Mostrar resumen
        system.print_system_summary()
        
        # Probar con diferentes clases de activos
        test_symbols = [
            ('BTCUSDT', 'cryptocurrencies'),
            ('EURUSD', 'forex'),
            ('SPX500', 'indices'),
            ('XAUUSD', 'commodities')
        ]
        
        print(f"\n🧪 PRUEBAS DE CONECTIVIDAD:")
        for symbol, expected_class in test_symbols:
            print(f"\n📊 Probando {symbol} ({expected_class})...")
            
            # Verificar clasificación
            detected_class = system.get_asset_class(symbol)
            print(f"   Clase detectada: {detected_class}")
            
            # Verificar estado del mercado
            market_open = system.is_market_open(detected_class)
            print(f"   Mercado: {'🟢 Abierto' if market_open else '🔴 Cerrado'}")
            
            # Intentar obtener datos
            data = system.get_multi_asset_data(symbol, '1h', 24)
            if data is not None:
                print(f"   ✅ Datos obtenidos: {len(data)} velas")
                # Verificar columnas disponibles
                if 'close' in data.columns:
                    print(f"   📈 Último precio: {data['close'].iloc[-1]:.4f}")
                elif 'Close' in data.columns:
                    print(f"   📈 Último precio: {data['Close'].iloc[-1]:.4f}")
                else:
                    print(f"   📊 Columnas disponibles: {list(data.columns)}")
            else:
                print(f"   ❌ No se pudieron obtener datos")
        
        # Estadísticas finales
        print(f"\n📊 ESTADÍSTICAS FINALES:")
        final_stats = system.get_system_stats()
        print(f"   • Total requests: {final_stats['total_requests']}")
        
        return system
        
    except Exception as e:
        logger.error(f"❌ Error en sistema multi-asset: {e}")
        return None

if __name__ == "__main__":
    system = main()