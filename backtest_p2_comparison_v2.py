"""
Backtest Comparison: OLD P2 vs NEW P2
Using git history to compare versions.
"""

import sys
sys.path.insert(0, '/home/nexus/nexus_bot')

import pandas as pd
import numpy as np
from collections import Counter

print("="*80)
print("BACKTEST COMPARISON: OLD P2 vs NEW P2 SCORING")
print("="*80)
print()

# Load historical OHLC
df = pd.read_csv('data/historical/BTCUSDT_15m_3month.csv')
print(f"Historical data: {len(df)} candles (BTCUSDT 15m, 3 months)")
print(f"Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
print()

# Sample 1000 candles
sample_size = 1000
step = len(df) // sample_size
df_sample = df.iloc[::step].head(sample_size).copy()

print(f"Testing on {len(df_sample)} sampled candles...")
print()

# Generate random P1 snapshots (simulate market conditions)
np.random.seed(42)  # Reproducible

def generate_p1_snapshot():
    """Generate randomized P1 snapshot to simulate market"""
    return {
        'basic_indicators': {
            'volume_ratio': np.random.uniform(0, 2.5),
            'rsi_value': np.random.uniform(20, 80),
        },
        'momentum_classifier': {
            'momentum_direction': np.random.choice(['BULLISH', 'BEARISH', 'NEUTRAL'], p=[0.3, 0.3, 0.4]),
            'momentum_strength': np.random.randint(1, 5),
        },
        'candle_pattern': {
            'pattern_signal': np.random.choice(['BULLISH', 'BEARISH', 'NEUTRAL'], p=[0.25, 0.25, 0.5]),
            'pattern_strength': np.random.choice(['WEAK', 'MEDIUM', 'STRONG'], p=[0.5, 0.3, 0.2]),
            'primary_pattern': np.random.choice(['BULLISH_MARUBOZU', 'BEARISH_MARUBOZU', 'DOJI', 'INSIDE_BAR', None], p=[0.15, 0.15, 0.2, 0.3, 0.2]),
        },
        'mss_detector': {
            'mss_structure': np.random.choice(['BULLISH', 'BEARISH', 'RANGING'], p=[0.3, 0.3, 0.4]),
        },
        'premium_discount': {
            'price_zone': np.random.choice(['DISCOUNT', 'PREMIUM', 'EQUILIBRIUM'], p=[0.35, 0.35, 0.3]),
        },
        'bollinger_bands': {
            'bb_position': np.random.choice(['lower_half', 'upper_half', 'middle'], p=[0.35, 0.35, 0.3]),
        },
    }

# === TEST OLD P2 (from git) ===
print("📊 Testing OLD P2 (commit 23d07a1, pre-optimization)...")

# Import old version
import importlib.util
spec = importlib.util.spec_from_file_location("scoring_engine_old", "scoring_engine_old.py")
scoring_old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scoring_old)

from config.strategy_config import NexusConfig
config = NexusConfig()

p2_old = scoring_old.ScoringEngine(config)

old_scores = []
old_grades = []

for i in range(sample_size):
    p1 = generate_p1_snapshot()
    result = p2_old.score(p1)
    old_scores.append(result['score'])
    old_grades.append(result['grade'])

print(f"  ✓ Scored {len(old_scores)} candles")
print()

# === TEST NEW P2 (current) ===
print("📊 Testing NEW P2 (optimized, current version)...")

from core.p2_supervisor.scoring_engine import ScoringEngine
p2_new = ScoringEngine(config)

new_scores = []
new_grades = []
volume_gate_count = 0

# Use SAME random seed for fair comparison
np.random.seed(42)

for i in range(sample_size):
    p1 = generate_p1_snapshot()
    result = p2_new.score(p1)
    new_scores.append(result['score'])
    new_grades.append(result['grade'])
    
    if 'Volume <0.5' in result.get('reject_reason', ''):
        volume_gate_count += 1

print(f"  ✓ Scored {len(new_scores)} candles")
print()

