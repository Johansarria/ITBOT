"""risk_manager: reglas de riesgo y parada (kill switch)"""
from dataclasses import dataclass, field
from threading import RLock
from typing import Dict, Any
from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RiskConfig:
    max_trade_loss: float = 100.0  # stop loss por operación en USD
    max_trade_profit: float | None = None  # take profit por operación en USD
    max_exposure_pct: float = 0.1  # porcentaje del capital total
    max_daily_drawdown: float = 0.05  # drawdown diario máximo (5% por defecto)
    max_concurrent_trades: int = 5


@dataclass
class AccountState:
    capital: float
    open_positions: Dict[str, float] = field(default_factory=dict)  # symbol -> exposure (USD)
    realized_pnl_today: float = 0.0
    peak_balance_today: float = 0.0


class RiskManager:
    """Gestión de riesgos y kill switch.

    Es seguros para usar desde hilos múltiples.
    """

    def __init__(self, config: RiskConfig, account: AccountState):
        self.config = config
        self.account = account
        self.lock = RLock()
        self.kill_switch_engaged = False

    # --- Checks
    def can_open_trade(self, symbol: str, notional: float) -> bool:
        with self.lock:
            if self.kill_switch_engaged:
                logger.warning("can_open_trade denied - kill switch engaged", extra={"symbol": symbol, "notional": notional})
                return False

            # concurrent trades
            if len(self.account.open_positions) >= self.config.max_concurrent_trades:
                logger.info("can_open_trade denied - max concurrent trades reached", extra={"current": len(self.account.open_positions)})
                return False

            # exposure check
            total_exposure = sum(self.account.open_positions.values())
            capital = self.account.capital
            new_total = total_exposure + notional
            if new_total > capital * self.config.max_exposure_pct:
                logger.info("can_open_trade denied - exposure limit", extra={"total_exposure": total_exposure, "notional": notional, "limit": capital * self.config.max_exposure_pct})
                return False

            # daily drawdown check
            # if realized_pnl_today falls below -max_daily_drawdown * peak_balance
            allowed_drawdown = -self.config.max_daily_drawdown * max(self.account.peak_balance_today, self.account.capital)
            if self.account.realized_pnl_today <= allowed_drawdown:
                logger.warning("can_open_trade denied - daily drawdown exceeded", extra={"realized_pnl_today": self.account.realized_pnl_today, "allowed_drawdown": allowed_drawdown})
                return False

            return True

    def register_new_position(self, symbol: str, notional: float):
        with self.lock:
            if symbol in self.account.open_positions:
                self.account.open_positions[symbol] += notional
            else:
                self.account.open_positions[symbol] = notional
            logger.info("position_opened", extra={"symbol": symbol, "notional": notional, "positions": dict(self.account.open_positions)})

    def close_position(self, symbol: str, realized_pnl: float):
        with self.lock:
            exposure = self.account.open_positions.pop(symbol, 0.0)
            self.account.realized_pnl_today += realized_pnl
            self.account.capital += realized_pnl
            self.account.peak_balance_today = max(self.account.peak_balance_today, self.account.capital)
            logger.info("position_closed", extra={"symbol": symbol, "exposure": exposure, "realized_pnl": realized_pnl, "capital": self.account.capital})

    # --- Kill switch
    def engage_kill_switch(self):
        with self.lock:
            self.kill_switch_engaged = True
            logger.critical("kill_switch_engaged", extra={"open_positions": dict(self.account.open_positions)})

    def disengage_kill_switch(self):
        with self.lock:
            self.kill_switch_engaged = False
            logger.warning("kill_switch_disengaged")

    def liquidate_all(self) -> Dict[str, float]:
        """Simula liquidación de todas las posiciones. Devuelve mapa symbol->exposure liquidado."""
        with self.lock:
            liquidated = dict(self.account.open_positions)
            self.account.open_positions.clear()
            logger.critical("liquidated_all_positions", extra={"liquidated": liquidated})
            return liquidated

    # --- Per-trade risk enforcement (stop loss / take profit math)
    def evaluate_trade_risk(self, entry_price: float, current_price: float, quantity: float) -> Dict[str, Any]:
        """Devuelve dict con keys 'stop_loss_hit', 'take_profit_hit' según configuración."""
        with self.lock:
            notional = entry_price * quantity
            pnl = (current_price - entry_price) * quantity
            stop_loss_hit = pnl <= -self.config.max_trade_loss
            take_profit_hit = False
            if self.config.max_trade_profit is not None:
                take_profit_hit = pnl >= self.config.max_trade_profit
            logger.debug("evaluate_trade_risk", extra={"entry_price": entry_price, "current_price": current_price, "quantity": quantity, "pnl": pnl, "stop_loss_hit": stop_loss_hit, "take_profit_hit": take_profit_hit})
            return {"stop_loss_hit": stop_loss_hit, "take_profit_hit": take_profit_hit, "pnl": pnl, "notional": notional}
