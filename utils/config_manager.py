import os
import re
import logging

logger = logging.getLogger(__name__)

def update_env_variable(key: str, value: str, env_path: str = '.env') -> bool:
    """
    Actualiza el valor de una variable en el archivo .env.
    Si la variable no existe, la añade al final.
    """
    try:
        if not os.path.exists(env_path):
            with open(env_path, 'w') as f:
                f.write(f"{key}={value}\n")
            logger.info(f"Variable {key} añadida al .env con valor {value}.")
            return True

        with open(env_path, 'r') as f:
            lines = f.readlines()

        updated = False
        with open(env_path, 'w') as f:
            for line in lines:
                if line.startswith(f"{key}="):
                    f.write(f"{key}={value}\n")
                    updated = True
                    logger.info(f"Variable {key} actualizada en .env a {value}.")
                else:
                    f.write(line)
            if not updated:
                f.write(f"{key}={value}\n")
                logger.info(f"Variable {key} añadida al .env con valor {value}.")
        return True
    except Exception as e:
        logger.error(f"Error al actualizar la variable {key} en el archivo .env: {e}", exc_info=True)
        return False
