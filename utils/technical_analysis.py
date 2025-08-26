# utils/technical_analysis.py

import os
import pandas as pd
from typing import Any, cast
from datetime import datetime
import logging

# Imports para RegimeDetector (movido aquí)
import numpy as np
from ta.volatility import BollingerBands
from ta.trend import MACD, ADXIndicator
from ta.momentum import RSIIndicator

logger = logging.getLogger(__name__) # Obtener logger para este módulo

from utils.exporter import export_analysis_result, export_features
import joblib # Importar joblib para cargar el modelo
from utils.binance_client import get_binance_client # Importar la función para obtener el cliente de Binance
from database.database_manager import get_klines # Importar get_klines de la BD
from utils.feature_pipeline import FeaturePipeline

import asyncio
import time
from functools import wraps
from binance.exceptions import BinanceAPIException, BinanceRequestException # Importar excepciones específicas

import mlflow.pyfunc

# Ruta al modelo de ML entrenado en MLflow
# Esto debería ser gestionado de forma más dinámica, por ejemplo, usando el Model Registry.
# Por ahora, usamos el último run ID conocido.
LAST_RUN_ID = "5006527129a74ad4bb014b9ce8553f51" # Reemplazar con el último run_id si es necesario
MODEL_PATH = f"runs:/{LAST_RUN_ID}/model"
ml_model = None

def load_ml_model() -> None:
    """
    Carga el modelo de Machine Learning desde el MLflow Model Registry.
    Asigna el modelo global ml_model.
    """
    global ml_model
    if ml_model is None:
        try:
            # Se necesita inicializar el tracking URI para que MLflow sepa dónde buscar los runs
            tracking_uri = "file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mlruns"))
            mlflow.set_tracking_uri(tracking_uri)

            ml_model = mlflow.pyfunc.load_model(MODEL_PATH)
            logger.info(f"Modelo PyFunc de ML cargado exitosamente desde {MODEL_PATH}")
        except Exception as e:
            logger.exception(f"Error al cargar el modelo PyFunc de ML desde MLflow: {e}")
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

from typing import Optional

async def analyze_market(symbol: str = "BTCUSDT", interval: str = "1h", limit: int = 100, export: bool = True, df_klines: Optional[pd.DataFrame] = None, current_index: Optional[int] = None, umbral_alto: float = 0.85, umbral_medio: float = 0.70, umbral_bajo: float = 0.55) -> dict:
    logger.info(f"Iniciando análisis de mercado para {symbol} - {interval}.")
    
    df_raw = None
    if df_klines is not None:
        if current_index is not None:
            df_raw = df_klines.iloc[:current_index].copy()
        else:
            df_raw = df_klines.copy()
    else:
        df_raw = await get_historical_klines(symbol, interval, limit)

    if df_raw.empty or 'close' not in df_raw.columns:
        logger.warning(f"No se pudieron obtener datos para el análisis de {symbol}.")
        return {"symbol": symbol, "interval": interval, "decision": "No hay datos para analizar", "score": 0}

    latest_close = df_raw.iloc[-1]['close']

    # Cargar el modelo si es necesario (lazy loading)
    if ml_model is None:
        load_ml_model()

    decision = "MANTENER"
    score = 0

    if ml_model is not None:
        try:
            # El modelo pyfunc se encarga de la transformación de features y la predicción
            prediction_df = ml_model.predict(df_raw)

            # El resultado es un DataFrame con 'sell_probability' y 'buy_probability'
            latest_prediction = prediction_df.iloc[-1]
            prob_sell = latest_prediction['sell_probability']
            prob_buy = latest_prediction['buy_probability']

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

    # Para el reporte, necesitamos los indicadores. Los calculamos aquí.
    # Esto es redundante ya que el modelo ya los calcula, pero es necesario para el reporte.
    # En una futura refactorización, el reporte podría ser generado de otra forma.
    feature_pipeline = FeaturePipeline()
    df_features = feature_pipeline.transform(df_raw.copy())
    latest = df_features.iloc[-1]

    rsi_state = "sobreventa" if latest["rsi"] < 30 else "sobrecompra" if latest["rsi"] > 70 else "neutral"
    macd_state = "alcista" if latest["macd"] > latest["macd_signal"] else "bajista"
    stoch_state = "alcista" if latest["stoch_k"] > latest["stoch_d"] else "bajista"
    cci_state = "sobreventa" if latest["cci"] < -100 else "sobrecompra" if latest["cci"] > 100 else "neutral"
    adx_strength = "fuerte" if latest["adx"] > 25 else "débil"
    bb_position = "cerca del techo" if latest["close"] >= latest["bb_upper"] else "cerca del piso" if latest["close"] <= latest["bb_lower"] else "en rango"

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
        "close": latest_close,
        "score": score
    }

    if export:
        export_analysis_result(symbol, interval, result)
        logger.info(f"Análisis exportado a CSV para {symbol}.")

    # La exportación de features ya no es necesaria aquí.
    # export_features(symbol, interval, df_features)

    return result

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    async def main_analysis():
        data = await analyze_market()
        for k, v in data.items():
            print(f"{k}: {v}")
    asyncio.run(main_analysis())


