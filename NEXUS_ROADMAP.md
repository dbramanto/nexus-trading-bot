# NEXUS OPTIMIZATION & ML ROADMAP
Last Updated: 2026-04-12

## CURRENT STATUS ✅
- Threshold: 57.5 (ML-optimized)
- Max Positions: 1 (learning mode)
- Timeframe: 15m primary
- Status: Forward test ACTIVE
- Purpose: ML data collection

---

## PHASE 1: DATA COLLECTION (Current - Month 3)
**Timeline:** 2-3 months
**Goal:** Collect 5K-10K high-quality labeled samples

### Active Tasks ✅
- [x] Threshold optimized (57.5)
- [x] Single position mode
- [x] Funding rate activated
- [x] Telegram reports scheduled
- [x] Forward test running

### Remaining Optimization:
1. **Open Interest Module** (Priority: HIGH)
   - Time: 1.5 hours
   - Impact: +3-5 points in T0
   - Data: Already have get_open_interest() API
   - Status: READY TO IMPLEMENT

2. **Liquidation Module** (Priority: MEDIUM)
   - Time: 4-6 hours
   - Impact: +4-5 points in T2
   - Method: Mathematical estimation
   - Status: Pine Script logic documented

3. **HTF Structure Enhancement** (Priority: MEDIUM)
   - Time: 1.5 hours
   - Impact: +7 points in T1
   - Current: Placeholder (returns neutral)
   - Status: READY TO IMPLEMENT

4. **Data Logging Enhancement** (Priority: HIGH)
   - Time: 2 hours
   - Impact: Better ML features
   - Add: All indicator values, market context
   - Status: RECOMMENDED

---

## PHASE 2: ML MODEL DEVELOPMENT (Month 3-4)
**Timeline:** 1 month
**Goal:** Train and validate ML enhancement

### Tasks:
1. **Data Preparation**
   - Clean collected data
   - Feature engineering
   - Train/validation split
   - Label verification

2. **Model Training**
   - Binary classification (win/loss)
   - Try: XGBoost, LightGBM, Neural Net
   - Hyperparameter tuning
   - Cross-validation

3. **Model Integration**
   - Add ML confidence score
   - Combine with rule-based
   - Hybrid scoring system
   - A/B testing framework

4. **Validation**
   - Out-of-sample testing
   - Forward test comparison
   - Performance metrics
   - Iteration cycles

---

## PHASE 3: SCALING (Month 4+)
**Timeline:** Ongoing
**Goal:** Full production with 3 positions

### Tasks:
1. **Multi-Position Management**
   - Update max_positions: 1 → 3
   - Portfolio correlation logic
   - Position sizing optimization
   - Risk distribution

2. **ML Refinement**
   - Continuous training
   - Model updates
   - Feature selection
   - Performance monitoring

3. **Advanced Features**
   - Multi-timeframe optimization
   - Regime detection
   - Adaptive thresholds
   - Dynamic position sizing

---

## OPTIMIZATION PRIORITY RANKING

### IMMEDIATE (Next 1-2 weeks):
1. ✅ Data Logging Enhancement
   - Critical for ML quality
   - Easy implementation
   - High ROI

2. ✅ Open Interest Module
   - Quick win (+3-5 points)
   - API already available
   - Crypto-specific edge

### SHORT-TERM (Next month):
3. ⏳ HTF Structure Activation
   - Moderate impact (+7 points)
   - Already designed
   - Need implementation

4. ⏳ Liquidation Module
   - Good for crypto
   - Moderate complexity
   - Nice-to-have

### MEDIUM-TERM (Month 2-3):
5. ⏳ Error Handling Improvements
   - Retry logic
   - Better exception handling
   - System stability

6. ⏳ Performance Optimization
   - Parallel scanning
   - Cache optimization
   - Speed improvements

### LONG-TERM (Phase 2+):
7. ⏳ ML Model Development
   - After sufficient data
   - Main goal of Phase 1
   - Game changer

---

## TIMEFRAME OPTIMIZATION CONSIDERATIONS

### Current: 15m Primary
**Pros:**
- Good signal frequency (~95/day with T57.5)
- Fast iteration for ML
- Responsive to market moves

**Cons:**
- More noise than higher TFs
- Requires tighter risk management
- Higher trade frequency

### Alternative Options:

**30m Timeframe:**
- Pros: Less noise, better quality
- Cons: Fewer signals (~50/day)
- When: Consider if 15m too noisy

**1h Timeframe:**
- Pros: Highest quality, less noise
- Cons: Low frequency (~25/day)
- When: For conservative approach

**Multi-TF Approach:**
- Use 15m for entry timing
- Use 1h/4h for trend confirmation
- Best of both worlds
- More complex implementation

### Recommendation:
**KEEP 15m for Phase 1**
- Good balance for ML data collection
- Can optimize TF in Phase 2 after ML model
- ML might learn optimal TF usage

---

## WEEKLY TASKS (Next 4 Weeks)

### Week 1 (Current):
- [x] Threshold optimization ✅
- [x] Forward test deployment ✅
- [x] Report schedule setup ✅
- [ ] Monitor first week performance
- [ ] Data logging enhancement

### Week 2:
- [ ] Implement Open Interest module
- [ ] Test OI scoring impact
- [ ] Continue data collection
- [ ] Review weekly metrics

### Week 3:
- [ ] HTF Structure activation
- [ ] Test combined improvements
- [ ] Data quality review
- [ ] Consider liquidation module

### Week 4:
- [ ] Month 1 review
- [ ] Adjust if needed
- [ ] Plan Month 2 enhancements
- [ ] ML preparation planning

---

## SUCCESS METRICS

### Phase 1 Targets:
- Collect: 5,000-10,000 trades
- Quality: Avg score 63.6+
- Frequency: ~95 signals/day
- Win rate: 40-50% (balanced)
- Duration: 2-3 months

### Phase 2 Targets:
- ML accuracy: >55%
- Improvement: +5% win rate
- Deployment: Hybrid system
- A/B test: Beat baseline

### Phase 3 Targets:
- Max positions: 3
- Portfolio win rate: >50%
- Monthly ROI: Consistent positive
- System stability: 99%+ uptime

---

## NOTES
- Focus on DATA QUALITY over quantity
- Don't over-optimize before ML
- Keep system simple during collection
- Document all changes
- Regular backups

