"""
NEXUS v2.0 - Forward Test Runner
Shadow mode dengan 3 model scoring paralel (A/B/C).
"""
import time, logging, os, sys, json, pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()
os.makedirs("logs", exist_ok=True)
os.makedirs("data/shadow_logs", exist_ok=True)
os.makedirs("data/trade_logs", exist_ok=True)
os.makedirs("data/ml", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler("logs/nexus_v2.log", encoding="utf-8")]
)
logger = logging.getLogger("NEXUS")

from config.strategy_config import NexusConfig
from config.symbols import WATCHLIST
from core.p1_analyst import build_indicator_manager
from core.p1_analyst.orderflow.funding_rate import FundingRate
from core.p1_analyst.orderflow.open_interest import OpenInterest
from core.p1_analyst.orderflow.cvd_analyzer import CVDAnalyzer
from core.p1_analyst.orderflow.orderbook_imbalance import OrderBookImbalance
from core.p2_supervisor.scoring_engine import ScoringEngine
from core.p3_manager.strategy_logic import StrategyLogic
from core.p4_auditor.circuit_breaker import CircuitBreaker
from core.p4_auditor.trade_logger import TradeLogger
from core.p4_auditor.daily_report import generate_daily_report
from execution.binance_client import BinanceClientWrapper
from execution.telegram_notifier import TelegramNotifier


