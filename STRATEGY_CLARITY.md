# NEXUS v2.0 - Strategy Definition

## Core Identity
NEXUS is a **momentum-based LONG strategy** for cryptocurrency futures.

## Strategy Type
- **Trend Following**: Ride strong upward momentum
- **Direction**: LONG only (no SHORT positions)
- **Universe**: Dynamic top 10 gainers (24h % change)

## Why LONG Only?

### Architectural Alignment
- Scanner selects TOP GAINERS (coins going UP)
- Trading LONG = aligned with selection bias
- Trading SHORT = contradicts momentum we selected
- Architectural coherence requires LONG only

### Empirical Evidence
- LONG: 50.8% WR, +$0.17/trade (viable)
- SHORT: 40.0% WR, -$3.75/trade (unprofitable)
- Market structure favors LONG in crypto

### Resource Focus
- 100% optimization effort on LONG performance
- No distraction from SHORT debugging
- Faster progress, clearer roadmap

## Optimization Priorities
1. Entry quality (score thresholds)
2. Exit management (TP/SL/trailing)
3. Regime detection (when to trade)
4. Risk management (position sizing, stops)

## Future Consideration
SHORT may be reconsidered IF:
- Building separate mean-reversion strategy
- Using different scanner (top LOSERS)
- Dedicated SHORT-specific modules developed

Until then: LONG ONLY.

---
Decision Date: May 1, 2026
Rationale: Strategic clarity > Feature completeness
