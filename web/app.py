#!/usr/bin/env python3
"""
ITBOT Web Panel - Panel de control web avanzado para ITBOT

Este módulo proporciona una interfaz web completa para la configuración
avanzada y monitoreo del bot de trading.

Arquitectura Híbrida:
- Telegram: Comandos básicos de monitoreo
- Web: Configuración avanzada, backtesting, análisis profundo
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for, send_file, Response
from flask_socketio import SocketIO, emit
import asyncio
import os
import sys
import json
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import glob
from sqlalchemy import text as _sa_text

# Agregar el directorio raíz al path para importar módulos (antes de imports locales)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# DB access
try:
    from database.database_manager import get_db_session
except Exception:
    get_db_session = None

# Importar módulos del bot
try:
    import telegram_logic_adapter as logic_stubs
    from modules.dynamic_pair_manager import dynamic_pair_manager
    from utils.notification_manager import notification_manager
    import config
    from utils import risk_manager as risk
    from strategies.backtester import Backtester, generate_mock_data
    from strategies.ml_strategy import MLStrategy
    import pandas as pd
    import numpy as np
    # ML thresholds tooling
    from utils.dynamic_thresholds import get_dynamic_thresholds
    from utils.ml_monitor import ml_monitor
    # Generador de equity histórico desde DB
    from tools.generate_equity_history import compute_equity_df
    # Risk manager APIs
    from utils import risk_manager as risk
except ImportError as e:
    print(f"Error importing bot modules: {e}")
    print("Some features may not be available")

# Configuración Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'itbot-web-secret-2024')

# Configuración SocketIO para actualizaciones en tiempo real
socketio = SocketIO(app, cors_allowed_origins="*")

# Logger específico para el web panel
logger = logging.getLogger(__name__)

# Variables globales para el estado de la aplicación
active_sessions = {}
last_update = {}

# --- Auditoría simple a JSONL ---
THRESHOLD_AUDIT_FILE = os.path.join('logs', 'ml_threshold_audit.jsonl')
RISK_LIMITS_AUDIT_FILE = os.path.join('logs', 'risk_limits_audit.jsonl')

# --- cTrader snapshot storage (simple file persistence) ---
CTRADER_DIR = os.path.join('data', 'ctrader')
CTRADER_ACCOUNT_FILE = os.path.join(CTRADER_DIR, 'account.json')
CTRADER_POSITIONS_FILE = os.path.join(CTRADER_DIR, 'positions.json')
CTRADER_ORDERS_QUEUE_FILE = os.path.join(CTRADER_DIR, 'orders_queue.json')
CTRADER_ORDERS_RESULTS_FILE = os.path.join(CTRADER_DIR, 'orders_results.json')

def _ensure_ctrader_dir():
    try:
        os.makedirs(CTRADER_DIR, exist_ok=True)
    except Exception:
        pass

def _read_json_file(path: str, default):
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"No se pudo leer {path}: {e}")
    return default

def _write_json_file(path: str, data: dict | list):
    try:
        _ensure_ctrader_dir()
        with open(path, 'w') as f:
            json.dump(data, f)
        return True
    except Exception as e:
        logger.error(f"No se pudo escribir {path}: {e}")
        return False

def _append_jsonl_file(path: str, record: dict) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'a') as f:
            f.write(json.dumps(record) + '\n')
        return True
    except Exception:
        return False

def _audit_threshold_event(event: str, payload: dict) -> None:
    try:
        os.makedirs(os.path.dirname(THRESHOLD_AUDIT_FILE), exist_ok=True)
        record = {
            'timestamp': datetime.now().isoformat(),
            'event': event,
            **{k: sanitize_json(v) for k, v in (payload or {}).items()}
        }
        with open(THRESHOLD_AUDIT_FILE, 'a') as f:
            f.write(json.dumps(record) + '\n')
    except Exception as e:
        logger.error(f"Error escribiendo auditoría de umbrales: {e}")

def _sanitize_mapping(m: dict) -> dict:
    out = {}
    try:
        for k, v in (m or {}).items():
            out[str(k)] = sanitize_json(v)
    except Exception:
        pass
    return out

def _sanitize_sequence(seq: list) -> list:
    try:
        return [sanitize_json(x) for x in (seq or [])]
    except Exception:
        return []

def _audit_risk_event(event: str, payload: dict) -> None:
    """Audita eventos de configuración de riesgo (incluye límites por símbolo)."""
    try:
        os.makedirs(os.path.dirname(RISK_LIMITS_AUDIT_FILE), exist_ok=True)
        record = {
            'timestamp': datetime.now().isoformat(),
            'event': event,
            **{k: sanitize_json(v) for k, v in (payload or {}).items()}
        }
        with open(RISK_LIMITS_AUDIT_FILE, 'a') as f:
            f.write(json.dumps(record) + '\n')
    except Exception as e:
        logger.error(f"Error escribiendo auditoría de riesgo: {e}")

# Utilidad global para sanear objetos antes de serializarlos a JSON
def sanitize_json(v: Any):
    try:
        if isinstance(v, (str, int, float)) or v is None:
            return v
        if isinstance(v, bool):
            return bool(v)
        # numpy tipos con .item()
        if hasattr(v, 'item'):
            try:
                return v.item()
            except Exception:
                pass
        if isinstance(v, (list, tuple)):
            return [sanitize_json(x) for x in v]
        if isinstance(v, dict):
            return {str(k): sanitize_json(val) for k, val in v.items()}
        # Evitar forzar a float tipos arbitrarios; usar str como último recurso
        return str(v)
    except Exception:
        try:
            return str(v)
        except Exception:
            return None

# Helper: convertir volatilidad anual a diaria, tolerante a tipos numpy/str
def daily_volatility_from_annual(val: Any) -> Optional[float]:
    try:
        if val is None:
            return None
        # Intentar float directo
        try:
            v = float(val)
        except Exception:
            # numpy scalar u otros con .item()
            if hasattr(val, 'item'):
                try:
                    v = float(val.item())
                except Exception:
                    return None
            else:
                return None
        return v / math.sqrt(365.0)
    except Exception:
        return None

# --- Uptime LIVE persistente ---
LIVE_UPTIME_FILE = os.path.join('data', 'live_uptime.json')

def _load_live_uptime_state() -> dict:
    try:
        if os.path.exists(LIVE_UPTIME_FILE):
            with open(LIVE_UPTIME_FILE, 'r') as f:
                data = json.load(f)
                # Valores por defecto si faltan
                data.setdefault('total_live_seconds', 0)
                data.setdefault('last_live_start', None)
                data.setdefault('first_live_start', None)
                return data
    except Exception as e:
        logger.warning(f"No se pudo leer estado de uptime LIVE, se reinicia: {e}")
    return {'total_live_seconds': 0, 'last_live_start': None, 'first_live_start': None}

def _save_live_uptime_state(state: dict) -> None:
    try:
        os.makedirs(os.path.dirname(LIVE_UPTIME_FILE), exist_ok=True)
        with open(LIVE_UPTIME_FILE, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        logger.error(f"Error guardando estado de uptime LIVE: {e}")

def _format_duration(seconds: int) -> str:
    seconds = int(max(0, seconds))
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return ' '.join(parts)

class WebAuthManager:
    """Gestor simple de autenticación para el panel web"""
    
    def __init__(self):
        self.valid_tokens = {}
        self.session_timeout = timedelta(hours=1)
    
    def generate_session(self, user_id: str = "default") -> str:
        """Genera una sesión temporal"""
        import uuid
        token = str(uuid.uuid4())[:16]
        self.valid_tokens[token] = {
            'user_id': user_id,
            'created_at': datetime.now(),
            'last_activity': datetime.now()
        }
        return token
    
    def validate_token(self, token: str) -> bool:
        """Valida si un token es válido y no ha expirado"""
        if token not in self.valid_tokens:
            return False
        
        session = self.valid_tokens[token]
        if datetime.now() - session['created_at'] > self.session_timeout:
            del self.valid_tokens[token]
            return False
        
        # Actualizar última actividad
        session['last_activity'] = datetime.now()
        return True
    
    def cleanup_expired_sessions(self):
        """Limpia sesiones expiradas"""
        expired = []
        for token, session in self.valid_tokens.items():
            if datetime.now() - session['created_at'] > self.session_timeout:
                expired.append(token)
        
        for token in expired:
            del self.valid_tokens[token]

    def get_session(self, token: str) -> Optional[dict]:
        """Obtiene la sesión asociada a un token (sin modificar actividad)."""
        return self.valid_tokens.get(token)

    def is_admin(self, token: str) -> bool:
        """Verifica si el token pertenece al administrador configurado."""
        try:
            sess = self.get_session(token)
            if not sess:
                return False
            user_id = sess.get('user_id')
            admin_id = getattr(config.settings, 'ADMIN_TELEGRAM_ID', None)
            if admin_id is None or user_id is None:
                return False
            # Comparación robusta (str/int)
            try:
                return int(user_id) == int(admin_id)
            except Exception:
                return str(user_id) == str(admin_id)
        except Exception:
            return False

# Instancia global del gestor de autenticación
auth_manager = WebAuthManager()

# Logo helper: path configured for Telegram banner can be reused as web logo
def get_default_logo_path() -> Optional[str]:
    try:
        banner_path = getattr(config.settings, 'BANNER_IMAGE_PATH', None)
        if banner_path and os.path.isfile(banner_path):
            return banner_path
    except Exception:
        pass
    # fallback to static logo
    static_logo = os.path.join(os.path.dirname(__file__), 'static', 'img', 'logo.svg')
    return static_logo if os.path.exists(static_logo) else None

@app.route('/assets/logo')
def serve_logo():
    """Sirve el logo: usa el banner del bot si existe, si no el logo estático."""
    p = get_default_logo_path()
    if p and os.path.exists(p):
        # Mejorar cache
        try:
            return send_file(p)
        except Exception:
            pass
    # Fallback a un 404 amigable
    return Response('Logo no disponible', status=404)

@app.route('/')
def index():
    """Página principal - redirecciona al dashboard"""
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """Dashboard principal del panel web"""
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return render_template('login.html', error="Token inválido o expirado")
    
    return render_template('dashboard.html', token=token)

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    """Página de login con formulario para ingresar token"""
    if request.method == 'POST':
        token = request.form.get('token', '').strip()
        if token and auth_manager.validate_token(token):
            return redirect(url_for('dashboard', token=token))
        else:
            return render_template('login.html', error="Token inválido o expirado")
    # GET
    return render_template('login.html', error=None)

@app.route('/api/generate_token', methods=['GET', 'POST'])
def api_generate_token():
    """API para generar un token de acceso temporal (1h)"""
    try:
        user_id = request.args.get('user_id') or (request.json.get('user_id') if request.is_json else None) or 'default'
    except Exception:
        user_id = 'default'
    token = auth_manager.generate_session(user_id=str(user_id))
    expires_at = (datetime.now() + auth_manager.session_timeout).isoformat()
    return jsonify({
        'success': True,
        'token': token,
        'expires_at': expires_at
    })

@app.route('/config')
def config_page():
    """Página de configuración avanzada"""
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return render_template('login.html', error="Acceso no autorizado")
    
    return render_template('config.html', token=token)

@app.route('/backtesting')
def backtesting():
    """Página de backtesting"""
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return render_template('login.html', error="Acceso no autorizado")
    
    return render_template('backtesting.html', token=token)

# ------------------ CONFIG API ------------------

@app.route('/api/config/info')
def api_config_info():
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Valores por defecto (settings) y efectivos (con overrides si existen)
        cfg_defaults = {
            'RISK_PER_TRADE_STOP_LOSS_PCT': getattr(config.settings, 'RISK_PER_TRADE_STOP_LOSS_PCT', None),
            'RISK_PER_TRADE_TAKE_PROFIT_PCT': getattr(config.settings, 'RISK_PER_TRADE_TAKE_PROFIT_PCT', None),
            'RISK_MAX_CONCURRENT_TRADES': getattr(config.settings, 'RISK_MAX_CONCURRENT_TRADES', None),
            'RISK_MAX_EXPOSURE_PCT': getattr(config.settings, 'RISK_MAX_EXPOSURE_PCT', None),
            'RISK_MAX_DAILY_DRAWDOWN_PCT': getattr(config.settings, 'RISK_MAX_DAILY_DRAWDOWN_PCT', None),
            'DEFAULT_RISK_PERCENTAGE': getattr(config.settings, 'DEFAULT_RISK_PERCENTAGE', None),
            'RISK_MAX_PER_SYMBOL_TRADES': getattr(config.settings, 'RISK_MAX_PER_SYMBOL_TRADES', None),
            'RISK_MAX_PER_SYMBOL_EXPOSURE_PCT': getattr(config.settings, 'RISK_MAX_PER_SYMBOL_EXPOSURE_PCT', None),
        }
        cfg_effective = risk.get_effective_risk_params()

        # Estado de riesgo (modo y porcentaje actual)
        risk_state = {
            'manual': risk.riesgo_forzado_activo(),
            'current_risk_pct': round(risk.obtener_riesgo_actual() * 100, 2),
            'custom_params_active': risk.custom_risk_params_active()
        }

        # Umbrales optimizados
        thresholds = risk.cargar_umbrales_optimizado()

        return jsonify({'success': True, 'config_defaults': cfg_defaults, 'config_effective': cfg_effective, 'risk': risk_state, 'thresholds': thresholds})
    except Exception as e:
        logger.error(f"Error en api_config_info: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/config/set_thresholds', methods=['POST'])
def api_set_thresholds():
    token = request.args.get('token') or (request.json.get('token') if request.is_json else None)
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        data = request.get_json(force=True)
        ua = float(data.get('umbral_alto'))
        um = float(data.get('umbral_medio'))
        ub = float(data.get('umbral_bajo'))
        if not (0 <= ub <= um <= ua <= 1):
            return jsonify({'error': 'Los umbrales deben estar en [0,1] y en orden bajo<=medio<=alto'}), 400
        risk.guardar_umbrales_optimizado({'umbral_alto': ua, 'umbral_medio': um, 'umbral_bajo': ub})
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error guardando umbrales: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/config/set_risk_mode', methods=['POST'])
def api_set_risk_mode():
    token = request.args.get('token') or (request.json.get('token') if request.is_json else None)
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        data = request.get_json(force=True)
        mode = str(data.get('mode', 'auto')).lower()
        if mode == 'manual':
            pct = float(data.get('percentage', 0))
            if not (0 < pct <= 100):
                return jsonify({'error': 'Porcentaje inválido (0-100]'}), 400
            risk.activar_riesgo_forzado(pct)
        else:
            risk.restaurar_riesgo_automatico()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error cambiando modo de riesgo: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/config/set_risk_params', methods=['POST'])
def api_set_risk_params():
    token = request.args.get('token') or (request.json.get('token') if request.is_json else None)
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        data = request.get_json(force=True)
        # Aceptamos subset de claves permitidas
        allowed = {'RISK_PER_TRADE_STOP_LOSS_PCT','RISK_PER_TRADE_TAKE_PROFIT_PCT','RISK_MAX_CONCURRENT_TRADES','RISK_MAX_EXPOSURE_PCT','RISK_MAX_DAILY_DRAWDOWN_PCT','DEFAULT_RISK_PERCENTAGE','RISK_MAX_PER_SYMBOL_TRADES','RISK_MAX_PER_SYMBOL_EXPOSURE_PCT'}
        clean = {k: data[k] for k in data.keys() if k in allowed}
        if not clean:
            return jsonify({'error': 'Sin parámetros válidos'}), 400
        risk.set_custom_risk_params(clean)
        try:
            _audit_risk_event('set_risk_params', {'user_token': request.args.get('token') or (request.json.get('token') if request.is_json else None), 'applied': clean})
        except Exception:
            pass
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error set_risk_params: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/config/reset_risk_params', methods=['POST'])
def api_reset_risk_params():
    token = request.args.get('token') or (request.json.get('token') if request.is_json else None)
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        risk.reset_custom_risk_params()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error reset_risk_params: {e}")
        return jsonify({'error': str(e)}), 500

# ------------------ BACKTESTING API ------------------

@app.route('/api/backtest/run', methods=['POST'])
def api_backtest_run():
    token = request.args.get('token') or (request.json.get('token') if request.is_json else None)
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        payload = request.get_json(force=True) if request.is_json else {}
        source = payload.get('source', 'mock')
        initial_balance = float(payload.get('initial_balance', 1000.0))
        commission = float(payload.get('commission', 0.001))
        warmup = int(payload.get('warmup_period', 100))
        
        # Preparar datos
        if source == 'file':
            file_path = payload.get('file_path', '')
            if not file_path or not os.path.exists(file_path):
                return jsonify({'error': 'Archivo no encontrado'}), 400
            historical = pd.read_csv(file_path, index_col='timestamp', parse_dates=True)
        else:
            days = int(payload.get('days', 500))
            historical = generate_mock_data(days=days, initial_price=50000)

        # Ejecutar backtest con MLStrategy
        def run_bt():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            strategy = MLStrategy()
            bt = Backtester(historical, initial_balance=initial_balance, commission=commission, warmup_period=warmup)
            return loop.run_until_complete(bt.run(strategy))

        metrics = run_bt()
        return jsonify({'success': True, 'metrics': metrics})
    except Exception as e:
        logger.error(f"Error ejecutando backtest: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
def api_status():
    """API: Estado actual del bot"""
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Obtener estado del bot de forma asíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        status = loop.run_until_complete(get_bot_status())
        
        return jsonify({
            'success': True,
            'data': status,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting bot status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/test')
def api_test():
    """API de prueba simple"""
    return jsonify({'message': 'API Test OK', 'timestamp': datetime.now().isoformat()})

# ------------------ cTrader PUSH/GET APIs ------------------

@app.route('/api/ctrader/push', methods=['POST'])
def api_ctrader_push():
    """Recibe snapshot de cuenta y posiciones desde cTrader (cBot) y lo persiste.

    Body JSON esperado: { account: {...}, positions: [...] }
    Token por query o body.
    """
    token = request.args.get('token') or (request.json.get('token') if request.is_json else None)
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        payload = request.get_json(force=True) if request.is_json else {}
        account = payload.get('account') or {}
        positions = payload.get('positions') or []

        # Saneado mínimo
        account['updated_at'] = datetime.now().isoformat()
        for p in positions:
            p.setdefault('updated_at', account['updated_at'])

        acc_clean = _sanitize_mapping(account) if isinstance(account, dict) else {}
        pos_clean = _sanitize_sequence(positions) if isinstance(positions, list) else []

        ok_acc = _write_json_file(CTRADER_ACCOUNT_FILE, acc_clean)
        ok_pos = _write_json_file(CTRADER_POSITIONS_FILE, pos_clean)
        return jsonify({'success': bool(ok_acc and ok_pos), 'stored': {'account': ok_acc, 'positions': ok_pos}})
    except Exception as e:
        logger.error(f"Error en api_ctrader_push: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ctrader/account')
def api_ctrader_account():
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        acc = _read_json_file(CTRADER_ACCOUNT_FILE, default={})
        return jsonify({'success': True, 'account': acc})
    except Exception as e:
        logger.error(f"Error en api_ctrader_account: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ctrader/positions')
def api_ctrader_positions():
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        pos = _read_json_file(CTRADER_POSITIONS_FILE, default=[])
        # Enriquecer con PnL y precio actual si faltan
        if isinstance(pos, list) and pos:
            # 1) Construir mapa de precios actual desde Binance para minimizar llamadas
            price_map: dict[str, float] = {}
            try:
                import asyncio as _asyncio
                from utils.binance_client import get_binance_client as _get_cli
                _loop = _asyncio.new_event_loop()
                _asyncio.set_event_loop(_loop)
                _client = _loop.run_until_complete(_get_cli())
                _tickers = _loop.run_until_complete(_client.get_all_tickers())
                if isinstance(_tickers, list):
                    for _t in _tickers:
                        try:
                            sym = _t.get('symbol')
                            pr = _t.get('price')
                            if sym and pr is not None:
                                price_map[str(sym).upper()] = float(pr)
                        except Exception:
                            continue
            except Exception:
                price_map = {}

            def _norm_side(v: Any) -> str:
                try:
                    s = str(v).upper()
                    if s.startswith('S') or s == 'SHORT':
                        return 'SELL'
                    return 'BUY'
                except Exception:
                    return 'BUY'

            def _to_float(x: Any) -> Optional[float]:
                try:
                    return float(x)
                except Exception:
                    return None

            def _map_to_binance(sym: Optional[str]) -> Optional[str]:
                if not sym:
                    return None
                s = sym.upper().replace(' ', '')
                # casos directos
                if s in price_map:
                    return s
                # USD -> USDT
                if s.endswith('USD') and not s.endswith('USDT'):
                    s2 = s[:-3] + 'USDT'
                    if s2 in price_map:
                        return s2
                # Si ya termina en USDT pero no existe, no insistir
                return None

            for p in pos:
                try:
                    sym = p.get('symbol') or p.get('Symbol') or p.get('pair')
                    side = _norm_side(p.get('side') or p.get('Side') or p.get('direction'))
                    size = _to_float(p.get('size') or p.get('volume') or p.get('qty')) or 0.0
                    entry = (
                        _to_float(p.get('entry_price'))
                        or _to_float(p.get('entryPrice'))
                        or _to_float(p.get('price'))
                    )
                    current = (
                        _to_float(p.get('current_price'))
                        or _to_float(p.get('currentPrice'))
                        or _to_float(p.get('lastPrice'))
                    )
                    # Completar precio actual desde Binance si falta
                    if current is None:
                        bsym = _map_to_binance(sym)
                        if bsym and bsym in price_map:
                            current = price_map.get(bsym)
                            if current is not None:
                                p['current_price'] = current
                    # Calcular PnL si es posible y si no viene provisto
                    if p.get('pnl_usd') is None and entry is not None and current is not None and size:
                        pnl_usd = (current - entry) * size if side == 'BUY' else (entry - current) * size
                        p['pnl_usd'] = float(pnl_usd)
                    if p.get('pnl_pct') is None and entry is not None and current is not None and entry != 0:
                        base_pct = ((current - entry) / entry * 100.0)
                        p['pnl_pct'] = float(base_pct if side == 'BUY' else -base_pct)
                    # Normalizar campos clave
                    if sym:
                        p['symbol'] = str(sym).upper()
                    p['side'] = side
                except Exception:
                    continue
        return jsonify({'success': True, 'positions': pos, 'count': len(pos) if isinstance(pos, list) else 0})
    except Exception as e:
        logger.error(f"Error en api_ctrader_positions: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ------------------ cTrader ORDER EXECUTION BRIDGE ------------------

from flask import make_response

def _require_internal_secret(req) -> Optional[Response]:
    """Valida el secreto interno para APIs internas.

    Devuelve None si está permitido continuar; de lo contrario, un Response 403.
    Si no hay secreto configurado, no bloquea (retorna None).
    """
    # Obtener secreto configurado
    try:
        sec = os.getenv('INTERNAL_API_SECRET') or getattr(config.settings, 'INTERNAL_API_SECRET', None)
    except Exception:
        sec = os.getenv('INTERNAL_API_SECRET')

    # Extraer secreto proporcionado en headers, query o body
    provided = None
    try:
        provided = req.headers.get('X-Internal-Secret') or req.args.get('secret')
        if not provided and getattr(req, 'is_json', False):
            body = req.get_json(silent=True) or {}
            if isinstance(body, dict):
                provided = body.get('secret')
    except Exception:
        provided = None

    # Si no hay secreto configurado, permitir (modo laxo)
    if not sec:
        return None
    # Validar coincidencia
    if provided and str(provided) == str(sec):
        return None
    return make_response(jsonify({'error': 'Forbidden'}), 403)

@app.route('/api/ctrader/orders/queue', methods=['POST'])
def api_ctrader_orders_queue():
    """Encola una orden para ejecución en cTrader.

    Seguridad: requiere token de usuario válido y/o secreto interno.

    Body JSON: {
      symbol, side (BUY/SELL), type (MARKET/LIMIT), quantity, price?, sl?, tp?, client_order_id?, account_id?
    }
    """
    token = request.args.get('token') or (request.json.get('token') if request.is_json else None)
    if token and not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    secret_check = _require_internal_secret(request)
    if isinstance(secret_check, Response):
        return secret_check
    try:
        data = request.get_json(force=True) if request.is_json else {}
        required = ['symbol', 'side', 'type', 'quantity']
        for k in required:
            if data.get(k) is None:
                return jsonify({'error': f'Falta campo requerido: {k}'}), 400
        order = {
            'id': data.get('client_order_id') or f"srv_{int(datetime.now().timestamp()*1000)}",
            'account_id': data.get('account_id') or getattr(config.settings, 'CTRADER_ACCOUNT_ID', None),
            'symbol': str(data['symbol']).upper(),
            'side': str(data['side']).upper(),
            'type': str(data['type']).upper(),
            'quantity': float(data['quantity']),
            'price': (float(data['price']) if data.get('price') is not None else None),
            'sl': (float(data['sl']) if data.get('sl') is not None else None),
            'tp': (float(data['tp']) if data.get('tp') is not None else None),
            'ts': datetime.now().isoformat(),
            'status': 'QUEUED'
        }
        # Cargar cola actual
        q = _read_json_file(CTRADER_ORDERS_QUEUE_FILE, default=[])
        if not isinstance(q, list):
            q = []
        q.append(order)
        ok = _write_json_file(CTRADER_ORDERS_QUEUE_FILE, q)
        if ok:
            _append_jsonl_file(os.path.join('logs', 'ctrader_orders_queue.jsonl'), order)
        return jsonify({'success': bool(ok), 'order': order})
    except Exception as e:
        logger.error(f"Error en orders_queue: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ctrader/orders/pull', methods=['POST', 'GET'])
def api_ctrader_orders_pull():
    """Consumido por el cBot: obtiene y limpia la cola de órdenes pendientes.
    Seguridad: usar secreto interno o token admin.
    """
    # Permitir con secreto o token admin
    secret_check = _require_internal_secret(request)
    if isinstance(secret_check, Response):
        # Si hay token admin, también vale
        token = request.args.get('token') or (request.json.get('token') if request.is_json else None)
        if not token or not auth_manager.is_admin(token):
            return secret_check
    try:
        q = _read_json_file(CTRADER_ORDERS_QUEUE_FILE, default=[])
        if not isinstance(q, list):
            q = []
        # Vaciar cola
        _write_json_file(CTRADER_ORDERS_QUEUE_FILE, [])
        return jsonify({'success': True, 'orders': q, 'count': len(q)})
    except Exception as e:
        logger.error(f"Error en orders_pull: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ctrader/orders/ack', methods=['POST'])
def api_ctrader_orders_ack():
    """El cBot confirma resultado de ejecución de una orden.
    Body: { id, status, executed_price?, executed_qty?, error? }
    Seguridad: secreto interno o token admin.
    """
    secret_check = _require_internal_secret(request)
    if isinstance(secret_check, Response):
        token = request.args.get('token') or (request.json.get('token') if request.is_json else None)
        if not token or not auth_manager.is_admin(token):
            return secret_check
    try:
        data = request.get_json(force=True) if request.is_json else {}
        oid = data.get('id')
        status = data.get('status')
        if not oid or not status:
            return jsonify({'error': 'id y status son requeridos'}), 400
        result = {
            'id': oid,
            'status': status,
            'executed_price': (float(data['executed_price']) if data.get('executed_price') is not None else None),
            'executed_qty': (float(data['executed_qty']) if data.get('executed_qty') is not None else None),
            'error': data.get('error'),
            'ts': datetime.now().isoformat()
        }
        # Persistir en resultados (lista)
        arr = _read_json_file(CTRADER_ORDERS_RESULTS_FILE, default=[])
        if not isinstance(arr, list):
            arr = []
        arr.append(result)
        ok = _write_json_file(CTRADER_ORDERS_RESULTS_FILE, arr)
        if ok:
            _append_jsonl_file(os.path.join('logs', 'ctrader_orders_results.jsonl'), result)
        return jsonify({'success': bool(ok), 'result': result})
    except Exception as e:
        logger.error(f"Error en orders_ack: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ctrader/orders/results/last')
def api_ctrader_orders_results_last():
    """Devuelve el último resultado de ack (para dashboard). Requiere token válido."""
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        arr = _read_json_file(CTRADER_ORDERS_RESULTS_FILE, default=[])
        if isinstance(arr, list) and arr:
            return jsonify({'success': True, 'result': arr[-1]})
        return jsonify({'success': True, 'result': None})
    except Exception as e:
        logger.error(f"Error leyendo último ack: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/balance')
def api_balance():
    """API: Balance de la cuenta de Binance (real)"""
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        # Intento asíncrono principal
        import asyncio
        from utils.binance_client import get_binance_client

        async def fetch_balances():
            client = await get_binance_client()
            account_info = await client.get_account()
            prices = await client.get_all_tickers()
            price_map = {p["symbol"]: float(p["price"]) for p in prices}

            balances: dict[str, dict] = {}
            total_usdt = 0.0
            threshold = 1e-6
            for b in account_info.get('balances', []):
                asset = b.get('asset')
                free = float(b.get('free', 0))
                locked = float(b.get('locked', 0))
                total = free + locked
                if total <= threshold:
                    continue
                balances[asset] = {'free': free, 'locked': locked, 'total': total}
                if asset == 'USDT':
                    total_usdt += total
                else:
                    symbol = f"{asset}USDT"
                    price = price_map.get(symbol)
                    if price:
                        total_usdt += total * price
            return balances, total_usdt

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            balances, total_usdt = loop.run_until_complete(fetch_balances())
        except Exception as e_async:
            # Fallback a cliente síncrono para evitar problemas de loop
            logger.warning(f"Fallo balance asíncrono, usando cliente síncrono: {e_async}")
            try:
                from binance.client import Client as SyncClient
                from config import settings as cfg
                cli = SyncClient(api_key=cfg.BINANCE_API_KEY, api_secret=cfg.BINANCE_SECRET_KEY)
                account_info = cli.get_account()
                prices = {p['symbol']: float(p['price']) for p in cli.get_all_tickers()}
                balances = {}
                total_usdt = 0.0
                threshold = 1e-6
                for b in account_info.get('balances', []):
                    asset = b.get('asset')
                    free = float(b.get('free', 0))
                    locked = float(b.get('locked', 0))
                    total = free + locked
                    if total <= threshold:
                        continue
                    balances[asset] = {'free': free, 'locked': locked, 'total': total}
                    if asset == 'USDT':
                        total_usdt += total
                    else:
                        sym = f"{asset}USDT"
                        price = prices.get(sym)
                        if price:
                            total_usdt += total * price
            except Exception as e_sync:
                logger.error(f"Error en fallback de balance síncrono: {e_sync}")
                return jsonify({'success': False, 'error': str(e_sync), 'balances': {}, 'total_usdt_equivalent': 0.0})

        resp = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'balances': balances,
            'total_usdt_equivalent': round(total_usdt, 2),
            'main_assets': {
                'USDT': balances.get('USDT', {}).get('total', 0.0),
                'BTC': balances.get('BTC', {}).get('total', 0.0),
                'BNB': balances.get('BNB', {}).get('total', 0.0)
            }
        }
        return jsonify(resp)
    except Exception as e:
        logger.error(f"Error en API balance: {e}")
        return jsonify({'success': False, 'error': str(e), 'balances': {}, 'total_usdt_equivalent': 0.0})

@app.route('/api/uptime')
def api_uptime():
    """API: Tiempo de operación ACUMULADO en modo LIVE (persistente)."""
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        # Estado actual del bot
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        current_mode = loop.run_until_complete(logic_stubs.get_bot_mode())
        now = datetime.now()

        state = _load_live_uptime_state()
        changed = False

        # Si estamos en LIVE, asegurar last_live_start y acumular en tiempo real
        if str(current_mode).upper() == 'LIVE':
            if not state.get('last_live_start'):
                state['last_live_start'] = now.isoformat()
                changed = True
                if not state.get('first_live_start'):
                    state['first_live_start'] = state['last_live_start']
            # Segundos acumulados incluyendo sesión actual
            last_start = datetime.fromisoformat(state['last_live_start'])
            reported_seconds = int(state.get('total_live_seconds', 0) + (now - last_start).total_seconds())
        else:
            # Si veníamos de LIVE, consolidar y limpiar last_live_start
            if state.get('last_live_start'):
                try:
                    last_start = datetime.fromisoformat(state['last_live_start'])
                    state['total_live_seconds'] = int(state.get('total_live_seconds', 0) + (now - last_start).total_seconds())
                except Exception:
                    pass
                state['last_live_start'] = None
                changed = True
            reported_seconds = int(state.get('total_live_seconds', 0))

        if changed:
            _save_live_uptime_state(state)

        return jsonify({
            'success': True,
            'uptime_seconds': reported_seconds,
            'uptime_formatted': _format_duration(reported_seconds),
            'start_time': state.get('first_live_start'),
            'start_time_current_session': state.get('last_live_start'),
            'live_mode': str(current_mode).upper() == 'LIVE',
            'timestamp': now.isoformat()
        })
    except Exception as e:
        logger.error(f"Error en API uptime: {e}")
        return jsonify({'success': False, 'error': str(e), 'uptime_seconds': 0, 'uptime_formatted': '0h 0m'})

@app.route('/api/pairs')
def api_pairs():
    """API: Información de pares dinámicos"""
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        pairs_data = loop.run_until_complete(get_pairs_data())
        
        return jsonify({
            'success': True,
            'data': pairs_data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting pairs data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance')
def api_performance():
    """API: Datos de rendimiento"""
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        performance_data = loop.run_until_complete(get_performance_data())
        
        return jsonify({
            'success': True,
            'data': performance_data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting performance data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/equity')
def api_equity():
    """API: Serie de equity histórica (normalizada base 100). Intenta leer de logs o genera mock si no disponible."""
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        # Intentar cargar de un archivo CSV estándar si existe
        eq = []
        ts = []
        possible_files = [
            os.path.join('logs', 'equity_history.csv'),
            os.path.join('data', 'equity_history.csv'),
        ]
        loaded = False
        for fp in possible_files:
            if os.path.exists(fp):
                df = pd.read_csv(fp)
                # Se espera columnas: timestamp, equity (USDT)
                if 'timestamp' in df.columns and 'equity' in df.columns and len(df) > 1:
                    base = df['equity'].iloc[0] if df['equity'].iloc[0] != 0 else 1.0
                    eq = (df['equity'] / base * 100.0).round(4).tolist()
                    ts = df['timestamp'].astype(str).tolist()
                    loaded = True
                    break
        if not loaded:
            # Generar serie mock suave si no existe archivo
            n = 120
            np.random.seed(7)
            steps = np.random.normal(loc=0.02, scale=0.3, size=n)
            curve = 100 + np.cumsum(steps)
            eq = curve.round(4).tolist()
            ts = [(datetime.now() - timedelta(minutes=(n-i))).strftime('%H:%M:%S') for i in range(n)]
        return jsonify({'success': True, 'equity': eq, 'labels': ts})
    except Exception as e:
        logger.error(f"Error en api_equity: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/equity/rebuild', methods=['POST'])
def api_equity_rebuild():
    """API: Recalcula y guarda logs/equity_history.csv leyendo operaciones cerradas de la DB."""
    token = request.args.get('token') or (request.json.get('token') if request.is_json else None)
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        # Parámetros opcionales
        payload = request.get_json(force=True) if request.is_json else {}
        initial_balance = float(payload.get('initial_balance', os.getenv('EQUITY_INITIAL_BALANCE', '10000')))

        df = compute_equity_df(initial_balance)
        out_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, 'equity_history.csv')
        df.to_csv(out_path, index=False)
        return jsonify({'success': True, 'rows': int(len(df)), 'path': out_path})
    except Exception as e:
        logger.error(f"Error en api_equity_rebuild: {e}")
        return jsonify({'error': str(e)}), 500

# ------------------ SYSTEM/QUICK ACTIONS ------------------

@app.route('/api/system/toggle_mode', methods=['POST'])
def api_system_toggle_mode():
    token = request.args.get('token') or (request.json.get('token') if request.is_json else None)
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        current_mode = loop.run_until_complete(logic_stubs.get_bot_mode())
        now = datetime.now()
        state = _load_live_uptime_state()
        if str(current_mode).upper() == 'LIVE':
            # Vamos a salir de LIVE: consolidar tiempo
            loop.run_until_complete(logic_stubs.set_bot_mode('PAPER_TRADING'))
            new_mode = 'PAPER_TRADING'
            if state.get('last_live_start'):
                try:
                    last_start = datetime.fromisoformat(state['last_live_start'])
                    state['total_live_seconds'] = int(state.get('total_live_seconds', 0) + (now - last_start).total_seconds())
                except Exception:
                    pass
                state['last_live_start'] = None
                _save_live_uptime_state(state)
        else:
            # Vamos a LIVE: marcar inicio
            loop.run_until_complete(logic_stubs.set_bot_mode('LIVE'))
            new_mode = 'LIVE'
            if not state.get('last_live_start'):
                state['last_live_start'] = now.isoformat()
                if not state.get('first_live_start'):
                    state['first_live_start'] = state['last_live_start']
                _save_live_uptime_state(state)
        return jsonify({'success': True, 'previous_mode': current_mode, 'new_mode': new_mode})
    except Exception as e:
        logger.error(f"Error toggling mode: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/tail')
def api_logs_tail():
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        # Buscar archivo de log más reciente en ./logs
        log_dir = os.path.join(os.getcwd(), 'logs')
        patterns = ['*.log', '*.txt']
        files = []
        for p in patterns:
            files.extend(glob.glob(os.path.join(log_dir, p)))
        target = None
        if files:
            files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
            target = files[0]
        # Fallback a equity_history.csv si no hay logs
        if not target and os.path.exists(os.path.join(log_dir, 'equity_history.csv')):
            target = os.path.join(log_dir, 'equity_history.csv')
        if not target:
            return Response('No hay logs disponibles.', mimetype='text/plain')
        # Leer últimas N líneas (por defecto 300)
        download_flag = request.args.get('download') in ('1','true','True','yes')
        n = int(request.args.get('lines', '300'))
        with open(target, 'rb') as f:
            try:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                block = 1024
                data = b''
                while size > 0 and data.count(b'\n') <= n:
                    step = block if size - block > 0 else size
                    f.seek(-step, os.SEEK_CUR)
                    data = f.read(step) + data
                    f.seek(-step, os.SEEK_CUR)
                    size -= step
                content = data.splitlines()[-n:]
                text = b"\n".join(content).decode('utf-8', errors='replace')
            except Exception:
                f.seek(0)
                text = f.read().decode('utf-8', errors='replace')
        resp = Response(text, mimetype='text/plain')
        if download_flag:
            # Nombre de archivo con timestamp
            fname = f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            resp.headers['Content-Disposition'] = f'attachment; filename="{fname}"'
        return resp
    except Exception as e:
        logger.error(f"Error leyendo logs: {e}")
        return Response(f'Error leyendo logs: {e}', mimetype='text/plain', status=500)

@app.route('/api/export/equity')
def api_export_equity():
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        candidates = [
            os.path.join('logs', 'equity_history.csv'),
            os.path.join('data', 'equity_history.csv'),
        ]
        for fp in candidates:
            if os.path.exists(fp):
                return send_file(fp, as_attachment=True)

        # Si no existe, intentamos reconstruir rápidamente y servir
        try:
            initial_balance = float(os.getenv('EQUITY_INITIAL_BALANCE', '10000'))
            df = compute_equity_df(initial_balance)
            out_dir = os.path.join(os.getcwd(), 'logs')
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, 'equity_history.csv')
            df.to_csv(out_path, index=False)
            if os.path.exists(out_path):
                return send_file(out_path, as_attachment=True)
        except Exception as e:
            logger.warning(f"No se pudo reconstruir equity para exportar: {e}")
        # Si llegamos aquí, no pudimos reconstruir
        return jsonify({'error': 'No se encontró equity_history.csv y no se pudo generar.'}), 404
    except Exception as e:
        logger.error(f"Error exportando equity: {e}")
        return jsonify({'error': str(e)}), 500

# ------------------ cTrader INTEGRATION (READ-ONLY SNAPSHOT) ------------------

@app.route('/api/ctrader/snapshot')
def api_ctrader_snapshot():
    """Devuelve un snapshot ligero para el dashboard/cTrader con fallbacks.

    Query params:
      - token: auth token (requerido)
      - symbol: símbolo base (ej. BTCUSDT). Si falta, usa el primero de pares actuales.
      - limit: cantidad de operaciones recientes (default 20)
    """
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    if get_db_session is None:
        return jsonify({'error': 'DB unavailable'}), 500

    try:
        symbol = (request.args.get('symbol') or '').strip().upper()
        try:
            limit = int(request.args.get('limit', '20'))
        except Exception:
            limit = 20

        # Metadatos para mostrar el origen de cada dato en el dashboard
        data_sources: dict[str, Optional[str]] = {
            'symbol': None,
            'price': None,
            'position': None,
            'regime': None
        }

        # Helper seguro para convertir a float sin romper tipado/ejecución
        def _safe_float(x) -> Optional[float]:
            try:
                return float(x) if x is not None else None
            except Exception:
                return None

        # 1) Régimen desde DB
        regime = {'name': None, 'confidence': None, 'timestamp': None}
        with get_db_session() as s:
            q = _sa_text(
                """
                SELECT market_regime, confidence, timestamp
                FROM market_analysis
                ORDER BY timestamp DESC
                LIMIT 1
                """
            )
            r = s.execute(q).fetchone()
            if r:
                regime = {
                    'name': r[0],
                    'confidence': float(r[1]) if r[1] is not None else None,
                    'timestamp': (r[2].isoformat() if hasattr(r[2], 'isoformat') else str(r[2]))
                }
                data_sources['regime'] = 'DB'

        # 2) Pares actuales y símbolo por defecto
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        dyn = loop.run_until_complete(dynamic_pair_manager.get_status_report())
        system_status = dyn.get('system_status', {}) or {}
        cp = system_status.get('current_pairs', []) or []
        def to_symbol(x: Any) -> Optional[str]:
            if not x:
                return None
            if isinstance(x, str):
                return x
            if isinstance(x, dict):
                return x.get('symbol') or x.get('pair') or x.get('name')
            return None
        current_pairs = [s for s in (to_symbol(x) for x in cp) if s]
        if not symbol:
            symbol = (current_pairs[0] if current_pairs else 'BTCUSDT')
            data_sources['symbol'] = 'CURRENT_PAIRS'
        else:
            data_sources['symbol'] = 'PARAM'

        # 3) Posición abierta y trades recientes
        open_position = None
        recent_trades: list[dict] = []
        current_price: Optional[float] = None
        ctrader_positions: list[dict] = []
        with get_db_session() as s:
            q_open = _sa_text(
                """
                SELECT operation_id, timestamp, side, price, quantity, decision
                FROM operations
                WHERE symbol = :symbol AND status = 'OPEN'
                ORDER BY timestamp DESC
                LIMIT 1
                """
            )
            ro = s.execute(q_open, {'symbol': symbol}).fetchone()
            if ro:
                open_position = {
                    'operation_id': ro[0],
                    'timestamp': (ro[1].isoformat() if hasattr(ro[1], 'isoformat') else str(ro[1])),
                    'side': ro[2],
                    'price': float(ro[3]),
                    'quantity': float(ro[4]),
                    'decision': ro[5]
                }
                data_sources['position'] = 'DB'
            q_hist = _sa_text(
                """
                SELECT operation_id, timestamp, side, price, quantity, status, decision, close_price, close_timestamp, close_reason
                FROM operations
                WHERE symbol = :symbol
                ORDER BY timestamp DESC
                LIMIT :limit
                """
            )
            rh = s.execute(q_hist, {'symbol': symbol, 'limit': int(limit)}).fetchall()
            for r in rh:
                recent_trades.append({
                    'operation_id': r[0],
                    'timestamp': (r[1].isoformat() if hasattr(r[1], 'isoformat') else str(r[1])),
                    'side': r[2],
                    'price': float(r[3]),
                    'quantity': float(r[4]),
                    'status': r[5],
                    'decision': r[6],
                    'close_price': (float(r[7]) if r[7] is not None else None),
                    'close_timestamp': (r[8].isoformat() if r[8] and hasattr(r[8], 'isoformat') else (str(r[8]) if r[8] else None)),
                    'close_reason': r[9]
                })

        # Posiciones cTrader para fallbacks
        try:
            ctrader_positions = _read_json_file(CTRADER_POSITIONS_FILE, default=[])
            if not isinstance(ctrader_positions, list):
                ctrader_positions = []
        except Exception:
            ctrader_positions = []

        # 3.1) Precio actual desde cTrader
        if ctrader_positions:
            try:
                cand = None
                for p in ctrader_positions:
                    psym = (p.get('symbol') or p.get('Symbol') or p.get('pair') or '').upper()
                    if psym == symbol:
                        cand = p
                        break
                if cand:
                    for k in ('current_price','currentPrice','lastPrice','mark_price','markPrice','price'):
                        if cand.get(k) is not None:
                            val = _safe_float(cand.get(k))
                            if val is not None:
                                current_price = val
                                data_sources['price'] = 'CTRADER_POSITIONS'
                                break
            except Exception:
                pass

        # 3.1.b) Precio actual vía Binance si falta
        if current_price is None:
            try:
                from utils.binance_client import get_binance_client
                client = loop.run_until_complete(asyncio.wait_for(get_binance_client(), timeout=2.5))
                try:
                    tkr = loop.run_until_complete(asyncio.wait_for(client.get_ticker(symbol=symbol), timeout=2.5))
                    if isinstance(tkr, dict):
                        p = tkr.get('lastPrice') or tkr.get('price') or tkr.get('last')
                        val = _safe_float(p)
                        if val is not None:
                            current_price = val
                            data_sources['price'] = 'BINANCE_TICKER'
                except Exception:
                    try:
                        arr = loop.run_until_complete(asyncio.wait_for(client.get_all_tickers(), timeout=2.5))
                        if isinstance(arr, list):
                            for item in arr:
                                if item.get('symbol') == symbol:
                                    try:
                                        valp = item.get('price')
                                        valf = _safe_float(valp)
                                        if valf is not None:
                                            current_price = valf
                                            data_sources['price'] = 'BINANCE_TICKERS'
                                    except Exception:
                                        pass
                                    break
                    except Exception:
                        current_price = None
            except Exception:
                current_price = None

        # 3.2) PnL estimado para posición abierta
        if open_position and current_price is not None:
            try:
                entry = float(open_position['price'])
                qty = float(open_position['quantity'])
                side = str(open_position['side']).upper()
                pnl = ((current_price - entry) * qty) if side == 'BUY' else ((entry - current_price) * qty)
                open_position['pnl_estimated'] = float(pnl)
            except Exception:
                pass

        # 3.2.b) Fallback de posición desde cTrader
        if open_position is None and ctrader_positions:
            try:
                cand = None
                for p in ctrader_positions:
                    psym = (p.get('symbol') or p.get('Symbol') or p.get('pair') or '').upper()
                    if psym:
                        if psym == symbol:
                            cand = p
                            break
                        if not cand:
                            cand = p
                if cand:
                    psym = (cand.get('symbol') or cand.get('Symbol') or cand.get('pair') or '').upper()
                    if psym:
                        symbol = psym
                        data_sources['symbol'] = 'CTRADER'
                    side = (cand.get('side') or cand.get('Side') or cand.get('direction') or '').upper()
                    qty = _safe_float(cand.get('size') or cand.get('volume') or cand.get('qty')) or 0.0
                    entry = _safe_float(cand.get('entry_price') or cand.get('entryPrice') or cand.get('price')) or 0.0
                    ts = cand.get('timestamp') or cand.get('open_time') or cand.get('openTime') or None
                    if current_price is None:
                        for k in ('current_price','currentPrice','lastPrice','mark_price','markPrice','price'):
                            if cand.get(k) is not None:
                                val = _safe_float(cand.get(k))
                                if val is not None:
                                    current_price = val
                                    if not data_sources['price']:
                                        data_sources['price'] = 'CTRADER_POSITIONS'
                                    break
                    open_position = {
                        'operation_id': cand.get('id') or cand.get('position_id') or cand.get('ticket'),
                        'timestamp': (ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)) if ts else None,
                        'side': side,
                        'price': entry,
                        'quantity': qty,
                        'decision': cand.get('source') or 'CTRADER'
                    }
                    if not data_sources['position']:
                        data_sources['position'] = 'CTRADER'
                    pnlv = cand.get('pnl_usd') or cand.get('pnl') or cand.get('unrealizedPnL')
                    try:
                        if pnlv is not None:
                            open_position['pnl_estimated'] = float(pnlv)
                        elif current_price is not None and entry and qty:
                            pnl = ((current_price - entry) * qty) if side == 'BUY' else ((entry - current_price) * qty)
                            open_position['pnl_estimated'] = float(pnl)
                    except Exception:
                        pass
            except Exception:
                pass

        # 3.3) Fallback con último ACK
        try:
            _orders_results = _read_json_file(CTRADER_ORDERS_RESULTS_FILE, default=[])
            if isinstance(_orders_results, list) and _orders_results:
                last_res = _orders_results[-1]
                try:
                    if not symbol:
                        sym_last = last_res.get('symbol') or last_res.get('pair')
                        if sym_last:
                            symbol = str(sym_last).upper()
                            if not data_sources['symbol']:
                                data_sources['symbol'] = 'ACK'
                except Exception:
                    pass
                try:
                    if last_res.get('executed_price') is not None and (current_price is None):
                        current_price = float(last_res.get('executed_price'))
                        if not data_sources['price']:
                            data_sources['price'] = 'ACK'
                except Exception:
                    pass
        except Exception:
            pass

        # 3.4) Forzar desde ACK si aún falta todo
        try:
            if (current_price is None or not symbol):
                _orders_results = _read_json_file(CTRADER_ORDERS_RESULTS_FILE, default=[])
                if isinstance(_orders_results, list) and _orders_results:
                    last_res = _orders_results[-1]
                    if not symbol:
                        sym_last = last_res.get('symbol') or last_res.get('pair') or 'USDCUSDT'
                        symbol = str(sym_last).upper()
                        if not data_sources['symbol']:
                            data_sources['symbol'] = 'ACK'
                    if current_price is None and last_res.get('executed_price') is not None:
                        val = _safe_float(last_res.get('executed_price'))
                        if val is not None:
                            current_price = val
                        if not data_sources['price']:
                            data_sources['price'] = 'ACK'
                    if open_position is None:
                        open_position = {
                            'operation_id': last_res.get('id'),
                            'timestamp': last_res.get('ts'),
                            'side': 'BUY',
                            'price': (_safe_float(last_res.get('executed_price')) or 0.0),
                            'quantity': (_safe_float(last_res.get('executed_qty')) or 0.0),
                            'decision': 'ACK',
                            'pnl_estimated': 0.0
                        }
                        if not data_sources['position']:
                            data_sources['position'] = 'ACK'
        except Exception:
            pass

        # 3.5) Si aún falta precio, adoptar primera posición cTrader
        if current_price is None and ctrader_positions:
            try:
                cand = ctrader_positions[0]
                psym = (cand.get('symbol') or cand.get('Symbol') or cand.get('pair') or '').upper()
                if psym:
                    symbol = psym
                    if not data_sources['symbol']:
                        data_sources['symbol'] = 'CTRADER'
                for k in ('current_price','currentPrice','lastPrice','mark_price','markPrice','price','entry_price','entryPrice'):
                    if cand.get(k) is not None:
                        val = _safe_float(cand.get(k))
                        if val is not None:
                            current_price = val
                            if not data_sources['price']:
                                data_sources['price'] = 'CTRADER_POSITIONS'
                            break
                if open_position is None:
                    side = (cand.get('side') or cand.get('Side') or cand.get('direction') or '').upper()
                    qty = _safe_float(cand.get('size') or cand.get('volume') or cand.get('qty')) or 0.0
                    entry = _safe_float(cand.get('entry_price') or cand.get('entryPrice') or cand.get('price')) or 0.0
                    ts = cand.get('timestamp') or cand.get('open_time') or cand.get('openTime') or None
                    open_position = {
                        'operation_id': cand.get('id') or cand.get('position_id') or cand.get('ticket'),
                        'timestamp': (ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)) if ts else None,
                        'side': side,
                        'price': entry,
                        'quantity': qty,
                        'decision': cand.get('source') or 'CTRADER'
                    }
                    if not data_sources['position']:
                        data_sources['position'] = 'CTRADER'
                    pnlv = cand.get('pnl_usd') or cand.get('pnl') or cand.get('unrealizedPnL')
                    try:
                        if pnlv is not None:
                            open_position['pnl_estimated'] = float(pnlv)
                        elif current_price is not None and entry and qty:
                            pnl = ((current_price - entry) * qty) if side == 'BUY' else ((entry - current_price) * qty)
                            open_position['pnl_estimated'] = float(pnl)
                    except Exception:
                        pass
            except Exception:
                pass

        # 4) Resumen de estrategias activas
        active_strategies = 0
        try:
            with get_db_session() as s:
                q2 = _sa_text("SELECT active_strategies FROM market_analysis ORDER BY timestamp DESC LIMIT 1")
                r2 = s.execute(q2).fetchone()
                if r2 and r2[0]:
                    import json as _json
                    val = r2[0]
                    try:
                        parsed = _json.loads(val) if isinstance(val, str) else val
                        if isinstance(parsed, list):
                            active_strategies = len(parsed)
                        elif isinstance(parsed, dict):
                            active_strategies = len(parsed.keys())
                    except Exception:
                        pass
        except Exception:
            pass

        regime_name = regime.get('name') if isinstance(regime, dict) else regime
        if not regime_name:
            regime_name = system_status.get('market_regime') or system_status.get('regime') or '--'
            if not data_sources['regime']:
                data_sources['regime'] = 'SYSTEM_STATUS' if regime_name and regime_name != '--' else 'FALLBACK'

        orders_queue_count = 0
        try:
            _q = _read_json_file(CTRADER_ORDERS_QUEUE_FILE, default=[])
            if isinstance(_q, list):
                orders_queue_count = len(_q)
        except Exception:
            orders_queue_count = 0

        logger.warning(
            "snapshot: symbol=%s price=%s regime=%s open_op=%s qcount=%s ctrader_pos=%s",
            symbol,
            (None if current_price is None else round(float(current_price), 6)),
            regime_name,
            (open_position or {}).get('operation_id') if isinstance(open_position, dict) else None,
            orders_queue_count,
            (len(ctrader_positions) if isinstance(ctrader_positions, list) else 'n/a')
        )
        return jsonify({
            'success': True,
            'server_time': datetime.now().isoformat(),
            'symbol': symbol,
            'current_pairs': current_pairs,
            'regime': regime_name,
            'regime_details': regime,
            'active_strategies_count': active_strategies,
            'open_position': open_position,
            'current_price': current_price,
            'recent_trades': recent_trades,
            'orders_queue_count': orders_queue_count,
            'data_sources': data_sources
        })
    except Exception as e:
        logger.error(f"Error en api_ctrader_snapshot: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/backtest/csv_files')
def api_backtest_csv_files():
    """API para listar archivos CSV disponibles para backtesting"""
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        csv_files = []
        
        # Buscar archivos CSV en data/analisis/
        data_dir = 'data/analisis'
        if os.path.exists(data_dir):
            for filename in sorted(os.listdir(data_dir)):
                if filename.endswith('.csv'):
                    file_path = os.path.join(data_dir, filename)
                    try:
                        # Obtener información del archivo
                        stat = os.stat(file_path)
                        size_mb = stat.st_size / (1024 * 1024)
                        modified = datetime.fromtimestamp(stat.st_mtime)
                        
                        # Verificar si tiene columna timestamp leyendo las primeras líneas
                        has_timestamp = False
                        try:
                            with open(file_path, 'r') as f:
                                header = f.readline().strip().lower()
                                if 'timestamp' in header or 'time' in header or 'date' in header:
                                    has_timestamp = True
                        except:
                            pass
                        
                        csv_files.append({
                            'filename': filename,
                            'path': file_path,
                            'size_mb': round(size_mb, 2),
                            'modified': modified.isoformat(),
                            'has_timestamp': has_timestamp
                        })
                    except Exception as e:
                        logger.warning(f"Error procesando archivo {filename}: {e}")
        
        return jsonify({
            'success': True,
            'csv_files': csv_files,
            'count': len(csv_files)
        })
        
    except Exception as e:
        logger.error(f"Error listando archivos CSV: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'csv_files': []
        })

# --- Admin helpers ---
def require_admin(token: str):
    if not auth_manager.is_admin(token):
        return jsonify({'error': 'Admin requerido'}), 403
    return None

# Acciones de sistema: Pausa/Reanudar
@app.route('/api/system/pause', methods=['POST'])
def api_system_pause():
    token = request.args.get('token') or (request.json.get('token') if request.is_json else None)
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    admin_check = require_admin(token)
    if admin_check is not None:
        return admin_check
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(logic_stubs.full_system_stop())
        return jsonify({'success': True, 'message': 'Sistema pausado'})
    except Exception as e:
        logger.error(f"Error al pausar sistema: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/resume', methods=['POST'])
def api_system_resume():
    token = request.args.get('token') or (request.json.get('token') if request.is_json else None)
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    admin_check = require_admin(token)
    if admin_check is not None:
        return admin_check
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(logic_stubs.resume_system())
        return jsonify({'success': True, 'message': 'Sistema reanudado'})
    except Exception as e:
        logger.error(f"Error al reanudar sistema: {e}")
        return jsonify({'error': str(e)}), 500

# ------------------ ML THRESHOLDS (VIEW/CONTROL + AUDITORÍA) ------------------

@app.route('/api/ml/thresholds', methods=['GET'])
def api_ml_thresholds_info():
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        cfg = config.settings
        # Base (runtime)
        base = {
            'high': getattr(cfg, 'ML_THRESHOLD_HIGH', None),
            'medium': getattr(cfg, 'ML_THRESHOLD_MEDIUM', None),
            'low': getattr(cfg, 'ML_THRESHOLD_LOW', None),
        }
        dynamic_enabled = bool(getattr(cfg, 'ML_DYNAMIC_THRESHOLDS', False))
        window_h = int(getattr(cfg, 'ML_DYNAMIC_WINDOW_HOURS', 24))
        bounds = {
            'HIGH_MIN': getattr(cfg, 'ML_DYNAMIC_HIGH_MIN', None),
            'HIGH_MAX': getattr(cfg, 'ML_DYNAMIC_HIGH_MAX', None),
            'MEDIUM_MIN': getattr(cfg, 'ML_DYNAMIC_MEDIUM_MIN', None),
            'MEDIUM_MAX': getattr(cfg, 'ML_DYNAMIC_MEDIUM_MAX', None),
        }
        # Preview dinámico
        dyn = get_dynamic_thresholds(cfg)
        # Stats recientes para contexto
        stats_24h = ml_monitor.get_recent_stats(hours=24)
        return jsonify({'success': True, 'dynamic_enabled': dynamic_enabled, 'window_hours': window_h, 'base': base, 'dynamic_preview': dyn, 'bounds': bounds, 'recent_stats_24h': sanitize_json(stats_24h)})
    except Exception as e:
        logger.error(f"Error en api_ml_thresholds_info: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ml/thresholds/toggle', methods=['POST'])
def api_ml_thresholds_toggle():
    token = request.args.get('token') or (request.json.get('token') if request.is_json else None)
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    admin_check = require_admin(token)
    if admin_check is not None:
        return admin_check
    try:
        data = request.get_json(force=True) if request.is_json else {}
        enabled = bool(data.get('enabled', True))
        prev = bool(getattr(config.settings, 'ML_DYNAMIC_THRESHOLDS', False))
        setattr(config.settings, 'ML_DYNAMIC_THRESHOLDS', enabled)
        _audit_threshold_event('toggle_dynamic_thresholds', {'user_token': token, 'previous': prev, 'new': enabled})
        return jsonify({'success': True, 'dynamic_enabled': enabled})
    except Exception as e:
        logger.error(f"Error activando/desactivando umbrales dinámicos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ml/thresholds/set_base', methods=['POST'])
def api_ml_thresholds_set_base():
    token = request.args.get('token') or (request.json.get('token') if request.is_json else None)
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    admin_check = require_admin(token)
    if admin_check is not None:
        return admin_check
    try:
        data = request.get_json(force=True)
        high = float(data.get('high'))
        med = float(data.get('medium'))
        low = float(data.get('low'))
        if not (0.0 <= low <= med <= high <= 1.0):
            return jsonify({'error': 'Umbrales deben cumplir 0 <= low <= medium <= high <= 1'}), 400
        prev = {
            'high': getattr(config.settings, 'ML_THRESHOLD_HIGH', None),
            'medium': getattr(config.settings, 'ML_THRESHOLD_MEDIUM', None),
            'low': getattr(config.settings, 'ML_THRESHOLD_LOW', None),
        }
        setattr(config.settings, 'ML_THRESHOLD_HIGH', high)
        setattr(config.settings, 'ML_THRESHOLD_MEDIUM', med)
        setattr(config.settings, 'ML_THRESHOLD_LOW', low)
        _audit_threshold_event('set_base_thresholds', {'user_token': token, 'previous': prev, 'new': {'high': high, 'medium': med, 'low': low}})
        return jsonify({'success': True, 'base': {'high': high, 'medium': med, 'low': low}})
    except Exception as e:
        logger.error(f"Error estableciendo umbrales base ML: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ml/thresholds/recompute_preview', methods=['POST'])
def api_ml_thresholds_recompute_preview():
    token = request.args.get('token') or (request.json.get('token') if request.is_json else None)
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        dyn = get_dynamic_thresholds(config.settings)
        _audit_threshold_event('recompute_dynamic_preview', {'user_token': token, 'dynamic_preview': dyn})
        return jsonify({'success': True, 'dynamic_preview': dyn})
    except Exception as e:
        logger.error(f"Error recomputando preview dinámico: {e}")
        return jsonify({'error': str(e)}), 500

# Ver/descargar auditoría de umbrales ML
@app.route('/api/ml/thresholds/audit')
def api_ml_thresholds_audit():
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        # Si piden descarga directa del archivo completo
        download_flag = request.args.get('download') in ('1','true','True','yes')
        if download_flag and os.path.exists(THRESHOLD_AUDIT_FILE):
            # Adjuntar archivo
            fname = f"ml_threshold_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            return send_file(THRESHOLD_AUDIT_FILE, as_attachment=True, download_name=fname)
        # Si no, devolver últimas N líneas como texto
        n = int(request.args.get('lines', '300'))
        if not os.path.exists(THRESHOLD_AUDIT_FILE):
            return Response('No hay auditoría disponible.', mimetype='text/plain')
        with open(THRESHOLD_AUDIT_FILE, 'rb') as f:
            try:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                block = 1024
                data = b''
                while size > 0 and data.count(b'\n') <= n:
                    step = block if size - block > 0 else size
                    f.seek(-step, os.SEEK_CUR)
                    data = f.read(step) + data
                    f.seek(-step, os.SEEK_CUR)
                    size -= step
                content = data.splitlines()[-n:]
                text = b"\n".join(content).decode('utf-8', errors='replace')
            except Exception:
                f.seek(0)
                text = f.read().decode('utf-8', errors='replace')
        return Response(text, mimetype='text/plain')
    except Exception as e:
        logger.error(f"Error leyendo auditoría ML: {e}")
        return Response(f'Error leyendo auditoría: {e}', mimetype='text/plain', status=500)

# ------------------ RISK LIMITS (READ/WRITE + AUDITORÍA) ------------------

@app.route('/api/risk/limits', methods=['GET', 'POST'])
def api_risk_limits():
    token = request.args.get('token') or (request.json.get('token') if request.is_json else None)
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        if request.method == 'GET':
            defaults = {
                'RISK_MAX_PER_SYMBOL_TRADES': getattr(config.settings, 'RISK_MAX_PER_SYMBOL_TRADES', None),
                'RISK_MAX_PER_SYMBOL_EXPOSURE_PCT': getattr(config.settings, 'RISK_MAX_PER_SYMBOL_EXPOSURE_PCT', None),
            }
            effective = risk.get_effective_risk_params()
            return jsonify({'success': True, 'defaults': defaults, 'effective': {
                'RISK_MAX_PER_SYMBOL_TRADES': effective.get('RISK_MAX_PER_SYMBOL_TRADES'),
                'RISK_MAX_PER_SYMBOL_EXPOSURE_PCT': effective.get('RISK_MAX_PER_SYMBOL_EXPOSURE_PCT')
            }})
        # POST (set) requiere admin
        admin_check = require_admin(token)
        if admin_check is not None:
            return admin_check
        data = request.get_json(force=True)
        out: dict[str, Any] = {}
        # Validaciones simples
        if 'RISK_MAX_PER_SYMBOL_TRADES' in data and data['RISK_MAX_PER_SYMBOL_TRADES'] is not None:
            try:
                v = int(data['RISK_MAX_PER_SYMBOL_TRADES'])
                if v < 1:
                    return jsonify({'error': 'RISK_MAX_PER_SYMBOL_TRADES debe ser >= 1'}), 400
                out['RISK_MAX_PER_SYMBOL_TRADES'] = v
            except Exception:
                return jsonify({'error': 'RISK_MAX_PER_SYMBOL_TRADES inválido'}), 400
        if 'RISK_MAX_PER_SYMBOL_EXPOSURE_PCT' in data and data['RISK_MAX_PER_SYMBOL_EXPOSURE_PCT'] is not None:
            try:
                v = float(data['RISK_MAX_PER_SYMBOL_EXPOSURE_PCT'])
                if not (0 < v <= 100):
                    return jsonify({'error': 'RISK_MAX_PER_SYMBOL_EXPOSURE_PCT debe estar en (0, 100]'}), 400
                out['RISK_MAX_PER_SYMBOL_EXPOSURE_PCT'] = v
            except Exception:
                return jsonify({'error': 'RISK_MAX_PER_SYMBOL_EXPOSURE_PCT inválido'}), 400
        if not out:
            return jsonify({'error': 'Sin cambios válidos'}), 400
        risk.set_custom_risk_params(out)
        _audit_risk_event('set_symbol_limits', {'user_token': token, 'applied': out})
        eff = risk.get_effective_risk_params()
        return jsonify({'success': True, 'effective': {
            'RISK_MAX_PER_SYMBOL_TRADES': eff.get('RISK_MAX_PER_SYMBOL_TRADES'),
            'RISK_MAX_PER_SYMBOL_EXPOSURE_PCT': eff.get('RISK_MAX_PER_SYMBOL_EXPOSURE_PCT')
        }})
    except Exception as e:
        logger.error(f"Error en api_risk_limits: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/risk/limits/audit')
def api_risk_limits_audit():
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        download_flag = request.args.get('download') in ('1','true','True','yes')
        if download_flag and os.path.exists(RISK_LIMITS_AUDIT_FILE):
            fname = f"risk_limits_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            return send_file(RISK_LIMITS_AUDIT_FILE, as_attachment=True, download_name=fname)
        n = int(request.args.get('lines', '300'))
        if not os.path.exists(RISK_LIMITS_AUDIT_FILE):
            return Response('No hay auditoría disponible.', mimetype='text/plain')
        with open(RISK_LIMITS_AUDIT_FILE, 'rb') as f:
            try:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                block = 1024
                data = b''
                while size > 0 and data.count(b'\n') <= n:
                    step = block if size - block > 0 else size
                    f.seek(-step, os.SEEK_CUR)
                    data = f.read(step) + data
                    f.seek(-step, os.SEEK_CUR)
                    size -= step
                content = data.splitlines()[-n:]
                text = b"\n".join(content).decode('utf-8', errors='replace')
            except Exception:
                f.seek(0)
                text = f.read().decode('utf-8', errors='replace')
        return Response(text, mimetype='text/plain')
    except Exception as e:
        logger.error(f"Error leyendo auditoría de límites: {e}")
        return Response(f'Error leyendo auditoría: {e}', mimetype='text/plain', status=500)

# ------------------ RISK METRICS (DAILY) ------------------

@app.route('/api/risk/metrics')
def api_risk_metrics():
    token = request.args.get('token')
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        # Intentar obtener métricas actuales del estado; si faltan, recalcular
        from utils.state_manager import StateManager
        sm = StateManager()
        metrics = sm.get_state('risk_metrics') or {}
        if not metrics or 'daily_pnl_percentage' not in metrics:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(risk._get_daily_pnl_pct())
            metrics = sm.get_state('risk_metrics') or {}
        # Pausa por drawdown
        paused_until = sm.get_state('system', 'drawdown_pause_until')
        paused_by_drawdown = False
        if paused_until:
            try:
                from datetime import timezone as _tz
                dt = datetime.fromisoformat(paused_until)
                paused_by_drawdown = datetime.now(_tz.utc) < (dt if dt.tzinfo else dt.replace(tzinfo=_tz.utc))
            except Exception:
                paused_by_drawdown = True
        return jsonify({'success': True, 'metrics': sanitize_json(metrics), 'paused_by_drawdown': paused_by_drawdown, 'pause_until': paused_until})
    except Exception as e:
        logger.error(f"Error en api_risk_metrics: {e}")
        return jsonify({'error': str(e)}), 500

# ------------------ DYNAMIC PAIRS ------------------

@app.route('/api/dynamic/reevaluate', methods=['POST'])
def api_dynamic_reevaluate():
    """Recalcula métricas de pares o fuerza re-evaluación completa.

    Body JSON opcional: { mode: 'quick' | 'full' }
    - quick: recalcula métricas solo de los pares actuales y genera reporte.
    - full (por defecto): fuerza re-evaluación completa y genera reporte.
    """
    token = request.args.get('token') or (request.json.get('token') if request.is_json else None)
    if not token or not auth_manager.validate_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        mode = 'full'
        try:
            if request.is_json:
                mode = str(request.json.get('mode', 'full')).lower()
        except Exception:
            pass
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        if mode == 'quick':
                # Recalcular métricas para los pares actuales y generar el archivo de selección
                dynamic_status = loop.run_until_complete(dynamic_pair_manager.get_status_report())
                system_status = dynamic_status.get('system_status', {}) or {}
                cp = system_status.get('current_pairs', []) or []
                # Normalizar símbolos
                def to_symbol(x: Any) -> Optional[str]:
                    if not x:
                        return None
                    if isinstance(x, str):
                        return x
                    if isinstance(x, dict):
                        return x.get('symbol') or x.get('pair') or x.get('name')
                    return None
                symbols = [s for s in (to_symbol(x) for x in cp) if s]

                selector = dynamic_pair_manager.pair_selector
                tasks = [selector.analyze_pair_performance(s) for s in symbols]
                results = loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                metrics = {}
                for s, r in zip(symbols, results):
                    if isinstance(r, Exception) or r is None:
                        continue
                    if isinstance(r, dict):
                        metrics[s] = r
                # Setear en selector y generar reporte con los pares actuales
                selector.pair_metrics = metrics
                selector.selected_pairs = symbols
                # Intentar generar reporte estándar; si falla, escribir JSON minimalista saneado
                try:
                    selector.generate_selection_report()
                except Exception as e:
                    logger.warning(f"Fallo al generar reporte estándar (quick): {e}; usando volcado alternativo")
                    try:
                        from pathlib import Path
                        out = {
                            "selection_timestamp": datetime.now().isoformat(),
                            "selected_pairs": symbols,
                            "pair_metrics": {s: sanitize_json(m) for s, m in metrics.items()}
                        }
                        out_dir = Path('data') / 'dynamic_pair_analysis'
                        out_dir.mkdir(parents=True, exist_ok=True)
                        with open(out_dir / 'dynamic_pair_selection.json', 'w') as f:
                            json.dump(out, f, indent=2)
                    except Exception as e2:
                        logger.error(f"No se pudo escribir volcado alternativo: {e2}")
                return jsonify({'success': True, 'mode': 'quick', 'evaluated_pairs': len(metrics), 'selected_pairs': symbols})
        else:
                # Re-evaluación completa
                changed, details = loop.run_until_complete(dynamic_pair_manager.force_reevaluation())
                # Generar archivo de selección con los pares actuales y métricas del selector
                try:
                    dynamic_pair_manager.pair_selector.generate_selection_report()
                except Exception as e:
                    logger.warning(f"No se pudo generar reporte tras re-evaluación: {e}; intentando volcado alternativo")
                    try:
                        selector = dynamic_pair_manager.pair_selector
                        metrics = getattr(selector, 'pair_metrics', {}) or {}
                        selected = getattr(selector, 'selected_pairs', []) or []
                        out = {
                            "selection_timestamp": datetime.now().isoformat(),
                            "selected_pairs": selected,
                            "pair_metrics": {s: sanitize_json(m) for s, m in metrics.items()}
                        }
                        from pathlib import Path
                        out_dir = Path('data') / 'dynamic_pair_analysis'
                        out_dir.mkdir(parents=True, exist_ok=True)
                        with open(out_dir / 'dynamic_pair_selection.json', 'w') as f:
                            json.dump(out, f, indent=2)
                    except Exception as e2:
                        logger.error(f"No se pudo escribir volcado alternativo: {e2}")
                return jsonify({'success': True, 'mode': 'full', 'changes_made': bool(changed), 'details': details})
    except Exception as e:
        logger.error(f"Error en re-evaluación dinámica: {e}")
        return jsonify({'error': str(e)}), 500

async def get_bot_status() -> Dict[str, Any]:
    """Obtiene el estado completo del bot"""
    try:
        status = await logic_stubs.get_consolidated_status()
        
        # Agregar información adicional del sistema dinámico
        dynamic_status = await dynamic_pair_manager.get_status_report()

        # Enriquecer los pares actuales con métricas para que el dashboard
        # muestre Score/Volatilidad/Volumen/Tendencia/Última Evaluación
        try:
            system_status = dynamic_status.get('system_status', {}) or {}
            cp = system_status.get('current_pairs', []) or []
            def to_symbol(x: Any) -> Optional[str]:
                if not x:
                    return None
                if isinstance(x, str):
                    return x
                if isinstance(x, dict):
                    return x.get('symbol') or x.get('pair') or x.get('name')
                return None
            symbols = [s for s in (to_symbol(x) for x in cp) if s]

            # Cargar métricas del archivo del selector
            metrics_map: Dict[str, Dict[str, Any]] = {}
            try:
                sel_path = os.path.join('data', 'dynamic_pair_analysis', 'dynamic_pair_selection.json')
                if os.path.exists(sel_path):
                    with open(sel_path, 'r') as f:
                        sel = json.load(f)
                        metrics_map = sel.get('pair_metrics', {}) or {}
            except Exception as e:
                logger.warning(f"No se pudo leer dynamic_pair_selection.json: {e}")

            # Completar métricas que falten (acotado)
            missing = [s for s in symbols if s not in metrics_map]
            if missing:
                try:
                    selector = dynamic_pair_manager.pair_selector
                    tasks = [selector.analyze_pair_performance(s) for s in missing]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for sym, res in zip(missing, results):
                        if isinstance(res, Exception) or res is None:
                            continue
                        if isinstance(res, dict):
                            metrics_map[sym] = res
                except Exception as e:
                    logger.warning(f"Fallo calculando métricas on-demand: {e}")

            # Fallback: calcular volatilidad diaria rápida para símbolos sin volatilidad_annual
            try:
                need_vol = [s for s in symbols if not (metrics_map.get(s) or {}).get('volatility_annual')]
                if need_vol:
                    from utils.binance_client import get_binance_client
                    client = await get_binance_client()
                    import aiohttp as _aiohttp
                    async def fetch_vol(s: str):
                        end_time = datetime.now()
                        start_time = end_time - timedelta(days=30)
                        # 1) Intento con cliente asíncrono centralizado
                        try:
                            kl = await client.get_historical_klines(
                                symbol=s,
                                interval="1d",
                                start_str=int(start_time.timestamp() * 1000),
                                end_str=int(end_time.timestamp() * 1000)
                            )
                        except Exception:
                            kl = None
                        # 2) Fallback REST público si no hay datos suficientes
                        if not kl or len(kl) < 7:
                            try:
                                url = "https://api.binance.com/api/v3/klines"
                                params = {
                                    "symbol": s,
                                    "interval": "1d",
                                    "startTime": int(start_time.timestamp() * 1000),
                                    "endTime": int(end_time.timestamp() * 1000)
                                }
                                async with _aiohttp.ClientSession() as session:
                                    async with session.get(
                                        url,
                                        params=params,
                                        timeout=_aiohttp.ClientTimeout(total=15)
                                    ) as resp:
                                        if resp.status == 200:
                                            kl = await resp.json()
                            except Exception:
                                kl = None
                        # 3) Último recurso: estimar volatilidad diaria desde cambio % 24h del ticker
                        if not kl or len(kl) < 7:
                            # Intentar con cliente asíncrono
                            try:
                                t = await client.get_ticker(symbol=s)
                                pct = None
                                if isinstance(t, dict):
                                    pct = t.get('priceChangePercent') or t.get('priceChange')
                                if pct is not None:
                                    dv_est = abs(float(pct)) / 100.0
                                    return s, dv_est
                            except Exception:
                                pass
                            # Intentar REST público
                            try:
                                url = "https://api.binance.com/api/v3/ticker/24hr"
                                params = {"symbol": s}
                                async with _aiohttp.ClientSession() as session:
                                    async with session.get(
                                        url,
                                        params=params,
                                        timeout=_aiohttp.ClientTimeout(total=10)
                                    ) as resp:
                                        if resp.status == 200:
                                            t = await resp.json()
                                            pct = t.get('priceChangePercent') or t.get('priceChange')
                                            if pct is not None:
                                                dv_est = abs(float(pct)) / 100.0
                                                return s, dv_est
                            except Exception:
                                pass
                            return s, None
                        try:
                            import pandas as _pd
                            closes = _pd.DataFrame(kl, columns=[
                                "timestamp","open","high","low","close","volume",
                                "close_time","quote_asset_volume","number_of_trades",
                                "taker_buy_base_volume","taker_buy_quote_volume","ignore"
                            ])['close'].astype(float)
                            rets = closes.pct_change().dropna()
                            dv = float(rets.std()) if len(rets) else None
                            return s, dv
                        except Exception:
                            return s, None
                    tasks = [fetch_vol(s) for s in need_vol]
                    vols = await asyncio.gather(*tasks, return_exceptions=True)
                    for item in vols:
                        if isinstance(item, tuple):
                            sym, dv = item
                            if sym and dv is not None:
                                metrics_map.setdefault(sym, {})['volatility_annual'] = float(dv) * float(np.sqrt(365))
            except Exception as e:
                logger.warning(f"Fallo en fallback de volatilidad: {e}")

            def map_trend(val: Optional[float]) -> str:
                try:
                    if val is None:
                        return 'FLAT'
                    return 'UP' if float(val) > 0 else ('DOWN' if float(val) < 0 else 'FLAT')
                except Exception:
                    return 'FLAT'

            last_eval = system_status.get('last_evaluation')
            # Índice auxiliar del historial
            history = (dynamic_status.get('history', {}) or {}).get('recent_evaluations', [])
            hist_map: Dict[str, Dict[str, Any]] = {}
            try:
                for ev in history:
                    for item in ev.get('selected_pairs_details', []) or []:
                        sym = item.get('symbol')
                        if sym and sym not in hist_map:
                            hist_map[sym] = item
            except Exception:
                pass

            enriched = []
            for s in symbols:
                m = metrics_map.get(s) or {}
                vol_annual = m.get('volatility_annual')
                volatility = daily_volatility_from_annual(vol_annual)
                # Fallbacks desde historial
                score = m.get('composite_score')
                if score is None and hist_map.get(s):
                    score = hist_map[s].get('score')
                vol24 = m.get('volume_24h_usdt')
                if vol24 is None and hist_map.get(s):
                    vol24 = hist_map[s].get('volume') or hist_map[s].get('volume_24h_usdt')

                enriched.append({
                    'symbol': s,
                    'score': score,
                    'volatility': volatility,
                    'volume_24h': vol24,
                    'trend': map_trend(m.get('trend_slope')),
                    'last_evaluation': last_eval or m.get('timestamp')
                })

            dynamic_status.setdefault('system_status', {})['current_pairs'] = enriched
        except Exception as e:
            logger.warning(f"No se pudieron enriquecer los pares actuales: {e}")
        
        return {
            'bot_status': status,
            'dynamic_system': dynamic_status,
            'system_health': await calculate_system_health(status, dynamic_status)
        }
    except Exception as e:
        logger.error(f"Error getting bot status: {e}")
        return {'error': str(e)}

async def get_pairs_data() -> Dict[str, Any]:
    """Obtiene datos detallados de los pares"""
    try:
        dynamic_status = await dynamic_pair_manager.get_status_report()

        # Extraer lista de símbolos actuales (pueden venir como strings u objetos)
        system_status = dynamic_status.get('system_status', {}) or {}
        cp = system_status.get('current_pairs', []) or []
        def to_symbol(x: Any) -> Optional[str]:
            if not x:
                return None
            if isinstance(x, str):
                return x
            if isinstance(x, dict):
                return x.get('symbol') or x.get('pair') or x.get('name')
            return None
        symbols = [s for s in (to_symbol(x) for x in cp) if s]

        # Intentar cargar métricas desde archivo generado por el selector dinámico
        metrics_map: Dict[str, Dict[str, Any]] = {}
        try:
            sel_path = os.path.join('data', 'dynamic_pair_analysis', 'dynamic_pair_selection.json')
            if os.path.exists(sel_path):
                with open(sel_path, 'r') as f:
                    sel = json.load(f)
                    metrics_map = sel.get('pair_metrics', {}) or {}
        except Exception as e:
            logger.warning(f"No se pudo leer dynamic_pair_selection.json: {e}")

        # Enriquecer: si faltan métricas para algún símbolo, calcular bajo demanda (máx 10)
        missing = [s for s in symbols if s not in metrics_map]
        if missing:
            try:
                # Usamos el selector ya disponible en el gestor para calcular métricas individuales
                selector = dynamic_pair_manager.pair_selector
                # Ejecutar en paralelo, pero acotado (pares suelen ser <=8)
                tasks = [selector.analyze_pair_performance(s) for s in missing]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for sym, res in zip(missing, results):
                    if isinstance(res, Exception) or res is None:
                        continue
                    if isinstance(res, dict):
                        metrics_map[sym] = res
            except Exception as e:
                logger.warning(f"Fallo calculando métricas on-demand: {e}")

        # Fallback: calcular volatilidad diaria rápida para símbolos sin volatilidad_annual
        try:
            need_vol = [s for s in symbols if not (metrics_map.get(s) or {}).get('volatility_annual')]
            if need_vol:
                from utils.binance_client import get_binance_client
                client = await get_binance_client()
                import aiohttp as _aiohttp
                async def fetch_vol(s: str):
                    end_time = datetime.now()
                    start_time = end_time - timedelta(days=30)
                    # 1) Intento con cliente asíncrono centralizado
                    try:
                        kl = await client.get_historical_klines(
                            symbol=s,
                            interval="1d",
                            start_str=int(start_time.timestamp() * 1000),
                            end_str=int(end_time.timestamp() * 1000)
                        )
                    except Exception:
                        kl = None
                    # 2) Fallback REST público si no hay datos suficientes
                    if not kl or len(kl) < 7:
                        try:
                            url = "https://api.binance.com/api/v3/klines"
                            params = {
                                "symbol": s,
                                "interval": "1d",
                                "startTime": int(start_time.timestamp() * 1000),
                                "endTime": int(end_time.timestamp() * 1000)
                            }
                            async with _aiohttp.ClientSession() as session:
                                async with session.get(
                                    url,
                                    params=params,
                                    timeout=_aiohttp.ClientTimeout(total=15)
                                ) as resp:
                                    if resp.status == 200:
                                        kl = await resp.json()
                        except Exception:
                            kl = None
                    # 3) Último recurso: estimar volatilidad diaria desde cambio % 24h del ticker
                    if not kl or len(kl) < 7:
                        # Intentar con cliente asíncrono
                        try:
                            t = await client.get_ticker(symbol=s)
                            pct = None
                            if isinstance(t, dict):
                                pct = t.get('priceChangePercent') or t.get('priceChange')
                            if pct is not None:
                                dv_est = abs(float(pct)) / 100.0
                                return s, dv_est
                        except Exception:
                            pass
                        # Intentar REST público
                        try:
                            url = "https://api.binance.com/api/v3/ticker/24hr"
                            params = {"symbol": s}
                            async with _aiohttp.ClientSession() as session:
                                async with session.get(
                                    url,
                                    params=params,
                                    timeout=_aiohttp.ClientTimeout(total=10)
                                ) as resp:
                                    if resp.status == 200:
                                        t = await resp.json()
                                        pct = t.get('priceChangePercent') or t.get('priceChange')
                                        if pct is not None:
                                            dv_est = abs(float(pct)) / 100.0
                                            return s, dv_est
                        except Exception:
                            pass
                        return s, None
                    try:
                        import pandas as _pd
                        closes = _pd.DataFrame(kl, columns=[
                            "timestamp","open","high","low","close","volume",
                            "close_time","quote_asset_volume","number_of_trades",
                            "taker_buy_base_volume","taker_buy_quote_volume","ignore"
                        ])['close'].astype(float)
                        rets = closes.pct_change().dropna()
                        dv = float(rets.std()) if len(rets) else None
                        return s, dv
                    except Exception:
                        return s, None
                tasks = [fetch_vol(s) for s in need_vol]
                vols = await asyncio.gather(*tasks, return_exceptions=True)
                for item in vols:
                    if isinstance(item, tuple):
                        sym, dv = item
                        if sym and dv is not None:
                            metrics_map.setdefault(sym, {})['volatility_annual'] = float(dv) * float(np.sqrt(365))
        except Exception as e:
            logger.warning(f"Fallo en fallback de volatilidad: {e}")

    # Mapear a la forma esperada por el frontend
        def map_trend(val: Optional[float]) -> str:
            try:
                if val is None:
                    return 'FLAT'
                return 'UP' if float(val) > 0 else ('DOWN' if float(val) < 0 else 'FLAT')
            except Exception:
                return 'FLAT'

        # Construir un índice auxiliar desde el historial por si faltan métricas
        history = (dynamic_status.get('history', {}) or {}).get('recent_evaluations', [])
        hist_map: Dict[str, Dict[str, Any]] = {}
        try:
            for ev in history:
                for item in ev.get('selected_pairs_details', []) or []:
                    sym = item.get('symbol')
                    if sym and sym not in hist_map:
                        hist_map[sym] = item
        except Exception:
            pass

        enriched = []
        last_eval = system_status.get('last_evaluation')
        for s in symbols:
            m = metrics_map.get(s) or {}
            # Volatilidad diaria aproximada desde anualizada
            vol_annual = m.get('volatility_annual')
            volatility = daily_volatility_from_annual(vol_annual)
            # Fallbacks desde historial
            score = m.get('composite_score')
            if score is None and hist_map.get(s):
                score = hist_map[s].get('score')
            vol24 = m.get('volume_24h_usdt')
            if vol24 is None and hist_map.get(s):
                vol24 = hist_map[s].get('volume') or hist_map[s].get('volume_24h_usdt')

            enriched.append({
                'symbol': s,
                'score': score,
                'volatility': volatility,
                'volume_24h': vol24,
                'trend': map_trend(m.get('trend_slope')),
                'last_evaluation': last_eval or m.get('timestamp')
            })

        return {
            'current_pairs': enriched,
            'analysis_results': dynamic_status.get('analysis_results', {}),
            'system_status': system_status
        }
    except Exception as e:
        logger.error(f"Error getting pairs data: {e}")
        return {'error': str(e)}

async def get_performance_data() -> Dict[str, Any]:
    """Obtiene datos de rendimiento detallados"""
    try:
        status = await logic_stubs.get_consolidated_status()
        
        return {
            'daily_pnl': status.get('daily_pnl_percent', 0.0),
            'total_pnl': status.get('total_pnl_percent', 0.0),
            'positions': status.get('positions', []),
            'trades_today': status.get('trades_today', 0),
            'win_rate': status.get('win_rate', 0.0)
        }
    except Exception as e:
        logger.error(f"Error getting performance data: {e}")
        return {'error': str(e)}

async def calculate_system_health(bot_status: Dict, dynamic_status: Dict) -> Dict[str, Any]:
    """Calcula la salud general del sistema"""
    health_score = 0
    max_score = 100
    issues = []
    flags = {}
    
    # Verificar estado del bot (30 puntos)
    if bot_status.get('running', False):
        health_score += 30
    else:
        issues.append("Bot no está ejecutándose")

    # Estado de pausa global (reduce salud, muestra badge)
    if bot_status.get('is_paused', False):
        flags['paused'] = True
        issues.append("Sistema en PAUSA global")
        # Penalizar salud moderadamente por estar pausado
        health_score = max(0, health_score - 15)
    else:
        flags['paused'] = False
    
    # Verificar sistema dinámico (25 puntos)
    dynamic_info = dynamic_status.get('system_status', {})
    if dynamic_info.get('is_initialized', False):
        health_score += 25
    else:
        issues.append("Sistema dinámico no inicializado")
    
    # Verificar pares activos (20 puntos)
    pairs_count = len(dynamic_info.get('current_pairs', []))
    if pairs_count >= 5:
        health_score += 20
    elif pairs_count >= 3:
        health_score += 15
        issues.append(f"Pocos pares activos ({pairs_count})")
    else:
        issues.append(f"Muy pocos pares activos ({pairs_count})")
    
    # Verificar escudos (15 puntos)
    shields = bot_status.get('shield_status', {})
    if any(shields.values()):
        health_score += 10
        issues.append("Escudos activados (precaución)")
    else:
        health_score += 15
    
    # Verificar posiciones (10 puntos)
    positions = len(bot_status.get('positions', []))
    if positions <= 5:  # No sobreapalancado
        health_score += 10
    else:
        issues.append(f"Muchas posiciones abiertas ({positions})")
    
    # Determinar estado general
    if health_score >= 90:
        status = "EXCELENTE"
        color = "success"
    elif health_score >= 70:
        status = "BUENO"
        color = "warning"
    elif health_score >= 50:
        status = "REGULAR"
        color = "warning"
    else:
        status = "CRÍTICO"
        color = "danger"
    
    return {
        'score': health_score,
        'max_score': max_score,
        'percentage': (health_score / max_score) * 100,
        'status': status,
        'color': color,
        'issues': issues,
        'flags': flags
    }

    

@socketio.on('connect')
def handle_connect():
    """Cliente conectado vía WebSocket"""
    print("Client connected")
    
    # Enviar estado inicial
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        initial_data = loop.run_until_complete(get_bot_status())
        emit('status_update', initial_data)
    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('disconnect')
def handle_disconnect():
    """Cliente desconectado"""
    print("Client disconnected")

def run_web_app():
    """Ejecuta la aplicación web"""
    host = os.getenv('WEB_HOST', '0.0.0.0')
    port = int(os.getenv('WEB_PORT', 8080))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🌐 Starting ITBOT Web Panel on {host}:{port}")
    
    # Limpiar sesiones expiradas
    auth_manager.cleanup_expired_sessions()
    
    # Configurar para producción con allow_unsafe_werkzeug
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    run_web_app()
