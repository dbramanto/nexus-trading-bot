"""
NEXUS Bot - Order Block Detector
Detects institutional order blocks in price action
Based on ICT/SMC concepts
"""

import logging
from typing import Dict, List, Optional
import pandas as pd

# Setup logging
logger = logging.getLogger(__name__)


class OrderBlockDetector:
    """
    Detects Order Blocks (OB) in price data
    
    Order Block = Last opposite candle before strong move
    - Bullish OB: Last down candle before bullish move
    - Bearish OB: Last up candle before bearish move
    
    These zones often act as support/resistance
    """
    
    def __init__(
        self,
        min_move_percent: float = 1.0,
        min_move_candles: int = 3,
        max_lookback: int = 20
    ):
        """
        Initialize order block detector
        
        Args:
            min_move_percent: Minimum move size (% of price)
            min_move_candles: Minimum candles in move
            max_lookback: Maximum candles to look back
        """
        self.min_move_percent = min_move_percent
        self.min_move_candles = min_move_candles
        self.max_lookback = max_lookback
        
        logger.info(
            f"OrderBlockDetector initialized "
            f"(min_move={min_move_percent}%, "
            f"min_candles={min_move_candles})"
        )
    
    def detect_order_blocks(
        self,
        candles_df: pd.DataFrame,
        max_obs: int = 5
    ) -> List[Dict]:
        """
        Detect all order blocks in recent candles
        
        Args:
            candles_df: DataFrame with OHLC data
            max_obs: Maximum order blocks to return
            
        Returns:
            list: List of order block dictionaries
        """
        if len(candles_df) < self.min_move_candles + 1:
            logger.debug("Not enough candles for OB detection")
            return []
        
        order_blocks = []
        
        # Look back through candles
        lookback = min(self.max_lookback, len(candles_df) - self.min_move_candles)
        
        for i in range(len(candles_df) - 1, len(candles_df) - 1 - lookback, -1):
            if i < self.min_move_candles:
                break
            
            # Check for bullish move (potential bullish OB)
            bullish_ob = self._detect_bullish_ob(candles_df, i)
            if bullish_ob:
                order_blocks.append(bullish_ob)
            
            # Check for bearish move (potential bearish OB)
            bearish_ob = self._detect_bearish_ob(candles_df, i)
            if bearish_ob:
                order_blocks.append(bearish_ob)
            
            # Stop if we have enough
            if len(order_blocks) >= max_obs:
                break
        
        if order_blocks:
            logger.info(f"Detected {len(order_blocks)} order blocks")
        
        return order_blocks[:max_obs]
    
    def _detect_bullish_ob(
        self,
        candles_df: pd.DataFrame,
        end_index: int
    ) -> Optional[Dict]:
        """
        Detect bullish order block
        
        Pattern: Down candle followed by strong bullish move
        
        Args:
            candles_df: DataFrame with OHLC data
            end_index: End of potential move
            
        Returns:
            dict: Order block data or None
        """
        # Need at least min_move_candles before this point
        if end_index < self.min_move_candles:
            return None
        
        # Get current candle (end of move)
        current = candles_df.iloc[end_index]
        
        # Look back for start of bullish move
        start_index = end_index - self.min_move_candles
        
        # Check if there's a bullish move
        move_start_low = candles_df.iloc[start_index:end_index]['low'].min()
        move_end_high = candles_df.iloc[start_index:end_index + 1]['high'].max()
        
        move_size = move_end_high - move_start_low
        move_percent = (move_size / move_start_low) * 100
        
        # Check minimum move size
        if move_percent < self.min_move_percent:
            return None
        
        # Find last down candle before move
        ob_candle = None
        ob_index = None
        
        for i in range(start_index - 1, max(0, start_index - 5), -1):
            candle = candles_df.iloc[i]
            # Down candle (bearish)
            if candle['close'] < candle['open']:
                ob_candle = candle
                ob_index = i
                break
        
        if ob_candle is None:
            return None
        
        # Order block zone = the down candle's range
        ob_high = ob_candle['high']
        ob_low = ob_candle['low']
        ob_size = ob_high - ob_low
        
        order_block = {
            'type': 'BULLISH',
            'zone_high': ob_high,
            'zone_low': ob_low,
            'zone_size': ob_size,
            'midpoint': (ob_high + ob_low) / 2,
            'candle_index': ob_index,
            'timestamp': ob_candle.get('timestamp'),
            'move_size': move_size,
            'move_percent': move_percent,
            'is_mitigated': False,
            'quality_score': self._calculate_ob_quality(move_percent, ob_size, move_start_low)
        }
        
        logger.debug(
            f"Bullish OB detected: ${ob_low:.2f}-${ob_high:.2f} "
            f"(move: {move_percent:.2f}%)"
        )
        
        return order_block
    
    def _detect_bearish_ob(
        self,
        candles_df: pd.DataFrame,
        end_index: int
    ) -> Optional[Dict]:
        """
        Detect bearish order block
        
        Pattern: Up candle followed by strong bearish move
        
        Args:
            candles_df: DataFrame with OHLC data
            end_index: End of potential move
            
        Returns:
            dict: Order block data or None
        """
        # Need at least min_move_candles before this point
        if end_index < self.min_move_candles:
            return None
        
        # Get current candle (end of move)
        current = candles_df.iloc[end_index]
        
        # Look back for start of bearish move
        start_index = end_index - self.min_move_candles
        
        # Check if there's a bearish move
        move_start_high = candles_df.iloc[start_index:end_index]['high'].max()
        move_end_low = candles_df.iloc[start_index:end_index + 1]['low'].min()
        
        move_size = move_start_high - move_end_low
        move_percent = (move_size / move_start_high) * 100
        
        # Check minimum move size
        if move_percent < self.min_move_percent:
            return None
        
        # Find last up candle before move
        ob_candle = None
        ob_index = None
        
        for i in range(start_index - 1, max(0, start_index - 5), -1):
            candle = candles_df.iloc[i]
            # Up candle (bullish)
            if candle['close'] > candle['open']:
                ob_candle = candle
                ob_index = i
                break
        
        if ob_candle is None:
            return None
        
        # Order block zone = the up candle's range
        ob_high = ob_candle['high']
        ob_low = ob_candle['low']
        ob_size = ob_high - ob_low
        
        order_block = {
            'type': 'BEARISH',
            'zone_high': ob_high,
            'zone_low': ob_low,
            'zone_size': ob_size,
            'midpoint': (ob_high + ob_low) / 2,
            'candle_index': ob_index,
            'timestamp': ob_candle.get('timestamp'),
            'move_size': move_size,
            'move_percent': move_percent,
            'is_mitigated': False,
            'quality_score': self._calculate_ob_quality(move_percent, ob_size, move_start_high)
        }
        
        logger.debug(
            f"Bearish OB detected: ${ob_low:.2f}-${ob_high:.2f} "
            f"(move: {move_percent:.2f}%)"
        )
        
        return order_block
    
    def _calculate_ob_quality(
        self,
        move_percent: float,
        ob_size: float,
        reference_price: float
    ) -> float:
        """
        Calculate order block quality score (0-100)
        
        Better quality = stronger move + tighter OB zone
        
        Args:
            move_percent: Size of move after OB
            ob_size: Size of OB zone
            reference_price: Price for normalization
            
        Returns:
            float: Quality score (0-100)
        """
        # Move strength score (0-60 points)
        # 1% = 20 points, 3%+ = 60 points
        max_move_for_score = 3.0
        move_score = min(move_percent / max_move_for_score, 1.0) * 60
        
        # Zone tightness score (0-40 points)
        # Smaller OB zone = better quality
        ob_percent = (ob_size / reference_price) * 100
        max_ob_size = 0.5  # 0.5% of price
        
        if ob_percent <= max_ob_size:
            tightness_score = (1 - (ob_percent / max_ob_size)) * 40
        else:
            tightness_score = 0
        
        total_score = move_score + tightness_score
        
        return round(total_score, 1)
    
    def check_ob_mitigation(
        self,
        ob: Dict,
        current_price: float
    ) -> bool:
        """
        Check if order block has been mitigated (tested/broken)
        
        Args:
            ob: Order block data
            current_price: Current market price
            
        Returns:
            bool: True if OB mitigated
        """
        zone_low = ob['zone_low']
        zone_high = ob['zone_high']
        
        # Price entered the OB zone = mitigated
        if zone_low <= current_price <= zone_high:
            return True
        
        # For bullish OB, price breaking below = mitigated
        if ob['type'] == 'BULLISH' and current_price < zone_low:
            return True
        
        # For bearish OB, price breaking above = mitigated
        if ob['type'] == 'BEARISH' and current_price > zone_high:
            return True
        
        return False
    
    def get_nearest_ob(
        self,
        obs: List[Dict],
        current_price: float,
        ob_type: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get nearest order block to current price
        
        Args:
            obs: List of order blocks
            current_price: Current price
            ob_type: Filter by type ('BULLISH'/'BEARISH') or None
            
        Returns:
            dict: Nearest OB or None
        """
        if not obs:
            return None
        
        # Filter by type if specified
        if ob_type:
            obs = [ob for ob in obs if ob['type'] == ob_type]
        
        if not obs:
            return None
        
        # Find nearest by midpoint distance
        nearest = min(
            obs,
            key=lambda ob: abs(ob['midpoint'] - current_price)
        )
        
        return nearest
    
    def get_valid_obs(
        self,
        obs: List[Dict],
        current_price: float
    ) -> List[Dict]:
        """
        Get only valid (non-mitigated) order blocks
        
        Args:
            obs: List of order blocks
            current_price: Current price
            
        Returns:
            list: Valid order blocks only
        """
        valid = []
        
        for ob in obs:
            if not self.check_ob_mitigation(ob, current_price):
                valid.append(ob)
        
        return valid


# Convenience function
def get_orderblock_detector(
    min_move_percent: float = 1.0,
    min_move_candles: int = 3
) -> OrderBlockDetector:
    """
    Factory function to create OrderBlockDetector
    
    Args:
        min_move_percent: Minimum move size
        min_move_candles: Minimum move duration
        
    Returns:
        OrderBlockDetector instance
    """
    return OrderBlockDetector(min_move_percent, min_move_candles)


if __name__ == "__main__":
    """Test order block detector"""
    
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
    print("Testing Order Block Detector")
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
    print("\n[3] Initializing order block detector...")
    detector = get_orderblock_detector(min_move_percent=0.8, min_move_candles=3)
    print("✅ Detector initialized")
    
    # Detect order blocks
    print("\n[4] Detecting order blocks...")
    obs = detector.detect_order_blocks(df, max_obs=5)
    
    if obs:
        print(f"\n✅ FOUND {len(obs)} ORDER BLOCKS!")
        
        current_price = df['close'].iloc[-1]
        print(f"\n   Current Price: ${current_price:,.2f}")
        print("\n   " + "─" * 68)
        
        for i, ob in enumerate(obs, 1):
            print(f"\n   OB #{i} - {ob['type']}")
            print(f"   Zone:       ${ob['zone_low']:>10,.2f} - ${ob['zone_high']:>10,.2f}")
            print(f"   Size:       ${ob['zone_size']:>10,.2f}")
            print(f"   Midpoint:   ${ob['midpoint']:>10,.2f}")
            print(f"   Move:       {ob['move_percent']:>10.2f}% (${ob['move_size']:,.2f})")
            print(f"   Quality:    {ob['quality_score']:>10.1f}/100")
            
            # Check mitigation
            is_mitigated = detector.check_ob_mitigation(ob, current_price)
            print(f"   Mitigated:  {'✅ YES (tested)' if is_mitigated else '❌ NO (still valid)'}")
            
            # Distance from current price
            distance = abs(ob['midpoint'] - current_price)
            distance_percent = (distance / current_price) * 100
            print(f"   Distance:   ${distance:>10,.2f} ({distance_percent:.2f}%)")
        
        print("\n   " + "─" * 68)
        
        # Get valid (non-mitigated) OBs
        valid_obs = detector.get_valid_obs(obs, current_price)
        print(f"\n   📊 Valid (untested) OBs: {len(valid_obs)}/{len(obs)}")
        
        # Get nearest OB
        nearest = detector.get_nearest_ob(obs, current_price)
        if nearest:
            print(f"   🎯 Nearest OB: {nearest['type']} at ${nearest['midpoint']:,.2f}")
        
    else:
        print("\n❌ NO ORDER BLOCKS DETECTED")
        print("   No significant moves with clear OBs found")
    
    print("\n" + "=" * 70)
    print("✅ Order block detector test complete!")
    print("=" * 70)