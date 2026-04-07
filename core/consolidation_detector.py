"""
NEXUS Bot - Consolidation Detector
Detects price consolidation ranges for breakout trading
"""

import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

# Setup logging
logger = logging.getLogger(__name__)


class ConsolidationDetector:
    """
    Detects consolidation ranges in price data
    Used to identify potential breakout setups
    """
    
    def __init__(
        self,
        atr_multiplier: float = 1.5,
        min_duration_candles: int = 16,
        atr_period: int = 14
    ):
        """
        Initialize consolidation detector
        
        Args:
            atr_multiplier: Maximum range size (ATR multiplier)
            min_duration_candles: Minimum candles in consolidation
            atr_period: ATR calculation period
        """
        self.atr_multiplier = atr_multiplier
        self.min_duration_candles = min_duration_candles
        self.atr_period = atr_period
        
        logger.info(
            f"ConsolidationDetector initialized "
            f"(ATR mult={atr_multiplier}, min_candles={min_duration_candles})"
        )
    
    def calculate_atr(self, candles_df: pd.DataFrame) -> pd.Series:
        """
        Calculate Average True Range
        
        Args:
            candles_df: DataFrame with OHLC data
            
        Returns:
            Series: ATR values
        """
        high = candles_df['high']
        low = candles_df['low']
        close = candles_df['close'].shift(1)
        
        # True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR = EMA of True Range
        atr = true_range.ewm(span=self.atr_period, adjust=False).mean()
        
        return atr
    
    def detect_consolidation(
        self,
        candles_df: pd.DataFrame
    ) -> Optional[Dict]:
        """
        Detect if price is currently in consolidation
        
        Args:
            candles_df: DataFrame with OHLC data (sorted oldest to newest)
            
        Returns:
            dict: Consolidation info or None if not consolidating
        """
        if len(candles_df) < self.min_duration_candles + self.atr_period:
            logger.debug("Not enough candles for consolidation detection")
            return None
        
        # Calculate ATR
        atr = self.calculate_atr(candles_df)
        current_atr = atr.iloc[-1]
        
        if pd.isna(current_atr) or current_atr == 0:
            logger.debug("Invalid ATR value")
            return None
        
        # Get recent candles for analysis
        recent_candles = candles_df.tail(self.min_duration_candles * 2)
        
        # Find high/low range
        range_high = recent_candles['high'].max()
        range_low = recent_candles['low'].min()
        range_size = range_high - range_low
        
        # Check if range is tight enough (< ATR multiplier)
        max_range = current_atr * self.atr_multiplier
        
        if range_size > max_range:
            logger.debug(
                f"Range too wide: {range_size:.2f} > {max_range:.2f} "
                f"(ATR: {current_atr:.2f})"
            )
            return None
        
        # Count candles within range
        candles_in_range = recent_candles[
            (recent_candles['high'] <= range_high) &
            (recent_candles['low'] >= range_low)
        ]
        
        duration = len(candles_in_range)
        
        if duration < self.min_duration_candles:
            logger.debug(f"Duration too short: {duration} < {self.min_duration_candles}")
            return None
        
        # Calculate consolidation quality (tighter = better)
        quality_score = self._calculate_quality_score(
            range_size=range_size,
            atr=current_atr,
            duration=duration
        )
        
        # Build consolidation data
        consolidation = {
            'is_consolidating': True,
            'range_high': range_high,
            'range_low': range_low,
            'range_size': range_size,
            'range_midpoint': (range_high + range_low) / 2,
            'atr': current_atr,
            'duration_candles': duration,
            'quality_score': quality_score,
            'max_range_allowed': max_range,
            'tightness_ratio': range_size / max_range  # Lower = tighter
        }
        
        logger.info(
            f"Consolidation detected: "
            f"Range ${range_low:.2f}-${range_high:.2f} "
            f"(${range_size:.2f}), Duration: {duration} candles, "
            f"Quality: {quality_score:.1f}"
        )
        
        return consolidation
    
    def _calculate_quality_score(
        self,
        range_size: float,
        atr: float,
        duration: int
    ) -> float:
        """
        Calculate consolidation quality score (0-100)
        
        Higher score = better consolidation
        
        Args:
            range_size: Range size in price units
            atr: Current ATR
            duration: Duration in candles
            
        Returns:
            float: Quality score (0-100)
        """
        # Tightness score (0-50 points)
        # Tighter range = higher score
        max_range = atr * self.atr_multiplier
        tightness_ratio = range_size / max_range
        tightness_score = (1 - tightness_ratio) * 50
        
        # Duration score (0-50 points)
        # Longer duration = higher score (up to 50 candles)
        max_duration_for_score = 50
        duration_ratio = min(duration / max_duration_for_score, 1.0)
        duration_score = duration_ratio * 50
        
        total_score = tightness_score + duration_score
        
        return round(total_score, 1)
    
    def get_support_resistance(
        self,
        candles_df: pd.DataFrame,
        consolidation: Dict
    ) -> Dict[str, float]:
        """
        Get support/resistance levels from consolidation
        
        Args:
            candles_df: DataFrame with OHLC data
            consolidation: Consolidation data from detect_consolidation
            
        Returns:
            dict: Support/resistance levels
        """
        range_high = consolidation['range_high']
        range_low = consolidation['range_low']
        range_size = range_high - range_low
        
        # Define levels
        levels = {
            'resistance': range_high,
            'support': range_low,
            'midpoint': (range_high + range_low) / 2,
            'upper_third': range_low + (range_size * 2/3),
            'lower_third': range_low + (range_size * 1/3)
        }
        
        return levels
    
    def is_near_boundary(
        self,
        current_price: float,
        consolidation: Dict,
        threshold_percent: float = 0.2
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if price is near consolidation boundary
        
        Args:
            current_price: Current price
            consolidation: Consolidation data
            threshold_percent: Distance threshold (% of range)
            
        Returns:
            tuple: (is_near, boundary_type)
                   boundary_type: 'upper', 'lower', or None
        """
        range_high = consolidation['range_high']
        range_low = consolidation['range_low']
        range_size = consolidation['range_size']
        
        threshold = range_size * (threshold_percent / 100)
        
        # Check upper boundary
        if abs(current_price - range_high) <= threshold:
            return True, 'upper'
        
        # Check lower boundary
        if abs(current_price - range_low) <= threshold:
            return True, 'lower'
        
        return False, None


# Convenience function
def get_consolidation_detector(
    atr_multiplier: float = 1.5,
    min_duration_candles: int = 16
) -> ConsolidationDetector:
    """
    Factory function to create ConsolidationDetector
    
    Args:
        atr_multiplier: Maximum range multiplier
        min_duration_candles: Minimum duration
        
    Returns:
        ConsolidationDetector instance
    """
    return ConsolidationDetector(atr_multiplier, min_duration_candles)


if __name__ == "__main__":
    """Test consolidation detector"""
    
    import os
    from datetime import datetime, timedelta
    from dotenv import load_dotenv
    from execution.binance_client import get_binance_client
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("Testing Consolidation Detector")
    print("=" * 70)
    
    # Load credentials
    load_dotenv()
    
    # Initialize Binance client
    print("\n[1] Initializing Binance client...")
    client = get_binance_client(testnet=False)
    print("✅ Client initialized")
    
    # Fetch BTC candles
    print("\n[2] Fetching BTC 15m candles (last 100)...")
    klines = client.get_klines('BTCUSDT', '15m', limit=100)
    
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
    print(f"   Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"   Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
    
    # Initialize detector
    print("\n[3] Initializing consolidation detector...")
    detector = get_consolidation_detector(
        atr_multiplier=1.5,
        min_duration_candles=16
    )
    print("✅ Detector initialized")
    
    # Detect consolidation
    print("\n[4] Detecting consolidation...")
    consolidation = detector.detect_consolidation(df)
    
    if consolidation:
        print("\n✅ CONSOLIDATION DETECTED!")
        print(f"\n   Range:")
        print(f"   High:     ${consolidation['range_high']:,.2f}")
        print(f"   Low:      ${consolidation['range_low']:,.2f}")
        print(f"   Size:     ${consolidation['range_size']:,.2f}")
        print(f"   Midpoint: ${consolidation['range_midpoint']:,.2f}")
        
        print(f"\n   Metrics:")
        print(f"   ATR:              ${consolidation['atr']:,.2f}")
        print(f"   Duration:         {consolidation['duration_candles']} candles")
        print(f"   Quality Score:    {consolidation['quality_score']:.1f}/100")
        print(f"   Tightness Ratio:  {consolidation['tightness_ratio']:.2%}")
        
        # Get support/resistance
        levels = detector.get_support_resistance(df, consolidation)
        print(f"\n   Support/Resistance Levels:")
        for level_name, level_price in levels.items():
            print(f"   {level_name:15s}: ${level_price:,.2f}")
        
        # Check if near boundary
        current_price = df['close'].iloc[-1]
        is_near, boundary = detector.is_near_boundary(current_price, consolidation)
        
        print(f"\n   Current Price: ${current_price:,.2f}")
        if is_near:
            print(f"   ⚠️  Near {boundary} boundary (potential breakout setup!)")
        else:
            print(f"   ℹ️  Not near boundaries")
        
    else:
        print("\n❌ NO CONSOLIDATION DETECTED")
        print("   Price is not in a tight consolidation range")
    
    print("\n" + "=" * 70)
    print("✅ Consolidation detector test complete!")
    print("=" * 70)