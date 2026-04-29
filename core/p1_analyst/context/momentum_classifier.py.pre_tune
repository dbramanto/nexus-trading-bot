"""
NEXUS v2.0 - P1 Momentum Classifier
Crypto-native: analisa momentum 5-10 candle terakhir.
Menggantikan Ichimoku sebagai penentu arah jangka pendek
dengan lag yang jauh lebih rendah — cocok untuk M15 crypto.
"""
import logging
import pandas as pd
import numpy as np
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)


class MomentumClassifier(BaseAnalyst):

    @property
    def name(self): return "momentum_classifier"
    @property
    def category(self): return "context"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 20

    def __init__(self, fast_bars=5, slow_bars=10, vol_bars=10):
        self.fast_bars = fast_bars
        self.slow_bars = slow_bars
        self.vol_bars = vol_bars

    def analyze(self, df, config=None):
        close = df["close"]
        volume = df["volume"]
        high = df["high"]
        low = df["low"]

        # 1. Price momentum
        fast_ret = (close.iloc[-1] - close.iloc[-self.fast_bars]) / close.iloc[-self.fast_bars] * 100
        slow_ret = (close.iloc[-1] - close.iloc[-self.slow_bars]) / close.iloc[-self.slow_bars] * 100

        # 2. Candle body momentum — berapa pct candle bullish dalam N bars
        recent = df.tail(self.fast_bars)
        bull_candles = sum(1 for _, r in recent.iterrows() if r["close"] > r["open"])
        bull_pct = bull_candles / self.fast_bars * 100

        # 3. Volume momentum — apakah volume naik seiring harga?
        avg_vol = volume.tail(self.vol_bars).mean()
        last_vol = volume.iloc[-1]
        vol_momentum = last_vol / avg_vol if avg_vol > 0 else 1.0

        # 4. Upper/lower wick analysis — rejection signal
        last = df.iloc[-1]
        body = abs(last["close"] - last["open"])
        total_range = last["high"] - last["low"]
        upper_wick = last["high"] - max(last["open"], last["close"])
        lower_wick = min(last["open"], last["close"]) - last["low"]

        upper_wick_pct = upper_wick / total_range * 100 if total_range > 0 else 0
        lower_wick_pct = lower_wick / total_range * 100 if total_range > 0 else 0

        # 5. Classify momentum
        if fast_ret > 0.3 and slow_ret > 0.5 and bull_pct >= 60:
            momentum = "STRONG_BULLISH"
            direction = "BULLISH"
            strength = 3
        elif fast_ret > 0.1 and bull_pct >= 50:
            momentum = "BULLISH"
            direction = "BULLISH"
            strength = 2
        elif fast_ret < -0.3 and slow_ret < -0.5 and bull_pct <= 40:
            momentum = "STRONG_BEARISH"
            direction = "BEARISH"
            strength = 3
        elif fast_ret < -0.1 and bull_pct <= 50:
            momentum = "BEARISH"
            direction = "BEARISH"
            strength = 2
        else:
            momentum = "NEUTRAL"
            direction = "NEUTRAL"
            strength = 0

        # 6. Rejection — upper wick besar di bullish momentum = bearish rejection
        rejection = None
        if upper_wick_pct > 40 and direction == "BULLISH":
            rejection = "BEARISH_REJECTION"
        elif lower_wick_pct > 40 and direction == "BEARISH":
            rejection = "BULLISH_REJECTION"

        return {
            "momentum": momentum,
            "momentum_direction": direction,
            "momentum_strength": strength,
            "fast_return_pct": round(fast_ret, 4),
            "slow_return_pct": round(slow_ret, 4),
            "bull_candle_pct": round(bull_pct, 1),
            "volume_momentum": round(vol_momentum, 2),
            "upper_wick_pct": round(upper_wick_pct, 1),
            "lower_wick_pct": round(lower_wick_pct, 1),
            "rejection_signal": rejection,
        }