class NexusForwardTest:

    def __init__(self):
        logger.info("=== NEXUS v2.0 INITIALIZING ===")
        self.config = NexusConfig("config/settings.yaml")
        self.client = BinanceClientWrapper(testnet=self.config.trading.api_testnet)
        self.telegram = TelegramNotifier(enabled=True, mode_prefix="[SHADOW v2]")
        self.p1 = build_indicator_manager()
        self.p2 = ScoringEngine(self.config)
        self.p3 = StrategyLogic(self.config)
        self.p4_cb = CircuitBreaker(self.config)
        self.p4_log = TradeLogger()
        self.open_positions = {}
        self.open_positions_b = {}
        self.open_positions_c = {}
        self.cycle_count = 0
        self.total_signals = 0
        self.total_signals_b = 0
        self.total_signals_c = 0
        self.total_scans = 0
        self._state_file = "data/nexus_state.json"
        self._load_state()
        self._orderflow_modules = [
            m for m in self.p1._modules
            if isinstance(m, (FundingRate, OpenInterest, CVDAnalyzer, OrderBookImbalance))
        ]
        summary = self.p1.get_module_summary()
        logger.info(f"P1: {len(summary['active'])} active, {len(summary['placeholder'])} placeholder")
        logger.info(f"Threshold={self.config.scoring.weak_threshold} (weak) / {self.config.scoring.valid_threshold} (valid) | Balance=${self.config.trading.initial_balance}")

    def _load_state(self):
        try:
            if os.path.exists(self._state_file):
                with open(self._state_file) as f:
                    state = json.load(f)
                self.open_positions = state.get("open_positions", {})
                self.open_positions_b = state.get("open_positions_b", {})
                self.open_positions_c = state.get("open_positions_c", {})
                self.total_signals = state.get("total_signals", 0)
                self.total_signals_b = state.get("total_signals_b", 0)
                self.total_signals_c = state.get("total_signals_c", 0)
                logger.info(f"State loaded: {len(self.open_positions)} open positions")
        except Exception as e:
            logger.warning(f"State load failed: {e}")

    def _save_state(self):
        try:
            state = {
                "open_positions": self.open_positions,
                "open_positions_b": self.open_positions_b,
                "open_positions_c": self.open_positions_c,
                "total_signals": self.total_signals,
                "total_signals_b": self.total_signals_b,
                "total_signals_c": self.total_signals_c,
                "cycle_count": self.cycle_count,
                "saved_at": datetime.now().isoformat()
            }
            with open(self._state_file, "w") as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"State save failed: {e}")

    def _health_check(self):
        try:
            self.client.client.futures_ping()
            logger.info("Health check: OK")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def _fetch_df(self, symbol, interval="15m", limit=300):
        klines = self.client.get_futures_candles(symbol, interval, limit)
        rows = [{"timestamp": pd.to_datetime(k[0], unit="ms"),
                 "open": float(k[1]), "high": float(k[2]),
                 "low": float(k[3]), "close": float(k[4]),
                 "volume": float(k[5])} for k in klines]
        df = pd.DataFrame(rows).set_index("timestamp")
        return df

    def _next_candle_wait(self):
        now = datetime.now()
        seconds_in_candle = now.minute % 15 * 60 + now.second
        return max(10, 900 - seconds_in_candle + 5)

    def _send_daily_summary(self):
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = f"data/shadow_logs/{today}.jsonl"
            if not os.path.exists(log_file):
                return
            entries = []
            with open(log_file) as f:
                for line in f:
                    try: entries.append(json.loads(line))
                    except: pass
            entries = [e for e in entries if e.get("symbol") != "TEST"]
            signals = [e for e in entries if e.get("reject_reason") == "SIGNAL"]
            scores = [e.get("score", 0) for e in entries]
            avg_score = round(sum(scores)/len(scores), 1) if scores else 0
            biases = [e.get("bias", "NEUTRAL") for e in entries]
            lines = [
                "DAILY SUMMARY " + today,
                "Total scans : " + str(len(entries)),
                "Signals     : " + str(len(signals)),
                "Avg score   : " + str(avg_score),
                "BULL=" + str(biases.count("BULLISH")) + " BEAR=" + str(biases.count("BEARISH")) + " NEU=" + str(biases.count("NEUTRAL")),
            ]
            self.telegram.send(chr(10).join(lines))
        except Exception as e:
            logger.error(f"Daily summary failed: {e}")

    def _check_exit(self, positions_dict, label):
        closed = []
        for sym, pos in list(positions_dict.items()):
            try:
                klines = self.client.get_futures_candles(sym, "15m", 3)
                if not klines: continue
                last_high = float(klines[-1][2])
                last_low = float(klines[-1][3])
                last_close = float(klines[-1][4])
                entry = pos["entry"]
                sl = pos.get("sl", 0)
                tp = pos.get("tp", 0)
                direction = pos.get("direction", "BULLISH")
                outcome = None
                exit_price = last_close
                if direction == "BULLISH":
                    if sl > 0 and last_low <= sl: outcome, exit_price = "LOSS", sl
                    elif tp > 0 and last_high >= tp: outcome, exit_price = "WIN", tp
                else:
                    if sl > 0 and last_high >= sl: outcome, exit_price = "LOSS", sl
                    elif tp > 0 and last_low <= tp: outcome, exit_price = "WIN", tp
                if outcome:
                    pnl = round((exit_price-entry)/entry*100, 4) if direction == "BULLISH" else round((entry-exit_price)/entry*100, 4)
                    open_time = pos.get("open_time", "")
                    duration = "N/A"
                    if open_time:
                        try:
                            delta = datetime.now() - datetime.fromisoformat(open_time)
                            candles = int(delta.total_seconds() / 900)
                            duration = str(candles) + " candles (" + str(round(delta.total_seconds()/3600, 1)) + "h)"
                        except: pass
                    msg = chr(10).join([
                        "[" + label + "] EXIT " + outcome,
                        "Symbol   : " + sym,
                        "Arah     : " + direction,
                        "Entry    : " + str(round(entry, 4)),
                        "Exit     : " + str(round(exit_price, 4)),
                        "PnL      : " + str(pnl) + "%",
                        "Score    : " + str(pos.get("score", 0)) + " [" + pos.get("grade", "") + "]",
                        "Duration : " + duration,
                        "Alasan   : " + pos.get("reason", "N/A"),
                        "Time     : " + datetime.now().strftime("%H:%M:%S WIB"),
                    ])
                    self.telegram.send(msg)
                    logger.info(f"[{label}] EXIT {outcome}: {sym} PnL={pnl}% {duration}")
                    closed.append(sym)
            except Exception as e:
                logger.error(f"Exit check error {label} {sym}: {e}")
        return closed

    def scan_symbol(self, symbol):
        df = self._fetch_df(symbol)
        if df is None or len(df) < 100:
            return None
        for mod in self._orderflow_modules:
            mod.set_context(symbol, self.client)
        p1_rep = self.p1.run_all(df, self.config)
        mods = p1_rep.get("modules", {})
        cb_state = self.p4_cb.get_state_for_p2(symbol)
        ctx = self.p2.score(p1_rep, cb_state)
        dec = self.p3.evaluate(ctx, circuit_breaker_active=self.p4_cb.is_symbol_paused(symbol))
        score = ctx["score"]
        grade = ctx["grade"]
        action = dec["action"]
        bias = ctx["bias"]
        price = df["close"].iloc[-1]

        # SL/TP calculation
        atr_val = mods.get("basic_indicators", {}).get("atr_value") or 0
        sl_mult, tp_mult = 3.0, 9.0
        direction = bias if bias != "NEUTRAL" else "N/A"
        if action != "WAIT" and atr_val > 0:
            if bias == "BULLISH":
                pot_sl = round(price - atr_val * sl_mult, 4)
                pot_tp = round(price + atr_val * tp_mult, 4)
            else:
                pot_sl = round(price + atr_val * sl_mult, 4)
                pot_tp = round(price - atr_val * tp_mult, 4)
            pot_lot = round(self.config.trading.initial_balance * self.config.risk.risk_per_trade_percent / 100 / (atr_val * sl_mult), 4)
            sl_dist_pct = round(abs(price - pot_sl) / price * 100, 4)
            tp_dist_pct = round(abs(pot_tp - price) / price * 100, 4)
        else:
            pot_sl = pot_tp = pot_lot = sl_dist_pct = tp_dist_pct = 0

        # Session label
        now = datetime.now()
        hour = now.hour
        if 6 <= hour < 14: session = "ASIA"
        elif 14 <= hour < 20: session = "LONDON"
        elif hour >= 20 or hour < 2: session = "NEWYORK"
        else: session = "OVERLAP"

        # BTC context
        btc_price_change = btc_vol_ratio = rs_vs_btc = 0
        btc_trend = "NEUTRAL"
        try:
            btc_klines = self.client.get_futures_candles("BTCUSDT", "15m", 5)
            if btc_klines and len(btc_klines) >= 4:
                btc_now = float(btc_klines[-1][4])
                btc_1h = float(btc_klines[-4][4])
                btc_price_change = round((btc_now - btc_1h) / btc_1h * 100, 4)
                btc_vols = [float(k[5]) for k in btc_klines]
                btc_vol_ratio = round(btc_vols[-1] / (sum(btc_vols[:-1]) / max(len(btc_vols[:-1]), 1)), 2)
                btc_trend = "BULLISH" if btc_price_change > 0.2 else "BEARISH" if btc_price_change < -0.2 else "NEUTRAL"
                if symbol != "BTCUSDT" and btc_price_change != 0:
                    sym_klines = self.client.get_futures_candles(symbol, "15m", 5)
                    if sym_klines and len(sym_klines) >= 4:
                        sym_chg = (float(sym_klines[-1][4]) - float(sym_klines[-4][4])) / float(sym_klines[-4][4]) * 100
                        rs_vs_btc = round(sym_chg - btc_price_change, 4)
        except: pass

        # Model B dan C evaluation
        dec_b = self.p3.evaluate_model_b(ctx)
        dec_c = self.p3.evaluate_model_c(ctx)

        # ML features
        mb = ctx.get("model_b", {})
        mc = ctx.get("model_c", {})
        tier = ctx.get("tier_breakdown", {})
        penalties = ctx.get("penalties_applied", [])
        bonuses = ctx.get("bonuses_applied", [])
        ml_features = {
            "hour_wib": hour, "day_of_week": now.weekday(), "session": session,
            "sl_dist_pct": sl_dist_pct, "tp_dist_pct": tp_dist_pct,
            "rr_ratio": round(tp_dist_pct / sl_dist_pct, 2) if sl_dist_pct > 0 else 0,
            "penalties_count": len(penalties), "bonuses_count": len(bonuses),
            "threshold_modifier": ctx.get("threshold_modifier", 0),
            "regime": ctx.get("regime", "UNKNOWN"),
            "btc_price_change_pct": btc_price_change, "btc_vol_ratio": btc_vol_ratio,
            "btc_trend": btc_trend, "rs_vs_btc": rs_vs_btc,
            "score_t0": tier.get("t0", 0), "score_t1": tier.get("t1", 0), "score_t2": tier.get("t2", 0),
            "penalty_sources": "|".join([p["source"] for p in penalties]),
            "bonus_sources": "|".join([b["source"] for b in bonuses]),
            "choch_detected": mods.get("mss_detector", {}).get("choch_detected", False),
            "choch_direction": mods.get("mss_detector", {}).get("choch_direction"),
            "pdl_swept": mods.get("daily_levels", {}).get("pdl_swept", False),
            "pdh_swept": mods.get("daily_levels", {}).get("pdh_swept", False),
            "cvd_signal": mods.get("cvd_analyzer", {}).get("cvd_signal", "NEUTRAL"),
            "ob_signal": mods.get("orderbook_imbalance", {}).get("ob_signal", "BALANCED"),
            "fng_value": mods.get("fear_greed_index", {}).get("fng_value", 50),
            "sweep_direction": mods.get("liquidity_sweeps", {}).get("sweep_direction"),
            "model_b_confidence": mb.get("confidence_pct", 0),
            "model_b_agree": mb.get("agree", 0),
            "model_b_action": dec_b["action"],
            "model_b_grade": dec_b.get("grade", ""),
            "model_c_score": mc.get("score", 0),
            "model_c_status": mc.get("status", ""),
            "model_c_action": dec_c["action"],
            "model_c_grade": dec_c.get("grade", ""),
        }

        # Score breakdown dan bias reason
        score_breakdown = {
            "t0": tier.get("t0", 0), "t1": tier.get("t1", 0), "t2": tier.get("t2", 0),
            "penalties": [{"source": p["source"], "value": p["value"]} for p in penalties],
            "bonuses": [{"source": b["source"], "value": b["value"]} for b in bonuses],
            "threshold_used": ctx.get("threshold_used", 55),
        }
        mss_d = mods.get("mss_detector", {})
        mom_d = mods.get("momentum_classifier", {})
        cvd_d = mods.get("cvd_analyzer", {})
        ob_d = mods.get("orderbook_imbalance", {})
        fng_d = mods.get("fear_greed_index", {})
        dl_d = mods.get("daily_levels", {})
        sw_d = mods.get("liquidity_sweeps", {})
        bias_reason = {
            "mss_structure": mss_d.get("mss_structure"),
            "choch_detected": mss_d.get("choch_detected"),
            "choch_direction": mss_d.get("choch_direction"),
            "momentum": mom_d.get("momentum"),
            "momentum_strength": mom_d.get("momentum_strength"),
            "cvd_signal": cvd_d.get("cvd_signal"),
            "ob_signal": ob_d.get("ob_signal"),
            "fng_value": fng_d.get("fng_value"),
            "fng_sentiment": fng_d.get("fng_sentiment"),
            "pdh_swept": dl_d.get("pdh_swept"),
            "pdl_swept": dl_d.get("pdl_swept"),
            "pdh_rejected": dl_d.get("pdh_rejected"),
            "pdl_rejected": dl_d.get("pdl_rejected"),
            "level_context": dl_d.get("level_context"),
            "sweep_direction": sw_d.get("sweep_direction"),
        }

        # Log shadow
        self.p4_log.log_shadow(
            symbol=symbol, direction=direction, potential_entry=price,
            potential_sl=pot_sl, potential_tp=pot_tp, potential_lot=pot_lot,
            score=score, grade=grade, bias=bias,
            reject_reason=dec["reason"] if action == "WAIT" else "SIGNAL",
            p1_snapshot=ctx.get("p1_snapshot", {}),
            ml_features=ml_features, score_breakdown=score_breakdown, bias_reason=bias_reason
        )

        self.total_scans += 1

        # Model A — entry
        if action != "WAIT" and symbol not in self.open_positions:
            self.total_signals += 1
            br = bias_reason
            reasons = []
            if br.get("choch_detected"): reasons.append("CHoCH " + str(br.get("choch_direction", "")))
            if br.get("pdl_swept") and br.get("pdl_rejected"): reasons.append("PDL swept+rejected")
            if br.get("pdh_swept") and br.get("pdh_rejected"): reasons.append("PDH swept+rejected")
            if br.get("cvd_signal", "NEUTRAL") != "NEUTRAL": reasons.append("CVD=" + str(br.get("cvd_signal", "")))
            if br.get("fng_value") and int(br.get("fng_value", 50)) <= 30: reasons.append("FNG=" + str(br.get("fng_value", "")) + " FEAR")
            reason_str = ", ".join(reasons) if reasons else "confluence"
            sb = score_breakdown
            pen_str = " | PEN: " + ", ".join([p["source"][:15] for p in sb.get("penalties", [])]) if sb.get("penalties") else ""
            self.open_positions[symbol] = {
                "action": action, "direction": bias, "entry": price,
                "sl": pot_sl, "tp": pot_tp, "score": score, "grade": grade,
                "reason": reason_str, "t0": tier.get("t0",0), "t1": tier.get("t1",0), "t2": tier.get("t2",0),
                "open_time": now.isoformat(),
            }
            self._save_state()
            entry_lines = [
                "[SHADOW A] ENTRY " + action,
                "Symbol  : " + symbol, "Arah    : " + bias,
                "Entry   : " + str(round(price, 4)),
                "SL      : " + str(pot_sl) + " (-" + str(sl_dist_pct) + "%)",
                "TP      : " + str(pot_tp) + " (+" + str(tp_dist_pct) + "%)",
                "Score   : " + str(score) + "/100 [" + grade + "]",
                "T0/T1/T2: " + str(tier.get("t0",0)) + "/" + str(tier.get("t1",0)) + "/" + str(tier.get("t2",0)) + pen_str,
                "Konfiden: " + str(mb.get("confidence_pct", 0)) + "% (" + str(mb.get("agree",0)) + "/" + str(mb.get("total",22)) + " modul)",
                "Regime  : " + ctx.get("regime", ""), "Session : " + session,
                "BTC     : " + btc_trend + " (" + str(btc_price_change) + "%)",
                "Alasan  : " + reason_str,
                "Time    : " + now.strftime("%H:%M:%S WIB"),
            ]
            self.telegram.send(chr(10).join(entry_lines))
            logger.info(f"[MODEL A] SIGNAL {symbol} Score={score} [{grade}] {bias}")

        # Model B — entry
        if dec_b["action"] != "WAIT" and symbol not in self.open_positions_b:
            self.total_signals_b += 1
            self.open_positions_b[symbol] = {
                "action": dec_b["action"], "direction": bias, "entry": price,
                "sl": pot_sl, "tp": pot_tp, "score": mb.get("confidence_pct", 0),
                "grade": dec_b.get("grade", ""), "reason": dec_b.get("reason", ""),
                "open_time": now.isoformat(),
            }
            b_lines = [
                "[SHADOW B] ENTRY " + dec_b["action"] + " (Binary)",
                "Symbol   : " + symbol,
                "Konfiden : " + str(mb.get("confidence_pct", 0)) + "% (" + str(mb.get("agree", 0)) + "/" + str(mb.get("total", 22)) + " modul)",
                "Grade    : " + dec_b.get("grade", ""),
                "Entry    : " + str(round(price, 4)),
                "SL/TP   : " + str(pot_sl) + " / " + str(pot_tp),
                "Session : " + session + " | BTC: " + btc_trend,
                "Time    : " + now.strftime("%H:%M:%S WIB"),
            ]
            self.telegram.send(chr(10).join(b_lines))
            logger.info(f"[MODEL B] SIGNAL {symbol} conf={mb.get('confidence_pct',0)}%")

        # Model C — entry
        if dec_c["action"] != "WAIT" and symbol not in self.open_positions_c:
            self.total_signals_c += 1
            self.open_positions_c[symbol] = {
                "action": dec_c["action"], "direction": bias, "entry": price,
                "sl": pot_sl, "tp": pot_tp, "score": mc.get("score", 0),
                "grade": dec_c.get("grade", ""), "reason": dec_c.get("reason", ""),
                "open_time": now.isoformat(),
            }
            c_lines = [
                "[SHADOW C] ENTRY " + dec_c["action"] + " (Hybrid)",
                "Symbol  : " + symbol,
                "Score A : " + str(score) + " [" + grade + "]",
                "Konfiden: " + str(mb.get("confidence_pct", 0)) + "%",
                "Score C : " + str(mc.get("score", 0)) + " [" + dec_c.get("grade", "") + "]",
                "Entry   : " + str(round(price, 4)),
                "SL/TP  : " + str(pot_sl) + " / " + str(pot_tp),
                "Session : " + session + " | BTC: " + btc_trend,
                "Time    : " + now.strftime("%H:%M:%S WIB"),
            ]
            self.telegram.send(chr(10).join(c_lines))
            logger.info(f"[MODEL C] SIGNAL {symbol} score={mc.get('score',0)}")

        return {
            "symbol": symbol, "action": action, "score": score,
            "grade": grade, "bias": bias,
            "penalties": len(penalties),
        }

    def run(self):
        if not self._health_check():
            logger.error("Aborting: health check failed")
            return
        logger.info(f"=== NEXUS v2.0 SHADOW MODE | {len(WATCHLIST)} symbols ===")
        self.telegram.send("NEXUS v2.0 Shadow Mode started")
        last_summary_date = datetime.now().strftime("%Y-%m-%d")
        while True:
            try:
                self.cycle_count += 1
                now = datetime.now()
                logger.info(f"--- Cycle {self.cycle_count} | {now.strftime('%H:%M:%S')} WIB ---")

                # Daily summary dan report jam 07:00 WIB
                today = now.strftime("%Y-%m-%d")
                if now.hour == 7 and now.minute < 15 and today != last_summary_date:
                    self._send_daily_summary()
                    try:
                        generate_daily_report(
                            shadow_log_dir="data/shadow_logs",
                            ml_csv="data/ml/labeled_trades.csv",
                            telegram_notifier=self.telegram
                        )
                    except Exception as e:
                        logger.error(f"Daily report error: {e}")
                    last_summary_date = today

                # Exit check semua model
                closed_a = self._check_exit(self.open_positions, "SHADOW A")
                closed_b = self._check_exit(self.open_positions_b, "SHADOW B")
                closed_c = self._check_exit(self.open_positions_c, "SHADOW C")
                for sym in closed_a: del self.open_positions[sym]
                for sym in closed_b: del self.open_positions_b[sym]
                for sym in closed_c: del self.open_positions_c[sym]
                if closed_a or closed_b or closed_c:
                    self._save_state()

                # Scan semua symbols
                results = []
                for symbol in WATCHLIST:
                    try:
                        r = self.scan_symbol(symbol)
                        if r: results.append(r)
                    except Exception as e:
                        logger.error(f"Error {symbol}: {e}")

                signals = [r for r in results if r["action"] != "WAIT"]
                penalized = [r for r in results if r["penalties"] > 0]
                logger.info(f"Cycle {self.cycle_count} | Scanned={len(results)} Signal={len(signals)} Penalized={len(penalized)} TotalSignals={self.total_signals}")
                if signals:
                    for s in signals:
                        logger.info(f"  >> {s['symbol']} Score={s['score']} [{s['grade']}] {s['bias']}")

                self._save_state()
                wait_secs = self._next_candle_wait()
                logger.info(f"Next scan in {wait_secs}s")
                time.sleep(wait_secs)

            except KeyboardInterrupt:
                logger.info(f"Stopped. Cycles={self.cycle_count} Signals={self.total_signals}")
                self._save_state()
                self.telegram.send("NEXUS v2.0 Stopped.")
                break
            except Exception as e:
                logger.error(f"Cycle error: {e}")
                time.sleep(60)


if __name__ == "__main__":
    bot = NexusForwardTest()
    bot.run()
