"""
Liquidity Sweeps Module
========================

Detects liquidity grabs and stop hunts - classic SMC concept.

Liquidity pools exist at:
- Equal highs/lows (retail stops)
- Round numbers (psychological levels)
- Previous day high/low
- Swing highs/lows

Sweep = Price briefly breaks level, then reverses
(Smart money taking liquidity before true move)

Author: NEXUS Elite
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class LiquiditySweeps:
    """Liquidity Sweep detector for stop hunts"""
    
    def __init__(
        self,
        lookback: int = 20,
        sweep_threshold: float = 0.2
    ):
        """
        Initialize Liquidity Sweeps detector
        
        Args:
            lookback: Bars to look back for swing levels (default 20)
            sweep_threshold: Min % move beyond level to confirm sweep (default 0.2%)
        """
        self.lookback = lookback
        self.sweep_threshold = sweep_threshold
        
        logger.info(
            f"LiquiditySweeps initialized "
            f"(lookback={lookback}, threshold={sweep_threshold}%)"
        )
    
    def detect(self, df: pd.DataFrame) -> Dict:
        """
        Detect liquidity sweeps
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            dict: Sweep analysis and signals
        """
        try:
            if len(df) < self.lookback + 10:
                logger.warning(
                    f"Insufficient data for Liquidity Sweeps "
                    f"(need {self.lookback + 10}, got {len(df)})"
                )
                return self._empty_result()
            
            # Find swing highs and lows
            swing_highs = self._find_swing_highs(df)
            swing_lows = self._find_swing_lows(df)
            
            # Detect recent sweeps
            bullish_sweep = self._check_sweep(
                df, 
                swing_lows, 
                direction='bullish'
            )
            
            bearish_sweep = self._check_sweep(
                df,
                swing_highs,
                direction='bearish'
            )
            
            # Current price
            current_price = df['close'].iloc[-1]
            
            # Find nearest liquidity levels
            nearest_high = self._find_nearest_level(current_price, swing_highs, 'above')
            nearest_low = self._find_nearest_level(current_price, swing_lows, 'below')
            
            result = {
                'bullish_sweep_detected': bullish_sweep['detected'],
                'bullish_sweep_price': bullish_sweep['price'],
                'bearish_sweep_detected': bearish_sweep['detected'],
                'bearish_sweep_price': bearish_sweep['price'],
                'nearest_liquidity_high': nearest_high,
                'nearest_liquidity_low': nearest_low,
                'current_price': current_price,
                'swing_highs_count': len(swing_highs),
                'swing_lows_count': len(swing_lows)
            }
            
            # Generate signal
            result['signal'] = self._generate_signal(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Liquidity Sweeps detection error: {e}")
            return self._empty_result()
    
    def _find_swing_highs(self, df: pd.DataFrame) -> List[float]:
        """Find swing high levels"""
        highs = []
        
        for i in range(5, len(df) - 5):
            # Check if this is a swing high
            is_swing_high = True
            center_high = df['high'].iloc[i]
            
            # Check 5 bars before and after
            for j in range(i - 5, i + 6):
                if j != i and df['high'].iloc[j] >= center_high:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                highs.append(center_high)
        
        return highs[-10:] if len(highs) > 10 else highs  # Keep last 10
    
    def _find_swing_lows(self, df: pd.DataFrame) -> List[float]:
        """Find swing low levels"""
        lows = []
        
        for i in range(5, len(df) - 5):
            # Check if this is a swing low
            is_swing_low = True
            center_low = df['low'].iloc[i]
            
            # Check 5 bars before and after
            for j in range(i - 5, i + 6):
                if j != i and df['low'].iloc[j] <= center_low:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                lows.append(center_low)
        
        return lows[-10:] if len(lows) > 10 else lows  # Keep last 10
    
    def _check_sweep(
        self, 
        df: pd.DataFrame, 
        levels: List[float], 
        direction: str
    ) -> Dict:
        """
        Check for liquidity sweep
        
        Returns:
            dict: {'detected': bool, 'price': float}
        """
        if not levels or len(df) < 10:
            return {'detected': False, 'price': 0}
        
        # Check last 10 candles
        recent_bars = df.iloc[-10:]
        
        for level in levels:
            for i in range(len(recent_bars)):
                candle = recent_bars.iloc[i]
                
                if direction == 'bullish':
                    # Sweep below low, then close above
                    sweep_distance = (level - candle['low']) / level * 100
                    
                    if (candle['low'] < level and 
                        candle['close'] > level and
                        sweep_distance >= self.sweep_threshold):
                        return {'detected': True, 'price': level}
                
                else:  # bearish
                    # Sweep above high, then close below
                    sweep_distance = (candle['high'] - level) / level * 100
                    
                    if (candle['high'] > level and 
                        candle['close'] < level and
                        sweep_distance >= self.sweep_threshold):
                        return {'detected': True, 'price': level}
        
        return {'detected': False, 'price': 0}
    
    def _find_nearest_level(
        self, 
        current_price: float, 
        levels: List[float], 
        direction: str
    ) -> float:
        """Find nearest liquidity level"""
        if not levels:
            return 0
        
        if direction == 'above':
            above_levels = [l for l in levels if l > current_price]
            return min(above_levels) if above_levels else 0
        else:  # below
            below_levels = [l for l in levels if l < current_price]
            return max(below_levels) if below_levels else 0
    
    def _generate_signal(self, data: Dict) -> Dict:
        """Generate trading signal"""
        strength = 0
        components = {}
        
        # Component 1: Bullish sweep (+4)
        if data['bullish_sweep_detected']:
            strength += 4
            components['sweep'] = f"bullish_at_{data['bullish_sweep_price']:.2f}"
        
        # Component 2: Bearish sweep (-4)
        if data['bearish_sweep_detected']:
            strength -= 4
            components['sweep'] = f"bearish_at_{data['bearish_sweep_price']:.2f}"
        
        # Component 3: Near liquidity level (+2/-2)
        if data['nearest_liquidity_high'] > 0:
            distance_to_high = (data['nearest_liquidity_high'] - data['current_price']) / data['current_price'] * 100
            if distance_to_high < 1:  # Within 1%
                strength -= 2
                components['proximity'] = 'near_resistance'
        
        if data['nearest_liquidity_low'] > 0:
            distance_to_low = (data['current_price'] - data['nearest_liquidity_low']) / data['current_price'] * 100
            if distance_to_low < 1:  # Within 1%
                strength += 2
                components['proximity'] = 'near_support'
        
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
            'bullish_sweep_detected': False,
            'bullish_sweep_price': 0,
            'bearish_sweep_detected': False,
            'bearish_sweep_price': 0,
            'nearest_liquidity_high': 0,
            'nearest_liquidity_low': 0,
            'current_price': 0,
            'swing_highs_count': 0,
            'swing_lows_count': 0,
            'signal': {
                'strength': 0,
                'direction': 'neutral',
                'components': {}
            }
        }


# Singleton
_liq_sweeps = None

def get_liquidity_sweeps() -> LiquiditySweeps:
    """Get singleton LiquiditySweeps instance"""
    global _liq_sweeps
    if _liq_sweeps is None:
        _liq_sweeps = LiquiditySweeps()
    return _liq_sweeps
