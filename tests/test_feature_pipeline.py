import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from utils.feature_pipeline import FeaturePipeline
from utils.feature_engineering import enrich_features
from utils.technical_analysis import calculate_all_indicators

# Mock de las funciones subyacentes para aislar FeaturePipeline
@pytest.fixture
def mock_feature_dependencies():
    with patch('utils.feature_pipeline.enrich_features', MagicMock(side_effect=lambda df: df.assign(new_feature=1))) as mock_enrich_features:
        with patch('utils.feature_pipeline.calculate_all_indicators', MagicMock(side_effect=lambda df: df.assign(rsi=50))) as mock_calculate_all_indicators:
            yield mock_enrich_features, mock_calculate_all_indicators # Yield the mock objects

@pytest.fixture
def sample_klines_df():
    data = {
        'open': [100, 102, 105, 103, 106, 108, 110, 109, 112, 115, 110, 108, 105, 103, 100, 98, 95, 93, 90, 88, 90, 92, 95, 98, 100, 102, 105, 108, 110, 112],
        'high': [103, 106, 107, 105, 108, 110, 112, 111, 114, 117, 112, 110, 107, 105, 102, 100, 97, 95, 92, 90, 92, 94, 97, 100, 102, 104, 107, 110, 112, 114],
        'low': [99, 101, 103, 102, 104, 106, 108, 107, 110, 113, 108, 106, 103, 101, 98, 96, 93, 91, 88, 86, 88, 90, 93, 96, 98, 100, 103, 106, 108, 110],
        'close': [102, 105, 103, 106, 108, 110, 109, 112, 115, 114, 110, 107, 104, 102, 99, 97, 94, 92, 89, 87, 89, 91, 94, 97, 99, 101, 104, 107, 109, 111],
        'volume': [1000, 1200, 1100, 1300, 1050, 1150, 1250, 1000, 1350, 1200, 1100, 1000, 900, 800, 700, 600, 500, 400, 300, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200],
        'open_time': pd.to_datetime(pd.date_range(start='2023-01-01', periods=30, freq='H'))
    }
    df = pd.DataFrame(data)
    df.set_index('open_time', inplace=True)
    return df

def test_feature_pipeline_initialization():
    pipeline = FeaturePipeline()
    assert isinstance(pipeline, FeaturePipeline)

def test_feature_pipeline_empty_dataframe():
    pipeline = FeaturePipeline()
    empty_df = pd.DataFrame()
    result_df = pipeline.transform(empty_df)
    assert result_df.empty

def test_feature_pipeline_transform(sample_klines_df, mock_feature_dependencies):
    mock_enrich_features, mock_calculate_all_indicators = mock_feature_dependencies # Unpack the mock objects
    pipeline = FeaturePipeline()
    result_df = pipeline.transform(sample_klines_df)

    # Verificar que las funciones subyacentes fueron llamadas
    called_df_enrich = mock_enrich_features.call_args[0][0]
    pd.testing.assert_frame_equal(called_df_enrich, sample_klines_df.copy())

    # Get the DataFrame passed to calculate_all_indicators
    called_df_calc = mock_calculate_all_indicators.call_args[0][0]
    # We expect this to be the return value of enrich_features, which is a DataFrame with 'new_feature'
    expected_df_calc = sample_klines_df.copy().assign(new_feature=1) # Recreate the expected DataFrame
    pd.testing.assert_frame_equal(called_df_calc, expected_df_calc)

    # Verificar que las nuevas features se añadieron al DataFrame
    assert 'new_feature' in result_df.columns
    assert 'rsi' in result_df.columns
    assert result_df['new_feature'].iloc[0] == 1
    assert result_df['rsi'].iloc[0] == 50
    assert len(result_df) == len(sample_klines_df)