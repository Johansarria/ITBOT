# utils/technical_analysis.py

import os
import inspect
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
from utils.ml_monitor import ml_monitor  # Registrar predicciones ML en JSONL

import asyncio
import time
from functools import wraps
from binance.exceptions import BinanceAPIException, BinanceRequestException # Importar excepciones específicas

import mlflow
import mlflow.pyfunc

# Ruta al modelo de ML entrenado en MLflow
# Esto debería ser gestionado de forma más dinámica, por ejemplo, usando el Model Registry.
# Por ahora, usamos el último run ID conocido.
LAST_RUN_ID = "5006527129a74ad4bb014b9ce8553f51" # Reemplazar con el último run_id si es necesario
MODEL_PATH = f"runs:/{LAST_RUN_ID}/model"
ml_model = None

def load_ml_model() -> None:
    """
    Carga el modelo de Machine Learning usando estrategia de fallback:
    1. Primero intenta cargar desde MLflow 
    2. Si falla, carga el modelo PKL directamente con wrapper manual
    """
    global ml_model
    if ml_model is None:
        # Estrategia 1: Intentar cargar desde MLflow
        try:
            tracking_uri = "file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mlruns"))
            mlflow.set_tracking_uri(tracking_uri)
            ml_model = mlflow.pyfunc.load_model(MODEL_PATH)
            logger.info(f"Modelo PyFunc de ML cargado exitosamente desde MLflow: {MODEL_PATH}")
            return
        except Exception as e:
            logger.warning(f"MLflow no disponible, intentando fallback: {e}")

        # Estrategia 2: Fallback - Cargar PKL directamente con wrapper manual
        try:
            import joblib
            from utils.ml_model_utils import MLModelWrapper

            # Si el usuario configuró explicitamente un .pkl y no existe, respetar y no cargar fallback por defecto
            try:
                if isinstance(MODEL_PATH, str) and MODEL_PATH.endswith('.pkl'):
                    configured_path = MODEL_PATH
                    if not os.path.isabs(configured_path):
                        configured_path = os.path.abspath(configured_path)
                    if not os.path.exists(configured_path):
                        logger.error(f"Modelo PKL no encontrado en ruta configurada: {configured_path}")
                        ml_model = None
                        return
                    else:
                        # Cargar directamente el archivo configurado
                        sklearn_model = joblib.load(configured_path)
                        logger.info(f"Modelo sklearn cargado desde ruta configurada: {configured_path}")
                        feature_columns = [
                            'rsi', 'macd', 'macd_signal', 'stoch_k', 'stoch_d', 'cci',
                            'adx', 'plus_di', 'minus_di', 'atr', 'bb_upper', 'bb_lower'
                        ]

                        class SimpleMLModelWrapperConfigured:
                            def __init__(self, sklearn_model, feature_columns):
                                self.sklearn_model = sklearn_model
                                self.feature_columns = feature_columns
                                from utils.feature_pipeline import FeaturePipeline
                                self.feature_pipeline = FeaturePipeline()

                            def predict(self, df_raw):
                                df_features = self.feature_pipeline.transform(df_raw.copy())
                                X = df_features[self.feature_columns]
                                probabilities = self.sklearn_model.predict_proba(X)
                                import pandas as pd
                                return pd.DataFrame({
                                    "sell_probability": probabilities[:, 0],
                                    "buy_probability": probabilities[:, 1]
                                })

                        ml_model = SimpleMLModelWrapperConfigured(sklearn_model, feature_columns)
                        logger.info("Modelo PKL envuelto exitosamente con SimpleMLModelWrapper")
                        return
            except Exception:
                # Si falla la resolución de la ruta, continuar con el fallback por defecto
                pass

            pkl_path = os.path.join(os.path.dirname(__file__), "..", "data", "ml_models", "lightgbm_model.pkl")
            if os.path.exists(pkl_path):
                # Cargar el modelo pkl (es un pipeline)
                sklearn_model = joblib.load(pkl_path)
                logger.info(f"Modelo sklearn cargado desde: {pkl_path}")
                
                # Crear wrapper manual compatible con MLflow pyfunc
                feature_columns = [
                    'rsi', 'macd', 'macd_signal', 'stoch_k', 'stoch_d', 'cci',
                    'adx', 'plus_di', 'minus_di', 'atr', 'bb_upper', 'bb_lower'
                ]
                
                # Crear una clase wrapper simple para compatibilidad
                class SimpleMLModelWrapper:
                    def __init__(self, sklearn_model, feature_columns):
                        self.sklearn_model = sklearn_model
                        self.feature_columns = feature_columns
                        from utils.feature_pipeline import FeaturePipeline
                        self.feature_pipeline = FeaturePipeline()
                    
                    def predict(self, df_raw):
                        # Generar features
                        df_features = self.feature_pipeline.transform(df_raw.copy())
                        # Seleccionar solo las features del modelo
                        X = df_features[self.feature_columns]
                        # Obtener probabilidades
                        probabilities = self.sklearn_model.predict_proba(X)
                        # Retornar en formato compatible
                        import pandas as pd
                        return pd.DataFrame({
                            "sell_probability": probabilities[:, 0],
                            "buy_probability": probabilities[:, 1]
                        })
                
                ml_model = SimpleMLModelWrapper(sklearn_model, feature_columns)
                logger.info("Modelo PKL envuelto exitosamente con SimpleMLModelWrapper")
            else:
                logger.error(f"Modelo PKL no encontrado en: {pkl_path}")
                ml_model = None
        except Exception as e:
            logger.exception(f"Error cargando modelo PKL como fallback: {e}")
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
    Si no encuentra datos en la BD, intenta leer desde archivos CSV como fallback.
    Args:
        symbol (str): Símbolo de trading (ej: 'BTCUSDT').
        interval (str): Intervalo de tiempo (ej: '1h').
        limit (int): Número máximo de registros a obtener.
    Returns:
        pd.DataFrame: DataFrame con los datos históricos.
    """
    from utils.symbols import suggest_fetch_symbols, normalize_symbol
    original_symbol = symbol
    symbol = normalize_symbol(symbol)
    logger.info(f"Obteniendo klines históricos para {symbol} (orig={original_symbol}) - {interval} (limit: {limit}) desde la BD.")
    # Consultar directamente a la BD respetando el límite (soporta mocks sin parámetro limit)
    try:
        df = get_klines(symbol=symbol, interval=interval, limit=limit)
    except TypeError:
        # Compatibilidad con tests que mockean get_klines(symbol, interval)
        df = get_klines(symbol, interval)

    if df.empty:
        logger.warning(f"No se encontraron klines en la BD para {symbol}-{interval}. Probando alias…")
        # Intentar alias de símbolo en BD
        tried_db_alias = [symbol]
        for cand in suggest_fetch_symbols(original_symbol):
            if cand in tried_db_alias:
                continue
            try:
                df_c = get_klines(symbol=cand, interval=interval, limit=limit)
            except TypeError:
                df_c = get_klines(cand, interval)
            if not df_c.empty:
                logger.info(f"BD: encontrado con alias {cand} (orig={original_symbol}).")
                df = df_c
                symbol = cand
                break
        # Intentar obtener cliente de Binance para fallbacks online
        binance_ok = True
        try:
            client = await get_binance_client()
        except Exception as e:
            binance_ok = False
            logger.warning(f"Fallo al obtener cliente de Binance ({e}). Se intentará solo fallback CSV.")

        # FALLBACK: Intentar leer desde archivos CSV
        logger.info(f"Intentando fallback: lectura desde CSV para {symbol}-{interval} (con alias)")
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        import os
        for cand in suggest_fetch_symbols(original_symbol):
            try:
                csv_path = f"data/analisis/historical_klines_{cand}_{interval}_1_Jan_2022_now.csv"
                if os.path.exists(csv_path):
                    logger.info(f"Archivo CSV encontrado: {csv_path}")
                    csv_df = pd.read_csv(csv_path)
                    if all(col in csv_df.columns for col in required_columns):
                        csv_df['timestamp'] = pd.to_datetime(csv_df['timestamp'], format='mixed', errors='coerce')
                        csv_df = csv_df.dropna(subset=['timestamp'])
                        csv_df.set_index('timestamp', inplace=True)
                        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
                        for col in numeric_cols:
                            csv_df[col] = pd.to_numeric(csv_df[col], errors='coerce')
                        csv_df = csv_df.sort_index()
                        if limit and len(csv_df) > limit:
                            csv_df = csv_df.tail(limit)
                        logger.info(f"✅ Datos cargados desde CSV para {cand}-{interval}: {len(csv_df)} registros (orig={original_symbol})")
                        return csv_df
                    else:
                        logger.warning(f"CSV {csv_path} no tiene columnas requeridas: {required_columns}")
            except Exception as e:
                logger.warning(f"Error leyendo CSV {cand}: {e}")

        # Backfill online rápido desde Binance si cliente disponible
        if binance_ok:
            try:
                # Buscar por alias hasta obtener datos suficientes
                for cand in suggest_fetch_symbols(original_symbol):
                    try:
                        # Usar klines recientes con end_time actual, pedir un bloque razonable
                        now_ms = int(datetime.now().timestamp() * 1000)
                        kl = await client.get_klines(symbol=cand, interval=interval, limit=max(100, limit))
                        # Formatear a DataFrame estándar
                        if kl and len(kl) > 0:
                            df_b = pd.DataFrame(kl, columns=[
                                'open_time','open','high','low','close','volume','close_time','qav','num_trades','taker_base','taker_quote','ignore'
                            ])
                            df_b['timestamp'] = pd.to_datetime(df_b['open_time'], unit='ms')
                            df_b.set_index('timestamp', inplace=True)
                            for col in ['open','high','low','close','volume']:
                                df_b[col] = pd.to_numeric(df_b[col], errors='coerce')
                            df_b = df_b[['open','high','low','close','volume']].dropna()
                            df_b = df_b.sort_index()
                            if limit and len(df_b) > limit:
                                df_b = df_b.tail(limit)
                            logger.info(f"✅ Backfill Binance para {cand}-{interval}: {len(df_b)} registros (orig={original_symbol})")
                            return df_b
                    except Exception as e:
                        logger.debug(f"Binance backfill fallo para {cand}: {e}")
            except Exception as e:
                logger.warning(f"Backfill online falló: {e}")
        
    # Si todo falla, devolver DataFrame vacío
    logger.error(f"No se pudieron obtener datos históricos para {symbol}-{interval} (orig={original_symbol})")
    return pd.DataFrame()
    # Datos obtenidos desde la BD
    logger.info(f"Klines históricos obtenidos desde la BD para {symbol}-{interval}. Filas: {len(df)}")
    # get_klines ya respeta el orden ASC y el límite; por seguridad, recortar si excede
    if limit and len(df) > limit:
        df = df.tail(limit)
    return df

from typing import Optional

async def analyze_market(symbol: str = "BTCUSDT", interval: str = "1h", limit: int = 100, export: bool = True, df_klines: Optional[pd.DataFrame] = None, current_index: Optional[int] = None, umbral_alto: Optional[float] = None, umbral_medio: Optional[float] = None, umbral_bajo: Optional[float] = None) -> dict:
    logger.info(f"Iniciando análisis de mercado para {symbol} - {interval}.")
    
    # Cargar configuración ML desde config
    from config import settings
    # Umbrales base desde settings
    base_high = settings.ML_THRESHOLD_HIGH
    base_med = settings.ML_THRESHOLD_MEDIUM
    base_low = settings.ML_THRESHOLD_LOW

    # Umbrales dinámicos opcionales
    dyn_enabled = getattr(settings, 'ML_DYNAMIC_THRESHOLDS', False)
    if dyn_enabled:
        try:
            from utils.dynamic_thresholds import get_dynamic_thresholds
            dyn = get_dynamic_thresholds(settings)
            base_high = dyn.get('high', base_high)
            base_med = dyn.get('medium', base_med)
            base_low = dyn.get('low', base_low)
            logger.info(f"Umbrales dinámicos activos: high={base_high}, medium={base_med}, low={base_low}")
        except Exception as e:
            logger.warning(f"Fallo obteniendo umbrales dinámicos. Usando base: {e}")

    umbral_alto = umbral_alto or base_high
    umbral_medio = umbral_medio or base_med
    umbral_bajo = umbral_bajo or base_low
    
    logger.info(f"🎯 Umbrales ML configurados: Alto={umbral_alto}, Medio={umbral_medio}, Bajo={umbral_bajo}")
    
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
    
    min_data_points = getattr(settings, 'ML_MIN_DATA_POINTS', 0)
    if min_data_points and len(df_raw) < min_data_points:
        # Permitir bypass en contextos de prueba o cuando el DF se pasa explícitamente
        allow_bypass = (df_klines is not None) or (os.environ.get("ITBOT_TEST_MODE") == "True") or (os.environ.get("ITBOT_ALLOW_SHORT_DF") == "True")
        if not allow_bypass:
            logger.warning(f"Datos insuficientes para ML: {len(df_raw)} < {min_data_points} requeridos. Saltando predicción.")
            return {"symbol": symbol, "interval": interval, "decision": "DATOS_INSUFICIENTES", "score": 0}
        else:
            logger.info(f"Bypass de ML_MIN_DATA_POINTS activado (len={len(df_raw)} < {min_data_points}). Continuando para pruebas/DF provisto.")

    latest_close = df_raw.iloc[-1]['close']

    if ml_model is None:
        load_ml_model()

    decision = "MANTENER"
    score = 0

    if ml_model is not None:
        try:
            prediction_df = ml_model.predict(df_raw)
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

            logger.info(f"🤖 ML Predicción: COMPRAR={prob_buy:.3f}, VENDER={prob_sell:.3f}")
            logger.info(f"🎯 Decisión: {decision}, Score: {score:.1f}")

            # Registrar predicción para monitoreo y umbrales dinámicos
            try:
                ml_monitor.log_prediction(
                    symbol=symbol,
                    timestamp=datetime.now().isoformat(),
                    buy_prob=float(prob_buy),
                    sell_prob=float(prob_sell),
                    decision=str(decision),
                    score=float(score),
                    price=float(latest_close),
                    indicators={
                        "interval": interval,
                        "umbral_alto": float(umbral_alto),
                        "umbral_medio": float(umbral_medio),
                    },
                )
            except Exception as log_exc:
                logger.warning(f"No se pudo registrar la predicción ML: {log_exc}")

        except Exception as e:
            logger.exception(f"Error al realizar la predicción con el modelo de ML: {e}")
            decision = "ERROR_ML"
            score = 0
    else:
        logger.warning("Modelo de ML no cargado. No se puede realizar la predicción.")
        decision = "ERROR_ML_NO_CARGADO"
        score = 0
    
    logger.info(f"Análisis completado para {symbol}. Decisión: {decision}, Score: {score}")

    feature_pipeline = FeaturePipeline()
    df_features = feature_pipeline.transform(df_raw.copy())
    latest = df_features.iloc[-1]

    rsi_state = "sobreventa" if latest["rsi"] < 30 else "sobrecompra" if latest["rsi"] > 70 else "neutral"
    macd_state = "alcista" if latest["macd"] > latest["macd_signal"] else "bajista"
    stoch_state = "alcista" if latest["stoch_k"] > latest["stoch_d"] else "bajista"
    cci_state = "sobreventa" if latest["cci"] < -100 else "sobrecompra" if latest["cci"] > 100 else "neutral"
    adx_strength = "fuerte" if latest["adx"] > 25 else "débil"
    bb_position = "cerca del techo" if latest["close"] >= latest["bb_upper"] else "cerca del piso" if latest["close"] <= latest["bb_lower"] else "en rango"

    ml_info = {}
    if ml_model is not None and decision not in ("ERROR_ML", "ERROR_ML_NO_CARGADO"):
        try:
            prediction_df = ml_model.predict(df_raw)
            latest_prediction = prediction_df.iloc[-1]
            ml_info = {
                "ml_buy_probability": round(latest_prediction['buy_probability'], 3),
                "ml_sell_probability": round(latest_prediction['sell_probability'], 3),
                "ml_status": "ACTIVO",
                "ml_data_points": len(df_raw)
            }
        except Exception as e:
            ml_info = {
                "ml_buy_probability": None,
                "ml_sell_probability": None,
                "ml_status": f"ERROR: {str(e)}",
                "ml_data_points": len(df_raw)
            }
    else:
        ml_info = {
            "ml_buy_probability": None,
            "ml_sell_probability": None,
            "ml_status": "NO_DISPONIBLE" if ml_model is None else "ERROR_ML",
            "ml_data_points": len(df_raw)
        }

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
        "score": score,
        **ml_info
    }

    if export:
        export_analysis_result(symbol, interval, result)
        logger.info(f"Análisis exportado a CSV para {symbol}.")

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
