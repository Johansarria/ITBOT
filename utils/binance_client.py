# utils/binance_client.py
import logging
from binance import AsyncClient
from binance.exceptions import BinanceAPIException, BinanceRequestException
import config
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
                api_key = config.BINANCE_API_KEY
                secret_key = config.BINANCE_SECRET_KEY

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
