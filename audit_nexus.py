"""
NEXUS v2.0 - Comprehensive System Audit
Identify integration issues, missing methods, broken contracts.
"""
import ast
import os
import sys
from pathlib import Path
from collections import defaultdict

print("="*80)
print("NEXUS v2.0 — COMPREHENSIVE SYSTEM AUDIT")
print("="*80)
print()

# ============================================================================
# PHASE 1: MODULE INVENTORY
# ============================================================================

print("📦 PHASE 1: MODULE INVENTORY")
print("-" * 80)

modules = {
    'P1': list(Path('core/p1_analyst').rglob('*.py')),
    'P2': list(Path('core/p2_supervisor').rglob('*.py')),
    'P3': list(Path('core/p3_manager').rglob('*.py')),
    'P4': list(Path('core/p4_auditor').rglob('*.py')),
    'Config': list(Path('config').rglob('*.py')),
    'Execution': list(Path('execution').rglob('*.py')),
}

for layer, files in modules.items():
    py_files = [f for f in files if not f.name.startswith('__')]
    print(f"{layer:12} | {len(py_files):2} files | {', '.join([f.stem for f in py_files[:3]])}{'...' if len(py_files) > 3 else ''}")

print()

# ============================================================================
# PHASE 2: CONFIG CONTRACT VALIDATION
# ============================================================================

print("📋 PHASE 2: CONFIG CONTRACT VALIDATION")
print("-" * 80)

print("\nChecking NexusConfig attributes...")

# Parse config file
config_file = 'config/strategy_config.py'
with open(config_file) as f:
    tree = ast.parse(f.read())

# Find NexusConfig class
nexus_config_methods = []
nexus_config_attrs = []

for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and node.name == 'NexusConfig':
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                nexus_config_methods.append(item.name)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        nexus_config_attrs.append(target.id)

print(f"NexusConfig methods: {len(nexus_config_methods)}")
for method in nexus_config_methods:
    print(f"  ✓ {method}")

print()

# ============================================================================
# PHASE 3: METHOD CALL VALIDATION
# ============================================================================

print("🔗 PHASE 3: METHOD CALL VALIDATION")
print("-" * 80)

print("\nScanning for config.method() calls...")

config_method_calls = defaultdict(list)

for layer, files in modules.items():
    for filepath in files:
        if filepath.name.startswith('__'):
            continue
        
        try:
            with open(filepath) as f:
                content = f.read()
                tree = ast.parse(content)
            
            for node in ast.walk(tree):
                # Look for self.config.method_name() or config.method_name()
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if isinstance(node.func.value, ast.Attribute):
                            # self.config.method_name
                            if node.func.value.attr == 'config':
                                method = node.func.attr
                                config_method_calls[method].append(str(filepath))
                        elif isinstance(node.func.value, ast.Name):
                            # config.method_name
                            if node.func.value.id == 'config':
                                method = node.func.attr
                                config_method_calls[method].append(str(filepath))
        except:
            pass

print(f"\nFound {len(config_method_calls)} distinct config method calls:")
for method, callers in sorted(config_method_calls.items()):
    exists = "✓" if method in nexus_config_methods else "✗ MISSING"
    print(f"  {exists} config.{method}() — called in {len(callers)} file(s)")
    if method not in nexus_config_methods:
        print(f"      Callers: {[Path(c).name for c in callers[:3]]}")

print()

# ============================================================================
# PHASE 4: P1→P2→P3→P4 DATA FLOW
# ============================================================================

print("🔄 PHASE 4: DATA FLOW VALIDATION")
print("-" * 80)

print("\nP1 Output Contract (p1_snapshot keys expected by P2/P3):")

# Find what P2/P3 expect from p1_snapshot
p1_keys_accessed = set()

for layer in ['P2', 'P3']:
    for filepath in modules[layer]:
        if filepath.name.startswith('__'):
            continue
        
        try:
            with open(filepath) as f:
                content = f.read()
            
            # Look for p1_snapshot.get("key") or p1_snap.get("key")
            import re
            matches = re.findall(r'p1_snap(?:shot)?\.get\(["\']([^"\']+)["\']', content)
            p1_keys_accessed.update(matches)
        except:
            pass

print(f"\nP2/P3 expect these {len(p1_keys_accessed)} P1 keys:")
for key in sorted(p1_keys_accessed):
    print(f"  - {key}")

print()

# ============================================================================
# PHASE 5: IMPORT VALIDATION
# ============================================================================

print("📥 PHASE 5: IMPORT VALIDATION")
print("-" * 80)

print("\nChecking critical imports...")

critical_imports = {
    'forward_test_runner.py': ['NexusConfig'],
    'core/p2_supervisor/scoring_engine.py': ['NexusConfig'],
    'core/p3_manager/strategy_logic.py': ['NexusConfig'],
}

for file, expected_imports in critical_imports.items():
    if not os.path.exists(file):
        print(f"  ✗ {file} NOT FOUND")
        continue
    
    with open(file) as f:
        content = f.read()
    
    for imp in expected_imports:
        if f'import {imp}' in content or f'from config.strategy_config import {imp}' in content:
            print(f"  ✓ {file} imports {imp}")
        else:
            print(f"  ✗ {file} MISSING import {imp}")

print()

# ============================================================================
# PHASE 6: CRITICAL ISSUES SUMMARY
# ============================================================================

print("⚠️ PHASE 6: CRITICAL ISSUES SUMMARY")
print("-" * 80)

issues = []

# Check for missing methods
for method, callers in config_method_calls.items():
    if method not in nexus_config_methods:
        issues.append(f"MISSING METHOD: config.{method}() called but not defined")

# Check for undefined attributes
if not nexus_config_methods:
    issues.append("CRITICAL: NexusConfig has no methods defined")

if issues:
    print(f"\n🚨 FOUND {len(issues)} CRITICAL ISSUES:")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
else:
    print("\n✅ NO CRITICAL ISSUES FOUND")

print()

# ============================================================================
# PHASE 7: RECOMMENDATIONS
# ============================================================================

print("💡 PHASE 7: RECOMMENDATIONS")
print("-" * 80)

print("""
1. Create Interface Contracts
   - Define explicit interfaces for P1→P2→P3→P4 data flow
   - Document expected p1_snapshot keys
   - Type hints for all config methods

2. Add Integration Tests
   - Test config.method() calls actually exist
   - Validate P1 output matches P2 expectations
   - End-to-end smoke test before deploy

3. Config Validation on Startup
   - Check all required methods exist
   - Validate all config fields
   - Fail fast with clear error messages

4. Dependency Documentation
   - Map all cross-module dependencies
   - Document which modules depend on config
   - Version contracts (like API versioning)

5. Pre-commit Hooks
   - Run audit script before git commit
   - Syntax check all Python files
   - Validate imports resolve
""")

print("="*80)
print("AUDIT COMPLETE")
print("="*80)
