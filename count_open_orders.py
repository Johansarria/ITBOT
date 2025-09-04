import os
import asyncio
import logging
import contextlib
from binance.client import AsyncClient
from dotenv import load_dotenv


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "t"}


async def main() -> None:
    # Silenciar logs para que la salida sea solo el número
    logging.getLogger().setLevel(logging.CRITICAL)

    # Cargar variables desde .env sin efectos colaterales del proyecto
    load_dotenv(override=False)

    api_key = os.getenv("BINANCE_API_KEY", "")
    secret_key = os.getenv("BINANCE_SECRET_KEY", "")
    use_testnet = _env_bool("BINANCE_USE_TESTNET_FUTURES", False)

    # Fallback a config solo si faltan credenciales en entorno
    if not api_key or not secret_key:
        with contextlib.suppress(Exception):
            from config import settings  # carga .env internamente
            api_key = api_key or getattr(settings, 'BINANCE_API_KEY', '')
            secret_key = secret_key or getattr(settings, 'BINANCE_SECRET_KEY', '')
            use_testnet = bool(getattr(settings, 'BINANCE_USE_TESTNET_FUTURES', use_testnet))

    client = await AsyncClient.create(
        api_key=api_key,
        api_secret=secret_key,
        testnet=use_testnet,
    )
    try:
        orders = await client.futures_get_open_orders()
        # Imprimir SOLO el total (sin mensajes adicionales)
        print(len(orders))
    finally:
        with contextlib.suppress(Exception):
            await client.close_connection()


if __name__ == "__main__":
    asyncio.run(main())
