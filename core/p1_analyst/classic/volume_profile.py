"""
NEXUS v2.0 - P1 Volume Profile
"""
import logging
import pandas as pd
import numpy as np
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)

class VolumeProfile(BaseAnalyst):

    @property
    def name(self): return "volume_profile"
    @property
    def category(self): return "classic"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 20

    def __init__(self, num_bins=24, value_area_pct=0.70):
        self.num_bins = num_bins
        self.value_area_pct = value_area_pct

    def analyze(self, df, config=None):
        high = df["high"].max()
        low = df["low"].min()
        price_range = high - low
        if price_range == 0:
            return {"poc": df["close"].iloc[-1], "vah": high, "val": low, "price_zone": "EQUILIBRIUM"}

        bins = np.linspace(low, high, self.num_bins + 1)
        vol_by_bin = np.zeros(self.num_bins)

        bar_lows = df["low"].values
        bar_highs = df["high"].values
        bar_vols = df["volume"].values
        bar_ranges = bar_highs - bar_lows
        bar_ranges = np.where(bar_ranges == 0, 1, bar_ranges)
        for i in range(self.num_bins):
            bin_low = bins[i]
            bin_high = bins[i + 1]
            overlaps = np.maximum(0, np.minimum(bar_highs, bin_high) - np.maximum(bar_lows, bin_low))
            vol_by_bin[i] = np.sum(bar_vols * overlaps / bar_ranges)

        poc_idx = np.argmax(vol_by_bin)
        poc = round((bins[poc_idx] + bins[poc_idx + 1]) / 2, 4)

        total_vol = vol_by_bin.sum()
        target_vol = total_vol * self.value_area_pct
        sorted_idx = np.argsort(vol_by_bin)[::-1]
        acc_vol = 0
        va_bins = []
        for idx in sorted_idx:
            acc_vol += vol_by_bin[idx]
            va_bins.append(idx)
            if acc_vol >= target_vol:
                break

        vah = round(bins[max(va_bins) + 1], 4)
        val = round(bins[min(va_bins)], 4)

        price = df["close"].iloc[-1]
        midpoint = (high + low) / 2
        if price > midpoint * 1.003: zone = "PREMIUM"
        elif price < midpoint * 0.997: zone = "DISCOUNT"
        else: zone = "EQUILIBRIUM"

        return {
            "poc": poc,
            "vah": vah,
            "val": val,
            "price_zone": zone,
            "midpoint": round(midpoint, 4),
        }
