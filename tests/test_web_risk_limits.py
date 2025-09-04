import os
import io
import json
import pytest
from unittest.mock import AsyncMock


@pytest.fixture()
def flask_app_client(monkeypatch, tmp_path):
    # Importar la app y preparar entorno controlado
    from web import app as web_app
    # Forzar ADMIN id conocido y archivo de auditoría en tmp
    monkeypatch.setattr(web_app.config.settings, 'ADMIN_TELEGRAM_ID', '999', raising=False)
    audit_path = tmp_path / 'risk_limits_audit.jsonl'
    monkeypatch.setattr(web_app, 'RISK_LIMITS_AUDIT_FILE', str(audit_path), raising=False)
    # Evitar side-effects de uptime en disco durante tests
    monkeypatch.setattr(web_app, 'LIVE_UPTIME_FILE', str(tmp_path / 'live_uptime.json'), raising=False)
    client = web_app.app.test_client()
    return web_app, client


def _get_admin_token(web_app, client):
    # user_id coincide con ADMIN_TELEGRAM_ID para privilegios admin
    resp = client.get('/api/generate_token?user_id=999')
    data = resp.get_json()
    assert data and data.get('success')
    return data['token']


def test_risk_limits_requires_token(flask_app_client):
    web_app, client = flask_app_client
    # Sin token debe 401
    r = client.get('/api/risk/limits')
    assert r.status_code == 401


def test_risk_limits_get_and_post_with_admin(flask_app_client):
    web_app, client = flask_app_client
    token = _get_admin_token(web_app, client)

    # GET debe responder con defaults/effective
    r = client.get(f'/api/risk/limits?token={token}')
    j = r.get_json()
    assert j and j.get('success')
    assert 'defaults' in j and 'effective' in j

    # POST setea límites válidos
    body = {
        'token': token,
        'RISK_MAX_PER_SYMBOL_TRADES': 2,
        'RISK_MAX_PER_SYMBOL_EXPOSURE_PCT': 25.0,
    }
    r2 = client.post('/api/risk/limits', data=json.dumps(body), content_type='application/json')
    j2 = r2.get_json()
    assert j2 and j2.get('success')
    eff = j2.get('effective') or {}
    assert eff.get('RISK_MAX_PER_SYMBOL_TRADES') == 2
    assert eff.get('RISK_MAX_PER_SYMBOL_EXPOSURE_PCT') == 25.0

    # GET nuevamente refleja los valores efectivos
    r3 = client.get(f'/api/risk/limits?token={token}')
    j3 = r3.get_json()
    assert j3 and j3.get('success')
    eff2 = j3.get('effective') or {}
    assert eff2.get('RISK_MAX_PER_SYMBOL_TRADES') == 2
    assert eff2.get('RISK_MAX_PER_SYMBOL_EXPOSURE_PCT') == 25.0


def test_risk_limits_audit_after_post(flask_app_client):
    web_app, client = flask_app_client
    token = _get_admin_token(web_app, client)

    # Asegurar POST para generar entrada de auditoría
    body = {'token': token, 'RISK_MAX_PER_SYMBOL_TRADES': 3}
    r = client.post('/api/risk/limits', data=json.dumps(body), content_type='application/json')
    assert r.get_json().get('success')

    # Leer auditoría via API
    audit = client.get(f'/api/risk/limits/audit?token={token}&lines=50')
    text = audit.get_data(as_text=True)
    # Debe contener el evento 'set_symbol_limits' o el valor aplicado
    assert 'set_symbol_limits' in text or 'RISK_MAX_PER_SYMBOL_TRADES' in text

    # Descargar archivo completo
    dl = client.get(f'/api/risk/limits/audit?token={token}&download=1')
    assert dl.status_code == 200
    # Debe tener cabecera de adjunto
    disp = dl.headers.get('Content-Disposition', '')
    assert 'attachment;' in disp


def test_risk_metrics_uses_state_or_fallback(flask_app_client, monkeypatch):
    web_app, client = flask_app_client
    token = _get_admin_token(web_app, client)

    # Simular StateManager con métricas predefinidas y sin pausa por drawdown
    class FakeSM:
        def __init__(self):
            self._state = {
                'risk_metrics': {
                    'daily_realized_pnl_usdt': 10.0,
                    'daily_unrealized_pnl_usdt': -2.0,
                    'daily_total_pnl_usdt': 8.0,
                    'total_capital_usdt': 1000.0,
                    'daily_pnl_percentage': 0.8,
                },
                'system': {
                    'drawdown_pause_until': None
                }
            }

        def get_state(self, module, key=None, default_value=None):
            if key is None:
                return self._state.get(module)
            return (self._state.get(module) or {}).get(key, default_value)

        def update_module_state(self, module, updates):
            self._state.setdefault(module, {}).update(updates)

    monkeypatch.setattr(web_app, 'StateManager', FakeSM)

    # Llamar endpoint
    r = client.get(f'/api/risk/metrics?token={token}')
    j = r.get_json()
    assert j and j.get('success')
    m = j.get('metrics') or {}
    assert m.get('daily_total_pnl_usdt') == 8.0
    assert j.get('paused_by_drawdown') is False


def test_risk_limits_post_requires_admin(flask_app_client):
    web_app, client = flask_app_client
    # Token de usuario no admin
    resp = client.get('/api/generate_token?user_id=123')
    token = resp.get_json()['token']
    body = {'token': token, 'RISK_MAX_PER_SYMBOL_TRADES': 2}
    r = client.post('/api/risk/limits', data=json.dumps(body), content_type='application/json')
    assert r.status_code == 403

