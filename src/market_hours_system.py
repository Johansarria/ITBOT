"""
SICAR Market Hours System
Sistema de horarios de mercado para índices US
Manejo de sesiones, feriados y horarios de trading
"""

import pytz
from datetime import datetime, time, date, timedelta
from typing import Dict, List, Optional, Tuple, Union
import pandas as pd
import numpy as np
from dataclasses import dataclass
import logging
import json
import requests
from enum import Enum

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketSession(Enum):
    """Tipos de sesiones de mercado"""
    PRE_MARKET = "pre_market"
    REGULAR = "regular"
    AFTER_HOURS = "after_hours"
    CLOSED = "closed"

class MarketStatus(Enum):
    """Estados del mercado"""
    OPEN = "open"
    CLOSED = "closed"
    HOLIDAY = "holiday"
    WEEKEND = "weekend"

@dataclass
class SessionInfo:
    """Información de una sesión de mercado"""
    session: MarketSession
    start_time: time
    end_time: time
    is_active: bool
    volume_factor: float  # Factor de volumen esperado (0-1)
    volatility_factor: float  # Factor de volatilidad esperado (0-2)

@dataclass
class MarketDay:
    """Información de un día de mercado"""
    date: date
    is_trading_day: bool
    is_holiday: bool
    holiday_name: Optional[str]
    sessions: List[SessionInfo]
    early_close: bool = False
    early_close_time: Optional[time] = None

