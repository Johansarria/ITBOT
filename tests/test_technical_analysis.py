# tests/test_technical_analysis.py

import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

# Importar la función a probar
from utils.technical_analysis import analyze_market, load_ml_model

# Fixture para mockear get_historical_klines
@pytest.fixture
def mock_get_historical_klines():
    with patch('utils.technical_analysis.get_historical_klines', new_callable=AsyncMock) as mock_klines:
        yield mock_klines

# Fixture para mockear export_analysis_result
@pytest.fixture
def mock_export_analysis_result():
    with patch('utils.technical_analysis.export_analysis_result') as mock_export:
        yield mock_export

# Fixture para mockear el modelo de ML
@pytest.fixture
def mock_ml_model():
    with patch('utils.technical_analysis.ml_model', new_callable=MagicMock) as mock_model:
        yield mock_model

# Datos de klines de ejemplo
def get_sample_klines(num_rows: int = 100) -> pd.DataFrame:
    timestamps = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(num_rows)]
    prices = [100 + i * 0.1 for i in range(num_rows)]
    data = {
        "timestamp": pd.to_datetime(timestamps),
        "open": [p - 0.5 for p in prices],
        "high": [p + 1 for p in prices],
        "low": [p - 1 for p in prices],
        "close": prices,
        "volume": [100] * num_rows
    }
    df = pd.DataFrame(data).set_index("timestamp")
    df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].apply(pd.to_numeric)
    return df

# --- Tests para analyze_market ---

@pytest.mark.asyncio
async def test_analyze_market_empty_data(mock_get_historical_klines, mock_export_analysis_result):
    mock_get_historical_klines.return_value = pd.DataFrame()
    result = await analyze_market("TESTUSDT", "1h", 50)
    assert result["decision"] == "No hay datos para analizar"
    assert result["score"] == 0
    mock_export_analysis_result.assert_not_called()

@pytest.mark.asyncio
async def test_analyze_market_no_model_loaded(mock_get_historical_klines, mock_export_analysis_result):
    # Asegurarse de que el modelo no esté cargado
    with patch('utils.technical_analysis.load_ml_model', return_value=None): # Patch load_ml_model to do nothing
        with patch('utils.technical_analysis.ml_model', None): # Ensure ml_model is None
            mock_get_historical_klines.return_value = get_sample_klines()
            result = await analyze_market("TESTUSDT", "1h", 50)
            assert result["decision"] == "ERROR_ML_NO_CARGADO"
            assert result["score"] == 0
            mock_export_analysis_result.assert_called_once()

@pytest.mark.asyncio
async def test_analyze_market_buy_prediction(mock_get_historical_klines, mock_export_analysis_result, mock_ml_model):
    mock_get_historical_klines.return_value = get_sample_klines()
    # Simular predicción de COMPRA (probabilidad de clase 1 > threshold)
    mock_ml_model.predict_proba.return_value = [[0.1, 0.9]] # [prob_sell, prob_buy]
    
    result = await analyze_market("TESTUSDT", "1h", 50, umbral_alto=0.8, umbral_medio=0.7, umbral_bajo=0.5)
    
    assert result["decision"] == "COMPRAR"
    assert result["score"] == 90.0
    mock_export_analysis_result.assert_called_once()

@pytest.mark.asyncio
async def test_analyze_market_sell_prediction(mock_get_historical_klines, mock_export_analysis_result, mock_ml_model):
    mock_get_historical_klines.return_value = get_sample_klines()
    # Simular predicción de VENTA (probabilidad de clase 0 > threshold)
    mock_ml_model.predict_proba.return_value = [[0.85, 0.15]] # [prob_sell, prob_buy]
    
    result = await analyze_market("TESTUSDT", "1h", 50, umbral_alto=0.8, umbral_medio=0.7, umbral_bajo=0.5)
    
    assert result["decision"] == "VENDER"
    assert result["score"] == 85.0
    mock_export_analysis_result.assert_called_once()

@pytest.mark.asyncio
async def test_analyze_market_hold_prediction(mock_get_historical_klines, mock_export_analysis_result, mock_ml_model):
    mock_get_historical_klines.return_value = get_sample_klines()
    # Simular predicción de MANTENER (ninguna probabilidad supera el threshold)
    mock_ml_model.predict_proba.return_value = [[0.6, 0.4]] # [prob_sell, prob_buy]
    
    result = await analyze_market("TESTUSDT", "1h", 50, umbral_alto=0.7, umbral_medio=0.65, umbral_bajo=0.65)
    
    assert result["decision"] == "MANTENER"
    assert result["score"] == 60.0
    mock_export_analysis_result.assert_called_once()

@pytest.mark.asyncio
async def test_analyze_market_prediction_error(mock_get_historical_klines, mock_export_analysis_result, mock_ml_model):
    mock_get_historical_klines.return_value = get_sample_klines()
    # Simular un error durante la predicción
    mock_ml_model.predict_proba.side_effect = Exception("Prediction failed")
    
    result = await analyze_market("TESTUSDT", "1h", 50)
    
    assert result["decision"] == "ERROR_ML"
    assert result["score"] == 0
    mock_export_analysis_result.assert_called_once()