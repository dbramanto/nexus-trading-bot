"""
Funding Rate Module
===================

Funding rate analysis for perpetual futures sentiment.

Funding Rate:
- Positive = Longs pay Shorts (market bullish)
- Negative = Shorts pay Longs (market bearish)
- High positive = Overleveraged longs (reversal risk)
- High negative = Overleveraged shorts (bounce risk)

Thresholds:
- Extreme positive: >0.1% (bearish contrarian)
- Extreme negative: <-0.1% (bullish contrarian)

Author: NEXUS Elite
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class FundingRate:
    """Funding Rate analyzer for perpetuals sentiment"""
    
    def __init__(
        self,
        extreme_positive: float = 0.1,
        extreme_negative: float = -0.1
    ):
        """
        Initialize Funding Rate analyzer
        
        Args:
            extreme_positive: Extreme positive threshold % (default 0.1)
            extreme_negative: Extreme negative threshold % (default -0.1)
        """
        self.extreme_positive = extreme_positive
        self.extreme_negative = extreme_negative
        
        logger.info(
            f"FundingRate initialized "
            f"(extreme_pos={extreme_positive}%, extreme_neg={extreme_negative}%)"
        )
    
    def analyze(self, funding_rate: float) -> Dict:
        """
        Analyze funding rate
        
        Args:
            funding_rate: Current funding rate (%)
            
        Returns:
            dict: Funding analysis and signals
        """
        try:
            # Determine sentiment
            if funding_rate > self.extreme_positive:
                sentiment = 'extreme_bullish'
                contrarian = 'bearish'
            elif funding_rate > 0.05:
                sentiment = 'bullish'
                contrarian = 'cautious'
            elif funding_rate > 0:
                sentiment = 'slightly_bullish'
                contrarian = 'neutral'
            elif funding_rate > self.extreme_negative:
                sentiment = 'slightly_bearish'
                contrarian = 'neutral'
            elif funding_rate > -0.05:
                sentiment = 'bearish'
                contrarian = 'cautious'
            else:
                sentiment = 'extreme_bearish'
                contrarian = 'bullish'
            
            # Risk assessment
            if abs(funding_rate) > 0.1:
                risk = 'high'  # Overleveraged, reversal risk
            elif abs(funding_rate) > 0.05:
                risk = 'moderate'
            else:
                risk = 'low'
            
            result = {
                'funding_rate': funding_rate,
                'sentiment': sentiment,
                'contrarian_signal': contrarian,
                'risk': risk,
                'abs_value': abs(funding_rate)
            }
            
            # Generate signal
            result['signal'] = self._generate_signal(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Funding Rate analysis error: {e}")
            return self._empty_result()
    
    def _generate_signal(self, data: Dict) -> Dict:
        """Generate trading signal"""
        strength = 0
        components = {}
        
        # Contrarian approach: Extreme funding = reversal opportunity
        
        # Component 1: Extreme levels (+3/-3)
        if data['sentiment'] == 'extreme_bullish':
            strength -= 3  # Too many longs, expect reversal down
            components['extreme'] = 'overleveraged_longs'
        elif data['sentiment'] == 'extreme_bearish':
            strength += 3  # Too many shorts, expect bounce up
            components['extreme'] = 'overleveraged_shorts'
        
        # Component 2: Moderate sentiment (+1/-1)
        elif data['sentiment'] == 'bullish':
            strength += 1  # Follow the flow
            components['flow'] = 'bullish'
        elif data['sentiment'] == 'bearish':
            strength -= 1
            components['flow'] = 'bearish'
        
        # Direction
        if strength >= 2:
            direction = 'long'
        elif strength <= -2:
            direction = 'short'
        else:
            direction = 'neutral'
        
        return {
            'strength': strength,
            'direction': direction,
            'components': components
        }
    
    def _empty_result(self) -> Dict:
        """Return empty result"""
        return {
            'funding_rate': 0,
            'sentiment': 'neutral',
            'contrarian_signal': 'neutral',
            'risk': 'low',
            'abs_value': 0,
            'signal': {
                'strength': 0,
                'direction': 'neutral',
                'components': {}
            }
        }


# Singleton
_funding = None

def get_funding_rate() -> FundingRate:
    """Get singleton FundingRate instance"""
    global _funding
    if _funding is None:
        _funding = FundingRate()
    return _funding
