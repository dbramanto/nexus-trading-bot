# NEXUS v2.0 - MASTER ROADMAP
# Version: 3.0 (Final Consolidated)
# Created: May 10, 2026
# Methodology: Sprint-based (progress gates, not dates)
# Single Source of Truth - Do not create other roadmap documents

================================================================================
PHILOSOPHY
================================================================================

"Done when criteria met, not when deadline arrives"

- Sprint gates are DATA-DRIVEN and MEASURABLE
- No arbitrary deadlines
- Progress at market pace
- Quality over speed

================================================================================
CURRENT STATE (May 10, 2026)
================================================================================

System:  NEXUS v2.0 - Paper Trading
Mode:    Top Gainers Momentum (LONG-only)
Balance: $10,607.39 (reset to $1,000 in Sprint 2)
Trades:  4 clean closed (collecting)
Sprint:  SPRINT 0 - Stabilization (active)

================================================================================
SPRINT 0: STABILIZATION
================================================================================

STATUS: IN PROGRESS

GOAL: Prove system stable 72h+ without crashes

EXIT CRITERIA (ALL must be met):
  [ ] 72 consecutive hours without crash
  [ ] 0 duplicate entries in CSV
  [ ] Hourly reports sending correctly
  [ ] Daily reports sending correctly
  [ ] State persists correctly after restart
  [ ] 0 errors in recent 200 log lines

BUGS FIXED (Complete):
  [x] CSV overwrite on restart
  [x] open_positions not loaded on startup
  [x] closed_trades not saved to CSV
  [x] closed_trades not loaded on startup
  [x] balance not restored on restart
  [x] get_stats reads memory only
  [x] CSV 402 duplicates
  [x] KeyError double-close crash
  [x] candle_str TypeError (str vs int)
  [x] entry_time type mismatch
  [x] Conditional exit (4h to 48h)
  [x] _save_to_csv duplicate growth
  [x] TRACE logs causing log bloat
  [x] Log rotation implemented

DO NOT during Sprint 0:
  - Change any parameters
  - Add any features
  - Modify any code

================================================================================
SPRINT 1: DATA COLLECTION & VALIDATION
================================================================================

STATUS: PENDING (after Sprint 0)

GOAL: Collect 50 clean closed trades, establish baseline

ENTRY CRITERIA:
  - Sprint 0 all exit criteria met

EXIT CRITERIA:
  [ ] 50 clean closed trades
  [ ] WR calculated
  [ ] Expectancy calculated
  [ ] Exit reason distribution analyzed
  [ ] Score range performance analyzed

CHECKPOINTS (not gates):
  10 closes = Preliminary glimpse
  30 closes = Early trends visible
  50 closes = Sprint 1 COMPLETE

PARAMETERS (unchanged during Sprint 1):
  Universe:  Top 10 gainers (Volume > $50M)
  Score:     >= 60
  Leverage:  2x (score 60-69) / 3x (score 70+)
  SL:        -10% price (pre-fix, noted)
  TP:        +25% price (pre-fix, noted)
  Hold:      Conditional 48h if not in profit
  Direction: LONG only

DECISION AT SPRINT 1 EXIT:
  WR >= 50% -> Proceed to Sprint 2
  WR 40-50% -> Investigate, decide
  WR < 40%  -> Root cause analysis first

================================================================================
SPRINT 2: PARAMETER OPTIMIZATION
================================================================================

STATUS: PLANNED

GOAL: Implement proper trade parameters, reset for stress test

ENTRY CRITERIA:
  - Sprint 1 complete (50 closes)
  - Performance baseline established

DELIVERABLES:

  2A. Balance Reset
      To: $1,000
      Why: Realistic stress test constraint

  2B. SL/TP Leverage-Adjusted
      Current (wrong):
        sl = entry x (1 - 0.10)       <- -10% price
        tp = entry x (1 + 0.25)       <- +25% price

      Fixed (correct):
        sl = entry x (1 - 0.10/lev)   <- -10% PnL always
        tp = entry x (1 + 0.25/lev)   <- +25% PnL always

  2C. Score-Based Position Sizing
      Score 60-69:
        Size: 5% balance ($50)
        Leverage: 2x
        SL: -10% PnL
        TP: +25% PnL

      Score 70+:
        Size: 10% balance ($100)
        Leverage: 3x
        SL: -10% PnL
        TP: +30% PnL

  2D. Position Limits
      Max simultaneous: 5 positions
      Max total exposure: 150% balance

