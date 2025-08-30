"""
Configuración de logging estructurado (JSON) para el proyecto.
Provee get_logger(name) que devuelve un logger configurado con JSON formatter.
"""
import logging
import os
from pythonjsonlogger import jsonlogger

DEFAULT_LEVEL = os.environ.get("LOG_LEVEL", "INFO")


def configure_root_logger():
    root = logging.getLogger()
    if root.handlers:
        return  # ya configurado

    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(DEFAULT_LEVEL)


def get_logger(name: str):
    configure_root_logger()
    return logging.getLogger(name)
