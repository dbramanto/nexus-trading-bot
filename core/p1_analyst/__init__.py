"""
NEXUS v2.0 - P1 Analyst Package
Import all modules and provide factory function.
"""
from core.p1_analyst.indicator_manager import IndicatorManager
from core.p1_analyst.classic.basic_indicators import BasicIndicators
from core.p1_analyst.classic.bollinger_bands import BollingerBands
from core.p1_analyst.classic.macd_indicator import MACDIndicator
from core.p1_analyst.classic.vwap_calculator import VWAPCalculator
from core.p1_analyst.classic.volume_profile import VolumeProfile
from core.p1_analyst.classic.stochastic_rsi import StochasticRSI
from core.p1_analyst.ict.fvg_detector import FVGDetector
from core.p1_analyst.ict.orderblock_detector import OrderBlockDetector
from core.p1_analyst.ict.liquidity_sweeps import LiquiditySweeps
from core.p1_analyst.ict.premium_discount import PremiumDiscountZones
from core.p1_analyst.ict.daily_levels import DailyLevels
from core.p1_analyst.ict.consolidation_detector import ConsolidationDetector
from core.p1_analyst.ict.breakout_detector import BreakoutDetector
from core.p1_analyst.ict.htf_structure import HTFStructure
from core.p1_analyst.orderflow.funding_rate import FundingRate
from core.p1_analyst.orderflow.open_interest import OpenInterest
from core.p1_analyst.ict.mss_detector import MSSDetector
from core.p1_analyst.context.momentum_classifier import MomentumClassifier
from core.p1_analyst.context.candle_pattern import CandlePattern
from core.p1_analyst.context.fear_greed_index import FearGreedIndex
from core.p1_analyst.orderflow.cvd_analyzer import CVDAnalyzer
from core.p1_analyst.orderflow.orderbook_imbalance import OrderBookImbalance
from core.p1_analyst.context.spike_classifier import SpikeClassifier


def build_indicator_manager() -> IndicatorManager:
    """
    Factory: create and register all P1 modules.
    Call this once at startup.
    """
    mgr = IndicatorManager()

    # Classic TA
    mgr.register(BasicIndicators())
    mgr.register(BollingerBands())
    mgr.register(MACDIndicator())
    mgr.register(VWAPCalculator())
    mgr.register(VolumeProfile())
    mgr.register(StochasticRSI())

    # ICT/SMC
    mgr.register(FVGDetector())
    mgr.register(OrderBlockDetector())
    mgr.register(LiquiditySweeps())
    mgr.register(PremiumDiscountZones())
    mgr.register(DailyLevels())
    mgr.register(ConsolidationDetector())
    mgr.register(BreakoutDetector())
    mgr.register(HTFStructure())       # placeholder

    # Orderflow
    mgr.register(FundingRate())
    mgr.register(OpenInterest())
    mgr.register(MSSDetector())
    mgr.register(MomentumClassifier())
    mgr.register(CandlePattern())
    mgr.register(FearGreedIndex())
    mgr.register(CVDAnalyzer())
    mgr.register(OrderBookImbalance())

    # Context
    mgr.register(SpikeClassifier())

    return mgr