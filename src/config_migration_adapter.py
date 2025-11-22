#!/usr/bin/env python3
"""
SICAR Configuration Migration Adapter
Adaptador para migrar configuraciones de crypto a índices
Mantiene compatibilidad con el sistema SICAR existente
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import copy
import warnings
warnings.filterwarnings('ignore')

from indices_config import IndicesConfigManager, IndexSpecificConfig
from indices_parameters_calibrator import IndicesParametersCalibrator

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfigMigrationAdapter:
    """
    Adaptador para migrar configuraciones de crypto a índices
    
    Funcionalidades:
    - Mapeo de símbolos crypto a índices
    - Adaptación de parámetros técnicos
    - Migración de configuraciones de trading
    - Mantenimiento de compatibilidad SICAR
    """
    
    def __init__(self):
        """Inicializar el adaptador de migración"""
        self.indices_config = IndicesConfigManager()
        self.calibrator = IndicesParametersCalibrator()
        
        # Mapeo de símbolos crypto a índices
        self.symbol_mapping = {
            # Crypto principales -> Índices principales
            'BTCUSDT': 'SPY',    # Bitcoin -> S&P 500
            'ETHUSDT': 'QQQ',    # Ethereum -> NASDAQ 100
            'ADAUSDT': 'IWM',    # Cardano -> Russell 2000
            'BNBUSDT': 'DIA',    # Binance Coin -> Dow Jones
            'XRPUSDT': 'SPY',    # Ripple -> S&P 500
            'SOLUSDT': 'QQQ',    # Solana -> NASDAQ 100
            'DOTUSDT': 'IWM',    # Polkadot -> Russell 2000
            'AVAXUSDT': 'QQQ',   # Avalanche -> NASDAQ 100
            'MATICUSDT': 'IWM',  # Polygon -> Russell 2000
            'LINKUSDT': 'SPY',   # Chainlink -> S&P 500
            
            # Crypto adicionales
            'LTCUSDT': 'SPY',    # Litecoin -> S&P 500
            'UNIUSDT': 'QQQ',    # Uniswap -> NASDAQ 100
            'ATOMUSDT': 'IWM',   # Cosmos -> Russell 2000
            'FILUSDT': 'SPY',    # Filecoin -> S&P 500
            'TRXUSDT': 'DIA',    # Tron -> Dow Jones
        }
        
        # Mapeo inverso (índices a crypto para referencia)
        self.reverse_mapping = {v: k for k, v in self.symbol_mapping.items()}
        
        # Factores de conversión para diferentes parámetros
        self.conversion_factors = {
            'timeframes': {
                # Crypto opera 24/7, índices solo horario de mercado
                'multiplier': 0.33,  # Reducir timeframes por menor tiempo de trading
                'min_value': 5,      # Mínimo 5 períodos
                'max_value': 200     # Máximo 200 períodos
            },
            'volatility': {
                # Índices menos volátiles que crypto
                'multiplier': 0.4,   # Reducir thresholds de volatilidad
                'min_value': 0.005,  # Mínimo 0.5%
                'max_value': 0.05    # Máximo 5%
            },
            'volume': {
                # Volúmenes diferentes entre crypto e índices
                'multiplier': 1.5,   # Aumentar thresholds de volumen
                'min_value': 100000, # Mínimo volumen
                'max_value': None    # Sin máximo
            },
            'risk': {
                # Ajustar parámetros de riesgo
                'multiplier': 0.7,   # Reducir riesgo para índices
                'min_value': 0.001,  # Mínimo 0.1%
                'max_value': 0.03    # Máximo 3%
            },
            'position_size': {
                # Tamaños de posición
                'multiplier': 1.2,   # Aumentar ligeramente para índices
                'min_value': 0.01,   # Mínimo 1%
                'max_value': 0.25    # Máximo 25%
            }
        }
        
        # Configuraciones específicas por tipo de índice
        self.index_specific_adjustments = {
            'SPY': {  # S&P 500 - Más estable
                'volatility_multiplier': 0.8,
                'timeframe_multiplier': 1.2,
                'risk_multiplier': 0.9
            },
            'QQQ': {  # NASDAQ 100 - Más volátil (tech)
                'volatility_multiplier': 1.1,
                'timeframe_multiplier': 0.9,
                'risk_multiplier': 1.1
            },
            'DIA': {  # Dow Jones - Muy estable
                'volatility_multiplier': 0.7,
                'timeframe_multiplier': 1.3,
                'risk_multiplier': 0.8
            },
            'IWM': {  # Russell 2000 - Más volátil (small caps)
                'volatility_multiplier': 1.2,
                'timeframe_multiplier': 0.8,
                'risk_multiplier': 1.2
            }
        }
        
        logger.info("🔄 Adaptador de migración de configuración inicializado")
    
    def migrate_crypto_config_to_indices(self, crypto_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrar configuración completa de crypto a índices
        
        Args:
            crypto_config: Configuración original de crypto
            
        Returns:
            Configuración adaptada para índices
        """
        try:
            logger.info("🔄 Iniciando migración de configuración crypto -> índices")
            
            # Crear copia de la configuración
            indices_config = copy.deepcopy(crypto_config)
            
            # 1. Migrar símbolos
            indices_config = self._migrate_symbols(indices_config)
            
            # 2. Migrar parámetros técnicos
            indices_config = self._migrate_technical_parameters(indices_config)
            
            # 3. Migrar configuraciones de trading
            indices_config = self._migrate_trading_config(indices_config)
            
            # 4. Migrar configuraciones de riesgo
            indices_config = self._migrate_risk_config(indices_config)
            
            # 5. Añadir configuraciones específicas de índices
            indices_config = self._add_indices_specific_config(indices_config)
            
            # 6. Validar configuración migrada
            validation_result = self._validate_migrated_config(indices_config)
            
            if validation_result['valid']:
                logger.info("✅ Migración de configuración completada exitosamente")
                indices_config['migration_info'] = {
                    'migrated_at': datetime.now().isoformat(),
                    'source_type': 'crypto',
                    'target_type': 'indices',
                    'validation_passed': True,
                    'symbols_migrated': len(indices_config.get('symbols', [])),
                    'parameters_migrated': len(indices_config.get('technical_parameters', {}))
                }
            else:
                logger.warning(f"⚠️ Migración completada con advertencias: {validation_result['warnings']}")
                indices_config['migration_info'] = {
                    'migrated_at': datetime.now().isoformat(),
                    'source_type': 'crypto',
                    'target_type': 'indices',
                    'validation_passed': False,
                    'warnings': validation_result['warnings']
                }
            
            return indices_config
            
        except Exception as e:
            logger.error(f"❌ Error en migración de configuración: {e}")
            raise
    
    def _migrate_symbols(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrar símbolos de crypto a índices"""
        try:
            if 'symbols' in config:
                migrated_symbols = []
                
                for crypto_symbol in config['symbols']:
                    if crypto_symbol in self.symbol_mapping:
                        index_symbol = self.symbol_mapping[crypto_symbol]
                        migrated_symbols.append(index_symbol)
                        logger.info(f"🔄 Símbolo migrado: {crypto_symbol} -> {index_symbol}")
                    else:
                        # Si no hay mapeo directo, usar SPY como default
                        migrated_symbols.append('SPY')
                        logger.warning(f"⚠️ Símbolo sin mapeo directo: {crypto_symbol} -> SPY (default)")
                
                # Eliminar duplicados manteniendo orden
                config['symbols'] = list(dict.fromkeys(migrated_symbols))
                
                # Guardar mapeo original para referencia
                config['original_crypto_symbols'] = config.get('symbols', [])
            
            return config
            
        except Exception as e:
            logger.error(f"Error migrando símbolos: {e}")
            return config
    
    def _migrate_technical_parameters(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrar parámetros técnicos"""
        try:
            if 'technical_parameters' not in config:
                config['technical_parameters'] = {}
            
            tech_params = config['technical_parameters']
            
            # Migrar timeframes
            if 'timeframes' in tech_params:
                tech_params['timeframes'] = self._convert_parameter_values(
                    tech_params['timeframes'], 'timeframes'
                )
            
            # Migrar parámetros de volatilidad
            if 'volatility' in tech_params:
                tech_params['volatility'] = self._convert_parameter_values(
                    tech_params['volatility'], 'volatility'
                )
            
            # Migrar parámetros de volumen
            if 'volume' in tech_params:
                tech_params['volume'] = self._convert_parameter_values(
                    tech_params['volume'], 'volume'
                )
            
            # Migrar indicadores técnicos
            if 'indicators' in tech_params:
                tech_params['indicators'] = self._migrate_indicators(tech_params['indicators'])
            
            # Añadir parámetros específicos de índices
            tech_params['market_hours_filter'] = True
            tech_params['session_based_parameters'] = True
            tech_params['earnings_season_adjustment'] = True
            
            return config
            
        except Exception as e:
            logger.error(f"Error migrando parámetros técnicos: {e}")
            return config
    
    def _migrate_trading_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrar configuraciones de trading"""
        try:
            if 'trading' not in config:
                config['trading'] = {}
            
            trading_config = config['trading']
            
            # Migrar intervalos de trading
            if 'intervals' in trading_config:
                # Crypto: ['1m', '5m', '15m', '1h', '4h', '1d']
                # Índices: ['1m', '5m', '15m', '1h', '1d'] (sin 4h por horarios de mercado)
                crypto_intervals = trading_config['intervals']
                indices_intervals = []
                
                for interval in crypto_intervals:
                    if interval in ['1m', '5m', '15m', '30m', '1h', '1d']:
                        indices_intervals.append(interval)
                    elif interval == '4h':
                        # 4h no es útil para índices, usar 1h
                        if '1h' not in indices_intervals:
                            indices_intervals.append('1h')
                
                trading_config['intervals'] = indices_intervals
            
            # Migrar horarios de trading
            trading_config['market_hours_only'] = True
            trading_config['pre_market_trading'] = True
            trading_config['after_hours_trading'] = False  # Más conservador para índices
            
            # Migrar configuración de posiciones
            if 'position_sizing' in trading_config:
                trading_config['position_sizing'] = self._convert_parameter_values(
                    trading_config['position_sizing'], 'position_size'
                )
            
            # Añadir configuraciones específicas de índices
            trading_config['earnings_season_filter'] = True
            trading_config['holiday_filter'] = True
            trading_config['options_expiration_filter'] = True
            
            return config
            
        except Exception as e:
            logger.error(f"Error migrando configuración de trading: {e}")
            return config
    
    def _migrate_risk_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrar configuraciones de riesgo"""
        try:
            if 'risk_management' not in config:
                config['risk_management'] = {}
            
            risk_config = config['risk_management']
            
            # Migrar parámetros de riesgo
            risk_params = ['max_drawdown', 'stop_loss', 'take_profit', 'risk_per_trade']
            
            for param in risk_params:
                if param in risk_config:
                    risk_config[param] = self._convert_parameter_values(
                        risk_config[param], 'risk'
                    )
            
            # Ajustar para características de índices
            if 'max_drawdown' in risk_config:
                # Índices más estables, permitir drawdown ligeramente mayor
                if isinstance(risk_config['max_drawdown'], (int, float)):
                    risk_config['max_drawdown'] = min(risk_config['max_drawdown'] * 1.2, 0.15)
            
            if 'volatility_filter' in risk_config:
                # Ajustar filtros de volatilidad para índices
                risk_config['volatility_filter'] = self._convert_parameter_values(
                    risk_config['volatility_filter'], 'volatility'
                )
            
            # Añadir gestión de riesgo específica para índices
            risk_config['sector_concentration_limit'] = 0.4  # Máximo 40% en un sector
            risk_config['correlation_limit'] = 0.8  # Máximo correlación entre posiciones
            risk_config['market_regime_adjustment'] = True
            
            return config
            
        except Exception as e:
            logger.error(f"Error migrando configuración de riesgo: {e}")
            return config
    
    def _add_indices_specific_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Añadir configuraciones específicas de índices"""
        try:
            # Configuración de fuentes de datos
            config['data_sources'] = {
                'primary': 'yahoo_finance',
                'secondary': 'iex',
                'fallback': 'alpha_vantage',
                'real_time': False,  # Usar datos delayed para índices
                'update_frequency': '1min'
            }
            
            # Configuración de horarios de mercado
            config['market_hours'] = {
                'timezone': 'US/Eastern',
                'regular_hours': {
                    'start': '09:30',
                    'end': '16:00'
                },
                'extended_hours': {
                    'pre_market_start': '04:00',
                    'after_hours_end': '20:00'
                },
                'trading_days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
            }
            
            # Configuración de filtros específicos
            config['indices_filters'] = {
                'earnings_season': True,
                'options_expiration': True,
                'dividend_dates': True,
                'economic_events': True,
                'market_holidays': True
            }
            
            # Configuración de benchmarks
            config['benchmarks'] = {
                'SPY': 'SPY',  # S&P 500 como benchmark principal
                'QQQ': 'QQQ',  # NASDAQ 100
                'DIA': 'DIA',  # Dow Jones
                'IWM': 'IWM'   # Russell 2000
            }
            
            return config
            
        except Exception as e:
            logger.error(f"Error añadiendo configuración específica de índices: {e}")
            return config
    
    def _convert_parameter_values(self, param_value: Any, param_type: str) -> Any:
        """Convertir valores de parámetros según factores de conversión"""
        try:
            if param_type not in self.conversion_factors:
                return param_value
            
            factors = self.conversion_factors[param_type]
            multiplier = factors['multiplier']
            min_val = factors['min_value']
            max_val = factors['max_value']
            
            if isinstance(param_value, (int, float)):
                # Valor numérico simple
                converted = param_value * multiplier
                
                if min_val is not None:
                    converted = max(converted, min_val)
                if max_val is not None:
                    converted = min(converted, max_val)
                
                return converted
            
            elif isinstance(param_value, dict):
                # Diccionario de parámetros
                converted_dict = {}
                for key, value in param_value.items():
                    if isinstance(value, (int, float)):
                        converted = value * multiplier
                        
                        if min_val is not None:
                            converted = max(converted, min_val)
                        if max_val is not None:
                            converted = min(converted, max_val)
                        
                        converted_dict[key] = converted
                    else:
                        converted_dict[key] = value
                
                return converted_dict
            
            elif isinstance(param_value, list):
                # Lista de valores
                converted_list = []
                for value in param_value:
                    if isinstance(value, (int, float)):
                        converted = value * multiplier
                        
                        if min_val is not None:
                            converted = max(converted, min_val)
                        if max_val is not None:
                            converted = min(converted, max_val)
                        
                        converted_list.append(converted)
                    else:
                        converted_list.append(value)
                
                return converted_list
            
            else:
                # Tipo no soportado, devolver original
                return param_value
                
        except Exception as e:
            logger.error(f"Error convirtiendo parámetro {param_type}: {e}")
            return param_value
    
    def _migrate_indicators(self, indicators_config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrar configuración de indicadores técnicos"""
        try:
            migrated_indicators = copy.deepcopy(indicators_config)
            
            # Ajustar períodos de indicadores para índices
            indicator_adjustments = {
                'sma': {'period_multiplier': 0.8},      # Períodos más cortos
                'ema': {'period_multiplier': 0.8},
                'rsi': {'period_multiplier': 1.0},      # RSI mantener igual
                'macd': {'period_multiplier': 0.9},
                'bollinger': {'period_multiplier': 0.8},
                'atr': {'period_multiplier': 1.1},      # ATR período ligeramente mayor
                'stochastic': {'period_multiplier': 0.9}
            }
            
            for indicator, config in migrated_indicators.items():
                if indicator in indicator_adjustments:
                    adjustment = indicator_adjustments[indicator]
                    
                    if isinstance(config, dict):
                        for param, value in config.items():
                            if 'period' in param.lower() and isinstance(value, (int, float)):
                                config[param] = max(int(value * adjustment['period_multiplier']), 2)
            
            return migrated_indicators
            
        except Exception as e:
            logger.error(f"Error migrando indicadores: {e}")
            return indicators_config
    
    def _validate_migrated_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validar configuración migrada"""
        try:
            validation_result = {
                'valid': True,
                'warnings': [],
                'errors': []
            }
            
            # Validar símbolos
            if 'symbols' not in config or not config['symbols']:
                validation_result['errors'].append("No hay símbolos configurados")
                validation_result['valid'] = False
            
            # Validar que los símbolos son índices válidos
            valid_indices = ['SPY', 'QQQ', 'DIA', 'IWM']
            for symbol in config.get('symbols', []):
                if symbol not in valid_indices:
                    validation_result['warnings'].append(f"Símbolo {symbol} no es un índice estándar")
            
            # Validar parámetros técnicos
            if 'technical_parameters' in config:
                tech_params = config['technical_parameters']
                
                # Validar timeframes
                if 'timeframes' in tech_params:
                    for tf_name, tf_value in tech_params['timeframes'].items():
                        if isinstance(tf_value, (int, float)) and tf_value < 2:
                            validation_result['warnings'].append(f"Timeframe {tf_name} muy pequeño: {tf_value}")
            
            # Validar configuración de trading
            if 'trading' in config:
                trading_config = config['trading']
                
                # Validar intervalos
                if 'intervals' in trading_config:
                    valid_intervals = ['1m', '5m', '15m', '30m', '1h', '1d']
                    for interval in trading_config['intervals']:
                        if interval not in valid_intervals:
                            validation_result['warnings'].append(f"Intervalo {interval} no recomendado para índices")
            
            # Validar gestión de riesgo
            if 'risk_management' in config:
                risk_config = config['risk_management']
                
                if 'max_drawdown' in risk_config:
                    max_dd = risk_config['max_drawdown']
                    if isinstance(max_dd, (int, float)) and max_dd > 0.2:
                        validation_result['warnings'].append(f"Max drawdown muy alto para índices: {max_dd}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validando configuración migrada: {e}")
            return {
                'valid': False,
                'warnings': [],
                'errors': [f"Error en validación: {str(e)}"]
            }
    
    def create_indices_config_from_crypto(self, crypto_symbols: List[str], 
                                        crypto_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Crear configuración de índices desde símbolos crypto
        
        Args:
            crypto_symbols: Lista de símbolos crypto
            crypto_config: Configuración crypto opcional
            
        Returns:
            Configuración completa para índices
        """
        try:
            # Configuración base si no se proporciona
            if crypto_config is None:
                crypto_config = {
                    'symbols': crypto_symbols,
                    'technical_parameters': {},
                    'trading': {},
                    'risk_management': {}
                }
            else:
                crypto_config['symbols'] = crypto_symbols
            
            # Migrar configuración completa
            indices_config = self.migrate_crypto_config_to_indices(crypto_config)
            
            # Añadir configuraciones por defecto específicas
            indices_config.update({
                'system_type': 'indices',
                'created_at': datetime.now().isoformat(),
                'version': '1.0.0',
                'description': 'Configuración migrada de crypto a índices'
            })
            
            return indices_config
            
        except Exception as e:
            logger.error(f"Error creando configuración de índices: {e}")
            raise
    
    def get_symbol_mapping(self, crypto_symbol: str) -> str:
        """Obtener mapeo de símbolo crypto a índice"""
        return self.symbol_mapping.get(crypto_symbol, 'SPY')
    
    def get_reverse_mapping(self, index_symbol: str) -> str:
        """Obtener mapeo de índice a crypto (para referencia)"""
        return self.reverse_mapping.get(index_symbol, 'BTCUSDT')
    
    def save_migrated_config(self, config: Dict[str, Any], filename: str = None) -> str:
        """Guardar configuración migrada"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"indices_config_migrated_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(config, f, indent=2, default=str)
            
            logger.info(f"💾 Configuración migrada guardada en: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error guardando configuración: {e}")
            raise

# Función de utilidad global
def migrate_crypto_to_indices_config(crypto_config: Dict[str, Any]) -> Dict[str, Any]:
    """Función de utilidad para migrar configuración"""
    adapter = ConfigMigrationAdapter()
    return adapter.migrate_crypto_config_to_indices(crypto_config)

if __name__ == "__main__":
    # Test del adaptador de migración
    print("🧪 Testing Configuration Migration Adapter...")
    
    adapter = ConfigMigrationAdapter()
    
    # Configuración crypto de ejemplo
    crypto_config = {
        'symbols': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT'],
        'technical_parameters': {
            'timeframes': {
                'fast_ma': 10,
                'slow_ma': 30,
                'rsi_period': 14
            },
            'volatility': {
                'threshold': 0.05,
                'lookback': 20
            }
        },
        'trading': {
            'intervals': ['1m', '5m', '15m', '1h', '4h', '1d'],
            'position_sizing': {
                'max_position': 0.1,
                'risk_per_trade': 0.02
            }
        },
        'risk_management': {
            'max_drawdown': 0.1,
            'stop_loss': 0.03,
            'take_profit': 0.06
        }
    }
    
    # Migrar configuración
    indices_config = adapter.migrate_crypto_config_to_indices(crypto_config)
    
    print(f"📊 Símbolos migrados: {indices_config['symbols']}")
    print(f"⚙️ Parámetros técnicos: {len(indices_config['technical_parameters'])} categorías")
    print(f"🔄 Trading config: {len(indices_config['trading'])} parámetros")
    print(f"🛡️ Risk management: {len(indices_config['risk_management'])} parámetros")
    
    if 'migration_info' in indices_config:
        migration_info = indices_config['migration_info']
        print(f"✅ Migración exitosa: {migration_info['validation_passed']}")
        print(f"📈 Símbolos migrados: {migration_info['symbols_migrated']}")
    
    print("\n🏁 Test completado")