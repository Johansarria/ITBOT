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

# Agregar el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
        allowed = {'RISK_PER_TRADE_STOP_LOSS_PCT','RISK_PER_TRADE_TAKE_PROFIT_PCT','RISK_MAX_CONCURRENT_TRADES','RISK_MAX_EXPOSURE_PCT','RISK_MAX_DAILY_DRAWDOWN_PCT','DEFAULT_RISK_PERCENTAGE'}
        clean = {k: data[k] for k in data.keys() if k in allowed}
        if not clean:
            return jsonify({'error': 'Sin parámetros válidos'}), 400
        risk.set_custom_risk_params(clean)
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
