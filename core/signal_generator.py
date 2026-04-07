"""
NEXUS Bot - Signal Generator
Generates entry signals from scoring analysis
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime

# Setup logging
logger = logging.getLogger(__name__)


class SignalGenerator:
    """
    Generates trading signals from scoring results
    
    Evaluates both LONG and SHORT directions
    Selects best direction if score meets threshold
    """
    
    def __init__(
        self,
        min_score: float = 55.0,
        min_score_diff: float = 5.0
    ):
        """
        Initialize signal generator
        
        Args:
            min_score: Minimum score to generate signal
            min_score_diff: Minimum difference between directions
        """
        self.min_score = min_score
        self.min_score_diff = min_score_diff
        
        logger.info(
            f"SignalGenerator initialized "
            f"(min_score={min_score}, min_diff={min_score_diff})"
        )
    
    def generate_signal(
        self,
        long_score: Dict,
        short_score: Dict,
        analysis: Dict
    ) -> Dict:
        """
        Generate trading signal from scores
        
        Args:
            long_score: LONG score from ScoringEngine
            short_score: SHORT score from ScoringEngine
            analysis: Full indicator analysis
            
        Returns:
            dict: Signal data
        """
        symbol = analysis.get('symbol', 'UNKNOWN')
        current_price = analysis.get('current_price')
        
        logger.info(
            f"Generating signal for {symbol} - "
            f"LONG:{long_score['total_score']:.1f} SHORT:{short_score['total_score']:.1f}"
        )
        
        # Check if either direction meets minimum threshold
        long_valid = long_score['total_score'] >= self.min_score
        short_valid = short_score['total_score'] >= self.min_score
        
        # No valid signals
        if not long_valid and not short_valid:
            return self._no_signal(
                symbol,
                current_price,
                reason="Both scores below minimum threshold",
                long_score=long_score['total_score'],
                short_score=short_score['total_score']
            )
        
        # Both valid - select best
        if long_valid and short_valid:
            # Check score difference
            score_diff = abs(long_score['total_score'] - short_score['total_score'])
            
            if score_diff < self.min_score_diff:
                # Too close - ambiguous signal
                return self._no_signal(
                    symbol,
                    current_price,
                    reason="Scores too close (ambiguous direction)",
                    long_score=long_score['total_score'],
                    short_score=short_score['total_score']
                )
            
            # Select higher score
            if long_score['total_score'] > short_score['total_score']:
                selected_score = long_score
                direction = 'LONG'
            else:
                selected_score = short_score
                direction = 'SHORT'
        
        # Only LONG valid
        elif long_valid:
            selected_score = long_score
            direction = 'LONG'
        
        # Only SHORT valid
        else:
            selected_score = short_score
            direction = 'SHORT'
        
        # Generate signal
        signal = self._create_signal(
            symbol=symbol,
            direction=direction,
            score_result=selected_score,
            analysis=analysis
        )
        
        logger.info(
            f"Signal generated: {direction} {signal['grade']} "
            f"(score: {signal['score']:.1f})"
        )
        
        return signal
    
    def _create_signal(
        self,
        symbol: str,
        direction: str,
        score_result: Dict,
        analysis: Dict
    ) -> Dict:
        """
        Create signal object
        
        Args:
            symbol: Trading symbol
            direction: LONG or SHORT
            score_result: Score result from engine
            analysis: Full analysis
            
        Returns:
            dict: Signal data
        """
        # Extract key reasons for signal
        reasons = self._extract_reasons(score_result, analysis, direction)
        
        # Get entry price
        current_price = analysis.get('current_price')
        
        signal = {
            'has_signal': True,
            'symbol': symbol,
            'direction': direction,
            'score': score_result['total_score'],
            'grade': score_result['grade'],
            'entry_price': current_price,
            'reasons': reasons,
            'timestamp': datetime.now(),
            'score_breakdown': {
                'tier_0': score_result['tier_0']['total'],
                'tier_1': score_result['tier_1']['total'],
                'tier_2': score_result['tier_2']['total']
            },
            'analysis': analysis  # Include full analysis for position calculator
        }
        
        return signal
    
    def _extract_reasons(
        self,
        score_result: Dict,
        analysis: Dict,
        direction: str
    ) -> List[str]:
        """
        Extract key reasons for the signal
        
        Args:
            score_result: Score result
            analysis: Analysis data
            direction: Trade direction
            
        Returns:
            list: List of reason strings
        """
        reasons = []
        
        # Check Tier 0 components
        tier_0 = score_result['tier_0']['scores']
        if tier_0.get('consolidation_quality', 0) > 0:
            reasons.append('consolidation_detected')
        if tier_0.get('volume_spike', 0) > 0:
            reasons.append('high_volume')
        if tier_0.get('liquidity', 0) > 0:
            reasons.append('liquidity_zones')
        
        # Check Tier 1 components
        tier_1 = score_result['tier_1']['scores']
        if tier_1.get('fvg_present', 0) > 0:
            reasons.append(f'fvg_{direction.lower()}')
        if tier_1.get('htf_alignment', 0) > 0:
            reasons.append('trend_aligned')
        if tier_1.get('premium_discount', 0) > 0:
            zone = 'discount' if direction == 'LONG' else 'premium'
            reasons.append(f'{zone}_zone')
        if tier_1.get('order_block', 0) > 0:
            reasons.append(f'orderblock_{direction.lower()}')
        if tier_1.get('momentum', 0) > 0:
            reasons.append('momentum_favorable')
        
        # Check Tier 2 components
        tier_2 = score_result['tier_2']['scores']
        if tier_2.get('ma_alignment', 0) > 0:
            reasons.append('ma_aligned')
        
        return reasons
    
    def _no_signal(
        self,
        symbol: str,
        current_price: Optional[float],
        reason: str,
        long_score: float = 0,
        short_score: float = 0
    ) -> Dict:
        """
        Create NO SIGNAL response
        
        Args:
            symbol: Trading symbol
            current_price: Current price
            reason: Reason for no signal
            long_score: LONG score
            short_score: SHORT score
            
        Returns:
            dict: No signal data
        """
        logger.info(f"No signal for {symbol}: {reason}")
        
        return {
            'has_signal': False,
            'symbol': symbol,
            'direction': None,
            'score': max(long_score, short_score),
            'grade': 'NO_TRADE',
            'entry_price': current_price,
            'reasons': [reason],
            'timestamp': datetime.now(),
            'score_breakdown': {
                'long_score': long_score,
                'short_score': short_score
            },
            'analysis': None
        }
    
    def validate_signal_conditions(self, signal: Dict) -> Dict:
        """
        Perform additional validation on signal
        
        Args:
            signal: Signal from generate_signal
            
        Returns:
            dict: Validation result
        """
        if not signal['has_signal']:
            return {
                'valid': False,
                'reason': 'No signal generated'
            }
        
        # Check if analysis exists
        if not signal.get('analysis'):
            return {
                'valid': False,
                'reason': 'Missing analysis data'
            }
        
        analysis = signal['analysis']
        
        # Consolidation required for our strategy
        if not analysis.get('consolidation'):
            return {
                'valid': False,
                'reason': 'No consolidation detected (required for our strategy)'
            }
        
        # Check for breakout if consolidation exists
        consolidation = analysis['consolidation']
        breakout = analysis.get('breakout')
        
        # For entry, we prefer either:
        # 1. Price in consolidation (pre-breakout)
        # 2. Fresh breakout with volume
        
        current_price = analysis['current_price']
        range_low = consolidation['range_low']
        range_high = consolidation['range_high']
        
        in_range = range_low <= current_price <= range_high
        
        # If not in range, must have valid breakout
        if not in_range and not breakout:
            return {
                'valid': False,
                'reason': 'Price outside range without confirmed breakout'
            }
        
        # If breakout exists, check confirmation
        if breakout:
            if not breakout.get('has_volume_confirmation'):
                return {
                    'valid': False,
                    'reason': 'Breakout lacks volume confirmation'
                }
            
            if breakout.get('type') != 'CONFIRMED':
                return {
                    'valid': False,
                    'reason': 'Breakout not confirmed (close required)'
                }
        
        # All checks passed
        return {
            'valid': True,
            'reason': 'All validation checks passed'
        }


# Convenience function
def get_signal_generator(
    min_score: float = 55.0,
    min_score_diff: float = 5.0
) -> SignalGenerator:
    """
    Factory function to create SignalGenerator
    
    Args:
        min_score: Minimum score threshold
        min_score_diff: Minimum score difference
        
    Returns:
        SignalGenerator instance
    """
    return SignalGenerator(min_score, min_score_diff)


if __name__ == "__main__":
    """Test signal generator"""
    
    import os
    from dotenv import load_dotenv
    from execution.binance_client import get_binance_client
    from core.indicator_manager import get_indicator_manager
    from core.scoring_engine import get_scoring_engine
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("Testing Signal Generator")
    print("=" * 70)
    
    # Load credentials
    load_dotenv()
    
    # Initialize components
    print("\n[1] Initializing components...")
    client = get_binance_client(testnet=False)
    manager = get_indicator_manager(client)
    scoring_engine = get_scoring_engine()
    signal_gen = get_signal_generator(min_score=55.0, min_score_diff=5.0)
    print("✅ Components initialized")
    
    # Analyze BTC
    print("\n[2] Analyzing BTCUSDT...")
    analysis = manager.analyze_symbol('BTCUSDT', primary_tf='15m')
    print("✅ Analysis complete")
    
    # Calculate scores
    print("\n[3] Calculating scores...")
    long_score = scoring_engine.calculate_score(analysis, 'LONG')
    short_score = scoring_engine.calculate_score(analysis, 'SHORT')
    print(f"   LONG:  {long_score['total_score']:.1f} ({long_score['grade']})")
    print(f"   SHORT: {short_score['total_score']:.1f} ({short_score['grade']})")
    
    # Generate signal
    print("\n[4] Generating signal...")
    signal = signal_gen.generate_signal(long_score, short_score, analysis)
    
    print("\n   " + "─" * 68)
    
    if signal['has_signal']:
        print(f"\n   ✅ SIGNAL GENERATED!")
        print(f"\n   Direction:    {signal['direction']}")
        print(f"   Score:        {signal['score']:.1f}/100")
        print(f"   Grade:        {signal['grade']}")
        print(f"   Entry Price:  ${signal['entry_price']:,.2f}")
        print(f"   Timestamp:    {signal['timestamp']}")
        
        print(f"\n   Score Breakdown:")
        print(f"   Tier 0:       {signal['score_breakdown']['tier_0']:.1f}/50")
        print(f"   Tier 1:       {signal['score_breakdown']['tier_1']:.1f}/35")
        print(f"   Tier 2:       {signal['score_breakdown']['tier_2']:.1f}/15")
        
        print(f"\n   Key Reasons:")
        for reason in signal['reasons']:
            print(f"   • {reason}")
        
        # Validate signal
        print("\n[5] Validating signal conditions...")
        validation = signal_gen.validate_signal_conditions(signal)
        
        if validation['valid']:
            print(f"   ✅ SIGNAL VALID: {validation['reason']}")
        else:
            print(f"   ❌ SIGNAL INVALID: {validation['reason']}")
        
    else:
        print(f"\n   ❌ NO SIGNAL")
        print(f"\n   Reason:       {signal['reasons'][0]}")
        print(f"   LONG Score:   {signal['score_breakdown']['long_score']:.1f}")
        print(f"   SHORT Score:  {signal['score_breakdown']['short_score']:.1f}")
        print(f"   Threshold:    {signal_gen.min_score:.1f}")
        
        print(f"\n   ℹ️  WAITING FOR BETTER SETUP")
        print(f"      Need: Score ≥ {signal_gen.min_score}")
        print(f"      Currently: Best score = {signal['score']:.1f}")
    
    print("\n   " + "─" * 68)
    
    print("\n" + "=" * 70)
    print("✅ Signal generator test complete!")
    print("=" * 70)