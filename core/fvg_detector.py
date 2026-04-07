"""
NEXUS Bot - Fair Value Gap (FVG) Detector
Detects imbalances/inefficiencies in price action
Based on ICT/SMC concepts
"""

import logging
from typing import Dict, List, Optional
import pandas as pd

# Setup logging
logger = logging.getLogger(__name__)


class FVGDetector:
    """
    Detects Fair Value Gaps (FVG) in price data
    
    FVG = 3-candle pattern with gap/inefficiency
    - Bullish FVG: Gap up (candle[0].high < candle[2].low)
    - Bearish FVG: Gap down (candle[0].low > candle[2].high)
    
    These gaps often get filled (price returns to fill inefficiency)
    """
    
    def __init__(
        self,
        min_gap_percent: float = 0.1,
        max_lookback: int = 20
    ):
        """
        Initialize FVG detector
        
        Args:
            min_gap_percent: Minimum gap size (% of price)
            max_lookback: Maximum candles to look back
        """
        self.min_gap_percent = min_gap_percent
        self.max_lookback = max_lookback
        
        logger.info(
            f"FVGDetector initialized "
            f"(min_gap={min_gap_percent}%, max_lookback={max_lookback})"
        )
    
    def detect_fvgs(
        self,
        candles_df: pd.DataFrame,
        max_fvgs: int = 5
    ) -> List[Dict]:
        """
        Detect all FVGs in recent candles
        
        Args:
            candles_df: DataFrame with OHLC data
            max_fvgs: Maximum FVGs to return
            
        Returns:
            list: List of FVG dictionaries (most recent first)
        """
        if len(candles_df) < 3:
            logger.debug("Not enough candles for FVG detection")
            return []
        
        fvgs = []
        
        # Look back through candles (need 3-candle patterns)
        lookback = min(self.max_lookback, len(candles_df) - 2)
        
        for i in range(len(candles_df) - 3, len(candles_df) - 3 - lookback, -1):
            if i < 0:
                break
            
            # Get 3-candle pattern
            candle_0 = candles_df.iloc[i]      # First candle
            candle_1 = candles_df.iloc[i + 1]  # Middle candle
            candle_2 = candles_df.iloc[i + 2]  # Third candle
            
            # Check for bullish FVG (gap up)
            bullish_fvg = self._detect_bullish_fvg(candle_0, candle_1, candle_2)
            if bullish_fvg:
                fvgs.append(bullish_fvg)
            
            # Check for bearish FVG (gap down)
            bearish_fvg = self._detect_bearish_fvg(candle_0, candle_1, candle_2)
            if bearish_fvg:
                fvgs.append(bearish_fvg)
            
            # Stop if we have enough
            if len(fvgs) >= max_fvgs:
                break
        
        if fvgs:
            logger.info(f"Detected {len(fvgs)} FVGs in recent {lookback} candles")
        
        return fvgs[:max_fvgs]
    
    def _detect_bullish_fvg(
        self,
        candle_0: pd.Series,
        candle_1: pd.Series,
        candle_2: pd.Series
    ) -> Optional[Dict]:
        """
        Detect bullish FVG (gap up)
        
        Pattern: candle_0.high < candle_2.low
        (Gap between first and third candle)
        
        Args:
            candle_0: First candle
            candle_1: Middle candle
            candle_2: Third candle
            
        Returns:
            dict: FVG data or None
        """
        # Check for gap
        if candle_0['high'] >= candle_2['low']:
            return None
        
        # Calculate gap size
        gap_low = candle_0['high']
        gap_high = candle_2['low']
        gap_size = gap_high - gap_low
        gap_percent = (gap_size / candle_1['close']) * 100
        
        # Check minimum gap size
        if gap_percent < self.min_gap_percent:
            return None
        
        fvg = {
            'type': 'BULLISH',
            'gap_low': gap_low,
            'gap_high': gap_high,
            'gap_size': gap_size,
            'gap_percent': gap_percent,
            'midpoint': (gap_low + gap_high) / 2,
            'candle_index': candle_1.name if hasattr(candle_1, 'name') else None,
            'timestamp': candle_1.get('timestamp'),
            'is_mitigated': False,
            'quality_score': self._calculate_fvg_quality(gap_percent, 'BULLISH')
        }
        
        logger.debug(
            f"Bullish FVG detected: ${gap_low:.2f}-${gap_high:.2f} "
            f"({gap_percent:.2f}%)"
        )
        
        return fvg
    
    def _detect_bearish_fvg(
        self,
        candle_0: pd.Series,
        candle_1: pd.Series,
        candle_2: pd.Series
    ) -> Optional[Dict]:
        """
        Detect bearish FVG (gap down)
        
        Pattern: candle_0.low > candle_2.high
        (Gap between first and third candle)
        
        Args:
            candle_0: First candle
            candle_1: Middle candle
            candle_2: Third candle
            
        Returns:
            dict: FVG data or None
        """
        # Check for gap
        if candle_0['low'] <= candle_2['high']:
            return None
        
        # Calculate gap size
        gap_high = candle_0['low']
        gap_low = candle_2['high']
        gap_size = gap_high - gap_low
        gap_percent = (gap_size / candle_1['close']) * 100
        
        # Check minimum gap size
        if gap_percent < self.min_gap_percent:
            return None
        
        fvg = {
            'type': 'BEARISH',
            'gap_low': gap_low,
            'gap_high': gap_high,
            'gap_size': gap_size,
            'gap_percent': gap_percent,
            'midpoint': (gap_low + gap_high) / 2,
            'candle_index': candle_1.name if hasattr(candle_1, 'name') else None,
            'timestamp': candle_1.get('timestamp'),
            'is_mitigated': False,
            'quality_score': self._calculate_fvg_quality(gap_percent, 'BEARISH')
        }
        
        logger.debug(
            f"Bearish FVG detected: ${gap_low:.2f}-${gap_high:.2f} "
            f"({gap_percent:.2f}%)"
        )
        
        return fvg
    
    def _calculate_fvg_quality(
        self,
        gap_percent: float,
        fvg_type: str
    ) -> float:
        """
        Calculate FVG quality score (0-100)
        
        Larger gaps = higher quality
        
        Args:
            gap_percent: Gap size as percent of price
            fvg_type: 'BULLISH' or 'BEARISH'
            
        Returns:
            float: Quality score (0-100)
        """
        # Score based on gap size
        # 0.1% = 20 points, 0.5%+ = 100 points
        max_gap_for_score = 0.5
        
        if gap_percent >= max_gap_for_score:
            score = 100
        else:
            score = (gap_percent / max_gap_for_score) * 100
        
        return round(score, 1)
    
    def check_fvg_mitigation(
        self,
        fvg: Dict,
        current_price: float
    ) -> bool:
        """
        Check if FVG has been filled/mitigated
        
        Args:
            fvg: FVG data
            current_price: Current market price
            
        Returns:
            bool: True if FVG filled
        """
        gap_low = fvg['gap_low']
        gap_high = fvg['gap_high']
        
        # Price entered the gap = mitigated
        if gap_low <= current_price <= gap_high:
            return True
        
        # For bullish FVG, price going back down into gap
        if fvg['type'] == 'BULLISH' and current_price <= gap_low:
            return True
        
        # For bearish FVG, price going back up into gap
        if fvg['type'] == 'BEARISH' and current_price >= gap_high:
            return True
        
        return False
    
    def get_nearest_fvg(
        self,
        fvgs: List[Dict],
        current_price: float,
        fvg_type: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get nearest FVG to current price
        
        Args:
            fvgs: List of FVGs
            current_price: Current price
            fvg_type: Filter by type ('BULLISH'/'BEARISH') or None
            
        Returns:
            dict: Nearest FVG or None
        """
        if not fvgs:
            return None
        
        # Filter by type if specified
        if fvg_type:
            fvgs = [fvg for fvg in fvgs if fvg['type'] == fvg_type]
        
        if not fvgs:
            return None
        
        # Find nearest by midpoint distance
        nearest = min(
            fvgs,
            key=lambda fvg: abs(fvg['midpoint'] - current_price)
        )
        
        return nearest


# Convenience function
def get_fvg_detector(
    min_gap_percent: float = 0.1,
    max_lookback: int = 20
) -> FVGDetector:
    """
    Factory function to create FVGDetector
    
    Args:
        min_gap_percent: Minimum gap size
        max_lookback: Lookback period
        
    Returns:
        FVGDetector instance
    """
    return FVGDetector(min_gap_percent, max_lookback)


if __name__ == "__main__":
    """Test FVG detector"""
    
    import os
    from datetime import datetime
    from dotenv import load_dotenv
    from execution.binance_client import get_binance_client
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("Testing FVG Detector")
    print("=" * 70)
    
    # Load credentials
    load_dotenv()
    
    # Initialize Binance client
    print("\n[1] Initializing Binance client...")
    client = get_binance_client(testnet=False)
    print("✅ Client initialized")
    
    # Fetch BTC candles
    print("\n[2] Fetching BTC 15m candles (last 50)...")
    klines = client.get_klines('BTCUSDT', '15m', limit=50)
    
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
    
    # Initialize detector
    print("\n[3] Initializing FVG detector...")
    detector = get_fvg_detector(min_gap_percent=0.05, max_lookback=20)
    print("✅ Detector initialized")
    
    # Detect FVGs
    print("\n[4] Detecting Fair Value Gaps...")
    fvgs = detector.detect_fvgs(df, max_fvgs=5)
    
    if fvgs:
        print(f"\n✅ FOUND {len(fvgs)} FVGs!")
        
        current_price = df['close'].iloc[-1]
        print(f"\n   Current Price: ${current_price:,.2f}")
        print("\n   " + "─" * 68)
        
        for i, fvg in enumerate(fvgs, 1):
            print(f"\n   FVG #{i} - {fvg['type']}")
            print(f"   Zone:       ${fvg['gap_low']:>10,.2f} - ${fvg['gap_high']:>10,.2f}")
            print(f"   Size:       ${fvg['gap_size']:>10,.2f} ({fvg['gap_percent']:.2f}%)")
            print(f"   Midpoint:   ${fvg['midpoint']:>10,.2f}")
            print(f"   Quality:    {fvg['quality_score']:>10.1f}/100")
            
            # Check mitigation
            is_mitigated = detector.check_fvg_mitigation(fvg, current_price)
            print(f"   Mitigated:  {'✅ YES' if is_mitigated else '❌ NO (still valid)'}")
            
            # Distance from current price
            distance = abs(fvg['midpoint'] - current_price)
            distance_percent = (distance / current_price) * 100
            print(f"   Distance:   ${distance:>10,.2f} ({distance_percent:.2f}%)")
        
        print("\n   " + "─" * 68)
        
        # Get nearest FVG
        nearest = detector.get_nearest_fvg(fvgs, current_price)
        if nearest:
            print(f"\n   🎯 Nearest FVG: {nearest['type']} at ${nearest['midpoint']:,.2f}")
        
    else:
        print("\n❌ NO FVGs DETECTED")
        print("   No significant gaps found in recent candles")
    
    print("\n" + "=" * 70)
    print("✅ FVG detector test complete!")
    print("=" * 70)