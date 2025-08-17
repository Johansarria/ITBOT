# utils/technical_analysis.py

import os
import pandas as pd
from typing import Any, cast
from datetime import datetime
import logging

logger = logging.getLogger(__name__) # Obtener logger para este módulo

from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, CCIIndicator, ADXIndicator
from ta.volatility import AverageTrueRange, BollingerBands
from utils.exporter import export_analysis_result, export_features
import joblib # Importar joblib para cargar el modelo
from utils.binance_client import get_binance_client # Importar la función para obtener el cliente de Binance
# Importar feature engineering avanzado
from utils.feature_engineering import enrich_features
from database.database_manager import get_klines # Importar get_klines de la BD

import asyncio
import time
from functools import wraps
from binance.exceptions import BinanceAPIException, BinanceRequestException # Importar excepciones específicas

# Ruta al modelo de ML entrenado
MODEL_PATH = "data/ml_models/lightgbm_model.pkl"
ml_model = None

def load_ml_model() -> None:
    """
    Carga el modelo de Machine Learning desde el disco si no está cargado.
    Asigna el modelo global ml_model.
    """
    global ml_model
    if ml_model is None:
        try:
            ml_model = joblib.load(MODEL_PATH)
            logger.info(f"Modelo de ML cargado exitosamente desde {MODEL_PATH}")
        except FileNotFoundError:
            logger.error(f"Modelo de ML no encontrado en {MODEL_PATH}. Asegúrate de haberlo entrenado y guardado.")
            ml_model = None
        except Exception as e:
            logger.exception(f"Error al cargar el modelo de ML: {e}")
            ml_model = None


# El modelo ya no se carga al inicio del módulo.
# load_ml_model()


# Decorador de reintentos con retroceso exponencial
from typing import Callable, Type, Tuple, Any

def retry(exceptions: Tuple[Type[BaseException], ...], tries: int = 4, delay: int = 3, backoff: int = 2, logger: Any = None) -> Callable:
    """
    Decorador de reintentos con retroceso exponencial.
    Args:
        exceptions (tuple): Excepciones a capturar.
        tries (int): Número de intentos.
        delay (int): Tiempo inicial de espera.
        backoff (int): Factor de multiplicación del delay.
        logger (Any): Logger opcional.
    Returns:
        Callable: Decorador para funciones asíncronas.
    """
    """
    Decorador de reintentos con retroceso exponencial.
    """
    def deco_retry(f):
        @wraps(f)
        async def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return await f(*args, **kwargs)
                except exceptions as e:
                    msg = f"{e}, Reintentando en {mdelay} segundos..."
                    if logger:
                        logger.warning(msg)
                    await asyncio.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return await f(*args, **kwargs) # Último intento sin captura
        return f_retry
    return deco_retry

logger = logging.getLogger(__name__) # Obtener logger para este módulo

