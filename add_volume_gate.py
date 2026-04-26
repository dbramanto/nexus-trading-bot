"""
Add early volume gate to score() method
"""

with open('core/p2_supervisor/scoring_engine.py', 'r') as f:
    lines = f.readlines()

new_lines = []
inserted = False

for i, line in enumerate(lines):
    new_lines.append(line)
    
    # Insert after "def score(self, p1_reports..." and its docstring
    if 'def score(self, p1_reports' in line and not inserted:
        # Find next line that starts actual code (after docstring)
        # Look for "modules = " or first real code
        for j in range(i+1, min(i+20, len(lines))):
            if 'modules = ' in lines[j] or 'p1_snapshot = ' in lines[j]:
                # Insert volume gate before this line
                indent = '        '
                volume_gate = f'''{indent}# === OPTIMIZATION: Early Volume Gate ===
{indent}# 93% of scans have volume <0.5 — reject early to save compute
{indent}bi_check = p1_reports.get("basic_indicators", {{}})
{indent}vol_check = bi_check.get("volume_ratio", 0) or 0
{indent}if vol_check < 0.5:
{indent}    return {{
{indent}        'score': 0,
{indent}        'grade': 'NO_TRADE',
{indent}        'bias': 'NEUTRAL',
{indent}        'tier_breakdown': {{'t0': 0, 't1': 0, 't2': 0}},
{indent}        'reject_reason': 'Volume <0.5 (early gate - 93% filtered here)',
{indent}        'p1_snapshot': p1_reports
{indent}    }}
{indent}
'''
                # Insert before the modules = line
                new_lines.insert(len(new_lines), volume_gate)
                inserted = True
                break

with open('core/p2_supervisor/scoring_engine.py', 'w') as f:
    f.writelines(new_lines)

print("✓ Volume gate added to score() method")
