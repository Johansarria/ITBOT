
import os
import csv
from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd
import matplotlib.pyplot as plt
from ta.volatility import BollingerBands
from ta.momentum import RSIIndicator
import logging

def export_features(symbol: str, interval: str, df: pd.DataFrame) -> str:
    """
    Exporta el DataFrame de features enriquecidos a un archivo CSV para análisis histórico y entrenamiento de modelos.
    Guarda todos los features calculados para cada timestamp.
    """
    os.makedirs(BASE_DIR, exist_ok=True)
    filename = f"{symbol}_{interval}_features.csv"
    filepath = os.path.join(BASE_DIR, filename)
    df.to_csv(filepath, index=True)
    return filepath

BASE_DIR = "data/analisis"
CHART_DIR = "storage/reportes/graficos" # ADDED: Directory for charts

os.makedirs(CHART_DIR, exist_ok=True) # ADDED: Ensure chart directory exists

def export_analysis_result(symbol: str, interval: str, result: Dict[str, Any]) -> None:
    """
    Guarda el resultado del análisis técnico en un archivo CSV específico por símbolo e intervalo.
    Si el archivo no existe, lo crea con encabezados.
    """
    os.makedirs(BASE_DIR, exist_ok=True)

    filename = f"{symbol}_{interval}.csv"
    filepath = os.path.join(BASE_DIR, filename)

    # Añadir fecha al resultado
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result_with_timestamp = {"timestamp": now, **result}

    file_exists = os.path.isfile(filepath)
    with open(filepath, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=result_with_timestamp.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(result_with_timestamp)

def generate_analysis_chart(df: pd.DataFrame, symbol: str, interval: str, output_filename: str) -> str:
    """
    Genera un gráfico de velas con Bandas de Bollinger y RSI, y lo guarda como imagen.
    :param df: DataFrame con datos históricos y los indicadores calculados.
    :param symbol: Símbolo del par de trading.
    :param interval: Intervalo de tiempo.
    :param output_filename: Nombre del archivo de salida (ej. "BTCUSDT_1h_chart.png").
    :return: Ruta completa del archivo de imagen generado.
    """
    if df.empty:
        logging.warning("DataFrame vacío, no se puede generar el gráfico.")
        return None

    # Asegurarse de que los indicadores necesarios estén en el DataFrame
    # Si no están, calcularlos (esto es redundante si ya se calculan antes, pero seguro)
    if 'bb_upper' not in df.columns or 'bb_lower' not in df.columns:
        bb = BollingerBands(close=df["close"])
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_lower"] = bb.bollinger_lband()
    
    if 'rsi' not in df.columns:
        df["rsi"] = RSIIndicator(close=df["close"]).rsi()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True, 
                                   gridspec_kw={'height_ratios': [3, 1]}) # 3:1 ratio for price/RSI

    # --- Gráfico de Precios y Bandas de Bollinger (ax1) ---
    ax1.plot(df.index, df['close'], label='Close Price', color='blue')
    ax1.plot(df.index, df['bb_upper'], label='BB Upper', color='red', linestyle='--')
    ax1.plot(df.index, df['bb_lower'], label='BB Lower', color='green', linestyle='--')
    ax1.fill_between(df.index, df['bb_lower'], df['bb_upper'], color='gray', alpha=0.1)
    ax1.set_title(f'{symbol} {interval} Price with Bollinger Bands')
    ax1.set_ylabel('Price')
    ax1.legend()
    ax1.grid(True)

    # --- Gráfico de RSI (ax2) ---
    ax2.plot(df.index, df['rsi'], label='RSI', color='purple')
    ax2.axhline(70, linestyle='--', alpha=0.5, color='red')
    ax2.axhline(30, linestyle='--', alpha=0.5, color='green')
    ax2.set_title('RSI Indicator')
    ax2.set_ylabel('RSI')
    ax2.set_xlabel('Date')
    ax2.grid(True)

    plt.tight_layout()
    
    filepath = os.path.join(CHART_DIR, output_filename)
    plt.savefig(filepath)
    plt.close(fig) # Close the figure to free memory
    logging.info(f"Gráfico generado y guardado en {filepath}")
    return filepath