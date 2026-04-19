"""
NEXUS v2.0 - P1 Ichimoku Cloud
"""
import logging
import pandas as pd
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)

class IchimokuCloud(BaseAnalyst):

    @property
    def name(self): return "ichimoku_cloud"
    @property
    def category(self): return "classic"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 80

    def __init__(self, tenkan=9, kijun=26, senkou_b=52, displacement=26):
        self.tenkan = tenkan
        self.kijun = kijun
        self.senkou_b = senkou_b
        self.displacement = displacement

    def analyze(self, df, config=None):
        tenkan = self._midline(df, self.tenkan)
        kijun = self._midline(df, self.kijun)
        senkou_a = ((tenkan + kijun) / 2).shift(self.displacement)
        senkou_b = self._midline(df, self.senkou_b).shift(self.displacement)
        chikou = df["close"].shift(-self.displacement)

        price = df["close"].iloc[-1]
        t_val = tenkan.iloc[-1]
        k_val = kijun.iloc[-1]
        sa_val = senkou_a.iloc[-1]
        sb_val = senkou_b.iloc[-1]

        above_cloud = price > max(sa_val, sb_val) if pd.notna(sa_val) and pd.notna(sb_val) else None
        below_cloud = price < min(sa_val, sb_val) if pd.notna(sa_val) and pd.notna(sb_val) else None
        in_cloud = not above_cloud and not below_cloud if above_cloud is not None else None

        tk_cross = "BULLISH" if t_val > k_val else "BEARISH" if t_val < k_val else "NEUTRAL"

        cloud_color = "GREEN" if pd.notna(sa_val) and pd.notna(sb_val) and sa_val > sb_val else "RED"

        if above_cloud: bias = "BULLISH"
        elif below_cloud: bias = "BEARISH"
        else: bias = "NEUTRAL"

        return {
            "tenkan": round(t_val, 4) if pd.notna(t_val) else None,
            "kijun": round(k_val, 4) if pd.notna(k_val) else None,
            "senkou_a": round(sa_val, 4) if pd.notna(sa_val) else None,
            "senkou_b": round(sb_val, 4) if pd.notna(sb_val) else None,
            "tk_cross": tk_cross,
            "above_cloud": above_cloud,
            "below_cloud": below_cloud,
            "in_cloud": in_cloud,
            "cloud_color": cloud_color,
            "ichimoku_bias": bias,
        }

    def _midline(self, df, period):
        high = df["high"].rolling(period).max()
        low = df["low"].rolling(period).min()
        return (high + low) / 2
