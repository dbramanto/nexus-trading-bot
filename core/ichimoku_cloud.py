"""
Ichimoku Cloud Indicator Module
================================

Implements full Ichimoku Kinko Hyo system for NEXUS Elite

Components:
- Tenkan-sen (Conversion Line): 9-period midpoint
- Kijun-sen (Base Line): 26-period midpoint  
- Senkou Span A (Leading Span A): (Tenkan + Kijun) / 2, shifted +26
- Senkou Span B (Leading Span B): 52-period midpoint, shifted +26
- Chikou Span (Lagging Span): Current close shifted -26
- Kumo (Cloud): Area between Senkou A & B

Author: NEXUS Elite
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class IchimokuCloud:
    """Ichimoku Cloud calculator and signal generator"""
    
    def __init__(
        self,
        tenkan_period: int = 9,
        kijun_period: int = 26,
        senkou_b_period: int = 52,
        displacement: int = 26
    ):
        """
        Initialize Ichimoku Cloud
        
        Args:
            tenkan_period: Conversion line period (default 9)
            kijun_period: Base line period (default 26)
            senkou_b_period: Leading Span B period (default 52)
            displacement: Cloud shift forward (default 26)
        """
        self.tenkan_period = tenkan_period
        self.kijun_period = kijun_period
        self.senkou_b_period = senkou_b_period
        self.displacement = displacement
        
        logger.info(
            f"IchimokuCloud initialized "
            f"(T={tenkan_period}, K={kijun_period}, "
            f"SB={senkou_b_period}, D={displacement})"
        )
    
    def calculate(self, df: pd.DataFrame) -> Dict:
        """
        Calculate all Ichimoku components
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            dict: Ichimoku values and signals
        """
        try:
            # Need minimum bars
            min_bars = self.senkou_b_period + 10
            if len(df) < min_bars:
                logger.warning(
                    f"Insufficient data for Ichimoku "
                    f"(need {min_bars}, got {len(df)})"
                )
                return self._empty_result()
            
            # Calculate lines
            tenkan = self._calc_line(df, self.tenkan_period)
            kijun = self._calc_line(df, self.kijun_period)
            senkou_a = (tenkan + kijun) / 2
            senkou_b = self._calc_line(df, self.senkou_b_period)
            
            # Current values
            current_price = df['close'].iloc[-1]
            cloud_top = max(senkou_a.iloc[-1], senkou_b.iloc[-1])
            cloud_bottom = min(senkou_a.iloc[-1], senkou_b.iloc[-1])
            
            # Cloud color
            cloud_bullish = senkou_a.iloc[-1] > senkou_b.iloc[-1]
            
            # Price position
            if current_price > cloud_top:
                price_pos = 'above'
            elif current_price < cloud_bottom:
                price_pos = 'below'
            else:
                price_pos = 'inside'
            
            # TK Cross
            tk_cross = self._check_tk_cross(tenkan, kijun)
            
            # Chikou
            chikou_bullish = False
            if len(df) >= self.displacement:
                past_price = df['close'].iloc[-self.displacement]
                chikou_bullish = current_price > past_price
            
            result = {
                'tenkan': tenkan.iloc[-1],
                'kijun': kijun.iloc[-1],
                'senkou_a': senkou_a.iloc[-1],
                'senkou_b': senkou_b.iloc[-1],
                'cloud_top': cloud_top,
                'cloud_bottom': cloud_bottom,
                'cloud_bullish': cloud_bullish,
                'cloud_thickness': cloud_top - cloud_bottom,
                'price_position': price_pos,
                'tk_cross': tk_cross,
                'chikou_bullish': chikou_bullish,
                'current_price': current_price
            }
            
            # Generate signals
            result['signal'] = self._generate_signal(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Ichimoku calculation error: {e}")
            return self._empty_result()
    
    def _calc_line(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate (high + low) / 2 over period"""
        high_max = df['high'].rolling(window=period).max()
        low_min = df['low'].rolling(window=period).min()
        return (high_max + low_min) / 2
    
    def _check_tk_cross(self, tenkan: pd.Series, kijun: pd.Series) -> str:
        """
        Check Tenkan-Kijun cross
        
        Returns:
            'bullish', 'bearish', or 'none'
        """
        if len(tenkan) < 2 or len(kijun) < 2:
            return 'none'
        
        curr_above = tenkan.iloc[-1] > kijun.iloc[-1]
        prev_above = tenkan.iloc[-2] > kijun.iloc[-2]
        
        if curr_above and not prev_above:
            return 'bullish'
        elif not curr_above and prev_above:
            return 'bearish'
        return 'none'
    
    def _generate_signal(self, data: Dict) -> Dict:
        """
        Generate trading signal from Ichimoku
        
        Returns:
            dict: strength (-3 to +3), direction, components
        """
        strength = 0
        components = {}
        
        # Price vs Cloud (+2/-2)
        if data['price_position'] == 'above':
            strength += 2
            components['cloud'] = 'bullish'
        elif data['price_position'] == 'below':
            strength -= 2
            components['cloud'] = 'bearish'
        else:
            components['cloud'] = 'neutral'
        
        # TK Cross (+1/-1)
        if data['tk_cross'] == 'bullish':
            strength += 1
            components['tk_cross'] = 'bullish'
        elif data['tk_cross'] == 'bearish':
            strength -= 1
            components['tk_cross'] = 'bearish'
        
        # Chikou (+1/0)
        if data['price_position'] == 'above' and data['chikou_bullish']:
            strength += 1
            components['chikou'] = 'bullish'
        elif data['price_position'] == 'below' and not data['chikou_bullish']:
            strength += 1
            components['chikou'] = 'bearish'
        
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
            'tenkan': 0,
            'kijun': 0,
            'senkou_a': 0,
            'senkou_b': 0,
            'cloud_top': 0,
            'cloud_bottom': 0,
            'cloud_bullish': False,
            'cloud_thickness': 0,
            'price_position': 'unknown',
            'tk_cross': 'none',
            'chikou_bullish': False,
            'current_price': 0,
            'signal': {
                'strength': 0,
                'direction': 'neutral',
                'components': {}
            }
        }


# Singleton
_ichimoku = None

def get_ichimoku_cloud() -> IchimokuCloud:
    """Get singleton Ichimoku instance"""
    global _ichimoku
    if _ichimoku is None:
        _ichimoku = IchimokuCloud()
    return _ichimoku
