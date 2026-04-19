"""
NEXUS v2.0 - Daily Report Generator
Laporan harian dengan reason yang actionable untuk monitoring dan ML.
"""
import json
import os
import pandas as pd
from datetime import datetime, timedelta
from collections import Counter


def generate_daily_report(shadow_log_dir, ml_csv, telegram_notifier):
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    log_file = shadow_log_dir + "/" + yesterday + ".jsonl"
    entries = []
    if os.path.exists(log_file):
        with open(log_file) as f:
            for line in f:
                try: entries.append(json.loads(line))
                except: pass

    entries = [e for e in entries if e.get("symbol") != "TEST"]
    signals = [e for e in entries if e.get("reject_reason") == "SIGNAL"]
    waits = [e for e in entries if e.get("reject_reason") != "SIGNAL"]

    # Rejection reason analysis
    reject_reasons = Counter()
    penalty_sources = Counter()
    for e in waits:
        reason = e.get("reject_reason", "unknown")
        if len(reason) > 40:
            reason = reason[:40]
        reject_reasons[reason] += 1
        pen_str = e.get("penalty_sources", "")
        if pen_str:
            for p in pen_str.split("|"):
                if p: penalty_sources[p] += 1

    # Bias distribution
    biases = Counter(e.get("bias", "NEUTRAL") for e in entries)
    sessions = Counter(e.get("session", "UNKNOWN") for e in entries if e.get("session"))
    regimes = Counter(e.get("regime", "UNKNOWN") for e in entries if e.get("regime"))

    # Score stats
    scores = [e.get("score", 0) for e in entries]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    max_score = max(scores) if scores else 0

    # Outcome dari ML CSV
    win = loss = pending = 0
    signal_details = []
    if os.path.exists(ml_csv):
        try:
            df_ml = pd.read_csv(ml_csv)
            ydf = df_ml[df_ml["timestamp"].str.startswith(yesterday)] if "timestamp" in df_ml.columns else pd.DataFrame()
            if not ydf.empty:
                win = len(ydf[ydf["outcome"] == "WIN"])
                loss = len(ydf[ydf["outcome"] == "LOSS"])
                pending = len(ydf[ydf["outcome"] == "PENDING"])
                for _, row in ydf.iterrows():
                    signal_details.append(row.to_dict())
        except Exception:
            pass

    # Cumulative ML
    total_labeled = 0
    overall_wr = 0
    if os.path.exists(ml_csv):
        try:
            df_all = pd.read_csv(ml_csv)
            df_done = df_all[df_all["outcome"].isin(["WIN", "LOSS"])]
            total_labeled = len(df_done)
            if total_labeled > 0:
                overall_wr = round(len(df_done[df_done["outcome"] == "WIN"]) / total_labeled * 100, 1)
        except Exception:
            pass

    total_outcomes = win + loss + pending
    wr_str = str(round(win / (win + loss) * 100, 1)) + "%" if (win + loss) > 0 else "N/A"

    nl = chr(10)
    lines = [
        "[NEXUS v2.0] DAILY REPORT " + yesterday,
        "",
        "SCAN SUMMARY",
        "Total scans : " + str(len(entries)),
        "Signals     : " + str(len(signals)),
        "Rejected    : " + str(len(waits)),
        "Avg score   : " + str(avg_score) + " | Max: " + str(max_score),
        "Bias: BULL=" + str(biases.get("BULLISH", 0)) + " BEAR=" + str(biases.get("BEARISH", 0)) + " NEU=" + str(biases.get("NEUTRAL", 0)),
        "Session: ASIA=" + str(sessions.get("ASIA", 0)) + " LDN=" + str(sessions.get("LONDON", 0)) + " NY=" + str(sessions.get("NEWYORK", 0)),
        "Regime: " + " ".join([k + "=" + str(v) for k, v in regimes.most_common(3)]),
    ]

    # Top rejection reasons
    if reject_reasons:
        lines += ["", "TOP REJECTION REASONS"]
        for reason, count in reject_reasons.most_common(4):
            pct = round(count / len(waits) * 100, 1) if waits else 0
            lines.append(str(count) + "x (" + str(pct) + "%) " + reason)

    # Top penalties
    if penalty_sources:
        lines += ["", "TOP PENALTIES"]
        for pen, count in penalty_sources.most_common(3):
            lines.append(str(count) + "x " + pen[:35])

    # Signals detail
    if signal_details:
        lines += ["", "SIGNALS HARI INI"]
        for i, sig in enumerate(signal_details[:5], 1):
            outcome = sig.get("outcome", "PENDING")
            outcome_str = "WIN" if outcome == "WIN" else "LOSS" if outcome == "LOSS" else "PENDING"
            lines.append(str(i) + ". " + str(sig.get("symbol", "")) + " [" + str(sig.get("grade", "")) + "] Score=" + str(sig.get("score", "")))
            lines.append("   Bias=" + str(sig.get("direction", "")) + " Regime=" + str(sig.get("regime", "")))
            lines.append("   Entry=" + str(sig.get("entry_price", "")) + " SL=" + str(sig.get("sl_price", "")) + " TP=" + str(sig.get("tp_price", "")))
            lines.append("   Outcome: " + outcome_str)
            if sig.get("candles_to_outcome"):
                lines.append("   Duration: " + str(sig.get("candles_to_outcome", "")) + " candles")
    elif signals:
        lines += ["", "SIGNALS HARI INI"]
        for e in signals[:3]:
            lines.append("- " + e.get("symbol", "") + " Score=" + str(e.get("score", "")) + " [" + e.get("grade", "") + "] " + e.get("bias", ""))
            br = e.get("bias_reason", {})
            if br:
                reasons = []
                if br.get("choch_detected"): reasons.append("CHoCH " + str(br.get("choch_direction", "")))
                if br.get("pdl_swept") and br.get("pdl_rejected"): reasons.append("PDL swept+rejected")
                if br.get("pdh_swept") and br.get("pdh_rejected"): reasons.append("PDH swept+rejected")
                if br.get("cvd_signal") != "NEUTRAL": reasons.append("CVD=" + str(br.get("cvd_signal", "")))
                if br.get("fng_value") and int(br.get("fng_value", 50)) < 30: reasons.append("FNG=" + str(br.get("fng_value", "")) + "(FEAR)")
                if reasons:
                    lines.append("  Alasan: " + ", ".join(reasons))
            sb = e.get("score_breakdown", {})
            if sb:
                lines.append("  T0=" + str(sb.get("t0", 0)) + " T1=" + str(sb.get("t1", 0)) + " T2=" + str(sb.get("t2", 0)))
                pens = sb.get("penalties", [])
                if pens:
                    lines.append("  Penalty: " + ", ".join([p["source"][:20] for p in pens]))

    # Outcome summary
    lines += [
        "",
        "OUTCOME",
        "WIN     : " + str(win) + " WR=" + wr_str,
        "LOSS    : " + str(loss),
        "PENDING : " + str(pending),
        "",
        "ML DATA PROGRESS",
        "Labeled : " + str(total_labeled) + "/200 (" + str(round(total_labeled / 200 * 100, 1)) + "%)",
        "Overall WR: " + str(overall_wr) + "%",
    ]

    msg = nl.join(lines)
    telegram_notifier.send(msg)
    return msg
