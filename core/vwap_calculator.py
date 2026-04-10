"""
VWAP (Volume Weighted Average Price) Module
============================================

VWAP is the average price weighted by volume.
Used to identify institutional buying/selling zones.

Formula: VWAP = Σ(Typical Price × Volume) / Σ(Volume)
where Typical Price = (High + Low + Close) / 3

Author: NEXUS Elite
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class VWAPCalculator:
    """VWAP calculator and signal generator"""
    
    def __init__(self, session_reset_hour: int = 0):
        """
        Initialize VWAP calculator
        
        Args:
            session_reset_hour: Hour to reset VWAP (default 0 = midnight UTC)
        """
        self.session_reset_hour = session_reset_hour
        logger.info(f"VWAPCalculator initialized (reset_hour={session_reset_hour})")
    
    def calculate(self, df: pd.DataFrame) -> Dict:
        """
        Calculate VWAP and generate signals
        
        Args:
            df: DataFrame with OHLC + volume data
            
        Returns:
            dict: VWAP values and signals
        """
        try:
            if len(df) < 10:
                logger.warning(f"Insufficient data for VWAP (need 10, got {len(df)})")
                return self._empty_result()
            
            # Calculate typical price
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            
            # Calculate VWAP (cumulative)
            cumulative_tp_volume = (typical_price * df['volume']).cumsum()
            cumulative_volume = df['volume'].cumsum()
            vwap = cumulative_tp_volume / cumulative_volume
            
            # Current values
            current_price = df['close'].iloc[-1]
            current_vwap = vwap.iloc[-1]
            
            # Price position relative to VWAP
            if current_price > current_vwap:
                position = 'above'
            elif current_price < current_vwap:
                position = 'below'
            else:
                position = 'at'
            
            # Deviation from VWAP (%)
            deviation_pct = ((current_price - current_vwap) / current_vwap) * 100
            
            # Check for recent VWAP cross
            vwap_cross = self._check_vwap_cross(df['close'], vwap)
            
            # Distance bands (standard deviations)
            price_series = df['close'].iloc[-20:]  # Last 20 candles
            std_dev = price_series.std()
            
            upper_band = current_vwap + (2 * std_dev)
            lower_band = current_vwap - (2 * std_dev)
            
            result = {
                'vwap': current_vwap,
                'current_price': current_price,
                'position': position,
                'deviation_pct': deviation_pct,
                'deviation_abs': abs(current_price - current_vwap),
                'vwap_cross': vwap_cross,
                'upper_band': upper_band,
                'lower_band': lower_band,
                'std_dev': std_dev,
                'near_vwap': abs(deviation_pct) < 0.5  # Within 0.5%
            }
            
            # Generate signal
            result['signal'] = self._generate_signal(result)
            
            return result
            
        except Exception as e:
            logger.error(f"VWAP calculation error: {e}")
            return self._empty_result()
    
    def _check_vwap_cross(self, price: pd.Series, vwap: pd.Series) -> str:
        """
        Check for recent VWAP cross
        
        Returns:
            'bullish', 'bearish', or 'none'
        """
        if len(price) < 2 or len(vwap) < 2:
            return 'none'
        
        # Current state
        price_above = price.iloc[-1] > vwap.iloc[-1]
        
        # Previous state
        price_above_prev = price.iloc[-2] > vwap.iloc[-2]
        
        # Detect cross
        if price_above and not price_above_prev:
            return 'bullish'
        elif not price_above and price_above_prev:
            return 'bearish'
        return 'none'
    
    def _generate_signal(self, data: Dict) -> Dict:
        """
        Generate trading signal from VWAP
        
        Returns:
            dict: strength, direction, components
        """
        strength = 0
        components = {}
        
        # Component 1: Position relative to VWAP (+2/-2)
        if data['position'] == 'above':
            strength += 2
            components['position'] = 'bullish'
        elif data['position'] == 'below':
            strength -= 2
            components['position'] = 'bearish'
        
        # Component 2: Recent cross (+1/-1)
        if data['vwap_cross'] == 'bullish':
            strength += 1
            components['cross'] = 'bullish'
        elif data['vwap_cross'] == 'bearish':
            strength -= 1
            components['cross'] = 'bearish'
        
        # Component 3: Near VWAP = fair value (+1)
        if data['near_vwap']:
            strength += 1 if data['position'] == 'above' else -1
            components['fair_value'] = 'near'
        
        # Determine direction
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
        """Return empty result on error"""
        return {
            'vwap': 0,
            'current_price': 0,
            'position': 'unknown',
            'deviation_pct': 0,
            'deviation_abs': 0,
            'vwap_cross': 'none',
            'upper_band': 0,
            'lower_band': 0,
            'std_dev': 0,
            'near_vwap': False,
            'signal': {
                'strength': 0,
                'direction': 'neutral',
                'components': {}
            }
        }


# Singleton
_vwap = None

def get_vwap_calculator() -> VWAPCalculator:
    """Get singleton VWAP instance"""
    global _vwap
    if _vwap is None:
        _vwap = VWAPCalculator()
    return _vwap
