with open('backtesting/outcome_tracker.py', 'r') as f:
    content = f.read()

# Find start of code after docstring
import_start = content.find('"""', content.find('"""') + 3) + 4

# Take docstring + rest
docstring = content[:import_start]
rest = content[import_start:]

# Clean header
new_header = """import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import pandas as pd
import time
import logging
from datetime import datetime, timedelta
from execution.binance_client import BinanceClientWrapper

"""

# Find where actual imports end
actual_code_start = rest.find('logging.basicConfig')

# Combine
final = docstring + new_header + rest[actual_code_start:]

with open('backtesting/outcome_tracker.py', 'w') as f:
    f.write(final)

print("✓ Fixed")
