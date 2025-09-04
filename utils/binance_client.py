# utils/binance_client.py
import logging
from binance.client import AsyncClient, Client
from typing import Any
from binance.exceptions import BinanceAPIException, BinanceRequestException
from config import settings  # Import the pydantic settings object
import asyncio

logger = logging.getLogger(__name__)

_binance_client_instance = None
_binance_sync_client_instance = None
_client_lock = asyncio.Lock()

async def get_binance_client() -> AsyncClient:
    """
    Devuelve una instancia singleton del cliente asíncrono de Binance.
    Inicializa el cliente solo si aún no ha sido inicializado, de forma thread-safe.
    """
    global _binance_client_instance
    if _binance_client_instance is None:
        async with _client_lock:
            if _binance_client_instance is None:
                logger.info("Inicializando cliente de Binance asíncrono centralizado...")
                api_key = settings.BINANCE_API_KEY
                secret_key = settings.BINANCE_SECRET_KEY

                try:
                    # Usamos create para instanciar el cliente asíncrono
                    use_testnet = bool(getattr(settings, 'BINANCE_USE_TESTNET_SPOT', False))
                    client_instance = await AsyncClient.create(api_key=api_key, api_secret=secret_key, testnet=use_testnet)
                    
                    # Probar la conexión
                    await client_instance.ping()
                    logger.info("Cliente de Binance asíncrono inicializado y conexión verificada exitosamente.")
                    _binance_client_instance = client_instance
                except (BinanceAPIException, BinanceRequestException) as e:
                    logger.error(f"Error de la API de Binance al conectar: {e}", exc_info=True)
                    # En caso de fallo, no asignamos la instancia para que pueda reintentarse
                    raise
                except Exception as e:
                    logger.exception(f"Error inesperado al conectar con la API de Binance: {e}")
                    raise
    return _binance_client_instance

def get_um_futures_client():
    """
    Devuelve una instancia del cliente sincrónico de Binance configurado para Futuros.
    """
    global _binance_sync_client_instance
    if _binance_sync_client_instance is None:
        logger.info("Inicializando cliente de Binance sincrónico para Futuros...")
        api_key = settings.BINANCE_API_KEY
        secret_key = settings.BINANCE_SECRET_KEY
        
        _binance_sync_client_instance = Client(api_key, secret_key, testnet=settings.BINANCE_USE_TESTNET_FUTURES)
    
    return _binance_sync_client_instance

async def close_binance_client():
    """
    Cierra la sesión del cliente de Binance si existe.
    Debe llamarse durante el apagado de la aplicación.
    """
    global _binance_client_instance
    if _binance_client_instance:
        logger.info("Cerrando cliente de Binance asíncrono...")
        try:
            # Preferir close() si está disponible para compatibilidad con tests
            client_any = _binance_client_instance  # type: ignore[assignment]
            if hasattr(client_any, 'close') and callable(getattr(client_any, 'close')):
                await getattr(client_any, 'close')()
            elif hasattr(_binance_client_instance, 'close_connection') and callable(_binance_client_instance.close_connection):
                await _binance_client_instance.close_connection()
            else:
                logger.warning("Instancia de cliente no tiene métodos de cierre conocidos.")
        except Exception as e:
            logger.warning(f"Error al cerrar conexión de Binance (puede ser normal): {e}")
        finally:
            _binance_client_instance = None
            logger.info("Cliente de Binance cerrado exitosamente.")

def close_um_futures_client():
    """UMFutures es cliente HTTP síncrono sin conexiones persistentes; no requiere cierre, pero limpiamos la instancia."""
    global _um_futures_client_instance
    _um_futures_client_instance = None

async def get_total_balance() -> float:
    """
    Obtiene el balance total del usuario en USDT, incluyendo el valor de las criptomonedas en posesión.
    Returns:
        float: Balance total en USDT.
    """
    client = await get_binance_client()
    total_balance_usdt = 0.0

    try:
        account_info = await client.get_account()
        balances = account_info["balances"]

        # Obtener todos los precios de los tickers para la conversión
        prices = await client.get_all_tickers()
        price_map = {p["symbol"]: float(p["price"]) for p in prices}

        for balance in balances:
            asset = balance["asset"]
            free = float(balance["free"])
            locked = float(balance["locked"])
            total_asset_amount = free + locked

            if total_asset_amount > 0:
                if asset == "USDT":
                    total_balance_usdt += total_asset_amount
                else:
                    # Intentar convertir a USDT
                    symbol_usdt = f"{asset}USDT"
                    if symbol_usdt in price_map:
                        total_balance_usdt += total_asset_amount * price_map[symbol_usdt]
                    else:
                        logger.warning(f"No se encontró precio para {symbol_usdt}. No se pudo incluir {asset} en el balance total.")

    except (BinanceAPIException, BinanceRequestException) as e:
        logger.error(f"Error de Binance al obtener balance total: {e}", exc_info=True)
        return 0.0
    except Exception as e:
        logger.exception(f"Error inesperado al obtener balance total: {e}")
        return 0.0

    return total_balance_usdt


async def get_bid_ask_spread(symbol: str) -> tuple[float | None, float | None, float | None, float | None]:
    """
    Obtiene el spread de compra/venta para un símbolo específico.

    Args:
        symbol (str): El símbolo del par de trading (ej. 'BTCUSDT').

    Returns:
        tuple[float | None, float | None, float | None, float | None]: Una tupla con el precio de bid,
        precio de ask, el spread absoluto y el spread porcentual.
        Retorna (None, None, None, None) en caso de error.
    """
    client = await get_binance_client()
    try:
        ticker = await client.get_orderbook_ticker(symbol=symbol)
        bid_price = float(ticker['bidPrice'])
        ask_price = float(ticker['askPrice'])
        
        if ask_price > 0:
            spread = ask_price - bid_price
            spread_percentage = (spread / ask_price) * 100
        else:
            spread = 0.0
            spread_percentage = 0.0
            
        return bid_price, ask_price, spread, spread_percentage
    except (BinanceAPIException, BinanceRequestException) as e:
        logger.error(f"Error de Binance al obtener el spread para {symbol}: {e}", exc_info=True)
        return None, None, None, None

def get_futures_exchange_info() -> dict | None:
    """Obtiene exchangeInfo de Futuros USDT-M. Devuelve dict o None si falla."""
    try:
        cli = get_um_futures_client()
        return cli.futures_exchange_info()
    except Exception as e:
        logger.error(f"Fallo exchange_info FUTURES: {e}")
        return None
