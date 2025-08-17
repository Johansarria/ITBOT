import os
from dotenv import load_dotenv
from pathlib import Path

def load_env():
    # Forza la carga absoluta del archivo .env desde la raíz del proyecto
    env_path = Path(__file__).resolve().parent.parent / ".env"
    print(f"DEBUG: Intentando cargar .env desde: {env_path}") # DEBUG
    
    # load_dotenv devuelve True si carga el archivo, False si no lo encuentra
    loaded = load_dotenv(dotenv_path=env_path)
    
    # Recuperar las variables del entorno
    env_vars = {
        "BINANCE_API_KEY": os.getenv("BINANCE_API_KEY"),
        "BINANCE_SECRET_KEY": os.getenv("BINANCE_SECRET_KEY"),
        "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
        "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID")
    }
    return env_vars