EXIT CRITERIA:
  [ ] Balance reset to $1,000
  [ ] SL/TP leverage-adjusted verified
  [ ] Score-based sizing working
  [ ] Max 5 positions enforced
  [ ] 20 trades with new parameters, no new bugs

================================================================================
SPRINT 3: SHORT IMPLEMENTATION
================================================================================

STATUS: PLANNED

GOAL: Enable SHORT signals, double opportunity universe

ENTRY CRITERIA:
  - Sprint 2 complete
  - LONG WR >= 50% consistently proven

DESIGN:
  Universe:  SAME (top gainers, not top losers)
  Direction: ICT/SMC signals determine LONG or SHORT
  
  SHORT parameters (leverage-adjusted):
    SL: +10% PnL above entry
    TP: -25% PnL below entry

  SHORT guard layers:
    - Funding rate check (negative = avoid short)
    - Not extreme oversold (bounce risk)
    - Strong bearish CHoCH/BOS confirmed
    - Volume confirmation

EXIT CRITERIA:
  [ ] SHORT executing correctly
  [ ] 30 SHORT trades collected
  [ ] SHORT WR >= 45%
  [ ] No regressions in LONG logic

================================================================================
SPRINT 4: ENHANCEMENTS
================================================================================

STATUS: PLANNED

GOAL: Advanced features for robustness

ENTRY CRITERIA:
  - Sprint 3 complete
  - 100+ total clean trades

DELIVERABLES:
  - Market Regime Detection
      IF BTC 24h < -5%: Defensive mode
        -> Raise threshold to 70+
        -> Reduce size 50%
      IF normal: Standard mode

  - Trailing Stop
      Activate: After +15% PnL
      Trail: -15% from peak

  - Correlation Filter
      Max 2 correlated positions (>0.7)

  - HTF Structure Module (currently placeholder)

  - Walk-Forward Validation

================================================================================
SPRINT 5: ML LAYER (VajraBrain)
================================================================================

STATUS: FUTURE

ENTRY CRITERIA:
  - Sprint 4 complete
  - 200+ labeled trades
  - Multiple market conditions covered
  - Both LONG and SHORT data available

FOCUS: STATISTICAL LEARNING from historical data
  NOT contextual reasoning (that is Sprint 6)
  NOT external context (news, events)

DELIVERABLES:
  - Adaptive scoring weights (learned from data)
  - Dynamic position sizing by ML confidence
  - Statistical pattern recognition
  - Backtesting framework
  - Regime classification (bull/bear/ranging)

CLEAR BOUNDARY:
  ML = learns from PAST trade data (statistical)
  AI Agent (Sprint 6) = reasons about CONTEXT (qualitative)
  These are COMPLEMENTARY, not overlapping!

================================================================================
DECISIONS LOG
================================================================================

D1: Universe = All coin types (no filtering by type)
    Why: Small caps ARE natural top gainers
         Data: 51.2% WR, +$615 from small caps
         Filtering by type = almost no trades

D2: Leverage max = 3x
    Why: Altcoins can drop 20-30% in 1 hour
         5x = liquidation risk
         3x = sweet spot for momentum alts

D3: SL/TP = PnL-based (leverage-adjusted)
    Why: Current -10% price = -20% PnL (wrong!)
         Must always be -10% PnL regardless of leverage

D4: SHORT = Same universe (top gainers)
    Why: Top losers have different dynamics
         ICT/SMC finds reversal SHORTs in gainers naturally

D5: Balance = $1,000 for stress test
    Why: Realistic individual trader constraint
         Forces disciplined position sizing

D6: Max positions = 5
    Why: Current 24 positions = 240% exposure (dangerous!)
         5 positions with $1k = ~50-100% exposure (safe)

D7: Sprint-based roadmap (no date targets)
    Why: Progress is data-driven, not calendar-driven
         Avoids artificial deadline pressure

================================================================================
PERFORMANCE BASELINE
================================================================================

OLD DATA (Pre-threshold fix):
  VALID (Score >= 60):
    Trades: 55
    WR: 54.5%
    Expectancy: $8.62/trade  <- TARGET

  WEAK (Score < 60):
    Trades: 67
    WR: 49.3%
    Expectancy: $0.55/trade

