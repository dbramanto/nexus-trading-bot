"""
NEXUS v2.0 - P1 Basic Indicators
Provides EMA, RSI, ATR, Volume analysis to P2.
"""
import logging
from typing import Dict, List
import pandas as pd
import numpy as np
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)

class BasicIndicators(BaseAnalyst):

    @property
    def name(self): return "basic_indicators"
    @property
    def category(self): return "classic"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 50

    def __init__(self, ema_periods=[20, 50, 200], rsi_period=14, atr_period=14, volume_period=20):
        self.ema_periods = ema_periods
        self.rsi_period = rsi_period
        self.atr_period = atr_period
        self.volume_period = volume_period

    def analyze(self, df, config=None):
        emas = self._calc_emas(df)
        rsi = self._calc_rsi(df)
        atr = self._calc_atr(df)
        vol = self._calc_volume(df)
        ma = self._check_ma_alignment(emas)
        return {
            "emas": emas,
            "rsi_value": rsi["value"],
            "rsi_signal": rsi["signal"],
            "rsi_overbought": rsi["overbought"],
            "rsi_oversold": rsi["oversold"],
            "atr_value": atr["value"],
            "atr_percent": atr["percent"],
            "volume_current": vol["current"],
            "volume_average": vol["average"],
            "volume_ratio": vol["ratio"],
            "volume_is_high": vol["is_high"],
            "ma_aligned": ma["aligned"],
            "ma_direction": ma["direction"],
            "trend": self._get_trend(df),
        }

    def _calc_emas(self, df):
        emas = {}
        for p in self.ema_periods:
            if len(df) < p:
                emas[p] = None
            else:
                emas[p] = round(df["close"].ewm(span=p, adjust=False).mean().iloc[-1], 4)
        return emas

    def _calc_rsi(self, df):
        if len(df) < self.rsi_period + 1:
            return {"value": None, "overbought": False, "oversold": False, "signal": "NEUTRAL"}
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(span=self.rsi_period, adjust=False).mean()
        avg_loss = loss.ewm(span=self.rsi_period, adjust=False).mean()
        rs = avg_gain / avg_loss
        rsi_val = round((100 - (100 / (1 + rs))).iloc[-1], 2)
        ob = rsi_val >= 70
        os_ = rsi_val <= 30
        sig = "OVERSOLD" if os_ else "OVERBOUGHT" if ob else "NEUTRAL"
        return {"value": rsi_val, "overbought": ob, "oversold": os_, "signal": sig}

    def _calc_atr(self, df):
        if len(df) < self.atr_period + 1:
            return {"value": None, "percent": None}
        high = df["high"]
        low = df["low"]
        prev_close = df["close"].shift(1)
        tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
        atr_val = round(tr.ewm(span=self.atr_period, adjust=False).mean().iloc[-1], 4)
        price = df["close"].iloc[-1]
        return {"value": atr_val, "percent": round((atr_val / price) * 100, 4)}

    def _calc_volume(self, df):
        if len(df) < self.volume_period:
            return {"current": None, "average": None, "ratio": None, "is_high": False}
        cur = df["volume"].iloc[-1]
        avg = df["volume"].tail(self.volume_period).mean()
        ratio = round(cur / avg, 2) if avg > 0 else 1.0
        return {"current": round(cur, 2), "average": round(avg, 2), "ratio": ratio, "is_high": ratio >= 1.5}

    def _check_ma_alignment(self, emas):
        valid = sorted({k: v for k, v in emas.items() if v is not None}.items())
        if len(valid) < 2:
            return {"aligned": False, "direction": "NEUTRAL", "strength": 0}
        bullish = all(valid[i][1] > valid[i+1][1] for i in range(len(valid)-1))
        bearish = all(valid[i][1] < valid[i+1][1] for i in range(len(valid)-1))
        if bullish: return {"aligned": True, "direction": "BULLISH", "strength": 100}
        if bearish: return {"aligned": True, "direction": "BEARISH", "strength": 100}
        return {"aligned": False, "direction": "NEUTRAL", "strength": 0}

    def _get_trend(self, df, period=20):
        if len(df) < period: return "NEUTRAL"
        price = df["close"].iloc[-1]
        ema = df["close"].ewm(span=period, adjust=False).mean().iloc[-1]
        if price > ema * 1.005: return "BULLISH"
        if price < ema * 0.995: return "BEARISH"
        return "NEUTRAL"

    def get_atr_value(self, df):
        return self._calc_atr(df).get("value")

    def get_rsi_series(self, df):
        if len(df) < self.rsi_period + 1: return pd.Series()
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        rs = gain.ewm(span=self.rsi_period, adjust=False).mean() / loss.ewm(span=self.rsi_period, adjust=False).mean()
        return 100 - (100 / (1 + rs))
