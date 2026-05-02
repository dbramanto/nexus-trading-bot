# NEXUS v2.0 - Complete System Documentation

**Last Updated:** May 2, 2026  
**System Status:** Production Ready  
**Version:** 2.0 (LONG-only, Adaptive Sizing)

## 🎯 SYSTEM OVERVIEW
NEXUS v2.0 is an automated cryptocurrency futures trading system running on Binance Futures, designed for LONG-only momentum trading on top-performing altcoins.

### Core Identity
- Strategy Type: Momentum-based LONG positions only
- Universe: Dynamic top 10 gainers (24h % change)
- Position Sizing: 5% of balance (adaptive)
- Leverage: 1-3x (inverse to score quality)
- Notifications: Real-time Telegram alerts

## 📊 CURRENT CONFIGURATION

### Trading Parameters
Balance: $10,000 (paper)
Position: 5% = $500 per trade
Leverage: 1-3x (score-based)
- Score 70+: 3x → $500 pos, $167 margin (1.67%)
- Score 60-69: 2x → $500 pos, $250 margin (2.50%)
- Score <60: 1x → $500 pos, $500 margin (5.00%)

### Risk Management
Stop Loss: 10% | Take Profit: 25% | Max Hold: 4h | Max Positions: 1

## 📈 PERFORMANCE (May 2, 2026)

Total Trades: 68
Strategy Evolution:
  - Trades 1-5 (Apr 30): SHORT trades (pre-LONG-only)
  - Trades 6-68 (May 1+): LONG ONLY (current)

Current Strategy (LONG-only since May 1):
  LONG: 63 trades (100% of new trades)
  Win Rate: 50.8%
  PnL: +$10.88
  Expectancy: +$0.17/trade

Note: 5 SHORT trades are HISTORICAL from before May 1 filter.
System NO LONGER executes SHORT - all BEARISH signals rejected.

## 🏗️ ARCHITECTURE

P1 (Indicators) → P2 (Scoring 0-100) → P3 (Strategy) → P4 (Execution)

Key Files:
- forward_test_runner_dual_optimized.py (main)
- core/paper_trader.py (positions + notifications)
- config/settings.yaml (Telegram)
- data/paper_trades_top_gainers.csv (history)

## 📱 NOTIFICATIONS

Entry: paper_trader.py:83 (🟢 ENTRY)
Exit: paper_trader.py:190 (✅/❌ EXIT)
Daily: scripts/daily_report.py (07:00 WIB)

## 🔄 TRADE LIFECYCLE

1. Scanner → Top 10 gainers
2. P1 → Analyze indicators
3. P2 → Score (0-100)
4. P3 → Evaluate (BEARISH = reject)
5. If ACCEPT → Adaptive position → Open → Notify
6. Monitor → TP/SL/MAX_HOLD → Close → Notify
7. Balance auto-updates → Next trade uses new balance

## 🛠️ MAINTENANCE

Daily: 07:00 daily report (auto)
Health: systemctl status nexus-dual.service
Logs: tail -f logs/nexus_dual_mode.log

## 💰 LIVE TRADING (When Ready)

Minimum: $500 (recommended)
Requirements: 200+ trades, 60%+ WR, proven strategy

## 📞 COMMANDS

Service: sudo systemctl restart nexus-dual.service
Logs: tail -100 logs/nexus_dual_mode.log | grep ERROR
Data: tail -20 data/paper_trades_top_gainers.csv
Health: systemctl is-active nexus-dual.service

---
Last Review: May 2, 2026 | Status: ✅ Production Ready