CLEAN DATA (Post-fix, May 5+):
  Closed: 4 (collecting in Sprint 1)

TARGETS (Sprint 2+):
  WR: >= 50% all conditions
  WR: >= 55% normal market
  Expectancy: >= $8/trade
  TP hit rate: >= 15%

================================================================================
KNOWN RISKS
================================================================================

HIGH (Sprint 4):
  - LONG-only vulnerable in dump market
  - No automated crash alerts

MEDIUM (Sprint 2-3):
  - SL/TP not leverage-adjusted yet
  - No hard position limit yet
  - No unit tests

LOW (When convenient):
  - Settings.yaml legacy file (unused)
  - Backup files accumulating
  - Old trades missing SL/TP data

================================================================================
ESCALATION PROTOCOL
================================================================================

INTERVENE IMMEDIATELY if:
  - Service crashed and not auto-recovering
  - No hourly report for 2+ hours
  - CSV duplicates growing again
  - FATAL error in logs

DO NOT INTERVENE for:
  - WR fluctuation (normal)
  - Consecutive losses (normal)
  - Low weekend activity (normal)
  - Score variations (normal)

================================================================================
DOCUMENT STRUCTURE
================================================================================

/home/nexus/nexus_bot/
  NEXUS_MASTER_ROADMAP.md    <- THIS FILE (single source of truth)

docs/active/                 <- Currently nothing (master is in root)
docs/archive/                <- Historical session summaries
docs/templates/              <- Audit & standards templates

Rule: Update ONLY this file when decisions change.
      Do not create new roadmap documents.

================================================================================
END OF MASTER ROADMAP v3.0
================================================================================

================================================================================
SPRINT 6: AI AGENT AUGMENTATION (FUTURE CONCEPT)
================================================================================

STATUS: CONCEPT ONLY - Do not implement yet

ENTRY CRITERIA:
  - Sprint 5 complete
  - 500+ clean trades collected
  - System proven profitable (real money)
  - Budget available for API costs

RELATIONSHIP WITH SPRINT 5 (ML):
  NOT overlapping - COMPLEMENTARY!
  
  ML (Sprint 5) = Statistical reasoning
    "This pattern won 73% historically"
    Fast, cheap, deterministic
    
  AI Agent (Sprint 6) = Contextual reasoning
    "Score good BUT FOMC today = skip"
    Handles unseen situations
    External context aware

CONCEPT: AI-AUGMENTED HYBRID (not full replacement)
  Keep rule-based for speed & consistency (P1, P2)
  ML improves scoring statistically (Sprint 5)
  AI adds contextual judgment (Sprint 6)

ARCHITECTURE:

  P1 ANALYST: Keep rule-based ✅
    Indicators = math, no AI needed
    Fast, cheap, reliable

  P2 SUPERVISOR: Keep rule-based ✅
    Scoring engine unchanged
    Consistent, auditable

  P3 MANAGER: Hybrid (rule + AI)
    Rule check first (threshold, guards)
    IF score >= 65: AI validation call
    AI can CONFIRM or VETO with reasoning
    Model: Claude Haiku (fast, cheap)

  P4 AUDITOR: Full AI ✅
    Daily performance review (async)
    Pattern identification in losses
    Improvement recommendations
    Model: Claude Sonnet (better reasoning)

FLOW:
  Market Data
    → P1 (rule-based, fast)
    → P2 (rule-based, scoring)
    → Score >= 65?
        NO  → SKIP (no AI call, saves cost)
        YES → AI Validator (P3 hybrid)
                → CONFIRM → Execute
                → VETO    → Skip + log reason
    → P4 AI Auditor (daily, async)

COST ESTIMATE:
  Full AI:   ~$2,300/month (not viable)
  Hybrid:    ~$29/month (viable!)
    Only AI call when score >= 65
    ~5% of signals = ~48 calls/day

BENEFITS:
  Contextual understanding beyond rules
  Adaptive to changing market conditions
  Holistic multi-factor reasoning
  Self-improving via P4 feedback loop

RISKS TO MANAGE:
  LLM non-determinism (use temp=0)
  Hallucination risk (structured output)
  API latency (2-10s per call)
  Cost creep (monitor daily)
  Over-reliance on AI reasoning

