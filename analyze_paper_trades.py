"""
Analyze paper trading results on top gainers
"""

import pandas as pd
import numpy as np

print("="*80)
print("PAPER TRADING ANALYSIS — Top Gainers")
print("="*80)
print()

# Load paper trades
try:
    df = pd.read_csv('data/paper_trades_top_gainers.csv')
except FileNotFoundError:
    print("⏳ No trades yet. Run paper trader first!")
    exit()

print(f"Total paper trades: {len(df)}")
print()

# Overall stats
wins = df[df['outcome'] == 'WIN']
losses = df[df['outcome'] == 'LOSS']

wr = len(wins) / len(df) * 100
total_pnl = df['pnl_usd'].sum()
avg_win = wins['pnl_usd'].mean() if len(wins) > 0 else 0
avg_loss = losses['pnl_usd'].mean() if len(losses) > 0 else 0

print("📊 PERFORMANCE")
print("-" * 80)
print(f"Win Rate:    {wr:.1f}% ({len(wins)}W / {len(losses)}L)")
print(f"Total PnL:   ${total_pnl:+.2f}")
print(f"Avg Win:     ${avg_win:+.2f}")
print(f"Avg Loss:    ${avg_loss:+.2f}")
print(f"Risk:Reward: 1:{abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "")
print()

# Exit reasons
print("🚪 EXIT REASONS")
print("-" * 80)
for reason, count in df['exit_reason'].value_counts().items():
    pct = count/len(df)*100
    print(f"  {reason:15} | {count:3} ({pct:5.1f}%)")
print()

# Best/worst trades
print("🏆 TOP 5 WINS")
print("-" * 80)
if len(wins) > 0:
    top_wins = wins.nlargest(min(5, len(wins)), 'pnl_usd')[['symbol', 'pnl_usd', 'pnl_pct', 'exit_reason']]
    for _, row in top_wins.iterrows():
        print(f"  {row['symbol']:12} | ${row['pnl_usd']:+7.2f} ({row['pnl_pct']:+6.1f}%) | {row['exit_reason']}")
else:
    print("  No wins yet")
print()

print("💀 TOP 5 LOSSES")
print("-" * 80)
if len(losses) > 0:
    top_losses = losses.nsmallest(min(5, len(losses)), 'pnl_usd')[['symbol', 'pnl_usd', 'pnl_pct', 'exit_reason']]
    for _, row in top_losses.iterrows():
        print(f"  {row['symbol']:12} | ${row['pnl_usd']:+7.2f} ({row['pnl_pct']:+6.1f}%) | {row['exit_reason']}")
else:
    print("  No losses yet")
print()

# Score vs Outcome
print("🎯 P2 SCORE vs OUTCOME")
print("-" * 80)
win_scores = wins['p2_score'].values
loss_scores = losses['p2_score'].values

if len(win_scores) > 0:
    print(f"Win avg score:  {win_scores.mean():.1f}")
else:
    print("Win avg score:  N/A")
    
if len(loss_scores) > 0:
    print(f"Loss avg score: {loss_scores.mean():.1f}")
else:
    print("Loss avg score: N/A")
print()

print("="*80)
print(f"✅ Need 50-100 trades for statistical significance (current: {len(df)})")
print("="*80)
