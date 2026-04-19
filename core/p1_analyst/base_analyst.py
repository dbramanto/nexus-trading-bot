"""
NEXUS v2.0 - P1 Base Analyst
Abstract base class for all P1 indicator modules.
"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class BaseAnalyst(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def category(self) -> str:
        pass

    @property
    @abstractmethod
    def is_implemented(self) -> bool:
        pass

    @abstractmethod
    def analyze(self, df: pd.DataFrame, config: Any = None) -> Dict[str, Any]:
        pass

    def safe_analyze(self, df: pd.DataFrame, config: Any = None) -> Dict[str, Any]:
        if not self.is_implemented:
            return {
                "module": self.name,
                "category": self.category,
                "is_implemented": False,
                "skipped": True,
                "reason": "Module not yet implemented"
            }
        if df is None or df.empty:
            return {
                "module": self.name,
                "category": self.category,
                "is_implemented": True,
                "error": True,
                "reason": "Empty or None DataFrame"
            }
        if len(df) < self.min_bars_required:
            return {
                "module": self.name,
                "category": self.category,
                "is_implemented": True,
                "error": True,
                "reason": f"Insufficient data: {len(df)} bars < {self.min_bars_required} required"
            }
        try:
            result = self.analyze(df, config)
            result["module"] = self.name
            result["category"] = self.category
            result["is_implemented"] = True
            result["error"] = False
            return result
        except Exception as e:
            logger.error(f"P1 module {self.name} failed: {e}", exc_info=True)
            return {
                "module": self.name,
                "category": self.category,
                "is_implemented": True,
                "error": True,
                "reason": str(e)
            }

    @property
    def min_bars_required(self) -> int:
        return 50
