"""
NEXUS v2.0 - P1 Breakout Detector
"""
import logging
import pandas as pd
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)

class BreakoutDetector(BaseAnalyst):

    @property
    def name(self): return "breakout_detector"
    @property
    def category(self): return "ict"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 25

    def __init__(self, volume_multiplier=2.0, close_confirmation=True, volume_period=20):
        self.volume_multiplier = volume_multiplier
        self.close_confirmation = close_confirmation
        self.volume_period = volume_period

    def analyze(self, df, config=None):
        if config:
            self.volume_multiplier = config.indicators.breakout_volume_multiplier
            self.close_confirmation = config.indicators.breakout_close_confirmation

        avg_vol = df["volume"].tail(self.volume_period).mean()
        last = df.iloc[-1]
        prev = df.iloc[-2]

        high_20 = df["high"].tail(20).max()
        low_20 = df["low"].tail(20).min()

        bull_break = last["high"] > high_20
        bear_break = last["low"] < low_20

        if self.close_confirmation:
            bull_break = bull_break and last["close"] > high_20
            bear_break = bear_break and last["close"] < low_20

        vol_confirmed = last["volume"] >= avg_vol * self.volume_multiplier

        direction = None
        if bull_break and vol_confirmed: direction = "BULLISH"
        elif bear_break and vol_confirmed: direction = "BEARISH"

        vol_ratio = round(last["volume"] / avg_vol, 2) if avg_vol > 0 else 0

        return {
            "breakout_detected": direction is not None,
            "breakout_direction": direction,
            "volume_confirmed": vol_confirmed,
            "volume_ratio": vol_ratio,
            "range_high_20": round(high_20, 4),
            "range_low_20": round(low_20, 4),
        }
