"""
NEXUS Bot - Breakout Detector
Detects volume-confirmed breakouts from consolidation ranges
"""

import logging
from typing import Dict, Optional
import pandas as pd
import numpy as np

# Setup logging
logger = logging.getLogger(__name__)


class BreakoutDetector:
    """
    Detects breakouts from consolidation ranges
    Uses volume confirmation and close validation
    """
    
    def __init__(
        self,
        volume_multiplier: float = 2.0,
        require_close_confirmation: bool = True,
        volume_period: int = 20
    ):
        """
        Initialize breakout detector
        
        Args:
            volume_multiplier: Volume must be >= this * average
            require_close_confirmation: Require candle close outside range
            volume_period: Period for average volume calculation
        """
        self.volume_multiplier = volume_multiplier
        self.require_close_confirmation = require_close_confirmation
        self.volume_period = volume_period
        
        logger.info(
            f"BreakoutDetector initialized "
            f"(volume_mult={volume_multiplier}, "
            f"close_confirm={require_close_confirmation})"
        )
    
    def calculate_average_volume(self, candles_df: pd.DataFrame) -> float:
        """
        Calculate average volume over period
        
        Args:
            candles_df: DataFrame with volume data
            
        Returns:
            float: Average volume
        """
        if len(candles_df) < self.volume_period:
            return candles_df['volume'].mean()
        
        recent_volume = candles_df['volume'].tail(self.volume_period)
        return recent_volume.mean()
    
    def detect_breakout(
        self,
        candles_df: pd.DataFrame,
        consolidation: Dict
    ) -> Optional[Dict]:
        """
        Detect breakout from consolidation range
        
        Args:
            candles_df: DataFrame with OHLC + volume data
            consolidation: Consolidation data from ConsolidationDetector
            
        Returns:
            dict: Breakout info or None if no breakout
        """
        if len(candles_df) < 2:
            logger.debug("Not enough candles for breakout detection")
            return None
        
        # Get latest candle
        latest = candles_df.iloc[-1]
        current_close = latest['close']
        current_high = latest['high']
        current_low = latest['low']
        current_volume = latest['volume']
        
        # Get consolidation boundaries
        range_high = consolidation['range_high']
        range_low = consolidation['range_low']
        
        # Calculate average volume
        avg_volume = self.calculate_average_volume(candles_df)
        
        if avg_volume == 0:
            logger.debug("Invalid average volume")
            return None
        
        # Check for breakout
        breakout_direction = None
        breakout_type = None
        
        # Bullish breakout (upward)
        if current_high > range_high:
            if self.require_close_confirmation:
                # Must close above range
                if current_close > range_high:
                    breakout_direction = 'BULLISH'
                    breakout_type = 'CONFIRMED'
                else:
                    breakout_direction = 'BULLISH'
                    breakout_type = 'UNCONFIRMED'
            else:
                # Just need to touch above
                breakout_direction = 'BULLISH'
                breakout_type = 'TOUCH'
        
        # Bearish breakout (downward)
        elif current_low < range_low:
            if self.require_close_confirmation:
                # Must close below range
                if current_close < range_low:
                    breakout_direction = 'BEARISH'
                    breakout_type = 'CONFIRMED'
                else:
                    breakout_direction = 'BEARISH'
                    breakout_type = 'UNCONFIRMED'
            else:
                # Just need to touch below
                breakout_direction = 'BEARISH'
                breakout_type = 'TOUCH'
        
        # No breakout
        if not breakout_direction:
            logger.debug("Price still within consolidation range")
            return None
        
        # Check volume confirmation
        volume_ratio = current_volume / avg_volume
        has_volume = volume_ratio >= self.volume_multiplier
        
        # Calculate breakout distance
        if breakout_direction == 'BULLISH':
            breakout_distance = current_close - range_high
            breakout_percent = (breakout_distance / range_high) * 100
        else:  # BEARISH
            breakout_distance = range_low - current_close
            breakout_percent = (breakout_distance / range_low) * 100
        
        # Calculate strength score (0-100)
        strength_score = self._calculate_strength_score(
            volume_ratio=volume_ratio,
            breakout_percent=abs(breakout_percent),
            is_confirmed=(breakout_type == 'CONFIRMED')
        )
        
        # Build breakout data
        breakout = {
            'is_breakout': True,
            'direction': breakout_direction,
            'type': breakout_type,
            'has_volume_confirmation': has_volume,
            'current_price': current_close,
            'range_high': range_high,
            'range_low': range_low,
            'breakout_distance': abs(breakout_distance),
            'breakout_percent': abs(breakout_percent),
            'current_volume': current_volume,
            'average_volume': avg_volume,
            'volume_ratio': volume_ratio,
            'strength_score': strength_score,
            'timestamp': latest.get('timestamp', pd.Timestamp.now())
        }
        
        logger.info(
            f"Breakout detected: {breakout_direction} {breakout_type} | "
            f"Volume: {volume_ratio:.2f}x | "
            f"Distance: {abs(breakout_percent):.2f}% | "
            f"Strength: {strength_score:.1f}"
        )
        
        return breakout
    
    def _calculate_strength_score(
        self,
        volume_ratio: float,
        breakout_percent: float,
        is_confirmed: bool
    ) -> float:
        """
        Calculate breakout strength score (0-100)
        
        Args:
            volume_ratio: Current volume / average volume
            breakout_percent: Distance from range (%)
            is_confirmed: Whether close confirms breakout
            
        Returns:
            float: Strength score (0-100)
        """
        # Volume score (0-50 points)
        # 2x volume = 25 points, 4x+ volume = 50 points
        max_volume_for_score = 4.0
        volume_score = min(volume_ratio / max_volume_for_score, 1.0) * 50
        
        # Distance score (0-30 points)
        # 0.5% = 15 points, 1.0%+ = 30 points
        max_distance_for_score = 1.0
        distance_score = min(breakout_percent / max_distance_for_score, 1.0) * 30
        
        # Confirmation bonus (0-20 points)
        confirmation_score = 20 if is_confirmed else 0
        
        total_score = volume_score + distance_score + confirmation_score
        
        return round(total_score, 1)
    
    def is_valid_breakout(self, breakout: Dict) -> bool:
        """
        Check if breakout meets validity criteria
        
        Args:
            breakout: Breakout data from detect_breakout
            
        Returns:
            bool: True if valid breakout
        """
        # Must be confirmed (close outside range)
        if breakout['type'] != 'CONFIRMED':
            return False
        
        # Must have volume confirmation
        if not breakout['has_volume_confirmation']:
            return False
        
        # Must have minimum strength
        if breakout['strength_score'] < 50:
            return False
        
        return True


