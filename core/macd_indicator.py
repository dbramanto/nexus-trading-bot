"""
MACD (Moving Average Convergence Divergence) Module
====================================================

MACD is a trend-following momentum indicator.

Components:
- MACD Line: 12 EMA - 26 EMA
- Signal Line: 9 EMA of MACD
- Histogram: MACD - Signal

Signals:
- MACD crosses above Signal = Bullish
- MACD crosses below Signal = Bearish
- Histogram growing = Momentum increasing

Author: NEXUS Elite
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class MACDIndicator:
    """MACD calculator and signal generator"""
    
    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ):
        """
        Initialize MACD
        
        Args:
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line period (default 9)
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        
        logger.info(
            f"MACDIndicator initialized "
            f"(fast={fast_period}, slow={slow_period}, signal={signal_period})"
        )
    
    def calculate(self, df: pd.DataFrame) -> Dict:
        """
        Calculate MACD
        
        Args:
            df: DataFrame with close prices
            
        Returns:
            dict: MACD values and signals
        """
        try:
            min_bars = self.slow_period + self.signal_period + 10
            if len(df) < min_bars:
                logger.warning(
                    f"Insufficient data for MACD "
                    f"(need {min_bars}, got {len(df)})"
                )
                return self._empty_result()
            
            # Calculate EMAs
            ema_fast = df['close'].ewm(span=self.fast_period, adjust=False).mean()
            ema_slow = df['close'].ewm(span=self.slow_period, adjust=False).mean()
            
            # MACD Line
            macd_line = ema_fast - ema_slow
            
            # Signal Line
            signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()
            
            # Histogram
            histogram = macd_line - signal_line
            
            # Current values
            current_macd = macd_line.iloc[-1]
            current_signal = signal_line.iloc[-1]
            current_hist = histogram.iloc[-1]
            
            # Previous values for trend
            prev_hist = histogram.iloc[-2] if len(histogram) > 1 else 0
            
            # Determine state
            if current_macd > current_signal:
                state = 'bullish'
            elif current_macd < current_signal:
                state = 'bearish'
            else:
                state = 'neutral'
            
            # Check for cross
            macd_cross = self._check_cross(macd_line, signal_line)
            
            # Histogram momentum
            hist_momentum = 'increasing' if current_hist > prev_hist else 'decreasing'
            
            # Zero line cross
            zero_cross = self._check_zero_cross(macd_line)
            
            result = {
                'macd': current_macd,
                'signal': current_signal,
                'histogram': current_hist,
                'state': state,
                'macd_cross': macd_cross,
                'hist_momentum': hist_momentum,
                'zero_cross': zero_cross,
                'divergence_strength': abs(current_macd - current_signal)
            }
            
            # Generate signal
            result['signal'] = self._generate_signal(result)
            
            return result
            
        except Exception as e:
            logger.error(f"MACD calculation error: {e}")
            return self._empty_result()
    
    def _check_cross(self, macd: pd.Series, signal: pd.Series) -> str:
        """Check for MACD/Signal cross"""
        if len(macd) < 2 or len(signal) < 2:
            return 'none'
        
        macd_above = macd.iloc[-1] > signal.iloc[-1]
        macd_above_prev = macd.iloc[-2] > signal.iloc[-2]
        
        if macd_above and not macd_above_prev:
            return 'bullish'
        elif not macd_above and macd_above_prev:
            return 'bearish'
        return 'none'
    
    def _check_zero_cross(self, macd: pd.Series) -> str:
        """Check for zero line cross"""
        if len(macd) < 2:
            return 'none'
        
        curr_positive = macd.iloc[-1] > 0
        prev_positive = macd.iloc[-2] > 0
        
        if curr_positive and not prev_positive:
            return 'bullish'
        elif not curr_positive and prev_positive:
            return 'bearish'
        return 'none'
    
    def _generate_signal(self, data: Dict) -> Dict:
        """Generate trading signal"""
        strength = 0
        components = {}
        
        # Component 1: MACD/Signal cross (+2/-2)
        if data['macd_cross'] == 'bullish':
            strength += 2
            components['cross'] = 'bullish'
        elif data['macd_cross'] == 'bearish':
            strength -= 2
            components['cross'] = 'bearish'
        
        # Component 2: Current state (+1/-1)
        if data['state'] == 'bullish':
            strength += 1
            components['state'] = 'bullish'
        elif data['state'] == 'bearish':
            strength -= 1
            components['state'] = 'bearish'
        
        # Component 3: Histogram momentum (+1/-1)
        if data['hist_momentum'] == 'increasing':
            if data['histogram'] > 0:
                strength += 1
                components['momentum'] = 'bullish'
        else:
            if data['histogram'] < 0:
                strength -= 1
                components['momentum'] = 'bearish'
        
        # Component 4: Zero line cross (+1/-1)
        if data['zero_cross'] == 'bullish':
            strength += 1
            components['zero_cross'] = 'bullish'
        elif data['zero_cross'] == 'bearish':
            strength -= 1
            components['zero_cross'] = 'bearish'
        
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
            'macd': 0,
            'signal': 0,
            'histogram': 0,
            'state': 'neutral',
            'macd_cross': 'none',
            'hist_momentum': 'neutral',
            'zero_cross': 'none',
            'divergence_strength': 0,
            'signal': {
                'strength': 0,
                'direction': 'neutral',
                'components': {}
            }
        }


# Singleton
_macd = None

def get_macd_indicator() -> MACDIndicator:
    """Get singleton MACD instance"""
    global _macd
    if _macd is None:
        _macd = MACDIndicator()
    return _macd
