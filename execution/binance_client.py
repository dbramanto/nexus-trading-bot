"""
NEXUS v2.0 - Binance Client Wrapper
"""
import os
import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException

logger = logging.getLogger(__name__)

class BinanceClientWrapper:

    def __init__(self, testnet: bool = False):
        load_dotenv()
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.api_secret = os.getenv("BINANCE_SECRET_KEY")
        if not self.api_key or not self.api_secret:
            raise ValueError("BINANCE_API_KEY and BINANCE_SECRET_KEY must be set in .env")
        self.testnet = testnet
        self.client = None
        self._connect()
        logger.info(f"BinanceClientWrapper initialized (testnet={testnet})")

    def _connect(self):
        self.client = Client(self.api_key, self.api_secret, testnet=self.testnet)
        logger.info("Binance client connected")

    def test_connection(self) -> bool:
        try:
            self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def get_futures_candles(self, symbol: str, interval: str, limit: int = 300) -> List:
        try:
            return self.client.futures_klines(symbol=symbol, interval=interval, limit=limit)
        except BinanceAPIException as e:
            logger.error(f"API error fetching candles {symbol}: {e}")
            return []

    def get_account_info(self) -> Dict:
        try:
            return self.client.futures_account()
        except BinanceAPIException as e:
            logger.error(f"Account info error: {e}")
            return {}

    def get_balance(self) -> float:
        try:
            account = self.client.futures_account()
            for asset in account.get("assets", []):
                if asset["asset"] == "USDT":
                    return float(asset["availableBalance"])
            return 0.0
        except Exception as e:
            logger.error(f"Balance error: {e}")
            return 0.0

    def place_order(self, symbol: str, side: str, quantity: float,
                    stop_loss: float = None, take_profit: float = None) -> Dict:
        try:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type="MARKET",
                quantity=quantity
            )
            logger.info(f"Order placed: {side} {quantity} {symbol}")
            return order
        except BinanceAPIException as e:
            logger.error(f"Order error {symbol}: {e}")
            return {}

    def get_open_positions(self) -> List:
        try:
            positions = self.client.futures_position_information()
            return [p for p in positions if float(p.get("positionAmt", 0)) != 0]
        except Exception as e:
            logger.error(f"Positions error: {e}")
            return []

    def get_funding_rate(self, symbol: str, limit: int = 10) -> List:
        try:
            return self.client.futures_funding_rate(symbol=symbol, limit=limit)
        except Exception as e:
            logger.error(f"Funding rate error {symbol}: {e}")
            return []

    def get_open_interest(self, symbol: str) -> Dict:
        try:
            return self.client.futures_open_interest(symbol=symbol)
        except Exception as e:
            logger.error(f"OI error {symbol}: {e}")
            return {}

    def get_long_short_ratio(self, symbol: str, period: str = "15m", limit: int = 10) -> List:
        try:
            return self.client.futures_top_longshort_account_ratio(
                symbol=symbol, period=period, limit=limit
            )
        except Exception as e:
            logger.error(f"L/S ratio error {symbol}: {e}")
            return []

    def close_position(self, symbol: str, side: str, quantity: float) -> Dict:
        close_side = "SELL" if side == "LONG" else "BUY"
        try:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=close_side,
                type="MARKET",
                quantity=quantity,
                reduceOnly=True
            )
            logger.info(f"Position closed: {symbol}")
            return order
        except BinanceAPIException as e:
            logger.error(f"Close position error {symbol}: {e}")
            return {}

    def get_agg_trades(self, symbol: str, limit: int = 500) -> list:
        try:
            return self.client.futures_aggregate_trades(symbol=symbol, limit=limit)
        except Exception as e:
            logger.error(f"AggTrades error {symbol}: {e}")
            return []

    def get_symbol_info(self, symbol: str) -> Dict:
        try:
            info = self.client.futures_exchange_info()
            for s in info.get("symbols", []):
                if s["symbol"] == symbol:
                    return s
            return {}
        except Exception as e:
            logger.error(f"Symbol info error {symbol}: {e}")
            return {}
