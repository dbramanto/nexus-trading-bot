#!/usr/bin/env python3
"""
Historical Data Loader for NEXUS Backtesting

Downloads historical klines from Binance for multiple symbols and timeframes.
Saves to CSV for fast backtesting replay.
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
from binance.client import Client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HistoricalDataLoader:
    """
    Download and manage historical OHLCV data from Binance
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        data_dir: str = 'data/historical'
    ):
        """
        Initialize data loader
        
        Args:
            api_key: Binance API key (optional for public data)
            api_secret: Binance API secret (optional)
            data_dir: Directory to save CSV files
        """
        self.client = Client(api_key, api_secret)
        self.data_dir = data_dir
        
        # Create directory if not exists
        os.makedirs(data_dir, exist_ok=True)
        
        logger.info(f"HistoricalDataLoader initialized (data_dir: {data_dir})")
    
    def download_klines(
        self,
        symbol: str,
        interval: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        Download klines for a symbol and timeframe
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Timeframe ('15m', '30m', '1h', '4h')
            start_date: Start date 'YYYY-MM-DD'
            end_date: End date 'YYYY-MM-DD'
        
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"Downloading {symbol} {interval} from {start_date} to {end_date}...")
        
        # Convert dates to milliseconds
        start_ms = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
        end_ms = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
        
        all_klines = []
        current_start = start_ms
        
        # Binance limit: 1000 klines per request
        limit = 1000
        
        while current_start < end_ms:
            try:
                klines = self.client.get_klines(
                    symbol=symbol,
                    interval=interval,
                    startTime=current_start,
                    endTime=end_ms,
                    limit=limit
                )
                
                if not klines:
                    break
                
                all_klines.extend(klines)
                
                # Update start time to last kline close time + 1ms
                current_start = klines[-1][0] + 1
                
                logger.info(f"  Downloaded {len(klines)} klines (total: {len(all_klines)})")
                
                # Rate limiting: ~1200 requests/minute
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error downloading {symbol} {interval}: {e}")
                time.sleep(5)
                continue
        
        # Convert to DataFrame
        df = pd.DataFrame(all_klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        # Convert types
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        # Keep only essential columns
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
        logger.info(f"✅ Downloaded {len(df)} klines for {symbol} {interval}")
        
        return df
    
    def save_to_csv(self, df: pd.DataFrame, symbol: str, interval: str):
        """
        Save DataFrame to CSV
        
        Args:
            df: DataFrame with OHLCV data
            symbol: Trading pair
            interval: Timeframe
        """
        filename = f"{symbol}_{interval}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        df.to_csv(filepath, index=False)
        logger.info(f"💾 Saved to {filepath}")
    
    def load_from_csv(self, symbol: str, interval: str) -> pd.DataFrame:
        """
        Load DataFrame from CSV
        
        Args:
            symbol: Trading pair
            interval: Timeframe
        
        Returns:
            DataFrame with OHLCV data
        """
        filename = f"{symbol}_{interval}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        df = pd.read_csv(filepath)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        logger.info(f"📂 Loaded {len(df)} klines from {filepath}")
        
        return df
    
    def download_multiple(
        self,
        symbols: List[str],
        intervals: List[str],
        start_date: str,
        end_date: str
    ) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Download multiple symbols and timeframes
        
        Args:
            symbols: List of trading pairs
            intervals: List of timeframes
            start_date: Start date 'YYYY-MM-DD'
            end_date: End date 'YYYY-MM-DD'
        
        Returns:
            Nested dict: {symbol: {interval: DataFrame}}
        """
        logger.info("=" * 70)
        logger.info("HISTORICAL DATA DOWNLOAD")
        logger.info("=" * 70)
        logger.info(f"Symbols: {len(symbols)}")
        logger.info(f"Intervals: {intervals}")
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info("=" * 70)
        
        data = {}
        total_files = len(symbols) * len(intervals)
        completed = 0
        
        for symbol in symbols:
            data[symbol] = {}
            
            for interval in intervals:
                completed += 1
                logger.info(f"\n[{completed}/{total_files}] Processing {symbol} {interval}...")
                
                try:
                    df = self.download_klines(symbol, interval, start_date, end_date)
                    self.save_to_csv(df, symbol, interval)
                    data[symbol][interval] = df
                    
                except Exception as e:
                    logger.error(f"❌ Failed to download {symbol} {interval}: {e}")
                    continue
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ DOWNLOAD COMPLETE!")
        logger.info(f"Total files: {completed}/{total_files}")
        logger.info("=" * 70)
        
        return data


if __name__ == "__main__":
    # Example usage
    loader = HistoricalDataLoader()
    
    # NEXUS symbols
    symbols = [
        'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
        'DOGEUSDT', 'ADAUSDT', 'TRXUSDT', 'AVAXUSDT', 'DOTUSDT',
        'LINKUSDT', 'MATICUSDT', 'LTCUSDT', 'UNIUSDT', 'ATOMUSDT'
    ]
    
    intervals = ['15m', '30m', '1h', '4h']
    
    # Download last 6 months
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
    
    loader.download_multiple(symbols, intervals, start_date, end_date)