# Convenience function
def get_breakout_detector(
    volume_multiplier: float = 2.0,
    require_close_confirmation: bool = True
) -> BreakoutDetector:
    """
    Factory function to create BreakoutDetector
    
    Args:
        volume_multiplier: Volume confirmation threshold
        require_close_confirmation: Require close outside range
        
    Returns:
        BreakoutDetector instance
    """
    return BreakoutDetector(volume_multiplier, require_close_confirmation)


if __name__ == "__main__":
    """Test breakout detector"""
    
    import os
    from datetime import datetime
    from dotenv import load_dotenv
    from execution.binance_client import get_binance_client
    from core.consolidation_detector import get_consolidation_detector
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("Testing Breakout Detector")
    print("=" * 70)
    
    # Load credentials
    load_dotenv()
    
    # Initialize Binance client
    print("\n[1] Initializing Binance client...")
    client = get_binance_client(testnet=False)
    print("✅ Client initialized")
    
    # Fetch ETH candles (try different coin)
    print("\n[2] Fetching ETH 15m candles (last 100)...")
    klines = client.get_klines('ETHUSDT', '15m', limit=100)
    
    # Convert to DataFrame
    candles_data = []
    for kline in klines:
        candles_data.append({
            'timestamp': datetime.fromtimestamp(kline[0] / 1000),
            'open': float(kline[1]),
            'high': float(kline[2]),
            'low': float(kline[3]),
            'close': float(kline[4]),
            'volume': float(kline[5])
        })
    
    df = pd.DataFrame(candles_data)
    print(f"✅ Fetched {len(df)} candles")
    print(f"   Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
    print(f"   Latest close: ${df['close'].iloc[-1]:.2f}")
    
    # Initialize detectors
    print("\n[3] Initializing detectors...")
    consol_detector = get_consolidation_detector()
    breakout_detector = get_breakout_detector()
    print("✅ Detectors initialized")
    
    # Check for consolidation first
    print("\n[4] Checking for consolidation...")
    consolidation = consol_detector.detect_consolidation(df)
    
    if consolidation:
        print("✅ Consolidation found!")
        print(f"   Range: ${consolidation['range_low']:.2f} - ${consolidation['range_high']:.2f}")
        
        # Check for breakout
        print("\n[5] Checking for breakout...")
        breakout = breakout_detector.detect_breakout(df, consolidation)
        
        if breakout:
            print("\n🚀 BREAKOUT DETECTED!")
            print(f"\n   Direction: {breakout['direction']}")
            print(f"   Type: {breakout['type']}")
            print(f"   Current Price: ${breakout['current_price']:.2f}")
            print(f"   Breakout Distance: {breakout['breakout_percent']:.2f}%")
            print(f"\n   Volume:")
            print(f"   Current: {breakout['current_volume']:.2f}")
            print(f"   Average: {breakout['average_volume']:.2f}")
            print(f"   Ratio: {breakout['volume_ratio']:.2f}x")
            print(f"\n   Strength Score: {breakout['strength_score']:.1f}/100")
            print(f"   Volume Confirmed: {'✅' if breakout['has_volume_confirmation'] else '❌'}")
            
            # Check validity
            is_valid = breakout_detector.is_valid_breakout(breakout)
            print(f"\n   Valid Breakout: {'✅ YES' if is_valid else '❌ NO'}")
            
        else:
            print("\n❌ NO BREAKOUT")
            print("   Price still within consolidation range")
    
    else:
        print("❌ NO CONSOLIDATION")
        print("   Cannot detect breakout without consolidation range")
        print("\n   ℹ️  This is normal - most of the time price is NOT")
        print("       in consolidation. The bot will wait for setups!")
    
    print("\n" + "=" * 70)
    print("✅ Breakout detector test complete!")
    print("=" * 70)