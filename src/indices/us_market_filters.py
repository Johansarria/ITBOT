"""
SICAR US Market Filters
Filtros específicos para mercados de índices estadounidenses
"""

import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum
import pytz
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingSession(Enum):
    """Sesiones de trading"""
    PRE_MARKET = "pre_market"
    REGULAR = "regular"
    AFTER_HOURS = "after_hours"
    CLOSED = "closed"

class MarketCondition(Enum):
    """Condiciones del mercado"""
    NORMAL = "normal"
    HOLIDAY = "holiday"
    EARLY_CLOSE = "early_close"
    DELAYED_OPEN = "delayed_open"
    EARNINGS_WEEK = "earnings_week"
    MONTH_END = "month_end"
    QUARTER_END = "quarter_end"
    OPTIONS_EXPIRY = "options_expiry"
    HIGH_VOLATILITY = "high_volatility"
    LOW_LIQUIDITY = "low_liquidity"

class USMarketFilters:
    """
    Filtros para mercados estadounidenses
    Integra con el sistema de horarios de mercado existente
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.eastern_tz = pytz.timezone('US/Eastern')
        
        # Horarios de trading (Eastern Time)
        self.trading_hours = {
            'pre_market': {'start': time(4, 0), 'end': time(9, 30)},
            'regular': {'start': time(9, 30), 'end': time(16, 0)},
            'after_hours': {'start': time(16, 0), 'end': time(20, 0)}
        }
        
        # Días festivos típicos (simplificado)
        self.holidays_2024 = [
            '2024-01-01',  # New Year's Day
            '2024-01-15',  # MLK Day
            '2024-02-19',  # Presidents Day
            '2024-03-29',  # Good Friday
            '2024-05-27',  # Memorial Day
            '2024-06-19',  # Juneteenth
            '2024-07-04',  # Independence Day
            '2024-09-02',  # Labor Day
            '2024-11-28',  # Thanksgiving
            '2024-12-25'   # Christmas
        ]
        
        # Configuración de filtros
        self.filter_config = {
            'min_volume_regular': 100000,
            'min_volume_extended': 50000,
            'max_spread_pct': 0.005,  # 0.5%
            'volatility_threshold': 0.03,  # 3%
            'liquidity_threshold': 0.8
        }
    
    def get_current_session(self, timestamp: Optional[datetime] = None) -> TradingSession:
        """
        Determinar la sesión de trading actual
        
        Args:
            timestamp: Timestamp específico (default: ahora)
            
        Returns:
            Sesión de trading actual
        """
        if timestamp is None:
            timestamp = datetime.now(self.eastern_tz)
        elif timestamp.tzinfo is None:
            timestamp = self.eastern_tz.localize(timestamp)
        else:
            timestamp = timestamp.astimezone(self.eastern_tz)
        
        # Verificar si es fin de semana
        if timestamp.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return TradingSession.CLOSED
        
        current_time = timestamp.time()
        
        # Determinar sesión
        if (self.trading_hours['pre_market']['start'] <= current_time < 
            self.trading_hours['pre_market']['end']):
            return TradingSession.PRE_MARKET
        elif (self.trading_hours['regular']['start'] <= current_time < 
              self.trading_hours['regular']['end']):
            return TradingSession.REGULAR
        elif (self.trading_hours['after_hours']['start'] <= current_time < 
              self.trading_hours['after_hours']['end']):
            return TradingSession.AFTER_HOURS
        else:
            return TradingSession.CLOSED
    
    def is_trading_allowed(self, 
                          timestamp: Optional[datetime] = None,
                          session: Optional[TradingSession] = None,
                          allow_extended: bool = False) -> bool:
        """
        Verificar si el trading está permitido
        
        Args:
            timestamp: Timestamp específico
            session: Sesión específica a verificar
            allow_extended: Permitir trading en horario extendido
            
        Returns:
            True si el trading está permitido
        """
        if timestamp is None:
            timestamp = datetime.now(self.eastern_tz)
        
        if session is None:
            session = self.get_current_session(timestamp)
        
        # Verificar día festivo
        if self._is_holiday(timestamp):
            return False
        
        # Verificar sesión
        if session == TradingSession.CLOSED:
            return False
        elif session == TradingSession.REGULAR:
            return True
        elif session in [TradingSession.PRE_MARKET, TradingSession.AFTER_HOURS]:
            return allow_extended
        
        return False
    
    def filter_trading_hours(self, 
                           data: pd.DataFrame,
                           hour_type: str = 'regular') -> pd.DataFrame:
        """
        Filtrar datos por horarios de trading
        
        Args:
            data: DataFrame con datos de mercado
            hour_type: 'regular', 'extended', 'all', 'weekday'
            
        Returns:
            DataFrame filtrado
        """
        try:
            if data.empty:
                return data
            
            # Asegurar que el índice sea datetime
            if not isinstance(data.index, pd.DatetimeIndex):
                if 'timestamp' in data.columns:
                    data = data.set_index('timestamp')
                else:
                    self.logger.warning("No se puede determinar timestamp en los datos")
                    return data
            
            # Convertir a Eastern Time si es necesario
            if data.index.tz is None:
                data.index = data.index.tz_localize('UTC').tz_convert(self.eastern_tz)
            else:
                data.index = data.index.tz_convert(self.eastern_tz)
            
            if hour_type == 'regular':
                # Solo horario regular
                mask = (
                    (data.index.time >= self.trading_hours['regular']['start']) &
                    (data.index.time < self.trading_hours['regular']['end']) &
                    (data.index.weekday < 5)  # Lunes a Viernes
                )
            elif hour_type == 'extended':
                # Horario extendido (pre + regular + after)
                mask = (
                    (data.index.time >= self.trading_hours['pre_market']['start']) &
                    (data.index.time < self.trading_hours['after_hours']['end']) &
                    (data.index.weekday < 5)
                )
            elif hour_type == 'weekday':
                # Solo días de semana
                mask = data.index.weekday < 5
            else:  # 'all'
                # Todos los datos
                return data
            
            # Filtrar días festivos
            holiday_mask = ~data.index.date.isin([
                pd.to_datetime(holiday).date() for holiday in self.holidays_2024
            ])
            
            final_mask = mask & holiday_mask
            
            return data[final_mask]
            
        except Exception as e:
            self.logger.error(f"Error filtrando horarios: {e}")
            return data
    
    def apply_session_filters(self, 
                            data: pd.DataFrame,
                            session: TradingSession) -> pd.DataFrame:
        """
        Aplicar filtros específicos de sesión
        
        Args:
            data: DataFrame con datos
            session: Sesión de trading
            
        Returns:
            DataFrame filtrado
        """
        try:
            if data.empty:
                return data
            
            filtered_data = data.copy()
            
            if session == TradingSession.REGULAR:
                # Filtros para horario regular
                filtered_data = self._apply_volume_filter(
                    filtered_data, 
                    min_volume=self.filter_config['min_volume_regular']
                )
                filtered_data = self._apply_spread_filter(filtered_data)
                
            elif session in [TradingSession.PRE_MARKET, TradingSession.AFTER_HOURS]:
                # Filtros para horario extendido (más estrictos)
                filtered_data = self._apply_volume_filter(
                    filtered_data,
                    min_volume=self.filter_config['min_volume_extended']
                )
                filtered_data = self._apply_volatility_filter(filtered_data)
                
            return filtered_data
            
        except Exception as e:
            self.logger.error(f"Error aplicando filtros de sesión: {e}")
            return data
    
    def filter_special_days(self, 
                          data: pd.DataFrame,
                          exclude_conditions: List[MarketCondition] = None) -> pd.DataFrame:
        """
        Filtrar días especiales
        
        Args:
            data: DataFrame con datos
            exclude_conditions: Condiciones a excluir
            
        Returns:
            DataFrame filtrado
        """
        try:
            if data.empty or exclude_conditions is None:
                return data
            
            filtered_data = data.copy()
            
            for condition in exclude_conditions:
                if condition == MarketCondition.HOLIDAY:
                    filtered_data = self._filter_holidays(filtered_data)
                elif condition == MarketCondition.MONTH_END:
                    filtered_data = self._filter_month_end(filtered_data)
                elif condition == MarketCondition.QUARTER_END:
                    filtered_data = self._filter_quarter_end(filtered_data)
                elif condition == MarketCondition.OPTIONS_EXPIRY:
                    filtered_data = self._filter_options_expiry(filtered_data)
                elif condition == MarketCondition.EARNINGS_WEEK:
                    # Este filtro requeriría datos externos de earnings
                    pass
            
            return filtered_data
            
        except Exception as e:
            self.logger.error(f"Error filtrando días especiales: {e}")
            return data
    
    def get_session_statistics(self, 
                             data: pd.DataFrame,
                             session: TradingSession) -> Dict[str, float]:
        """
        Calcular estadísticas de sesión
        
        Args:
            data: DataFrame con datos
            session: Sesión de trading
            
        Returns:
            Diccionario con estadísticas
        """
        try:
            if data.empty:
                return {}
            
            # Filtrar datos por sesión
            session_data = self._filter_by_session(data, session)
            
            if session_data.empty:
                return {}
            
            stats = {
                'avg_volume': float(session_data['Volume'].mean()) if 'Volume' in session_data.columns else 0,
                'avg_volatility': float(session_data['Close'].pct_change().std() * np.sqrt(252)),
                'avg_spread': self._calculate_average_spread(session_data),
                'liquidity_score': self._calculate_liquidity_score(session_data),
                'data_points': len(session_data),
                'session': session.value
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error calculando estadísticas: {e}")
            return {}
    
    def _is_holiday(self, timestamp: datetime) -> bool:
        """Verificar si es día festivo"""
        date_str = timestamp.strftime('%Y-%m-%d')
        return date_str in self.holidays_2024
    
    def _apply_volume_filter(self, data: pd.DataFrame, min_volume: int) -> pd.DataFrame:
        """Aplicar filtro de volumen"""
        if 'Volume' not in data.columns:
            return data
        
        return data[data['Volume'] >= min_volume]
    
    def _apply_spread_filter(self, data: pd.DataFrame) -> pd.DataFrame:
        """Aplicar filtro de spread"""
        if not all(col in data.columns for col in ['High', 'Low']):
            return data
        
        # Calcular spread aproximado
        spread_pct = (data['High'] - data['Low']) / data['Close']
        max_spread = self.filter_config['max_spread_pct']
        
        return data[spread_pct <= max_spread]
    
    def _apply_volatility_filter(self, data: pd.DataFrame) -> pd.DataFrame:
        """Aplicar filtro de volatilidad"""
        if 'Close' not in data.columns:
            return data
        
        # Calcular volatilidad rolling
        returns = data['Close'].pct_change()
        volatility = returns.rolling(window=20).std()
        
        threshold = self.filter_config['volatility_threshold']
        
        return data[volatility <= threshold]
    
    def _filter_holidays(self, data: pd.DataFrame) -> pd.DataFrame:
        """Filtrar días festivos"""
        if not isinstance(data.index, pd.DatetimeIndex):
            return data
        
        holiday_dates = [pd.to_datetime(holiday).date() for holiday in self.holidays_2024]
        mask = ~data.index.date.isin(holiday_dates)
        
        return data[mask]
    
    def _filter_month_end(self, data: pd.DataFrame) -> pd.DataFrame:
        """Filtrar fin de mes (últimos 2 días hábiles)"""
        if not isinstance(data.index, pd.DatetimeIndex):
            return data
        
        # Identificar últimos días del mes
        month_end_mask = data.index.to_series().dt.is_month_end
        
        # También incluir el día anterior al último día hábil
        prev_day_mask = data.index.to_series().shift(-1).dt.is_month_end
        
        exclude_mask = month_end_mask | prev_day_mask.fillna(False)
        
        return data[~exclude_mask]
    
    def _filter_quarter_end(self, data: pd.DataFrame) -> pd.DataFrame:
        """Filtrar fin de trimestre"""
        if not isinstance(data.index, pd.DatetimeIndex):
            return data
        
        # Identificar fines de trimestre (marzo, junio, septiembre, diciembre)
        quarter_end_months = [3, 6, 9, 12]
        quarter_end_mask = (
            data.index.month.isin(quarter_end_months) &
            data.index.to_series().dt.is_month_end
        )
        
        return data[~quarter_end_mask]
    
    def _filter_options_expiry(self, data: pd.DataFrame) -> pd.DataFrame:
        """Filtrar días de vencimiento de opciones (tercer viernes del mes)"""
        if not isinstance(data.index, pd.DatetimeIndex):
            return data
        
        def is_third_friday(date):
            """Verificar si es el tercer viernes del mes"""
            if date.weekday() != 4:  # No es viernes
                return False
            
            # Calcular el tercer viernes
            first_day = date.replace(day=1)
            first_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7)
            third_friday = first_friday + timedelta(days=14)
            
            return date.date() == third_friday.date()
        
        expiry_mask = data.index.to_series().apply(is_third_friday)
        
        return data[~expiry_mask]
    
    def _filter_by_session(self, data: pd.DataFrame, session: TradingSession) -> pd.DataFrame:
        """Filtrar datos por sesión específica"""
        if not isinstance(data.index, pd.DatetimeIndex):
            return data
        
        # Convertir a Eastern Time
        if data.index.tz is None:
            data_tz = data.copy()
            data_tz.index = data_tz.index.tz_localize('UTC').tz_convert(self.eastern_tz)
        else:
            data_tz = data.copy()
            data_tz.index = data_tz.index.tz_convert(self.eastern_tz)
        
        if session == TradingSession.REGULAR:
            mask = (
                (data_tz.index.time >= self.trading_hours['regular']['start']) &
                (data_tz.index.time < self.trading_hours['regular']['end'])
            )
        elif session == TradingSession.PRE_MARKET:
            mask = (
                (data_tz.index.time >= self.trading_hours['pre_market']['start']) &
                (data_tz.index.time < self.trading_hours['pre_market']['end'])
            )
        elif session == TradingSession.AFTER_HOURS:
            mask = (
                (data_tz.index.time >= self.trading_hours['after_hours']['start']) &
                (data_tz.index.time < self.trading_hours['after_hours']['end'])
            )
        else:
            return pd.DataFrame()  # CLOSED session
        
        return data_tz[mask]
    
    def _calculate_average_spread(self, data: pd.DataFrame) -> float:
        """Calcular spread promedio"""
        if not all(col in data.columns for col in ['High', 'Low', 'Close']):
            return 0.0
        
        spread_pct = (data['High'] - data['Low']) / data['Close']
        return float(spread_pct.mean())
    
    def _calculate_liquidity_score(self, data: pd.DataFrame) -> float:
        """Calcular score de liquidez"""
        if 'Volume' not in data.columns:
            return 0.5
        
        # Score basado en volumen y consistencia
        avg_volume = data['Volume'].mean()
        vol_std = data['Volume'].std()
        
        # Normalizar volumen (valores típicos para ETFs principales)
        volume_score = min(1.0, avg_volume / 1000000)  # 1M como referencia
        
        # Score de consistencia
        consistency_score = 1 - min(1.0, vol_std / avg_volume) if avg_volume > 0 else 0
        
        return float((volume_score + consistency_score) / 2)

# Funciones de utilidad
def get_market_session(timestamp: Optional[datetime] = None) -> TradingSession:
    """Obtener sesión de mercado actual"""
    filters = USMarketFilters()
    return filters.get_current_session(timestamp)

def is_market_open(timestamp: Optional[datetime] = None, allow_extended: bool = False) -> bool:
    """Verificar si el mercado está abierto"""
    filters = USMarketFilters()
    return filters.is_trading_allowed(timestamp, allow_extended=allow_extended)

def filter_market_hours(data: pd.DataFrame, hour_type: str = 'regular') -> pd.DataFrame:
    """Filtrar datos por horarios de mercado"""
    filters = USMarketFilters()
    return filters.filter_trading_hours(data, hour_type)