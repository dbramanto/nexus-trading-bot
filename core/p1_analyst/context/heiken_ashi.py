"""
NEXUS v2.0 - P1 Heiken Ashi Calculator
Hitung nilai HA dari OHLC biasa dan tentukan arah + kekuatan sinyal.
"""
import pandas as pd
import numpy as np
from core.p1_analyst.base_analyst import BaseAnalyst


class HeikenAshiCalculator(BaseAnalyst):
    name = "heiken_ashi"
    category = "context"
    is_implemented = True

    def analyze(self, df: pd.DataFrame, config=None) -> dict:
        if len(df) < 3:
            return self._neutral()

        # Hitung HA values
        ha_close = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
        ha_open = ha_close.copy()
        for i in range(1, len(df)):
            ha_open.iloc[i] = (ha_open.iloc[i-1] + ha_close.iloc[i-1]) / 2
        ha_high = pd.concat([df["high"], ha_open, ha_close], axis=1).max(axis=1)
        ha_low = pd.concat([df["low"], ha_open, ha_close], axis=1).min(axis=1)

        # Candle terakhir
        last_ha_open = ha_open.iloc[-1]
        last_ha_close = ha_close.iloc[-1]
        last_ha_high = ha_high.iloc[-1]
        last_ha_low = ha_low.iloc[-1]

        # Candle sebelumnya
        prev_ha_open = ha_open.iloc[-2]
        prev_ha_close = ha_close.iloc[-2]

        # Arah HA
        if last_ha_close > last_ha_open:
            ha_direction = "BULLISH"
        elif last_ha_close < last_ha_open:
            ha_direction = "BEARISH"
        else:
            ha_direction = "NEUTRAL"

        # Kekuatan HA
        body = abs(last_ha_close - last_ha_open)
        total_range = last_ha_high - last_ha_low
        body_ratio = round(body / total_range, 3) if total_range > 0 else 0

        # Shadow analysis
        if ha_direction == "BULLISH":
            lower_shadow = last_ha_open - last_ha_low
            upper_shadow = last_ha_high - last_ha_close
        else:
            lower_shadow = last_ha_close - last_ha_low
            upper_shadow = last_ha_high - last_ha_open

        no_lower_shadow = lower_shadow < (body * 0.1)
        no_upper_shadow = upper_shadow < (body * 0.1)

        # Kekuatan sinyal
        if ha_direction == "BULLISH" and no_lower_shadow:
            ha_strength = "STRONG"
        elif ha_direction == "BEARISH" and no_upper_shadow:
            ha_strength = "STRONG"
        elif body_ratio >= 0.6:
            ha_strength = "MODERATE"
        else:
            ha_strength = "WEAK"

        # Konsistensi — apakah 2 candle terakhir searah?
        prev_direction = "BULLISH" if prev_ha_close > prev_ha_open else "BEARISH"
        consistent = prev_direction == ha_direction

        # Trend count — berapa candle berturut-turut searah
        trend_count = 0
        for i in range(len(df)-1, max(len(df)-6, 0)-1, -1):
            if ha_close.iloc[i] > ha_open.iloc[i]:
                if ha_direction == "BULLISH":
                    trend_count += 1
                else:
                    break
            else:
                if ha_direction == "BEARISH":
                    trend_count += 1
                else:
                    break

        return {
            "ha_direction": ha_direction,
            "ha_strength": ha_strength,
            "ha_body_ratio": body_ratio,
            "no_lower_shadow": no_lower_shadow,
            "no_upper_shadow": no_upper_shadow,
            "consistent": consistent,
            "trend_count": trend_count,
            "ha_open": round(last_ha_open, 6),
            "ha_close": round(last_ha_close, 6),
            "ha_high": round(last_ha_high, 6),
            "ha_low": round(last_ha_low, 6),
        }

    def _neutral(self):
        return {
            "ha_direction": "NEUTRAL",
            "ha_strength": "WEAK",
            "ha_body_ratio": 0,
            "no_lower_shadow": False,
            "no_upper_shadow": False,
            "consistent": False,
            "trend_count": 0,
            "ha_open": 0, "ha_close": 0,
            "ha_high": 0, "ha_low": 0,
        }
