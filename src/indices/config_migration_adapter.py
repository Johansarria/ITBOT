"""
SICAR Config Migration Adapter
Adaptador para migrar configuraciones de crypto a índices
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfigMigrationAdapter:
    """
    Adaptador para migrar configuraciones de crypto a índices
    Facilita la transición manteniendo compatibilidad
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Mapeo de símbolos crypto -> índices
        self.symbol_mapping = {
            'BTCUSDT': 'SPY',    # Bitcoin -> S&P 500
            'ETHUSDT': 'QQQ',    # Ethereum -> Nasdaq
            'ADAUSDT': 'IWM',    # Cardano -> Russell 2000
            'DOTUSDT': 'DIA',    # Polkadot -> Dow Jones
            'LINKUSDT': 'VTI',   # Chainlink -> Total Market
            'SOLUSDT': 'QQQ',    # Solana -> Nasdaq
            'AVAXUSDT': 'IWM',   # Avalanche -> Small Cap
            'MATICUSDT': 'QQQ',  # Polygon -> Tech
            'ATOMUSDT': 'VTI',   # Cosmos -> Broad Market
            'NEARUSDT': 'IWM'    # Near -> Small Cap
        }
        
        # Mapeo de intervalos crypto -> índices
        self.interval_mapping = {
            '1m': '1m',      # Mantener para backtesting
            '5m': '5m',      # Mantener para análisis intraday
            '15m': '15m',    # Mantener
            '1h': '1h',      # Mantener
            '4h': '1d',      # 4h crypto -> 1d índices
            '1d': '1d',      # Mantener
            '1w': '1w'       # Mantener
        }
        
        # Factores de conversión para parámetros
        self.conversion_factors = {
            'volatility': 0.3,      # Índices menos volátiles
            'timeframe': 1.5,       # Timeframes más largos
            'position_size': 0.8,   # Posiciones más conservadoras
            'stop_loss': 0.7,       # Stop loss más ajustados
            'take_profit': 0.8,     # Take profit más conservadores
            'risk_per_trade': 0.6,  # Menor riesgo por trade
            'max_positions': 0.5,   # Menos posiciones simultáneas
            'leverage': 0.1         # Leverage muy reducido
        }
        
        # Configuraciones específicas para índices
        self.indices_specific_config = {
            'market_hours': {
                'regular_hours': {'start': '09:30', 'end': '16:00'},
                'extended_hours': {'start': '04:00', 'end': '20:00'},
                'timezone': 'US/Eastern'
            },
            'data_sources': {
                'primary': 'yahoo_finance',
                'secondary': 'iex',
                'backup': 'alpha_vantage'
            },
            'trading_sessions': {
                'allow_pre_market': False,
                'allow_after_hours': False,
                'regular_hours_only': True
            },
            'holidays': {
                'respect_us_holidays': True,
                'early_close_days': True,
                'custom_holidays': []
            }
        }
    
    def migrate_config(self, crypto_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrar configuración completa de crypto a índices
        
        Args:
            crypto_config: Configuración original de crypto
            
        Returns:
            Configuración migrada para índices
        """
        try:
            self.logger.info("Iniciando migración de configuración crypto -> índices")
            
            migrated_config = {
                'migration_info': {
                    'source': 'crypto',
                    'target': 'indices',
                    'migration_date': datetime.now().isoformat(),
                    'version': '1.0'
                }
            }
            
            # Migrar símbolos
            migrated_config['symbols'] = self._migrate_symbols(
                crypto_config.get('symbols', {})
            )
            
            # Migrar parámetros de trading
            migrated_config['trading'] = self._migrate_trading_params(
                crypto_config.get('trading', {})
            )
            
            # Migrar parámetros de riesgo
            migrated_config['risk'] = self._migrate_risk_params(
                crypto_config.get('risk', {})
            )
            
            # Migrar parámetros técnicos
            migrated_config['technical'] = self._migrate_technical_params(
                crypto_config.get('technical', {})
            )
            
            # Migrar configuración de datos
            migrated_config['data'] = self._migrate_data_config(
                crypto_config.get('data', {})
            )
            
            # Añadir configuraciones específicas de índices
            migrated_config.update(self.indices_specific_config)
            
            # Validar configuración migrada
            validation_result = self._validate_migrated_config(migrated_config)
            migrated_config['validation'] = validation_result
            
            self.logger.info("Migración de configuración completada")
            return migrated_config
            
        except Exception as e:
            self.logger.error(f"Error en migración de configuración: {e}")
            return self._get_default_indices_config()
    
    def _migrate_symbols(self, crypto_symbols: Dict[str, Any]) -> Dict[str, Any]:
        """Migrar configuración de símbolos"""
        migrated_symbols = {}
        
        for crypto_symbol, config in crypto_symbols.items():
            # Mapear símbolo crypto a índice
            index_symbol = self.symbol_mapping.get(crypto_symbol, 'SPY')
            
            migrated_symbols[index_symbol] = {
                'original_crypto_symbol': crypto_symbol,
                'symbol_type': 'ETF',
                'market': 'US',
                'currency': 'USD',
                'active': config.get('active', True),
                'weight': config.get('weight', 1.0) * 0.8,  # Reducir peso
                'min_position_size': max(1, config.get('min_position_size', 10) * 0.1),
                'max_position_size': config.get('max_position_size', 1000) * 0.5
            }
        
        # Asegurar que tenemos al menos SPY
        if not migrated_symbols:
            migrated_symbols['SPY'] = {
                'symbol_type': 'ETF',
                'market': 'US',
                'currency': 'USD',
                'active': True,
                'weight': 1.0,
                'min_position_size': 1,
                'max_position_size': 100
            }
        
        return migrated_symbols
    
    def _migrate_trading_params(self, crypto_trading: Dict[str, Any]) -> Dict[str, Any]:
        """Migrar parámetros de trading"""
        return {
            'strategy': crypto_trading.get('strategy', 'sicar_indices'),
            'timeframe': self.interval_mapping.get(
                crypto_trading.get('timeframe', '1h'), '1d'
            ),
            'position_sizing': {
                'method': crypto_trading.get('position_sizing', {}).get('method', 'fixed'),
                'base_size': (
                    crypto_trading.get('position_sizing', {}).get('base_size', 1000) * 
                    self.conversion_factors['position_size']
                ),
                'max_size': (
                    crypto_trading.get('position_sizing', {}).get('max_size', 10000) * 
                    self.conversion_factors['position_size']
                )
            },
            'execution': {
                'order_type': 'market',  # Más simple para índices
                'slippage_tolerance': crypto_trading.get('execution', {}).get('slippage_tolerance', 0.001) * 2,
                'timeout': crypto_trading.get('execution', {}).get('timeout', 30),
                'retry_attempts': crypto_trading.get('execution', {}).get('retry_attempts', 3)
            },
            'leverage': max(1.0, crypto_trading.get('leverage', 1.0) * self.conversion_factors['leverage']),
            'max_positions': max(1, int(crypto_trading.get('max_positions', 5) * self.conversion_factors['max_positions']))
        }
    
    def _migrate_risk_params(self, crypto_risk: Dict[str, Any]) -> Dict[str, Any]:
        """Migrar parámetros de riesgo"""
        return {
            'max_drawdown': crypto_risk.get('max_drawdown', 0.1) * 0.5,  # Más conservador
            'risk_per_trade': (
                crypto_risk.get('risk_per_trade', 0.02) * 
                self.conversion_factors['risk_per_trade']
            ),
            'stop_loss': {
                'type': crypto_risk.get('stop_loss', {}).get('type', 'percentage'),
                'value': (
                    crypto_risk.get('stop_loss', {}).get('value', 0.02) * 
                    self.conversion_factors['stop_loss']
                ),
                'trailing': crypto_risk.get('stop_loss', {}).get('trailing', False)
            },
            'take_profit': {
                'type': crypto_risk.get('take_profit', {}).get('type', 'percentage'),
                'value': (
                    crypto_risk.get('take_profit', {}).get('value', 0.04) * 
                    self.conversion_factors['take_profit']
                ),
                'partial_exits': crypto_risk.get('take_profit', {}).get('partial_exits', False)
            },
            'position_limits': {
                'max_correlation': crypto_risk.get('position_limits', {}).get('max_correlation', 0.7),
                'max_sector_exposure': 0.3,  # Nuevo para índices
                'max_single_position': 0.2   # Nuevo para índices
            },
            'volatility_filter': {
                'enabled': True,
                'max_volatility': crypto_risk.get('volatility_filter', {}).get('max_volatility', 0.05) * 0.6,
                'lookback_period': crypto_risk.get('volatility_filter', {}).get('lookback_period', 20)
            }
        }
    
    def _migrate_technical_params(self, crypto_technical: Dict[str, Any]) -> Dict[str, Any]:
        """Migrar parámetros técnicos"""
        timeframe_factor = self.conversion_factors['timeframe']
        
        return {
            'indicators': {
                'rsi': {
                    'period': max(10, int(crypto_technical.get('indicators', {}).get('rsi', {}).get('period', 14) * timeframe_factor)),
                    'overbought': crypto_technical.get('indicators', {}).get('rsi', {}).get('overbought', 70),
                    'oversold': crypto_technical.get('indicators', {}).get('rsi', {}).get('oversold', 30)
                },
                'macd': {
                    'fast': max(8, int(crypto_technical.get('indicators', {}).get('macd', {}).get('fast', 12) * timeframe_factor)),
                    'slow': max(20, int(crypto_technical.get('indicators', {}).get('macd', {}).get('slow', 26) * timeframe_factor)),
                    'signal': max(6, int(crypto_technical.get('indicators', {}).get('macd', {}).get('signal', 9) * timeframe_factor))
                },
                'bollinger_bands': {
                    'period': max(15, int(crypto_technical.get('indicators', {}).get('bollinger_bands', {}).get('period', 20) * timeframe_factor)),
                    'std_dev': crypto_technical.get('indicators', {}).get('bollinger_bands', {}).get('std_dev', 2.0)
                },
                'moving_averages': {
                    'short': max(8, int(crypto_technical.get('indicators', {}).get('moving_averages', {}).get('short', 9) * timeframe_factor)),
                    'long': max(15, int(crypto_technical.get('indicators', {}).get('moving_averages', {}).get('long', 21) * timeframe_factor)),
                    'trend': max(30, int(crypto_technical.get('indicators', {}).get('moving_averages', {}).get('trend', 50) * timeframe_factor))
                }
            },
            'filters': {
                'volume_filter': {
                    'enabled': True,
                    'min_volume': 100000,  # Mínimo para índices
                    'volume_sma_period': max(15, int(crypto_technical.get('filters', {}).get('volume_filter', {}).get('volume_sma_period', 20) * timeframe_factor))
                },
                'volatility_filter': {
                    'enabled': True,
                    'max_volatility': crypto_technical.get('filters', {}).get('volatility_filter', {}).get('max_volatility', 0.05) * 0.6,
                    'period': max(15, int(crypto_technical.get('filters', {}).get('volatility_filter', {}).get('period', 20) * timeframe_factor))
                },
                'trend_filter': {
                    'enabled': crypto_technical.get('filters', {}).get('trend_filter', {}).get('enabled', True),
                    'min_trend_strength': crypto_technical.get('filters', {}).get('trend_filter', {}).get('min_trend_strength', 0.3),
                    'period': max(30, int(crypto_technical.get('filters', {}).get('trend_filter', {}).get('period', 50) * timeframe_factor))
                }
            }
        }
    
    def _migrate_data_config(self, crypto_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrar configuración de datos"""
        return {
            'source': 'yahoo_finance',  # Cambiar de Binance
            'backup_sources': ['iex', 'alpha_vantage'],
            'intervals': {
                'primary': self.interval_mapping.get(crypto_data.get('interval', '1h'), '1d'),
                'secondary': ['1h', '1d'],  # Para análisis múltiple
                'backtest': '1d'
            },
            'history': {
                'lookback_days': crypto_data.get('history', {}).get('lookback_days', 365),
                'min_data_points': crypto_data.get('history', {}).get('min_data_points', 100),
                'max_data_points': crypto_data.get('history', {}).get('max_data_points', 1000)
            },
            'quality': {
                'min_completeness': crypto_data.get('quality', {}).get('min_completeness', 0.95),
                'max_gaps': crypto_data.get('quality', {}).get('max_gaps', 5),
                'outlier_detection': True,
                'data_validation': True
            },
            'caching': {
                'enabled': crypto_data.get('caching', {}).get('enabled', True),
                'ttl_minutes': crypto_data.get('caching', {}).get('ttl_minutes', 60),
                'max_cache_size': crypto_data.get('caching', {}).get('max_cache_size', 1000)
            }
        }
    
    def _validate_migrated_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validar configuración migrada"""
        validation = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        try:
            # Validar símbolos
            if not config.get('symbols'):
                validation['errors'].append("No hay símbolos configurados")
                validation['is_valid'] = False
            
            # Validar parámetros de riesgo
            risk_config = config.get('risk', {})
            if risk_config.get('max_drawdown', 0) > 0.2:
                validation['warnings'].append("Max drawdown muy alto para índices")
            
            if risk_config.get('risk_per_trade', 0) > 0.02:
                validation['warnings'].append("Riesgo por trade alto para índices")
            
            # Validar leverage
            trading_config = config.get('trading', {})
            if trading_config.get('leverage', 1) > 2:
                validation['warnings'].append("Leverage alto para índices")
            
            # Validar timeframes
            technical_config = config.get('technical', {})
            indicators = technical_config.get('indicators', {})
            
            rsi_period = indicators.get('rsi', {}).get('period', 14)
            if rsi_period < 10:
                validation['warnings'].append("Período RSI muy corto para índices")
            
            # Recomendaciones
            validation['recommendations'].extend([
                "Considerar usar solo horario regular de mercado",
                "Implementar filtros de días festivos",
                "Usar órdenes limit en lugar de market para mejor ejecución",
                "Considerar rebalanceo mensual del portfolio"
            ])
            
        except Exception as e:
            validation['errors'].append(f"Error en validación: {str(e)}")
            validation['is_valid'] = False
        
        return validation
    
    def _get_default_indices_config(self) -> Dict[str, Any]:
        """Obtener configuración por defecto para índices"""
        return {
            'migration_info': {
                'source': 'default',
                'target': 'indices',
                'migration_date': datetime.now().isoformat(),
                'version': '1.0'
            },
            'symbols': {
                'SPY': {
                    'symbol_type': 'ETF',
                    'market': 'US',
                    'currency': 'USD',
                    'active': True,
                    'weight': 1.0,
                    'min_position_size': 1,
                    'max_position_size': 100
                }
            },
            'trading': {
                'strategy': 'sicar_indices',
                'timeframe': '1d',
                'position_sizing': {
                    'method': 'fixed',
                    'base_size': 1000,
                    'max_size': 5000
                },
                'leverage': 1.0,
                'max_positions': 3
            },
            'risk': {
                'max_drawdown': 0.05,
                'risk_per_trade': 0.01,
                'stop_loss': {'type': 'percentage', 'value': 0.015},
                'take_profit': {'type': 'percentage', 'value': 0.03}
            },
            **self.indices_specific_config
        }
    
    def save_migrated_config(self, config: Dict[str, Any], filepath: str):
        """Guardar configuración migrada"""
        try:
            with open(filepath, 'w') as f:
                json.dump(config, f, indent=2)
            self.logger.info(f"Configuración migrada guardada en {filepath}")
        except Exception as e:
            self.logger.error(f"Error guardando configuración: {e}")
    
    def load_crypto_config(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Cargar configuración de crypto"""
        try:
            with open(filepath, 'r') as f:
                config = json.load(f)
            self.logger.info(f"Configuración crypto cargada desde {filepath}")
            return config
        except Exception as e:
            self.logger.error(f"Error cargando configuración crypto: {e}")
            return None
    
    def get_symbol_mapping(self) -> Dict[str, str]:
        """Obtener mapeo de símbolos"""
        return self.symbol_mapping.copy()
    
    def get_conversion_factors(self) -> Dict[str, float]:
        """Obtener factores de conversión"""
        return self.conversion_factors.copy()

# Función de utilidad para migración rápida
def quick_migrate(crypto_config_path: str, output_path: str) -> bool:
    """Migración rápida de configuración"""
    try:
        adapter = ConfigMigrationAdapter()
        
        # Cargar configuración crypto
        crypto_config = adapter.load_crypto_config(crypto_config_path)
        if not crypto_config:
            return False
        
        # Migrar configuración
        indices_config = adapter.migrate_config(crypto_config)
        
        # Guardar configuración migrada
        adapter.save_migrated_config(indices_config, output_path)
        
        return True
        
    except Exception as e:
        logger.error(f"Error en migración rápida: {e}")
        return False