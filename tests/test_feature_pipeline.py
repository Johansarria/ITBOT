import pytest
import pandas as pd
from utils.feature_pipeline import FeaturePipeline

@pytest.fixture
def sample_klines_df():
    data = {
        'open': [100, 102, 105, 103, 106, 108, 110, 109, 112, 115, 110, 108, 105, 103, 100, 98, 95, 93, 90, 88, 90, 92, 95, 98, 100, 102, 105, 108, 110, 112],
        'high': [103, 106, 107, 105, 108, 110, 112, 111, 114, 117, 112, 110, 107, 105, 102, 100, 97, 95, 92, 90, 92, 94, 97, 100, 102, 104, 107, 110, 112, 114],
        'low': [99, 101, 103, 102, 104, 106, 108, 107, 110, 113, 108, 106, 103, 101, 98, 96, 93, 91, 88, 86, 88, 90, 93, 96, 98, 100, 103, 106, 108, 110],
        'close': [102, 105, 103, 106, 108, 110, 109, 112, 115, 114, 110, 107, 104, 102, 99, 97, 94, 92, 89, 87, 89, 91, 94, 97, 99, 101, 104, 107, 109, 111],
        'volume': [1000, 1200, 1100, 1300, 1050, 1150, 1250, 1000, 1350, 1200, 1100, 1000, 900, 800, 700, 600, 500, 400, 300, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200],
        'open_time': pd.to_datetime(pd.date_range(start='2023-01-01', periods=30, freq='h'))
    }
    df = pd.DataFrame(data)
    return df

def test_feature_pipeline_initialization():
    pipeline = FeaturePipeline()
    assert isinstance(pipeline, FeaturePipeline)

def test_feature_pipeline_empty_dataframe():
    pipeline = FeaturePipeline()
    empty_df = pd.DataFrame()
    result_df = pipeline.transform(empty_df)
    assert result_df.empty

def test_feature_pipeline_transform(sample_klines_df):
    pipeline = FeaturePipeline()
    result_df = pipeline.transform(sample_klines_df)

    # Check that the original columns are still there
    for col in sample_klines_df.columns:
        assert col in result_df.columns

    # Check that the new feature columns are there
    feature_names = pipeline.get_feature_names()
    for feature in feature_names:
        assert feature in result_df.columns

    # Check that the number of rows is the same
    assert len(result_df) == len(sample_klines_df)

    # Check that there are no NaNs
    assert not result_df.isnull().values.any()

def test_get_feature_names():
    pipeline = FeaturePipeline()
    feature_names = pipeline.get_feature_names()
    assert isinstance(feature_names, list)
    assert 'rsi' in feature_names
    assert 'ma_20' in feature_names