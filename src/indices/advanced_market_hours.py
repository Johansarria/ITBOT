"""
Advanced Market Hours System for SICAR
======================================

Sistema avanzado de horarios de mercado con soporte para múltiples zonas horarias,
mercados internacionales, días festivos, y sesiones especiales de trading.

Author: SICAR System
Date: 2024-10-27
Version: 1.0
"""

import pytz
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum
import holidays
import warnings
warnings.filterwarnings('ignore')

class MarketType(Enum):
    """Tipos de mercados soportados"""
    US_EQUITY = "us_equity"
    US_OPTIONS = "us_options"
    US_FUTURES = "us_futures"
    FOREX = "forex"
    CRYPTO = "crypto"
    EUROPEAN_EQUITY = "european_equity"
    ASIAN_EQUITY = "asian_equity"

class SessionType(Enum):
    """Tipos de sesiones de trading"""
    PRE_MARKET = "pre_market"
    REGULAR = "regular"
    AFTER_HOURS = "after_hours"
    EXTENDED = "extended"  # Pre + Regular + After
    OVERNIGHT = "overnight"
    CLOSED = "closed"

class MarketStatus(Enum):
    """Estados del mercado"""
    OPEN = "open"
    CLOSED = "closed"
    PRE_MARKET = "pre_market"
    AFTER_HOURS = "after_hours"
    HOLIDAY = "holiday"
    WEEKEND = "weekend"
    EARLY_CLOSE = "early_close"

@dataclass
class TradingSession:
    """Definición de una sesión de trading"""
    name: str
    session_type: SessionType
    start_time: time
    end_time: time
    timezone: str
    is_active: bool = True
    volume_factor: float = 1.0  # Factor de volumen esperado
    volatility_factor: float = 1.0  # Factor de volatilidad esperado

@dataclass
class MarketSchedule:
    """Horario completo de un mercado"""
    market_name: str
    market_type: MarketType
    timezone: str
    sessions: List[TradingSession]
    holidays: List[datetime]
    early_close_days: Dict[datetime, time]  # Fecha -> hora de cierre temprano

@dataclass
class MarketStatus:
    """Estado actual del mercado"""
    market_name: str
    current_status: MarketStatus
    current_session: Optional[TradingSession]
    next_session: Optional[TradingSession]
    time_to_next_session: Optional[timedelta]
    is_trading_day: bool
    session_progress: float  # 0-1, progreso en la sesión actual
    volume_factor: float
    volatility_factor: float

