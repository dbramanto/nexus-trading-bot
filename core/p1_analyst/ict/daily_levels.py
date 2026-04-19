"""
NEXUS v2.0 - P1 Daily Levels (PDH/PDL)
NEW MODULE - not in old NEXUS.
Detects Previous Day High/Low as key liquidity levels.
Critical for scalp-intra: institutions target these levels
for liquidity grabs before true directional move.
"""
import logging
import pandas as pd
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)

class DailyLevels(BaseAnalyst):

    @property
    def name(self): return "daily_levels"
    @property
    def category(self): return "ict"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 100

    def analyze(self, df, config=None):
        if "timestamp" in df.columns:
            df = df.copy()
            df["date"] = pd.to_datetime(df["timestamp"]).dt.date
        elif hasattr(df.index, "date"):
            df = df.copy()
            df["date"] = df.index.date
        else:
            return self._no_daily_data()

        dates = sorted(df["date"].unique())
        if len(dates) < 2:
            return self._no_daily_data()

        prev_date = dates[-2]
        prev_day = df[df["date"] == prev_date]

        pdh = round(prev_day["high"].max(), 4)
        pdl = round(prev_day["low"].min(), 4)
        price = df["close"].iloc[-1]

        above_pdh = price > pdh
        below_pdl = price < pdl
        in_range = not above_pdh and not below_pdl

        dist_pdh_pct = round(((price - pdh) / pdh) * 100, 4)
        dist_pdl_pct = round(((price - pdl) / pdl) * 100, 4)

        approaching_pdh = not above_pdh and dist_pdh_pct > -0.5
        approaching_pdl = not below_pdl and dist_pdl_pct < 0.5

        today_data = df[df["date"] == dates[-1]]
        pdh_swept = False
        pdl_swept = False
        pdh_rejected = False
        pdl_rejected = False

        if len(today_data) >= 2:
            today_high = today_data["high"].max()
            today_low = today_data["low"].min()
            last_close = today_data["close"].iloc[-1]

            pdh_swept = today_high > pdh and last_close < pdh
            pdl_swept = today_low < pdl and last_close > pdl

            if pdh_swept:
                recent = today_data.tail(3)
                pdh_rejected = recent["close"].iloc[-1] < pdh
            if pdl_swept:
                recent = today_data.tail(3)
                pdl_rejected = recent["close"].iloc[-1] > pdl

        if above_pdh: level_context = "ABOVE_PDH"
        elif below_pdl: level_context = "BELOW_PDL"
        elif approaching_pdh: level_context = "APPROACHING_PDH"
        elif approaching_pdl: level_context = "APPROACHING_PDL"
        else: level_context = "INSIDE_RANGE"

        return {
            "pdh": pdh,
            "pdl": pdl,
            "above_pdh": above_pdh,
            "below_pdl": below_pdl,
            "in_range": in_range,
            "dist_to_pdh_pct": dist_pdh_pct,
            "dist_to_pdl_pct": dist_pdl_pct,
            "approaching_pdh": approaching_pdh,
            "approaching_pdl": approaching_pdl,
            "pdh_swept": pdh_swept,
            "pdl_swept": pdl_swept,
            "pdh_rejected": pdh_rejected,
            "pdl_rejected": pdl_rejected,
            "level_context": level_context,
        }

    def _no_daily_data(self):
        return {
            "pdh": None, "pdl": None,
            "above_pdh": False, "below_pdl": False, "in_range": True,
            "dist_to_pdh_pct": None, "dist_to_pdl_pct": None,
            "approaching_pdh": False, "approaching_pdl": False,
            "pdh_swept": False, "pdl_swept": False,
            "pdh_rejected": False, "pdl_rejected": False,
            "level_context": "UNKNOWN",
        }
