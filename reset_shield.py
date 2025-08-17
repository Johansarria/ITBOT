# reset_shield.py
import logging
from datetime import datetime
from utils.state_manager import StateManager
from utils.logger_setup import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

def reset_shield():
    """
    Desactiva manualmente cualquier escudo activo en el state manager.
    """
    try:
        state_manager = StateManager()
        
        shield_state = state_manager.get_state("shield_manager")
        if not shield_state.get("escudo_activo", False):
            print("✅ El escudo ya se encuentra desactivado. No se necesita ninguna acción.")
            logger.info("El escudo ya se encuentra desactivado.")
            return

        updates = {
            "escudo_activo": False,
            "tipo_escudo": "ninguno",
            "fuente_escudo": "manual_reset",
            "desactivado_at": datetime.now().isoformat()
        }
        state_manager.update_module_state("shield_manager", updates)
        print("✅ Kill Switch (Escudo Extremo) desactivado exitosamente.")
        logger.info("Kill Switch (Escudo Extremo) ha sido desactivado manualmente.")
    except Exception as e:
        print(f"❌ Error al desactivar el escudo: {e}")
        logger.exception("Error al ejecutar reset_shield.py")

if __name__ == "__main__":
    reset_shield()