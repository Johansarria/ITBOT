"""
SICAR - Conector TD Ameritrade
=============================

Este módulo proporciona conectividad con TD Ameritrade para trading de índices ETF.
Incluye autenticación OAuth, gestión de órdenes, datos de mercado y gestión de cuentas.

Autor: SICAR Team
Fecha: Enero 2025
"""

import asyncio
import aiohttp
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from urllib.parse import urlencode, parse_qs, urlparse

class TDAOrderType(Enum):
    """Tipos de órdenes TD Ameritrade"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"

class TDAOrderInstruction(Enum):
    """Instrucciones de orden"""
    BUY = "BUY"
    SELL = "SELL"
    BUY_TO_COVER = "BUY_TO_COVER"
    SELL_SHORT = "SELL_SHORT"

class TDAOrderStatus(Enum):
    """Estados de orden TD Ameritrade"""
    AWAITING_PARENT_ORDER = "AWAITING_PARENT_ORDER"
    AWAITING_CONDITION = "AWAITING_CONDITION"
    AWAITING_MANUAL_REVIEW = "AWAITING_MANUAL_REVIEW"
    ACCEPTED = "ACCEPTED"
    AWAITING_UR_OUT = "AWAITING_UR_OUT"
    PENDING_ACTIVATION = "PENDING_ACTIVATION"
    QUEUED = "QUEUED"
    WORKING = "WORKING"
    REJECTED = "REJECTED"
    PENDING_CANCEL = "PENDING_CANCEL"
    CANCELED = "CANCELED"
    PENDING_REPLACE = "PENDING_REPLACE"
    REPLACED = "REPLACED"
    FILLED = "FILLED"
    EXPIRED = "EXPIRED"

class TDAAssetType(Enum):
    """Tipos de activos"""
    EQUITY = "EQUITY"
    ETF = "ETF"
    OPTION = "OPTION"
    MUTUAL_FUND = "MUTUAL_FUND"

@dataclass
class TDAOrder:
    """Representación de una orden TD Ameritrade"""
    order_id: Optional[str] = None
    symbol: str = ""
    instruction: TDAOrderInstruction = TDAOrderInstruction.BUY
    order_type: TDAOrderType = TDAOrderType.MARKET
    quantity: int = 0
    price: Optional[float] = None
    stop_price: Optional[float] = None
    duration: str = "DAY"
    session: str = "NORMAL"
    status: TDAOrderStatus = TDAOrderStatus.WORKING
    filled_quantity: int = 0
    remaining_quantity: int = 0
    avg_fill_price: float = 0.0
    total_fees: float = 0.0
    entered_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    tag: str = "SICAR"

@dataclass
class TDAPosition:
    """Representación de una posición TD Ameritrade"""
    symbol: str
    asset_type: TDAAssetType
    quantity: float
    average_price: float
    market_value: float
    day_pnl: float
    day_pnl_percentage: float
    long_quantity: float = 0.0
    short_quantity: float = 0.0
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class TDAQuote:
    """Cotización TD Ameritrade"""
    symbol: str
    asset_type: TDAAssetType
    bid_price: float
    ask_price: float
    last_price: float
    bid_size: int
    ask_size: int
    total_volume: int
    high_price: float
    low_price: float
    open_price: float
    close_price: float
    change: float
    change_percent: float
    volatility: float
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class TDAAccount:
    """Información de cuenta TD Ameritrade"""
    account_id: str
    account_type: str
    current_balances: Dict[str, float] = field(default_factory=dict)
    initial_balances: Dict[str, float] = field(default_factory=dict)
    positions: List[TDAPosition] = field(default_factory=list)
    orders: List[TDAOrder] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.now)

class TDAmeritradeConnector:
    """
    Conector principal para TD Ameritrade API
    """
    
    def __init__(self, client_id: str, redirect_uri: str = "https://localhost"):
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        
        self.logger = logging.getLogger(__name__)
        
        # URLs de la API
        self.base_url = "https://api.tdameritrade.com/v1"
        self.auth_url = "https://auth.tdameritrade.com/auth"
        
        # Tokens de autenticación
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        
        # Sesión HTTP
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Datos almacenados
        self.accounts: Dict[str, TDAAccount] = {}
        self.quotes: Dict[str, TDAQuote] = {}
        self.orders: Dict[str, TDAOrder] = {}
        
        # Configuración
        self.max_retries = 3
        self.retry_delay = 1
        self.rate_limit_delay = 0.5  # TD Ameritrade tiene límites de rate
        
        # Estadísticas
        self.api_calls_made = 0
        self.successful_calls = 0
        self.failed_calls = 0
        
    async def __aenter__(self):
        """Entrada del context manager"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Salida del context manager"""
        if self.session:
            await self.session.close()
    
    def get_auth_url(self) -> str:
        """
        Obtener URL de autorización para OAuth
        
        Returns:
            str: URL de autorización
        """
        params = {
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'client_id': f"{self.client_id}@AMER.OAUTHAP"
        }
        
        auth_url = f"{self.auth_url}?{urlencode(params)}"
        self.logger.info("URL de autorización generada")
        return auth_url
    
    async def authenticate_with_code(self, authorization_code: str) -> bool:
        """
        Autenticar usando código de autorización
        
        Args:
            authorization_code: Código obtenido del flujo OAuth
            
        Returns:
            bool: True si la autenticación es exitosa
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Datos para obtener token
            data = {
                'grant_type': 'authorization_code',
                'refresh_token': '',
                'access_type': 'offline',
                'code': authorization_code,
                'client_id': f"{self.client_id}@AMER.OAUTHAP",
                'redirect_uri': self.redirect_uri
            }
            
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            
            async with self.session.post(
                f"{self.base_url}/oauth2/token",
                data=urlencode(data),
                headers=headers
            ) as response:
                
                if response.status == 200:
                    token_data = await response.json()
                    
                    self.access_token = token_data.get('access_token')
                    self.refresh_token = token_data.get('refresh_token')
                    
                    # Calcular expiración
                    expires_in = token_data.get('expires_in', 1800)  # 30 minutos por defecto
                    self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                    
                    self.logger.info("Autenticación exitosa")
                    return True
                else:
                    error_text = await response.text()
                    self.logger.error(f"Error en autenticación: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error en autenticación: {e}")
            return False
    
    async def refresh_access_token(self) -> bool:
        """
        Refrescar token de acceso
        
        Returns:
            bool: True si el refresh es exitoso
        """
        try:
            if not self.refresh_token:
                self.logger.error("No hay refresh token disponible")
                return False
            
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': f"{self.client_id}@AMER.OAUTHAP"
            }
            
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            
            async with self.session.post(
                f"{self.base_url}/oauth2/token",
                data=urlencode(data),
                headers=headers
            ) as response:
                
                if response.status == 200:
                    token_data = await response.json()
                    
                    self.access_token = token_data.get('access_token')
                    
                    # Actualizar expiración
                    expires_in = token_data.get('expires_in', 1800)
                    self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                    
                    self.logger.info("Token refrescado exitosamente")
                    return True
                else:
                    self.logger.error(f"Error refrescando token: {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error refrescando token: {e}")
            return False
    
    async def _ensure_valid_token(self) -> bool:
        """Asegurar que el token sea válido"""
        if not self.access_token:
            return False
        
        # Verificar si el token está por expirar (5 minutos antes)
        if self.token_expires_at and datetime.now() >= (self.token_expires_at - timedelta(minutes=5)):
            return await self.refresh_access_token()
        
        return True
    
    async def _make_api_call(self, method: str, endpoint: str, 
                           params: Optional[Dict] = None,
                           data: Optional[Dict] = None) -> Optional[Dict]:
        """
        Realizar llamada a la API con manejo de errores y rate limiting
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            endpoint: Endpoint de la API
            params: Parámetros de query
            data: Datos del body
            
        Returns:
            Respuesta de la API o None si hay error
        """
        try:
            if not await self._ensure_valid_token():
                self.logger.error("Token inválido o expirado")
                return None
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            url = f"{self.base_url}{endpoint}"
            
            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)
            
            self.api_calls_made += 1
            
            async with self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=headers
            ) as response:
                
                if response.status == 200:
                    self.successful_calls += 1
                    return await response.json()
                elif response.status == 401:
                    # Token expirado, intentar refresh
                    if await self.refresh_access_token():
                        headers['Authorization'] = f'Bearer {self.access_token}'
                        # Reintentar la llamada
                        async with self.session.request(
                            method=method,
                            url=url,
                            params=params,
                            json=data,
                            headers=headers
                        ) as retry_response:
                            if retry_response.status == 200:
                                self.successful_calls += 1
                                return await retry_response.json()
                    
                    self.failed_calls += 1
                    self.logger.error("Error de autenticación no resuelto")
                    return None
                else:
                    self.failed_calls += 1
                    error_text = await response.text()
                    self.logger.error(f"Error API: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            self.failed_calls += 1
            self.logger.error(f"Error en llamada API: {e}")
            return None
    
    async def get_accounts(self) -> List[TDAAccount]:
        """
        Obtener información de cuentas
        
        Returns:
            Lista de cuentas
        """
        try:
            response = await self._make_api_call('GET', '/accounts', {'fields': 'positions,orders'})
            
            if not response:
                return []
            
            accounts = []
            for account_data in response:
                account_info = account_data.get('securitiesAccount', {})
                
                # Crear objeto cuenta
                account = TDAAccount(
                    account_id=account_info.get('accountId', ''),
                    account_type=account_info.get('type', ''),
                    current_balances=account_info.get('currentBalances', {}),
                    initial_balances=account_info.get('initialBalances', {})
                )
                
                # Procesar posiciones
                positions_data = account_info.get('positions', [])
                for pos_data in positions_data:
                    instrument = pos_data.get('instrument', {})
                    position = TDAPosition(
                        symbol=instrument.get('symbol', ''),
                        asset_type=TDAAssetType(instrument.get('assetType', 'EQUITY')),
                        quantity=pos_data.get('longQuantity', 0) - pos_data.get('shortQuantity', 0),
                        average_price=pos_data.get('averagePrice', 0),
                        market_value=pos_data.get('marketValue', 0),
                        day_pnl=pos_data.get('currentDayProfitLoss', 0),
                        day_pnl_percentage=pos_data.get('currentDayProfitLossPercentage', 0),
                        long_quantity=pos_data.get('longQuantity', 0),
                        short_quantity=pos_data.get('shortQuantity', 0)
                    )
                    account.positions.append(position)
                
                # Procesar órdenes
                orders_data = account_info.get('orderStrategies', [])
                for order_data in orders_data:
                    order = self._parse_order_data(order_data)
                    if order:
                        account.orders.append(order)
                
                accounts.append(account)
                self.accounts[account.account_id] = account
            
            self.logger.info(f"Obtenidas {len(accounts)} cuentas")
            return accounts
            
        except Exception as e:
            self.logger.error(f"Error obteniendo cuentas: {e}")
            return []
    
    def _parse_order_data(self, order_data: Dict) -> Optional[TDAOrder]:
        """Parsear datos de orden de la API"""
        try:
            order_leg = order_data.get('orderLegCollection', [{}])[0]
            instrument = order_leg.get('instrument', {})
            
            order = TDAOrder(
                order_id=str(order_data.get('orderId', '')),
                symbol=instrument.get('symbol', ''),
                instruction=TDAOrderInstruction(order_leg.get('instruction', 'BUY')),
                order_type=TDAOrderType(order_data.get('orderType', 'MARKET')),
                quantity=int(order_leg.get('quantity', 0)),
                price=order_data.get('price'),
                stop_price=order_data.get('stopPrice'),
                duration=order_data.get('duration', 'DAY'),
                session=order_data.get('session', 'NORMAL'),
                status=TDAOrderStatus(order_data.get('status', 'WORKING')),
                filled_quantity=int(order_data.get('filledQuantity', 0)),
                remaining_quantity=int(order_data.get('remainingQuantity', 0)),
                tag=order_data.get('tag', 'SICAR')
            )
            
            # Parsear fechas
            if order_data.get('enteredTime'):
                order.entered_time = datetime.fromisoformat(order_data['enteredTime'].replace('Z', '+00:00'))
            
            if order_data.get('closeTime'):
                order.close_time = datetime.fromisoformat(order_data['closeTime'].replace('Z', '+00:00'))
            
            return order
            
        except Exception as e:
            self.logger.error(f"Error parseando orden: {e}")
            return None
    
    async def place_order(self, account_id: str, order: TDAOrder) -> Optional[str]:
        """
        Colocar una orden
        
        Args:
            account_id: ID de la cuenta
            order: Orden a colocar
            
        Returns:
            ID de la orden o None si hay error
        """
        try:
            # Construir payload de la orden
            order_payload = {
                "orderType": order.order_type.value,
                "session": order.session,
                "duration": order.duration,
                "orderStrategyType": "SINGLE",
                "orderLegCollection": [
                    {
                        "instruction": order.instruction.value,
                        "quantity": order.quantity,
                        "instrument": {
                            "symbol": order.symbol,
                            "assetType": "ETF"  # Asumiendo ETFs para índices
                        }
                    }
                ]
            }
            
            # Agregar precio si es orden LIMIT
            if order.order_type == TDAOrderType.LIMIT and order.price:
                order_payload["price"] = order.price
            
            # Agregar stop price si es orden STOP
            if order.order_type in [TDAOrderType.STOP, TDAOrderType.STOP_LIMIT] and order.stop_price:
                order_payload["stopPrice"] = order.stop_price
                if order.order_type == TDAOrderType.STOP_LIMIT and order.price:
                    order_payload["price"] = order.price
            
            response = await self._make_api_call(
                'POST',
                f'/accounts/{account_id}/orders',
                data=order_payload
            )
            
            if response is not None:
                # TD Ameritrade devuelve el ID en el header Location
                # Para simulación, generar ID
                order_id = f"TDA_{int(time.time())}"
                order.order_id = order_id
                self.orders[order_id] = order
                
                self.logger.info(f"Orden colocada: {order_id} - {order.instruction.value} {order.quantity} {order.symbol}")
                return order_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error colocando orden: {e}")
            return None
    
    async def cancel_order(self, account_id: str, order_id: str) -> bool:
        """
        Cancelar una orden
        
        Args:
            account_id: ID de la cuenta
            order_id: ID de la orden
            
        Returns:
            bool: True si la cancelación es exitosa
        """
        try:
            response = await self._make_api_call(
                'DELETE',
                f'/accounts/{account_id}/orders/{order_id}'
            )
            
            if response is not None:
                # Actualizar estado local
                if order_id in self.orders:
                    self.orders[order_id].status = TDAOrderStatus.CANCELED
                
                self.logger.info(f"Orden {order_id} cancelada")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error cancelando orden {order_id}: {e}")
            return False
    
    async def get_quotes(self, symbols: List[str]) -> Dict[str, TDAQuote]:
        """
        Obtener cotizaciones para múltiples símbolos
        
        Args:
            symbols: Lista de símbolos
            
        Returns:
            Diccionario de cotizaciones
        """
        try:
            symbols_str = ','.join(symbols)
            response = await self._make_api_call(
                'GET',
                '/marketdata/quotes',
                params={'symbol': symbols_str}
            )
            
            if not response:
                return {}
            
            quotes = {}
            for symbol, quote_data in response.items():
                quote = TDAQuote(
                    symbol=symbol,
                    asset_type=TDAAssetType(quote_data.get('assetType', 'ETF')),
                    bid_price=quote_data.get('bidPrice', 0),
                    ask_price=quote_data.get('askPrice', 0),
                    last_price=quote_data.get('lastPrice', 0),
                    bid_size=quote_data.get('bidSize', 0),
                    ask_size=quote_data.get('askSize', 0),
                    total_volume=quote_data.get('totalVolume', 0),
                    high_price=quote_data.get('highPrice', 0),
                    low_price=quote_data.get('lowPrice', 0),
                    open_price=quote_data.get('openPrice', 0),
                    close_price=quote_data.get('closePrice', 0),
                    change=quote_data.get('netChange', 0),
                    change_percent=quote_data.get('netPercentChangeInDouble', 0),
                    volatility=quote_data.get('volatility', 0)
                )
                
                quotes[symbol] = quote
                self.quotes[symbol] = quote
            
            self.logger.info(f"Obtenidas cotizaciones para {len(quotes)} símbolos")
            return quotes
            
        except Exception as e:
            self.logger.error(f"Error obteniendo cotizaciones: {e}")
            return {}
    
    async def get_price_history(self, symbol: str, period_type: str = "day",
                              period: int = 1, frequency_type: str = "minute",
                              frequency: int = 1) -> pd.DataFrame:
        """
        Obtener historial de precios
        
        Args:
            symbol: Símbolo del instrumento
            period_type: Tipo de período (day, month, year, ytd)
            period: Número de períodos
            frequency_type: Tipo de frecuencia (minute, daily, weekly, monthly)
            frequency: Frecuencia
            
        Returns:
            DataFrame con datos históricos
        """
        try:
            params = {
                'periodType': period_type,
                'period': period,
                'frequencyType': frequency_type,
                'frequency': frequency
            }
            
            response = await self._make_api_call(
                'GET',
                f'/marketdata/{symbol}/pricehistory',
                params=params
            )
            
            if not response or 'candles' not in response:
                return pd.DataFrame()
            
            candles = response['candles']
            
            # Convertir a DataFrame
            data = []
            for candle in candles:
                data.append({
                    'datetime': pd.to_datetime(candle['datetime'], unit='ms'),
                    'open': candle['open'],
                    'high': candle['high'],
                    'low': candle['low'],
                    'close': candle['close'],
                    'volume': candle['volume']
                })
            
            df = pd.DataFrame(data)
            if not df.empty:
                df.set_index('datetime', inplace=True)
            
            self.logger.info(f"Obtenidos {len(df)} datos históricos para {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error obteniendo historial para {symbol}: {e}")
            return pd.DataFrame()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas del conector"""
        success_rate = (self.successful_calls / max(self.api_calls_made, 1)) * 100
        
        return {
            'authenticated': self.access_token is not None,
            'token_expires_at': self.token_expires_at.isoformat() if self.token_expires_at else None,
            'api_calls_made': self.api_calls_made,
            'successful_calls': self.successful_calls,
            'failed_calls': self.failed_calls,
            'success_rate': success_rate,
            'accounts_loaded': len(self.accounts),
            'quotes_cached': len(self.quotes),
            'orders_tracked': len(self.orders)
        }

