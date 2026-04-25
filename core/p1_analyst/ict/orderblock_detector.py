"""
NEXUS v2.0 - P1 Order Block Detector
"""
import logging
import pandas as pd
from typing import Dict, List
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)

class OrderBlockDetector(BaseAnalyst):

    @property
    def name(self): return "orderblock_detector"
    @property
    def category(self): return "ict"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 10

    def __init__(self, min_move_pct=1.5, min_move_candles=3, max_lookback=30):
        self.min_move_pct = min_move_pct
        self.min_move_candles = min_move_candles
        self.max_lookback = max_lookback

    def analyze(self, df, config=None):
        obs = self._detect_all(df)
        bullish = [o for o in obs if o["type"] == "BULLISH"]
        bearish = [o for o in obs if o["type"] == "BEARISH"]
        price = df["close"].iloc[-1]
        nearest = self._get_nearest(obs, price)
        return {
            "ob_count": len(obs),
            "ob_bullish_count": len(bullish),
            "ob_bearish_count": len(bearish),
            "ob_present": len(obs) > 0,
            "ob_nearest_type": nearest.get("type") if nearest else None,
            "ob_nearest_top": nearest.get("top") if nearest else None,
            "ob_nearest_bottom": nearest.get("bottom") if nearest else None,
            "ob_nearest_fresh": nearest.get("fresh") if nearest else None,
            "ob_list": obs[:5],
        }

    def _detect_all(self, df):
        obs = []
        lookback = min(self.max_lookback, len(df) - self.min_move_candles)
        for i in range(len(df) - 1, len(df) - 1 - lookback, -1):
            if i < self.min_move_candles: break
            bul = self._bullish_ob(df, i)
            if bul: obs.append(bul)
            ber = self._bearish_ob(df, i)
            if ber: obs.append(ber)
        return obs

    def _bullish_ob(self, df, i):
        if i < self.min_move_candles: return None
        c = df.iloc[i]
        if c["close"] >= c["open"]: return None
        move_start = i + 1
        move_end = min(i + 1 + self.min_move_candles, len(df))
        if move_end >= len(df): return None
        move = df.iloc[move_start:move_end]
        move_pct = ((move["close"].iloc[-1] - c["close"]) / c["close"]) * 100
        if move_pct < self.min_move_pct: return None
        # Freshness check: apakah harga sudah pernah masuk ke zona OB?
        ob_top = round(c["high"], 4)
        ob_bottom = round(c["low"], 4)
        future_candles = df.iloc[i+1:]
        tested = any(
            (row["low"] <= ob_top and row["high"] >= ob_bottom)
            for _, row in future_candles.iterrows()
        )
        return {
            "type": "BULLISH",
            "top": ob_top,
            "bottom": ob_bottom,
            "fresh": not tested,
            "strength": round(move_pct, 2),
        }

    def _bearish_ob(self, df, i):
        if i < self.min_move_candles: return None
        c = df.iloc[i]
        if c["close"] <= c["open"]: return None
        move_start = i + 1
        move_end = min(i + 1 + self.min_move_candles, len(df))
        if move_end >= len(df): return None
        move = df.iloc[move_start:move_end]
        move_pct = ((c["close"] - move["close"].iloc[-1]) / c["close"]) * 100
        if move_pct < self.min_move_pct: return None
        # Freshness check: apakah harga sudah pernah masuk ke zona OB?
        ob_top = round(c["high"], 4)
        ob_bottom = round(c["low"], 4)
        future_candles = df.iloc[i+1:]
        tested = any(
            (row["low"] <= ob_top and row["high"] >= ob_bottom)
            for _, row in future_candles.iterrows()
        )
        return {
            "type": "BEARISH",
            "top": ob_top,
            "bottom": ob_bottom,
            "fresh": not tested,
            "strength": round(move_pct, 2),
        }

    def _get_nearest(self, obs, price):
        if not obs: return None
        return min(obs, key=lambda o: abs(((o["top"] + o["bottom"]) / 2) - price))
