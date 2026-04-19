"""
NEXUS v2.0 - P1 Liquidity Sweeps
"""
import logging
import pandas as pd
import numpy as np
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)

class LiquiditySweeps(BaseAnalyst):

    @property
    def name(self): return "liquidity_sweeps"
    @property
    def category(self): return "ict"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 30

    def __init__(self, lookback=20, sweep_threshold=0.2):
        self.lookback = lookback
        self.sweep_threshold = sweep_threshold

    def analyze(self, df, config=None):
        swing_highs = self._swing_highs(df)
        swing_lows = self._swing_lows(df)
        bull_sweep = self._check_sweep(df, swing_lows, "bullish")
        bear_sweep = self._check_sweep(df, swing_highs, "bearish")
        is_sweep = bull_sweep["swept"] or bear_sweep["swept"]
        direction = None
        if bull_sweep["swept"]: direction = "BULLISH"
        elif bear_sweep["swept"]: direction = "BEARISH"
        return {
            "sweep_detected": is_sweep,
            "sweep_direction": direction,
            "bull_sweep": bull_sweep["swept"],
            "bear_sweep": bear_sweep["swept"],
            "bull_sweep_level": bull_sweep.get("level"),
            "bear_sweep_level": bear_sweep.get("level"),
            "swing_highs": swing_highs[:3],
            "swing_lows": swing_lows[:3],
            "idm_level": bull_sweep.get("level") or bear_sweep.get("level"),
        }

    def _swing_highs(self, df):
        highs = []
        for i in range(2, len(df) - 2):
            if df["high"].iloc[i] == df["high"].iloc[i-2:i+3].max():
                highs.append(round(df["high"].iloc[i], 4))
        return highs[-5:]

    def _swing_lows(self, df):
        lows = []
        for i in range(2, len(df) - 2):
            if df["low"].iloc[i] == df["low"].iloc[i-2:i+3].min():
                lows.append(round(df["low"].iloc[i], 4))
        return lows[-5:]

    def _check_sweep(self, df, levels, direction):
        if not levels: return {"swept": False}
        last = df.iloc[-1]
        prev = df.iloc[-2]
        if direction == "bullish":
            level = min(levels)
            swept = last["low"] < level and last["close"] > level
            return {"swept": swept, "level": round(level, 4) if swept else None}
        else:
            level = max(levels)
            swept = last["high"] > level and last["close"] < level
            return {"swept": swept, "level": round(level, 4) if swept else None}
