"""
NEXUS v2.0 - P1 FVG Detector
"""
import logging
import pandas as pd
from typing import Dict, List
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)

class FVGDetector(BaseAnalyst):

    @property
    def name(self): return "fvg_detector"
    @property
    def category(self): return "ict"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 10

    def __init__(self, min_gap_pct=0.15, max_lookback=30):
        self.min_gap_pct = min_gap_pct
        self.max_lookback = max_lookback

    def analyze(self, df, config=None):
        fvgs = self._detect_all(df)
        bullish = [f for f in fvgs if f["type"] == "BULLISH"]
        bearish = [f for f in fvgs if f["type"] == "BEARISH"]
        nearest = self._get_nearest(fvgs, df["close"].iloc[-1])
        return {
            "fvg_count": len(fvgs),
            "fvg_bullish_count": len(bullish),
            "fvg_bearish_count": len(bearish),
            "fvg_present": len(fvgs) > 0,
            "fvg_nearest_type": nearest.get("type") if nearest else None,
            "fvg_nearest_top": nearest.get("top") if nearest else None,
            "fvg_nearest_bottom": nearest.get("bottom") if nearest else None,
            "fvg_nearest_quality": nearest.get("quality") if nearest else None,
            "fvg_list": fvgs[:5],
        }

    def _detect_all(self, df):
        fvgs = []
        lookback = min(self.max_lookback, len(df) - 2)
        for i in range(len(df) - 3, len(df) - 3 - lookback, -1):
            if i < 0: break
            c0 = df.iloc[i]
            c1 = df.iloc[i + 1]
            c2 = df.iloc[i + 2]
            bf = self._bullish_fvg(c0, c1, c2)
            if bf: fvgs.append(bf)
            brf = self._bearish_fvg(c0, c1, c2)
            if brf: fvgs.append(brf)
        return fvgs

    def _bullish_fvg(self, c0, c1, c2):
        gap = c2["low"] - c0["high"]
        if gap <= 0: return None
        mid = (c0["high"] + c2["low"]) / 2
        if mid == 0: return None
        gap_pct = (gap / mid) * 100
        if gap_pct < self.min_gap_pct: return None
        return {
            "type": "BULLISH",
            "top": round(c2["low"], 4),
            "bottom": round(c0["high"], 4),
            "gap_pct": round(gap_pct, 3),
            "quality": "HIGH" if gap_pct > 0.5 else "MEDIUM" if gap_pct > 0.25 else "LOW",
            "filled": False,
        }

    def _bearish_fvg(self, c0, c1, c2):
        gap = c0["low"] - c2["high"]
        if gap <= 0: return None
        mid = (c0["low"] + c2["high"]) / 2
        if mid == 0: return None
        gap_pct = (gap / mid) * 100
        if gap_pct < self.min_gap_pct: return None
        return {
            "type": "BEARISH",
            "top": round(c0["low"], 4),
            "bottom": round(c2["high"], 4),
            "gap_pct": round(gap_pct, 3),
            "quality": "HIGH" if gap_pct > 0.5 else "MEDIUM" if gap_pct > 0.25 else "LOW",
            "filled": False,
        }

    def _get_nearest(self, fvgs, price):
        if not fvgs: return None
        return min(fvgs, key=lambda f: abs(((f["top"] + f["bottom"]) / 2) - price))
