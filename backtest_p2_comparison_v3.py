"""
Backtest Comparison: OLD P2 vs NEW P2
Using REAL P1 structure from shadow logs.
"""

import sys
sys.path.insert(0, '/home/nexus/nexus_bot')

import json
import numpy as np
from collections import Counter

print("="*80)
print("BACKTEST COMPARISON: OLD P2 vs NEW P2 SCORING")
print("="*80)
print()

# Load REAL P1 snapshots from shadow logs
print("Loading real P1 snapshots from shadow logs...")

all_p1_snapshots = []

for day in ['2024', '2025', '2026']:
    import os
    files = [f for f in os.listdir('data/shadow_logs') if f.startswith(f'{day}-')]
    
    for fname in files[:5]:  # Sample from multiple days
        fpath = f'data/shadow_logs/{fname}'
        if not os.path.exists(fpath):
            continue
        
        with open(fpath) as f:
            entries = [json.loads(line) for line in f if line.strip()]
        
        for entry in entries:
            p1 = entry.get('p1_snapshot')
            if p1:
                all_p1_snapshots.append(p1)

print(f"Loaded {len(all_p1_snapshots)} real P1 snapshots")

# Sample 1000 for testing
sample_size = min(1000, len(all_p1_snapshots))
np.random.seed(42)
sample_indices = np.random.choice(len(all_p1_snapshots), sample_size, replace=False)
p1_samples = [all_p1_snapshots[i] for i in sample_indices]

print(f"Testing on {len(p1_samples)} real market snapshots")
print()

# === TEST OLD P2 ===
print("📊 Testing OLD P2 (pre-optimization)...")

import importlib.util
spec = importlib.util.spec_from_file_location("scoring_engine_old", "scoring_engine_old.py")
scoring_old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scoring_old)

from config.strategy_config import NexusConfig
config = NexusConfig()

p2_old = scoring_old.ScoringEngine(config)

old_scores = []
old_grades = []

for p1 in p1_samples:
    # OLD P2 expects p1_reports with 'modules' key
    p1_reports = {'modules': p1}
    result = p2_old.score(p1_reports)
    old_scores.append(result['score'])
    old_grades.append(result['grade'])

print(f"  ✓ Scored {len(old_scores)} snapshots")
print()

# === TEST NEW P2 ===
print("📊 Testing NEW P2 (optimized)...")

from core.p2_supervisor.scoring_engine import ScoringEngine
p2_new = ScoringEngine(config)

new_scores = []
new_grades = []
volume_gate_count = 0

for p1 in p1_samples:
    # NEW P2 expects p1_snapshot directly
    result = p2_new.score(p1)
    new_scores.append(result['score'])
    new_grades.append(result['grade'])
    
    if 'Volume <0.5' in result.get('reject_reason', ''):
        volume_gate_count += 1

print(f"  ✓ Scored {len(new_scores)} snapshots")
print()

# === RESULTS ===
print("="*80)
print("COMPARISON RESULTS (REAL MARKET DATA)")
print("="*80)
print()

print("📊 SCORE DISTRIBUTION")
print("-" * 80)

print(f"OLD P2 (pre-optimization):")
print(f"  Mean:   {np.mean(old_scores):.2f}")
print(f"  Median: {np.median(old_scores):.2f}")
print(f"  Max:    {max(old_scores):.1f}")
print(f"  Min:    {min(old_scores):.1f}")
print(f"  Std:    {np.std(old_scores):.2f}")

print(f"\nNEW P2 (optimized):")
print(f"  Mean:   {np.mean(new_scores):.2f}")
print(f"  Median: {np.median(new_scores):.2f}")
print(f"  Max:    {max(new_scores):.1f}")
print(f"  Min:    {min(new_scores):.1f}")
print(f"  Std:    {np.std(new_scores):.2f}")

score_delta = np.mean(new_scores) - np.mean(old_scores)
pct_change = (score_delta / np.mean(old_scores) * 100) if np.mean(old_scores) > 0 else 0

print(f"\n📈 Mean Score Change: {score_delta:+.2f} points ({pct_change:+.1f}%)")

print()

# === SCORE BUCKETS ===
print("📊 SCORE DISTRIBUTION BUCKETS")
print("-" * 80)

def bucket_scores(scores):
    buckets = {
        '0': 0,
        '1-10': 0,
        '11-20': 0,
        '21-40': 0,
        '41-55': 0,
        '55-70': 0,
        '70+': 0
    }
    for s in scores:
        if s == 0: buckets['0'] += 1
        elif s <= 10: buckets['1-10'] += 1
        elif s <= 20: buckets['11-20'] += 1
        elif s <= 40: buckets['21-40'] += 1
        elif s <= 55: buckets['41-55'] += 1
        elif s <= 70: buckets['55-70'] += 1
        else: buckets['70+'] += 1
    return buckets

old_buckets = bucket_scores(old_scores)
new_buckets = bucket_scores(new_scores)

print("OLD P2:")
for bucket, count in old_buckets.items():
    pct = count/len(old_scores)*100
    print(f"  {bucket:8} | {count:4} ({pct:5.1f}%)")

print("\nNEW P2:")
for bucket, count in new_buckets.items():
    pct = count/len(new_scores)*100
    print(f"  {bucket:8} | {count:4} ({pct:5.1f}%)")

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
gate_pct = volume_gate_count/len(new_scores)*100
print(f"Volume gate (<0.5) triggered: {volume_gate_count}/{len(new_scores)} ({gate_pct:.1f}%)")
print(f"Expected from analysis: ~93%")

if gate_pct > 80:
    print("  ✓ Volume gate working as expected")
elif gate_pct > 50:
    print("  ~ Volume gate active but lower than expected")
else:
    print("  ⚠️ Volume gate lower than expected")

print()

# === VERDICT ===
print("="*80)
print("OPTIMIZATION VERDICT")
print("="*80)

if score_delta > 3:
    print("✅ MAJOR IMPROVEMENT: NEW P2 significantly boosts scores")
elif score_delta > 1:
    print("✓ MODERATE IMPROVEMENT: NEW P2 produces higher scores")
elif score_delta > -1:
    print("~ NEUTRAL: Minimal difference between versions")
else:
    print("⚠️ REGRESSION: OLD P2 scored higher (investigate!)")

print()

# Check if quality improved (higher tier distribution)
old_premium = old_dist.get('PREMIUM', 0) + old_dist.get('VALID', 0)
new_premium = new_dist.get('PREMIUM', 0) + new_dist.get('VALID', 0)

if new_premium > old_premium:
    print(f"✅ QUALITY: More PREMIUM/VALID grades ({new_premium} vs {old_premium})")
elif new_premium == old_premium:
    print(f"~ QUALITY: Same PREMIUM/VALID count ({new_premium})")
else:
    print(f"⚠️ QUALITY: Fewer PREMIUM/VALID grades ({new_premium} vs {old_premium})")

print()

# Summary
print("KEY CHANGES:")
print("  1. Momentum weight: 2x → 3x (should increase T1 scores)")
print("  2. Candle pattern: +5 → +8 pts (should increase T2 scores)")
print("  3. Volume gate: Reject vol <0.5 (should filter ~93% early)")
print()

print("="*80)
