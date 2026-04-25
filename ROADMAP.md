# NEXUS Trading System — Roadmap

## NEXUS M15 (Active Development)

### Sprint 1 — DONE
Core architecture P1→P2→P3→P4, 23 modul aktif, systemd service

### Sprint 2 — DONE (extended)
Crypto-native modules, 5 shadow accounts, data collection pipeline,
HA+PA trigger, RANGING block, CHoCH requirement, PREMIUM block,
FVG kalibrasi, OB freshness, outcome tracker, Telegram report

### Sprint 3 — PENDING (butuh 100+ labeled trades)
- Kalibrasi bobot scoring berdasarkan data empiris
- Walk-forward backtest dengan parameter baru
- HTF structure implementation
- Structure-based SL
- Exit management (trailing stop, time-based)
- Evaluasi modul: FVG, OB, StochRSI, MACD relevance

### Sprint 3B — PENDING
Paper trading Binance testnet, 30 trades dengan PnL tracking

### Sprint 4 — PENDING (butuh 200+ labeled trades)
- ML training: XGBoost/LightGBM
- MLAdvisor di P3 sebagai co-decision maker
- AdaptiveWeightEngine
- Dynamic watchlist top mover

### Sprint 5 — PENDING
Live trading kecil ($100-200), A/B test rule-based vs ML

### Sprint 6 — PENDING
Scale capital, HTF structure full, multi-symbol optimization

## Konsep Pending (Sprint 4-5)
- Adaptive Scale In: leverage 1x, scale in berbasis struktur
  stop kalau bias broken (BOS/CHoCH)
- SL berbasis average price (5% dari average)
- Maximum 2-3 scale in per trade

## NEXUS Scalper (Future Vision)
- Varian terpisah dari NEXUS M15
- Timeframe: M1-M5
- Receive HTF bias dari NEXUS M15
- Focus: order flow, momentum, volume spike
- Latency target: < 100ms
- Top mover Binance >5% sebagai watchlist
- Prerequisite: NEXUS M15 sudah profitable dan stabil

## Data Collection Status (25 April 2026)
- Shadow A: 14 signals | WR 33% (BULLISH only)
- Shadow B: 2 signals  | Binary confidence
- Shadow C: 1 signal   | Hybrid
- Shadow L: 0 signals  | LONG only (new)
- Shadow T: 0 signals  | Top Mover (new)
- Labeled trades: 90 | Target: 200 untuk ML
- Overall WR: 11.8% (pre-fix data)