class MarketHoursSystem:
    """
    Sistema de horarios de mercado para índices US
    Maneja sesiones, feriados y horarios especiales
    """
    
    def __init__(self, timezone: str = 'US/Eastern'):
        self.timezone = pytz.timezone(timezone)
        self.utc = pytz.UTC
        
        # Horarios estándar (Eastern Time)
        self.standard_hours = {
            MarketSession.PRE_MARKET: {
                'start': time(4, 0),   # 4:00 AM ET
                'end': time(9, 30),    # 9:30 AM ET
                'volume_factor': 0.1,
                'volatility_factor': 1.2
            },
            MarketSession.REGULAR: {
                'start': time(9, 30),  # 9:30 AM ET
                'end': time(16, 0),    # 4:00 PM ET
                'volume_factor': 1.0,
                'volatility_factor': 1.0
            },
            MarketSession.AFTER_HOURS: {
                'start': time(16, 0),  # 4:00 PM ET
                'end': time(20, 0),    # 8:00 PM ET
                'volume_factor': 0.15,
                'volatility_factor': 1.5
            }
        }
        
        # Feriados del mercado US (fechas fijas y variables)
        self.market_holidays = {}
        self._initialize_holidays()
        
        # Cache para optimizar consultas
        self.cache = {}
        self.cache_duration = 3600  # 1 hora
        
    def _initialize_holidays(self):
        """Inicializa los feriados del mercado"""
        
        # Feriados fijos
        fixed_holidays = {
            'New Year\'s Day': (1, 1),
            'Independence Day': (7, 4),
            'Christmas Day': (12, 25)
        }
        
        # Generar feriados para varios años
        current_year = datetime.now().year
        for year in range(current_year - 1, current_year + 3):
            year_holidays = {}
            
            # Feriados fijos
            for name, (month, day) in fixed_holidays.items():
                holiday_date = date(year, month, day)
                # Si cae en fin de semana, se observa el lunes/viernes
                if holiday_date.weekday() == 5:  # Sábado
                    holiday_date = holiday_date + timedelta(days=2)
                elif holiday_date.weekday() == 6:  # Domingo
                    holiday_date = holiday_date + timedelta(days=1)
                
                year_holidays[holiday_date] = name
            
            # Feriados variables
            year_holidays.update(self._calculate_variable_holidays(year))
            
            self.market_holidays[year] = year_holidays
    
    def _calculate_variable_holidays(self, year: int) -> Dict[date, str]:
        """Calcula feriados variables para un año específico"""
        
        holidays = {}
        
        # Martin Luther King Jr. Day (3er lunes de enero)
        mlk_day = self._get_nth_weekday(year, 1, 0, 3)  # 3er lunes
        holidays[mlk_day] = "Martin Luther King Jr. Day"
        
        # Presidents' Day (3er lunes de febrero)
        presidents_day = self._get_nth_weekday(year, 2, 0, 3)  # 3er lunes
        holidays[presidents_day] = "Presidents' Day"
        
        # Good Friday (viernes antes de Easter)
        easter = self._calculate_easter(year)
        good_friday = easter - timedelta(days=2)
        holidays[good_friday] = "Good Friday"
        
        # Memorial Day (último lunes de mayo)
        memorial_day = self._get_last_weekday(year, 5, 0)  # Último lunes
        holidays[memorial_day] = "Memorial Day"
        
        # Juneteenth (19 de junio, desde 2021)
        if year >= 2021:
            juneteenth = date(year, 6, 19)
            if juneteenth.weekday() == 5:  # Sábado
                juneteenth = juneteenth + timedelta(days=2)
            elif juneteenth.weekday() == 6:  # Domingo
                juneteenth = juneteenth + timedelta(days=1)
            holidays[juneteenth] = "Juneteenth"
        
        # Labor Day (1er lunes de septiembre)
        labor_day = self._get_nth_weekday(year, 9, 0, 1)  # 1er lunes
        holidays[labor_day] = "Labor Day"
        
        # Columbus Day (2do lunes de octubre) - Mercado abierto
        # Thanksgiving (4to jueves de noviembre)
        thanksgiving = self._get_nth_weekday(year, 11, 3, 4)  # 4to jueves
        holidays[thanksgiving] = "Thanksgiving"
        
        # Day after Thanksgiving (viernes después de Thanksgiving)
        black_friday = thanksgiving + timedelta(days=1)
        holidays[black_friday] = "Day after Thanksgiving"
        
        return holidays
    
    def _get_nth_weekday(self, year: int, month: int, weekday: int, n: int) -> date:
        """Obtiene el n-ésimo día de la semana en un mes"""
        first_day = date(year, month, 1)
        first_weekday = first_day.weekday()
        
        # Calcular días hasta el primer día de la semana deseado
        days_to_add = (weekday - first_weekday) % 7
        first_occurrence = first_day + timedelta(days=days_to_add)
        
        # Agregar semanas para llegar al n-ésimo
        nth_occurrence = first_occurrence + timedelta(weeks=n-1)
        
        return nth_occurrence
    
    def _get_last_weekday(self, year: int, month: int, weekday: int) -> date:
        """Obtiene el último día de la semana específico en un mes"""
        # Último día del mes
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)
        
        # Retroceder hasta encontrar el día de la semana deseado
        days_back = (last_day.weekday() - weekday) % 7
        return last_day - timedelta(days=days_back)
    
    def _calculate_easter(self, year: int) -> date:
        """Calcula la fecha de Easter usando el algoritmo de Gauss"""
        a = year % 19
        b = year // 100
        c = year % 100
        d = b // 4
        e = b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i = c // 4
        k = c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        month = (h + l - 7 * m + 114) // 31
        day = ((h + l - 7 * m + 114) % 31) + 1
        
        return date(year, month, day)
    
    def is_market_open(self, timestamp: datetime = None) -> Dict[str, Union[bool, MarketSession]]:
        """
        Verifica si el mercado está abierto en un momento específico
        
        Args:
            timestamp: Momento a verificar (default: ahora)
        
        Returns:
            Dict con información del estado del mercado
        """
        
        if timestamp is None:
            timestamp = datetime.now(self.timezone)
        elif timestamp.tzinfo is None:
            timestamp = self.timezone.localize(timestamp)
        else:
            timestamp = timestamp.astimezone(self.timezone)
        
        # Verificar cache
        cache_key = f"market_status_{timestamp.strftime('%Y%m%d_%H%M')}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        market_day = self.get_market_day_info(timestamp.date())
        
        if not market_day.is_trading_day:
            result = {
                'is_open': False,
                'current_session': MarketSession.CLOSED,
                'status': MarketStatus.HOLIDAY if market_day.is_holiday else MarketStatus.WEEKEND,
                'next_open': self._get_next_market_open(timestamp),
                'time_to_open': None
            }
        else:
            current_time = timestamp.time()
            current_session = self._get_current_session(current_time, market_day)
            
            is_open = current_session != MarketSession.CLOSED
            
            result = {
                'is_open': is_open,
                'current_session': current_session,
                'status': MarketStatus.OPEN if is_open else MarketStatus.CLOSED,
                'next_open': self._get_next_session_change(timestamp, market_day),
                'time_to_open': None
            }
            
            if not is_open:
                next_open = result['next_open']
                if next_open:
                    result['time_to_open'] = (next_open - timestamp).total_seconds() / 60  # minutos
        
        # Guardar en cache
        self.cache[cache_key] = result
        
        return result
    
    def get_market_day_info(self, target_date: date) -> MarketDay:
        """Obtiene información completa de un día de mercado"""
        
        # Verificar si es fin de semana
        if target_date.weekday() >= 5:  # Sábado o domingo
            return MarketDay(
                date=target_date,
                is_trading_day=False,
                is_holiday=False,
                holiday_name=None,
                sessions=[]
            )
        
        # Verificar si es feriado
        year_holidays = self.market_holidays.get(target_date.year, {})
        is_holiday = target_date in year_holidays
        holiday_name = year_holidays.get(target_date) if is_holiday else None
        
        if is_holiday:
            return MarketDay(
                date=target_date,
                is_trading_day=False,
                is_holiday=True,
                holiday_name=holiday_name,
                sessions=[]
            )
        
        # Verificar si es cierre temprano
        early_close, early_close_time = self._check_early_close(target_date)
        
        # Crear sesiones
        sessions = []
        for session_type, hours in self.standard_hours.items():
            end_time = early_close_time if early_close and session_type == MarketSession.REGULAR else hours['end']
            
            session_info = SessionInfo(
                session=session_type,
                start_time=hours['start'],
                end_time=end_time,
                is_active=True,
                volume_factor=hours['volume_factor'],
                volatility_factor=hours['volatility_factor']
            )
            sessions.append(session_info)
        
        return MarketDay(
            date=target_date,
            is_trading_day=True,
            is_holiday=False,
            holiday_name=None,
            sessions=sessions,
            early_close=early_close,
            early_close_time=early_close_time
        )
    
    def _check_early_close(self, target_date: date) -> Tuple[bool, Optional[time]]:
        """Verifica si es un día de cierre temprano"""
        
        year_holidays = self.market_holidays.get(target_date.year, {})
        
        # Día después de Thanksgiving (Black Friday) - cierre a las 1:00 PM
        for holiday_date, holiday_name in year_holidays.items():
            if holiday_name == "Day after Thanksgiving" and target_date == holiday_date:
                return True, time(13, 0)  # 1:00 PM
        
        # Víspera de Navidad y Año Nuevo - cierre a las 1:00 PM
        christmas_eve = date(target_date.year, 12, 24)
        new_years_eve = date(target_date.year, 12, 31)
        
        if target_date in [christmas_eve, new_years_eve] and target_date.weekday() < 5:
            return True, time(13, 0)  # 1:00 PM
        
        # Víspera del 4 de julio - cierre a las 1:00 PM
        july_3 = date(target_date.year, 7, 3)
        if target_date == july_3 and target_date.weekday() < 5:
            return True, time(13, 0)  # 1:00 PM
        
        return False, None
    
    def _get_current_session(self, current_time: time, market_day: MarketDay) -> MarketSession:
        """Determina la sesión actual basada en la hora"""
        
        for session in market_day.sessions:
            if session.start_time <= current_time < session.end_time:
                return session.session
        
        return MarketSession.CLOSED
    
    def _get_next_market_open(self, timestamp: datetime) -> Optional[datetime]:
        """Obtiene el próximo momento de apertura del mercado"""
        
        current_date = timestamp.date()
        
        # Buscar el próximo día de trading
        for i in range(1, 10):  # Buscar hasta 10 días adelante
            next_date = current_date + timedelta(days=i)
            market_day = self.get_market_day_info(next_date)
            
            if market_day.is_trading_day:
                # Encontrar la primera sesión del día
                for session in market_day.sessions:
                    if session.session == MarketSession.REGULAR:  # Usar sesión regular
                        next_open = datetime.combine(next_date, session.start_time)
                        return self.timezone.localize(next_open)
        
        return None
    
    def _get_next_session_change(self, timestamp: datetime, market_day: MarketDay) -> Optional[datetime]:
        """Obtiene el próximo cambio de sesión"""
        
        current_time = timestamp.time()
        current_date = timestamp.date()
        
        # Buscar la próxima sesión en el mismo día
        for session in market_day.sessions:
            if current_time < session.start_time:
                next_change = datetime.combine(current_date, session.start_time)
                return self.timezone.localize(next_change)
        
        # Si no hay más sesiones hoy, buscar el próximo día de trading
        return self._get_next_market_open(timestamp)
    
    def get_session_info(self, timestamp: datetime = None) -> Optional[SessionInfo]:
        """Obtiene información detallada de la sesión actual"""
        
        if timestamp is None:
            timestamp = datetime.now(self.timezone)
        elif timestamp.tzinfo is None:
            timestamp = self.timezone.localize(timestamp)
        else:
            timestamp = timestamp.astimezone(self.timezone)
        
        market_day = self.get_market_day_info(timestamp.date())
        
        if not market_day.is_trading_day:
            return None
        
        current_time = timestamp.time()
        current_session = self._get_current_session(current_time, market_day)
        
        # Encontrar la información de la sesión
        for session in market_day.sessions:
            if session.session == current_session:
                return session
        
        return None
    
    def get_trading_calendar(self, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Genera un calendario de trading para un rango de fechas
        
        Returns:
            DataFrame con información de cada día
        """
        
        calendar_data = []
        current_date = start_date
        
        while current_date <= end_date:
            market_day = self.get_market_day_info(current_date)
            
            calendar_data.append({
                'date': current_date,
                'is_trading_day': market_day.is_trading_day,
                'is_holiday': market_day.is_holiday,
                'holiday_name': market_day.holiday_name,
                'early_close': market_day.early_close,
                'weekday': current_date.strftime('%A')
            })
            
            current_date += timedelta(days=1)
        
        return pd.DataFrame(calendar_data)
    
    def is_trading_allowed(self, timestamp: datetime = None, 
                          session_filter: List[MarketSession] = None) -> bool:
        """
        Verifica si se permite trading en un momento específico
        
        Args:
            timestamp: Momento a verificar
            session_filter: Lista de sesiones permitidas
        
        Returns:
            True si se permite trading
        """
        
        if session_filter is None:
            session_filter = [MarketSession.REGULAR]  # Solo sesión regular por defecto
        
        market_status = self.is_market_open(timestamp)
        
        if not market_status['is_open']:
            return False
        
        current_session = market_status['current_session']
        return current_session in session_filter
    
    def get_volume_factor(self, timestamp: datetime = None) -> float:
        """Obtiene el factor de volumen esperado para el momento actual"""
        
        session_info = self.get_session_info(timestamp)
        return session_info.volume_factor if session_info else 0.0
    
    def get_volatility_factor(self, timestamp: datetime = None) -> float:
        """Obtiene el factor de volatilidad esperado para el momento actual"""
        
        session_info = self.get_session_info(timestamp)
        return session_info.volatility_factor if session_info else 1.0
    
    def clear_cache(self):
        """Limpia el cache del sistema"""
        self.cache.clear()
        logger.info("Cache del sistema de horarios limpiado")

# Instancia global del sistema de horarios
market_hours = MarketHoursSystem()

def is_market_open_now() -> bool:
    """Función de utilidad para verificar si el mercado está abierto ahora"""
    return market_hours.is_market_open()['is_open']

def get_current_session() -> MarketSession:
    """Función de utilidad para obtener la sesión actual"""
    return market_hours.is_market_open()['current_session']

def is_trading_time(session_filter: List[MarketSession] = None) -> bool:
    """Función de utilidad para verificar si es momento de trading"""
    return market_hours.is_trading_allowed(session_filter=session_filter)

if __name__ == "__main__":
    # Ejemplo de uso
    system = MarketHoursSystem()
    
    # Estado actual del mercado
    status = system.is_market_open()
    print(f"Estado del mercado: {status}")
    
    # Información de la sesión actual
    session_info = system.get_session_info()
    if session_info:
        print(f"Sesión actual: {session_info.session.value}")
        print(f"Factor de volumen: {session_info.volume_factor}")
        print(f"Factor de volatilidad: {session_info.volatility_factor}")
    
    # Calendario de trading para la próxima semana
    start_date = date.today()
    end_date = start_date + timedelta(days=7)
    calendar = system.get_trading_calendar(start_date, end_date)
    print("\nCalendario de trading:")
    print(calendar)
    
    # Verificar si se permite trading
    trading_allowed = system.is_trading_allowed()
    print(f"\nTrading permitido: {trading_allowed}")