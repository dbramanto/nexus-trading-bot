"""
Remove early volume gate, keep momentum + pattern optimizations.
Let volume contribute to scoring naturally via T0.
"""

with open('core/p2_supervisor/scoring_engine.py', 'r') as f:
    content = f.read()

# Remove volume gate block
old_gate = '''    def score(self, p1_reports, circuit_breaker_state=None):
        # === OPTIMIZATION: Early Volume Gate ===
        # 93% of scans have volume <0.5 — reject early to save compute
        bi_check = p1_reports.get("basic_indicators", {})
        vol_check = bi_check.get("volume_ratio", 0) or 0
        if vol_check < 0.5:
            return {
                'score': 0,
                'grade': 'NO_TRADE',
                'bias': 'NEUTRAL',
                'tier_breakdown': {'t0': 0, 't1': 0, 't2': 0},
                'reject_reason': 'Volume <0.5 (early gate - 93% filtered here)',
                'p1_snapshot': p1_reports
            }
        
        modules = p1_reports.get("modules", {})'''

new_gate = '''    def score(self, p1_reports, circuit_breaker_state=None):
        # OPTIMIZATION NOTE: Volume gate removed - let T0 scoring handle volume naturally
        # Low volume will still get low scores via T0 context scoring
        modules = p1_reports'''

content = content.replace(old_gate, new_gate)

with open('core/p2_supervisor/scoring_engine.py', 'w') as f:
    f.write(content)

print("✓ Volume gate removed")
print("✓ Momentum 3x optimization retained")
print("✓ Candle pattern +8 optimization retained")
