"""
NEXUS Bot - Trade Validator
Final validation layer before trade execution
Integrated with Daily Session Manager for UTC-based daily limits
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, time

# Setup logging
logger = logging.getLogger(__name__)


class TradeValidator:
    """
    Final trade validation before execution
    
    Performs multiple layers of checks:
    - Daily session limits (via DailySessionManager)
    - Position parameters validation
    - Risk management checks
    - Market condition checks
    - Strategy rule validation
    """
    
    def __init__(
        self,
        session_manager=None,  # Optional: DailySessionManager
        max_exposure_percent: float = 75.0,  # Updated for single position
        min_account_balance: float = 100.0,
        allowed_trading_hours: Optional[tuple] = None,
        min_signal_grade: str = 'WEAK'
    ):
        """
        Initialize trade validator
        
        Args:
            session_manager: DailySessionManager instance (optional)
            max_exposure_percent: Maximum account exposure (%)
            min_account_balance: Minimum account balance required
            allowed_trading_hours: Trading hours tuple (start, end) in UTC
            min_signal_grade: Minimum acceptable signal grade
        """
        self.session_manager = session_manager
        self.max_exposure_percent = max_exposure_percent
        self.min_account_balance = min_account_balance
        self.allowed_trading_hours = allowed_trading_hours
        self.min_signal_grade = min_signal_grade
        
        # Grade hierarchy
        self.grade_hierarchy = {
            'NO_TRADE': 0,
            'WEAK': 1,
            'VALID': 2,
            'PREMIUM': 3
        }
        
        if session_manager:
            logger.info(
                f"TradeValidator initialized "
                f"(with DailySessionManager, max_exposure={max_exposure_percent}%, "
                f"min_grade={min_signal_grade})"
            )
        else:
            logger.info(
                f"TradeValidator initialized "
                f"(max_exposure={max_exposure_percent}%, min_grade={min_signal_grade})"
            )
    
    def validate_trade(
        self,
        position: Dict,
        account_state: Dict
    ) -> Dict:
        """
        Complete trade validation
        
        Args:
            position: Position from PositionCalculator
            account_state: Current account state
            
        Returns:
            dict: Validation result
        """
        symbol = position.get('symbol', 'UNKNOWN')
        direction = position.get('direction', 'UNKNOWN')
        
        logger.info(f"Validating trade: {symbol} {direction}")
        
        # Run all validation layers
        validations = []
        
        # Layer 0: Daily Session Check (if session manager exists)
        if self.session_manager:
            session_check = self._validate_daily_session()
            validations.append(session_check)
            
            # If daily limit hit, stop immediately
            if not session_check['valid']:
                return {
                    'approved': False,
                    'reason': session_check['reason'],
                    'checks': [session_check]
                }
        
        # Layer 1: Position Parameters
        position_check = self._validate_position_parameters(position)
        validations.append(position_check)
        
        # Layer 2: Risk Management
        risk_check = self._validate_risk_management(position, account_state)
        validations.append(risk_check)
        
        # Layer 3: Market Conditions
        market_check = self._validate_market_conditions(position)
        validations.append(market_check)
        
        # Layer 4: Strategy Rules
        strategy_check = self._validate_strategy_rules(position, account_state)
        validations.append(strategy_check)
        
        # Compile results
        all_valid = all(v['valid'] for v in validations)
        
        if all_valid:
            result = {
                'approved': True,
                'reason': 'All validation checks passed',
                'checks': validations
            }
            logger.info(f"Trade APPROVED: {symbol} {direction}")
        else:
            # Find first failed check
            failed = next((v for v in validations if not v['valid']), None)
            result = {
                'approved': False,
                'reason': failed['reason'],
                'checks': validations
            }
            logger.warning(f"Trade REJECTED: {symbol} {direction} - {failed['reason']}")
        
        return result
    
    def _validate_daily_session(self) -> Dict:
        """
        Validate daily session limits via DailySessionManager
        
        Returns:
            dict: Validation result
        """
        can_trade, reason = self.session_manager.can_trade()
        
        if not can_trade:
            return {
                'layer': 'Daily Session',
                'valid': False,
                'reason': reason
            }
        
        return {
            'layer': 'Daily Session',
            'valid': True,
            'reason': 'Daily limits OK'
        }
    
    def _validate_position_parameters(self, position: Dict) -> Dict:
        """
        Validate position parameters
        
        Args:
            position: Position data
            
        Returns:
            dict: Validation result
        """
        # Check if position exists
        if not position.get('symbol'):
            return {
                'layer': 'Position Parameters',
                'valid': False,
                'reason': 'Invalid position data'
            }
        
        # Check entry price
        entry = position.get('entry_price')
        if not entry or entry <= 0:
            return {
                'layer': 'Position Parameters',
                'valid': False,
                'reason': 'Invalid entry price'
            }
        
        # Check stop loss
        sl = position.get('stop_loss')
        if not sl or not sl.get('price'):
            return {
                'layer': 'Position Parameters',
                'valid': False,
                'reason': 'Invalid stop loss'
            }
        
        # Check take profit
        tp = position.get('take_profit')
        if not tp or not tp.get('tp1'):
            return {
                'layer': 'Position Parameters',
                'valid': False,
                'reason': 'Invalid take profit'
            }
        
        # Check position size
        sizing = position.get('position_sizing')
        if not sizing or sizing.get('position_size_usdt', 0) <= 0:
            return {
                'layer': 'Position Parameters',
                'valid': False,
                'reason': 'Invalid position size'
            }
        
        # All position parameters valid
        return {
            'layer': 'Position Parameters',
            'valid': True,
            'reason': 'All position parameters valid'
        }
    
    def _validate_risk_management(
        self,
        position: Dict,
        account_state: Dict
    ) -> Dict:
        """
        Validate risk management rules
        
        Args:
            position: Position data
            account_state: Account state
            
        Returns:
            dict: Validation result
        """
        # Check account balance
        balance = account_state.get('balance', 0)
        if balance < self.min_account_balance:
            return {
                'layer': 'Risk Management',
                'valid': False,
                'reason': f'Account balance too low (${balance:.2f} < ${self.min_account_balance})'
            }
        
        # Note: Daily loss check is now handled by DailySessionManager
        # No need for duplicate daily_pnl check here
        
        # Check max exposure (single position mode - relaxed to 75%)
        current_exposure = account_state.get('total_exposure_usdt', 0)
        position_size = position['position_sizing']['position_size_usdt']
        new_exposure = current_exposure + position_size
        exposure_percent = (new_exposure / balance * 100) if balance > 0 else 0
        
        if exposure_percent > self.max_exposure_percent:
            return {
                'layer': 'Risk Management',
                'valid': False,
                'reason': f'Max exposure exceeded ({exposure_percent:.1f}% > {self.max_exposure_percent}%)'
            }
        
        # All risk checks passed
        return {
            'layer': 'Risk Management',
            'valid': True,
            'reason': 'All risk limits within acceptable range'
        }
    
    def _validate_market_conditions(self, position: Dict) -> Dict:
        """
        Validate market conditions
        
        Args:
            position: Position data
            
        Returns:
            dict: Validation result
        """
        # Check trading hours (if specified)
        if self.allowed_trading_hours:
            current_time = datetime.utcnow().time()
            start_hour, end_hour = self.allowed_trading_hours
            
            start_time = time(start_hour, 0)
            end_time = time(end_hour, 0)
            
            # Check if current time is within trading hours
            if not (start_time <= current_time <= end_time):
                return {
                    'layer': 'Market Conditions',
                    'valid': False,
                    'reason': f'Outside trading hours ({start_hour}:00-{end_hour}:00 UTC)'
                }
        
        # Check if symbol is valid
        symbol = position.get('symbol')
        if not symbol or not symbol.endswith('USDT'):
            return {
                'layer': 'Market Conditions',
                'valid': False,
                'reason': 'Invalid trading symbol'
            }
        
        # All market conditions acceptable
        return {
            'layer': 'Market Conditions',
            'valid': True,
            'reason': 'Market conditions acceptable'
        }
    
    def _validate_strategy_rules(
        self,
        position: Dict,
        account_state: Dict
    ) -> Dict:
        """
        Validate strategy-specific rules
        
        Args:
            position: Position data
            account_state: Account state
            
        Returns:
            dict: Validation result
        """
        # Check signal grade
        signal_grade = position.get('signal_grade', 'NO_TRADE')
        min_grade_value = self.grade_hierarchy.get(self.min_signal_grade, 0)
        current_grade_value = self.grade_hierarchy.get(signal_grade, 0)
        
        if current_grade_value < min_grade_value:
            return {
                'layer': 'Strategy Rules',
                'valid': False,
                'reason': f'Signal grade too low ({signal_grade} < {self.min_signal_grade})'
            }
        
        # Check for conflicting positions (single position mode)
        symbol = position.get('symbol')
        direction = position.get('direction')
        
        existing_positions = account_state.get('positions', [])
        for pos in existing_positions:
            if pos.get('symbol') == symbol:
                # Same symbol - check direction
                if pos.get('direction') != direction:
                    return {
                        'layer': 'Strategy Rules',
                        'valid': False,
                        'reason': f'Conflicting position exists ({symbol} {pos.get("direction")})'
                    }
        
        # All strategy rules satisfied
        return {
            'layer': 'Strategy Rules',
            'valid': True,
            'reason': 'Strategy rules satisfied'
        }
    
    def get_validation_summary(self, validation_result: Dict) -> str:
        """
        Get human-readable validation summary
        
        Args:
            validation_result: Result from validate_trade
            
        Returns:
            str: Summary text
        """
        if validation_result['approved']:
            summary = "✅ TRADE APPROVED\n"
        else:
            summary = "❌ TRADE REJECTED\n"
        
        summary += f"Reason: {validation_result['reason']}\n\n"
        summary += "Validation Checks:\n"
        
        for check in validation_result['checks']:
            status = "✅" if check['valid'] else "❌"
            summary += f"{status} {check['layer']}: {check['reason']}\n"
        
        return summary


# Convenience function
def get_trade_validator(
    session_manager=None,
    min_signal_grade: str = 'WEAK'
) -> TradeValidator:
    """
    Factory function to create TradeValidator
    
    Args:
        session_manager: DailySessionManager instance (optional)
        min_signal_grade: Minimum signal grade
        
    Returns:
        TradeValidator instance
    """
    return TradeValidator(
        session_manager=session_manager,
        min_signal_grade=min_signal_grade
    )


if __name__ == "__main__":
    """Test trade validator with DailySessionManager"""
    
    import os
    from dotenv import load_dotenv
    from execution.binance_client import get_binance_client
    from execution.daily_session_manager import get_daily_session_manager
    from core.indicator_manager import get_indicator_manager
    from core.scoring_engine import get_scoring_engine
    from core.signal_generator import get_signal_generator
    from core.position_calculator import get_position_calculator
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("Testing Trade Validator - WITH DAILY SESSION MANAGER")
    print("=" * 70)
    
    # Load credentials
    load_dotenv()
    
    # Initialize Daily Session Manager
    print("\n[1] Initializing Daily Session Manager...")
    session_manager = get_daily_session_manager(
        initial_balance=1000.0,
        daily_loss_limit=5.0
    )
    print("✅ Session manager initialized")
    
    # Test account state
    test_balance = 1000.0
    test_account_state = {
        'balance': test_balance,
        'open_positions': 0,
        'total_exposure_usdt': 0.0,
        'positions': []
    }
    
    # Initialize components
    print("\n[2] Initializing ALL components...")
    client = get_binance_client(testnet=False)
    manager = get_indicator_manager(client)
    scoring_engine = get_scoring_engine()
    signal_gen = get_signal_generator()
    position_calc = get_position_calculator(
        risk_per_trade=1.0,
        min_leverage=10.0,
        max_leverage=20.0,
        max_position_percent=25.0
    )
    validator = get_trade_validator(
        session_manager=session_manager,  # NEW!
        min_signal_grade='WEAK'
    )
    print("✅ All components initialized")
    
    # Get session summary
    summary = session_manager.get_session_summary()
    print(f"\n   Session Date: {summary['session_date']}")
    print(f"   Session Start: {summary['session_start']}")
    print(f"   Balance: ${summary['start_balance']:,.2f}")
    print(f"   Daily Limit: -{summary['daily_loss_limit']}%")
    
    # Run complete pipeline
    print("\n[3] Running complete trading pipeline...")
    
    # Analysis
    analysis = manager.analyze_symbol('BTCUSDT', primary_tf='15m')
    
    # Scoring
    long_score = scoring_engine.calculate_score(analysis, 'LONG')
    short_score = scoring_engine.calculate_score(analysis, 'SHORT')
    
    # Signal
    signal = signal_gen.generate_signal(long_score, short_score, analysis)
    
    # Position
    if signal['has_signal']:
        position = position_calc.calculate_position(signal, test_balance)
    else:
        # Create demo position
        demo_signal = {
            'has_signal': True,
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'entry_price': analysis['current_price'],
            'score': 75.0,
            'grade': 'VALID',
            'analysis': analysis
        }
        position = position_calc.calculate_position(demo_signal, test_balance)
    
    print("✅ Pipeline complete")
    
    # Validation
    print("\n[4] Validating trade...")
    validation = validator.validate_trade(position, test_account_state)
    
    print("\n" + "=" * 70)
    print(validator.get_validation_summary(validation))
    print("=" * 70)
    
    # Test daily limit scenario
    print("\n[5] Testing daily loss limit enforcement...")
    print("   Simulating losses to hit 5% limit...")
    
    session_manager.update_balance(980.0)  # -$20
    session_manager.record_trade()
    session_manager.update_balance(965.0)  # -$35
    session_manager.record_trade()
    session_manager.update_balance(945.0)  # -$55 (5.5% loss)
    session_manager.record_trade()
    
    summary = session_manager.get_session_summary()
    print(f"\n   Daily P&L: ${summary['daily_pnl']:,.2f} ({summary['daily_pnl_percent']:.2f}%)")
    print(f"   Suspended: {summary['is_suspended']}")
    
    # Try to validate trade with limit hit
    print("\n[6] Attempting validation with daily limit hit...")
    test_account_state['balance'] = 945.0
    validation2 = validator.validate_trade(position, test_account_state)
    
    print("\n" + "=" * 70)
    print(validator.get_validation_summary(validation2))
    print("=" * 70)
    
    print("\n" + "=" * 70)
    print("✅ Trade Validator with Daily Session Manager test complete!")
    print("=" * 70)