class AdvancedMarketHours:
    """
    Sistema avanzado de horarios de mercado
    
    Funcionalidades:
    - Soporte para múltiples mercados y zonas horarias
    - Gestión de días festivos por país/mercado
    - Sesiones especiales (pre-market, after-hours)
    - Cálculo de factores de volumen y volatilidad
    - Predicción de próximas sesiones
    - Integración con datos históricos
    """
    
    def __init__(self):
        """Inicializar el sistema de horarios de mercado"""
        self.market_schedules = {}
        self.holiday_calendars = {}
        self._initialize_market_schedules()
        self._initialize_holiday_calendars()
    
    def _initialize_market_schedules(self):
        """Inicializar horarios de mercados principales"""
        
        # Mercado de valores estadounidense (NYSE/NASDAQ)
        us_equity_sessions = [
            TradingSession(
                name="Pre-Market",
                session_type=SessionType.PRE_MARKET,
                start_time=time(4, 0),  # 4:00 AM ET
                end_time=time(9, 30),   # 9:30 AM ET
                timezone="US/Eastern",
                volume_factor=0.1,
                volatility_factor=1.5
            ),
            TradingSession(
                name="Regular Hours",
                session_type=SessionType.REGULAR,
                start_time=time(9, 30),  # 9:30 AM ET
                end_time=time(16, 0),    # 4:00 PM ET
                timezone="US/Eastern",
                volume_factor=1.0,
                volatility_factor=1.0
            ),
            TradingSession(
                name="After Hours",
                session_type=SessionType.AFTER_HOURS,
                start_time=time(16, 0),  # 4:00 PM ET
                end_time=time(20, 0),    # 8:00 PM ET
                timezone="US/Eastern",
                volume_factor=0.05,
                volatility_factor=2.0
            )
        ]
        
        self.market_schedules["US_EQUITY"] = MarketSchedule(
            market_name="US Equity Markets",
            market_type=MarketType.US_EQUITY,
            timezone="US/Eastern",
            sessions=us_equity_sessions,
            holidays=[],  # Se llenarán dinámicamente
            early_close_days={}
        )
        
        # Mercado de futuros estadounidense
        us_futures_sessions = [
            TradingSession(
                name="Overnight",
                session_type=SessionType.OVERNIGHT,
                start_time=time(18, 0),  # 6:00 PM ET (día anterior)
                end_time=time(17, 0),    # 5:00 PM ET
                timezone="US/Eastern",
                volume_factor=0.3,
                volatility_factor=1.2
            )
        ]
        
        self.market_schedules["US_FUTURES"] = MarketSchedule(
            market_name="US Futures Markets",
            market_type=MarketType.US_FUTURES,
            timezone="US/Eastern",
            sessions=us_futures_sessions,
            holidays=[],
            early_close_days={}
        )
        
        # Forex (24/5)
        forex_sessions = [
            TradingSession(
                name="Sydney",
                session_type=SessionType.REGULAR,
                start_time=time(22, 0),  # 10:00 PM UTC (domingo)
                end_time=time(7, 0),     # 7:00 AM UTC
                timezone="UTC",
                volume_factor=0.3,
                volatility_factor=0.8
            ),
            TradingSession(
                name="Tokyo",
                session_type=SessionType.REGULAR,
                start_time=time(0, 0),   # 12:00 AM UTC
                end_time=time(9, 0),     # 9:00 AM UTC
                timezone="UTC",
                volume_factor=0.6,
                volatility_factor=1.0
            ),
            TradingSession(
                name="London",
                session_type=SessionType.REGULAR,
                start_time=time(8, 0),   # 8:00 AM UTC
                end_time=time(17, 0),    # 5:00 PM UTC
                timezone="UTC",
                volume_factor=1.0,
                volatility_factor=1.2
            ),
            TradingSession(
                name="New York",
                session_type=SessionType.REGULAR,
                start_time=time(13, 0),  # 1:00 PM UTC
                end_time=time(22, 0),    # 10:00 PM UTC
                timezone="UTC",
                volume_factor=1.0,
                volatility_factor=1.1
            )
        ]
        
        self.market_schedules["FOREX"] = MarketSchedule(
            market_name="Forex Markets",
            market_type=MarketType.FOREX,
            timezone="UTC",
            sessions=forex_sessions,
            holidays=[],
            early_close_days={}
        )
        
        # Crypto (24/7)
        crypto_sessions = [
            TradingSession(
                name="24/7 Trading",
                session_type=SessionType.REGULAR,
                start_time=time(0, 0),
                end_time=time(23, 59),
                timezone="UTC",
                volume_factor=1.0,
                volatility_factor=1.5
            )
        ]
        
        self.market_schedules["CRYPTO"] = MarketSchedule(
            market_name="Cryptocurrency Markets",
            market_type=MarketType.CRYPTO,
            timezone="UTC",
            sessions=crypto_sessions,
            holidays=[],
            early_close_days={}
        )
    
    def _initialize_holiday_calendars(self):
        """Inicializar calendarios de días festivos"""
        
        # Días festivos estadounidenses (mercados de valores)
        us_holidays = holidays.UnitedStates(years=range(2020, 2030))
        
        # Días festivos específicos del mercado de valores
        market_specific_holidays = [
            # Añadir días específicos como Good Friday, etc.
        ]
        
        self.holiday_calendars["US"] = us_holidays
        
        # Días de cierre temprano típicos
        early_close_dates = {
            # Black Friday (día después de Thanksgiving)
            # Christmas Eve
            # New Year's Eve
        }
        
        # Actualizar horarios de mercado con días festivos
        if "US_EQUITY" in self.market_schedules:
            self.market_schedules["US_EQUITY"].holidays = list(us_holidays.keys())
    
    def get_current_market_status(self, market_name: str, 
                                current_time: Optional[datetime] = None) -> MarketStatus:
        """
        Obtener estado actual del mercado
        
        Args:
            market_name: Nombre del mercado
            current_time: Tiempo actual (default: ahora)
            
        Returns:
            MarketStatus: Estado actual del mercado
        """
        if current_time is None:
            current_time = datetime.now(pytz.UTC)
        
        if market_name not in self.market_schedules:
            raise ValueError(f"Mercado {market_name} no encontrado")
        
        schedule = self.market_schedules[market_name]
        
        # Convertir tiempo a zona horaria del mercado
        market_tz = pytz.timezone(schedule.timezone)
        market_time = current_time.astimezone(market_tz)
        
        # Verificar si es día de trading
        is_trading_day = self._is_trading_day(market_time.date(), schedule)
        
        if not is_trading_day:
            return MarketStatus(
                market_name=market_name,
                current_status=MarketStatus.HOLIDAY if self._is_holiday(market_time.date(), schedule) else MarketStatus.WEEKEND,
                current_session=None,
                next_session=self._get_next_session(market_time, schedule),
                time_to_next_session=self._time_to_next_session(market_time, schedule),
                is_trading_day=False,
                session_progress=0.0,
                volume_factor=0.0,
                volatility_factor=1.0
            )
        
        # Encontrar sesión actual
        current_session = self._get_current_session(market_time, schedule)
        
        if current_session:
            # Calcular progreso en la sesión
            session_progress = self._calculate_session_progress(market_time, current_session)
            
            return MarketStatus(
                market_name=market_name,
                current_status=self._session_to_market_status(current_session.session_type),
                current_session=current_session,
                next_session=self._get_next_session(market_time, schedule),
                time_to_next_session=self._time_to_next_session(market_time, schedule),
                is_trading_day=True,
                session_progress=session_progress,
                volume_factor=current_session.volume_factor,
                volatility_factor=current_session.volatility_factor
            )
        else:
            return MarketStatus(
                market_name=market_name,
                current_status=MarketStatus.CLOSED,
                current_session=None,
                next_session=self._get_next_session(market_time, schedule),
                time_to_next_session=self._time_to_next_session(market_time, schedule),
                is_trading_day=True,
                session_progress=0.0,
                volume_factor=0.0,
                volatility_factor=1.0
            )
    
    def _is_trading_day(self, date: datetime.date, schedule: MarketSchedule) -> bool:
        """Verificar si es día de trading"""
        
        # Verificar fin de semana
        if date.weekday() >= 5:  # Sábado = 5, Domingo = 6
            return False
        
        # Verificar días festivos
        if self._is_holiday(date, schedule):
            return False
        
        return True
    
    def _is_holiday(self, date: datetime.date, schedule: MarketSchedule) -> bool:
        """Verificar si es día festivo"""
        
        # Verificar en calendario de días festivos
        if schedule.market_type == MarketType.US_EQUITY:
            us_holidays = self.holiday_calendars.get("US", {})
            return date in us_holidays
        
        # Crypto y Forex no tienen días festivos
        if schedule.market_type in [MarketType.CRYPTO, MarketType.FOREX]:
            return False
        
        return False
    
    def _get_current_session(self, market_time: datetime, 
                           schedule: MarketSchedule) -> Optional[TradingSession]:
        """Obtener sesión actual del mercado"""
        
        current_time = market_time.time()
        
        for session in schedule.sessions:
            if not session.is_active:
                continue
            
            # Manejar sesiones que cruzan medianoche
            if session.start_time > session.end_time:
                # Sesión cruza medianoche
                if current_time >= session.start_time or current_time <= session.end_time:
                    return session
            else:
                # Sesión normal
                if session.start_time <= current_time <= session.end_time:
                    return session
        
        return None
    
    def _get_next_session(self, market_time: datetime, 
                         schedule: MarketSchedule) -> Optional[TradingSession]:
        """Obtener próxima sesión de trading"""
        
        current_time = market_time.time()
        current_date = market_time.date()
        
        # Buscar próxima sesión en el mismo día
        for session in schedule.sessions:
            if not session.is_active:
                continue
            
            if session.start_time > current_time:
                return session
        
        # Si no hay más sesiones hoy, buscar en el próximo día de trading
        next_date = current_date + timedelta(days=1)
        while not self._is_trading_day(next_date, schedule):
            next_date += timedelta(days=1)
            if (next_date - current_date).days > 7:  # Evitar bucle infinito
                break
        
        # Retornar primera sesión del próximo día de trading
        if schedule.sessions:
            return schedule.sessions[0]
        
        return None
    
    def _time_to_next_session(self, market_time: datetime, 
                            schedule: MarketSchedule) -> Optional[timedelta]:
        """Calcular tiempo hasta la próxima sesión"""
        
        next_session = self._get_next_session(market_time, schedule)
        if not next_session:
            return None
        
        current_time = market_time.time()
        current_date = market_time.date()
        
        # Calcular tiempo hasta próxima sesión
        if next_session.start_time > current_time:
            # Próxima sesión es hoy
            next_session_datetime = datetime.combine(current_date, next_session.start_time)
            next_session_datetime = pytz.timezone(schedule.timezone).localize(next_session_datetime)
        else:
            # Próxima sesión es mañana o después
            next_date = current_date + timedelta(days=1)
            while not self._is_trading_day(next_date, schedule):
                next_date += timedelta(days=1)
            
            next_session_datetime = datetime.combine(next_date, next_session.start_time)
            next_session_datetime = pytz.timezone(schedule.timezone).localize(next_session_datetime)
        
        return next_session_datetime - market_time
    
    def _calculate_session_progress(self, market_time: datetime, 
                                  session: TradingSession) -> float:
        """Calcular progreso en la sesión actual (0-1)"""
        
        current_time = market_time.time()
        
        # Convertir tiempos a minutos desde medianoche
        def time_to_minutes(t):
            return t.hour * 60 + t.minute
        
        start_minutes = time_to_minutes(session.start_time)
        end_minutes = time_to_minutes(session.end_time)
        current_minutes = time_to_minutes(current_time)
        
        # Manejar sesiones que cruzan medianoche
        if start_minutes > end_minutes:
            if current_minutes >= start_minutes:
                # Estamos en la parte del día anterior
                total_minutes = (24 * 60 - start_minutes) + end_minutes
                elapsed_minutes = current_minutes - start_minutes
            else:
                # Estamos en la parte del día siguiente
                total_minutes = (24 * 60 - start_minutes) + end_minutes
                elapsed_minutes = (24 * 60 - start_minutes) + current_minutes
        else:
            # Sesión normal
            total_minutes = end_minutes - start_minutes
            elapsed_minutes = current_minutes - start_minutes
        
        if total_minutes <= 0:
            return 0.0
        
        progress = elapsed_minutes / total_minutes
        return max(0.0, min(1.0, progress))
    
    def _session_to_market_status(self, session_type: SessionType) -> MarketStatus:
        """Convertir tipo de sesión a estado de mercado"""
        
        mapping = {
            SessionType.PRE_MARKET: MarketStatus.PRE_MARKET,
            SessionType.REGULAR: MarketStatus.OPEN,
            SessionType.AFTER_HOURS: MarketStatus.AFTER_HOURS,
            SessionType.EXTENDED: MarketStatus.OPEN,
            SessionType.OVERNIGHT: MarketStatus.OPEN,
            SessionType.CLOSED: MarketStatus.CLOSED
        }
        
        return mapping.get(session_type, MarketStatus.CLOSED)
    
    def get_trading_calendar(self, market_name: str, 
                           start_date: datetime, 
                           end_date: datetime) -> pd.DataFrame:
        """
        Generar calendario de trading para un período
        
        Args:
            market_name: Nombre del mercado
            start_date: Fecha de inicio
            end_date: Fecha de fin
            
        Returns:
            pd.DataFrame: Calendario con días de trading y sesiones
        """
        
        if market_name not in self.market_schedules:
            raise ValueError(f"Mercado {market_name} no encontrado")
        
        schedule = self.market_schedules[market_name]
        
        # Generar rango de fechas
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        calendar_data = []
        
        for date in date_range:
            is_trading = self._is_trading_day(date.date(), schedule)
            is_holiday = self._is_holiday(date.date(), schedule)
            
            # Obtener sesiones del día
            sessions_info = []
            if is_trading:
                for session in schedule.sessions:
                    if session.is_active:
                        sessions_info.append({
                            'name': session.name,
                            'type': session.session_type.value,
                            'start': session.start_time.strftime('%H:%M'),
                            'end': session.end_time.strftime('%H:%M'),
                            'volume_factor': session.volume_factor,
                            'volatility_factor': session.volatility_factor
                        })
            
            calendar_data.append({
                'date': date.date(),
                'is_trading_day': is_trading,
                'is_holiday': is_holiday,
                'is_weekend': date.weekday() >= 5,
                'sessions': sessions_info,
                'total_sessions': len(sessions_info)
            })
        
        return pd.DataFrame(calendar_data)
    
    def get_optimal_trading_hours(self, market_name: str, 
                                criteria: str = "volume") -> List[TradingSession]:
        """
        Obtener horas óptimas de trading basadas en criterios
        
        Args:
            market_name: Nombre del mercado
            criteria: Criterio de optimización ("volume", "volatility", "both")
            
        Returns:
            List[TradingSession]: Sesiones ordenadas por criterio
        """
        
        if market_name not in self.market_schedules:
            raise ValueError(f"Mercado {market_name} no encontrado")
        
        schedule = self.market_schedules[market_name]
        sessions = [s for s in schedule.sessions if s.is_active]
        
        if criteria == "volume":
            return sorted(sessions, key=lambda x: x.volume_factor, reverse=True)
        elif criteria == "volatility":
            return sorted(sessions, key=lambda x: x.volatility_factor, reverse=True)
        elif criteria == "both":
            return sorted(sessions, 
                         key=lambda x: x.volume_factor * x.volatility_factor, 
                         reverse=True)
        else:
            return sessions
    
    def is_market_overlap(self, market1: str, market2: str, 
                         current_time: Optional[datetime] = None) -> bool:
        """
        Verificar si dos mercados tienen sesiones superpuestas
        
        Args:
            market1: Primer mercado
            market2: Segundo mercado
            current_time: Tiempo actual
            
        Returns:
            bool: True si hay superposición
        """
        
        if current_time is None:
            current_time = datetime.now(pytz.UTC)
        
        status1 = self.get_current_market_status(market1, current_time)
        status2 = self.get_current_market_status(market2, current_time)
        
        # Ambos mercados deben estar abiertos
        return (status1.current_status in [MarketStatus.OPEN, MarketStatus.PRE_MARKET, MarketStatus.AFTER_HOURS] and
                status2.current_status in [MarketStatus.OPEN, MarketStatus.PRE_MARKET, MarketStatus.AFTER_HOURS])
    
    def get_market_summary(self, current_time: Optional[datetime] = None) -> Dict:
        """
        Obtener resumen de todos los mercados
        
        Args:
            current_time: Tiempo actual
            
        Returns:
            Dict: Resumen de estados de mercados
        """
        
        if current_time is None:
            current_time = datetime.now(pytz.UTC)
        
        summary = {
            'timestamp': current_time.isoformat(),
            'markets': {},
            'active_markets': [],
            'upcoming_sessions': []
        }
        
        for market_name in self.market_schedules.keys():
            try:
                status = self.get_current_market_status(market_name, current_time)
                
                summary['markets'][market_name] = {
                    'status': status.current_status.value,
                    'is_trading': status.current_status in [MarketStatus.OPEN, MarketStatus.PRE_MARKET, MarketStatus.AFTER_HOURS],
                    'current_session': status.current_session.name if status.current_session else None,
                    'session_progress': status.session_progress,
                    'volume_factor': status.volume_factor,
                    'volatility_factor': status.volatility_factor,
                    'time_to_next_session': str(status.time_to_next_session) if status.time_to_next_session else None
                }
                
                if status.current_status in [MarketStatus.OPEN, MarketStatus.PRE_MARKET, MarketStatus.AFTER_HOURS]:
                    summary['active_markets'].append(market_name)
                
                if status.next_session and status.time_to_next_session:
                    summary['upcoming_sessions'].append({
                        'market': market_name,
                        'session': status.next_session.name,
                        'time_to_start': str(status.time_to_next_session)
                    })
                    
            except Exception as e:
                summary['markets'][market_name] = {'error': str(e)}
        
        return summary
    
    def add_custom_market(self, market_name: str, schedule: MarketSchedule):
        """
        Añadir mercado personalizado
        
        Args:
            market_name: Nombre del mercado
            schedule: Horario del mercado
        """
        self.market_schedules[market_name] = schedule
    
    def export_to_dict(self) -> Dict:
        """
        Exportar configuración completa a diccionario
        
        Returns:
            Dict: Configuración completa del sistema
        """
        
        export_data = {
            'markets': {},
            'holiday_calendars': {},
            'system_info': {
                'total_markets': len(self.market_schedules),
                'supported_timezones': list(set(s.timezone for s in self.market_schedules.values())),
                'last_updated': datetime.now().isoformat()
            }
        }
        
        # Exportar horarios de mercados
        for name, schedule in self.market_schedules.items():
            export_data['markets'][name] = {
                'market_name': schedule.market_name,
                'market_type': schedule.market_type.value,
                'timezone': schedule.timezone,
                'sessions': [
                    {
                        'name': s.name,
                        'type': s.session_type.value,
                        'start_time': s.start_time.strftime('%H:%M:%S'),
                        'end_time': s.end_time.strftime('%H:%M:%S'),
                        'timezone': s.timezone,
                        'is_active': s.is_active,
                        'volume_factor': s.volume_factor,
                        'volatility_factor': s.volatility_factor
                    }
                    for s in schedule.sessions
                ],
                'total_holidays': len(schedule.holidays),
                'early_close_days': len(schedule.early_close_days)
            }
        
        return export_data

