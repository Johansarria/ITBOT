import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock
from utils.order_executor import evaluar_y_ejecutar_operacion
from utils.logger_setup import setup_logging

# Configurar logging para el script de prueba
setup_logging()
logger = logging.getLogger(__name__)

async def run_test_case(test_name: str, decision: str, symbol: str, score: float):
    logger.info(f"--- Ejecutando caso de prueba: {test_name} ---")

    # Mockear bot_instance y chat_id
    mock_bot = AsyncMock()
    mock_chat_id = 123456789

    # Simular resultado_analisis
    simulated_analysis_result = {
        "symbol": symbol,
        "decision": decision,
        "score": score,
        "interval": "1h" # Añadir intervalo para completar el resultado
    }

    # Ejecutar la función
    result_message = await evaluar_y_ejecutar_operacion(mock_bot, mock_chat_id, simulated_analysis_result, take_profit=None, stop_loss=None)
    logger.info(f"Resultado de la ejecución: {result_message}")
    logger.info(f"--- Fin del caso de prueba: {test_name} ---\n")

async def main():
    # Caso de prueba 1: Decisión de COMPRAR
    await run_test_case("COMPRAR", "COMPRAR", "BTCUSDT", 0.85)

    # Caso de prueba 2: Decisión de VENDER
    await run_test_case("VENDER", "VENDER", "ETHUSDT", -0.70)

    # Caso de prueba 3: Decisión de MANTENER
    await run_test_case("MANTENER", "MANTENER", "BNBUSDT", 0.10)

if __name__ == "__main__":
    asyncio.run(main())