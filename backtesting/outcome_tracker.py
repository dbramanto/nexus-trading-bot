"""
NEXUS v2.0 - Outcome Tracker
Jalan setiap hari untuk label shadow log dengan outcome aktual.
Fetch candle data setelah entry, cek apakah hit TP atau SL.
Output: labeled_trades.csv untuk ML training.
"""
import sys, os
sys.path.insert(0, "/home/nexus/nexus_bot")
import json
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import os
import pandas as pd
import time
import logging
from datetime import datetime, timedelta
from execution.binance_client import BinanceClientWrapper

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("OutcomeTracker")

MAX_CANDLES_WAIT = 96  # 24 jam di M15


def fetch_candles_after(client, symbol, entry_timestamp, limit=100):
    try:
        ts_ms = int(pd.Timestamp(entry_timestamp).timestamp() * 1000)
        klines = client.client.futures_klines(
            symbol=symbol, interval="15m",
            startTime=ts_ms, limit=limit
        )
        rows = []
        for k in klines:
            rows.append({
                "timestamp": pd.to_datetime(k[0], unit="ms"),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
            })
        return pd.DataFrame(rows)
    except Exception as e:
        logger.error(f"Fetch error {symbol}: {e}")
        return pd.DataFrame()


def determine_outcome(df, entry_price, sl_price, tp_price, direction):
    if df.empty or sl_price == 0 or tp_price == 0:
        return "UNKNOWN", 0, 0, 0

    max_fav = 0
    max_adv = 0

    for i, row in df.iterrows():
        if direction == "BULLISH":
            fav = row["high"] - entry_price
            adv = entry_price - row["low"]
            if row["low"] <= sl_price:
                return "LOSS", i, round(max_fav, 4), round(max_adv, 4)
            if row["high"] >= tp_price:
                return "WIN", i, round(max_fav, 4), round(max_adv, 4)
        else:
            fav = entry_price - row["low"]
            adv = row["high"] - entry_price
            if row["high"] >= sl_price:
                return "LOSS", i, round(max_fav, 4), round(max_adv, 4)
            if row["low"] <= tp_price:
                return "WIN", i, round(max_fav, 4), round(max_adv, 4)

        max_fav = max(max_fav, fav)
        max_adv = max(max_adv, adv)

    return "NEUTRAL", MAX_CANDLES_WAIT, round(max_fav, 4), round(max_adv, 4)


