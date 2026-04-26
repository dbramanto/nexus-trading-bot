"""
NEXUS v2.0 - Strategy Configuration - SINGLE SOURCE OF TRUTH
"""
import yaml, os
from dataclasses import dataclass, asdict

@dataclass
class ScoringConfig:
    premium_threshold: int = 90
    valid_threshold: int = 70
    weak_threshold: int = 55
    no_trade_threshold: int = 0
    tier_0_max: int = 20
    tier_1_max: int = 50
    tier_2_max: int = 30
    penalty_fake_bos: int = -100
    penalty_wrong_zone: int = -50
    penalty_extreme_funding: int = -30
    penalty_counter_trend: int = -40
    bonus_valid_sweep: int = 20
    bonus_zone_confluence: int = 15
    bonus_volume_confirmation: int = 10
    adaptive_enabled: bool = True
    adaptive_modifier_min: int = -15
    adaptive_modifier_max: int = 20
    adaptive_threshold_floor: int = 50
    adaptive_threshold_ceiling: int = 90

@dataclass
class RiskConfig:
    risk_per_trade_percent: float = 2.5
    max_consecutive_losses: int = 4
    daily_loss_limit_percent: float = 5.0
    max_positions: int = 1
    max_hold_hours: int = 24
    size_premium_pct: float = 1.0
    size_valid_pct: float = 0.6
    size_weak_pct: float = 0.3
    sl_method: str = "range_based"
    sl_buffer_percent: float = 0.5
    tp_method: str = "risk_reward"
    tp_risk_reward_ratio: float = 2.0
    trailing_trigger_percent: float = 3.0
    trailing_trail_percent: float = 1.5
    breakeven_trigger_percent: float = 2.0

@dataclass
class IndicatorConfig:
    primary_tf: str = "15m"
    confirmation_tf: str = "30m"
    higher_tf: str = "1h"
    consolidation_min_candles: int = 16
    consolidation_atr_multiplier: float = 1.5
    breakout_volume_multiplier: float = 2.0
    breakout_close_confirmation: bool = True
    premium_zone_threshold: float = 0.618
    discount_zone_threshold: float = 0.382
    spike_atr_multiplier: float = 2.0

@dataclass
class TradingConfig:
    mode: str = "paper"
    initial_balance: float = 1000.0
    top_coins: int = 15
    min_volume_usd: int = 50000000
    universe_update_hours: int = 24
    api_testnet: bool = False
    api_timeout: int = 30

@dataclass
class BacktestConfig:
    fee_maker_pct: float = 0.02
    fee_taker_pct: float = 0.04
    slippage_pct: float = 0.03
    walk_forward_train_months: int = 2
    walk_forward_test_months: int = 1
    is_backtest: bool = False


# ============================================================================
# STRATEGY RULES — Config-Driven Filters
# ============================================================================

class StrategyRules:
    """
    Strategy-level decision rules for P3 Manager.
    
    Philosophy: Strategy rules live in config, not code.
    Benefits: Fast iteration, A/B testing, emergency rollback.
    """
    
    # === PATTERN FILTER ===
    # Data-driven validation: BULLISH_MARUBOZU = 77% win coverage (10/13 wins)
    PATTERN_FILTER_ENABLED = True
    APPROVED_PATTERNS = [
        "BULLISH_MARUBOZU",
        # Future expansion (add after validation):
        # "BULLISH_ENGULFING",
        # "BULLISH_PIN_BAR",
    ]
    
    # === MSS FILTER ===
    MSS_FILTER_ENABLED = False
    APPROVED_MSS = ["BULLISH"]
    REJECTED_MSS = ["RANGING", "UNDEFINED"]
    
    # === ZONE FILTER ===
    ZONE_FILTER_ENABLED = False
    REJECTED_ZONES = ["PREMIUM"]
    
    # === MOMENTUM FILTER ===
    MOMENTUM_FILTER_ENABLED = False
    REJECTED_MOMENTUM = ["BEARISH"]
    
    # === BB POSITION FILTER ===
    BB_FILTER_ENABLED = False
    REJECTED_BB_POSITIONS = ["upper_half"]


class NexusConfig:
    def __init__(self, config_path: str = "config/settings.yaml"):
        self.scoring = ScoringConfig()
        self.risk = RiskConfig()
        self.indicators = IndicatorConfig()
        self.trading = TradingConfig()
        self.backtest = BacktestConfig()
        self.rules = StrategyRules()
        
        if os.path.exists(config_path):
            self._load_from_yaml(config_path)

    def get_effective_threshold(self, modifier: int = 0) -> int:
        """Calculate adaptive threshold based on modifier."""
        if not self.scoring.adaptive_enabled:
            return self.scoring.weak_threshold
        clamped = max(self.scoring.adaptive_modifier_min, min(self.scoring.adaptive_modifier_max, modifier))
        eff = self.scoring.weak_threshold + clamped
        eff = max(self.scoring.adaptive_threshold_floor, eff)
        eff = min(self.scoring.adaptive_threshold_ceiling, eff)
        return eff

    def get_position_size_multiplier(self, grade: str) -> float:
        """Get position size multiplier based on grade."""
        if grade == "PREMIUM": 
            return self.risk.size_premium_pct
        if grade == "VALID": 
            return self.risk.size_valid_pct
        if grade == "WEAK": 
            return self.risk.size_weak_pct
        return 0.3

    def _load_from_yaml(self, path: str):
        with open(path, "r") as f:
            raw = yaml.safe_load(f)
        if not raw:
            return
        
        # Scoring
        s = raw.get("scoring", {})
        t = s.get("thresholds", {})
        if t:
            self.scoring.premium_threshold = t.get("premium", self.scoring.premium_threshold)
            self.scoring.valid_threshold = t.get("valid", self.scoring.valid_threshold)
            self.scoring.weak_threshold = t.get("weak", self.scoring.weak_threshold)
        
        # Risk
        self.risk.risk_per_trade_percent = raw.get("risk_per_trade_percent", self.risk.risk_per_trade_percent)
        self.risk.max_consecutive_losses = raw.get("max_consecutive_losses", self.risk.max_consecutive_losses)
        self.risk.max_positions = raw.get("max_positions", self.risk.max_positions)
        
        # Trading
        self.trading.initial_balance = raw.get("initial_balance", self.trading.initial_balance)
        
        # Position management
        pm = raw.get("position_management", {})
        if pm:
            sl = pm.get("stop_loss", {})
            if sl:
                self.risk.sl_method = sl.get("method", self.risk.sl_method)
                self.risk.sl_buffer_percent = sl.get("buffer_percent", self.risk.sl_buffer_percent)
            
            tp = pm.get("take_profit", {})
            if tp:
                self.risk.tp_method = tp.get("method", self.risk.tp_method)
                self.risk.tp_risk_reward_ratio = tp.get("risk_reward_ratio", self.risk.tp_risk_reward_ratio)
