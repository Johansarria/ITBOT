# --- Escudo por drift de modelo ---
import pandas as pd
from ta.volatility import AverageTrueRange
import asyncio
from datetime import datetime
import logging # Importar logging
import aiohttp # Importar aiohttp

# Mis imports
from utils.state_manager import StateManager
from utils.telegram_handler import send_message
from aiogram import Bot
from utils.binance_client import get_binance_client # Importar la función para obtener el cliente de Binance
from binance.exceptions import BinanceAPIException, BinanceRequestException # Importar excepciones específicas

logger = logging.getLogger(__name__) # Obtener logger para este módulo

# --- Configuración ---
VOLATILITY_THRESHOLD_PERCENT = 1.5

# Obtener la instancia del StateManager
state_manager = StateManager()

# --- Funciones para el estado del escudo (manual/bot) ---

async def activar_escudo(bot_instance: Bot, chat_id: int, tipo: str, fuente: str = "manual", send_notification: bool = True):
    logger.info(f"Intentando activar escudo: {tipo} por {fuente}. ")
    shield_state = state_manager.get_state("shield_manager")
    
    if shield_state.get("escudo_activo", False) and shield_state.get("tipo_escudo") == tipo.lower():
        logger.info(f"Escudo {tipo} ya está activo. No se realiza acción. ")
        return

    updates = {
        "escudo_activo": True,
        "tipo_escudo": tipo.lower(),
        "fuente_escudo": fuente,
        "activado_at": datetime.now().isoformat()
    }
    state_manager.update_module_state("shield_manager", updates)
    
    if send_notification:
        fuente_txt = "por el usuario" if fuente == "manual" else "automáticamente por el bot"
        
        if fuente == "manual":
            mensaje = f"🛡️ ESCUDO {tipo.upper()} ACTIVADO {fuente_txt}.\n\n<i>Este escudo permanecerá activo hasta que se desactive manualmente.</i>"
        else: # fuente == 'bot'
            mensaje = f"🛡️ ESCUDO {tipo.upper()} ACTIVADO {fuente_txt}.\n\n<i>Se desactivará automáticamente si las condiciones del mercado mejoran.</i>"

        logger.warning(f"ESCUDO {tipo.upper()} ACTIVADO por {fuente}.") # Log conciso
        await send_message(bot_instance, chat_id, mensaje)

async def desactivar_escudo(bot_instance: Bot, chat_id: int, fuente: str = "manual", send_notification: bool = True):
    logger.info(f"Intentando desactivar escudo por {fuente}. ")
    shield_state = state_manager.get_state("shield_manager")
    
    if not shield_state.get("escudo_activo", False):
        logger.info("No hay escudo activo para desactivar. ")
        # No enviar mensaje al usuario si no había nada que hacer
        return

    updates = {
        "escudo_activo": False,
        "tipo_escudo": "ninguno",
        "fuente_escudo": None,
        "desactivado_at": datetime.now().isoformat()
    }
    state_manager.update_module_state("shield_manager", updates)
    
    if send_notification:
        fuente_txt = "por el usuario" if fuente == "manual" else "automáticamente por el bot"
        mensaje = f"🔓 ESCUDO DESACTIVADO {fuente_txt}.\n\n<i>El bot reanudará su operativa normal.</i>"
        logger.warning(mensaje)
        await send_message(bot_instance, chat_id, mensaje)

def escudo_activo() -> str:
    shield_state = state_manager.get_state("shield_manager")
    tipo = shield_state.get("tipo_escudo", "ninguno")
    logger.debug(f"Estado actual del escudo: {tipo}. ")
    return tipo

