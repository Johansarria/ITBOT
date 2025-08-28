# utils/binance_client.py
import logging
from binance import AsyncClient
from binance.exceptions import BinanceAPIException, BinanceRequestException
from config import settings  # Import the pydantic settings object
import asyncio

logger = logging.getLogger(__name__)

_binance_client_instance = None
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
                    client_instance = await AsyncClient.create(api_key=api_key, api_secret=secret_key)
                    
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

async def close_binance_client():
    """
    Cierra la sesión del cliente de Binance si existe.
    Debe llamarse durante el apagado de la aplicación.
    """
    global _binance_client_instance
    if _binance_client_instance:
        logger.info("Cerrando cliente de Binance asíncrono...")
        await _binance_client_instance.close()
        _binance_client_instance = None
        logger.info("Cliente de Binance cerrado exitosamente.")

async def get_total_balance() -> float:
    """
    Obtiene el balance total del usuario en USDT, incluyendo el valor de las criptomonedas en posesión.
    Returns:
        float: Balance total en USDT.
    """
    client = await get_binance_client()
    total_balance_usdt = 0.0

    try:
        account_info = await asyncio.to_thread(client.get_account)
        balances = account_info["balances"]

        # Obtener todos los precios de los tickers para la conversión
        prices = await asyncio.to_thread(client.get_all_tickers)
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
