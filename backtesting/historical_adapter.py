#!/usr/bin/env python3
"""
Historical Data Adapter for Backtesting

Mocks IndicatorManager's data fetching to use historical CSV instead of live Binance API.
"""

import logging
from typing import Dict
import pandas as pd

logger = logging.getLogger(__name__)


class HistoricalDataAdapter:
    """
    Adapter to provide historical data to IndicatorManager during backtesting
    """
    
    def __init__(self, historical_data: Dict[str, Dict[str, pd.DataFrame]]):
        """
        Initialize adapter with pre-loaded historical data
        
        Args:
            historical_data: Nested dict {symbol: {interval: DataFrame}}
        """
        self.historical_data = historical_data
        self.current_timestamp = None
        
        logger.info("HistoricalDataAdapter initialized")
    
    def set_timestamp(self, timestamp: pd.Timestamp):
        """
        Set current timestamp for backtest replay
        
        Args:
            timestamp: Current timestamp in backtest
        """
        self.current_timestamp = timestamp
    
    def get_candles(
        self,
        symbol: str,
        interval: str,
        limit: int = 200
    ) -> pd.DataFrame:
        """
        Get historical candles up to current timestamp
        
        This mimics fetch_candles() behavior but uses historical data
        
        Args:
            symbol: Trading symbol
            interval: Timeframe
            limit: Number of candles to return
        
        Returns:
            DataFrame with candles up to current_timestamp
        """
        if self.current_timestamp is None:
            raise ValueError("current_timestamp not set! Call set_timestamp() first")
        
        # Get full historical data for symbol/interval
        if symbol not in self.historical_data:
            logger.warning(f"No data for {symbol}")
            return pd.DataFrame()
        
        if interval not in self.historical_data[symbol]:
            logger.warning(f"No {interval} data for {symbol}")
            return pd.DataFrame()
        
        df = self.historical_data[symbol][interval]
        
        # Filter: only candles up to current timestamp
        mask = df['timestamp'] <= self.current_timestamp
        filtered = df[mask].tail(limit)
        
        if len(filtered) == 0:
            logger.warning(
                f"No candles for {symbol} {interval} at {self.current_timestamp}"
            )
            return pd.DataFrame()
        
        # Return copy to avoid modifying original
        return filtered.copy()
    
    def inject_into_indicator_manager(self, indicator_manager):
        """
        Monkey-patch IndicatorManager to use historical data
        
        Replaces fetch_candles() method with our historical version
        
        Args:
            indicator_manager: IndicatorManager instance to patch
        """
        # Store original method (in case we need it)
        indicator_manager._original_fetch_candles = indicator_manager.fetch_candles
        
        # Replace with our adapter
        def historical_fetch_candles(symbol: str, interval: str, limit: int = 200):
            return self.get_candles(symbol, interval, limit)
        
        indicator_manager.fetch_candles = historical_fetch_candles
        
        logger.info("✅ IndicatorManager patched for historical data")


if __name__ == "__main__":
    # Example usage
    from backtesting.historical_data_loader import HistoricalDataLoader
    
    # Load historical data
    loader = HistoricalDataLoader()
    data = loader.load_historical_data(['BTCUSDT'], ['15m', '1h'])
    
    # Create adapter
    adapter = HistoricalDataAdapter(data)
    
    # Set timestamp
    timestamp = pd.to_datetime('2026-04-03 12:00:00')
    adapter.set_timestamp(timestamp)
    
    # Get candles
    candles = adapter.get_candles('BTCUSDT', '15m', limit=100)
    
    print(f"Got {len(candles)} candles up to {timestamp}")
    print(candles.tail())
