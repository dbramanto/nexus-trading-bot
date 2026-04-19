"""
NEXUS v2.0 - P1 Funding Rate
Orderflow module — requires binance_client injection.
"""
import logging
from typing import Dict, Optional
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)

class FundingRate(BaseAnalyst):

    @property
    def name(self): return "funding_rate"
    @property
    def category(self): return "orderflow"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 1

    def __init__(self, extreme_pos=0.1, extreme_neg=-0.1):
        self.extreme_pos = extreme_pos
        self.extreme_neg = extreme_neg
        self._binance_client = None
        self._symbol = None

    def set_context(self, symbol: str, binance_client):
        self._symbol = symbol
        self._binance_client = binance_client

    def analyze(self, df, config=None):
        if self._binance_client is None or self._symbol is None:
            return self._neutral()
        if config and getattr(getattr(config, 'backtest', None), 'is_backtest', False):
            return self._neutral()
        if config and getattr(getattr(config, "backtest", None), "is_backtest", False):
            return self._neutral()


        try:
            data = self._binance_client.get_funding_rate(self._symbol, limit=10)
            if not data:
                return self._neutral()

            latest = data[-1]
            fr_raw = float(latest["fundingRate"])
            fr_pct = fr_raw * 100

            avg_fr = sum(float(d["fundingRate"]) * 100 for d in data) / len(data)

            if fr_pct >= self.extreme_pos: sentiment = "EXTREME_BEARISH"
            elif fr_pct >= 0.05: sentiment = "BULLISH_CROWDED"
            elif fr_pct <= self.extreme_neg: sentiment = "EXTREME_BULLISH"
            elif fr_pct <= -0.05: sentiment = "BEARISH_CROWDED"
            else: sentiment = "NEUTRAL"

            is_extreme = abs(fr_pct) >= abs(self.extreme_pos)

            return {
                "funding_rate": round(fr_pct, 6),
                "funding_avg": round(avg_fr, 6),
                "sentiment": sentiment,
                "is_extreme": is_extreme,
                "contrarian_bias": "BULLISH" if fr_pct >= self.extreme_pos else
                                   "BEARISH" if fr_pct <= self.extreme_neg else "NEUTRAL",
            }
        except Exception as e:
            logger.error(f"FundingRate error: {e}")
            return self._neutral()

    def _neutral(self):
        return {
            "funding_rate": 0.0,
            "funding_avg": 0.0,
            "sentiment": "NEUTRAL",
            "is_extreme": False,
            "contrarian_bias": "NEUTRAL",
        }
