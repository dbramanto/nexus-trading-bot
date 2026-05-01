"""
Phase 1 Fast-Track: Filter Effectiveness Analysis
Using existing python-binance (no need ccxt!)
"""

from binance.um_futures import UMFutures
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import time
import sys

print("="*70)
print("PHASE 1: FILTER EFFECTIVENESS ANALYSIS")
print("="*70)
print("")

# Configuration
SYMBOLS = [
    # MODE A (Stable)
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT',
    'XRPUSDT', 'ADAUSDT', 'AVAXUSDT', 'DOTUSDT',
    'MATICUSDT', 'LINKUSDT', 'UNIUSDT', 'ATOMUSDT',
    'LTCUSDT', 'ARBUSDT',
    # MODE B (Top gainers - sample)
    'NEIROUSDT', 'GOATUSDT', 'MOODENGUSDT', 'ZEREBROUSDT',
    'FARTCOINUSDT', 'AI16ZUSDT', 'GRIFFAINUSDT', 'CHAOSUSDT',
]

DAYS = 30
INTERVAL = '15m'
CANDLES_NEEDED = DAYS * 96  # 30 days * 96 candles/day

print(f"Target: {DAYS} days of {INTERVAL} data")
print(f"Symbols: {len(SYMBOLS)}")
print(f"Candles needed per symbol: {CANDLES_NEEDED}")
print("")

# Initialize Binance client (NO API KEY NEEDED for public data!)
try:
    client = UMFutures()
    print("✅ Binance Futures client initialized (public data mode)")
except Exception as e:
    print(f"❌ Failed to initialize client: {e}")
    sys.exit(1)

print("")
print("Starting download...")
print("─" * 70)

# Download data
all_data = {}
failed = []
total_candles = 0

for i, symbol in enumerate(SYMBOLS, 1):
    try:
        print(f"[{i:2d}/{len(SYMBOLS)}] {symbol:15s} ", end='', flush=True)
        
        # Binance allows max 1500 candles per request
        # For 2880 candles, need 2 requests
        all_klines = []
        
        # First batch (most recent 1500)
        klines1 = client.klines(
            symbol=symbol,
            interval=INTERVAL,
            limit=1500
        )
        all_klines.extend(klines1)
        
        # Second batch (older 1500)
        if len(klines1) > 0:
            oldest_time = klines1[0][0]
            klines2 = client.klines(
                symbol=symbol,
                interval=INTERVAL,
                limit=1500,
                endTime=oldest_time - 1
            )
            all_klines.extend(klines2)
        
        # Convert to DataFrame
        df = pd.DataFrame(all_klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        # Keep only needed columns
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Convert to float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        # Sort by timestamp (oldest first)
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Keep last 30 days
        df = df.tail(CANDLES_NEEDED)
        
        all_data[symbol] = df
        total_candles += len(df)
        print(f"✓ {len(df):4d} candles")
        
        time.sleep(0.1)  # Small delay to be nice to API
        
    except Exception as e:
        print(f"✗ ERROR: {str(e)[:30]}")
        failed.append((symbol, str(e)))

print("─" * 70)
print("")
print("DOWNLOAD SUMMARY:")
print(f"  ✅ Success: {len(all_data)}/{len(SYMBOLS)} symbols")
print(f"  📊 Total candles: {total_candles:,}")

if failed:
    print(f"  ❌ Failed: {len(failed)}")
    for sym, err in failed:
        print(f"     • {sym}: {err[:50]}")

print("")

# Save raw data
if all_data:
    import os
    os.makedirs('data/historical', exist_ok=True)
    
    print("Saving data to CSV files...")
    
    for symbol, df in all_data.items():
        filename = f"data/historical/{symbol}_M15_30d.csv"
        df.to_csv(filename, index=False)
        print(f"  ✓ {filename}")
    
    print("")
    print("✅ All data saved to data/historical/")
    
    # Create summary file
    summary = {
        'download_date': datetime.now().isoformat(),
        'days': DAYS,
        'interval': INTERVAL,
        'symbols_requested': len(SYMBOLS),
        'symbols_success': len(all_data),
        'symbols_failed': len(failed),
        'total_candles': total_candles,
        'failed_symbols': [{'symbol': s, 'error': e} for s, e in failed],
        'method': 'python-binance (existing library)'
    }
    
    with open('data/historical/download_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("✅ Summary saved to data/historical/download_summary.json")
else:
    print("❌ No data downloaded!")
    sys.exit(1)

print("")
print("="*70)
print("DOWNLOAD COMPLETE!")
print("="*70)
print("")
print("Next step: Analyze filter effectiveness")
print("")

