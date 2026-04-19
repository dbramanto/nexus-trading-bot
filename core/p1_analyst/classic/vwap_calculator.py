"""
NEXUS v2.0 - P1 VWAP Calculator
"""
import logging
import pandas as pd
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)

class VWAPCalculator(BaseAnalyst):

    @property
    def name(self): return "vwap_calculator"
    @property
    def category(self): return "classic"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 10

    def __init__(self, session_reset_hour=0):
        self.session_reset_hour = session_reset_hour

    def analyze(self, df, config=None):
        tp = (df["high"] + df["low"] + df["close"]) / 3
        cum_tpv = (tp * df["volume"]).cumsum()
        cum_vol = df["volume"].cumsum()
        vwap = cum_tpv / cum_vol

        price = df["close"].iloc[-1]
        vwap_val = round(vwap.iloc[-1], 4)

        std = (tp - vwap).rolling(20).std().iloc[-1]
        upper1 = round(vwap_val + std, 4)
        lower1 = round(vwap_val - std, 4)
        upper2 = round(vwap_val + 2 * std, 4)
        lower2 = round(vwap_val - 2 * std, 4)

        if price > upper2: pos = "FAR_ABOVE"
        elif price > upper1: pos = "ABOVE"
        elif price > vwap_val: pos = "ABOVE_VWAP"
        elif price > lower1: pos = "BELOW_VWAP"
        elif price > lower2: pos = "BELOW"
        else: pos = "FAR_BELOW"

        diff_pct = round(((price - vwap_val) / vwap_val) * 100, 3)

        return {
            "vwap": vwap_val,
            "vwap_upper1": upper1,
            "vwap_lower1": lower1,
            "vwap_upper2": upper2,
            "vwap_lower2": lower2,
            "vwap_position": pos,
            "vwap_diff_pct": diff_pct,
        }
