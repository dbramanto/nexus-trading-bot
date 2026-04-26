"""
NEXUS v2.0 - Full Shadow Log Outcome Simulator
Process ALL 9 days shadow logs untuk comprehensive pattern validation.
"""
import sys
sys.path.insert(0, "/home/nexus/nexus_bot")

import json
import pandas as pd
from datetime import datetime, timedelta
from execution.binance_client import BinanceClientWrapper
import time

client = BinanceClientWrapper(testnet=False)

def fetch_outcome_candles(symbol, entry_time, limit=100):
    """Fetch candles after entry untuk cek TP/SL hit."""
    try:
        entry_dt = pd.to_datetime(entry_time)
        end_dt = entry_dt + timedelta(hours=24)
        
        klines = client.client.get_historical_klines(
            symbol,
            "15m",
            entry_dt.strftime("%Y-%m-%d %H:%M"),
            end_dt.strftime("%Y-%m-%d %H:%M")
        )
        
        if not klines:
            return None
        
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close']:
            df[col] = df[col].astype(float)
        
        return df
        
    except Exception as e:
        return None

def calc_sl_tp(entry_price, direction, atr_pct=1.5, rr=2.0):
    """Simple SL/TP calculation."""
    if direction == "BULLISH":
        sl = entry_price * (1 - atr_pct/100)
        tp = entry_price * (1 + (atr_pct * rr)/100)
    else:
        sl = entry_price * (1 + atr_pct/100)
        tp = entry_price * (1 - (atr_pct * rr)/100)
    
    return sl, tp

def check_outcome(df, entry_price, sl, tp, direction):
    """Check if TP or SL hit dalam candles."""
    if df is None or df.empty:
        return "UNKNOWN", 0
    
    for idx, row in df.iterrows():
        high = row['high']
        low = row['low']
        
        if direction == "BULLISH":
            if low <= sl:
                return "LOSS", idx
            if high >= tp:
                return "WIN", idx
        else:
            if high >= sl:
                return "LOSS", idx
            if low <= tp:
                return "WIN", idx
    
    return "PENDING", len(df)

def main():
    print("=== FULL SHADOW LOG OUTCOME SIMULATION ===\n")
    
    import os
    shadow_dir = 'data/shadow_logs'
    files = sorted([f for f in os.listdir(shadow_dir) 
                    if f.endswith('.jsonl') and not f.endswith('.backup')])
    
    print(f"Found {len(files)} shadow log files\n")
    
    all_simulated = []
    total_processed = 0
    
    for fname in files:
        print(f"Processing {fname}...")
        fpath = os.path.join(shadow_dir, fname)
        
        with open(fpath) as f:
            entries = [json.loads(line) for line in f if line.strip()]
        
        # Filter: grade bukan NO_TRADE, bias valid
        eligible = [e for e in entries 
                   if e.get('grade') != 'NO_TRADE'
                   and e.get('bias') in ['BULLISH', 'BEARISH']]
        
        print(f"  Eligible entries: {len(eligible)}")
        
        for i, entry in enumerate(eligible, 1):
            symbol = entry['symbol']
            entry_time = entry['timestamp']
            entry_price = entry.get('potential_entry', 0)
            bias = entry['bias']
            score = entry.get('score', 0)
            
            if entry_price == 0:
                continue
            
            # Calc SL/TP
            sl, tp = calc_sl_tp(entry_price, bias)
            
            # Fetch outcome candles
            df = fetch_outcome_candles(symbol, entry_time)
            
            # Check outcome
            outcome, candles = check_outcome(df, entry_price, sl, tp, bias)
            
            # Extract P1 features
            p1_snap = entry.get('p1_snapshot', {})
            
            simulated = {
                'timestamp': entry_time,
                'symbol': symbol,
                'direction': bias,
                'entry_price': entry_price,
                'sl_price': sl,
                'tp_price': tp,
                'outcome': outcome,
                'candles_to_outcome': candles,
                'score': score,
                'grade': entry.get('grade'),
                
                # Tier 1 features
                'choch_detected': p1_snap.get('mss_detector', {}).get('choch_detected'),
                'mss_structure': p1_snap.get('mss_detector', {}).get('mss_structure'),
                'primary_pattern': p1_snap.get('candle_pattern', {}).get('primary_pattern'),
                
                # Tier 3 features
                'price_zone': p1_snap.get('premium_discount', {}).get('price_zone'),
                'momentum': p1_snap.get('momentum_classifier', {}).get('momentum'),
                'bb_position': p1_snap.get('bollinger_bands', {}).get('bb_position'),
                
                # Additional context
                'volume_ratio': p1_snap.get('basic_indicators', {}).get('volume_ratio'),
                'rsi_value': p1_snap.get('basic_indicators', {}).get('rsi_value'),
            }
            
            all_simulated.append(simulated)
            total_processed += 1
            
            # Progress indicator
            if i % 10 == 0:
                print(f"    Processed {i}/{len(eligible)}...")
            
            # Rate limit protection
            if i % 50 == 0:
                time.sleep(1)
        
        print(f"  Completed: {len(eligible)} entries\n")
    
    # Save results
    if all_simulated:
        df_sim = pd.DataFrame(all_simulated)
        output_file = 'data/simulated_full.csv'
        df_sim.to_csv(output_file, index=False)
        
        print(f"{'='*60}")
        print(f"=== SIMULATION COMPLETE ===")
        print(f"Total simulated: {len(all_simulated)}")
        print(f"Results saved: {output_file}")
        print(f"{'='*60}\n")
        
        # Quick stats
        df_closed = df_sim[df_sim['outcome'].isin(['WIN', 'LOSS'])]
        wins = len(df_closed[df_closed['outcome'] == 'WIN'])
        losses = len(df_closed[df_closed['outcome'] == 'LOSS'])
        pending = len(df_sim[df_sim['outcome'] == 'PENDING'])
        
        print(f"Closed trades: {len(df_closed)}")
        print(f"  WIN: {wins}")
        print(f"  LOSS: {losses}")
        print(f"  WR: {wins/(wins+losses)*100:.1f}%")
        print(f"Pending (no TP/SL hit in 24h): {pending}")
    else:
        print("❌ No data simulated!")

if __name__ == "__main__":
    main()
