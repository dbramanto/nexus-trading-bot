"""
NEXUS v2.0 NOTE: BB dipakai sebagai volatility context saja, bukan sinyal arah.

NEXUS v2.0 - P1 Bollinger Bands
"""
import logging
import pandas as pd
from typing import Dict
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)

class BollingerBands(BaseAnalyst):

    @property
    def name(self): return "bollinger_bands"
    @property
    def category(self): return "classic"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 30

    def __init__(self, period=20, std_dev=2.0):
        self.period = period
        self.std_dev = std_dev

    def analyze(self, df, config=None):
        middle = df["close"].rolling(window=self.period).mean()
        std = df["close"].rolling(window=self.period).std()
        upper = middle + (self.std_dev * std)
        lower = middle - (self.std_dev * std)

        price = df["close"].iloc[-1]
        cur_mid = middle.iloc[-1]
        cur_up = upper.iloc[-1]
        cur_low = lower.iloc[-1]

        band_width = (cur_up - cur_low) / cur_mid * 100
        percent_b = (price - cur_low) / (cur_up - cur_low) if (cur_up - cur_low) != 0 else 0.5

        if price > cur_up: position = "above_upper"
        elif price < cur_low: position = "below_lower"
        elif price > cur_mid: position = "upper_half"
        else: position = "lower_half"

        avg_bw = (upper - lower).iloc[-20:].mean() / middle.iloc[-20:].mean() * 100
        squeeze = band_width < avg_bw * 0.7
        expansion = band_width > avg_bw * 1.3

        return {
            "bb_upper": round(cur_up, 4),
            "bb_middle": round(cur_mid, 4),
            "bb_lower": round(cur_low, 4),
            "bb_width": round(band_width, 4),
            "bb_percent_b": round(percent_b, 4),
            "bb_position": position,
            "bb_squeeze": squeeze,
            "bb_expansion": expansion,
        }
