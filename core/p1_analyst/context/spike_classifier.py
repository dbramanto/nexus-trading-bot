"""
NEXUS v2.0 - P1 Spike Classifier
NEW MODULE: Direction-aware spike detection.
Adapted from Pragya spike_detector concept but NOT a blind filter.
Classifies spikes as opportunity or threat based on context.
"""
import logging
import pandas as pd
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)

class SpikeClassifier(BaseAnalyst):

    @property
    def name(self): return "spike_classifier"
    @property
    def category(self): return "context"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 20

    def __init__(self, atr_multiplier=2.0, atr_period=14):
        self.atr_multiplier = atr_multiplier
        self.atr_period = atr_period

    def analyze(self, df, config=None):
        if config:
            self.atr_multiplier = config.indicators.spike_atr_multiplier

        atr = self._calc_atr(df)
        if atr is None or atr == 0:
            return {"spike_detected": False, "spike_type": None}

        last = df.iloc[-1]
        bar_range = last["high"] - last["low"]
        is_spike = bar_range > (atr * self.atr_multiplier)
        spike_magnitude = round(bar_range / atr, 2) if atr > 0 else 0

        if not is_spike:
            return {
                "spike_detected": False,
                "spike_magnitude": spike_magnitude,
                "spike_type": None,
                "spike_direction": None,
                "volume_confirmed": False,
                "spike_classification": "NORMAL",
            }

        avg_vol = df["volume"].tail(20).mean()
        vol_confirmed = last["volume"] > avg_vol * 1.5

        candle_body = last["close"] - last["open"]
        spike_direction = "UP" if candle_body > 0 else "DOWN"

        upper_wick = last["high"] - max(last["open"], last["close"])
        lower_wick = min(last["open"], last["close"]) - last["low"]
        rejected = upper_wick > bar_range * 0.4 or lower_wick > bar_range * 0.4

        if rejected and lower_wick > upper_wick:
            classification = "BULLISH_SWEEP_REJECTION"
        elif rejected and upper_wick > lower_wick:
            classification = "BEARISH_SWEEP_REJECTION"
        elif vol_confirmed and spike_direction == "UP":
            classification = "BULLISH_BREAKOUT"
        elif vol_confirmed and spike_direction == "DOWN":
            classification = "BEARISH_BREAKOUT"
        else:
            classification = "NOISE_SPIKE"

        return {
            "spike_detected": True,
            "spike_magnitude": spike_magnitude,
            "spike_direction": spike_direction,
            "volume_confirmed": vol_confirmed,
            "spike_classification": classification,
            "is_rejection": rejected,
            "is_opportunity": classification in (
                "BULLISH_SWEEP_REJECTION", "BEARISH_SWEEP_REJECTION",
                "BULLISH_BREAKOUT", "BEARISH_BREAKOUT"
            ),
            "is_noise": classification == "NOISE_SPIKE",
        }

    def _calc_atr(self, df):
        if len(df) < self.atr_period + 1: return None
        high = df["high"]
        low = df["low"]
        prev_close = df["close"].shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        return tr.ewm(span=self.atr_period, adjust=False).mean().iloc[-1]
