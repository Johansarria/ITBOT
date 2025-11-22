"""
Configuración Mejorada para SICAR
Incluye todas las mejoras sugeridas en el análisis
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

class SicarConfig:
    """Configuración centralizada para el sistema SICAR"""
    
    # Directorios base
    BASE_DIR = Path(__file__).parent
    LOG_DIR = BASE_DIR / "logs"
    DATA_DIR = BASE_DIR / "data"
    CONFIG_FILE = BASE_DIR / "sicar_config.json"
    
    # 🤖 AUTO TRADING - ACTIVADO POR DEFECTO
    AUTO_TRADING_DEFAULT = True
    AUTO_TRADING_POSITION_SIZE_PCT = 0.05  # 5% del capital por trade
    AUTO_TRADING_MAX_POSITIONS = 3
    AUTO_TRADING_STOP_LOSS_PCT = 0.02  # 2%
    AUTO_TRADING_TAKE_PROFIT_PCT = 0.04  # 4%
    
    # 📝 LOGGING MEJORADO
    LOGGING_CONFIG = {
        'level': logging.INFO,
        'format': '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        'date_format': '%Y-%m-%d %H:%M:%S',
        'files': {
            'main': 'sicar_main.log',
            'trading': 'sicar_trading.log',
            'breakouts': 'sicar_breakouts.log',
            'sessions': 'sicar_sessions.log',
            'errors': 'sicar_errors.log'
        },
        'max_file_size': 10 * 1024 * 1024,  # 10MB
        'backup_count': 5
    }

    ENV = {
        'TRADING_MODE': os.getenv('TRADING_MODE', 'testnet').lower(),
        'PAPER_TRADING': os.getenv('PAPER_TRADING', 'true').lower() == 'true',
        'BINANCE_API_KEY': os.getenv('BINANCE_API_KEY', ''),
        'BINANCE_API_SECRET': os.getenv('BINANCE_API_SECRET', ''),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', ''),
        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY', ''),
        'ZAI_API_KEY': os.getenv('ZAI_API_KEY', ''),
        'ZAI_API_URL': os.getenv('ZAI_API_URL', 'https://api.z.ai/api/paas/v4'),
        'GROK_API_KEY': os.getenv('GROK_API_KEY', ''),
        'GROK_API_URL': os.getenv('GROK_API_URL', 'https://api.x.ai/v1'),
        'ALLOW_EXTERNAL_LLMS': os.getenv('ALLOW_EXTERNAL_LLMS', 'false').lower() == 'true',
        'LLM_FALLBACK_ORDER': os.getenv('LLM_FALLBACK_ORDER', 'openai,anthropic,zai,grok,local').split(',')
    }
    
    # 🔄 DASHBOARD-JSON SYNC
    DASHBOARD_SYNC = {
        'auto_sync_enabled': True,
        'sync_interval': 1.0,  # segundos
        'backup_enabled': True,
        'max_backups': 5,
        'backup_dir': 'session_backups',
        'session_file': 'paper_trading_session.json'
    }
    
    # Alias para compatibilidad
    SYNC_CONFIG = DASHBOARD_SYNC
    
    # 📊 ALERTAS DE BREAKOUTS
    BREAKOUT_ALERTS = {
        'enabled': True,
        'sound_alerts': True,
        'visual_alerts': True,
        'log_alerts': True,
        'alert_cooldown': 60,  # segundos entre alertas del mismo símbolo
        'min_confidence': 0.7,
        'alert_channels': ['console', 'file', 'gui']
    }
    
    # ⚡ SENSIBILIDAD DE BREAKOUTS
    BREAKOUT_SENSITIVITY = {
        'volume_threshold_multiplier': 1.5,
        'price_movement_threshold': 0.005,  # 0.5%
        'confirmation_candles': 2,
        'lookback_periods': 20,
        'volatility_adjustment': True,
        'session_specific_thresholds': {
            'asian': {'volume_mult': 1.2, 'price_thresh': 0.003},
            'european': {'volume_mult': 1.5, 'price_thresh': 0.005},
            'american': {'volume_mult': 2.0, 'price_thresh': 0.007}
        }
    }
    
    # 🔍 DETECCIÓN DE BREAKOUTS
    BREAKOUT_DETECTION = {
        'sensitivity': 0.5,  # Sensibilidad general (reducida para mayor detección)
        'min_volume_ratio': 1.2,  # Ratio mínimo de volumen (reducido)
        'min_price_change_pct': 0.3,  # 0.3% cambio mínimo de precio (más realista)
        'symbols_to_monitor': ['ETHUSDT', 'BTCUSDT', 'ADAUSDT'],
        'detection_interval': 30,  # segundos entre detecciones
        'lookback_periods': 15,  # Períodos reducidos para mayor sensibilidad
        'confirmation_candles': 2,
        'min_signal_interval': 15,  # Intervalo mínimo entre señales (segundos)
        
        # 🚨 CONFIGURACIÓN ULTRA-SENSIBLE PARA VENTANAS DE SESIÓN
        'session_window_config': {
            'sensitivity': 0.1,  # Extremadamente sensible
            'min_volume_ratio': 1.05,  # Casi cualquier aumento de volumen
            'min_price_change_pct': 0.1,  # Solo 0.1% de cambio mínimo
            'lookback_periods': 5,  # Períodos muy cortos
            'confirmation_candles': 1,  # Sin confirmación adicional
            'force_detection': True,  # Forzar detección si no hay breakout natural
            'detection_interval': 30,  # Detección cada 30 segundos
            'min_confidence_threshold': 30,  # Umbral de confianza muy bajo
            'min_signal_interval': 5  # Intervalo mínimo entre señales durante ventanas (segundos)
        }
    }
    
    # 🌐 SESIONES DE TRADING
    SESSIONS_CONFIG = {
        'asian': {
            'name': 'Sesión Asiática',
            'start_time': '19:00',
            'end_time': '19:05',
            'timezone': 'US/Eastern',
            'active': True,
            'symbols': ['ETHUSDT'],
            'description': 'Sesión de trading asiática - ETH breakouts'
        },
        'european': {
            'name': 'Sesión Europea',
            'start_time': '03:00',
            'end_time': '03:05',
            'timezone': 'US/Eastern',
            'active': True,
            'symbols': ['ETHUSDT'],
            'description': 'Sesión de trading europea - ETH breakouts'
        },
        'american': {
            'name': 'Sesión Americana',
            'start_time': '09:30',
            'end_time': '09:35',
            'timezone': 'US/Eastern',
            'active': True,
            'symbols': ['ETHUSDT'],
            'description': 'Sesión de trading americana - ETH breakouts'
        }
    }
    
    # ⚡ SCALPING AUTOMÁTICO - NUEVO MÓDULO
    SCALPING_CONFIG = {
        'enabled': True,  # HABILITADO POR DEFECTO
        'operation_duration_minutes': 5,  # Duración de cada operación
        'min_confidence_threshold': 0.5,  # Confianza mínima para activar scalping
        'max_confidence_threshold': 85.0,  # Confianza máxima para scalping (evitar sobrecompra)
        'take_profit_pct': 0.8,  # 0.8% take profit
        'stop_loss_pct': 0.4,  # 0.4% stop loss
        'position_size_pct': 0.15,  # 15% del capital por operación
        'max_concurrent_positions': 2,  # Máximo 2 posiciones simultáneas
        'cooldown_minutes': 10,  # Tiempo de espera entre operaciones del mismo símbolo
        'symbols_allowed': ['ETHUSDT', 'BTCUSDT', 'ADAUSDT'],
        'volume_confirmation_required': True,
        'min_volume_ratio': 1.3,  # Confirmación de volumen
        'exclude_session_windows': False,  # Si operar también durante ventanas críticas
        'auto_close_on_session': True,  # Cerrar posiciones antes de ventanas críticas
        'session_buffer_minutes': 2,  # Minutos antes de sesión para cerrar posiciones
        'profit_scaling': {  # Escalado de ganancias según confianza
            'enabled': True,
            'min_profit_pct': 0.5,  # Ganancia mínima con baja confianza
            'max_profit_pct': 1.2   # Ganancia máxima con alta confianza
        },
        'risk_management': {
            'max_daily_loss_pct': 2.0,  # Máximo 2% pérdida diaria
            'max_consecutive_losses': 3,  # Parar después de 3 pérdidas consecutivas
            'recovery_mode_enabled': True,  # Modo recuperación con posiciones más pequeñas
            'recovery_position_size_pct': 0.08  # 8% en modo recuperación
        }
    }

    # 💰 PAPER TRADING
    PAPER_TRADING_CONFIG = {
        'initial_capital': 200.0,      # Base real de $200
        'commission_rate': 0.001,
        'slippage_base': 0.0005,
        'max_position_size_pct': 0.3,  # 30% máximo por posición (como Swing Trading exitoso)
        'risk_per_trade_pct': 0.05,    # 5% riesgo por trade (más agresivo para 4-5% mensual)
        'auto_save_trades': True
    }
    
    # 🔧 PATHS Y ARCHIVOS
    PATHS = {
        'logs_dir': 'logs',
        'data_dir': 'data',
        'backups_dir': 'backups',
        'reports_dir': 'reports'
    }
    
    # 📁 FILE PATHS
    FILE_PATHS = {
        'paper_trading_session': 'data/paper_trading_session.json',
        'trades_log': 'data/trades_detailed.log',
        'config_file': 'config.json'
    }
    
    @classmethod
    def ensure_directories(cls):
        """Asegurar que existan los directorios necesarios"""
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Crear directorio de backups de sesión
        backup_dir = cls.BASE_DIR / cls.SYNC_CONFIG['backup_dir']
        backup_dir.mkdir(parents=True, exist_ok=True)
    

    
    @classmethod
    def get_session_file_path(cls) -> str:
        """Obtener ruta completa del archivo de sesión"""
        return cls.SYNC_CONFIG['session_file']

    @classmethod
    def safe_runtime_modes(cls) -> Dict[str, Any]:
        binance_ready = bool(cls.ENV['BINANCE_API_KEY']) and bool(cls.ENV['BINANCE_API_SECRET'])
        trading_mode = cls.ENV['TRADING_MODE'] if binance_ready else 'testnet'
        paper_trading = cls.ENV['PAPER_TRADING'] if binance_ready else True
        return {'trading_mode': trading_mode, 'paper_trading': paper_trading}

    @classmethod
    def is_live_trading_allowed(cls) -> bool:
        allow_flag = os.getenv('ALLOW_LIVE_TRADING', 'false').lower() == 'true'
        creds_ok = bool(cls.ENV['BINANCE_API_KEY']) and bool(cls.ENV['BINANCE_API_SECRET'])
        return cls.ENV['TRADING_MODE'] == 'live' and not cls.ENV['PAPER_TRADING'] and allow_flag and creds_ok
    
    @classmethod
    def get_log_file_path(cls, log_type: str) -> str:
        """Obtener ruta completa de un archivo de log"""
        filename = cls.LOGGING_CONFIG['files'].get(log_type, f'sicar_{log_type}.log')
        return str(cls.LOG_DIR / filename)
    
    @classmethod
    def create_default_session_file(cls):
        """Crear archivo de sesión por defecto con auto trading activado"""
        import json
        
        default_session = {
            "timestamp": datetime.now().isoformat(),
            "capital": cls.PAPER_TRADING_CONFIG['initial_capital'],
            "positions": 0,
            "total_trades": 0,
            "auto_trading": cls.AUTO_TRADING_DEFAULT,  # ✅ ACTIVADO POR DEFECTO
            "session_config": {
                "position_size_pct": cls.AUTO_TRADING_POSITION_SIZE_PCT,
                "max_positions": cls.AUTO_TRADING_MAX_POSITIONS,
                "stop_loss_pct": cls.AUTO_TRADING_STOP_LOSS_PCT,
                "take_profit_pct": cls.AUTO_TRADING_TAKE_PROFIT_PCT
            },
            "created_at": datetime.now().isoformat(),
            "version": "2.0_enhanced"
        }
        
        session_file = cls.get_session_file_path()
        with open(session_file, 'w') as f:
            json.dump(default_session, f, indent=2)
        
        return default_session

    @classmethod
    def save_config_to_file(cls):
        """Guardar configuración actual en archivo JSON"""
        try:
            config_data = {
                'AUTO_TRADING_DEFAULT': cls.AUTO_TRADING_DEFAULT,
                'BREAKOUT_DETECTION': cls.BREAKOUT_DETECTION.copy(),
                'SYNC_CONFIG': cls.SYNC_CONFIG.copy(),
                'PAPER_TRADING_CONFIG': cls.PAPER_TRADING_CONFIG.copy(),
                'last_updated': datetime.now().isoformat()
            }
            
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error guardando configuración: {e}")
            return False
    
    @classmethod
    def load_config_from_file(cls):
        """Cargar configuración desde archivo JSON"""
        try:
            if not cls.CONFIG_FILE.exists():
                # Si no existe el archivo, crear uno con valores por defecto
                cls.save_config_to_file()
                return True
            
            with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Actualizar configuración en memoria
            if 'AUTO_TRADING_DEFAULT' in config_data:
                cls.AUTO_TRADING_DEFAULT = config_data['AUTO_TRADING_DEFAULT']
            
            if 'BREAKOUT_DETECTION' in config_data:
                cls.BREAKOUT_DETECTION.update(config_data['BREAKOUT_DETECTION'])
            
            if 'SYNC_CONFIG' in config_data:
                cls.SYNC_CONFIG.update(config_data['SYNC_CONFIG'])
            
            if 'PAPER_TRADING_CONFIG' in config_data:
                cls.PAPER_TRADING_CONFIG.update(config_data['PAPER_TRADING_CONFIG'])
            
            return True
        except Exception as e:
            print(f"Error cargando configuración: {e}")
            return False

# Configuración global
CONFIG = SicarConfig()
