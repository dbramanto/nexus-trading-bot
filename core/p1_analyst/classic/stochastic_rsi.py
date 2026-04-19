"""
NEXUS v2.0 - P1 Stochastic RSI
Note: RSI series dari BasicIndicators.get_rsi_series() — no duplication.
"""
import logging
import pandas as pd
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)

class StochasticRSI(BaseAnalyst):

    @property
    def name(self): return "stochastic_rsi"
    @property
    def category(self): return "classic"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 50

    def __init__(self, rsi_period=14, stoch_period=14, smooth_k=3, smooth_d=3):
        self.rsi_period = rsi_period
        self.stoch_period = stoch_period
        self.smooth_k = smooth_k
        self.smooth_d = smooth_d

    def analyze(self, df, config=None):
        rsi = self._calc_rsi(df)
        if len(rsi) < self.stoch_period:
            return {"stoch_k": None, "stoch_d": None, "stoch_signal": "NEUTRAL"}

        rsi_min = rsi.rolling(self.stoch_period).min()
        rsi_max = rsi.rolling(self.stoch_period).max()
        rng = rsi_max - rsi_min
        raw_k = ((rsi - rsi_min) / rng.replace(0, 1)) * 100

        k = raw_k.rolling(self.smooth_k).mean()
        d = k.rolling(self.smooth_d).mean()

        k_val = round(k.iloc[-1], 2) if pd.notna(k.iloc[-1]) else None
        d_val = round(d.iloc[-1], 2) if pd.notna(d.iloc[-1]) else None

        if k_val is None:
            return {"stoch_k": None, "stoch_d": None, "stoch_signal": "NEUTRAL"}

        overbought = k_val >= 80
        oversold = k_val <= 20
        cross = "BULLISH" if k_val > d_val else "BEARISH" if k_val < d_val else "NEUTRAL" if d_val else "NEUTRAL"

        if oversold: signal = "OVERSOLD"
        elif overbought: signal = "OVERBOUGHT"
        else: signal = "NEUTRAL"

        return {
            "stoch_k": k_val,
            "stoch_d": d_val,
            "stoch_signal": signal,
            "stoch_cross": cross,
            "stoch_overbought": overbought,
            "stoch_oversold": oversold,
        }

    def _calc_rsi(self, df):
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(span=self.rsi_period, adjust=False).mean()
        avg_loss = loss.ewm(span=self.rsi_period, adjust=False).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
