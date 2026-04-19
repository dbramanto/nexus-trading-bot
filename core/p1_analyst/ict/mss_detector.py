"""
NEXUS v2.0 - P1 MSS Detector (Market Structure Shift)
Crypto-native: deteksi BOS dan CHoCH untuk menentukan kapan
struktur market benar-benar berubah arah.

BOS  (Break of Structure) = konfirmasi trend berlanjut
CHoCH (Change of Character) = sinyal awal trend berbalik — ini yang paling penting

Di crypto M15, CHoCH adalah entry trigger terkuat karena menunjukkan
institusi mulai akumulasi/distribusi arah baru.
"""
import logging
import pandas as pd
import numpy as np
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)


class MSSDetector(BaseAnalyst):

    @property
    def name(self): return "mss_detector"
    @property
    def category(self): return "ict"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 30

    def __init__(self, swing_lookback=5, min_swing_pct=0.3):
        self.swing_lookback = swing_lookback
        self.min_swing_pct = min_swing_pct

    def analyze(self, df, config=None):
        swings = self._find_swings(df)
        if len(swings) < 4:
            return self._empty()

        structure = self._determine_structure(swings)
        bos = self._detect_bos(df, swings, structure)
        choch = self._detect_choch(df, swings, structure)

        last_swing_high = max((s["price"] for s in swings if s["type"] == "HIGH"), default=None)
        last_swing_low = min((s["price"] for s in swings if s["type"] == "LOW"), default=None)

        signal_strength = 0
        if choch["detected"]: signal_strength = 3
        elif bos["detected"]: signal_strength = 2

        return {
            "mss_structure": structure,
            "bos_detected": bos["detected"],
            "bos_direction": bos["direction"],
            "choch_detected": choch["detected"],
            "choch_direction": choch["direction"],
            "choch_strength": choch.get("strength", "NONE"),
            "last_swing_high": round(last_swing_high, 4) if last_swing_high else None,
            "last_swing_low": round(last_swing_low, 4) if last_swing_low else None,
            "signal_strength": signal_strength,
            "swing_count": len(swings),
        }

    def _find_swings(self, df):
        swings = []
        n = self.swing_lookback
        for i in range(n, len(df) - n):
            high = df["high"].iloc[i]
            low = df["low"].iloc[i]
            left_highs = df["high"].iloc[i-n:i]
            right_highs = df["high"].iloc[i+1:i+n+1]
            left_lows = df["low"].iloc[i-n:i]
            right_lows = df["low"].iloc[i+1:i+n+1]

            if high >= left_highs.max() and high >= right_highs.max():
                swings.append({"type": "HIGH", "price": high, "idx": i})

            if low <= left_lows.min() and low <= right_lows.min():
                swings.append({"type": "LOW", "price": low, "idx": i})

        swings.sort(key=lambda x: x["idx"])
        return swings[-10:]

    def _determine_structure(self, swings):
        highs = [s for s in swings if s["type"] == "HIGH"]
        lows = [s for s in swings if s["type"] == "LOW"]

        if len(highs) < 2 or len(lows) < 2:
            return "UNDEFINED"

        hh = highs[-1]["price"] > highs[-2]["price"]
        hl = lows[-1]["price"] > lows[-2]["price"]
        lh = highs[-1]["price"] < highs[-2]["price"]
        ll = lows[-1]["price"] < lows[-2]["price"]

        if hh and hl: return "BULLISH"
        if lh and ll: return "BEARISH"
        if hh and ll: return "RANGING"
        if lh and hl: return "RANGING"
        return "UNDEFINED"

    def _detect_bos(self, df, swings, structure):
        price = df["close"].iloc[-1]
        highs = [s for s in swings if s["type"] == "HIGH"]
        lows = [s for s in swings if s["type"] == "LOW"]

        if structure == "BULLISH" and highs:
            prev_high = highs[-1]["price"]
            if price > prev_high:
                return {"detected": True, "direction": "BULLISH", "level": prev_high}

        if structure == "BEARISH" and lows:
            prev_low = lows[-1]["price"]
            if price < prev_low:
                return {"detected": True, "direction": "BEARISH", "level": prev_low}

        return {"detected": False, "direction": None}

    def _detect_choch(self, df, swings, structure):
        price = df["close"].iloc[-1]
        highs = [s for s in swings if s["type"] == "HIGH"]
        lows = [s for s in swings if s["type"] == "LOW"]

        # CHoCH: struktur BULLISH tapi harga break swing low terbaru
        if structure == "BULLISH" and lows:
            last_low = lows[-1]["price"]
            if price < last_low:
                swing_range = highs[-1]["price"] - last_low if highs else 1
                break_pct = (last_low - price) / last_low * 100
                strength = "STRONG" if break_pct > 0.5 else "WEAK"
                return {
                    "detected": True,
                    "direction": "BEARISH",
                    "level": last_low,
                    "strength": strength
                }

        # CHoCH: struktur BEARISH tapi harga break swing high terbaru
        if structure == "BEARISH" and highs:
            last_high = highs[-1]["price"]
            if price > last_high:
                break_pct = (price - last_high) / last_high * 100
                strength = "STRONG" if break_pct > 0.5 else "WEAK"
                return {
                    "detected": True,
                    "direction": "BULLISH",
                    "level": last_high,
                    "strength": strength
                }

        return {"detected": False, "direction": None, "strength": "NONE"}

    def _empty(self):
        return {
            "mss_structure": "UNDEFINED",
            "bos_detected": False,
            "bos_direction": None,
            "choch_detected": False,
            "choch_direction": None,
            "choch_strength": "NONE",
            "last_swing_high": None,
            "last_swing_low": None,
            "signal_strength": 0,
            "swing_count": 0,
        }
