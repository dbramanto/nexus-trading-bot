"""
NEXUS v2.0 - P4 Circuit Breaker
"""
import logging
from typing import Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self, max_consecutive_losses: int = 4, daily_loss_limit_pct: float = 5.0):
        self.max_consecutive_losses = max_consecutive_losses
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self._symbol_losses: Dict[str, int] = {}
        self._symbol_paused: Dict[str, bool] = {}
        self._symbol_penalty: Dict[str, int] = {}
        self._daily_pnl: float = 0.0
        self._daily_trade_count: int = 0
        self._current_date: str = ""
        self._daily_paused: bool = False

    def record_trade_result(self, symbol: str, pnl: float, balance: float):
        self._check_daily_reset()
        self._daily_pnl += pnl
        self._daily_trade_count += 1
        if pnl < 0:
            self._symbol_losses[symbol] = self._symbol_losses.get(symbol, 0) + 1
            consecutive = self._symbol_losses[symbol]
            if consecutive >= self.max_consecutive_losses:
                self._symbol_paused[symbol] = True
                self._symbol_penalty[symbol] = -50
                logger.warning(f"Circuit breaker ACTIVATED: {symbol} ({consecutive} consecutive losses)")
            elif consecutive >= 2:
                self._symbol_penalty[symbol] = -10 * consecutive
        else:
            self._symbol_losses[symbol] = 0
            self._symbol_paused[symbol] = False
            self._symbol_penalty[symbol] = 0
        if balance > 0:
            daily_loss_pct = abs(min(0, self._daily_pnl)) / balance * 100
            if daily_loss_pct >= self.daily_loss_limit_pct:
                self._daily_paused = True
                logger.warning(f"Daily loss limit hit: {daily_loss_pct:.1f}%")

    def is_symbol_paused(self, symbol: str) -> bool:
        self._check_daily_reset()
        if self._daily_paused: return True
        return self._symbol_paused.get(symbol, False)

    def get_state_for_p2(self, symbol: str) -> Dict[str, Any]:
        self._check_daily_reset()
        return {
            "symbol_penalty": self._symbol_penalty.get(symbol, 0),
            "is_paused": self.is_symbol_paused(symbol),
            "consecutive_losses": self._symbol_losses.get(symbol, 0),
            "daily_paused": self._daily_paused,
        }

    def get_daily_summary(self) -> Dict[str, Any]:
        return {
            "daily_pnl": round(self._daily_pnl, 2),
            "daily_trades": self._daily_trade_count,
            "daily_paused": self._daily_paused,
            "paused_symbols": [s for s, p in self._symbol_paused.items() if p],
            "symbol_streaks": dict(self._symbol_losses),
        }

    def reset_symbol(self, symbol: str):
        self._symbol_losses[symbol] = 0
        self._symbol_paused[symbol] = False
        self._symbol_penalty[symbol] = 0
        logger.info(f"Circuit breaker reset for {symbol}")

    def _check_daily_reset(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._current_date != today:
            if self._current_date:
                logger.info(f"Daily reset: PnL={self._daily_pnl:.2f}, Trades={self._daily_trade_count}")
            self._current_date = today
            self._daily_pnl = 0.0
            self._daily_trade_count = 0
            self._daily_paused = False