IMPLEMENTATION ORDER (when ready):
  Step 1: P4 AI Auditor (lowest risk)
          Daily async job, no trading impact
  Step 2: P3 AI Validator (A/B test)
          Compare with/without AI decisions
  Step 3: Evaluate P2 augmentation
          Based on Step 2 results only

DECISION POINT:
  Only proceed if Step 1+2 prove AI adds value
  Measured by: WR improvement >= 5%
  Cost must be covered by profit

================================================================================

================================================================================
SPRINT 6: AI AGENT AUGMENTATION (FUTURE CONCEPT)
================================================================================

STATUS: CONCEPT ONLY - Do not implement yet

ENTRY CRITERIA:
  - Sprint 5 complete
  - 500+ clean trades collected
  - System proven profitable (real money)
  - Budget available for API costs

RELATIONSHIP WITH SPRINT 5 (ML):
  NOT overlapping - COMPLEMENTARY!
  
  ML (Sprint 5) = Statistical reasoning
    "This pattern won 73% historically"
    Fast, cheap, deterministic
    
  AI Agent (Sprint 6) = Contextual reasoning
    "Score good BUT FOMC today = skip"
    Handles unseen situations
    External context aware

CONCEPT: AI-AUGMENTED HYBRID (not full replacement)
  Keep rule-based for speed & consistency (P1, P2)
  ML improves scoring statistically (Sprint 5)
  AI adds contextual judgment (Sprint 6)

ARCHITECTURE:

  P1 ANALYST: Keep rule-based ✅
    Indicators = math, no AI needed
    Fast, cheap, reliable

  P2 SUPERVISOR: Keep rule-based ✅
    Scoring engine unchanged
    Consistent, auditable

  P3 MANAGER: Hybrid (rule + AI)
    Rule check first (threshold, guards)
    IF score >= 65: AI validation call
    AI can CONFIRM or VETO with reasoning
    Model: Claude Haiku (fast, cheap)

  P4 AUDITOR: Full AI ✅
    Daily performance review (async)
    Pattern identification in losses
    Improvement recommendations
    Model: Claude Sonnet (better reasoning)

FLOW:
  Market Data
    → P1 (rule-based, fast)
    → P2 (rule-based, scoring)
    → Score >= 65?
        NO  → SKIP (no AI call, saves cost)
        YES → AI Validator (P3 hybrid)
                → CONFIRM → Execute
                → VETO    → Skip + log reason
    → P4 AI Auditor (daily, async)

COST ESTIMATE:
  Full AI:   ~$2,300/month (not viable)
  Hybrid:    ~$29/month (viable!)
    Only AI call when score >= 65
    ~5% of signals = ~48 calls/day

BENEFITS:
  Contextual understanding beyond rules
  Adaptive to changing market conditions
  Holistic multi-factor reasoning
  Self-improving via P4 feedback loop

RISKS TO MANAGE:
  LLM non-determinism (use temp=0)
  Hallucination risk (structured output)
  API latency (2-10s per call)
  Cost creep (monitor daily)
  Over-reliance on AI reasoning

IMPLEMENTATION ORDER (when ready):
  Step 1: P4 AI Auditor (lowest risk)
          Daily async job, no trading impact
  Step 2: P3 AI Validator (A/B test)
          Compare with/without AI decisions
  Step 3: Evaluate P2 augmentation
          Based on Step 2 results only

DECISION POINT:
  Only proceed if Step 1+2 prove AI adds value
  Measured by: WR improvement >= 5%
  Cost must be covered by profit

================================================================================

================================================================================
MOMENTUM SYSTEM REDESIGN (Approved: May 11, 2026)
================================================================================

PHILOSOPHY:
  "Ride the wave - never chase it"
  "Exit dead momentum, immediately hunt fresh"
  Main TF: M15

COMPLETE MOMENTUM LIFECYCLE:

PHASE 1 - DETECTION (Entry Filter):
  Criteria (ALL must pass):
  - Freshness: Coin < 2h in top gainers
  - Rate of Change: 15m price change positive
  - Volume: Current > 2x average volume
  - Structure: Price > MA20
  - Score: >= 65 (raised from 60)
  - Not just exited this cycle

