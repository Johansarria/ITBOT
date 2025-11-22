"""
Sistema de Integración con Múltiples Exchanges - SICAR Fase 2
Conecta con Binance, Coinbase, Kraken y otros exchanges
"""

import asyncio
import aiohttp
import json
import hmac
import hashlib
import time
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import logging
from abc import ABC, abstractmethod

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExchangeType(Enum):
    """Tipos de exchanges soportados"""
    BINANCE = "binance"
    COINBASE = "coinbase"
    KRAKEN = "kraken"
    KUCOIN = "kucoin"
    BYBIT = "bybit"

class OrderSide(Enum):
    """Lado de la orden"""
    BUY = "buy"
    SELL = "sell"

class OrderType(Enum):
    """Tipo de orden"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

class OrderStatus(Enum):
    """Estado de la orden"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

@dataclass
class ExchangeCredentials:
    """Credenciales del exchange"""
    api_key: str
    api_secret: str
    passphrase: Optional[str] = None  # Para Coinbase Pro
    sandbox: bool = True  # Usar sandbox por defecto

@dataclass
class MarketData:
    """Datos de mercado"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    exchange: str

@dataclass
class OrderRequest:
    """Solicitud de orden"""
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None

@dataclass
class Order:
    """Orden ejecutada"""
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: float
    filled_quantity: float
    status: OrderStatus
    timestamp: datetime
    exchange: str
    commission: float = 0.0

@dataclass
class Balance:
    """Balance de cuenta"""
    asset: str
    free: float
    locked: float
    total: float
    exchange: str

class BaseExchange(ABC):
    """Clase base para todos los exchanges"""
    
    def __init__(self, credentials: ExchangeCredentials):
        self.credentials = credentials
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = ""
        self.name = ""
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def get_market_data(self, symbol: str, interval: str = "1d", limit: int = 100) -> List[MarketData]:
        """Obtener datos de mercado"""
        pass
    
    @abstractmethod
    async def place_order(self, order_request: OrderRequest) -> Order:
        """Colocar una orden"""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str, symbol: str) -> Order:
        """Obtener estado de una orden"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancelar una orden"""
        pass
    
    @abstractmethod
    async def get_balances(self) -> List[Balance]:
        """Obtener balances de cuenta"""
        pass
    
    @abstractmethod
    async def get_trading_fees(self, symbol: str) -> Tuple[float, float]:
        """Obtener comisiones de trading (maker, taker)"""
        pass

