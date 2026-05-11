# NEXUS v2.0 - Phase 1 Context (30 Apr 2026, 12:38 WIB)

## 📍 CURRENT STATUS

**System State:**
- VPS: root@vps69547
- Path: /home/nexus/nexus_bot
- Service: nexus-dual.service (ACTIVE, running normally)
- Current Performance: 7 closed trades, 71.4% WR, +$104.82 PnL
- **CRITICAL ISSUE**: 0.07% accept rate (1/1344 scans) - filters TOO STRICT
- Main Blocker: Heiken Ashi alignment requirement

**Current Config (Interim):**
- SL: 4%, TP: 10%, Hold: 24h
- Leverage: Not optimized yet
- Position size: Not optimized yet
- Status: Temporary, pending Phase 1 validation

---

## ✅ PHASE 1 PART 1 - COMPLETED (30 Apr 2026, 12:38 WIB)

**Downloaded Historical Data:**
- 14 symbols (MODE A stable coins)
- 30 days × M15 timeframe
- 40,320 total candles
- 0 failures
- Method: Direct HTTP (requests library)

**Files in data/historical/:**
- BTCUSDT_M15_30d.csv (170K, 2880 candles)
- ETHUSDT_M15_30d.csv (173K, 2880 candles)
- BNBUSDT_M15_30d.csv (157K, 2880 candles)
- SOLUSDT_M15_30d.csv (150K, 2880 candles)
- XRPUSDT_M15_30d.csv (162K, 2880 candles)
- ADAUSDT_M15_30d.csv (163K, 2880 candles)
- AVAXUSDT_M15_30d.csv (147K, 2880 candles)
- DOTUSDT_M15_30d.csv (149K, 2880 candles)
- MATICUSDT_M15_30d.csv (158K, 2880 candles)
- LINKUSDT_M15_30d.csv (149K, 2880 candles)
- UNIUSDT_M15_30d.csv (147K, 2880 candles)
- ATOMUSDT_M15_30d.csv (149K, 2880 candles)
- LTCUSDT_M15_30d.csv (149K, 2880 candles)
- ARBUSDT_M15_30d.csv (162K, 2880 candles)
- download_summary.json

---

## 🎯 NEXT TASK: Phase 1 Part 2 - Filter Analysis

**Objective:** Analyze Heiken Ashi filter effectiveness

**What to Build:**
Script: scripts/analyze_filter_effectiveness.py

Tasks:
1. Load CSV data from data/historical/
2. Calculate Heiken Ashi candles
3. Simulate P2 scoring (reproduce NEXUS logic)
4. Test HA filter impact:
   - WR with HA filter
   - WR without HA filter
   - Optimal Grade threshold
5. Calculate volatility metrics
6. Output: optimized_config.json

**Expected Output:**
- Is HA filter helping or hurting?
- Optimal acceptance threshold
- Recommended filter configuration

---

## 📊 KEY DIAGNOSTIC FINDINGS

**Current Filter Issue:**
- Accept Rate: 0.07% (1 accept in 1344 scans)
- Example: NAORISUSDT scored 65 (WEAK), bias BULLISH
- P3 wanted to LONG, but HA was BEARISH
- Result: Signal REJECTED due to HA conflict

**Current Performance (Small Sample):**
- MODE A: 100% WR (1 trade)
- MODE B: 66.7% WR (6 trades)
- Overall: 71.4% WR (7 trades)
- Total PnL: +$104.82

**Question:** Is high WR due to good filters or just luck (small sample)?

---

## 🎯 OPTIMIZATION STRATEGY

**Chosen Approach:** Option B (Data-Driven)

Why NOT Option A (Relax now):
- 30% risk WR drops <35%
- No data justification
- Could collect bad ML training data

Why NOT Option C (Hybrid):
- Moderate config still a guess
- Split focus

Why Option B:
- Data validates before deploy
- 70% success probability
- High confidence WR maintained
- Reproducible & scientific

**Timeline:**
- Day 1 (30 Apr): Download ✅ + Analysis ⏳
- Day 2 (1 May): Deploy optimized config
- Day 2-16: Collect 100 trades
- Day 16 (15 May): Sprint 3 complete

---

## 🔧 TECHNICAL NOTES

**NEXUS Connection:**
- Library: python_binance 1.0.36
- Method: Custom BinanceClientWrapper
- Location: execution/binance_client.py

**Analysis Scripts:**
- Use: requests library (already available)
- Method: Direct HTTP to Binance API
- Impact: ZERO (separate from NEXUS trading)

**Important:**
- NEXUS still running normally
- No service restart needed
- Analysis is offline/separate

---

## 📋 DUAL-MODE CONFIG (Designed, Not Deployed)

Pending Phase 1 validation:

MODE A (Stable):
- Symbols: BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, MATIC, LINK, UNI, ATOM, LTC, ARB
- Leverage: 8x
- SL: 2.5%, TP: 5%, Hold: 4h
- Position: $1000, Max: 5
- Risk: $25/trade (0.25% balance)

MODE B (Gainers):
- Symbols: Dynamic top 10
- Leverage: 3x
- SL: 5%, TP: 10%, Hold: 4h
- Position: $500, Max: 5
- Risk: $25/trade (0.25% balance)

Status: Will adjust based on Phase 1 results

---

## 🚀 READY FOR NEW CHAT

**Files Available:**
- ✅ data/historical/*.csv (30 days M15 data)
- ✅ scripts/download_binance_data_simple.py
- ✅ PHASE1_CONTEXT_FOR_NEXT_CHAT.md (this file)

**Next Step:**
Build filter analysis script to determine optimal configuration

**Start New Chat With:**
"Continue NEXUS Phase 1 Part 2: Filter Effectiveness Analysis. Data ready in data/historical/. Need to analyze HA filter impact and derive optimal config."

---

END OF CONTEXT FILE
