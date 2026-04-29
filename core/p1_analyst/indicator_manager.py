"""
NEXUS v2.0 - P1 Indicator Manager
Orchestrator that calls all registered P1 modules.
"""
import pandas as pd
import logging
import time
from typing import Dict, Any, List
from core.p1_analyst.base_analyst import BaseAnalyst

logger = logging.getLogger(__name__)

class IndicatorManager:
    def __init__(self):
        self._modules: List[BaseAnalyst] = []

    def register(self, module: BaseAnalyst):
        if not isinstance(module, BaseAnalyst):
            raise TypeError(f"Module must inherit from BaseAnalyst, got {type(module)}")
        existing_names = [m.name for m in self._modules]
        if module.name in existing_names:
            raise ValueError(f"Module {module.name} already registered")
        self._modules.append(module)
        status = "ACTIVE" if module.is_implemented else "PLACEHOLDER"
        logger.info(f"P1 registered: {module.name} [{module.category}] - {status}")

    def run_all(self, df: pd.DataFrame, config: Any = None, symbol: str = None) -> Dict[str, Any]:
        start_time = time.time()
        logger.info("TRACE 2: P1.run_all received symbol=%s" % symbol)
        reports = {}
        reports["symbol"] = symbol if symbol else "UNKNOWN"
        logger.info("TRACE 3: P1 stored symbol=%s in reports" % reports.get("symbol"))
        active_count = 0
        skipped_count = 0
        errored_count = 0
        for module in self._modules:
            report = module.safe_analyze(df, config)
            reports[module.name] = report
            if report.get("skipped"):
                skipped_count += 1
            elif report.get("error"):
                errored_count += 1
            else:
                active_count += 1
        scan_time_ms = (time.time() - start_time) * 1000
        return {
            "modules": reports,
            "meta": {
                "total_modules": len(self._modules),
                "active_modules": active_count,
                "skipped_modules": skipped_count,
                "errored_modules": errored_count,
                "scan_time_ms": round(scan_time_ms, 1)
            },
            "symbol": reports.get("symbol", "UNKNOWN")
        }

    def get_active_modules(self) -> List[str]:
        return [m.name for m in self._modules if m.is_implemented]

    def get_placeholder_modules(self) -> List[str]:
        return [m.name for m in self._modules if not m.is_implemented]

    def get_module_summary(self) -> Dict[str, Any]:
        summary = {"active": [], "placeholder": []}
        for m in self._modules:
            entry = {"name": m.name, "category": m.category}
            if m.is_implemented:
                summary["active"].append(entry)
            else:
                summary["placeholder"].append(entry)
        return summary
