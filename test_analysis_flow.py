import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import pandas as pd
import logging
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Configure logging for this test script
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock the external dependencies
# Mock the Bot instance
mock_bot = AsyncMock()
mock_chat_id = 123456789

# Mock get_historical_klines to return a sample DataFrame
sample_klines_data = {
    "timestamp": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05"]),
    "open": [100, 101, 102, 103, 104],
    "high": [105, 106, 107, 108, 109],
    "low": [99, 100, 101, 102, 103],
    "close": [101, 102, 103, 104, 105],
    "volume": [1000, 1100, 1200, 1300, 1400],
    "close_time": [0,0,0,0,0], "quote_asset_volume": [0,0,0,0,0], "number_of_trades": [0,0,0,0,0],
    "taker_buy_base_volume": [0,0,0,0,0], "taker_buy_quote_volume": [0,0,0,0,0], "ignore": [0,0,0,0,0]
}
mock_historical_klines_df = pd.DataFrame(sample_klines_data).set_index("timestamp")

async def run_test():
    logger.info("Running test for procesar_comando_analisis in flujo_principal context.")
    
    # Patch the external functions that procesar_comando_analisis depends on
    with patch('modules.analisis_bot.get_historical_klines', new_callable=AsyncMock) as mock_get_historical_klines,         patch('modules.analisis_bot.StrategyManager') as MockStrategyManager:
        
        mock_get_historical_klines.return_value = mock_historical_klines_df
        
        # Mock the active strategy to return a predictable analysis result
        mock_active_strategy = MagicMock()
        mock_active_strategy.name = "MockStrategy"
        mock_active_strategy.analyze = AsyncMock(return_value={
            "symbol": "BTCUSDT",
            "decision": "COMPRAR",
            "score": 0.85,
            "rsi": 60.0,
            "macd": 1.5,
            "macd_signal": 1.0,
            "stoch_k": 70.0,
            "stoch_d": 65.0,
            "cci": 50.0,
            "adx": 30.0
        })
        
        mock_strategy_manager_instance = MockStrategyManager.return_value
        mock_strategy_manager_instance.get_active_strategy.return_value = mock_active_strategy

        # Import procesar_comando_analisis after patching to ensure it uses the mocks
        from modules.analisis_bot import procesar_comando_analisis
        from strategies.strategy_manager import StrategyManager

        analysis_result = await procesar_comando_analisis(
            mock_bot, 
            mock_chat_id, 
            "recomendar accion", 
            send_telegram_message=False
        )
        
        logger.info(f"Analysis Result: {analysis_result}")
        
        # Assertions to check if the result is as expected
        assert analysis_result.get("decision") == "COMPRAR"
        assert analysis_result.get("score") == 0.85
        assert analysis_result.get("symbol") == "BTCUSDT"
        logger.info("Assertions passed: Analysis result is as expected.")

if __name__ == "__main__":
    asyncio.run(run_test())