def process_shadow_log(log_file, client, output_csv):
    if not os.path.exists(log_file):
        logger.warning(f"File not found: {log_file}")
        return 0

    processed = 0
    labeled = []

    with open(log_file) as f:
        entries = [json.loads(line) for line in f if line.strip()]

    # Hanya proses yang punya SL/TP dan belum di-label
    to_label = [
        e for e in entries
        if e.get("potential_sl", 0) != 0
        and e.get("potential_tp", 0) != 0
        and e.get("outcome", "PENDING") == "PENDING"
        and e.get("bias") in ("BULLISH", "BEARISH")
    ]

    logger.info(f"Entries to label: {len(to_label)}")

    for entry in to_label:
        symbol = entry["symbol"]
        ts = entry["timestamp"]
        entry_price = entry.get("potential_entry", 0)
        sl = entry.get("potential_sl", 0)
        tp = entry.get("potential_tp", 0)
        bias = entry.get("bias")

        df = fetch_candles_after(client, symbol, ts, limit=MAX_CANDLES_WAIT)
        if df.empty:
            continue

        outcome, candles_to_outcome, mfe, mae = determine_outcome(
            df, entry_price, sl, tp, bias
        )

        snap = entry.get("p1_snapshot", {})
        row = {
            "timestamp": ts,
            "symbol": symbol,
            "direction": bias,
            "score": entry.get("score", 0),
            "grade": entry.get("grade", ""),
            "regime": entry.get("regime", entry.get("ml_features", {}).get("regime", "UNKNOWN")),
            "hour_wib": entry.get("hour_wib", 0),
            "day_of_week": entry.get("day_of_week", 0),
            "entry_price": entry_price,
            "sl_price": sl,
            "tp_price": tp,
            "sl_dist_pct": entry.get("sl_dist_pct", 0),
            "tp_dist_pct": entry.get("tp_dist_pct", 0),
            "rr_ratio": entry.get("rr_ratio", 0),
            "penalties_count": entry.get("penalties_count", 0),
            "bonuses_count": entry.get("bonuses_count", 0),
            "outcome": outcome,
            "candles_to_outcome": candles_to_outcome,
            "max_favorable_excursion": mfe,
            "max_adverse_excursion": mae,
            "rsi_value": snap.get("basic_indicators", {}).get("rsi_value"),
            "volume_ratio": snap.get("basic_indicators", {}).get("volume_ratio"),
            "atr_percent": snap.get("basic_indicators", {}).get("atr_percent"),
            "mss_structure": snap.get("mss_detector", {}).get("mss_structure"),
            "choch_detected": snap.get("mss_detector", {}).get("choch_detected"),
            "momentum": snap.get("momentum_classifier", {}).get("momentum"),
            "momentum_strength": snap.get("momentum_classifier", {}).get("momentum_strength"),
            "price_zone": snap.get("premium_discount", {}).get("price_zone"),
            "fvg_present": snap.get("fvg_detector", {}).get("fvg_present"),
            "ob_present": snap.get("orderblock_detector", {}).get("ob_present"),
            "sweep_detected": snap.get("liquidity_sweeps", {}).get("sweep_detected"),
            "pdh_swept": snap.get("daily_levels", {}).get("pdh_swept"),
            "pdl_swept": snap.get("daily_levels", {}).get("pdl_swept"),
            "breakout_detected": snap.get("breakout_detector", {}).get("breakout_detected"),
            "cvd_signal": snap.get("cvd_analyzer", {}).get("cvd_signal"),
            "ob_signal": snap.get("orderbook_imbalance", {}).get("ob_signal"),
            "fng_value": snap.get("fear_greed_index", {}).get("fng_value"),
            "funding_sentiment": snap.get("funding_rate", {}).get("sentiment"),
            "primary_pattern": snap.get("candle_pattern", {}).get("primary_pattern"),
            "pattern_strength": snap.get("candle_pattern", {}).get("pattern_strength"),
            "vwap_position": snap.get("vwap_calculator", {}).get("vwap_position"),
            "bb_position": snap.get("bollinger_bands", {}).get("bb_position"),
            "stoch_signal": snap.get("stochastic_rsi", {}).get("stoch_signal"),
            "macd_cross": snap.get("macd_indicator", {}).get("cross"),
        }
        labeled.append(row)
        processed += 1
        time.sleep(0.2)

    if labeled:
        df_out = pd.DataFrame(labeled)
        if os.path.exists(output_csv):
            df_existing = pd.read_csv(output_csv)
            df_out = pd.concat([df_existing, df_out], ignore_index=True)
        df_out.to_csv(output_csv, index=False)
        logger.info(f"Saved {len(labeled)} labeled trades to {output_csv}")

    return processed


if __name__ == "__main__":
    sys.path.insert(0, ".")
    client = BinanceClientWrapper(testnet=False)
    os.makedirs("data/ml", exist_ok=True)

    # Proses semua shadow log yang ada
    log_dir = "data/shadow_logs"
    all_dates = sorted([
        f[:10] for f in os.listdir(log_dir)
        if f.endswith(".jsonl")
    ])

    for date in all_dates:
        log_file = f"data/shadow_logs/{date}.jsonl"
        output_csv = "data/ml/labeled_trades.csv"
        logger.info(f"Processing {log_file}...")
        n = process_shadow_log(log_file, client, output_csv)
        logger.info(f"Processed {n} entries from {date}")

    if os.path.exists("data/ml/labeled_trades.csv"):
        df = pd.read_csv("data/ml/labeled_trades.csv")
        print()
        print("=== LABELED TRADES SUMMARY ===")
        print(f"Total records: {len(df)}")
        if "outcome" in df.columns:
            print(df["outcome"].value_counts().to_string())

        # Kirim daily report ke Telegram
        try:
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from execution.telegram_notifier import TelegramNotifier
            from core.p4_auditor.daily_report import generate_daily_report
            tg = TelegramNotifier(enabled=True, mode_prefix="[SHADOW v2]")
            generate_daily_report(
                shadow_log_dir="data/shadow_logs",
                ml_csv="data/ml/labeled_trades.csv",
                telegram_notifier=tg
            )
            logger.info("Daily report sent to Telegram")
        except Exception as e:
            logger.error(f"Daily report failed: {e}")