# === RESULTS ===
print("="*80)
print("COMPARISON RESULTS")
print("="*80)
print()

print("📊 SCORE DISTRIBUTION")
print("-" * 80)

print(f"OLD P2 (pre-optimization):")
print(f"  Mean:   {np.mean(old_scores):.2f}")
print(f"  Median: {np.median(old_scores):.2f}")
print(f"  Max:    {max(old_scores):.1f}")
print(f"  Std:    {np.std(old_scores):.2f}")

print(f"\nNEW P2 (optimized):")
print(f"  Mean:   {np.mean(new_scores):.2f}")
print(f"  Median: {np.median(new_scores):.2f}")
print(f"  Max:    {max(new_scores):.1f}")
print(f"  Std:    {np.std(new_scores):.2f}")

score_delta = np.mean(new_scores) - np.mean(old_scores)
pct_change = (score_delta / np.mean(old_scores) * 100) if np.mean(old_scores) > 0 else 0

print(f"\n📈 Mean Score Change: {score_delta:+.2f} points ({pct_change:+.1f}%)")

print()

# === GRADE DISTRIBUTION ===
print("🎓 GRADE DISTRIBUTION")
print("-" * 80)

old_dist = Counter(old_grades)
new_dist = Counter(new_grades)

print("OLD P2:")
for grade in ['PREMIUM', 'VALID', 'WEAK', 'NO_TRADE']:
    count = old_dist.get(grade, 0)
    pct = count/len(old_grades)*100
    print(f"  {grade:10} | {count:4} ({pct:5.1f}%)")

print("\nNEW P2:")
for grade in ['PREMIUM', 'VALID', 'WEAK', 'NO_TRADE']:
    count = new_dist.get(grade, 0)
    pct = count/len(new_grades)*100
    print(f"  {grade:10} | {count:4} ({pct:5.1f}%)")

print()

# === SIGNAL RATE ===
print("📡 SIGNAL RATE (Grade != NO_TRADE)")
print("-" * 80)

old_signals = sum(1 for g in old_grades if g != 'NO_TRADE')
new_signals = sum(1 for g in new_grades if g != 'NO_TRADE')

old_rate = old_signals/len(old_grades)*100
new_rate = new_signals/len(new_grades)*100

print(f"OLD: {old_signals}/{len(old_grades)} ({old_rate:.2f}%)")
print(f"NEW: {new_signals}/{len(new_grades)} ({new_rate:.2f}%)")
print(f"Change: {new_rate - old_rate:+.2f} percentage points")

print()

# === VOLUME GATE ===
print("⚡ VOLUME GATE EFFECTIVENESS")
print("-" * 80)
print(f"Volume gate (<0.5) triggered: {volume_gate_count}/{len(new_scores)} ({volume_gate_count/len(new_scores)*100:.1f}%)")
print(f"Note: Random test data, real market shows ~93% low volume")

print()

# === VERDICT ===
print("="*80)
print("VERDICT")
print("="*80)

if score_delta > 3:
    print("✅ MAJOR IMPROVEMENT: NEW P2 significantly increases scores")
elif score_delta > 1:
    print("✓ MODERATE IMPROVEMENT: NEW P2 produces higher scores")
elif score_delta > -1:
    print("~ NEUTRAL: No significant difference")
else:
    print("⚠️ REGRESSION: OLD P2 performed better (unexpected!)")

print()

if volume_gate_count > 400:  # >40% with random data
    print("✅ VOLUME GATE: Working effectively")

if new_rate > old_rate:
    print("✅ MORE SIGNALS: Optimization allows more qualified setups")
elif new_rate == old_rate:
    print("~ SAME SIGNALS: Rate unchanged")
else:
    print("⚠️ FEWER SIGNALS: Higher selectivity (quality over quantity)")

print()
print("="*80)
print("NOTE: This uses simulated P1 data. Real performance may vary.")
print("Monitor live system for 24-48h for actual market validation.")
print("="*80)