def obtener_estado_escudo() -> tuple[bool, str]:
    """Devuelve un booleano y una cadena de texto que describe el estado actual del escudo."""
    shield_state = state_manager.get_state("shield_manager")
    is_active = shield_state.get("escudo_activo", False)
    
    if is_active:
        tipo = shield_state.get("tipo_escudo", "desconocido").upper()
        fuente = shield_state.get("fuente_escudo", "desconocida")
        activado_at = shield_state.get("activado_at")
        
        if activado_at:
            try:
                activado_dt = datetime.fromisoformat(activado_at)
                duracion = datetime.now() - activado_dt
                horas = int(duracion.total_seconds() // 3600)
                minutos = int((duracion.total_seconds() % 3600) // 60)
                if horas > 0:
                    texto_duracion = f"hace {horas}h {minutos}m"
                else:
                    texto_duracion = f"hace {minutos}m"
                return True, f"🛡️ ACTIVO: {tipo} (por {fuente} {texto_duracion})"
            except ValueError:
                return True, f"🛡️ ACTIVO: {tipo} (por {fuente}, tiempo inv.)"
        else:
            return True, f"🛡️ ACTIVO: {tipo} (por {fuente})"
    else:
        return False, "✅ INACTIVO"

def obtener_estado_escudo_texto() -> str:
    """Función de conveniencia que solo devuelve el texto. Mantenida por retrocompatibilidad si es necesario."""
    _, texto = obtener_estado_escudo()
    return texto

# --- Función para la verificación automática de condiciones ---

async def verificar_condiciones_mercado(bot_instance: Bot, chat_id: int) -> dict:
    logger.info("Verificando condiciones de mercado (volatilidad). ")
    try:
        symbol = "BTCUSDT"
        interval = "1h"
        client_instance = await get_binance_client() # MODIFIED: Added await
        logger.debug(f"Type of client_instance: {type(client_instance)}") # NEW DEBUG
        klines = await client_instance.get_klines(symbol=symbol, interval=interval, limit=100)
        logger.debug(f"Type of klines: {type(klines)}")
        logger.debug(f"Content of klines (first 2): {klines[:2] if isinstance(klines, list) else klines}")
        logger.debug(f"Length of klines: {len(klines) if isinstance(klines, list) else 'N/A'}")
        logger.debug(f"Length of first kline: {len(klines[0]) if klines and isinstance(klines, list) and len(klines) > 0 else 'N/A'}")
        
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_vol', 'taker_buy_quote_vol', 'ignore'
        ])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        
        atr_indicator = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14)
        df['atr'] = atr_indicator.average_true_range()

        if df.empty or 'atr' not in df.columns or df['atr'].iloc[-1] is None or pd.isna(df['atr'].iloc[-1]):
            logger.warning("No se pudo calcular el ATR. Se asumen condiciones seguras.")
            return {"status": "SAFE", "reason": "No se pudo calcular la volatilidad (ATR)."}

        latest_atr = df['atr'].iloc[-1]
        latest_close = df['close'].iloc[-1]

        if latest_close == 0:
            logger.warning("El precio de cierre es 0, no se puede calcular la volatilidad.")
            return {"status": "SAFE", "reason": "Precio de cierre cero, no se puede calcular volatilidad."}

        volatility_percent = (latest_atr / latest_close) * 100
        logger.info(f"Volatilidad actual para {symbol}: {volatility_percent:.2f}%. Umbral: {VOLATILITY_THRESHOLD_PERCENT}%. ")

        if volatility_percent > VOLATILITY_THRESHOLD_PERCENT:
            reason = f"Volatilidad Extrema detectada en {symbol} ({volatility_percent:.2f}%)."
            logger.warning(f"Condiciones de mercado peligrosas: {reason}")
            await activar_escudo(bot_instance, chat_id, tipo="volatilidad_alta", fuente="bot")
            return {"status": "DANGER", "reason": reason}
        else:
            logger.info("Condiciones de mercado estables. ")
            shield_state = state_manager.get_state("shield_manager")
            if shield_state.get("fuente_escudo") == "bot" and shield_state.get("tipo_escudo") == "volatilidad_alta":
                logger.info("Desactivando escudo automático ya que las condiciones son estables. ")
                await desactivar_escudo(bot_instance, chat_id, fuente="bot")
            return {"status": "SAFE", "reason": "Condiciones de mercado estables."}

    except (BinanceAPIException, BinanceRequestException) as e:
        logger.error(f"Error de la API de Binance al verificar condiciones del mercado: {e}", exc_info=True)
        await activar_escudo(bot_instance, chat_id, tipo="extremo", fuente="bot")
        return {"status": "DANGER", "reason": f"Error de la API de Binance al analizar el mercado: {e}"}
    except aiohttp.ClientError as e:
        logger.error(f"Error de conexión al verificar condiciones del mercado: {e}", exc_info=True)
        await activar_escudo(bot_instance, chat_id, tipo="extremo", fuente="bot")
        return {"status": "DANGER", "reason": f"Error de conexión al analizar el mercado: {e}"}
    except Exception as e:
        logger.exception(f"Error inesperado al verificar las condiciones del mercado: {e}")
        await activar_escudo(bot_instance, chat_id, tipo="extremo", fuente="bot")
        return {"status": "DANGER", "reason": f"Error inesperado al analizar el mercado: {e}"}
