"""
NEXUS Bot - Position Calculator
Calculates position sizing, SL, TP, and risk parameters
"""

import logging
from typing import Dict, List, Optional, Tuple

# Setup logging
logger = logging.getLogger(__name__)


class PositionCalculator:
    """
    Calculates trading position parameters
    
    - Stop Loss (structure-based or ATR-based)
    - Take Profit (multi-level targets)
    - Position sizing (risk-based)
    - Risk:Reward ratios
    """
    
    def __init__(
        self,
        risk_per_trade_percent: float = 1.0,
        min_leverage: float = 10.0,
        max_leverage: float = 20.0,
        min_risk_reward: float = 1.5,
        max_position_percent: float = 25.0,
        atr_sl_multiplier: float = 1.5,
        use_multi_tp: bool = True
    ):
        """
        Initialize position calculator
        
        Args:
            risk_per_trade_percent: Risk per trade (%)
            min_leverage: Minimum leverage (default: 10x)
            max_leverage: Maximum leverage (default: 20x)
            min_risk_reward: Minimum R:R ratio
            max_position_percent: Max position size (% of balance)
            atr_sl_multiplier: ATR multiplier for SL (default: 1.5)
            use_multi_tp: Use multiple TP levels (default: True)
        """
        self.risk_per_trade_percent = risk_per_trade_percent
        self.min_leverage = min_leverage
        self.max_leverage = max_leverage
        self.min_risk_reward = min_risk_reward
        self.max_position_percent = max_position_percent
        self.atr_sl_multiplier = atr_sl_multiplier
        self.use_multi_tp = use_multi_tp
        
        logger.info(
            f"PositionCalculator initialized "
            f"(risk={risk_per_trade_percent}%, leverage={min_leverage}-{max_leverage}x, "
            f"max_position={max_position_percent}%, min_RR={min_risk_reward})"
        )
    
    def calculate_position(
        self,
        signal: Dict,
        account_balance: float
    ) -> Dict:
        """
        Calculate complete position parameters
        
        Args:
            signal: Signal from SignalGenerator
            account_balance: Current account balance (USDT)
            
        Returns:
            dict: Complete position parameters
        """
        if not signal['has_signal']:
            logger.warning("Cannot calculate position: No signal")
            return self._empty_position()
        
        analysis = signal['analysis']
        direction = signal['direction']
        entry_price = signal['entry_price']
        
        logger.info(
            f"Calculating position for {signal['symbol']} {direction} @ ${entry_price:,.2f}"
        )
        
        # 1. Calculate Stop Loss
        sl_data = self._calculate_stop_loss(
            direction=direction,
            entry_price=entry_price,
            analysis=analysis
        )
        
        # 2. Calculate Take Profit levels
        tp_data = self._calculate_take_profit(
            direction=direction,
            entry_price=entry_price,
            sl_price=sl_data['price'],
            analysis=analysis
        )
        
        # 3. Calculate position size
        size_data = self._calculate_position_size(
            entry_price=entry_price,
            sl_price=sl_data['price'],
            account_balance=account_balance
        )
        
        # 4. Calculate risk metrics
        risk_data = self._calculate_risk_metrics(
            entry_price=entry_price,
            sl_price=sl_data['price'],
            tp_data=tp_data,
            position_size=size_data['position_size_usdt']
        )
        
        position = {
            'symbol': signal['symbol'],
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': sl_data,
            'take_profit': tp_data,
            'position_sizing': size_data,
            'risk_metrics': risk_data,
            'signal_score': signal['score'],
            'signal_grade': signal['grade']
        }
        
        logger.info(
            f"Position calculated: Size=${size_data['position_size_usdt']:,.2f} "
            f"SL=${sl_data['price']:,.2f} ({sl_data['distance_percent']:.2f}%) "
            f"TP1=${tp_data['tp1']['price']:,.2f} RR={risk_data['rr_ratio_tp1']:.2f}"
        )
        
        return position
    
    def _calculate_stop_loss(
        self,
        direction: str,
        entry_price: float,
        analysis: Dict
    ) -> Dict:
        """
        Calculate stop loss price
        
        Priority:
        1. Consolidation range (best)
        2. FVG/Order Block levels
        3. ATR-based (fallback)
        
        Args:
            direction: Trade direction
            entry_price: Entry price
            analysis: Full analysis
            
        Returns:
            dict: SL data
        """
        # Method 1: Consolidation-based SL (preferred)
        consolidation = analysis.get('consolidation')
        if consolidation:
            if direction == 'LONG':
                # SL below consolidation range
                sl_price = consolidation['range_low'] * 0.998  # 0.2% below
                method = 'consolidation_range'
            else:
                # SL above consolidation range
                sl_price = consolidation['range_high'] * 1.002  # 0.2% above
                method = 'consolidation_range'
        
        # Method 2: FVG/OB-based SL
        elif analysis.get('fvgs') or analysis.get('order_blocks'):
            atr_value = analysis['indicators']['atr']['value']
            sl_distance = atr_value * self.atr_sl_multiplier
            
            if direction == 'LONG':
                sl_price = entry_price - sl_distance
            else:
                sl_price = entry_price + sl_distance
            
            method = 'structure_atr'
        
        # Method 3: Pure ATR-based (fallback)
        else:
            atr_value = analysis['indicators']['atr']['value']
            sl_distance = atr_value * self.atr_sl_multiplier
            
            if direction == 'LONG':
                sl_price = entry_price - sl_distance
            else:
                sl_price = entry_price + sl_distance
            
            method = 'atr_based'
        
        # Ensure minimum SL distance (0.3% of entry)
        min_sl_distance = entry_price * 0.003
        sl_distance = abs(entry_price - sl_price)
        
        if sl_distance < min_sl_distance:
            if direction == 'LONG':
                sl_price = entry_price - min_sl_distance
            else:
                sl_price = entry_price + min_sl_distance
            method += '_minimum_enforced'
        
        sl_distance = abs(entry_price - sl_price)
        sl_distance_percent = (sl_distance / entry_price) * 100
        
        return {
            'price': round(sl_price, 2),
            'distance': round(sl_distance, 2),
            'distance_percent': round(sl_distance_percent, 2),
            'method': method
        }
    
    def _calculate_take_profit(
        self,
        direction: str,
        entry_price: float,
        sl_price: float,
        analysis: Dict
    ) -> Dict:
        """
        Calculate take profit levels
        
        Multi-TP approach:
        - TP1: 1:1.5 RR (50% of position)
        - TP2: 1:2.5 RR (30% of position)
        - TP3: 1:4.0 RR (20% of position)
        
        Args:
            direction: Trade direction
            entry_price: Entry price
            sl_price: Stop loss price
            analysis: Full analysis
            
        Returns:
            dict: TP data
        """
        risk = abs(entry_price - sl_price)
        
        if self.use_multi_tp:
            # Multi-TP levels
            if direction == 'LONG':
                tp1_price = entry_price + (risk * 1.5)  # 1:1.5 RR
                tp2_price = entry_price + (risk * 2.5)  # 1:2.5 RR
                tp3_price = entry_price + (risk * 4.0)  # 1:4.0 RR
            else:
                tp1_price = entry_price - (risk * 1.5)
                tp2_price = entry_price - (risk * 2.5)
                tp3_price = entry_price - (risk * 4.0)
            
            return {
                'tp1': {
                    'price': round(tp1_price, 2),
                    'rr_ratio': 1.5,
                    'allocation': 50  # 50% of position
                },
                'tp2': {
                    'price': round(tp2_price, 2),
                    'rr_ratio': 2.5,
                    'allocation': 30  # 30% of position
                },
                'tp3': {
                    'price': round(tp3_price, 2),
                    'rr_ratio': 4.0,
                    'allocation': 20  # 20% of position
                },
                'method': 'multi_tp'
            }
        
        else:
            # Single TP
            if direction == 'LONG':
                tp_price = entry_price + (risk * 2.0)  # 1:2 RR
            else:
                tp_price = entry_price - (risk * 2.0)
            
            return {
                'tp1': {
                    'price': round(tp_price, 2),
                    'rr_ratio': 2.0,
                    'allocation': 100
                },
                'method': 'single_tp'
            }
    
    def _calculate_position_size(
        self,
        entry_price: float,
        sl_price: float,
        account_balance: float
    ) -> Dict:
        """
        Calculate position size based on risk with leverage range 10-20x
        
        Formula:
        Position Size = (Account × Risk%) / (Entry - SL)
        
        Args:
            entry_price: Entry price
            sl_price: Stop loss price
            account_balance: Account balance in USDT
            
        Returns:
            dict: Position sizing data
        """
        # Risk amount in USDT
        risk_amount = account_balance * (self.risk_per_trade_percent / 100)
        
        # SL distance
        sl_distance = abs(entry_price - sl_price)
        sl_distance_percent = (sl_distance / entry_price) * 100
        
        # Position size in quote currency (USDT)
        position_size_usdt = risk_amount / (sl_distance_percent / 100)
        
        # Calculate required leverage
        required_leverage = position_size_usdt / account_balance
        
        # Enforce leverage range: 10-20x
        leverage_adjusted = False
        
        if required_leverage < self.min_leverage:
            # Force to minimum leverage
            required_leverage = self.min_leverage
            position_size_usdt = account_balance * required_leverage
            leverage_adjusted = True
            logger.debug(f"Leverage increased to minimum: {required_leverage}x")
        
        elif required_leverage > self.max_leverage:
            # Cap at maximum leverage
            position_size_usdt = account_balance * self.max_leverage
            required_leverage = self.max_leverage
            leverage_adjusted = True
            logger.debug(f"Leverage capped at maximum: {required_leverage}x")
        
        # Apply max position size limit (25% cap for compounding)
        max_position_size = account_balance * (self.max_position_percent / 100)
        
        if position_size_usdt > max_position_size:
            logger.info(
                f"Position size capped: ${position_size_usdt:.2f} → ${max_position_size:.2f} "
                f"({self.max_position_percent}% of balance)"
            )
            position_size_usdt = max_position_size
            # Recalculate leverage with capped size
            required_leverage = position_size_usdt / account_balance
            leverage_adjusted = True
        
        # Position size in base currency (coins)
        position_size_coins = position_size_usdt / entry_price
        
        return {
            'position_size_usdt': round(position_size_usdt, 2),
            'position_size_coins': round(position_size_coins, 6),
            'risk_amount_usdt': round(risk_amount, 2),
            'risk_percent': self.risk_per_trade_percent,
            'leverage': round(required_leverage, 1),
            'leverage_adjusted': leverage_adjusted,
            'min_leverage': self.min_leverage,
            'max_leverage': self.max_leverage
        }
    
    def _calculate_risk_metrics(
        self,
        entry_price: float,
        sl_price: float,
        tp_data: Dict,
        position_size: float
    ) -> Dict:
        """
        Calculate risk/reward metrics
        
        Args:
            entry_price: Entry price
            sl_price: Stop loss price
            tp_data: Take profit data
            position_size: Position size in USDT
            
        Returns:
            dict: Risk metrics
        """
        risk = abs(entry_price - sl_price)
        
        # Calculate RR ratios for each TP
        tp1_reward = abs(tp_data['tp1']['price'] - entry_price)
        rr_ratio_tp1 = tp1_reward / risk
        
        if 'tp2' in tp_data:
            tp2_reward = abs(tp_data['tp2']['price'] - entry_price)
            rr_ratio_tp2 = tp2_reward / risk
        else:
            rr_ratio_tp2 = None
        
        if 'tp3' in tp_data:
            tp3_reward = abs(tp_data['tp3']['price'] - entry_price)
            rr_ratio_tp3 = tp3_reward / risk
        else:
            rr_ratio_tp3 = None
        
        # Potential profit/loss in USDT
        max_loss_usdt = (risk / entry_price) * position_size
        max_profit_tp1 = (tp1_reward / entry_price) * position_size
        
        return {
            'rr_ratio_tp1': round(rr_ratio_tp1, 2),
            'rr_ratio_tp2': round(rr_ratio_tp2, 2) if rr_ratio_tp2 else None,
            'rr_ratio_tp3': round(rr_ratio_tp3, 2) if rr_ratio_tp3 else None,
            'max_loss_usdt': round(max_loss_usdt, 2),
            'max_profit_tp1_usdt': round(max_profit_tp1, 2),
            'risk_amount': round(risk, 2),
            'risk_percent_of_entry': round((risk / entry_price) * 100, 2)
        }
    
    def _empty_position(self) -> Dict:
        """Return empty position structure"""
        return {
            'symbol': None,
            'direction': None,
            'entry_price': None,
            'stop_loss': None,
            'take_profit': None,
            'position_sizing': None,
            'risk_metrics': None
        }
    
    def validate_position(self, position: Dict) -> Dict:
        """
        Validate position parameters
        
        Args:
            position: Position from calculate_position
            
        Returns:
            dict: Validation result
        """
        if not position.get('symbol'):
            return {'valid': False, 'reason': 'No position data'}
        
        # Check minimum RR ratio
        rr_ratio = position['risk_metrics']['rr_ratio_tp1']
        if rr_ratio < self.min_risk_reward:
            return {
                'valid': False,
                'reason': f'RR ratio too low ({rr_ratio:.2f} < {self.min_risk_reward})'
            }
        
        # Check leverage range
        leverage = position['position_sizing']['leverage']
        if leverage > self.max_leverage:
            return {
                'valid': False,
                'reason': f'Leverage too high ({leverage:.1f}x > {self.max_leverage}x)'
            }
        
        if leverage < self.min_leverage:
            return {
                'valid': False,
                'reason': f'Leverage too low ({leverage:.1f}x < {self.min_leverage}x)'
            }
        
        # All checks passed
        return {'valid': True, 'reason': 'Position parameters validated'}