# @retry((BinanceAPIException, BinanceRequestException), tries=3, delay=2, logger=logger) # Ya no es necesario el retry aquí
async def get_historical_klines(symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
    """
    Obtiene datos históricos de klines para un símbolo y periodo dado desde la base de datos.
    Args:
        symbol (str): Símbolo de trading (ej: 'BTCUSDT').
        interval (str): Intervalo de tiempo (ej: '1h').
        limit (int): Número máximo de registros a obtener.
    Returns:
        pd.DataFrame: DataFrame con los datos históricos.
    """
    logger.info(f"Obteniendo klines históricos para {symbol} - {interval} (limit: {limit}) desde la BD.")
    df = get_klines(symbol=symbol, interval=interval) # Usar la función de la BD

    if df.empty:
        logger.warning(f"No se encontraron klines en la BD para {symbol}-{interval}.")
        return pd.DataFrame()

    # Aplicar límite si es necesario (get_klines trae todo el historial)
    if limit and len(df) > limit:
        df = df.tail(limit)

    logger.info(f"Klines históricos obtenidos exitosamente para {symbol} desde la BD. Filas: {len(df)}.")
    return df

def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula todos los indicadores técnicos necesarios y los añade al DataFrame.
    """
    if df.empty:
        return df

    # Ensure 'high', 'low', and 'close' columns are numeric
    df["high"] = pd.to_numeric(df["high"], errors="coerce")
    df["low"] = pd.to_numeric(df["low"], errors="coerce")
    
    # Convert 'close' column to numeric and check for NaNs
    initial_nan_count = df["close"].isnull().sum()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    final_nan_count = df["close"].isnull().sum()

    if final_nan_count > initial_nan_count:
        newly_coerced_nans = final_nan_count - initial_nan_count
        nan_indices = df[df["close"].isnull()].index
        
        # Group consecutive NaNs to report date ranges
        if not nan_indices.empty:
            # Convert index to datetime if it's not already
            if not isinstance(nan_indices, pd.DatetimeIndex):
                nan_indices = pd.to_datetime(nan_indices)

            # Find consecutive groups of NaNs
            s = pd.Series(nan_indices)
            breaks = s.diff().dt.total_seconds() > 1 # Assuming 1 second is enough to break a sequence
            groups = s.groupby(breaks.cumsum())

            date_ranges = []
            for _, group in groups:
                if not group.empty:
                    start_date = group.min().strftime("%Y-%m-%d %H:%M:%S")
                    end_date = group.max().strftime("%Y-%m-%d %H:%M:%S")
                    date_ranges.append(f"[{start_date} to {end_date}]")
            
            logger.warning(f"Se convirtieron {newly_coerced_nans} valores a NaN en la columna 'close'. Rangos de fechas afectados: {'; '.join(date_ranges)}")

    logger.debug("Calculando indicadores técnicos.")
    # Indicadores técnicos
    df["rsi"] = RSIIndicator(close=df["close"]).rsi().fillna(0)
    macd = MACD(close=df["close"])
    df["macd"] = macd.macd().fillna(0)
    df["macd_signal"] = macd.macd_signal().fillna(0)
    stoch = StochasticOscillator(high=df["high"], low=df["low"], close=df["close"])
    df["stoch_k"] = stoch.stoch().fillna(0)
    df["stoch_d"] = stoch.stoch_signal().fillna(0)
    df["cci"] = CCIIndicator(high=df["high"], low=df["low"], close=df["close"]).cci().fillna(0)
    adx = ADXIndicator(high=df["high"], low=df["low"], close=df["close"])
    df["adx"] = adx.adx().fillna(0)
    df["plus_di"] = adx.adx_pos().fillna(0)
    df["minus_di"] = adx.adx_neg().fillna(0)
    df["atr"] = AverageTrueRange(high=df["high"], low=df["low"], close=df["close"]).average_true_range().fillna(0)
    bb = BollingerBands(close=df["close"])
    df["bb_upper"] = bb.bollinger_hband().fillna(0)
    df["bb_lower"] = bb.bollinger_lband().fillna(0)

    # Rellenar NaN con 0 después de calcular todos los indicadores
    df = df.fillna(0)

    logger.debug("Cálculo de indicadores completado.")
    return df

from typing import Optional

async def analyze_market(symbol: str = "BTCUSDT", interval: str = "1h", limit: int = 100, export: bool = True, df_klines: Optional[pd.DataFrame] = None, current_index: Optional[int] = None, umbral_alto: float = 0.85, umbral_medio: float = 0.70, umbral_bajo: float = 0.55) -> dict:
    logger.info(f"Iniciando análisis de mercado para {symbol} - {interval}.")
    

    if df_klines is not None:
        # Use the provided df_klines, slicing it if current_index is given
        if current_index is not None:
            df = df_klines.iloc[:current_index].copy() # Copy only the relevant slice
            logger.debug(f"Usando slice de DataFrame de klines proporcionado para el análisis hasta índice {current_index}.")
        else:
            df = df_klines.copy() # If no index, assume full df is passed for a single analysis
            logger.debug("Usando DataFrame de klines proporcionado para el análisis (sin slice).")
    else:
        df = await get_historical_klines(symbol, interval, limit)
        logger.info("Obteniendo klines históricos de Binance para el análisis.")

    if df.empty:
        logger.warning(f"No se pudieron obtener datos para el análisis de {symbol}.")
        return {"symbol": symbol, "interval": interval, "decision": "No hay datos para analizar", "score": 0}

    # Enriquecer el DataFrame con features avanzados
    df = enrich_features(df)
    # También calcular los indicadores clásicos para compatibilidad
    df = calculate_all_indicators(df)

    latest = df.iloc[-1]

    # Interpretaciones técnicas (siempre calculadas para el reporte)
    rsi_state = "sobreventa" if latest["rsi"] < 30 else "sobrecompra" if latest["rsi"] > 70 else "neutral"
    macd_state = "alcista" if latest["macd"] > latest["macd_signal"] else "bajista"
    stoch_state = "alcista" if latest["stoch_k"] > latest["stoch_d"] else "bajista"
    cci_state = "sobreventa" if latest["cci"] < -100 else "sobrecompra" if latest["cci"] > 100 else "neutral"
    adx_strength = "fuerte" if latest["adx"] > 25 else "débil"
    bb_position = "cerca del techo" if latest["close"] >= latest["bb_upper"] else "cerca del piso" if latest["close"] <= latest["bb_lower"] else "en rango"

    # Seleccionar las características para la predicción del modelo de ML
    feature_columns = [
        'rsi', 'macd', 'macd_signal', 'stoch_k', 'stoch_d', 'cci',
        'adx', 'plus_di', 'minus_di', 'atr', 'bb_upper', 'bb_lower'
    ]
    
    # Asegurarse de que todas las columnas de características existen y son numéricas
    # Esto es crucial para la inferencia del modelo
    for col in feature_columns:
        if col not in df.columns:
            logger.warning(f"Columna de característica '{col}' no encontrada en el DataFrame. Se omitirá.")
            feature_columns.remove(col)
        else:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0) # Asegurar numérico y rellenar NaN

    # Preparar los datos para la predicción del modelo de ML
    X_latest = df[feature_columns].iloc[-1:].copy() # Tomar la última fila para la predicción

    decision = "MANTENER"
    score = 0

    # Cargar el modelo si es necesario (lazy loading)
    if ml_model is None:
        load_ml_model()

    # Usar los umbrales pasados como argumento
    if ml_model is not None:
        try:
            # Obtener las probabilidades de predicción
            probabilities = ml_model.predict_proba(X_latest)[0]
            # Las clases son 0.0 (VENDER) y 1.0 (COMPRAR)
            prob_sell = probabilities[0] # Probabilidad de VENDER
            prob_buy = probabilities[1]  # Probabilidad de COMPRAR

            if prob_buy >= umbral_alto:
                decision = "COMPRAR"
                score = prob_buy * 100
            elif prob_buy >= umbral_medio:
                decision = "COMPRAR_BAJO"
                score = prob_buy * 100
            elif prob_sell >= umbral_alto:
                decision = "VENDER"
                score = prob_sell * 100
            elif prob_sell >= umbral_medio:
                decision = "VENDER_ALTO"
                score = prob_sell * 100
            else:
                decision = "MANTENER"
                score = max(prob_buy, prob_sell) * 100

            logger.info(f"Predicción del modelo de ML: COMPRAR={prob_buy:.2f}, VENDER={prob_sell:.2f} -> Decisión: {decision}, Score: {score}")
        except Exception as e:
            logger.exception(f"Error al realizar la predicción con el modelo de ML: {e}")
            decision = "ERROR_ML"
            score = 0
    else:
        logger.warning("Modelo de ML no cargado. No se puede realizar la predicción.")
        decision = "ERROR_ML_NO_CARGADO"
        score = 0
    
    logger.info(f"Análisis completado para {symbol}. Decisión: {decision}, Score: {score}")

    result = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": symbol,
        "interval": interval,
        "rsi": round(latest["rsi"], 2),
        "macd": round(latest["macd"], 4),
        "macd_signal": round(latest["macd_signal"], 4),
        "stoch_k": round(latest["stoch_k"], 2),
        "stoch_d": round(latest["stoch_d"], 2),
        "cci": round(latest["cci"], 2),
        "adx": round(latest["adx"], 2),
        "atr": round(latest["atr"], 4),
        "bb_upper": round(latest["bb_upper"], 4),
        "bb_lower": round(latest["bb_lower"], 4),
        "rsi_state": rsi_state,
        "macd_state": macd_state,
        "stoch_state": stoch_state,
        "cci_state": cci_state,
        "adx_strength": adx_strength,
        "bb_position": bb_position,
        "decision": decision,
        "close": latest["close"],
        "score": score
    }

    if export:
        export_analysis_result(symbol, interval, result)
        logger.info(f"Análisis exportado a CSV para {symbol}.")

    # Exportar features enriquecidos para análisis histórico y entrenamiento
    export_features(symbol, interval, df)
    logger.info(f"Features enriquecidos exportados a CSV para {symbol}.")

    return result

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    async def main_analysis():
        data = await analyze_market()
        for k, v in data.items():
            print(f"{k}: {v}")
    asyncio.run(main_analysis())