# Función de utilidad para autenticación
async def authenticate_td_ameritrade(client_id: str, 
                                   redirect_uri: str = "https://localhost") -> Optional[TDAmeritradeConnector]:
    """
    Función de utilidad para autenticación interactiva
    
    Args:
        client_id: Client ID de TD Ameritrade
        redirect_uri: URI de redirección
        
    Returns:
        Conector autenticado o None
    """
    async with TDAmeritradeConnector(client_id, redirect_uri) as connector:
        # Obtener URL de autorización
        auth_url = connector.get_auth_url()
        
        print(f"Por favor, visita esta URL para autorizar la aplicación:")
        print(auth_url)
        print("\nDespués de autorizar, copia el código de la URL de redirección:")
        
        # En un entorno real, esto sería manejado por un servidor web
        authorization_code = input("Ingresa el código de autorización: ")
        
        if await connector.authenticate_with_code(authorization_code):
            return connector
        else:
            return None

# Demo y testing
if __name__ == "__main__":
    async def demo():
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        
        print("=== SICAR - Conector TD Ameritrade Demo ===\n")
        
        # Nota: Para demo, usar client_id ficticio
        client_id = "DEMO_CLIENT_ID"
        
        async with TDAmeritradeConnector(client_id) as connector:
            print("1. Generando URL de autorización...")
            auth_url = connector.get_auth_url()
            print(f"   URL: {auth_url[:50]}...")
            
            # Simular autenticación exitosa
            print("\n2. Simulando autenticación...")
            connector.access_token = "demo_access_token"
            connector.refresh_token = "demo_refresh_token"
            connector.token_expires_at = datetime.now() + timedelta(hours=1)
            print("   ✓ Autenticación simulada exitosa")
            
            # Simular obtención de cuentas
            print("\n3. Simulando obtención de cuentas...")
            # En demo, crear cuenta ficticia
            demo_account = TDAAccount(
                account_id="123456789",
                account_type="MARGIN",
                current_balances={
                    "liquidationValue": 100000.0,
                    "buyingPower": 200000.0,
                    "cashBalance": 50000.0
                }
            )
            connector.accounts["123456789"] = demo_account
            print(f"   ✓ Cuenta demo cargada: {demo_account.account_id}")
            
            # Simular cotizaciones
            print("\n4. Simulando obtención de cotizaciones...")
            symbols = ['SPY', 'QQQ', 'IWM']
            
            # Crear cotizaciones ficticias
            for symbol in symbols:
                base_price = {'SPY': 450, 'QQQ': 380, 'IWM': 200}.get(symbol, 100)
                quote = TDAQuote(
                    symbol=symbol,
                    asset_type=TDAAssetType.ETF,
                    bid_price=base_price - 0.01,
                    ask_price=base_price + 0.01,
                    last_price=base_price,
                    bid_size=100,
                    ask_size=100,
                    total_volume=1000000,
                    high_price=base_price + 2,
                    low_price=base_price - 2,
                    open_price=base_price - 0.5,
                    close_price=base_price - 0.3,
                    change=0.5,
                    change_percent=0.11,
                    volatility=0.15
                )
                connector.quotes[symbol] = quote
            
            print(f"   ✓ {len(symbols)} cotizaciones simuladas")
            
            # Mostrar cotizaciones
            for symbol in symbols:
                quote = connector.quotes[symbol]
                print(f"   {symbol}: ${quote.last_price:.2f} (${quote.change:+.2f}, {quote.change_percent:+.2f}%)")
            
            # Simular colocación de orden
            print("\n5. Simulando colocación de orden...")
            demo_order = TDAOrder(
                symbol='SPY',
                instruction=TDAOrderInstruction.BUY,
                order_type=TDAOrderType.MARKET,
                quantity=100
            )
            
            order_id = await connector.place_order("123456789", demo_order)
            if order_id:
                print(f"   ✓ Orden simulada colocada: {order_id}")
            
            # Simular datos históricos
            print("\n6. Simulando datos históricos...")
            # Crear DataFrame ficticio
            periods = 100
            dates = pd.date_range(end=datetime.now(), periods=periods, freq='1min')
            base_price = 450
            
            returns = np.random.normal(0, 0.001, periods)
            prices = base_price * np.exp(np.cumsum(returns))
            
            historical_data = pd.DataFrame({
                'open': prices * (1 + np.random.normal(0, 0.0005, periods)),
                'high': prices * (1 + np.abs(np.random.normal(0, 0.001, periods))),
                'low': prices * (1 - np.abs(np.random.normal(0, 0.001, periods))),
                'close': prices,
                'volume': np.random.randint(100000, 1000000, periods)
            }, index=dates)
            
            print(f"   ✓ {len(historical_data)} barras históricas simuladas")
            
            # Mostrar estadísticas
            print("\n7. Estadísticas del conector:")
            stats = connector.get_statistics()
            for key, value in stats.items():
                if isinstance(value, float):
                    print(f"   {key}: {value:.2f}")
                else:
                    print(f"   {key}: {value}")
        
        print("\n=== Demo Completado ===")
    
    # Ejecutar demo
    asyncio.run(demo())