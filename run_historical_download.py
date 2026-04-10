#!/usr/bin/env python3
"""Run full historical data download"""

from backtesting.historical_data_loader import HistoricalDataLoader
from datetime import datetime, timedelta

# Initialize loader
loader = HistoricalDataLoader()

# NEXUS symbols (15 coins)
symbols = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
    'DOGEUSDT', 'ADAUSDT', 'TRXUSDT', 'AVAXUSDT', 'DOTUSDT',
    'LINKUSDT', 'MATICUSDT', 'LTCUSDT', 'UNIUSDT', 'ATOMUSDT'
]

# Timeframes
intervals = ['15m', '30m', '1h', '4h']

# Date range: Last 6 months
end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')

print(f"Starting download: {start_date} to {end_date}")
print(f"Symbols: {len(symbols)}")
print(f"Intervals: {len(intervals)}")
print(f"Total files: {len(symbols) * len(intervals)}")
print("Estimated time: 1-2 hours")
print("=" * 70)

# Run download
loader.download_multiple(symbols, intervals, start_date, end_date)

print("\n✅ ALL DOWNLOADS COMPLETE!")
