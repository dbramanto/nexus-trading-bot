"""
NEXUS v2.0 - P3 Strategy Logic
"""
import logging
from typing import Dict, Any
from config.strategy_config import NexusConfig

logger = logging.getLogger(__name__)

class StrategyLogic:
    def __init__(self, config: NexusConfig):
        self.config = config

    def evaluate(self, context_package: Dict[str, Any], circuit_breaker_active: bool = False) -> Dict[str, Any]:
        score = context_package.get("score", 0)
        grade = context_package.get("grade", "NO_TRADE")
        bias = context_package.get("bias", "NEUTRAL")
        threshold = context_package.get("threshold_used", self.config.scoring.weak_threshold)
        original_grade = grade
        downgraded = False
        downgrade_reason = None
        if circuit_breaker_active:
            return self._wait("Circuit breaker active", score, grade, threshold)
        if grade == "NO_TRADE":
            return self._wait(f"Grade NO_TRADE — tidak memenuhi syarat minimum", score, grade, threshold)
        if score < threshold:
            return self._wait(f"Score {score} below threshold {threshold}", score, grade, threshold)
        if bias == "NEUTRAL":
            if grade == "PREMIUM":
                grade = "VALID"
                downgraded = True
                downgrade_reason = "Bias NEUTRAL - downgraded PREMIUM to VALID"
            elif grade in ("VALID", "WEAK"):
                return self._wait("Score meets threshold but bias NEUTRAL", score, grade, threshold)

        # P3 Consensus Guard — cek kontradiksi antara bias dan sinyal kuat
        p1_snapshot = context_package.get("p1_snapshot", {})
        mom_dir = p1_snapshot.get("momentum_classifier", {}).get("momentum_direction", "NEUTRAL")
        mom_str = p1_snapshot.get("momentum_classifier", {}).get("momentum_strength", 0)
        vol_ratio = p1_snapshot.get("basic_indicators", {}).get("volume_ratio", 1.0) or 1.0

        # Volume terlalu rendah — tidak reliable
        if vol_ratio < 0.2:
            return self._wait(f"Volume terlalu rendah ({vol_ratio:.2f}x) — setup tidak reliable", score, grade, threshold)

        # Momentum kuat berlawanan dengan bias — kontradiksi serius
        if mom_str >= 3 and mom_dir != "NEUTRAL" and mom_dir != bias:
            return self._wait(f"Kontradiksi: bias {bias} tapi momentum {mom_dir} strength={mom_str}", score, grade, threshold)

        if bias == "BULLISH": action = "LONG"
        elif bias == "BEARISH": action = "SHORT"
        else: return self._wait("No clear bias", score, grade, threshold)
        size_multiplier = self.config.get_position_size_multiplier(grade)
        return {
            "action": action,
            "grade": grade,
            "original_grade": original_grade,
            "size_multiplier": size_multiplier,
            "score": score,
            "threshold_used": threshold,
            "reason": f"APPROVED: {action} | Score {score} | Grade {grade} | Size {size_multiplier:.0%}",
            "downgraded": downgraded,
            "downgrade_reason": downgrade_reason,
        }

    def _wait(self, reason, score, grade, threshold):
        return {
            "action": "WAIT",
            "grade": grade,
            "original_grade": grade,
            "size_multiplier": 0.0,
            "score": score,
            "threshold_used": threshold,
            "reason": reason,
            "downgraded": False,
            "downgrade_reason": None,
        }

    def evaluate_model_b(self, context_package):
        """P3 decision untuk Model B — Binary Confidence."""
        mb = context_package.get("model_b", {})
        conf = mb.get("confidence_pct", 0)
        agree = mb.get("agree", 0)
        total = mb.get("total", 22)
        bias = context_package.get("bias", "NEUTRAL")
        threshold_b = 50.0

        if bias == "NEUTRAL":
            return {"action": "WAIT", "model": "B", "score": conf,
                    "reason": "Bias NEUTRAL", "grade": "NO_TRADE"}
        if conf < threshold_b:
            return {"action": "WAIT", "model": "B", "score": conf,
                    "reason": f"Confidence {conf}% < {threshold_b}%", "grade": "NO_TRADE"}

        grade = "PREMIUM" if conf >= 75 else "VALID" if conf >= 60 else "WEAK"
        action = "LONG" if bias == "BULLISH" else "SHORT"
        return {
            "action": action, "model": "B", "score": conf,
            "grade": grade, "bias": bias,
            "reason": f"Confidence {conf}% ({agree}/{total} modul agree)",
            "size_multiplier": self.config.get_position_size_multiplier(grade),
        }

    def evaluate_model_c(self, context_package):
        """P3 decision untuk Model C — Hybrid."""
        mc = context_package.get("model_c", {})
        score_c = mc.get("score", 0)
        status = mc.get("status", "FILTERED")
        reason = mc.get("reason", "")
        bias = context_package.get("bias", "NEUTRAL")
        threshold = context_package.get("threshold_used", 55)

        if bias == "NEUTRAL":
            return {"action": "WAIT", "model": "C", "score": score_c,
                    "reason": "Bias NEUTRAL", "grade": "NO_TRADE"}
        if status == "FILTERED":
            return {"action": "WAIT", "model": "C", "score": score_c,
                    "reason": reason, "grade": "NO_TRADE"}
        if score_c < threshold:
            return {"action": "WAIT", "model": "C", "score": score_c,
                    "reason": f"Score {score_c} < threshold {threshold}", "grade": "NO_TRADE"}

        grade = "PREMIUM" if score_c >= 80 else "VALID" if score_c >= 65 else "WEAK"
        action = "LONG" if bias == "BULLISH" else "SHORT"
        return {
            "action": action, "model": "C", "score": score_c,
            "grade": grade, "bias": bias,
            "reason": f"Hybrid passed: {reason}",
            "size_multiplier": self.config.get_position_size_multiplier(grade),
        }