# --- Contenido de regime_detector.py movido aquí ---

class RegimeDetector:
    def __init__(self, data: pd.DataFrame):
        if not isinstance(data, pd.DataFrame) or data.empty:
            raise ValueError("Data must be a non-empty pandas DataFrame.")
        if not all(col in data.columns for col in ['high', 'low', 'close', 'volume']):
            raise ValueError("DataFrame must contain 'high', 'low', 'close', 'volume' columns.")
        self.data = data.copy()
        self._calculate_indicators()

    def _calculate_indicators(self):
        """Calcula todos los indicadores técnicos necesarios."""
        try:
            # Bollinger Bands
            bb = BollingerBands(close=self.data['close'], window=20, window_dev=2)
            self.data['bb_width'] = (bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg()
            self.data['bb_percent'] = (self.data['close'] - bb.bollinger_lband()) / (bb.bollinger_hband() - bb.bollinger_lband())

            # MACD
            macd = MACD(close=self.data['close'])
            self.data['macd_diff'] = macd.macd_diff()

            # ADX
            adx = ADXIndicator(high=self.data['high'], low=self.data['low'], close=self.data['close'], window=14)
            self.data['adx'] = adx.adx()

            # RSI
            rsi = RSIIndicator(close=self.data['close'], window=14)
            self.data['rsi'] = rsi.rsi()
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}", exc_info=True)
            # Rellenar con NaN si hay un error para evitar fallos posteriores
            for col in ['bb_width', 'bb_percent', 'macd_diff', 'adx', 'rsi']:
                if col not in self.data.columns:
                    self.data[col] = np.nan

    def get_market_regime(self) -> str:
        """
        Determina el régimen de mercado actual basado en los indicadores.
        Devuelve una de las siguientes cadenas:
        - 'BULLISH_TREND'
        - 'BEARISH_TREND'
        - 'BULLISH_REVERSAL'
        - 'BEARISH_REVERSAL'
        - 'HIGH_VOLATILITY_RANGE'
        - 'LOW_VOLATILITY_RANGE'
        - 'UNDEFINED'
        """
        if self.data.isnull().values.any():
            logger.warning("Data contains NaN values. Regime detection might be unreliable.")
            return 'UNDEFINED'

        last = self.data.iloc[-1]
        
        # Lógica de detección de régimen
        is_trending = last['adx'] > 25
        is_volatile = last['bb_width'] > self.data['bb_width'].rolling(50).mean().iloc[-1] * 1.2 # 20% por encima de la media

        if is_trending:
            if last['macd_diff'] > 0 and last['rsi'] > 55:
                return 'BULLISH_TREND'
            elif last['macd_diff'] < 0 and last['rsi'] < 45:
                return 'BEARISH_TREND'

        # Lógica de reversión
        if last['bb_percent'] < 0.05 and last['rsi'] < 30:
            return 'BULLISH_REVERSAL' # Potencial suelo
        if last['bb_percent'] > 0.95 and last['rsi'] > 70:
            return 'BEARISH_REVERSAL' # Potencial techo

        # Lógica de rango
        if is_volatile:
            return 'HIGH_VOLATILITY_RANGE'
        else:
            return 'LOW_VOLATILITY_RANGE'
            
        return 'UNDEFINED'
