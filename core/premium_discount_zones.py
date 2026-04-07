"""
NEXUS Bot - Premium/Discount Zones
Identifies price zones using Fibonacci-based range analysis
Based on ICT/SMC concepts
"""

import logging
from typing import Dict, Optional
import pandas as pd

# Setup logging
logger = logging.getLogger(__name__)


class PremiumDiscountZones:
    """
    Calculates premium/discount zones from price ranges
    
    Zone Structure:
    - Premium: 61.8% - 100% of range (expensive)
    - Fair Value: 38.2% - 61.8% of range (neutral)
    - Discount: 0% - 38.2% of range (cheap)
    """
    
    def __init__(
        self,
        premium_threshold: float = 0.618,
        discount_threshold: float = 0.382
    ):
        """
        Initialize premium/discount zone calculator
        
        Args:
            premium_threshold: Upper boundary (default 61.8%)
            discount_threshold: Lower boundary (default 38.2%)
        """
        self.premium_threshold = premium_threshold
        self.discount_threshold = discount_threshold
        
        logger.info(
            f"PremiumDiscountZones initialized "
            f"(premium>={premium_threshold:.1%}, "
            f"discount<={discount_threshold:.1%})"
        )
    
    def calculate_zones(
        self,
        range_high: float,
        range_low: float
    ) -> Dict:
        """
        Calculate zone levels from range
        
        Args:
            range_high: Range high price
            range_low: Range low price
            
        Returns:
            dict: Zone levels and boundaries
        """
        range_size = range_high - range_low
        
        if range_size <= 0:
            logger.error("Invalid range: high must be > low")
            return {}
        
        # Calculate Fibonacci levels
        premium_level = range_low + (range_size * self.premium_threshold)
        discount_level = range_low + (range_size * self.discount_threshold)
        midpoint = range_low + (range_size * 0.5)
        
        # Additional Fibonacci levels (optional, for reference)
        fib_levels = {
            '0.0': range_low,
            '0.236': range_low + (range_size * 0.236),
            '0.382': discount_level,
            '0.5': midpoint,
            '0.618': premium_level,
            '0.786': range_low + (range_size * 0.786),
            '1.0': range_high
        }
        
        zones = {
            'range_high': range_high,
            'range_low': range_low,
            'range_size': range_size,
            'premium_threshold': premium_level,
            'discount_threshold': discount_level,
            'midpoint': midpoint,
            'fib_levels': fib_levels,
            'zones': {
                'premium': {
                    'lower': premium_level,
                    'upper': range_high,
                    'description': 'Premium Zone (Expensive)'
                },
                'fair_value': {
                    'lower': discount_level,
                    'upper': premium_level,
                    'description': 'Fair Value Zone (Neutral)'
                },
                'discount': {
                    'lower': range_low,
                    'upper': discount_level,
                    'description': 'Discount Zone (Cheap)'
                }
            }
        }
        
        return zones
    
    def get_current_zone(
        self,
        current_price: float,
        zones: Dict
    ) -> Dict:
        """
        Identify which zone current price is in
        
        Args:
            current_price: Current market price
            zones: Zone data from calculate_zones
            
        Returns:
            dict: Current zone info
        """
        range_high = zones['range_high']
        range_low = zones['range_low']
        range_size = zones['range_size']
        premium_threshold = zones['premium_threshold']
        discount_threshold = zones['discount_threshold']
        
        # Calculate price position in range (0-1)
        if range_size == 0:
            position_ratio = 0.5
        else:
            position_ratio = (current_price - range_low) / range_size
        
        # Determine zone
        if current_price >= premium_threshold:
            zone_name = 'PREMIUM'
            zone_data = zones['zones']['premium']
            bias = 'SELL'
            quality_score = self._calculate_zone_quality(
                position_ratio,
                zone_type='premium'
            )
        elif current_price <= discount_threshold:
            zone_name = 'DISCOUNT'
            zone_data = zones['zones']['discount']
            bias = 'BUY'
            quality_score = self._calculate_zone_quality(
                position_ratio,
                zone_type='discount'
            )
        else:
            zone_name = 'FAIR_VALUE'
            zone_data = zones['zones']['fair_value']
            bias = 'NEUTRAL'
            quality_score = self._calculate_zone_quality(
                position_ratio,
                zone_type='fair_value'
            )
        
        result = {
            'current_price': current_price,
            'zone_name': zone_name,
            'zone_boundaries': zone_data,
            'position_ratio': position_ratio,
            'position_percent': position_ratio * 100,
            'bias': bias,
            'quality_score': quality_score,
            'distance_from_midpoint': abs(current_price - zones['midpoint']),
            'distance_from_midpoint_percent': abs(
                (current_price - zones['midpoint']) / zones['midpoint'] * 100
            )
        }
        
        logger.info(
            f"Current zone: {zone_name} "
            f"(position: {position_ratio:.1%}, bias: {bias}, "
            f"quality: {quality_score:.1f})"
        )
        
        return result
    
    def _calculate_zone_quality(
        self,
        position_ratio: float,
        zone_type: str
    ) -> float:
        """
        Calculate quality score for current position in zone
        
        Args:
            position_ratio: Position in range (0-1)
            zone_type: 'premium', 'discount', or 'fair_value'
            
        Returns:
            float: Quality score (0-100)
        """
        if zone_type == 'PREMIUM' or zone_type == 'premium':
            # Higher in premium = better for sells
            # 100% = score 100, 61.8% = score 0
            if position_ratio >= self.premium_threshold:
                normalized = (position_ratio - self.premium_threshold) / (1.0 - self.premium_threshold)
                score = normalized * 100
            else:
                score = 0
                
        elif zone_type == 'DISCOUNT' or zone_type == 'discount':
            # Lower in discount = better for buys
            # 0% = score 100, 38.2% = score 0
            if position_ratio <= self.discount_threshold:
                normalized = 1.0 - (position_ratio / self.discount_threshold)
                score = normalized * 100
            else:
                score = 0
                
        else:  # fair_value
            # Fair value zone gets lower scores
            # Closer to midpoint = slightly better
            distance_from_mid = abs(position_ratio - 0.5)
            normalized = 1.0 - (distance_from_mid / 0.118)  # 0.118 = half of fair value zone width
            score = max(0, normalized * 30)  # Max 30 points for fair value
        
        return round(score, 1)
    
    def get_entry_recommendation(
        self,
        current_zone: Dict,
        direction: str
    ) -> Dict:
        """
        Get entry recommendation based on zone and direction
        
        Args:
            current_zone: Current zone info from get_current_zone
            direction: Intended direction ('LONG' or 'SHORT')
            
        Returns:
            dict: Recommendation with score
        """
        zone_name = current_zone['zone_name']
        zone_bias = current_zone['bias']
        quality_score = current_zone['quality_score']
        
        # Match direction with zone bias
        if direction == 'LONG':
            if zone_name == 'DISCOUNT':
                recommendation = 'EXCELLENT'
                score_bonus = quality_score
            elif zone_name == 'FAIR_VALUE':
                recommendation = 'ACCEPTABLE'
                score_bonus = quality_score * 0.5
            else:  # PREMIUM
                recommendation = 'POOR'
                score_bonus = 0
                
        else:  # SHORT
            if zone_name == 'PREMIUM':
                recommendation = 'EXCELLENT'
                score_bonus = quality_score
            elif zone_name == 'FAIR_VALUE':
                recommendation = 'ACCEPTABLE'
                score_bonus = quality_score * 0.5
            else:  # DISCOUNT
                recommendation = 'POOR'
                score_bonus = 0
        
        result = {
            'direction': direction,
            'current_zone': zone_name,
            'zone_bias': zone_bias,
            'recommendation': recommendation,
            'score_bonus': round(score_bonus, 1),
            'reason': self._get_recommendation_reason(
                direction,
                zone_name,
                recommendation
            )
        }
        
        return result
    
    def _get_recommendation_reason(
        self,
        direction: str,
        zone_name: str,
        recommendation: str
    ) -> str:
        """Get human-readable reason for recommendation"""
        if recommendation == 'EXCELLENT':
            if direction == 'LONG':
                return "Buying at discount - optimal entry"
            else:
                return "Selling at premium - optimal entry"
        elif recommendation == 'ACCEPTABLE':
            return "Fair value zone - neutral entry"
        else:
            if direction == 'LONG':
                return "Buying at premium - poor entry (expensive)"
            else:
                return "Selling at discount - poor entry (cheap)"


