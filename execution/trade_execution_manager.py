"""
NEXUS Bot - Trade Execution Manager
Manages complete trading workflow from analysis to execution
SINGLE POSITION ONLY - Best scoring symbol only
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from execution.binance_client import BinanceClientWrapper
from execution.paper_trading_engine import PaperTradingEngine
from core.indicator_manager import IndicatorManager
from core.scoring_engine import ScoringEngine
from core.signal_generator import SignalGenerator
from core.position_calculator import PositionCalculator
from core.trade_validator import TradeValidator

# Setup logging
logger = logging.getLogger(__name__)


class TradeExecutionManager:
    """
    Manages complete trade execution workflow
    
    SINGLE POSITION STRATEGY:
    - Only 1 position at any time
    - Best scoring symbol only
    - Wait until position closes before next trade
    - No multi-layer / no averaging
    
    Workflow:
    1. Check if position open → skip if yes
    2. Analyze market (IndicatorManager)
    3. Calculate scores (ScoringEngine)
    4. Generate signal (SignalGenerator)
    5. Calculate position (PositionCalculator)
    6. Validate trade (TradeValidator)
    7. Execute trade (PaperTradingEngine)
    8. Monitor position
    """
    
    def __init__(
        self,
        binance_client: BinanceClientWrapper,
        paper_engine: PaperTradingEngine,
        indicator_manager: IndicatorManager,
        scoring_engine: ScoringEngine,
        signal_generator: SignalGenerator,
        position_calculator: PositionCalculator,
        trade_validator: TradeValidator
    ):
        """
        Initialize trade execution manager
        
        Args:
            binance_client: Binance client for market data
            paper_engine: Paper trading engine
            indicator_manager: Indicator analysis
            scoring_engine: Scoring system
            signal_generator: Signal generation
            position_calculator: Position sizing
            trade_validator: Trade validation
        """
        self.client = binance_client
        self.paper_engine = paper_engine
        self.indicator_manager = indicator_manager
        self.scoring_engine = scoring_engine
        self.signal_generator = signal_generator
        self.position_calculator = position_calculator
        self.trade_validator = trade_validator
        
        # Execution history
        self.execution_history: List[Dict] = []
        
        logger.info("TradeExecutionManager initialized (SINGLE POSITION MODE)")
    
    def execute_trading_cycle(
        self,
        symbol: str,
        timeframe: str = '15m'
    ) -> Dict:
        """
        Execute complete trading cycle for a symbol
        
        SINGLE POSITION CHECK:
        - If ANY position open → Skip trading
        - Only trade when NO positions open
        
        Workflow:
        0. Check position → 1. Analysis → 2. Scoring → 3. Signal → 
        4. Position → 5. Validation → 6. Execution
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe for analysis
            
        Returns:
            dict: Execution result
        """
        logger.info(f"Starting trading cycle: {symbol} {timeframe}")
        
        result = {
            'symbol': symbol,
            'timeframe': timeframe,
            'timestamp': datetime.now(),
            'steps': {}
        }
        
        try:
            # STEP 0: Check if position already open (SINGLE POSITION)
            account_state = self.paper_engine.get_account_state()
            
            if account_state['open_positions'] > 0:
                result['action'] = 'POSITION_ALREADY_OPEN'
                result['reason'] = f"Single position mode: {account_state['open_positions']} position already open"
                logger.info(f"⏸️  Position already open - skipping new trade")
                self._log_execution(result)
                return result
            
            # STEP 1: Market Analysis
            logger.info(f"[1/6] Analyzing {symbol}...")
            analysis = self.indicator_manager.analyze_symbol(symbol, timeframe)
            result['steps']['analysis'] = 'SUCCESS'
            
            # STEP 2: Scoring
            logger.info(f"[2/6] Calculating scores...")
            long_score = self.scoring_engine.calculate_score(analysis, 'LONG')
            short_score = self.scoring_engine.calculate_score(analysis, 'SHORT')
            result['steps']['scoring'] = 'SUCCESS'
            result['long_score'] = long_score['total_score']
            result['short_score'] = short_score['total_score']
            
            # STEP 3: Signal Generation
            logger.info(f"[3/6] Generating signal...")
            signal = self.signal_generator.generate_signal(
                long_score,
                short_score,
                analysis
            )
            result['steps']['signal'] = 'SUCCESS'
            result['has_signal'] = signal['has_signal']
            
            # No signal → Stop here
            if not signal['has_signal']:
                result['action'] = 'NO_TRADE'
                result['reason'] = signal['reasons'][0]
                logger.info(f"No signal: {result['reason']}")
                self._log_execution(result)
                return result
            
            result['direction'] = signal['direction']
            result['signal_score'] = signal['score']
            result['signal_grade'] = signal['grade']
            
            # STEP 4: Position Calculation
            logger.info(f"[4/6] Calculating position...")
            position = self.position_calculator.calculate_position(
                signal,
                account_state['balance']
            )
            result['steps']['position'] = 'SUCCESS'
            result['position_size'] = position['position_sizing']['position_size_usdt']
            result['leverage'] = position['position_sizing']['leverage']
            
            # STEP 5: Validation
            logger.info(f"[5/6] Validating trade...")
            validation = self.trade_validator.validate_trade(
                position,
                account_state
            )
            result['steps']['validation'] = 'SUCCESS'
            result['validated'] = validation['approved']
            
            # Not approved → Stop here
            if not validation['approved']:
                result['action'] = 'REJECTED'
                result['reason'] = validation['reason']
                logger.warning(f"Trade rejected: {result['reason']}")
                self._log_execution(result)
                return result
            
            # STEP 6: Execution
            logger.info(f"[6/6] Executing trade...")
            execution = self._execute_trade(position)
            result['steps']['execution'] = 'SUCCESS' if execution['success'] else 'FAILED'
            
            if execution['success']:
                result['action'] = 'EXECUTED'
                result['position_id'] = execution['position_id']
                logger.info(
                    f"✅ Trade executed: {signal['direction']} {symbol} "
                    f"@ ${position['entry_price']:,.2f} "
                    f"(Leverage: {result['leverage']}x)"
                )
            else:
                result['action'] = 'EXECUTION_FAILED'
                result['reason'] = execution['reason']
                logger.error(f"Execution failed: {result['reason']}")
            
        except Exception as e:
            logger.error(f"Trading cycle error: {e}", exc_info=True)
            result['action'] = 'ERROR'
            result['error'] = str(e)
        
        # Log execution
        self._log_execution(result)
        
        return result
    
    def _execute_trade(self, position: Dict) -> Dict:
        """
        Execute trade in paper trading engine
        
        Args:
            position: Position data from PositionCalculator
            
        Returns:
            dict: Execution result
        """
        try:
            # Open position (single position only)
            result = self.paper_engine.open_position(
                symbol=position['symbol'],
                direction=position['direction'],
                entry_price=position['entry_price'],
                position_size_usdt=position['position_sizing']['position_size_usdt'],
                leverage=position['position_sizing']['leverage'],
                stop_loss=position['stop_loss']['price'],
                take_profit=position['take_profit']
            )
            
            if result['success']:
                return {
                    'success': True,
                    'position_id': result['position']['position_id']
                }
            else:
                return {
                    'success': False,
                    'reason': result.get('reason', 'Unknown error')
                }
                
        except Exception as e:
            logger.error(f"Execution error: {e}")
            return {
                'success': False,
                'reason': str(e)
            }
    
    def update_positions(self, current_prices: Dict[str, float]):
        """
        Update open position with current prices
        
        Handles:
        - P&L updates
        - SL/TP checks
        - Trailing stop updates
        
        Args:
            current_prices: {symbol: current_price}
        """
        self.paper_engine.update_positions(current_prices)
    
    def get_open_position(self) -> Optional[Dict]:
        """
        Get the open position (single position mode)
        
        Returns:
            dict: Open position or None
        """
        state = self.paper_engine.get_account_state()
        positions = state['positions']
        
        if positions:
            return positions[0]  # Only 1 position possible
        return None
    
    def has_open_position(self) -> bool:
        """
        Check if there's an open position
        
        Returns:
            bool: True if position open
        """
        state = self.paper_engine.get_account_state()
        return state['open_positions'] > 0
    
    def close_position_manual(
        self,
        position_id: int,
        reason: str = 'MANUAL_CLOSE'
    ) -> Dict:
        """
        Manually close the position
        
        Args:
            position_id: Position ID
            reason: Close reason
            
        Returns:
            dict: Close result
        """
        return self.paper_engine.close_position(position_id, reason=reason)
    
    def _log_execution(self, result: Dict):
        """
        Log execution result
        
        Args:
            result: Execution result
        """
        self.execution_history.append(result)
        
        # Keep last 100 executions
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]
    
    def get_execution_summary(self) -> Dict:
        """
        Get execution statistics
        
        Returns:
            dict: Execution summary
        """
        if not self.execution_history:
            return {
                'total_cycles': 0,
                'signals_generated': 0,
                'trades_executed': 0,
                'trades_rejected': 0,
                'position_already_open': 0
            }
        
        total = len(self.execution_history)
        signals = sum(1 for r in self.execution_history if r.get('has_signal'))
        executed = sum(1 for r in self.execution_history if r.get('action') == 'EXECUTED')
        rejected = sum(1 for r in self.execution_history if r.get('action') == 'REJECTED')
        already_open = sum(1 for r in self.execution_history if r.get('action') == 'POSITION_ALREADY_OPEN')
        
        return {
            'total_cycles': total,
            'signals_generated': signals,
            'trades_executed': executed,
            'trades_rejected': rejected,
            'position_already_open': already_open,
            'signal_rate': round(signals / total * 100, 1) if total > 0 else 0,
            'execution_rate': round(executed / signals * 100, 1) if signals > 0 else 0
        }
    
    def get_account_summary(self) -> Dict:
        """
        Get account and trading summary
        
        Returns:
            dict: Complete summary
        """
        account = self.paper_engine.get_account_state()
        stats = self.paper_engine.get_statistics()
        execution = self.get_execution_summary()
        
        return {
            'account': account,
            'trading_stats': stats,
            'execution_stats': execution
        }


# Convenience function
def get_trade_execution_manager(
    binance_client: BinanceClientWrapper,
    paper_engine: PaperTradingEngine,
    indicator_manager: IndicatorManager,
    scoring_engine: ScoringEngine,
    signal_generator: SignalGenerator,
    position_calculator: PositionCalculator,
    trade_validator: TradeValidator
) -> TradeExecutionManager:
    """
    Factory function to create TradeExecutionManager
    
    Returns:
        TradeExecutionManager instance (SINGLE POSITION MODE)
    """
    return TradeExecutionManager(
        binance_client,
        paper_engine,
        indicator_manager,
        scoring_engine,
        signal_generator,
        position_calculator,
        trade_validator
    )


if __name__ == "__main__":
    """Test trade execution manager - SINGLE POSITION MODE"""
    
    import os
    from dotenv import load_dotenv
    from execution.binance_client import get_binance_client
    from execution.paper_trading_engine import get_paper_trading_engine
    from core.indicator_manager import get_indicator_manager
    from core.scoring_engine import get_scoring_engine
    from core.signal_generator import get_signal_generator
    from core.position_calculator import get_position_calculator
    from core.trade_validator import get_trade_validator
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("Testing Trade Execution Manager - SINGLE POSITION MODE")
    print("=" * 70)
    
    # Load credentials
    load_dotenv()
    
    # Initialize all components
    print("\n[1] Initializing all components...")
    
    client = get_binance_client(testnet=False)
    paper_engine = get_paper_trading_engine(initial_balance=1000.0)
    indicator_manager = get_indicator_manager(client)
    scoring_engine = get_scoring_engine()
    signal_generator = get_signal_generator()
    position_calculator = get_position_calculator(
        risk_per_trade=1.0,
        min_leverage=10.0,  # NEW: Leverage range
        max_leverage=20.0,
        max_position_percent=25.0
    )
    trade_validator = get_trade_validator()
    
    execution_manager = get_trade_execution_manager(
        client,
        paper_engine,
        indicator_manager,
        scoring_engine,
        signal_generator,
        position_calculator,
        trade_validator
    )
    
    print("✅ All components initialized")
    print("   Mode: SINGLE POSITION ONLY")
    print("   Leverage Range: 10-20x")
    
    # Run trading cycle
    print("\n[2] Running complete trading cycle for BTCUSDT...")
    print("   (Check Position → Analysis → Scoring → Signal → Position → Validation → Execution)")
    
    result = execution_manager.execute_trading_cycle('BTCUSDT', '15m')
    
    print("\n" + "=" * 70)
    print("TRADING CYCLE RESULT")
    print("=" * 70)
    
    print(f"\nSymbol: {result['symbol']}")
    print(f"Action: {result['action']}")
    
    if result['action'] == 'POSITION_ALREADY_OPEN':
        print(f"\n⏸️  POSITION ALREADY OPEN")
        print(f"   Reason: {result['reason']}")
        print(f"   Note: Single position mode - wait for current position to close")
    
    elif result.get('has_signal'):
        print(f"\n✅ SIGNAL GENERATED:")
        print(f"   Direction: {result['direction']}")
        print(f"   Score: {result['signal_score']:.1f}/100")
        print(f"   Grade: {result['signal_grade']}")
        print(f"   Long Score: {result['long_score']:.1f}")
        print(f"   Short Score: {result['short_score']:.1f}")
    else:
        print(f"\n❌ NO SIGNAL")
        print(f"   Reason: {result.get('reason', 'N/A')}")
    
    if result.get('validated') is not None:
        print(f"\nVALIDATION: {'✅ APPROVED' if result['validated'] else '❌ REJECTED'}")
        if not result['validated']:
            print(f"   Reason: {result.get('reason', 'N/A')}")
    
    if result['action'] == 'EXECUTED':
        print(f"\n🚀 TRADE EXECUTED!")
        print(f"   Position ID: {result['position_id']}")
        print(f"   Position Size: ${result['position_size']:,.2f}")
        print(f"   Leverage: {result['leverage']}x")
    
    # Show workflow steps
    if result.get('steps'):
        print(f"\nWORKFLOW STEPS:")
        for step, status in result['steps'].items():
            icon = "✅" if status == "SUCCESS" else "❌"
            print(f"   {icon} {step.title()}: {status}")
    
    # Show account state
    print("\n" + "=" * 70)
    print("ACCOUNT STATE")
    print("=" * 70)
    
    summary = execution_manager.get_account_summary()
    account = summary['account']
    
    print(f"\nBalance: ${account['balance']:,.2f}")
    print(f"Equity: ${account['equity']:,.2f}")
    print(f"Open Positions: {account['open_positions']} (max: 1)")
    print(f"Total Trades: {account['total_trades']}")
    
    # Show execution stats
    exec_stats = summary['execution_stats']
    print(f"\nEXECUTION STATISTICS:")
    print(f"   Total Cycles: {exec_stats['total_cycles']}")
    print(f"   Signals Generated: {exec_stats['signals_generated']}")
    print(f"   Trades Executed: {exec_stats['trades_executed']}")
    print(f"   Trades Rejected: {exec_stats['trades_rejected']}")
    print(f"   Position Already Open: {exec_stats['position_already_open']}")
    
    print("\n" + "=" * 70)
    print("✅ Trade Execution Manager test complete!")
    print("=" * 70)