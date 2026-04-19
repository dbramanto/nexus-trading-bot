"""
NEXUS v2.0 - P1 Candle Pattern Detector
Deteksi pola candlestick yang paling reliable di crypto M15.
Tidak butuh API call — cukup dari OHLCV DataFrame.
Hanya pola yang statistically proven di crypto futures:
Engulfing, Pin Bar, Inside Bar, Doji at key level.
"""
import logging
import pandas as pd
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)


class CandlePattern(BaseAnalyst):

    @property
    def name(self): return "candle_pattern"
    @property
    def category(self): return "context"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 5

    def __init__(self, wick_ratio=0.6, engulf_pct=0.5):
        self.wick_ratio = wick_ratio
        self.engulf_pct = engulf_pct

    def analyze(self, df, config=None):
        if len(df) < 3:
            return self._empty()

        last = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3]

        total_range = last["high"] - last["low"]
        if total_range == 0:
            return self._empty()

        body = abs(last["close"] - last["open"])
        upper_wick = last["high"] - max(last["open"], last["close"])
        lower_wick = min(last["open"], last["close"]) - last["low"]
        body_pct = body / total_range
        upper_wick_pct = upper_wick / total_range
        lower_wick_pct = lower_wick / total_range

        bull_candle = last["close"] > last["open"]
        bear_candle = last["close"] < last["open"]

        prev_range = prev["high"] - prev["low"]
        prev_body = abs(prev["close"] - prev["open"])
        prev_bull = prev["close"] > prev["open"]
        prev_bear = prev["close"] < prev["open"]

        patterns = []

        # 1. Bullish Engulfing
        if (bull_candle and prev_bear and
            last["close"] > prev["open"] and
            last["open"] < prev["close"] and
            body > prev_body * self.engulf_pct):
            patterns.append("BULLISH_ENGULFING")

        # 2. Bearish Engulfing
        if (bear_candle and prev_bull and
            last["close"] < prev["open"] and
            last["open"] > prev["close"] and
            body > prev_body * self.engulf_pct):
            patterns.append("BEARISH_ENGULFING")

        # 3. Bullish Pin Bar (Hammer)
        if (lower_wick_pct >= self.wick_ratio and
            upper_wick_pct <= 0.2 and
            last["close"] > (last["high"] + last["low"]) / 2):
            patterns.append("BULLISH_PIN_BAR")

        # 4. Bearish Pin Bar (Shooting Star)
        if (upper_wick_pct >= self.wick_ratio and
            lower_wick_pct <= 0.2 and
            last["close"] < (last["high"] + last["low"]) / 2):
            patterns.append("BEARISH_PIN_BAR")

        # 5. Inside Bar (konsolidasi, potential breakout)
        if (last["high"] <= prev["high"] and
            last["low"] >= prev["low"]):
            patterns.append("INSIDE_BAR")

        # 6. Doji (indecision — penting di key level)
        if body_pct < 0.1 and total_range > 0:
            patterns.append("DOJI")

        # 7. Bullish Marubozu (strong momentum, no wick)
        if (bull_candle and
            upper_wick_pct < 0.05 and
            lower_wick_pct < 0.05 and
            body_pct > 0.9):
            patterns.append("BULLISH_MARUBOZU")

        # 8. Bearish Marubozu
        if (bear_candle and
            upper_wick_pct < 0.05 and
            lower_wick_pct < 0.05 and
            body_pct > 0.9):
            patterns.append("BEARISH_MARUBOZU")

        # Determine primary signal
        bullish_patterns = [p for p in patterns if "BULLISH" in p]
        bearish_patterns = [p for p in patterns if "BEARISH" in p]
        neutral_patterns = [p for p in patterns if p in ("INSIDE_BAR", "DOJI")]

        if bullish_patterns:
            primary = bullish_patterns[0]
            signal = "BULLISH"
        elif bearish_patterns:
            primary = bearish_patterns[0]
            signal = "BEARISH"
        elif neutral_patterns:
            primary = neutral_patterns[0]
            signal = "NEUTRAL"
        else:
            primary = None
            signal = "NEUTRAL"

        # Pattern strength
        strong = ["BULLISH_ENGULFING", "BEARISH_ENGULFING",
                  "BULLISH_MARUBOZU", "BEARISH_MARUBOZU"]
        medium = ["BULLISH_PIN_BAR", "BEARISH_PIN_BAR"]
        strength = "STRONG" if primary in strong else "MEDIUM" if primary in medium else "WEAK"

        return {
            "patterns_detected": patterns,
            "primary_pattern": primary,
            "pattern_signal": signal,
            "pattern_strength": strength,
            "body_pct": round(body_pct, 3),
            "upper_wick_pct": round(upper_wick_pct, 3),
            "lower_wick_pct": round(lower_wick_pct, 3),
            "is_bullish_candle": bull_candle,
            "is_bearish_candle": bear_candle,
        }

    def _empty(self):
        return {
            "patterns_detected": [],
            "primary_pattern": None,
            "pattern_signal": "NEUTRAL",
            "pattern_strength": "WEAK",
            "body_pct": 0,
            "upper_wick_pct": 0,
            "lower_wick_pct": 0,
            "is_bullish_candle": False,
            "is_bearish_candle": False,
        }
