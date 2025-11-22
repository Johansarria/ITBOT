#!/usr/bin/env python3
"""
Configuración Multi-Asset para SICAR
====================================

Basado en la investigación de los mejores instrumentos para trading en 2025:
- Forex: Pares principales con alta liquidez
- Índices: Los más volátiles y líquidos globalmente  
- Commodities: Metales preciosos y energía
- Criptomonedas: Top 10 validadas previamente

Fuentes de datos priorizadas:
1. Binance (crypto y algunos forex/commodities)
2. CoinGecko (crypto y datos alternativos)
3. Coinbase (crypto)
4. APIs tradicionales para forex/índices (futuro)

Año: 2025
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any

class MultiAssetConfigurator:
    """Configurador de activos múltiples para SICAR"""
    
    def __init__(self):
        self.config = {
            "metadata": {
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "version": "1.0",
                "description": "Configuración multi-asset basada en investigación 2025",
                "data_sources": ["Binance", "CoinGecko", "Coinbase"],
                "excluded_sources": ["yfinance"]
            },
            "asset_classes": {}
        }
        
    def configure_cryptocurrencies(self):
        """Configura las criptomonedas validadas (top 10)"""
        crypto_config = {
            "description": "Top 10 criptomonedas validadas para backtesting",
            "market_hours": "24/7",
            "base_currency": "USDT",
            "symbols": [
                {
                    "symbol": "BTCUSDT",
                    "name": "Bitcoin",
                    "category": "Major Crypto",
                    "priority": "high",
                    "validated": True
                },
                {
                    "symbol": "ETHUSDT", 
                    "name": "Ethereum",
                    "category": "Major Crypto",
                    "priority": "high",
                    "validated": True
                },
                {
                    "symbol": "BNBUSDT",
                    "name": "Binance Coin",
                    "category": "Exchange Token",
                    "priority": "high",
                    "validated": True
                },
                {
                    "symbol": "ADAUSDT",
                    "name": "Cardano",
                    "category": "Layer 1",
                    "priority": "medium",
                    "validated": True
                },
                {
                    "symbol": "SOLUSDT",
                    "name": "Solana",
                    "category": "Layer 1",
                    "priority": "high",
                    "validated": True
                },
                {
                    "symbol": "XRPUSDT",
                    "name": "XRP",
                    "category": "Payment",
                    "priority": "medium",
                    "validated": True
                },
                {
                    "symbol": "DOTUSDT",
                    "name": "Polkadot",
                    "category": "Layer 0",
                    "priority": "medium",
                    "validated": True
                },
                {
                    "symbol": "DOGEUSDT",
                    "name": "Dogecoin",
                    "category": "Meme",
                    "priority": "low",
                    "validated": True
                },
                {
                    "symbol": "AVAXUSDT",
                    "name": "Avalanche",
                    "category": "Layer 1",
                    "priority": "medium",
                    "validated": True
                },
                {
                    "symbol": "MATICUSDT",
                    "name": "Polygon",
                    "category": "Layer 2",
                    "priority": "medium",
                    "validated": True
                }
            ]
        }
        
        self.config["asset_classes"]["cryptocurrencies"] = crypto_config
        
    def configure_forex(self):
        """Configura los pares de forex principales"""
        forex_config = {
            "description": "Pares de forex principales con alta liquidez y volatilidad",
            "market_hours": "24/5 (Lunes-Viernes)",
            "session_overlap": "Londres-Nueva York (mayor liquidez)",
            "symbols": [
                {
                    "symbol": "EURUSD",
                    "name": "Euro/US Dollar",
                    "category": "Major Pair",
                    "priority": "high",
                    "daily_volume": "Highest",
                    "spread": "Lowest",
                    "validated": False,
                    "notes": "Par más líquido del mundo"
                },
                {
                    "symbol": "GBPUSD",
                    "name": "British Pound/US Dollar",
                    "category": "Major Pair",
                    "priority": "high",
                    "daily_volume": "High",
                    "spread": "Low",
                    "validated": False,
                    "notes": "Alta volatilidad, bueno para swing trading"
                },
                {
                    "symbol": "USDJPY",
                    "name": "US Dollar/Japanese Yen",
                    "category": "Major Pair",
                    "priority": "high",
                    "daily_volume": "High",
                    "spread": "Low",
                    "validated": False,
                    "notes": "Sensible a políticas del Banco de Japón"
                },
                {
                    "symbol": "AUDUSD",
                    "name": "Australian Dollar/US Dollar",
                    "category": "Major Pair",
                    "priority": "medium",
                    "daily_volume": "Medium",
                    "spread": "Medium",
                    "validated": False,
                    "notes": "Correlacionado con commodities"
                },
                {
                    "symbol": "USDCAD",
                    "name": "US Dollar/Canadian Dollar",
                    "category": "Major Pair",
                    "priority": "medium",
                    "daily_volume": "Medium",
                    "spread": "Medium",
                    "validated": False,
                    "notes": "Influenciado por precios del petróleo"
                },
                {
                    "symbol": "USDCHF",
                    "name": "US Dollar/Swiss Franc",
                    "category": "Major Pair",
                    "priority": "medium",
                    "daily_volume": "Medium",
                    "spread": "Medium",
                    "validated": False,
                    "notes": "Refugio seguro en tiempos de incertidumbre"
                }
            ]
        }
        
        self.config["asset_classes"]["forex"] = forex_config
        
    def configure_indices(self):
        """Configura los índices principales"""
        indices_config = {
            "description": "Índices principales con alta volatilidad y liquidez",
            "market_hours": "Varía según región",
            "trading_method": "CFDs, ETFs, Futuros",
            "symbols": [
                {
                    "symbol": "SPX500",
                    "name": "S&P 500",
                    "category": "US Index",
                    "priority": "high",
                    "market": "Estados Unidos",
                    "trading_hours": "09:30-16:00 EST",
                    "validated": False,
                    "notes": "Índice más seguido globalmente"
                },
                {
                    "symbol": "NAS100",
                    "name": "Nasdaq 100",
                    "category": "US Tech Index",
                    "priority": "high",
                    "market": "Estados Unidos",
                    "trading_hours": "09:30-16:00 EST",
                    "validated": False,
                    "notes": "Alta volatilidad, enfoque tecnológico"
                },
                {
                    "symbol": "DAX",
                    "name": "DAX 40",
                    "category": "European Index",
                    "priority": "high",
                    "market": "Alemania",
                    "trading_hours": "09:00-17:30 CET",
                    "validated": False,
                    "notes": "Índice alemán más volátil"
                },
                {
                    "symbol": "UK100",
                    "name": "FTSE 100",
                    "category": "European Index",
                    "priority": "medium",
                    "market": "Reino Unido",
                    "trading_hours": "08:00-16:30 GMT",
                    "validated": False,
                    "notes": "Índice británico principal"
                },
                {
                    "symbol": "JPN225",
                    "name": "Nikkei 225",
                    "category": "Asian Index",
                    "priority": "medium",
                    "market": "Japón",
                    "trading_hours": "09:00-15:00 JST",
                    "validated": False,
                    "notes": "Principal índice asiático"
                },
                {
                    "symbol": "AUS200",
                    "name": "ASX 200",
                    "category": "Pacific Index",
                    "priority": "low",
                    "market": "Australia",
                    "trading_hours": "10:00-16:00 AEST",
                    "validated": False,
                    "notes": "Correlacionado con commodities"
                }
            ]
        }
        
        self.config["asset_classes"]["indices"] = indices_config
        
    def configure_commodities(self):
        """Configura los commodities principales"""
        commodities_config = {
            "description": "Commodities principales: metales preciosos y energía",
            "market_hours": "24/5 para la mayoría",
            "trading_method": "CFDs, Futuros, ETFs",
            "symbols": [
                {
                    "symbol": "XAUUSD",
                    "name": "Gold/US Dollar",
                    "category": "Precious Metal",
                    "priority": "high",
                    "market": "Global",
                    "validated": False,
                    "notes": "Refugio seguro, hedge contra inflación"
                },
                {
                    "symbol": "XAGUSD",
                    "name": "Silver/US Dollar",
                    "category": "Precious Metal",
                    "priority": "medium",
                    "market": "Global",
                    "validated": False,
                    "notes": "Más volátil que el oro, uso industrial"
                },
                {
                    "symbol": "USOIL",
                    "name": "Crude Oil WTI",
                    "category": "Energy",
                    "priority": "high",
                    "market": "Global",
                    "validated": False,
                    "notes": "Benchmark estadounidense del petróleo"
                },
                {
                    "symbol": "UKOIL",
                    "name": "Brent Crude Oil",
                    "category": "Energy",
                    "priority": "high",
                    "market": "Global",
                    "validated": False,
                    "notes": "Benchmark europeo del petróleo"
                },
                {
                    "symbol": "NATGAS",
                    "name": "Natural Gas",
                    "category": "Energy",
                    "priority": "medium",
                    "market": "Global",
                    "validated": False,
                    "notes": "Alta volatilidad estacional"
                },
                {
                    "symbol": "COPPER",
                    "name": "Copper",
                    "category": "Industrial Metal",
                    "priority": "medium",
                    "market": "Global",
                    "validated": False,
                    "notes": "Indicador económico global"
                }
            ]
        }
        
        self.config["asset_classes"]["commodities"] = commodities_config
        
    def configure_trading_sessions(self):
        """Configura las sesiones de trading para diferentes mercados"""
        sessions_config = {
            "description": "Horarios de trading por región y clase de activo",
            "timezone_reference": "UTC",
            "sessions": {
                "crypto": {
                    "hours": "24/7",
                    "peak_volume": "14:00-22:00 UTC (overlap US-Europe)"
                },
                "forex": {
                    "sydney": "22:00-07:00 UTC",
                    "tokyo": "00:00-09:00 UTC", 
                    "london": "08:00-17:00 UTC",
                    "new_york": "13:00-22:00 UTC",
                    "overlap_london_ny": "13:00-17:00 UTC (highest liquidity)"
                },
                "indices": {
                    "us_indices": "14:30-21:00 UTC",
                    "european_indices": "08:00-16:30 UTC",
                    "asian_indices": "00:00-06:00 UTC"
                },
                "commodities": {
                    "metals": "24/5",
                    "energy": "24/5",
                    "peak_hours": "13:00-17:00 UTC"
                }
            }
        }
        
        self.config["trading_sessions"] = sessions_config
        
    def configure_risk_parameters(self):
        """Configura parámetros de riesgo por clase de activo"""
        risk_config = {
            "description": "Parámetros de riesgo específicos por clase de activo",
            "parameters": {
                "cryptocurrencies": {
                    "max_position_size": 0.02,  # 2% del capital por posición
                    "max_daily_risk": 0.05,     # 5% del capital por día
                    "volatility_multiplier": 1.5,
                    "correlation_limit": 0.7
                },
                "forex": {
                    "max_position_size": 0.03,  # 3% del capital por posición
                    "max_daily_risk": 0.04,     # 4% del capital por día
                    "volatility_multiplier": 1.0,
                    "correlation_limit": 0.6
                },
                "indices": {
                    "max_position_size": 0.025, # 2.5% del capital por posición
                    "max_daily_risk": 0.045,    # 4.5% del capital por día
                    "volatility_multiplier": 1.2,
                    "correlation_limit": 0.65
                },
                "commodities": {
                    "max_position_size": 0.025, # 2.5% del capital por posición
                    "max_daily_risk": 0.04,     # 4% del capital por día
                    "volatility_multiplier": 1.3,
                    "correlation_limit": 0.6
                }
            }
        }
        
        self.config["risk_management"] = risk_config
        
    def generate_configuration(self):
        """Genera la configuración completa"""
        print("🔧 Generando configuración multi-asset...")
        
        # Configurar todas las clases de activos
        self.configure_cryptocurrencies()
        self.configure_forex()
        self.configure_indices()
        self.configure_commodities()
        self.configure_trading_sessions()
        self.configure_risk_parameters()
        
        # Estadísticas de la configuración
        stats = {
            "total_instruments": 0,
            "by_asset_class": {},
            "validated_instruments": 0,
            "priority_distribution": {"high": 0, "medium": 0, "low": 0}
        }
        
        for asset_class, config in self.config["asset_classes"].items():
            count = len(config["symbols"])
            stats["total_instruments"] += count
            stats["by_asset_class"][asset_class] = count
            
            for symbol in config["symbols"]:
                if symbol.get("validated", False):
                    stats["validated_instruments"] += 1
                stats["priority_distribution"][symbol["priority"]] += 1
        
        self.config["statistics"] = stats
        
        return self.config
        
    def save_configuration(self, filename=None):
        """Guarda la configuración en archivo JSON"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"multi_asset_config_{timestamp}.json"
            
        filepath = os.path.join(os.getcwd(), filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Configuración guardada en: {filepath}")
        return filepath
        
    def print_summary(self):
        """Imprime un resumen de la configuración"""
        stats = self.config["statistics"]
        
        print("\n" + "="*60)
        print("📊 RESUMEN CONFIGURACIÓN MULTI-ASSET SICAR 2025")
        print("="*60)
        
        print(f"\n📈 INSTRUMENTOS TOTALES: {stats['total_instruments']}")
        print(f"✅ INSTRUMENTOS VALIDADOS: {stats['validated_instruments']}")
        print(f"⏳ PENDIENTES DE VALIDACIÓN: {stats['total_instruments'] - stats['validated_instruments']}")
        
        print("\n🏷️  POR CLASE DE ACTIVO:")
        for asset_class, count in stats["by_asset_class"].items():
            print(f"   • {asset_class.title()}: {count} instrumentos")
            
        print("\n🎯 POR PRIORIDAD:")
        for priority, count in stats["priority_distribution"].items():
            print(f"   • {priority.title()}: {count} instrumentos")
            
        print("\n💡 FUENTES DE DATOS:")
        for source in self.config["metadata"]["data_sources"]:
            print(f"   ✅ {source}")
            
        print(f"\n❌ EXCLUIDAS: {', '.join(self.config['metadata']['excluded_sources'])}")
        
        print("\n🕐 HORARIOS DE TRADING:")
        print("   • Crypto: 24/7")
        print("   • Forex: 24/5 (Lunes-Viernes)")
        print("   • Índices: Horarios regionales")
        print("   • Commodities: 24/5 mayoría")
        
        print("\n🛡️  GESTIÓN DE RIESGO:")
        print("   • Tamaño máximo posición: 2-3% por instrumento")
        print("   • Riesgo diario máximo: 4-5% del capital")
        print("   • Límites de correlación configurados")
        
        print("\n" + "="*60)

def main():
    """Función principal"""
    print("🚀 Iniciando configuración multi-asset SICAR...")
    
    # Crear configurador
    configurator = MultiAssetConfigurator()
    
    # Generar configuración
    config = configurator.generate_configuration()
    
    # Guardar configuración
    filepath = configurator.save_configuration()
    
    # Mostrar resumen
    configurator.print_summary()
    
    print(f"\n🎯 PRÓXIMOS PASOS:")
    print("1. Validar disponibilidad de instrumentos forex/índices/commodities")
    print("2. Configurar APIs adicionales para datos tradicionales")
    print("3. Adaptar sistema de backtesting para multi-asset")
    print("4. Implementar análisis de correlaciones")
    print("5. Configurar gestión de riesgo multi-asset")
    
    return config, filepath

if __name__ == "__main__":
    config, filepath = main()