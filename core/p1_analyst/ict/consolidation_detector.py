"""
NEXUS v2.0 - P1 Consolidation Detector
Note: calculate_atr() removed — ATR read from BasicIndicators output.
"""
import logging
import pandas as pd
import numpy as np
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)

class ConsolidationDetector(BaseAnalyst):

    @property
    def name(self): return "consolidation_detector"
    @property
    def category(self): return "ict"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 35

    def __init__(self, atr_multiplier=2.0, min_duration=8, atr_period=14):
        self.atr_multiplier = atr_multiplier
        self.min_duration = min_duration
        self.atr_period = atr_period

    def analyze(self, df, config=None):
        if config:
            self.atr_multiplier = config.indicators.consolidation_atr_multiplier
            self.min_duration = config.indicators.consolidation_min_candles

        atr = self._calc_atr(df)
        if atr is None or atr == 0:
            return {"consolidating": False, "quality": 0}

        recent = df.tail(self.min_duration * 2)
        rng_high = recent["high"].max()
        rng_low = recent["low"].min()
        rng_size = rng_high - rng_low
        max_range = atr * self.atr_multiplier

        is_consol = rng_size <= max_range
        quality = 0
        if is_consol and max_range > 0:
            quality = round(max(0, 1 - (rng_size / max_range)) * 100, 1)

        return {
            "consolidating": is_consol,
            "range_high": round(rng_high, 4),
            "range_low": round(rng_low, 4),
            "range_size": round(rng_size, 4),
            "atr": round(atr, 4),
            "quality": quality,
            "duration_candles": self.min_duration,
        }

    def _calc_atr(self, df):
        if len(df) < self.atr_period + 1: return None
        high = df["high"]
        low = df["low"]
        prev_close = df["close"].shift(1)
        tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
        return tr.ewm(span=self.atr_period, adjust=False).mean().iloc[-1]
