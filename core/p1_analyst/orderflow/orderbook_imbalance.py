"""
NEXUS v2.0 - P1 Order Book Imbalance
Snapshot order book via REST API — tidak butuh WebSocket.
Bid/Ask imbalance adalah leading indicator jangka sangat pendek.

Bid > Ask secara signifikan = buying pressure (BULLISH)
Ask > Bid secara signifikan = selling pressure (BEARISH)
"""
import logging
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)


class OrderBookImbalance(BaseAnalyst):

    @property
    def name(self): return "orderbook_imbalance"
    @property
    def category(self): return "orderflow"
    @property
    def is_implemented(self): return True
    @property
    def min_bars_required(self): return 1

    def __init__(self, depth=20, imbalance_threshold=1.3):
        self.depth = depth
        self.imbalance_threshold = imbalance_threshold
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
            book = self._binance_client.client.futures_order_book(
                symbol=self._symbol,
                limit=self.depth
            )
            if not book:
                return self._neutral()

            bid_vol = sum(float(b[1]) for b in book.get("bids", []))
            ask_vol = sum(float(a[1]) for a in book.get("asks", []))
            total = bid_vol + ask_vol

            if total == 0:
                return self._neutral()

            ratio = bid_vol / ask_vol if ask_vol > 0 else 1.0
            bid_pct = bid_vol / total * 100
            ask_pct = ask_vol / total * 100

            if ratio >= self.imbalance_threshold:
                signal = "BID_DOMINANT"
                bias = "BULLISH"
            elif ratio <= (1 / self.imbalance_threshold):
                signal = "ASK_DOMINANT"
                bias = "BEARISH"
            else:
                signal = "BALANCED"
                bias = "NEUTRAL"

            best_bid = float(book["bids"][0][0]) if book.get("bids") else 0
            best_ask = float(book["asks"][0][0]) if book.get("asks") else 0
            spread = round(best_ask - best_bid, 6) if best_bid and best_ask else 0
            spread_pct = round(spread / best_bid * 100, 6) if best_bid > 0 else 0

            return {
                "bid_volume": round(bid_vol, 4),
                "ask_volume": round(ask_vol, 4),
                "bid_ask_ratio": round(ratio, 4),
                "bid_pct": round(bid_pct, 2),
                "ask_pct": round(ask_pct, 2),
                "ob_signal": signal,
                "ob_bias": bias,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread_pct": spread_pct,
            }

        except Exception as e:
            logger.error(f"OrderBook error {self._symbol}: {e}")
            return self._neutral()

    def _neutral(self):
        return {
            "bid_volume": 0,
            "ask_volume": 0,
            "bid_ask_ratio": 1.0,
            "bid_pct": 50,
            "ask_pct": 50,
            "ob_signal": "BALANCED",
            "ob_bias": "NEUTRAL",
            "best_bid": 0,
            "best_ask": 0,
            "spread_pct": 0,
        }
