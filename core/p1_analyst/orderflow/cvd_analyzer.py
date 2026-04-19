"""
NEXUS v2.0 - P1 CVD Analyzer (Cumulative Volume Delta)
Crypto-native: selisih taker buy vs taker sell dari aggTrades.
Binance API sudah tersambung — fetch via REST, tidak butuh WebSocket.

CVD rising + price rising = genuine buying pressure (BULLISH confirmed)
CVD falling + price rising = distribution (bearish divergence)
CVD rising + price falling = accumulation (bullish divergence)
CVD falling + price falling = genuine selling pressure (BEARISH confirmed)
"""
import logging
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)


class CVDAnalyzer(BaseAnalyst):

    @property
    def name(self): return "cvd_analyzer"
    @property
    def category(self): return "orderflow"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 1

    def __init__(self, lookback_trades=500):
        self.lookback_trades = lookback_trades
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
        # Di BT environment, skip API call


        try:
            trades = self._binance_client.get_agg_trades(
                symbol=self._symbol,
                limit=self.lookback_trades
            )
            if not trades:
                return self._neutral()

            buy_vol = 0.0
            sell_vol = 0.0
            for t in trades:
                qty = float(t["q"])
                if t["m"]:
                    sell_vol += qty
                else:
                    buy_vol += qty

            total_vol = buy_vol + sell_vol
            cvd = buy_vol - sell_vol
            cvd_ratio = buy_vol / total_vol if total_vol > 0 else 0.5

            # Price direction dari df
            if len(df) >= 5:
                price_change = (df["close"].iloc[-1] - df["close"].iloc[-5]) / df["close"].iloc[-5] * 100
            else:
                price_change = 0

            price_rising = price_change > 0.1
            price_falling = price_change < -0.1
            cvd_positive = cvd > 0
            cvd_negative = cvd < 0

            if cvd_positive and price_rising:
                signal = "BULLISH_CONFIRMED"
                bias = "BULLISH"
                divergence = False
            elif cvd_negative and price_falling:
                signal = "BEARISH_CONFIRMED"
                bias = "BEARISH"
                divergence = False
            elif cvd_negative and price_rising:
                signal = "BEARISH_DIVERGENCE"
                bias = "BEARISH"
                divergence = True
            elif cvd_positive and price_falling:
                signal = "BULLISH_DIVERGENCE"
                bias = "BULLISH"
                divergence = True
            else:
                signal = "NEUTRAL"
                bias = "NEUTRAL"
                divergence = False

            return {
                "cvd_value": round(cvd, 4),
                "cvd_ratio": round(cvd_ratio, 4),
                "buy_volume": round(buy_vol, 4),
                "sell_volume": round(sell_vol, 4),
                "cvd_signal": signal,
                "cvd_bias": bias,
                "cvd_divergence": divergence,
                "price_change_pct": round(price_change, 4),
            }

        except Exception as e:
            logger.error(f"CVD error {self._symbol}: {e}")
            return self._neutral()

    def _neutral(self):
        return {
            "cvd_value": 0,
            "cvd_ratio": 0.5,
            "buy_volume": 0,
            "sell_volume": 0,
            "cvd_signal": "NEUTRAL",
            "cvd_bias": "NEUTRAL",
            "cvd_divergence": False,
            "price_change_pct": 0,
        }
