"""
NEXUS v2.0 - P1 MACD Indicator
"""
import logging
import pandas as pd
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)

class MACDIndicator(BaseAnalyst):

    @property
    def name(self): return "macd_indicator"
    @property
    def category(self): return "classic"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 35

    def __init__(self, fast=12, slow=26, signal=9):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def analyze(self, df, config=None):
        close = df["close"]
        fast_ema = close.ewm(span=self.fast, adjust=False).mean()
        slow_ema = close.ewm(span=self.slow, adjust=False).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=self.signal, adjust=False).mean()
        histogram = macd_line - signal_line

        macd_val = round(macd_line.iloc[-1], 6)
        signal_val = round(signal_line.iloc[-1], 6)
        hist_val = round(histogram.iloc[-1], 6)
        hist_prev = round(histogram.iloc[-2], 6) if len(histogram) > 1 else 0

        cross = "BULLISH" if macd_val > signal_val else "BEARISH"
        zero_cross = "ABOVE" if macd_val > 0 else "BELOW"
        momentum = "INCREASING" if abs(hist_val) > abs(hist_prev) else "DECREASING"

        return {
            "macd_line": macd_val,
            "signal_line": signal_val,
            "histogram": hist_val,
            "cross": cross,
            "zero_cross": zero_cross,
            "momentum": momentum,
        }
