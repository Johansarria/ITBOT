# init_audit_db.py
import logging
from utils.audit_operations_db import ensure_operations_table
from utils.logger_setup import setup_logging

if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Inicializando la tabla 'audit_operations' en la base de datos PostgreSQL...")
    try:
        ensure_operations_table()
        logger.info("Tabla 'audit_operations' verificada/creada exitosamente.")
    except Exception as e:
        logger.error(f"No se pudo inicializar la tabla de auditoría: {e}", exc_info=True)
