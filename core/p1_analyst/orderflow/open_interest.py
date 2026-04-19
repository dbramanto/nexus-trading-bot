"""
NEXUS v2.0 - P1 Open Interest Analyzer
Crypto-native signal — tidak ada di forex.
Rising OI + rising price = genuine buying pressure.
Rising OI + falling price = genuine selling pressure.
Falling OI = position unwinding, trend melemah.
"""
import logging
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)


class OpenInterest(BaseAnalyst):

    @property
    def name(self): return "open_interest"
    @property
    def category(self): return "orderflow"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 1

    def __init__(self):
        self._symbol = None
        self._binance_client = None

    def set_context(self, symbol, binance_client):
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
            # Fetch current OI
            oi_data = self._binance_client.get_open_interest(self._symbol)
            if not oi_data:
                return self._neutral()

            current_oi = float(oi_data.get("openInterest", 0))

            # Fetch OI history untuk trend
            oi_hist = self._binance_client.client.futures_open_interest_hist(
                symbol=self._symbol,
                period="15m",
                limit=10
            )

            if not oi_hist or len(oi_hist) < 2:
                return self._neutral()

            oi_values = [float(x["sumOpenInterest"]) for x in oi_hist]
            oi_change_pct = (oi_values[-1] - oi_values[0]) / oi_values[0] * 100 if oi_values[0] > 0 else 0

            price_recent = df["close"].iloc[-1]
            price_prev = df["close"].iloc[-5] if len(df) >= 5 else df["close"].iloc[0]
            price_change = (price_recent - price_prev) / price_prev * 100

            oi_rising = oi_change_pct > 0.5
            oi_falling = oi_change_pct < -0.5
            price_rising = price_change > 0

            if oi_rising and price_rising:
                oi_signal = "BULLISH_CONFIRMED"
                bias_contribution = "BULLISH"
            elif oi_rising and not price_rising:
                oi_signal = "BEARISH_CONFIRMED"
                bias_contribution = "BEARISH"
            elif oi_falling and price_rising:
                oi_signal = "SHORT_COVERING"
                bias_contribution = "BULLISH"
            elif oi_falling and not price_rising:
                oi_signal = "LONG_UNWINDING"
                bias_contribution = "BEARISH"
            else:
                oi_signal = "NEUTRAL"
                bias_contribution = "NEUTRAL"

            return {
                "oi_current": round(current_oi, 2),
                "oi_change_pct": round(oi_change_pct, 4),
                "oi_rising": oi_rising,
                "oi_falling": oi_falling,
                "oi_signal": oi_signal,
                "oi_bias": bias_contribution,
                "price_change_pct": round(price_change, 4),
            }

        except Exception as e:
            logger.error(f"OpenInterest error {self._symbol}: {e}")
            return self._neutral()

    def _neutral(self):
        return {
            "oi_current": 0,
            "oi_change_pct": 0,
            "oi_rising": False,
            "oi_falling": False,
            "oi_signal": "NEUTRAL",
            "oi_bias": "NEUTRAL",
            "price_change_pct": 0,
        }
