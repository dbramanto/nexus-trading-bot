"""
NEXUS v2.0 - P4 Trade Logger
"""
import json, os, uuid, logging
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)

class TradeLogger:
    def __init__(self, trade_log_dir="data/trade_logs", shadow_log_dir="data/shadow_logs"):
        self.trade_log_dir = trade_log_dir
        self.shadow_log_dir = shadow_log_dir
        os.makedirs(trade_log_dir, exist_ok=True)
        os.makedirs(shadow_log_dir, exist_ok=True)
        self._current_date = None

    def _get_log_path(self, log_dir):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._current_date = today
        return os.path.join(log_dir, f"{today}.jsonl")

    def log_executed(self, symbol, direction, entry_price, position_size, leverage,
                     sl_price, tp_price, score, grade, bias, regime,
                     threshold_used, threshold_modifier, p1_snapshot, is_paper=True):
        trade_id = str(uuid.uuid4())[:12]
        entry = {
            "trade_id": trade_id, "type": "EXECUTED",
            "symbol": symbol, "direction": direction,
            "entry_price": entry_price, "exit_price": None,
            "entry_time": datetime.now(timezone.utc).isoformat(), "exit_time": None,
            "position_size": position_size, "leverage": leverage,
            "fee_entry": round(entry_price * position_size * 0.0004, 4), "fee_exit": None,
            "slippage_entry": round(entry_price * 0.0003, 4), "slippage_exit": None,
            "sl_price": sl_price, "tp_price": tp_price,
            "pnl_gross": None, "pnl_net": None, "exit_reason": None,
            "score_at_entry": score, "grade_at_entry": grade,
            "bias_at_entry": bias, "regime_at_entry": regime,
            "threshold_used": threshold_used, "threshold_modifier": threshold_modifier,
            "p1_snapshot": p1_snapshot,
            "shadow": False, "paper": is_paper, "status": "OPEN"
        }
        self._write(self.trade_log_dir, entry)
        logger.info(f"Trade logged: {trade_id} | {direction} {symbol} @ {entry_price}")
        return trade_id

    def log_trade_close(self, trade_id, exit_price, exit_reason, pnl_gross, pnl_net):
        entry = {
            "trade_id": trade_id, "type": "CLOSE_UPDATE",
            "exit_price": exit_price,
            "exit_time": datetime.now(timezone.utc).isoformat(),
            "exit_reason": exit_reason,
            "pnl_gross": round(pnl_gross, 4), "pnl_net": round(pnl_net, 4),
            "fee_exit": round(exit_price * 0.0004, 4),
            "slippage_exit": round(exit_price * 0.0003, 4),
            "status": "CLOSED"
        }
        self._write(self.trade_log_dir, entry)
        logger.info(f"Trade closed: {trade_id} | {exit_reason} | PnL: {pnl_net:.2f}")

    def log_rejected(self, symbol, score, grade, bias, reason, p1_snapshot):
        entry = {
            "trade_id": None, "type": "REJECTED",
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "score": score, "grade": grade, "bias": bias,
            "reject_reason": reason, "p1_snapshot": p1_snapshot, "shadow": False
        }
        self._write(self.trade_log_dir, entry)

    def log_shadow(self, symbol, direction, potential_entry, potential_sl,
                   potential_tp, potential_lot, score, grade, bias,
                   reject_reason, p1_snapshot, ml_features=None,
                   score_breakdown=None, bias_reason=None):
        entry = {
            "type": "SHADOW", "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "direction": direction,
            "potential_entry": potential_entry, "potential_sl": potential_sl,
            "potential_tp": potential_tp, "potential_lot": potential_lot,
            "score": score, "grade": grade, "bias": bias,
            "reject_reason": reject_reason,
            "p1_snapshot": p1_snapshot, "shadow": True,
            "outcome": "PENDING",
        }
        if ml_features:
            entry.update(ml_features)
        if score_breakdown:
            entry["score_breakdown"] = score_breakdown
        if bias_reason:
            entry["bias_reason"] = bias_reason
        self._write(self.shadow_log_dir, entry)

    def _write(self, log_dir, entry):
        path = self._get_log_path(log_dir)
        try:
            with open(path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to write log: {e}")
