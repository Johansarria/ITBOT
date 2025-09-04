"""
Shim de compatibilidad para tests.

Define `log_dummy_operation` en este módulo y expone dependencias
como nombres del propio módulo para que los tests puedan parchearlas
directamente con `patch('log_dummy_operation.*')`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

# Dependencias parcheables por tests
from utils.order_executor import registrar_operacion  # noqa: F401
from utils.shield_manager import escudo_activo  # noqa: F401
from utils.risk_manager import riesgo_forzado_activo  # noqa: F401


class MockBot:
	async def send_message(self, chat_id, text, parse_mode=None, reply_markup=None):
		# No-op para pruebas
		return True


async def log_dummy_operation():
	"""Genera una operación dummy y la registra mediante registrar_operacion.

	Nota: Usa los nombres del módulo (registrar_operacion, escudo_activo,
	riesgo_forzado_activo) para que puedan ser parcheados en tests.
	"""
	dummy_bot = MockBot()
	dummy_chat_id = 123456789

	operation_id = str(uuid.uuid4())
	# Fecha fija para estabilidad en tests
	timestamp_open = datetime(2025, 8, 5, 10, 30, 0).isoformat()

	entry_price = 60000.0
	size_usdt = 100.0

	log_data = {
		"operation_id": operation_id,
		"timestamp_open": timestamp_open,
		"timestamp_close": None,
		"symbol": "BTCUSDT",
		"side": "BUY",
		"entry_price": entry_price,
		"exit_price": None,
		"take_profit": round(entry_price * 1.02, 2),
		"stop_loss": round(entry_price * 0.98, 2),
		"size_usdt": size_usdt,
		"risk_percent": 1.0,
		"mode": "SIMULATED",
		"pnl_usdt": None,
		"pnl_percent": None,
		"reason_open": "TECHNICAL_SIGNAL",
		"reason_close": None,
		"market_score_open": 0.75,
		"market_score_close": None,
		"version_bot": "1.0.0-dummy",
		"notes": "Operación de prueba generada por shim.",
		"balance_usdt_al_abrir": 15000.0,
		"escudo_activo_al_abrir": escudo_activo() != "ninguno",
		"tipo_escudo_al_abrir": escudo_activo(),
		"riesgo_forzado_al_abrir": riesgo_forzado_activo(),
		"cantidad_token_operada": size_usdt / entry_price,
		"min_notional_filter": 10.0,
		"step_size_filter": 0.0001,
		"price_tick_size_filter": 0.01,
		"slippage_apertura_pct": 0.0,
		"order_id_binance": None,
		"order_status_binance": None,
	}

	await registrar_operacion(dummy_bot, dummy_chat_id, log_data)
	print("Operación dummy registrada exitosamente.")


__all__ = [
	"log_dummy_operation",
	"registrar_operacion",
	"escudo_activo",
	"riesgo_forzado_activo",
]
