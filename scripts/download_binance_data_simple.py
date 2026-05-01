"""
Simple Binance data downloader using ONLY requests
No external libraries needed!
"""

import requests
import pandas as pd
from datetime import datetime
import json
import time
import os

print("="*70)
print("BINANCE DATA DOWNLOAD (Direct HTTP Method)")
print("="*70)
print("")

SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT',
    'XRPUSDT', 'ADAUSDT', 'AVAXUSDT', 'DOTUSDT',
    'MATICUSDT', 'LINKUSDT', 'UNIUSDT', 'ATOMUSDT',
    'LTCUSDT', 'ARBUSDT',
]

INTERVAL = '15m'
DAYS = 30
LIMIT = 1500
BASE_URL = 'https://fapi.binance.com/fapi/v1/klines'

print(f"Target: {DAYS} days × {INTERVAL} data")
print(f"Symbols: {len(SYMBOLS)}")
print(f"Expected candles: ~{DAYS * 96} per symbol")
print("")
print("Starting download...")
print("─" * 70)

all_data = {}
failed = []
total_candles = 0

for i, symbol in enumerate(SYMBOLS, 1):
    try:
        print(f"[{i:2d}/{len(SYMBOLS)}] {symbol:15s} ", end='', flush=True)
        
        all_klines = []
        
        # Request 1: Latest 1500 candles
        params = {'symbol': symbol, 'interval': INTERVAL, 'limit': LIMIT}
        r = requests.get(BASE_URL, params=params, timeout=10)
        r.raise_for_status()
        klines1 = r.json()
        all_klines.extend(klines1)
        
        # Request 2: Older 1500 candles
        if klines1:
            params['endTime'] = klines1[0][0] - 1
            r = requests.get(BASE_URL, params=params, timeout=10)
            r.raise_for_status()
            all_klines.extend(r.json())
        
        # Convert to DataFrame
        df = pd.DataFrame(all_klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        # Process
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        df = df.sort_values('timestamp').reset_index(drop=True).tail(DAYS * 96)
        
        all_data[symbol] = df
        total_candles += len(df)
        print(f"✓ {len(df):4d} candles")
        
        time.sleep(0.2)
        
    except Exception as e:
        print(f"✗ {str(e)[:30]}")
        failed.append((symbol, str(e)))

print("─" * 70)
print("")
print(f"✅ Success: {len(all_data)}/{len(SYMBOLS)}")
print(f"📊 Total: {total_candles:,} candles")

if failed:
    print(f"❌ Failed: {len(failed)}")
    for s, e in failed:
        print(f"   • {s}: {e[:40]}")

# Save
os.makedirs('data/historical', exist_ok=True)

print("")
print("Saving files...")

for symbol, df in all_data.items():
    filename = f"data/historical/{symbol}_M15_30d.csv"
    df.to_csv(filename, index=False)
    print(f"  ✓ {filename}")

# Summary
summary = {
    'download_date': datetime.now().isoformat(),
    'days': DAYS,
    'interval': INTERVAL,
    'symbols_success': len(all_data),
    'symbols_failed': len(failed),
    'total_candles': total_candles,
    'method': 'Direct HTTP (requests)',
    'failed': [{'symbol': s, 'error': e} for s, e in failed]
}

with open('data/historical/download_summary.json', 'w') as f:
    json.dump(summary, f, indent=2)

print("")
print("✅ Download complete!")
print(f"📁 Saved to: data/historical/")
print(f"📊 Summary: data/historical/download_summary.json")

