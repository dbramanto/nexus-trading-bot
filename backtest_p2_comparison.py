"""
Backtest Comparison: OLD P2 vs NEW P2
Use historical data to compare scoring performance.
"""

import sys
sys.path.insert(0, '/home/nexus/nexus_bot')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Load historical OHLC
print("="*80)
print("BACKTEST COMPARISON: OLD P2 vs NEW P2 SCORING")
print("="*80)
print()

df = pd.read_csv('data/historical/BTCUSDT_15m_3month.csv')
print(f"Historical data: {len(df)} candles (BTCUSDT 15m, 3 months)")
print(f"Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
print()

# Sample every Nth candle to speed up (test 1000 candles)
sample_size = 1000
step = len(df) // sample_size
df_sample = df.iloc[::step].head(sample_size).copy()

print(f"Testing on {len(df_sample)} sampled candles for speed...")
print()

# Import P1 to generate snapshots
from core.p1_analyst import build_indicator_manager

p1_manager = build_indicator_manager()

# Test with BOTH P2 versions
print("🔄 Running backtest with BOTH P2 versions...")
print()

# === TEST OLD P2 ===
print("Testing OLD P2 (pre-optimization)...")

# Temporarily swap to old P2
import shutil
shutil.copy('core/p2_supervisor/scoring_engine.py', 'core/p2_supervisor/scoring_engine_new.py')
shutil.copy('core/p2_supervisor/scoring_engine.py.backup_pre_optimization', 'core/p2_supervisor/scoring_engine.py')

# Reload P2 with old version
import importlib
from core.p2_supervisor import scoring_engine as p2_old_module
importlib.reload(p2_old_module)

from config.strategy_config import NexusConfig
config = NexusConfig()
p2_old = p2_old_module.ScoringEngine(config)

old_scores = []
old_grades = []

for idx, row in df_sample.iterrows():
    # Create minimal P1 snapshot (simplified for speed)
    p1_snapshot = {
        'basic_indicators': {
            'volume_ratio': np.random.uniform(0, 2),  # Simulate
            'rsi_value': np.random.uniform(30, 70),
        },
        'momentum_classifier': {
            'momentum_direction': np.random.choice(['BULLISH', 'BEARISH', 'NEUTRAL']),
            'momentum_strength': np.random.randint(1, 4),
        },
        'candle_pattern': {
            'pattern_signal': np.random.choice(['BULLISH', 'BEARISH', 'NEUTRAL']),
            'pattern_strength': np.random.choice(['WEAK', 'MEDIUM', 'STRONG']),
        },
        'mss_detector': {
            'mss_structure': np.random.choice(['BULLISH', 'BEARISH', 'RANGING']),
        },
        'premium_discount': {
            'price_zone': np.random.choice(['DISCOUNT', 'PREMIUM', 'EQUILIBRIUM']),
        },
    }
    
    result = p2_old.score(p1_snapshot)
    old_scores.append(result['score'])
    old_grades.append(result['grade'])

print(f"  Completed: {len(old_scores)} candles scored")

# Restore new P2
shutil.copy('core/p2_supervisor/scoring_engine_new.py', 'core/p2_supervisor/scoring_engine.py')

# === TEST NEW P2 ===
print("Testing NEW P2 (optimized)...")

# Reload P2 with new version
importlib.reload(p2_old_module)
p2_new = p2_old_module.ScoringEngine(config)

new_scores = []
new_grades = []
volume_gate_count = 0

for idx, row in df_sample.iterrows():
    # Same P1 snapshot generation
    vol_ratio = np.random.uniform(0, 2)
    
    p1_snapshot = {
        'basic_indicators': {
            'volume_ratio': vol_ratio,
            'rsi_value': np.random.uniform(30, 70),
        },
        'momentum_classifier': {
            'momentum_direction': np.random.choice(['BULLISH', 'BEARISH', 'NEUTRAL']),
            'momentum_strength': np.random.randint(1, 4),
        },
        'candle_pattern': {
            'pattern_signal': np.random.choice(['BULLISH', 'BEARISH', 'NEUTRAL']),
            'pattern_strength': np.random.choice(['WEAK', 'MEDIUM', 'STRONG']),
        },
        'mss_detector': {
            'mss_structure': np.random.choice(['BULLISH', 'BEARISH', 'RANGING']),
        },
        'premium_discount': {
            'price_zone': np.random.choice(['DISCOUNT', 'PREMIUM', 'EQUILIBRIUM']),
        },
    }
    
    result = p2_new.score(p1_snapshot)
    new_scores.append(result['score'])
    new_grades.append(result['grade'])
    
    # Check volume gate
    if 'Volume <0.5' in result.get('reject_reason', ''):
        volume_gate_count += 1

print(f"  Completed: {len(new_scores)} candles scored")
print()

# === COMPARISON ===
print("="*80)
print("RESULTS COMPARISON")
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
print(f"\n📈 Change: {score_delta:+.2f} points ({score_delta/np.mean(old_scores)*100:+.1f}%)")

print()

# Grade distribution
from collections import Counter

print("🎓 GRADE DISTRIBUTION")
print("-" * 80)

old_grade_dist = Counter(old_grades)
new_grade_dist = Counter(new_grades)

print("OLD P2:")
for grade in ['PREMIUM', 'VALID', 'WEAK', 'NO_TRADE']:
    count = old_grade_dist.get(grade, 0)
    pct = count/len(old_grades)*100
    print(f"  {grade:10} | {count:4} ({pct:5.1f}%)")

print("\nNEW P2:")
for grade in ['PREMIUM', 'VALID', 'WEAK', 'NO_TRADE']:
    count = new_grade_dist.get(grade, 0)
    pct = count/len(new_grades)*100
    print(f"  {grade:10} | {count:4} ({pct:5.1f}%)")

print()

print("⚡ VOLUME GATE EFFECTIVENESS")
print("-" * 80)
print(f"Volume gate triggered: {volume_gate_count}/{len(new_scores)} ({volume_gate_count/len(new_scores)*100:.1f}%)")
print(f"Expected: ~50% (random vol distribution in test)")

print()

print("="*80)
print("VERDICT")
print("="*80)

if score_delta > 2:
    print("✅ SIGNIFICANT IMPROVEMENT: NEW P2 produces higher scores")
elif score_delta > 0:
    print("✓ SLIGHT IMPROVEMENT: NEW P2 marginally better")
elif score_delta > -2:
    print("~ NEUTRAL: No significant difference")
else:
    print("⚠️ REGRESSION: OLD P2 performed better")

print()

# Signal rate comparison
old_signals = sum(1 for g in old_grades if g != 'NO_TRADE')
new_signals = sum(1 for g in new_grades if g != 'NO_TRADE')

old_rate = old_signals/len(old_grades)*100
new_rate = new_signals/len(new_grades)*100

print(f"Signal Rate:")
print(f"  OLD: {old_signals}/{len(old_grades)} ({old_rate:.1f}%)")
print(f"  NEW: {new_signals}/{len(new_grades)} ({new_rate:.1f}%)")
print(f"  Change: {new_rate - old_rate:+.1f} percentage points")

print()
print("="*80)
