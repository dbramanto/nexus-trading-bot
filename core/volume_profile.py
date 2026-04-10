"""
Volume Profile Module
======================

Analyzes horizontal volume distribution to identify
key support/resistance zones and value areas.

Components:
- POC (Point of Control): Price with highest volume
- VAH (Value Area High): Upper value area boundary
- VAL (Value Area Low): Lower value area boundary
- Value Area: Range containing 70% of volume

Author: NEXUS Elite
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class VolumeProfile:
    """Volume Profile calculator for market structure analysis"""
    
    def __init__(
        self,
        num_bins: int = 24,
        value_area_pct: float = 0.70
    ):
        """
        Initialize Volume Profile
        
        Args:
            num_bins: Number of price bins (default 24)
            value_area_pct: Value area percentage (default 0.70 = 70%)
        """
        self.num_bins = num_bins
        self.value_area_pct = value_area_pct
        
        logger.info(
            f"VolumeProfile initialized "
            f"(bins={num_bins}, value_area={value_area_pct*100}%)"
        )
    
    def calculate(self, df: pd.DataFrame) -> Dict:
        """
        Calculate Volume Profile
        
        Args:
            df: DataFrame with OHLC + volume data
            
        Returns:
            dict: POC, VAH, VAL, and signals
        """
        try:
            if len(df) < 20:
                logger.warning(
                    f"Insufficient data for Volume Profile "
                    f"(need 20, got {len(df)})"
                )
                return self._empty_result()
            
            # Get price range
            price_min = df['low'].min()
            price_max = df['high'].max()
            
            # Create price bins
            price_bins = np.linspace(price_min, price_max, self.num_bins + 1)
            
            # Calculate volume at each price level
            volume_at_price = np.zeros(self.num_bins)
            
            for i in range(len(df)):
                candle_low = df['low'].iloc[i]
                candle_high = df['high'].iloc[i]
                candle_volume = df['volume'].iloc[i]
                
                # Distribute volume across bins this candle touched
                for j in range(self.num_bins):
                    bin_low = price_bins[j]
                    bin_high = price_bins[j + 1]
                    
                    # Check if candle overlaps with this bin
                    if candle_high >= bin_low and candle_low <= bin_high:
                        # Calculate overlap
                        overlap_low = max(candle_low, bin_low)
                        overlap_high = min(candle_high, bin_high)
                        overlap_pct = (overlap_high - overlap_low) / (candle_high - candle_low + 0.0001)
                        
                        # Add proportional volume
                        volume_at_price[j] += candle_volume * overlap_pct
            
            # Find POC (Point of Control) - price with highest volume
            poc_index = np.argmax(volume_at_price)
            poc_price = (price_bins[poc_index] + price_bins[poc_index + 1]) / 2
            
            # Calculate Value Area (70% of volume)
            total_volume = volume_at_price.sum()
            value_area_volume = total_volume * self.value_area_pct
            
            # Find value area boundaries starting from POC
            vah_index, val_index = self._find_value_area(
                volume_at_price, 
                poc_index, 
                value_area_volume
            )
            
            vah_price = price_bins[vah_index + 1]  # Upper boundary
            val_price = price_bins[val_index]      # Lower boundary
            
            # Current price
            current_price = df['close'].iloc[-1]
            
            # Price position
            if current_price > vah_price:
                position = 'above_va'
            elif current_price < val_price:
                position = 'below_va'
            elif abs(current_price - poc_price) < (vah_price - val_price) * 0.1:
                position = 'at_poc'
            else:
                position = 'in_va'
            
            # Profile shape analysis
            profile_shape = self._analyze_profile_shape(volume_at_price, poc_index)
            
            result = {
                'poc': poc_price,
                'vah': vah_price,
                'val': val_price,
                'value_area_width': vah_price - val_price,
                'current_price': current_price,
                'position': position,
                'profile_shape': profile_shape,
                'total_volume': total_volume,
                'poc_volume': volume_at_price[poc_index],
                'distance_to_poc': current_price - poc_price,
                'distance_to_poc_pct': ((current_price - poc_price) / poc_price) * 100
            }
            
            # Generate signal
            result['signal'] = self._generate_signal(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Volume Profile calculation error: {e}")
            return self._empty_result()
    
    def _find_value_area(
        self, 
        volume_at_price: np.ndarray, 
        poc_index: int, 
        target_volume: float
    ) -> Tuple[int, int]:
        """
        Find Value Area High and Low indices
        
        Args:
            volume_at_price: Volume distribution array
            poc_index: POC index
            target_volume: Target volume for value area
            
        Returns:
            tuple: (vah_index, val_index)
        """
        accumulated_volume = volume_at_price[poc_index]
        vah_index = poc_index
        val_index = poc_index
        
        # Expand from POC until we reach target volume
        while accumulated_volume < target_volume:
            # Check which direction has more volume
            volume_above = volume_at_price[vah_index + 1] if vah_index + 1 < len(volume_at_price) else 0
            volume_below = volume_at_price[val_index - 1] if val_index > 0 else 0
            
            if volume_above > volume_below:
                vah_index += 1
                accumulated_volume += volume_above
            elif volume_below > 0:
                val_index -= 1
                accumulated_volume += volume_below
            else:
                break
        
        return vah_index, val_index
    
    def _analyze_profile_shape(
        self, 
        volume_at_price: np.ndarray, 
        poc_index: int
    ) -> str:
        """
        Analyze volume profile shape
        
        Returns:
            'normal', 'p_shape', 'b_shape', or 'double'
        """
        total_bins = len(volume_at_price)
        
        # P-shape: POC in upper third
        if poc_index > total_bins * 0.66:
            return 'p_shape'  # Bearish distribution
        
        # b-shape: POC in lower third
        elif poc_index < total_bins * 0.33:
            return 'b_shape'  # Bullish distribution
        
        # Check for double distribution (two peaks)
        else:
            # Simple peak detection
            peaks = []
            for i in range(1, len(volume_at_price) - 1):
                if (volume_at_price[i] > volume_at_price[i-1] and 
                    volume_at_price[i] > volume_at_price[i+1] and
                    volume_at_price[i] > volume_at_price.mean()):
                    peaks.append(i)
            
            if len(peaks) >= 2:
                return 'double'
            else:
                return 'normal'  # Balanced distribution
    
    def _generate_signal(self, data: Dict) -> Dict:
        """
        Generate trading signal from Volume Profile
        
        Returns:
            dict: strength, direction, components
        """
        strength = 0
        components = {}
        
        # Component 1: Position relative to Value Area (+3/-3)
        if data['position'] == 'above_va':
            strength += 3
            components['va_position'] = 'bullish_breakout'
        elif data['position'] == 'below_va':
            strength -= 3
            components['va_position'] = 'bearish_breakdown'
        elif data['position'] == 'at_poc':
            # Neutral, but note POC proximity
            components['va_position'] = 'at_poc'
        else:
            components['va_position'] = 'in_value_area'
        
        # Component 2: Profile shape (+2/-2)
        if data['profile_shape'] == 'b_shape':
            strength += 2
            components['profile'] = 'bullish_distribution'
        elif data['profile_shape'] == 'p_shape':
            strength -= 2
            components['profile'] = 'bearish_distribution'
        elif data['profile_shape'] == 'double':
            components['profile'] = 'balanced'
        
        # Component 3: Distance to POC (+1)
        if abs(data['distance_to_poc_pct']) < 1.0:
            strength += 1 if data['position'] == 'above_va' else -1
            components['poc_proximity'] = 'near'
        
        # Determine direction
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
        """Return empty result on error"""
        return {
            'poc': 0,
            'vah': 0,
            'val': 0,
            'value_area_width': 0,
            'current_price': 0,
            'position': 'unknown',
            'profile_shape': 'unknown',
            'total_volume': 0,
            'poc_volume': 0,
            'distance_to_poc': 0,
            'distance_to_poc_pct': 0,
            'signal': {
                'strength': 0,
                'direction': 'neutral',
                'components': {}
            }
        }


# Singleton
_volume_profile = None

def get_volume_profile() -> VolumeProfile:
    """Get singleton VolumeProfile instance"""
    global _volume_profile
    if _volume_profile is None:
        _volume_profile = VolumeProfile()
    return _volume_profile