PHASE 2 - ENTRY CONFIRMATION:
  P1 → P2 scoring (existing)
  PLUS momentum filter above
  Both must pass → EXECUTE

PHASE 3 - HOLD MONITORING (Every M15 cycle):
  Check momentum health:
  
  ALIVE (all green → HOLD):
  - Volume > 50% of entry volume
  - Price > MA20
  - Rate of change positive
  - No bearish CHoCH
  
  WARNING (1-2 yellow → MONITOR):
  - Volume 25-50% of entry
  - Price at MA20
  - Rate of change flat
  
  DEAD (any red → EXIT NOW):
  - Volume < 25% of entry
  - Price break below MA20
  - Bearish CHoCH confirmed
  - Rate of change negative 3 candles

PHASE 4 - EXIT TRIGGERS:
  Priority order:
  1. SL hit (price protection)
  2. TP hit (profit target)
  3. Momentum DEAD (new! exit early)
  4. Time 48h (last resort safety net)
  
  KEY: Exit because momentum dies,
       NOT because time runs out!

SYSTEMIC CONTEXT:

SYSTEMIC ISSUE (Confirmed May 11, 2026):
  NOT just INXUSDT - affects ALL coins!
  
  Pattern observed:
    INXUSDT:    TP +$267 → re-entry SL -$264
    BILLUSDT:   TP +$499 → re-entry SL -$131
    PLAYUSDT:   TP +$364 → re-entry SL -$304
    COLLECTUSDT:TP +$376 → re-entry SL -$208
    STRKUSDT:   TP +$246 → re-entry SL -$216
    
  Root cause: System has no memory of
  per-coin momentum state!
  Top gainers list = lagging indicator.
  Coin stays in list after momentum dies.
  System keeps re-entering dead momentum!
  
  REQUIRED FIXES (Sprint 2):
  A. Per-coin trade history tracking (daily)
     today_traded[symbol] = {exits, reasons, times}
     
  B. Momentum state per coin
     momentum_state[symbol] = FRESH/FADING/DEAD
     
  C. Freshness gate for ALL coins
     Any coin exited today = needs fresh momentum proof
     
  D. Stricter re-entry threshold
     Normal entry:  Score >= 65
     Re-entry:      Score >= 75 (higher confidence needed)
     
  E. Immediate coin hunting post-exit
     Priority: Brand new coins > Re-entry old coins

PHASE 5 - POST EXIT (Hunt Fresh):
  NO COOLDOWN! Immediately scan:
  
  IF fresh coin available:
  - Different coin from just exited
  - Fresh momentum (< 2h in gainers)
  - All entry criteria pass
  → ENTER immediately! ✅
  
  IF no fresh coin:
  - Wait next M15 cycle
  - Scan again
  → Never re-enter same coin same cycle! ❌

RE-ENTRY RULES:
  Same coin re-entry ONLY if:
  - Minimum 1 cycle passed (15 min)
  - Fresh momentum NEWLY formed
  - Not continuation of dead momentum
  - All entry criteria pass again
  
  Priority: NEW coin > Re-entry same coin

MOMENTUM SCORE FORMULA:
  Rate of Change (30%): 15m change
  Volume Surge (25%):   vs average
  Freshness (25%):      time in gainers
  Structure (20%):      price vs MA20
  
  >= 70: STRONG → Entry OK
  50-69: MODERATE → Skip
  < 50:  WEAK → Skip

IMPLEMENTATION SPRINTS:
  Sprint 2 - Tier 1 (Basic):
    - Threshold 60 → 65
    - No re-entry same coin same cycle
    - Basic momentum check at entry
    - Balance reset $1,000
    - SL/TP leverage-adjusted
    - Max positions 5
    
  Sprint 3 - Tier 2 (Full Momentum):
    - Full momentum hold monitoring
    - Momentum-based exit triggers
    - Freshness tracking system
    - Post-exit immediate coin hunting
    - SHORT momentum logic
    
  Sprint 4 - Tier 3 (Advanced):
    - Momentum score formula
    - Volume momentum tracking
    - Multi-TF momentum confirmation
    - Regime-aware momentum thresholds

EXPECTED IMPACT:
  WR: 45% → 58%+ (projected)
  Fewer but higher quality trades
  Smaller losses (early momentum exit)
  Better wins (hold while alive)
  No more INXUSDT-style re-entry bleeding
