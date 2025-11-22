#!/usr/bin/env python3
"""
SICAR US Market Filters
Sistema de filtros específicos para horarios de mercado US
Integra con el sistema de horarios existente y proporciona filtros avanzados
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple, Any, Union
import pytz
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

from market_hours_system import MarketHoursSystem, MarketSession, MarketStatus
from indices_config import IndicesConfigManager

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingSession(Enum):
    """Sesiones de trading específicas"""
    PRE_MARKET_EARLY = "pre_market_early"      # 4:00-6:30 AM ET
    PRE_MARKET_ACTIVE = "pre_market_active"    # 6:30-9:30 AM ET
    MARKET_OPEN = "market_open"                # 9:30-10:00 AM ET
    MORNING_SESSION = "morning_session"        # 10:00-12:00 PM ET
    LUNCH_SESSION = "lunch_session"            # 12:00-2:00 PM ET
    AFTERNOON_SESSION = "afternoon_session"    # 2:00-3:30 PM ET
    MARKET_CLOSE = "market_close"              # 3:30-4:00 PM ET
    AFTER_HOURS_EARLY = "after_hours_early"   # 4:00-6:00 PM ET
    AFTER_HOURS_LATE = "after_hours_late"     # 6:00-8:00 PM ET
    OVERNIGHT = "overnight"                    # 8:00 PM - 4:00 AM ET

class MarketCondition(Enum):
    """Condiciones de mercado"""
    HIGH_VOLUME = "high_volume"
    LOW_VOLUME = "low_volume"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    TRENDING = "trending"
    RANGING = "ranging"
    NEWS_EVENT = "news_event"
    EARNINGS_SEASON = "earnings_season"
    HOLIDAY_WEEK = "holiday_week"
    MONTH_END = "month_end"
    QUARTER_END = "quarter_end"

class USMarketFilters:
    """
    Sistema de filtros específicos para mercado US
    
    Proporciona filtros avanzados para:
    - Horarios de trading específicos
    - Condiciones de mercado
    - Eventos especiales
    - Volatilidad por sesión
    - Volumen por sesión
    """
    
    def __init__(self):
        """Inicializar el sistema de filtros"""
        self.market_hours = MarketHoursSystem()
        self.config_manager = IndicesConfigManager()
        
        # Zona horaria del mercado US
        self.market_tz = pytz.timezone('US/Eastern')
        
        # Definir horarios de sesiones específicas (ET)
        self.session_times = {
            TradingSession.PRE_MARKET_EARLY: (time(4, 0), time(6, 30)),
            TradingSession.PRE_MARKET_ACTIVE: (time(6, 30), time(9, 30)),
            TradingSession.MARKET_OPEN: (time(9, 30), time(10, 0)),
            TradingSession.MORNING_SESSION: (time(10, 0), time(12, 0)),
            TradingSession.LUNCH_SESSION: (time(12, 0), time(14, 0)),
            TradingSession.AFTERNOON_SESSION: (time(14, 0), time(15, 30)),
            TradingSession.MARKET_CLOSE: (time(15, 30), time(16, 0)),
            TradingSession.AFTER_HOURS_EARLY: (time(16, 0), time(18, 0)),
            TradingSession.AFTER_HOURS_LATE: (time(18, 0), time(20, 0)),
            TradingSession.OVERNIGHT: (time(20, 0), time(4, 0))  # Cruza medianoche
        }
        
        # Configuración de filtros por sesión
        self.session_filters = {
            TradingSession.PRE_MARKET_EARLY: {
                'min_volume_multiplier': 0.1,    # 10% del volumen normal
                'max_spread_multiplier': 3.0,    # Máximo 3x spread normal
                'volatility_threshold': 0.02,    # 2% volatilidad máxima
                'allow_new_positions': False,    # No abrir nuevas posiciones
                'allow_close_positions': True    # Permitir cerrar posiciones
            },
            TradingSession.PRE_MARKET_ACTIVE: {
                'min_volume_multiplier': 0.3,
                'max_spread_multiplier': 2.0,
                'volatility_threshold': 0.03,
                'allow_new_positions': True,
                'allow_close_positions': True
            },
            TradingSession.MARKET_OPEN: {
                'min_volume_multiplier': 2.0,    # Alta actividad en apertura
                'max_spread_multiplier': 1.5,
                'volatility_threshold': 0.05,    # Mayor volatilidad permitida
                'allow_new_positions': True,
                'allow_close_positions': True
            },
            TradingSession.MORNING_SESSION: {
                'min_volume_multiplier': 1.0,
                'max_spread_multiplier': 1.2,
                'volatility_threshold': 0.03,
                'allow_new_positions': True,
                'allow_close_positions': True
            },
            TradingSession.LUNCH_SESSION: {
                'min_volume_multiplier': 0.6,    # Menor actividad en almuerzo
                'max_spread_multiplier': 1.5,
                'volatility_threshold': 0.02,
                'allow_new_positions': False,    # Evitar trading en almuerzo
                'allow_close_positions': True
            },
            TradingSession.AFTERNOON_SESSION: {
                'min_volume_multiplier': 1.2,
                'max_spread_multiplier': 1.2,
                'volatility_threshold': 0.03,
                'allow_new_positions': True,
                'allow_close_positions': True
            },
            TradingSession.MARKET_CLOSE: {
                'min_volume_multiplier': 1.5,    # Alta actividad en cierre
                'max_spread_multiplier': 1.3,
                'volatility_threshold': 0.04,
                'allow_new_positions': False,    # No abrir cerca del cierre
                'allow_close_positions': True
            },
            TradingSession.AFTER_HOURS_EARLY: {
                'min_volume_multiplier': 0.2,
                'max_spread_multiplier': 2.5,
                'volatility_threshold': 0.02,
                'allow_new_positions': False,
                'allow_close_positions': True
            },
            TradingSession.AFTER_HOURS_LATE: {
                'min_volume_multiplier': 0.1,
                'max_spread_multiplier': 4.0,
                'volatility_threshold': 0.015,
                'allow_new_positions': False,
                'allow_close_positions': False   # Evitar trading muy tarde
            },
            TradingSession.OVERNIGHT: {
                'min_volume_multiplier': 0.05,
                'max_spread_multiplier': 5.0,
                'volatility_threshold': 0.01,
                'allow_new_positions': False,
                'allow_close_positions': False
            }
        }
        
        # Días especiales y eventos
        self.special_days = {
            'earnings_season_months': [1, 4, 7, 10],  # Enero, Abril, Julio, Octubre
            'holiday_weeks': [
                'thanksgiving_week',
                'christmas_week', 
                'new_year_week',
                'july_4_week',
                'memorial_day_week',
                'labor_day_week'
            ],
            'fomc_meeting_days': [],  # Se actualizaría con fechas reales
            'options_expiration_days': []  # Tercer viernes de cada mes
        }
        
        logger.info("🕐 Sistema de filtros de mercado US inicializado")
    
    def get_current_trading_session(self, timestamp: datetime = None) -> TradingSession:
        """
        Obtener la sesión de trading actual
        
        Args:
            timestamp: Timestamp específico (opcional)
            
        Returns:
            Sesión de trading actual
        """
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            # Convertir a zona horaria del mercado
            if timestamp.tzinfo is None:
                timestamp = pytz.UTC.localize(timestamp)
            
            market_time = timestamp.astimezone(self.market_tz)
            current_time = market_time.time()
            
            # Verificar cada sesión
            for session, (start_time, end_time) in self.session_times.items():
                if session == TradingSession.OVERNIGHT:
                    # Sesión overnight cruza medianoche
                    if current_time >= start_time or current_time <= end_time:
                        return session
                else:
                    if start_time <= current_time <= end_time:
                        return session
            
            # Si no coincide con ninguna sesión, asumir overnight
            return TradingSession.OVERNIGHT
            
        except Exception as e:
            logger.error(f"Error obteniendo sesión de trading: {e}")
            return TradingSession.OVERNIGHT
    
    def is_trading_allowed(self, action: str = 'new_position', timestamp: datetime = None) -> Dict[str, Any]:
        """
        Verificar si el trading está permitido
        
        Args:
            action: Tipo de acción ('new_position', 'close_position', 'modify_position')
            timestamp: Timestamp específico (opcional)
            
        Returns:
            Diccionario con información sobre si el trading está permitido
        """
        try:
            # Obtener sesión actual
            current_session = self.get_current_trading_session(timestamp)
            
            # Obtener configuración de la sesión
            session_config = self.session_filters.get(current_session, {})
            
            # Verificar estado básico del mercado
            market_status = self.market_hours.is_market_open(timestamp)
            
            # Determinar si la acción está permitida
            allowed = False
            reasons = []
            
            if action == 'new_position':
                allowed = session_config.get('allow_new_positions', False)
                if not allowed:
                    reasons.append(f"Nuevas posiciones no permitidas en {current_session.value}")
            
            elif action == 'close_position':
                allowed = session_config.get('allow_close_positions', True)
                if not allowed:
                    reasons.append(f"Cerrar posiciones no permitido en {current_session.value}")
            
            elif action == 'modify_position':
                # Modificaciones generalmente permitidas si el mercado está abierto
                allowed = market_status.get('is_open', False)
                if not allowed:
                    reasons.append("Mercado cerrado para modificaciones")
            
            # Verificar condiciones especiales
            special_conditions = self._check_special_conditions(timestamp)
            if special_conditions['has_restrictions']:
                if action == 'new_position':
                    allowed = False
                    reasons.extend(special_conditions['restrictions'])
            
            return {
                'allowed': allowed,
                'session': current_session.value,
                'market_status': market_status,
                'reasons': reasons,
                'session_config': session_config,
                'special_conditions': special_conditions
            }
            
        except Exception as e:
            logger.error(f"Error verificando si trading está permitido: {e}")
            return {
                'allowed': False,
                'session': 'unknown',
                'reasons': [f'Error: {str(e)}']
            }
    
    def filter_trading_data(self, df: pd.DataFrame, symbol: str, filter_type: str = 'standard') -> pd.DataFrame:
        """
        Filtrar datos de trading basado en horarios de mercado
        
        Args:
            df: DataFrame con datos de trading
            symbol: Símbolo del índice
            filter_type: Tipo de filtro ('standard', 'strict', 'extended')
            
        Returns:
            DataFrame filtrado
        """
        try:
            if df.empty:
                return df
            
            # Asegurar que el índice sea datetime
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            
            # Aplicar filtros según el tipo
            if filter_type == 'strict':
                # Solo horario regular de mercado
                filtered_df = self._filter_regular_hours_only(df)
            
            elif filter_type == 'extended':
                # Incluir pre-market y after-hours activos
                filtered_df = self._filter_extended_hours(df)
            
            else:  # standard
                # Horario regular + pre-market activo
                filtered_df = self._filter_standard_hours(df)
            
            # Aplicar filtros de calidad específicos por sesión
            filtered_df = self._apply_session_quality_filters(filtered_df, symbol)
            
            # Aplicar filtros de días especiales
            filtered_df = self._filter_special_days(filtered_df)
            
            logger.info(f"📊 Datos filtrados: {len(df)} -> {len(filtered_df)} registros ({filter_type})")
            return filtered_df
            
        except Exception as e:
            logger.error(f"Error filtrando datos de trading: {e}")
            return df
    
    def _filter_regular_hours_only(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filtrar solo horario regular de mercado (9:30-16:00 ET)"""
        try:
            filtered_data = []
            
            for timestamp, row in df.iterrows():
                session = self.get_current_trading_session(timestamp)
                
                # Solo sesiones de mercado regular
                if session in [
                    TradingSession.MARKET_OPEN,
                    TradingSession.MORNING_SESSION,
                    TradingSession.LUNCH_SESSION,
                    TradingSession.AFTERNOON_SESSION,
                    TradingSession.MARKET_CLOSE
                ]:
                    filtered_data.append(row)
            
            if filtered_data:
                return pd.DataFrame(filtered_data, index=[row.name for row in filtered_data])
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error filtrando horario regular: {e}")
            return df
    
    def _filter_extended_hours(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filtrar horario extendido (pre-market + regular + after-hours)"""
        try:
            filtered_data = []
            
            for timestamp, row in df.iterrows():
                session = self.get_current_trading_session(timestamp)
                
                # Excluir solo overnight y after-hours muy tarde
                if session not in [TradingSession.OVERNIGHT, TradingSession.AFTER_HOURS_LATE]:
                    filtered_data.append(row)
            
            if filtered_data:
                return pd.DataFrame(filtered_data, index=[row.name for row in filtered_data])
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error filtrando horario extendido: {e}")
            return df
    
    def _filter_standard_hours(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filtrar horario estándar (pre-market activo + regular)"""
        try:
            filtered_data = []
            
            for timestamp, row in df.iterrows():
                session = self.get_current_trading_session(timestamp)
                
                # Incluir pre-market activo y todas las sesiones regulares
                if session in [
                    TradingSession.PRE_MARKET_ACTIVE,
                    TradingSession.MARKET_OPEN,
                    TradingSession.MORNING_SESSION,
                    TradingSession.LUNCH_SESSION,
                    TradingSession.AFTERNOON_SESSION,
                    TradingSession.MARKET_CLOSE
                ]:
                    filtered_data.append(row)
            
            if filtered_data:
                return pd.DataFrame(filtered_data, index=[row.name for row in filtered_data])
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error filtrando horario estándar: {e}")
            return df
    
    def _apply_session_quality_filters(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Aplicar filtros de calidad específicos por sesión"""
        try:
            if df.empty:
                return df
            
            filtered_data = []
            
            # Calcular métricas base para comparación
            avg_volume = df['Volume'].mean() if 'Volume' in df.columns else 0
            
            for timestamp, row in df.iterrows():
                session = self.get_current_trading_session(timestamp)
                session_config = self.session_filters.get(session, {})
                
                # Verificar volumen mínimo
                min_volume = avg_volume * session_config.get('min_volume_multiplier', 0.1)
                if 'Volume' in df.columns and row['Volume'] < min_volume:
                    continue  # Saltar este registro
                
                # Verificar volatilidad máxima
                if 'volatility' in df.columns:
                    max_volatility = session_config.get('volatility_threshold', 0.05)
                    if row['volatility'] > max_volatility:
                        continue  # Saltar este registro
                
                # Si pasa todos los filtros, incluir
                filtered_data.append(row)
            
            if filtered_data:
                return pd.DataFrame(filtered_data, index=[row.name for row in filtered_data])
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error aplicando filtros de calidad por sesión: {e}")
            return df
    
    def _filter_special_days(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filtrar días especiales (feriados, eventos, etc.)"""
        try:
            if df.empty:
                return df
            
            filtered_data = []
            
            for timestamp, row in df.iterrows():
                # Verificar si es un día especial
                special_conditions = self._check_special_conditions(timestamp)
                
                # Si hay restricciones severas, saltar
                if special_conditions.get('severity', 'low') == 'high':
                    continue
                
                filtered_data.append(row)
            
            if filtered_data:
                return pd.DataFrame(filtered_data, index=[row.name for row in filtered_data])
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error filtrando días especiales: {e}")
            return df
    
    def _check_special_conditions(self, timestamp: datetime) -> Dict[str, Any]:
        """Verificar condiciones especiales del mercado"""
        try:
            conditions = {
                'has_restrictions': False,
                'restrictions': [],
                'severity': 'low',
                'conditions': []
            }
            
            if timestamp is None:
                timestamp = datetime.now()
            
            # Convertir a zona horaria del mercado
            if timestamp.tzinfo is None:
                timestamp = pytz.UTC.localize(timestamp)
            
            market_time = timestamp.astimezone(self.market_tz)
            
            # Verificar si es temporada de earnings
            if market_time.month in self.special_days['earnings_season_months']:
                conditions['conditions'].append('earnings_season')
                conditions['restrictions'].append('Temporada de earnings - mayor volatilidad')
            
            # Verificar fin de mes/trimestre
            if self._is_month_end(market_time):
                conditions['conditions'].append('month_end')
                conditions['restrictions'].append('Fin de mes - rebalanceo de portafolios')
            
            if self._is_quarter_end(market_time):
                conditions['conditions'].append('quarter_end')
                conditions['restrictions'].append('Fin de trimestre - mayor actividad institucional')
                conditions['severity'] = 'medium'
            
            # Verificar días festivos
            if self._is_holiday_week(market_time):
                conditions['conditions'].append('holiday_week')
                conditions['restrictions'].append('Semana festiva - menor liquidez')
                conditions['severity'] = 'medium'
            
            # Verificar viernes de vencimiento de opciones
            if self._is_options_expiration(market_time):
                conditions['conditions'].append('options_expiration')
                conditions['restrictions'].append('Vencimiento de opciones - mayor volatilidad')
            
            # Determinar si hay restricciones
            if conditions['restrictions']:
                conditions['has_restrictions'] = True
            
            return conditions
            
        except Exception as e:
            logger.error(f"Error verificando condiciones especiales: {e}")
            return {'has_restrictions': False, 'restrictions': [], 'severity': 'low'}
    
    def _is_month_end(self, timestamp: datetime) -> bool:
        """Verificar si es fin de mes"""
        try:
            # Últimos 3 días hábiles del mes
            next_month = timestamp.replace(day=28) + timedelta(days=4)
            last_day = next_month - timedelta(days=next_month.day)
            
            # Calcular días hábiles desde el timestamp hasta fin de mes
            days_to_end = (last_day - timestamp).days
            
            # Si faltan 3 días hábiles o menos, es fin de mes
            return days_to_end <= 3 and timestamp.weekday() < 5
            
        except Exception as e:
            logger.error(f"Error verificando fin de mes: {e}")
            return False
    
    def _is_quarter_end(self, timestamp: datetime) -> bool:
        """Verificar si es fin de trimestre"""
        try:
            quarter_end_months = [3, 6, 9, 12]  # Marzo, Junio, Septiembre, Diciembre
            
            return (timestamp.month in quarter_end_months and 
                    self._is_month_end(timestamp))
            
        except Exception as e:
            logger.error(f"Error verificando fin de trimestre: {e}")
            return False
    
    def _is_holiday_week(self, timestamp: datetime) -> bool:
        """Verificar si es semana festiva"""
        try:
            # Simplificado - en implementación real se usaría una librería de feriados
            holiday_weeks = [
                (11, 4),  # Thanksgiving (4ta semana de noviembre)
                (12, 4),  # Christmas (4ta semana de diciembre)
                (1, 1),   # New Year (1ra semana de enero)
                (7, 1),   # July 4th (1ra semana de julio)
            ]
            
            for month, week in holiday_weeks:
                if timestamp.month == month:
                    # Calcular semana del mes
                    week_of_month = (timestamp.day - 1) // 7 + 1
                    if week_of_month == week:
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error verificando semana festiva: {e}")
            return False
    
    def _is_options_expiration(self, timestamp: datetime) -> bool:
        """Verificar si es día de vencimiento de opciones (tercer viernes)"""
        try:
            # Tercer viernes del mes
            if timestamp.weekday() == 4:  # Viernes
                # Calcular el tercer viernes
                first_day = timestamp.replace(day=1)
                first_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7)
                third_friday = first_friday + timedelta(days=14)
                
                return timestamp.date() == third_friday.date()
            
            return False
            
        except Exception as e:
            logger.error(f"Error verificando vencimiento de opciones: {e}")
            return False
    
    def get_session_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Obtener estadísticas por sesión de trading"""
        try:
            if df.empty:
                return {}
            
            session_stats = {}
            
            for timestamp, row in df.iterrows():
                session = self.get_current_trading_session(timestamp)
                session_name = session.value
                
                if session_name not in session_stats:
                    session_stats[session_name] = {
                        'count': 0,
                        'volume': [],
                        'volatility': [],
                        'returns': [],
                        'price_range': []
                    }
                
                session_stats[session_name]['count'] += 1
                
                if 'Volume' in df.columns:
                    session_stats[session_name]['volume'].append(row['Volume'])
                
                if 'volatility' in df.columns:
                    session_stats[session_name]['volatility'].append(row['volatility'])
                
                if 'returns' in df.columns:
                    session_stats[session_name]['returns'].append(row['returns'])
                
                if 'High' in df.columns and 'Low' in df.columns:
                    price_range = (row['High'] - row['Low']) / row['Close']
                    session_stats[session_name]['price_range'].append(price_range)
            
            # Calcular estadísticas agregadas
            for session_name, stats in session_stats.items():
                for metric in ['volume', 'volatility', 'returns', 'price_range']:
                    if stats[metric]:
                        stats[f'{metric}_mean'] = np.mean(stats[metric])
                        stats[f'{metric}_std'] = np.std(stats[metric])
                        stats[f'{metric}_median'] = np.median(stats[metric])
                    
                    # Limpiar listas para ahorrar memoria
                    del stats[metric]
            
            return session_stats
            
        except Exception as e:
            logger.error(f"Error calculando estadísticas por sesión: {e}")
            return {}
    
    def get_optimal_trading_sessions(self, symbol: str) -> List[TradingSession]:
        """Obtener sesiones óptimas para trading de un índice específico"""
        try:
            # Configuración por índice
            optimal_sessions = {
                'SPY': [
                    TradingSession.MARKET_OPEN,
                    TradingSession.MORNING_SESSION,
                    TradingSession.AFTERNOON_SESSION
                ],
                'QQQ': [
                    TradingSession.PRE_MARKET_ACTIVE,
                    TradingSession.MARKET_OPEN,
                    TradingSession.MORNING_SESSION,
                    TradingSession.AFTERNOON_SESSION
                ],
                'DIA': [
                    TradingSession.MARKET_OPEN,
                    TradingSession.MORNING_SESSION,
                    TradingSession.AFTERNOON_SESSION,
                    TradingSession.MARKET_CLOSE
                ],
                'IWM': [
                    TradingSession.MARKET_OPEN,
                    TradingSession.MORNING_SESSION,
                    TradingSession.AFTERNOON_SESSION
                ]
            }
            
            return optimal_sessions.get(symbol, [
                TradingSession.MARKET_OPEN,
                TradingSession.MORNING_SESSION,
                TradingSession.AFTERNOON_SESSION
            ])
            
        except Exception as e:
            logger.error(f"Error obteniendo sesiones óptimas: {e}")
            return []

# Función de utilidad global
def create_us_market_filters():
    """Crear instancia del sistema de filtros de mercado US"""
    return USMarketFilters()

# Instancia global
us_market_filters = USMarketFilters()

if __name__ == "__main__":
    # Test del sistema de filtros
    print("🧪 Testing US Market Filters...")
    
    filters = USMarketFilters()
    
    # Test sesión actual
    current_session = filters.get_current_trading_session()
    print(f"📊 Sesión actual: {current_session.value}")
    
    # Test si trading está permitido
    trading_status = filters.is_trading_allowed('new_position')
    print(f"🔄 Trading permitido: {trading_status['allowed']}")
    print(f"   Razones: {trading_status['reasons']}")
    
    # Test sesiones óptimas
    optimal_sessions = filters.get_optimal_trading_sessions('SPY')
    print(f"⏰ Sesiones óptimas para SPY: {[s.value for s in optimal_sessions]}")
    
    print("\n🏁 Test completado")