# Función de utilidad para uso rápido
def get_market_status_summary(markets: List[str] = None) -> Dict:
    """
    Función de utilidad para obtener resumen rápido de mercados
    
    Args:
        markets: Lista de mercados específicos (default: todos)
        
    Returns:
        Dict: Resumen de estados de mercados
    """
    
    market_hours = AdvancedMarketHours()
    
    if markets is None:
        return market_hours.get_market_summary()
    
    summary = market_hours.get_market_summary()
    filtered_summary = {
        'timestamp': summary['timestamp'],
        'markets': {k: v for k, v in summary['markets'].items() if k in markets},
        'active_markets': [m for m in summary['active_markets'] if m in markets],
        'upcoming_sessions': [s for s in summary['upcoming_sessions'] if s['market'] in markets]
    }
    
    return filtered_summary

if __name__ == "__main__":
    # Demo del sistema de horarios de mercado
    print("=== SICAR Advanced Market Hours Demo ===")
    
    market_hours = AdvancedMarketHours()
    
    # Obtener resumen de todos los mercados
    summary = market_hours.get_market_summary()
    
    print(f"\n📅 Resumen de Mercados ({summary['timestamp'][:19]})")
    print(f"🟢 Mercados Activos: {len(summary['active_markets'])}")
    
    for market, info in summary['markets'].items():
        if 'error' not in info:
            status_emoji = "🟢" if info['is_trading'] else "🔴"
            print(f"{status_emoji} {market}: {info['status']}")
            if info['current_session']:
                print(f"   📊 Sesión: {info['current_session']} ({info['session_progress']:.1%})")
                print(f"   📈 Volumen: {info['volume_factor']:.1f}x | Volatilidad: {info['volatility_factor']:.1f}x")
    
    # Mostrar próximas sesiones
    if summary['upcoming_sessions']:
        print(f"\n⏰ Próximas Sesiones:")
        for session in summary['upcoming_sessions'][:3]:
            print(f"   {session['market']}: {session['session']} en {session['time_to_start']}")
    
    # Ejemplo de calendario de trading
    print(f"\n📅 Calendario US_EQUITY (próximos 7 días):")
    start_date = datetime.now()
    end_date = start_date + timedelta(days=7)
    
    try:
        calendar = market_hours.get_trading_calendar("US_EQUITY", start_date, end_date)
        for _, day in calendar.iterrows():
            trading_emoji = "📈" if day['is_trading_day'] else "🚫"
            holiday_emoji = "🎉" if day['is_holiday'] else ""
            weekend_emoji = "🏖️" if day['is_weekend'] else ""
            
            print(f"   {trading_emoji} {day['date']} - {day['total_sessions']} sesiones {holiday_emoji}{weekend_emoji}")
    except Exception as e:
        print(f"   Error generando calendario: {e}")