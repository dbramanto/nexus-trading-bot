"""
NEXUS v2.0 - Backtest Engine
Fee model: Taker 0.05% per side (verified dari Binance API, Fee Tier 0)
Round trip cost: 0.10% per trade
Slippage: 0 (diabaikan untuk retail position size)
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Fee constants — verified dari Binance API Fee Tier 0
TAKER_FEE = 0.0005   # 0.05%
MAKER_FEE = 0.0002   # 0.02%
ROUND_TRIP_FEE = TAKER_FEE * 2  # 0.10% — pakai taker kedua sisi


class FeeModel:
    """Fee calculator untuk backtest."""

    def __init__(self, maker_fee=MAKER_FEE, taker_fee=TAKER_FEE):
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee

    def calc_entry_fee(self, position_value: float) -> float:
        return round(position_value * self.taker_fee, 6)

    def calc_exit_fee(self, position_value: float) -> float:
        return round(position_value * self.taker_fee, 6)

    def calc_round_trip_fee(self, position_value: float) -> float:
        return round(position_value * ROUND_TRIP_FEE, 6)

    def calc_pnl_net(self, pnl_gross: float, position_value: float) -> float:
        total_fee = self.calc_round_trip_fee(position_value)
        return round(pnl_gross - total_fee, 6)


class BacktestTrade:
    """Single trade record dalam backtest."""

    def __init__(self, symbol, direction, entry_price, entry_bar,
                 sl_price, tp_price, position_size, leverage, score, grade):
        self.symbol = symbol
        self.direction = direction
        self.entry_price = entry_price
        self.entry_bar = entry_bar
        self.sl_price = sl_price
        self.tp_price = tp_price
        self.position_size = position_size
        self.leverage = leverage
        self.score = score
        self.grade = grade
        self.position_value = entry_price * position_size
        self.exit_price = None
        self.exit_bar = None
        self.exit_reason = None
        self.pnl_gross = None
        self.pnl_net = None
        self.status = "OPEN"

    def close(self, exit_price, exit_bar, exit_reason, fee_model: FeeModel):
        self.exit_price = exit_price
        self.exit_bar = exit_bar
        self.exit_reason = exit_reason
        self.status = "CLOSED"

        if self.direction == "LONG":
            self.pnl_gross = (exit_price - self.entry_price) * self.position_size
        else:
            self.pnl_gross = (self.entry_price - exit_price) * self.position_size

        self.pnl_net = fee_model.calc_pnl_net(self.pnl_gross, self.position_value)

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "entry_bar": self.entry_bar,
            "exit_bar": self.exit_bar,
            "sl_price": self.sl_price,
            "tp_price": self.tp_price,
            "position_size": self.position_size,
            "position_value": round(self.position_value, 4),
            "leverage": self.leverage,
            "score": self.score,
            "grade": self.grade,
            "exit_reason": self.exit_reason,
            "pnl_gross": round(self.pnl_gross, 4) if self.pnl_gross else None,
            "pnl_net": round(self.pnl_net, 4) if self.pnl_net else None,
            "status": self.status,
        }


class BacktestEngine:
    """
    Backtesting engine untuk NEXUS v2.0.
    Jalankan pipeline P1->P2->P3 di setiap bar historical data.
    Fee model: Taker 0.05% per side.
    """

    def __init__(self, config, initial_balance=1000.0):
        self.config = config
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.fee_model = FeeModel()
        self.trades: List[BacktestTrade] = []
        self.open_trades: Dict[str, BacktestTrade] = {}
        self.equity_curve = []
        self.rejected_count = 0

    def _calc_position(self, balance, risk_pct, entry, sl, leverage=10):
        risk_amount = balance * risk_pct
        sl_distance = abs(entry - sl)
        if sl_distance == 0:
            return 0, 0
        position_size = risk_amount / sl_distance
        position_value = position_size * entry
        required_margin = position_value / leverage
        if required_margin > balance * 0.5:
            position_size = (balance * 0.5 * leverage) / entry
        return round(position_size, 6), leverage

    def _calc_sl_tp(self, df, bar_idx, direction, atr_mult_sl=1.5, rr=2.0):
        if bar_idx < 14:
            return None, None
        recent = df.iloc[max(0, bar_idx-14):bar_idx+1]
        high = recent["high"]
        low = recent["low"]
        prev_close = recent["close"].shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        atr = tr.ewm(span=14, adjust=False).mean().iloc[-1]
        entry = df["close"].iloc[bar_idx]
        if direction == "LONG":
            sl = round(entry - atr * atr_mult_sl, 6)
            tp = round(entry + atr * atr_mult_sl * rr, 6)
        else:
            sl = round(entry + atr * atr_mult_sl, 6)
            tp = round(entry - atr * atr_mult_sl * rr, 6)
        return sl, tp

    def _check_exit(self, trade: BacktestTrade, bar) -> Optional[tuple]:
        high = bar["high"]
        low = bar["low"]
        if trade.direction == "LONG":
            if low <= trade.sl_price:
                return trade.sl_price, "SL_HIT"
            if high >= trade.tp_price:
                return trade.tp_price, "TP_HIT"
        else:
            if high >= trade.sl_price:
                return trade.sl_price, "SL_HIT"
            if low <= trade.tp_price:
                return trade.tp_price, "TP_HIT"
        return None

    def run(self, df: pd.DataFrame, p1_manager, p2_engine, p3_logic,
            symbol="BTCUSDT", warmup_bars=100) -> Dict:

        self.config.backtest.is_backtest = True
        logger.info(f"Backtest starting: {symbol} | {len(df)} bars | Balance=${self.balance}")
        # Set backtest mode — modul orderflow akan skip API call

        self.balance = self.initial_balance
        self.trades = []
        self.open_trades = {}
        self.equity_curve = [self.initial_balance]
        self.rejected_count = 0

        for i in range(warmup_bars, len(df)):
            bar = df.iloc[i]
            bar_time = df.index[i]

            # Check exit untuk open trades
            exits = []
            for sym, trade in list(self.open_trades.items()):
                result = self._check_exit(trade, bar)
                if result:
                    exits.append((sym, trade, result[0], result[1]))

            for sym, trade, exit_price, reason in exits:
                trade.close(exit_price, i, reason, self.fee_model)
                self.balance += trade.pnl_net
                self.trades.append(trade)
                del self.open_trades[sym]
                logger.debug(f"Exit {reason}: {sym} | PnL={trade.pnl_net:.4f} | Balance={self.balance:.2f}")

            self.equity_curve.append(round(self.balance, 2))

            # Skip jika sudah ada open trade di symbol ini
            if symbol in self.open_trades:
                continue

            # Run P1->P2->P3 di slice data sampai bar ini
            df_slice = df.iloc[max(0, i-299):i+1].copy()
            if len(df_slice) < 50:
                continue

            try:
                p1_rep = p1_manager.run_all(df_slice, self.config)
                ctx = p2_engine.score(p1_rep, None)
                dec = p3_logic.evaluate(ctx, circuit_breaker_active=False)
            except Exception as e:
                logger.error(f"Pipeline error bar {i}: {e}")
                continue

            action = dec["action"]
            score = ctx["score"]
            grade = ctx["grade"]
            bias = ctx["bias"]

            if action == "WAIT":
                self.rejected_count += 1
                continue

            # Guard: jangan execute jika grade NO_TRADE atau bias NEUTRAL
            grade_check = ctx.get("grade", "NO_TRADE")
            if grade_check == "NO_TRADE" or bias == "NEUTRAL":
                self.rejected_count += 1
                continue

            entry_price = bar["close"]
            direction = "LONG" if bias == "BULLISH" else "SHORT"
            sl, tp = self._calc_sl_tp(df, i, direction, atr_mult_sl=1.5, rr=3.0)

            if sl is None:
                continue

            size, lev = self._calc_position(
                self.balance,
                self.config.risk.risk_per_trade_percent / 100,
                entry_price, sl
            )

            if size <= 0:
                continue

            entry_fee = self.fee_model.calc_entry_fee(entry_price * size)
            self.balance -= entry_fee

            trade = BacktestTrade(
                symbol=symbol, direction=direction,
                entry_price=entry_price, entry_bar=i,
                sl_price=sl, tp_price=tp,
                position_size=size, leverage=lev,
                score=score, grade=grade
            )
            self.open_trades[symbol] = trade
            logger.debug(f"Entry {direction}: {symbol} @ {entry_price} | Score={score} | SL={sl} | TP={tp}")

        # Close semua trade yang masih open di akhir backtest
        last_bar = df.iloc[-1]
        for sym, trade in list(self.open_trades.items()):
            exit_price = last_bar["close"]
            trade.close(exit_price, len(df)-1, "END_OF_DATA", self.fee_model)
            self.balance += trade.pnl_net
            self.trades.append(trade)

        return self._generate_report(symbol, df)

    def _generate_report(self, symbol, df) -> Dict:
        if not self.trades:
            return {
                "symbol": symbol,
                "total_trades": 0,
                "message": "No trades generated"
            }

        closed = [t for t in self.trades if t.status == "CLOSED"]
        winners = [t for t in closed if t.pnl_net > 0]
        losers = [t for t in closed if t.pnl_net <= 0]

        total_pnl = sum(t.pnl_net for t in closed)
        total_fees = sum(self.fee_model.calc_round_trip_fee(t.position_value) for t in closed)
        win_rate = len(winners) / len(closed) * 100 if closed else 0

        avg_win = sum(t.pnl_net for t in winners) / len(winners) if winners else 0
        avg_loss = sum(t.pnl_net for t in losers) / len(losers) if losers else 0
        profit_factor = abs(sum(t.pnl_net for t in winners) / sum(t.pnl_net for t in losers)) if losers and sum(t.pnl_net for t in losers) != 0 else 0

        equity = self.equity_curve
        peak = equity[0]
        max_dd = 0
        for e in equity:
            if e > peak:
                peak = e
            dd = (peak - e) / peak * 100
            if dd > max_dd:
                max_dd = dd

        by_grade = {}
        for t in closed:
            g = t.grade
            if g not in by_grade:
                by_grade[g] = {"count": 0, "wins": 0, "pnl": 0}
            by_grade[g]["count"] += 1
            by_grade[g]["pnl"] += t.pnl_net
            if t.pnl_net > 0:
                by_grade[g]["wins"] += 1

        return {
            "symbol": symbol,
            "bars_tested": len(df),
            "total_trades": len(closed),
            "rejected": self.rejected_count,
            "winners": len(winners),
            "losers": len(losers),
            "win_rate_pct": round(win_rate, 2),
            "total_pnl_net": round(total_pnl, 4),
            "total_fees_paid": round(total_fees, 4),
            "avg_win": round(avg_win, 4),
            "avg_loss": round(avg_loss, 4),
            "profit_factor": round(profit_factor, 4),
            "max_drawdown_pct": round(max_dd, 2),
            "initial_balance": self.initial_balance,
            "final_balance": round(self.balance, 2),
            "return_pct": round((self.balance - self.initial_balance) / self.initial_balance * 100, 2),
            "by_grade": by_grade,
            "fee_model": {
                "taker_fee_pct": TAKER_FEE * 100,
                "round_trip_pct": ROUND_TRIP_FEE * 100,
                "slippage_pct": 0,
            },
            "trades": [t.to_dict() for t in closed]
        }
