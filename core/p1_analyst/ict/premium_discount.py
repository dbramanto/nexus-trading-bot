"""
NEXUS v2.0 - P1 Premium Discount Zones
"""
import logging
import pandas as pd
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)

class PremiumDiscountZones(BaseAnalyst):

    @property
    def name(self): return "premium_discount"
    @property
    def category(self): return "ict"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 20

    def __init__(self, premium_threshold=0.618, discount_threshold=0.382, lookback=20):
        self.premium_threshold = premium_threshold
        self.discount_threshold = discount_threshold
        self.lookback = lookback

    def analyze(self, df, config=None):
        if config:
            self.premium_threshold = config.indicators.premium_zone_threshold
            self.discount_threshold = config.indicators.discount_zone_threshold
        data = df.tail(self.lookback)
        range_high = data["high"].max()
        range_low = data["low"].min()
        range_size = range_high - range_low
        if range_size == 0:
            return {"price_zone": "EQUILIBRIUM", "zone_score": 0}

        premium_level = range_low + (range_size * self.premium_threshold)
        discount_level = range_low + (range_size * self.discount_threshold)
        midpoint = range_low + (range_size * 0.5)
        price = df["close"].iloc[-1]

        fib_pct = (price - range_low) / range_size

        if fib_pct >= self.premium_threshold:
            zone = "PREMIUM"
        elif fib_pct <= self.discount_threshold:
            zone = "DISCOUNT"
        else:
            zone = "EQUILIBRIUM"

        return {
            "price_zone": zone,
            "range_high": round(range_high, 4),
            "range_low": round(range_low, 4),
            "premium_level": round(premium_level, 4),
            "discount_level": round(discount_level, 4),
            "midpoint": round(midpoint, 4),
            "fib_position": round(fib_pct, 4),
        }
