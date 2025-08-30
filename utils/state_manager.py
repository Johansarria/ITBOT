# utils/state_manager.py

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

STATE_FILE = "data/bot_state.json"

# Moved _json_serializer to top-level and corrected its indentation
def _json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

# Normalización consistente de modo de sesión
def _normalize_mode(val: Any) -> str:
    if not isinstance(val, str):
        return "PAPER_TRADING"
    v = val.strip().lower()
    if v == "live":
        return "LIVE"
    if v in ("paper", "paper_trading", "sim", "simulated", "papertrading"):
        return "PAPER_TRADING"
    # Fallback seguro
    try:
        up = val.upper()
        if up in ("LIVE", "PAPER_TRADING"):
            return up
    except Exception:
        pass
    return "PAPER_TRADING"

class StateManager:
    _instance = None
    _state: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StateManager, cls).__new__(cls)
            cls._instance._load_state()
        return cls._instance

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    self._state = json.load(f)
                # Migración/normalización de modo si viene en formatos antiguos
                try:
                    sess = self._state.get("session", {})
                    if isinstance(sess, dict) and "mode" in sess:
                        norm = _normalize_mode(sess.get("mode"))
                        if sess.get("mode") != norm:
                            sess["mode"] = norm
                            self._state["session"] = sess
                except Exception:
                    pass
            except json.decoder.JSONDecodeError:
                # Si el archivo está vacío o corrupto, inicializar con estado por defecto
                self._state = self._get_default_state()
                self._save_state() # Guardar el estado por defecto
        else:
            # Estado inicial por defecto si el archivo no existe
            self._state = self._get_default_state()
        self._save_state() # Guardar el estado inicial si no existía

    def _get_default_state(self):
        # Intentar usar el modo por defecto de configuración global si está disponible
        try:
            from config import settings as _settings
            default_mode = getattr(_settings, "MODE", "LIVE")
        except Exception:
            default_mode = "LIVE"
        return {
            "risk_manager": {
                "riesgo_actual": 0.01,
                "riesgo_forzado": False,
                "tiempo_riesgo_forzado": None, # Se guardará como string ISO
                "ganancias_riesgo_forzado": 0.0,
                "operaciones_riesgo_forzado": [],
                "recordatorio_riesgo_forzado_hoy": True
            },
            "shield_manager": {
                "escudo_activo": False,
                "tipo_escudo": None,
                "fuente_escudo": None
            },
            "ia_manager": {
                "ia_activa": False,
                "modo_ia": "normal"
            },
            "last_daily_report_date": None, # Para controlar el reporte diario
            "session": {
                "mode": default_mode  # Default session mode (normalizado via _normalize_mode en acceso/escritura)
            },
            "system": {
                "is_paused": False
            }
        }

    def _save_state(self):
        state_to_save = self._state.copy()
        # Removed manual datetime conversion as it's handled by _json_serializer
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(state_to_save, f, indent=4, default=_json_serializer)
            f.flush()
            os.fsync(f.fileno())

    def get_state(self, module: str, key: Optional[str] = None, default_value: Any = None) -> Any:
        self._load_state()  # Forzar la recarga del estado desde el archivo
        if key:
            val = self._state.get(module, {}).get(key, default_value)
            # Normalizar acceso a session.mode y devolver valor consistente
            if module == "session" and key == "mode":
                norm = _normalize_mode(val)
                # Si cambia respecto a lo persistido, persistir normalizado
                if isinstance(self._state.get("session", {}), dict):
                    if self._state["session"].get("mode") != norm:
                        self._state.setdefault("session", {})["mode"] = norm
                        self._save_state()
                return norm
            return val
        return self._state.get(module, default_value)

    def set_state(self, module: str, key: str, value: Any):
        self._load_state()  # Cargar el estado más reciente antes de modificar
        if module not in self._state:
            self._state[module] = {}
        # Normalizar escritura de session.mode
        if module == "session" and key == "mode":
            value = _normalize_mode(value)
        self._state[module][key] = value
        self._save_state()

    def update_module_state(self, module: str, updates: Dict[str, Any]):
        self._load_state()  # Cargar el estado más reciente antes de modificar
        if module not in self._state:
            self._state[module] = {}
        self._state[module].update(updates)
        self._save_state()

# Asegurarse de que la carpeta 'data' exista
os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)