import pandas as pd
import asyncio
import logging
import os

logger = logging.getLogger(__name__)

COLUMN_ALIASES = {
    'timestamp_open': ['timestamp_open', 'timestamp', 'open_time'],
    'timestamp_close': ['timestamp_close', 'close_time'],
    'symbol': ['symbol', 'asset'],
    'side': ['side', 'trade_type'],
    'entry_price': ['entry_price', 'price_in'],
    'exit_price': ['exit_price', 'price_out'],
    'pnl_percent': ['pnl_percent', 'profit_loss_percent', 'pnl'],
    'operation_id': ['operation_id', 'id']
    # Add all other critical columns and their potential aliases
}

REQUIRED_COLUMNS = [
    'operation_id', 'timestamp_open', 'timestamp_close', 'symbol', 'side',
    'entry_price', 'exit_price', 'pnl_percent'
]

DATE_COLUMNS_MAP = {
    'timestamp_open': ['timestamp_open', 'timestamp', 'open_time'],
    'timestamp_close': ['timestamp_close', 'close_time']
}

class SchemaValidationError(Exception):
    """Custom exception for schema validation failures."""
    pass

async def load_operations_data(file_path: str) -> pd.DataFrame:
    if not os.path.exists(file_path):
        logger.warning(f"Archivo de operaciones no encontrado: {file_path}")
        return pd.DataFrame() # Return empty DataFrame if file not found

    loop = asyncio.get_event_loop()
    
    try:
        # Read CSV without parsing dates initially, we'll handle it manually for robustness
        df = await loop.run_in_executor(None, lambda: pd.read_csv(file_path))
    except Exception as e:
        logger.error(f"Error al leer el archivo CSV {file_path}: {e}", exc_info=True)
        return pd.DataFrame() # Return empty DataFrame on read error

    # Dynamic column renaming based on aliases
    renamed_columns = {}
    for standard_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in df.columns and standard_name not in df.columns:
                renamed_columns[alias] = standard_name
                break # Found an alias, move to next standard_name
    df = df.rename(columns=renamed_columns)

    # Robust Date Parsing should happen before final schema validation
    # to allow for the creation of missing required date columns.
    for standard_date_col, possible_names in DATE_COLUMNS_MAP.items():
        found_date_col = None
        for name in possible_names:
            if name in df.columns:
                found_date_col = name
                break

        if found_date_col:
            try:
                df[standard_date_col] = await loop.run_in_executor(
                    None, lambda col=df[found_date_col]: pd.to_datetime(col, errors='coerce')
                )
                # Drop the original aliased column if it's different
                if found_date_col != standard_date_col and found_date_col in df.columns:
                    df = df.drop(columns=[found_date_col])
            except Exception as e:
                logger.warning(f"Error al parsear columna de fecha '{found_date_col}' en {file_path}: {e}. Columna se mantendrá como está.", exc_info=True)
        else:
            # If the date column or its aliases are not found, create it if required.
            if standard_date_col in REQUIRED_COLUMNS and standard_date_col not in df.columns:
                logger.warning(f"Columna de fecha requerida '{standard_date_col}' no encontrada. Se creará con valores nulos (NaT).")
                df[standard_date_col] = pd.NaT

    # Schema Validation
    missing_required = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_required:
        error_msg = f"Columnas requeridas faltantes en {file_path}: {', '.join(missing_required)}"
        logger.error(error_msg)
        return pd.DataFrame()

    logger.info(f"Datos de operaciones cargados y validados desde {file_path}.")
    return df
