"""
Feature Store centralizado para generación, versionado y carga de features ML.
"""
import pandas as pd
import os
from typing import Optional

FEATURES_DIR = os.path.join(os.path.dirname(__file__), '../data/features')
os.makedirs(FEATURES_DIR, exist_ok=True)

def save_features(df: pd.DataFrame, name: str, version: Optional[str] = None):
    """Guarda un DataFrame de features versionado."""
    fname = f"{name}{'_' + version if version else ''}.parquet"
    path = os.path.join(FEATURES_DIR, fname)
    df.to_parquet(path)
    return path

def load_features(name: str, version: Optional[str] = None) -> pd.DataFrame:
    """Carga un DataFrame de features versionado."""
    fname = f"{name}{'_' + version if version else ''}.parquet"
    path = os.path.join(FEATURES_DIR, fname)
    return pd.read_parquet(path)
