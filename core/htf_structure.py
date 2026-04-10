"""
HTF (Higher Timeframe) Structure Module
========================================

Analyzes higher timeframe trend and structure for context.

Analyzes H4 and D1 timeframes to determine:
- Overall trend direction
- Key structure levels
- HTF alignment with entry timeframe

Strong trades = HTF aligned with entry direction

Author: NEXUS Elite
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class HTFStructure:
    """Higher Timeframe Structure analyzer"""
    
    def __init__(self):
        """Initialize HTF Structure analyzer"""
        logger.info("HTFStructure initialized (H4/D1 analysis)")
    
    def analyze(
        self, 
        h4_data: pd.DataFrame = None,
        d1_data: pd.DataFrame = None,
        current_timeframe: str = '15m'
    ) -> Dict:
        """
        Analyze HTF structure
        
        Args:
            h4_data: H4 timeframe data (optional)
            d1_data: D1 timeframe data (optional)
            current_timeframe: Current trading timeframe
            
        Returns:
            dict: HTF analysis and signals
        """
        try:
            result = {
                'h4_trend': 'neutral',
                'h4_structure': 'neutral',
                'd1_trend': 'neutral',
                'd1_structure': 'neutral',
                'alignment': 'none',
                'strength': 0
            }
            
            # Analyze H4 if available
            if h4_data is not None and len(h4_data) >= 50:
                h4_analysis = self._analyze_timeframe(h4_data, 'H4')
                result['h4_trend'] = h4_analysis['trend']
                result['h4_structure'] = h4_analysis['structure']
            
            # Analyze D1 if available
            if d1_data is not None and len(d1_data) >= 50:
                d1_analysis = self._analyze_timeframe(d1_data, 'D1')
                result['d1_trend'] = d1_analysis['trend']
                result['d1_structure'] = d1_analysis['structure']
            
            # Check alignment
            result['alignment'] = self._check_alignment(
                result['h4_trend'],
                result['d1_trend']
            )
            
            # Generate signal
            result['signal'] = self._generate_signal(result)
            
            return result
            
        except Exception as e:
            logger.error(f"HTF Structure analysis error: {e}")
            return self._empty_result()
    
    def _analyze_timeframe(self, df: pd.DataFrame, tf: str) -> Dict:
        """
        Analyze single timeframe
        
        Args:
            df: OHLC data
            tf: Timeframe label
            
        Returns:
            dict: Trend and structure analysis
        """
        # Simple trend analysis using EMAs
        if len(df) < 50:
            return {'trend': 'neutral', 'structure': 'neutral'}
        
        # Calculate EMAs
        ema_20 = df['close'].ewm(span=20, adjust=False).mean()
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        current_price = df['close'].iloc[-1]
        current_ema20 = ema_20.iloc[-1]
        current_ema50 = ema_50.iloc[-1]
        
        # Trend determination
        if current_price > current_ema20 > current_ema50:
            trend = 'bullish'
        elif current_price < current_ema20 < current_ema50:
            trend = 'bearish'
        else:
            trend = 'neutral'
        
        # Structure analysis (simple swing high/low)
        highs = df['high'].iloc[-20:]
        lows = df['low'].iloc[-20:]
        
        # Higher highs and higher lows = bullish structure
        if (highs.iloc[-1] > highs.iloc[-10] and 
            lows.iloc[-1] > lows.iloc[-10]):
            structure = 'bullish'
        # Lower highs and lower lows = bearish structure
        elif (highs.iloc[-1] < highs.iloc[-10] and 
              lows.iloc[-1] < lows.iloc[-10]):
            structure = 'bearish'
        else:
            structure = 'neutral'
        
        return {
            'trend': trend,
            'structure': structure
        }
    
    def _check_alignment(self, h4_trend: str, d1_trend: str) -> str:
        """
        Check HTF alignment
        
        Returns:
            'bullish', 'bearish', or 'none'
        """
        if h4_trend == 'bullish' and d1_trend == 'bullish':
            return 'bullish'
        elif h4_trend == 'bearish' and d1_trend == 'bearish':
            return 'bearish'
        elif h4_trend == 'bullish' or d1_trend == 'bullish':
            return 'mixed_bullish'
        elif h4_trend == 'bearish' or d1_trend == 'bearish':
            return 'mixed_bearish'
        else:
            return 'none'
    
    def _generate_signal(self, data: Dict) -> Dict:
        """Generate trading signal"""
        strength = 0
        components = {}
        
        # Component 1: Full alignment (+4/-4)
        if data['alignment'] == 'bullish':
            strength += 4
            components['alignment'] = 'full_bullish'
        elif data['alignment'] == 'bearish':
            strength -= 4
            components['alignment'] = 'full_bearish'
        
        # Component 2: Partial alignment (+2/-2)
        elif data['alignment'] == 'mixed_bullish':
            strength += 2
            components['alignment'] = 'partial_bullish'
        elif data['alignment'] == 'mixed_bearish':
            strength -= 2
            components['alignment'] = 'partial_bearish'
        
        # Component 3: Structure confirmation (+1/-1)
        if data['h4_structure'] == 'bullish':
            strength += 1
            components['h4_structure'] = 'bullish'
        elif data['h4_structure'] == 'bearish':
            strength -= 1
            components['h4_structure'] = 'bearish'
        
        # Direction
        if strength >= 3:
            direction = 'long'
        elif strength <= -3:
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
            'h4_trend': 'neutral',
            'h4_structure': 'neutral',
            'd1_trend': 'neutral',
            'd1_structure': 'neutral',
            'alignment': 'none',
            'strength': 0,
            'signal': {
                'strength': 0,
                'direction': 'neutral',
                'components': {}
            }
        }


# Singleton
_htf = None

def get_htf_structure() -> HTFStructure:
    """Get singleton HTFStructure instance"""
    global _htf
    if _htf is None:
        _htf = HTFStructure()
    return _htf
