"""
NEXUS v2.0 - P1 Fear & Greed Index
Crypto-native sentiment indicator dari alternative.me API.
Free, tidak butuh API key.

Extreme Fear (0-25)  : pasar oversold sentiment, contrarian BULLISH
Fear (26-45)         : cautious, seller dominan
Neutral (46-55)      : balanced
Greed (56-75)        : momentum bullish, mulai waspada
Extreme Greed (76+)  : pasar overbought sentiment, contrarian BEARISH
"""
import logging
import requests
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)

FNG_URL = "https://api.alternative.me/fng/?limit=2"


class FearGreedIndex(BaseAnalyst):

    @property
    def name(self): return "fear_greed_index"
    @property
    def category(self): return "context"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 1

    def __init__(self):
        self._cache = None
        self._cache_time = 0

    def analyze(self, df, config=None):
        if config and getattr(getattr(config, "backtest", None), "is_backtest", False):
            return self._neutral()
        import time
        now = time.time()
        # Cache 1 jam — FNG tidak berubah tiap candle
        if self._cache and (now - self._cache_time) < 3600:
            return self._cache
        try:
            resp = requests.get(FNG_URL, timeout=5)
            if resp.status_code != 200:
                return self._neutral()

            data = resp.json().get("data", [])
            if not data:
                return self._neutral()

            current = data[0]
            value = int(current["value"])
            classification = current["value_classification"]

            prev_value = int(data[1]["value"]) if len(data) > 1 else value
            change = value - prev_value

            if value <= 25:
                sentiment = "EXTREME_FEAR"
                bias = "BULLISH"
                strength = 3
            elif value <= 45:
                sentiment = "FEAR"
                bias = "BULLISH"
                strength = 1
            elif value <= 55:
                sentiment = "NEUTRAL"
                bias = "NEUTRAL"
                strength = 0
            elif value <= 75:
                sentiment = "GREED"
                bias = "BEARISH"
                strength = 1
            else:
                sentiment = "EXTREME_GREED"
                bias = "BEARISH"
                strength = 3

            trending = "UP" if change > 5 else "DOWN" if change < -5 else "STABLE"

            result = {
                "fng_value": value,
                "fng_classification": classification,
                "fng_sentiment": sentiment,
                "fng_bias": bias,
                "fng_strength": strength,
                "fng_prev_value": prev_value,
                "fng_change": change,
                "fng_trending": trending,
            }
            self._cache = result
            self._cache_time = now
            return result

        except Exception as e:
            logger.error(f"FearGreed error: {e}")
            result = self._neutral()
            self._cache = result
            self._cache_time = now
            return result

    def _neutral(self):
        return {
            "fng_value": 50,
            "fng_classification": "Neutral",
            "fng_sentiment": "NEUTRAL",
            "fng_bias": "NEUTRAL",
            "fng_strength": 0,
            "fng_prev_value": 50,
            "fng_change": 0,
            "fng_trending": "STABLE",
        }