# Convenience function
def get_position_calculator(
    risk_per_trade: float = 1.0,
    min_leverage: float = 10.0,
    max_leverage: float = 20.0,
    max_position_percent: float = 25.0
) -> PositionCalculator:
    """
    Factory function to create PositionCalculator
    
    Args:
        risk_per_trade: Risk per trade (%)
        min_leverage: Minimum leverage
        max_leverage: Maximum leverage
        max_position_percent: Max position size (% of balance)
        
    Returns:
        PositionCalculator instance
    """
    return PositionCalculator(
        risk_per_trade_percent=risk_per_trade,
        min_leverage=min_leverage,
        max_leverage=max_leverage,
        max_position_percent=max_position_percent
    )


if __name__ == "__main__":
    """Test position calculator with leverage range"""
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("Testing Position Calculator - Leverage Range 10-20x")
    print("=" * 70)
    
    # Initialize
    position_calc = get_position_calculator(
        risk_per_trade=1.0,
        min_leverage=10.0,
        max_leverage=20.0,
        max_position_percent=25.0
    )
    
    print("\n✅ Position Calculator initialized")
    print(f"   Leverage Range: {position_calc.min_leverage}-{position_calc.max_leverage}x")
    print(f"   Max Position: {position_calc.max_position_percent}%")
    print(f"   Risk per Trade: {position_calc.risk_per_trade_percent}%")
    
    print("\n" + "=" * 70)
    print("✅ Position calculator leverage range test complete!")
    print("=" * 70)