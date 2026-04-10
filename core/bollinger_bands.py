"""
Bollinger Bands Module
=======================

Bollinger Bands measure volatility and potential reversal zones.

Components:
- Middle Band: 20 SMA
- Upper Band: Middle + (2 * Std Dev)
- Lower Band: Middle - (2 * Std Dev)

Signals:
- Price touches upper band = Overbought
- Price touches lower band = Oversold
- Bands squeeze = Low volatility (breakout coming)
- Bands expand = High volatility

Author: NEXUS Elite
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class BollingerBands:
    """Bollinger Bands calculator"""
    
    def __init__(
        self,
        period: int = 20,
        std_dev: float = 2.0
    ):
        """
        Initialize Bollinger Bands
        
        Args:
            period: SMA period (default 20)
            std_dev: Standard deviation multiplier (default 2.0)
        """
        self.period = period
        self.std_dev = std_dev
        
        logger.info(
            f"BollingerBands initialized "
            f"(period={period}, std_dev={std_dev})"
        )
    
    def calculate(self, df: pd.DataFrame) -> Dict:
        """
        Calculate Bollinger Bands
        
        Args:
            df: DataFrame with close prices
            
        Returns:
            dict: BB values and signals
        """
        try:
            if len(df) < self.period + 10:
                logger.warning(
                    f"Insufficient data for Bollinger Bands "
                    f"(need {self.period + 10}, got {len(df)})"
                )
                return self._empty_result()
            
            # Middle Band (SMA)
            middle = df['close'].rolling(window=self.period).mean()
            
            # Standard Deviation
            std = df['close'].rolling(window=self.period).std()
            
            # Upper and Lower Bands
            upper = middle + (self.std_dev * std)
            lower = middle - (self.std_dev * std)
            
            # Current values
            current_price = df['close'].iloc[-1]
            current_middle = middle.iloc[-1]
            current_upper = upper.iloc[-1]
            current_lower = lower.iloc[-1]
            current_std = std.iloc[-1]
            
            # Band width (volatility measure)
            band_width = (current_upper - current_lower) / current_middle * 100
            
            # %B (position within bands)
            percent_b = (current_price - current_lower) / (current_upper - current_lower)
            
            # Determine position
            if current_price > current_upper:
                position = 'above_upper'
            elif current_price < current_lower:
                position = 'below_lower'
            elif current_price > current_middle:
                position = 'upper_half'
            else:
                position = 'lower_half'
            
            # Squeeze detection (low volatility)
            avg_bandwidth = (upper - lower).iloc[-20:].mean() / middle.iloc[-20:].mean() * 100
            squeeze = band_width < avg_bandwidth * 0.7  # 30% tighter than average
            
            # Band expansion (high volatility)
            expansion = band_width > avg_bandwidth * 1.3  # 30% wider than average
            
            result = {
                'upper': current_upper,
                'middle': current_middle,
                'lower': current_lower,
                'current_price': current_price,
                'band_width': band_width,
                'percent_b': percent_b,
                'position': position,
                'squeeze': squeeze,
                'expansion': expansion,
                'std_dev': current_std
            }
            
            # Generate signal
            result['signal'] = self._generate_signal(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Bollinger Bands calculation error: {e}")
            return self._empty_result()
    
    def _generate_signal(self, data: Dict) -> Dict:
        """Generate trading signal"""
        strength = 0
        components = {}
        
        # Component 1: Position (+2/-2)
        if data['position'] == 'below_lower':
            strength += 2
            components['position'] = 'oversold_bounce'
        elif data['position'] == 'above_upper':
            strength -= 2
            components['position'] = 'overbought_reversal'
        
        # Component 2: Squeeze (volatility contraction) (+1)
        if data['squeeze']:
            strength += 1
            components['volatility'] = 'squeeze_breakout_coming'
        
        # Component 3: Mean reversion (+1/-1)
        if data['percent_b'] < 0.2:  # Near lower band
            strength += 1
            components['mean_reversion'] = 'bullish'
        elif data['percent_b'] > 0.8:  # Near upper band
            strength -= 1
            components['mean_reversion'] = 'bearish'
        
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
            'upper': 0,
            'middle': 0,
            'lower': 0,
            'current_price': 0,
            'band_width': 0,
            'percent_b': 0.5,
            'position': 'neutral',
            'squeeze': False,
            'expansion': False,
            'std_dev': 0,
            'signal': {
                'strength': 0,
                'direction': 'neutral',
                'components': {}
            }
        }


# Singleton
_bb = None

def get_bollinger_bands() -> BollingerBands:
    """Get singleton BollingerBands instance"""
    global _bb
    if _bb is None:
        _bb = BollingerBands()
    return _bb