class BinanceExchange(BaseExchange):
    """Integración con Binance"""
    
    def __init__(self, credentials: ExchangeCredentials):
        super().__init__(credentials)
        self.name = "Binance"
        self.base_url = "https://testnet.binance.vision" if credentials.sandbox else "https://api.binance.com"
        
    def _generate_signature(self, query_string: str) -> str:
        """Generar firma para autenticación"""
        return hmac.new(
            self.credentials.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def get_market_data(self, symbol: str, interval: str = "1d", limit: int = 100) -> List[MarketData]:
        """Obtener datos de mercado de Binance"""
        try:
            url = f"{self.base_url}/api/v3/klines"
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    market_data = []
                    for kline in data:
                        market_data.append(MarketData(
                            symbol=symbol,
                            timestamp=datetime.fromtimestamp(kline[0] / 1000),
                            open=float(kline[1]),
                            high=float(kline[2]),
                            low=float(kline[3]),
                            close=float(kline[4]),
                            volume=float(kline[5]),
                            exchange=self.name
                        ))
                    
                    return market_data
                else:
                    logger.error(f"Error obteniendo datos de Binance: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error en get_market_data Binance: {e}")
            return []
    
    async def place_order(self, order_request: OrderRequest) -> Order:
        """Colocar orden en Binance"""
        try:
            timestamp = int(time.time() * 1000)
            
            params = {
                "symbol": order_request.symbol,
                "side": order_request.side.value.upper(),
                "type": order_request.order_type.value.upper(),
                "quantity": order_request.quantity,
                "timestamp": timestamp
            }
            
            if order_request.order_type == OrderType.LIMIT and order_request.price:
                params["price"] = order_request.price
                params["timeInForce"] = "GTC"
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            signature = self._generate_signature(query_string)
            params["signature"] = signature
            
            headers = {"X-MBX-APIKEY": self.credentials.api_key}
            
            url = f"{self.base_url}/api/v3/order"
            
            async with self.session.post(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    return Order(
                        id=str(data["orderId"]),
                        symbol=data["symbol"],
                        side=OrderSide(data["side"].lower()),
                        order_type=OrderType(data["type"].lower()),
                        quantity=float(data["origQty"]),
                        price=float(data.get("price", 0)),
                        filled_quantity=float(data["executedQty"]),
                        status=OrderStatus.FILLED if data["status"] == "FILLED" else OrderStatus.PENDING,
                        timestamp=datetime.fromtimestamp(data["transactTime"] / 1000),
                        exchange=self.name
                    )
                else:
                    error_data = await response.json()
                    logger.error(f"Error colocando orden en Binance: {error_data}")
                    raise Exception(f"Error en orden: {error_data}")
                    
        except Exception as e:
            logger.error(f"Error en place_order Binance: {e}")
            raise
    
    async def get_order_status(self, order_id: str, symbol: str) -> Order:
        """Obtener estado de orden en Binance"""
        try:
            timestamp = int(time.time() * 1000)
            
            params = {
                "symbol": symbol,
                "orderId": order_id,
                "timestamp": timestamp
            }
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            signature = self._generate_signature(query_string)
            params["signature"] = signature
            
            headers = {"X-MBX-APIKEY": self.credentials.api_key}
            
            url = f"{self.base_url}/api/v3/order"
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    return Order(
                        id=str(data["orderId"]),
                        symbol=data["symbol"],
                        side=OrderSide(data["side"].lower()),
                        order_type=OrderType(data["type"].lower()),
                        quantity=float(data["origQty"]),
                        price=float(data.get("price", 0)),
                        filled_quantity=float(data["executedQty"]),
                        status=OrderStatus.FILLED if data["status"] == "FILLED" else OrderStatus.PENDING,
                        timestamp=datetime.fromtimestamp(data["time"] / 1000),
                        exchange=self.name
                    )
                else:
                    logger.error(f"Error obteniendo estado de orden en Binance: {response.status}")
                    raise Exception("Error obteniendo estado de orden")
                    
        except Exception as e:
            logger.error(f"Error en get_order_status Binance: {e}")
            raise
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancelar orden en Binance"""
        try:
            timestamp = int(time.time() * 1000)
            
            params = {
                "symbol": symbol,
                "orderId": order_id,
                "timestamp": timestamp
            }
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            signature = self._generate_signature(query_string)
            params["signature"] = signature
            
            headers = {"X-MBX-APIKEY": self.credentials.api_key}
            
            url = f"{self.base_url}/api/v3/order"
            
            async with self.session.delete(url, params=params, headers=headers) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Error en cancel_order Binance: {e}")
            return False
    
    async def get_balances(self) -> List[Balance]:
        """Obtener balances de Binance"""
        try:
            timestamp = int(time.time() * 1000)
            
            params = {"timestamp": timestamp}
            query_string = f"timestamp={timestamp}"
            signature = self._generate_signature(query_string)
            params["signature"] = signature
            
            headers = {"X-MBX-APIKEY": self.credentials.api_key}
            
            url = f"{self.base_url}/api/v3/account"
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    balances = []
                    for balance_data in data["balances"]:
                        free = float(balance_data["free"])
                        locked = float(balance_data["locked"])
                        
                        if free > 0 or locked > 0:
                            balances.append(Balance(
                                asset=balance_data["asset"],
                                free=free,
                                locked=locked,
                                total=free + locked,
                                exchange=self.name
                            ))
                    
                    return balances
                else:
                    logger.error(f"Error obteniendo balances de Binance: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error en get_balances Binance: {e}")
            return []
    
    async def get_trading_fees(self, symbol: str) -> Tuple[float, float]:
        """Obtener comisiones de trading de Binance"""
        # Binance tiene comisiones estándar de 0.1% para maker y taker
        return (0.001, 0.001)  # (maker, taker)

class CoinbaseExchange(BaseExchange):
    """Integración con Coinbase Pro (simulada)"""
    
    def __init__(self, credentials: ExchangeCredentials):
        super().__init__(credentials)
        self.name = "Coinbase"
        self.base_url = "https://api-public.sandbox.pro.coinbase.com" if credentials.sandbox else "https://api.pro.coinbase.com"
    
    async def get_market_data(self, symbol: str, interval: str = "1d", limit: int = 100) -> List[MarketData]:
        """Obtener datos de mercado de Coinbase (simulado)"""
        # Implementación simulada
        logger.info(f"Obteniendo datos de mercado de Coinbase para {symbol}")
        return []
    
    async def place_order(self, order_request: OrderRequest) -> Order:
        """Colocar orden en Coinbase (simulado)"""
        logger.info(f"Colocando orden en Coinbase: {order_request}")
        raise NotImplementedError("Coinbase integration en desarrollo")
    
    async def get_order_status(self, order_id: str, symbol: str) -> Order:
        """Obtener estado de orden en Coinbase (simulado)"""
        raise NotImplementedError("Coinbase integration en desarrollo")
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancelar orden en Coinbase (simulado)"""
        return False
    
    async def get_balances(self) -> List[Balance]:
        """Obtener balances de Coinbase (simulado)"""
        return []
    
    async def get_trading_fees(self, symbol: str) -> Tuple[float, float]:
        """Obtener comisiones de Coinbase"""
        return (0.005, 0.005)  # (maker, taker)

class ExchangeManager:
    """Gestor de múltiples exchanges"""
    
    def __init__(self):
        self.exchanges: Dict[ExchangeType, BaseExchange] = {}
        self.active_exchanges: List[ExchangeType] = []
        
    def add_exchange(self, exchange_type: ExchangeType, credentials: ExchangeCredentials):
        """Agregar un exchange"""
        try:
            if exchange_type == ExchangeType.BINANCE:
                exchange = BinanceExchange(credentials)
            elif exchange_type == ExchangeType.COINBASE:
                exchange = CoinbaseExchange(credentials)
            else:
                logger.warning(f"Exchange {exchange_type.value} no implementado completamente")
                return False
            
            self.exchanges[exchange_type] = exchange
            self.active_exchanges.append(exchange_type)
            logger.info(f"✅ Exchange {exchange_type.value} agregado")
            return True
            
        except Exception as e:
            logger.error(f"Error agregando exchange {exchange_type.value}: {e}")
            return False
    
    async def get_aggregated_market_data(self, symbol: str, interval: str = "1d") -> Dict[str, List[MarketData]]:
        """Obtener datos de mercado de todos los exchanges"""
        results = {}
        
        for exchange_type in self.active_exchanges:
            exchange = self.exchanges[exchange_type]
            
            try:
                async with exchange:
                    data = await exchange.get_market_data(symbol, interval)
                    if data:
                        results[exchange.name] = data
                        logger.info(f"✅ Datos obtenidos de {exchange.name}: {len(data)} períodos")
                    else:
                        logger.warning(f"⚠️ No se obtuvieron datos de {exchange.name}")
                        
            except Exception as e:
                logger.error(f"❌ Error obteniendo datos de {exchange.name}: {e}")
        
        return results
    
    async def place_order_on_exchange(self, exchange_type: ExchangeType, order_request: OrderRequest) -> Optional[Order]:
        """Colocar orden en un exchange específico"""
        if exchange_type not in self.exchanges:
            logger.error(f"Exchange {exchange_type.value} no configurado")
            return None
        
        exchange = self.exchanges[exchange_type]
        
        try:
            async with exchange:
                order = await exchange.place_order(order_request)
                logger.info(f"✅ Orden colocada en {exchange.name}: {order.id}")
                return order
                
        except Exception as e:
            logger.error(f"❌ Error colocando orden en {exchange.name}: {e}")
            return None
    
    async def get_all_balances(self) -> Dict[str, List[Balance]]:
        """Obtener balances de todos los exchanges"""
        results = {}
        
        for exchange_type in self.active_exchanges:
            exchange = self.exchanges[exchange_type]
            
            try:
                async with exchange:
                    balances = await exchange.get_balances()
                    if balances:
                        results[exchange.name] = balances
                        logger.info(f"✅ Balances obtenidos de {exchange.name}: {len(balances)} activos")
                        
            except Exception as e:
                logger.error(f"❌ Error obteniendo balances de {exchange.name}: {e}")
        
        return results
    
    def get_best_price(self, market_data: Dict[str, List[MarketData]], side: OrderSide) -> Tuple[str, float]:
        """Encontrar el mejor precio entre exchanges"""
        best_exchange = ""
        best_price = 0.0
        
        for exchange_name, data_list in market_data.items():
            if data_list:
                current_price = data_list[-1].close
                
                if side == OrderSide.BUY:
                    # Para comprar, queremos el precio más bajo
                    if best_price == 0.0 or current_price < best_price:
                        best_price = current_price
                        best_exchange = exchange_name
                else:
                    # Para vender, queremos el precio más alto
                    if current_price > best_price:
                        best_price = current_price
                        best_exchange = exchange_name
        
        return best_exchange, best_price

async def test_exchange_integration():
    """Función de prueba del sistema de integración"""
    
    print("🚀 Iniciando prueba del Sistema de Integración con Exchanges...")
    
    # Crear manager
    manager = ExchangeManager()
    
    # Configurar credenciales de prueba (sandbox)
    binance_creds = ExchangeCredentials(
        api_key="test_api_key",
        api_secret="test_api_secret",
        sandbox=True
    )
    
    coinbase_creds = ExchangeCredentials(
        api_key="test_api_key",
        api_secret="test_api_secret",
        passphrase="test_passphrase",
        sandbox=True
    )
    
    # Agregar exchanges
    print("📊 Configurando exchanges...")
    manager.add_exchange(ExchangeType.BINANCE, binance_creds)
    manager.add_exchange(ExchangeType.COINBASE, coinbase_creds)
    
    # Probar obtención de datos de mercado
    print("\n📈 Probando obtención de datos de mercado...")
    market_data = await manager.get_aggregated_market_data("BTCUSDT", "1h")
    
    for exchange_name, data_list in market_data.items():
        if data_list:
            latest = data_list[-1]
            print(f"📊 {exchange_name}: ${latest.close:,.2f} (Vol: {latest.volume:,.0f})")
    
    # Encontrar mejor precio
    if market_data:
        best_exchange, best_price = manager.get_best_price(market_data, OrderSide.BUY)
        print(f"\n💰 Mejor precio para comprar: ${best_price:,.2f} en {best_exchange}")
    
    # Simular colocación de orden
    print("\n📋 Simulando colocación de orden...")
    order_request = OrderRequest(
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.001
    )
    
    try:
        order = await manager.place_order_on_exchange(ExchangeType.BINANCE, order_request)
        if order:
            print(f"✅ Orden simulada: {order.id} - {order.quantity} {order.symbol}")
    except Exception as e:
        print(f"⚠️ Error en orden simulada: {e}")
    
    # Probar balances
    print("\n💰 Probando obtención de balances...")
    all_balances = await manager.get_all_balances()
    
    for exchange_name, balances in all_balances.items():
        print(f"💼 {exchange_name}: {len(balances)} activos con balance")
        for balance in balances[:3]:  # Mostrar solo los primeros 3
            print(f"   {balance.asset}: {balance.total:.6f}")
    
    print("\n✅ Prueba del Sistema de Integración completada!")

if __name__ == "__main__":
    asyncio.run(test_exchange_integration())