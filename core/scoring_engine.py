"""
NEXUS Bot - Scoring Engine
Calculates setup scores based on indicator confluence
"""

import logging
from typing import Dict, Optional
import yaml

# Setup logging
logger = logging.getLogger(__name__)


class ScoringEngine:
    """
    Calculates setup scores from indicator analysis
    
    Uses tier-based weighting system:
    - Tier 0: Structure + Volume (max 50)
    - Tier 1: Primary Signals (max 35)
    - Tier 2: Confirmation (max 15)
    
    Total possible: 100 points
    """
    
    def __init__(self, config_path: str = 'config/settings.yaml'):
        """
        Initialize scoring engine
        
        Args:
            config_path: Path to settings.yaml
        """
        self.config_path = config_path
        self.weights = {}
        self.thresholds = {}
        
        # Load configuration
        self._load_config()
        
        logger.info(
            f"ScoringEngine initialized "
            f"(min_score={self.thresholds.get('weak', 55)})"
        )
    
    def _load_config(self):
        """Load weights from configuration file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            scoring_config = config.get('scoring', {})
            
            # Load weights
            initial_weights = scoring_config.get('initial_weights', {})
            self.weights = {
                'tier_0': initial_weights.get('tier_0', {}),
                'tier_1': initial_weights.get('tier_1', {}),
                'tier_2': initial_weights.get('tier_2', {})
            }
            
            # Load thresholds
            thresholds = scoring_config.get('thresholds', {})
            self.thresholds = {
                'premium': thresholds.get('premium', 85),
                'valid': thresholds.get('valid', 70),
                'weak': thresholds.get('weak', 55),
                'no_trade': thresholds.get('no_trade', 0)
            }
            
            logger.info("Configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            # Use defaults
            self._load_default_weights()
    
    def _load_default_weights(self):
        """Load default weights if config fails"""
        self.weights = {
            'tier_0': {
                'consolidation_quality': 15,
                'volume_spike': 15,
                'liquidity': 10,
                'range_duration': 10,
                'funding_rate': 5,
            },
            'tier_1': {
                'fvg_present': 8,
                'htf_alignment': 7,
                'premium_discount': 7,
                'order_block': 7,
                'ichimoku': 8,
                'vwap': 4,
                'volume_profile': 6,
                'stochastic_rsi': 5,
                'macd': 5,
                'bollinger_bands': 4,
                'htf_structure': 7,
                'momentum': 6
            },
            'tier_2': {
                'candlestick_pattern': 5,
                'ma_alignment': 5,
                'fibonacci': 5,
                'liquidity_sweeps': 8,
            }
        }
        self.thresholds = {
            'premium': 85,
            'valid': 70,
            'weak': 55,
            'no_trade': 0
        }
    
    def calculate_score(
        self,
        analysis: Dict,
        direction: str = 'LONG'
    ) -> Dict:
        """
        Calculate complete setup score
        
        Args:
            analysis: Analysis from IndicatorManager
            direction: Trade direction ('LONG' or 'SHORT')
            
        Returns:
            dict: Score breakdown and grade
        """
        logger.info(f"Calculating score for {analysis['symbol']} ({direction})")
        
        # Initialize scores
        tier_0_score = self._calculate_tier_0(analysis)
        tier_1_score = self._calculate_tier_1(analysis, direction)
        tier_2_score = self._calculate_tier_2(analysis)
        
        # Total score
        total_score = tier_0_score['total'] + tier_1_score['total'] + tier_2_score['total']
        
        # Determine grade
        grade = self._get_grade(total_score)
        
        result = {
            'total_score': round(total_score, 1),
            'grade': grade,
            'direction': direction,
            'tier_0': tier_0_score,
            'tier_1': tier_1_score,
            'tier_2': tier_2_score,
            'breakdown': {
                'tier_0_total': tier_0_score['total'],
                'tier_1_total': tier_1_score['total'],
                'tier_2_total': tier_2_score['total']
            }
        }
        
        logger.info(
            f"Score calculated: {total_score:.1f} ({grade}) - "
            f"T0:{tier_0_score['total']:.1f} T1:{tier_1_score['total']:.1f} T2:{tier_2_score['total']:.1f}"
        )
        
        return result
    
    def _calculate_tier_0(self, analysis: Dict) -> Dict:
        """
        Calculate Tier 0 score (Structure + Volume)
        
        Args:
            analysis: Indicator analysis
            
        Returns:
            dict: Tier 0 scores
        """
        weights = self.weights['tier_0']
        scores = {}
        
        # 1. Consolidation Quality
        consolidation = analysis.get('consolidation')
        if consolidation:
            quality = consolidation.get('quality_score', 0)
            # Scale to max weight
            max_weight = weights.get('consolidation_quality', 15)
            scores['consolidation_quality'] = (quality / 100) * max_weight
        else:
            scores['consolidation_quality'] = 0
        
        # 2. Volume Spike
        volume = analysis['indicators'].get('volume', {})
        volume_ratio = volume.get('ratio', 0)
        if volume_ratio >= 2.0:
            # Strong volume
            scores['volume_spike'] = weights.get('volume_spike', 15)
        elif volume_ratio >= 1.5:
            # Moderate volume
            scores['volume_spike'] = weights.get('volume_spike', 15) * 0.7
        else:
            # Weak volume
            scores['volume_spike'] = 0

        # 3. Funding Rate (NEXUS Elite)
        funding = analysis.get('funding_rate', {})
        if funding and funding.get('signal'):
            funding_strength = abs(funding['signal'].get('strength', 0))
            max_weight = weights.get('funding_rate', 5)
            scores['funding_rate'] = (funding_strength / 3) * max_weight
        else:
            scores['funding_rate'] = 0
        
        # 3. Liquidity (FVG + OB presence)
        fvgs = analysis.get('fvgs', [])
        obs = analysis.get('order_blocks', [])
        
        has_fvg = len(fvgs) > 0
        has_ob = len(obs) > 0
        
        max_liquidity = weights.get('liquidity', 10)
        if has_fvg and has_ob:
            scores['liquidity'] = max_liquidity
        elif has_fvg or has_ob:
            scores['liquidity'] = max_liquidity * 0.5
        else:
            scores['liquidity'] = 0
        
        # 4. Range Duration
        if consolidation:
            duration = consolidation.get('duration_candles', 0)
            min_duration = 16
            max_duration = 50
            
            if duration >= min_duration:
                duration_ratio = min((duration - min_duration) / (max_duration - min_duration), 1.0)
                scores['range_duration'] = duration_ratio * weights.get('range_duration', 10)
            else:
                scores['range_duration'] = 0
        else:
            scores['range_duration'] = 0
        
        total = sum(scores.values())
        
        return {
            'scores': scores,
            'total': round(total, 1)
        }
    
    def _calculate_tier_1(self, analysis: Dict, direction: str) -> Dict:
        """
        Calculate Tier 1 score (Primary Signals)
        
        Args:
            analysis: Indicator analysis
            direction: Trade direction
            
        Returns:
            dict: Tier 1 scores
        """
        weights = self.weights['tier_1']
        scores = {}
        
        # 1. FVG Present
        fvgs = analysis.get('fvgs', [])
        if fvgs:
            # Check for relevant FVG based on direction
            relevant_fvgs = [
                fvg for fvg in fvgs
                if (direction == 'LONG' and fvg['type'] == 'BULLISH') or
                   (direction == 'SHORT' and fvg['type'] == 'BEARISH')
            ]
            if relevant_fvgs:
                # Use quality of best FVG
                best_quality = max(fvg.get('quality_score', 0) for fvg in relevant_fvgs)
                scores['fvg_present'] = (best_quality / 100) * weights.get('fvg_present', 8)
            else:
                scores['fvg_present'] = 0
        else:
            scores['fvg_present'] = 0
        
        # 2. HTF Alignment (simplified - using MA alignment as proxy)
        ma_alignment = analysis['indicators']['ma_alignment']
        if ma_alignment['aligned']:
            if (direction == 'LONG' and ma_alignment['direction'] == 'BULLISH') or \
               (direction == 'SHORT' and ma_alignment['direction'] == 'BEARISH'):
                scores['htf_alignment'] = weights.get('htf_alignment', 7)
            else:
                scores['htf_alignment'] = 0
        else:
            scores['htf_alignment'] = 0

        # NEXUS ELITE TIER 1 INDICATORS
        # 3. Ichimoku Cloud
        ichimoku = analysis.get('ichimoku', {})
        if ichimoku and ichimoku.get('signal'):
            ich_strength = abs(ichimoku['signal'].get('strength', 0))
            max_weight = weights.get('ichimoku', 8)
            scores['ichimoku'] = (ich_strength / 3) * max_weight
        else:
            scores['ichimoku'] = 0

        # 4. VWAP
        vwap = analysis.get('vwap', {})
        if vwap and vwap.get('signal'):
            vwap_strength = abs(vwap['signal'].get('strength', 0))
            max_weight = weights.get('vwap', 4)
            scores['vwap'] = (vwap_strength / 4) * max_weight
        else:
            scores['vwap'] = 0

        # 5. Volume Profile
        vol_profile = analysis.get('volume_profile', {})
        if vol_profile and vol_profile.get('signal'):
            vp_strength = abs(vol_profile['signal'].get('strength', 0))
            max_weight = weights.get('volume_profile', 6)
            scores['volume_profile'] = (vp_strength / 6) * max_weight
        else:
            scores['volume_profile'] = 0

        # 6. Stochastic RSI
        stoch_rsi = analysis.get('stoch_rsi', {})
        if stoch_rsi and stoch_rsi.get('signal'):
            stoch_strength = abs(stoch_rsi['signal'].get('strength', 0))
            max_weight = weights.get('stochastic_rsi', 5)
            scores['stochastic_rsi'] = (stoch_strength / 5) * max_weight
        else:
            scores['stochastic_rsi'] = 0

        # 7. MACD
        macd = analysis.get('macd', {})
        if macd and macd.get('signal'):
            macd_strength = abs(macd['signal'].get('strength', 0))
            max_weight = weights.get('macd', 5)
            scores['macd'] = (macd_strength / 5) * max_weight
        else:
            scores['macd'] = 0

        # 8. Bollinger Bands
        bollinger = analysis.get('bollinger', {})
        if bollinger and bollinger.get('signal'):
            bb_strength = abs(bollinger['signal'].get('strength', 0))
            max_weight = weights.get('bollinger_bands', 4)
            scores['bollinger_bands'] = (bb_strength / 4) * max_weight
        else:
            scores['bollinger_bands'] = 0

        # 9. HTF Structure
        htf_structure = analysis.get('htf_structure', {})
        if htf_structure and htf_structure.get('signal'):
            htf_strength = abs(htf_structure['signal'].get('strength', 0))
            max_weight = weights.get('htf_structure', 7)
            scores['htf_structure'] = (htf_strength / 7) * max_weight
        else:
            scores['htf_structure'] = 0
        
        # 3. Premium/Discount
        zones = analysis.get('zones')
        if zones:
            current_zone = zones.get('current', {})
            zone_name = current_zone.get('zone_name')
            quality = current_zone.get('quality_score', 0)
            
            # Check if zone matches direction
            if (direction == 'LONG' and zone_name == 'DISCOUNT') or \
               (direction == 'SHORT' and zone_name == 'PREMIUM'):
                scores['premium_discount'] = (quality / 100) * weights.get('premium_discount', 7)
            else:
                scores['premium_discount'] = 0
        else:
            scores['premium_discount'] = 0
        
        # 4. Order Block
        obs = analysis.get('order_blocks', [])
        if obs:
            relevant_obs = [
                ob for ob in obs
                if (direction == 'LONG' and ob['type'] == 'BULLISH') or
                   (direction == 'SHORT' and ob['type'] == 'BEARISH')
            ]
            if relevant_obs:
                best_quality = max(ob.get('quality_score', 0) for ob in relevant_obs)
                scores['order_block'] = (best_quality / 100) * weights.get('order_block', 7)
            else:
                scores['order_block'] = 0
        else:
            scores['order_block'] = 0
        
        # 5. Momentum (RSI)
        rsi = analysis['indicators']['rsi']
        rsi_value = rsi.get('value')
        
        if rsi_value:
            if direction == 'LONG' and rsi_value <= 40:
                # Oversold for LONG
                scores['momentum'] = weights.get('momentum', 6)
            elif direction == 'SHORT' and rsi_value >= 60:
                # Overbought for SHORT
                scores['momentum'] = weights.get('momentum', 6)
            else:
                scores['momentum'] = 0
        else:
            scores['momentum'] = 0
        
        total = sum(scores.values())
        
        return {
            'scores': scores,
            'total': round(total, 1)
        }
    
    def _calculate_tier_2(self, analysis: Dict) -> Dict:
        """
        Calculate Tier 2 score (Confirmation)
        
        Args:
            analysis: Indicator analysis
            
        Returns:
            dict: Tier 2 scores
        """
        weights = self.weights['tier_2']
        scores = {}
        
        # 1. Candlestick Pattern (placeholder - would need pattern recognition)
        # For now, award points if there's a breakout
        breakout = analysis.get('breakout')
        if breakout and breakout.get('has_volume_confirmation'):
            scores['candlestick_pattern'] = weights.get('candlestick_pattern', 5)
        else:
            scores['candlestick_pattern'] = 0
        
        # 2. MA Alignment
        ma_alignment = analysis['indicators']['ma_alignment']
        if ma_alignment['aligned']:
            strength_ratio = ma_alignment.get('strength', 0) / 100
            scores['ma_alignment'] = strength_ratio * weights.get('ma_alignment', 5)
        else:
            scores['ma_alignment'] = 0

        # 3. Liquidity Sweeps (NEXUS Elite)
        liquidity = analysis.get('liquidity_sweeps', {})
        if liquidity and liquidity.get('signal'):
            liq_strength = abs(liquidity['signal'].get('strength', 0))
            max_weight = weights.get('liquidity_sweeps', 8)
            scores['liquidity_sweeps'] = (liq_strength / 8) * max_weight
        else:
            scores['liquidity_sweeps'] = 0
        
        # 3. Fibonacci (uses premium/discount zones)
        zones = analysis.get('zones')
        if zones:
            current_zone = zones.get('current', {})
            quality = current_zone.get('quality_score', 0)
            scores['fibonacci'] = (quality / 100) * weights.get('fibonacci', 5)
        else:
            scores['fibonacci'] = 0
        
        total = sum(scores.values())
        
        return {
            'scores': scores,
            'total': round(total, 1)
        }
    
    def _get_grade(self, score: float) -> str:
        """
        Determine grade from score
        
        Args:
            score: Total score
            
        Returns:
            str: Grade (PREMIUM/VALID/WEAK/NO_TRADE)
        """
        if score >= self.thresholds['premium']:
            return 'PREMIUM'
        elif score >= self.thresholds['valid']:
            return 'VALID'
        elif score >= self.thresholds['weak']:
            return 'WEAK'
        else:
            return 'NO_TRADE'
    
    def is_tradeable(self, score_result: Dict) -> bool:
        """
        Check if score meets minimum trading threshold
        
        Args:
            score_result: Score result from calculate_score
            
        Returns:
            bool: True if score >= weak threshold
        """
        return score_result['total_score'] >= self.thresholds['weak']


# Convenience function
def get_scoring_engine(config_path: str = 'config/settings.yaml') -> ScoringEngine:
    """
    Factory function to create ScoringEngine
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        ScoringEngine instance
    """
    return ScoringEngine(config_path)


if __name__ == "__main__":
    """Test scoring engine"""
    
    import os
    from dotenv import load_dotenv
    from execution.binance_client import get_binance_client
    from core.indicator_manager import get_indicator_manager
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("Testing Scoring Engine")
    print("=" * 70)
    
    # Load credentials
    load_dotenv()
    
    # Initialize components
    print("\n[1] Initializing components...")
    client = get_binance_client(testnet=False)
    manager = get_indicator_manager(client)
    engine = get_scoring_engine()
    print("✅ Components initialized")
    
    # Analyze BTC
    print("\n[2] Analyzing BTCUSDT...")
    analysis = manager.analyze_symbol('BTCUSDT', primary_tf='15m')
    print("✅ Analysis complete")
    
    # Calculate scores for both directions
    print("\n[3] Calculating scores...")
    
    # LONG score
    long_score = engine.calculate_score(analysis, direction='LONG')
    
    # SHORT score
    short_score = engine.calculate_score(analysis, direction='SHORT')
    
    print("\n✅ SCORES CALCULATED!")
    print("\n   " + "─" * 68)
    
    # Display LONG score
    print(f"\n   📊 LONG SETUP SCORE:")
    print(f"   Total:    {long_score['total_score']:>6.1f}/100 ({long_score['grade']})")
    print(f"   Tier 0:   {long_score['tier_0']['total']:>6.1f}/50  (Structure + Volume)")
    print(f"   Tier 1:   {long_score['tier_1']['total']:>6.1f}/35  (Primary Signals)")
    print(f"   Tier 2:   {long_score['tier_2']['total']:>6.1f}/15  (Confirmation)")
    print(f"   Tradeable: {'✅ YES' if engine.is_tradeable(long_score) else '❌ NO'}")
    
    # Display SHORT score
    print(f"\n   📊 SHORT SETUP SCORE:")
    print(f"   Total:    {short_score['total_score']:>6.1f}/100 ({short_score['grade']})")
    print(f"   Tier 0:   {short_score['tier_0']['total']:>6.1f}/50  (Structure + Volume)")
    print(f"   Tier 1:   {short_score['tier_1']['total']:>6.1f}/35  (Primary Signals)")
    print(f"   Tier 2:   {short_score['tier_2']['total']:>6.1f}/15  (Confirmation)")
    print(f"   Tradeable: {'✅ YES' if engine.is_tradeable(short_score) else '❌ NO'}")
    
    # Show detailed breakdown for best score
    best = long_score if long_score['total_score'] > short_score['total_score'] else short_score
    
    print(f"\n   🎯 BEST SETUP: {best['direction']}")
    print(f"\n   Tier 0 Breakdown:")
    for key, val in best['tier_0']['scores'].items():
        print(f"   {key:25s}: {val:>5.1f}")
    
    print(f"\n   Tier 1 Breakdown:")
    for key, val in best['tier_1']['scores'].items():
        print(f"   {key:25s}: {val:>5.1f}")
    
    print(f"\n   Tier 2 Breakdown:")
    for key, val in best['tier_2']['scores'].items():
        print(f"   {key:25s}: {val:>5.1f}")
    
    print("\n   " + "─" * 68)
    
    print("\n" + "=" * 70)
    print("✅ Scoring engine test complete!")
    print("=" * 70)