# Convenience function
def get_premium_discount_zones(
    premium_threshold: float = 0.618,
    discount_threshold: float = 0.382
) -> PremiumDiscountZones:
    """
    Factory function to create PremiumDiscountZones
    
    Args:
        premium_threshold: Premium zone threshold
        discount_threshold: Discount zone threshold
        
    Returns:
        PremiumDiscountZones instance
    """
    return PremiumDiscountZones(premium_threshold, discount_threshold)


if __name__ == "__main__":
    """Test premium/discount zones"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("Testing Premium/Discount Zones")
    print("=" * 70)
    
    # Initialize zone calculator
    print("\n[1] Initializing zone calculator...")
    zones_calc = get_premium_discount_zones()
    print("✅ Zone calculator initialized")
    
    # Create sample range (e.g., BTC $60K - $70K)
    print("\n[2] Creating sample range...")
    range_low = 60000.0
    range_high = 70000.0
    print(f"   Range: ${range_low:,.0f} - ${range_high:,.0f}")
    print(f"   Size: ${range_high - range_low:,.0f}")
    
    # Calculate zones
    print("\n[3] Calculating zone levels...")
    zones = zones_calc.calculate_zones(range_high, range_low)
    
    print("\n   ✅ Zone Levels:")
    print(f"   Premium Zone:   ${zones['premium_threshold']:,.2f} - ${range_high:,.2f}")
    print(f"   Fair Value:     ${zones['discount_threshold']:,.2f} - ${zones['premium_threshold']:,.2f}")
    print(f"   Discount Zone:  ${range_low:,.2f} - ${zones['discount_threshold']:,.2f}")
    print(f"   Midpoint:       ${zones['midpoint']:,.2f}")
    
    print("\n   📊 Fibonacci Levels:")
    for level, price in zones['fib_levels'].items():
        print(f"   {level:6s}: ${price:>10,.2f}")
    
    # Test different price positions
    print("\n[4] Testing different price positions...")
    
    test_prices = [
        (61000, "Just above low (DISCOUNT)"),
        (64000, "Mid-discount zone"),
        (65000, "Fair value zone"),
        (67000, "Just below premium"),
        (69000, "Deep in PREMIUM")
    ]
    
    print("\n   Price Position Analysis:")
    print("   " + "─" * 68)
    
    for price, description in test_prices:
        current_zone = zones_calc.get_current_zone(price, zones)
        
        print(f"\n   💰 ${price:,} - {description}")
        print(f"      Zone: {current_zone['zone_name']:12s} | "
              f"Position: {current_zone['position_percent']:>5.1f}% | "
              f"Bias: {current_zone['bias']:7s} | "
              f"Quality: {current_zone['quality_score']:>4.1f}/100")
        
        # Get recommendations for both directions
        long_rec = zones_calc.get_entry_recommendation(current_zone, 'LONG')
        short_rec = zones_calc.get_entry_recommendation(current_zone, 'SHORT')
        
        print(f"      LONG:  {long_rec['recommendation']:10s} (Bonus: +{long_rec['score_bonus']:>4.1f})")
        print(f"      SHORT: {short_rec['recommendation']:10s} (Bonus: +{short_rec['score_bonus']:>4.1f})")
    
    print("\n   " + "─" * 68)
    
    # Summary
    print("\n[5] Usage in Trading:")
    print("   ✅ BUY setups: Prefer DISCOUNT zone (0-38.2%)")
    print("   ✅ SELL setups: Prefer PREMIUM zone (61.8-100%)")
    print("   ⚠️  FAIR VALUE: Reduced scoring, wait for better zones")
    print("   ❌ Avoid: LONG in premium, SHORT in discount")
    
    print("\n" + "=" * 70)
    print("✅ Premium/Discount zones test complete!")
    print("=" * 70)