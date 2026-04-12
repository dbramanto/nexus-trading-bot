"""
NEXUS Bot - Paper Trading Engine
Simulates live trading for testing without risk
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import json
from pathlib import Path

# Setup logging
logger = logging.getLogger(__name__)


class PaperTradingEngine:
    """
    Paper trading simulation engine
    
    Manages:
    - Virtual account balance
    - Position tracking
    - Order execution simulation
    - P&L calculation
    - Trade history
    """
    
    def __init__(
        self,
        initial_balance: float = 1000.0,
        leverage: float = 20.0,
        taker_fee: float = 0.0005,  # 0.05%
        slippage: float = 0.0002,   # 0.02%
        max_positions: int = 1,     # Max concurrent positions (1 for learning)
        data_dir: str = 'data/paper_trading'
    ):
        """
        Initialize paper trading engine
        
        Args:
            initial_balance: Starting balance (USDT)
            leverage: Maximum leverage
            taker_fee: Trading fee (decimal)
            slippage: Simulated slippage (decimal)
            data_dir: Directory for trade data
        """
        self.initial_balance = initial_balance
        self.max_leverage = leverage
        self.taker_fee = taker_fee
        self.slippage = slippage
        self.data_dir = Path(data_dir)
        
        # Account state
        self.balance = initial_balance
        self.equity = initial_balance
        self.margin_used = 0.0
        self.unrealized_pnl = 0.0
        self.realized_pnl = 0.0
        
        # Positions and trades
        self.open_positions: List[Dict] = []
        self.closed_trades: List[Dict] = []
        
        # Position ID counter
        self.position_id_counter = 1
        self.max_positions = max_positions
        
        # Create data directory
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"PaperTradingEngine initialized "
            f"(balance=${initial_balance:,.2f}, leverage={leverage}x)"
        )
    
    def get_account_state(self) -> Dict:
        """
        Get current account state
        
        Returns:
            dict: Account state
        """
        return {
            'balance': round(self.balance, 2),
            'equity': round(self.equity, 2),
            'margin_used': round(self.margin_used, 2),
            'margin_free': round(self.balance - self.margin_used, 2),
            'unrealized_pnl': round(self.unrealized_pnl, 2),
            'realized_pnl': round(self.realized_pnl, 2),
            'total_pnl': round(self.realized_pnl + self.unrealized_pnl, 2),
            'open_positions': len(self.open_positions),
            'total_trades': len(self.closed_trades),
            'positions': self.open_positions.copy()
        }
    
    def open_position(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        position_size_usdt: float,
        leverage: float,
        stop_loss: float,
        take_profit: Dict
    ) -> Dict:
        """
        Open a new position
        
        Args:
            symbol: Trading symbol
            direction: 'LONG' or 'SHORT'
            entry_price: Entry price
            position_size_usdt: Position size in USDT
            leverage: Position leverage
            stop_loss: Stop loss price
            take_profit: Take profit data
            
        Returns:
            dict: Position data
        """
        # Apply slippage to entry
        if direction == 'LONG':
            actual_entry = entry_price * (1 + self.slippage)
        else:
            actual_entry = entry_price * (1 - self.slippage)
        
        # Calculate fees
        fee = position_size_usdt * self.taker_fee
        
        # Check max positions limit
        current_positions = len(self.open_positions)
        if current_positions >= self.max_positions:
            logger.warning(
                f"Max positions ({self.max_positions}) reached. "
                f"Current: {current_positions}. Skipping {symbol} {direction}"
            )
            return {
                'success': False,
                'reason': 'Max positions reached'
            }

        # Calculate margin required
        margin_required = position_size_usdt / leverage
        
        # Check if sufficient margin
        if margin_required > (self.balance - self.margin_used):
            logger.warning(
                f"Insufficient margin: Need ${margin_required:.2f}, "
                f"Available ${self.balance - self.margin_used:.2f}"
            )
            return {
                'success': False,
                'reason': 'Insufficient margin'
            }
        
        # Calculate position size in coins
        position_size_coins = position_size_usdt / actual_entry
        
        # Create position
        position = {
            'position_id': self.position_id_counter,
            'symbol': symbol,
            'direction': direction,
            'entry_price': round(actual_entry, 2),
            'position_size_usdt': round(position_size_usdt, 2),
            'position_size_coins': round(position_size_coins, 6),
            'original_size_usdt': round(position_size_usdt, 2),
            'original_size_coins': round(position_size_coins, 6),
            'leverage': leverage,
            'margin_used': round(margin_required, 2),
            'stop_loss': round(stop_loss, 2),
            'initial_stop_loss': round(stop_loss, 2),
            'take_profit': take_profit,
            'entry_fee': round(fee, 2),
            'unrealized_pnl': 0.0,
            'opened_at': datetime.now(),
            'status': 'OPEN',
            'trailing_active': False,
            'tp1_filled': False,
            'tp2_filled': False,
            'tp3_filled': False,
            'highest_price': round(actual_entry, 2),
            'lowest_price': round(actual_entry, 2),
            'partial_closes': []
        }
        
        # Update account
        self.margin_used += margin_required
        self.balance -= fee  # Deduct entry fee
        
        # Add to positions
        self.open_positions.append(position)
        self.position_id_counter += 1
        
        logger.info(
            f"Position opened: {symbol} {direction} @ ${actual_entry:,.2f} "
            f"(Size: ${position_size_usdt:,.2f}, Margin: ${margin_required:.2f})"
        )
        
        return {
            'success': True,
            'position': position
        }
    
    def update_positions(self, current_prices: Dict[str, float]):
        """
        Update all open positions with current prices
        
        Args:
            current_prices: {symbol: current_price}
        """
        total_unrealized = 0.0
        
        for position in self.open_positions:
            symbol = position['symbol']
            current_price = current_prices.get(symbol)
            
            if not current_price:
                continue
            
            # Calculate unrealized P&L
            entry_price = position['entry_price']
            size_coins = position['position_size_coins']
            direction = position['direction']
            
            if direction == 'LONG':
                pnl = (current_price - entry_price) * size_coins
            else:
                pnl = (entry_price - current_price) * size_coins
            
            position['unrealized_pnl'] = round(pnl, 2)
            position['current_price'] = round(current_price, 2)
            total_unrealized += pnl
            
            # Check SL/TP
            self._check_stop_loss(position, current_price)
            self._check_take_profit(position, current_price)
        
        # Update account unrealized P&L
        self.unrealized_pnl = total_unrealized
        self.equity = self.balance + total_unrealized
    
    def _check_stop_loss(self, position: Dict, current_price: float):
        """Check if stop loss is hit"""
        direction = position['direction']
        sl_price = position['stop_loss']
        
        hit = False
        if direction == 'LONG' and current_price <= sl_price:
            hit = True
        elif direction == 'SHORT' and current_price >= sl_price:
            hit = True
        
        if hit:
            self.close_position(
                position['position_id'],
                exit_price=sl_price,
                reason='STOP_LOSS'
            )
    
    def _check_take_profit(self, position: Dict, current_price: float):
        """
        Check TP1 and manage trailing stop for remaining 60%
        
        NEW LOGIC:
        - TP1 (40% close)
        - Move SL to BE+ after TP1
        - Trail remaining 60% with 1.5x ATR distance
        
        Args:
            position: Position data
            current_price: Current market price
        """
        direction = position['direction']
        tp_data = position['take_profit']
        
        # Update highest/lowest for trailing
        if direction == 'LONG':
            position['highest_price'] = max(position.get('highest_price', current_price), current_price)
        else:
            position['lowest_price'] = min(position.get('lowest_price', current_price), current_price)
        
        # Check TP1 (40% allocation)
        if not position.get('tp1_filled', False):
            tp1_price = tp_data['tp1']['price']
            tp1_hit = False
            
            if direction == 'LONG' and current_price >= tp1_price:
                tp1_hit = True
            elif direction == 'SHORT' and current_price <= tp1_price:
                tp1_hit = True
            
            if tp1_hit:
                allocation = tp_data['tp1'].get('allocation', 40)
                result = self.close_partial_position(
                    position['position_id'],
                    percentage=allocation,
                    exit_price=tp1_price,
                    reason='TAKE_PROFIT_1'
                )
                
                if result.get('success'):
                    position['tp1_filled'] = True
                    
                    # Move SL to breakeven+ (Entry + 25% of risk)
                    if 'breakeven_plus' in tp_data:
                        be_plus_price = tp_data['breakeven_plus']['price']
                        position['stop_loss'] = be_plus_price
                        logger.info(f"SL moved to BE+ ${be_plus_price:,.2f}")
                    else:
                        # Fallback to exact BE
                        position['stop_loss'] = position['entry_price']
                        logger.info(f"SL moved to BE ${position['entry_price']:,.2f}")
                    
                    # Activate trailing stop for remaining 60%
                    position['trailing_active'] = True
                    if 'trailing' in tp_data:
                        position['trail_distance'] = tp_data['trailing']['distance']
                    
                    logger.info(
                        f"✅ TP1 HIT! {allocation}% closed @ ${tp1_price:,.2f}, "
                        f"SL → BE+ ${position['stop_loss']:,.2f}, "
                        f"trailing activated (60% remaining)"
                    )
                return
        
        # Apply trailing stop if active (after TP1)
        if position.get('trailing_active'):
            self._update_trailing_stop(position, current_price)

    def _update_trailing_stop(self, position: Dict, current_price: float):
        """
        Update trailing stop based on price movement
        
        Trails SL to lock in profits as price moves favorably
        
        Args:
            position: Position data
            current_price: Current market price
        """
        direction = position['direction']
        
        # Trail distance: 0.5% for crypto volatility
        # In production, use ATR from analysis for dynamic trailing
        trail_distance_percent = 0.005  # 0.5%
        
        if direction == 'LONG':
            # Trail below highest price reached
            highest = position['highest_price']
            trail_distance = highest * trail_distance_percent
            new_sl = highest - trail_distance
            
            # Only move SL up, never down
            if new_sl > position['stop_loss']:
                old_sl = position['stop_loss']
                position['stop_loss'] = round(new_sl, 2)
                
                logger.info(
                    f"🔼 Trail SL: ${old_sl:,.2f} → ${new_sl:,.2f} "
                    f"(High: ${highest:,.2f}, Current: ${current_price:,.2f})"
                )
        
        else:  # SHORT
            # Trail above lowest price reached
            lowest = position['lowest_price']
            trail_distance = lowest * trail_distance_percent
            new_sl = lowest + trail_distance
            
            # Only move SL down, never up
            if new_sl < position['stop_loss']:
                old_sl = position['stop_loss']
                position['stop_loss'] = round(new_sl, 2)
                
                logger.info(
                    f"🔽 Trail SL: ${old_sl:,.2f} → ${new_sl:,.2f} "
                    f"(Low: ${lowest:,.2f}, Current: ${current_price:,.2f})"
                )
    
    def close_position(
        self,
        position_id: int,
        exit_price: Optional[float] = None,
        reason: str = 'MANUAL'
    ) -> Dict:
        """
        Close a position
        
        Args:
            position_id: Position ID
            exit_price: Exit price (None = market)
            reason: Close reason
            
        Returns:
            dict: Result
        """
        # Find position
        position = next(
            (p for p in self.open_positions if p['position_id'] == position_id),
            None
        )
        
        if not position:
            return {'success': False, 'reason': 'Position not found'}
        
        # Use current price if not specified
        if exit_price is None:
            exit_price = position.get('current_price', position['entry_price'])
        
        # Apply slippage
        direction = position['direction']
        if direction == 'LONG':
            actual_exit = exit_price * (1 - self.slippage)
        else:
            actual_exit = exit_price * (1 + self.slippage)
        
        # Calculate P&L
        entry_price = position['entry_price']
        size_coins = position['position_size_coins']
        
        if direction == 'LONG':
            pnl = (actual_exit - entry_price) * size_coins
        else:
            pnl = (entry_price - actual_exit) * size_coins
        
        # Calculate exit fee
        position_value = size_coins * actual_exit
        exit_fee = position_value * self.taker_fee
        
        # Net P&L
        net_pnl = pnl - position['entry_fee'] - exit_fee
        
        # Update account
        self.margin_used -= position['margin_used']
        self.balance += net_pnl
        self.realized_pnl += net_pnl
        
        # Create closed trade record
        trade = {
            **position,
            'exit_price': round(actual_exit, 2),
            'exit_fee': round(exit_fee, 2),
            'gross_pnl': round(pnl, 2),
            'net_pnl': round(net_pnl, 2),
            'closed_at': datetime.now(),
            'close_reason': reason,
            'status': 'CLOSED'
        }
        
        # Remove from open positions
        self.open_positions = [
            p for p in self.open_positions
            if p['position_id'] != position_id
        ]
        
        # Add to closed trades
        self.closed_trades.append(trade)
        
        logger.info(
            f"Position closed: {position['symbol']} {direction} "
            f"P&L: ${net_pnl:+,.2f} ({reason})"
        )
        
        # Save trade
        self._save_trade(trade)
        
        return {
            'success': True,
            'trade': trade
        }
    
    def close_partial_position(
        self,
        position_id: int,
        percentage: float,
        exit_price: float,
        reason: str = 'PARTIAL_TP'
    ) -> Dict:
        """
        Close partial position (for multi-TP)
        
        Args:
            position_id: Position ID
            percentage: Percentage to close (0-100)
            exit_price: Exit price
            reason: Close reason
            
        Returns:
            dict: Result
        """
        # Find position
        position = next(
            (p for p in self.open_positions if p['position_id'] == position_id),
            None
        )
        
        if not position:
            return {'success': False, 'reason': 'Position not found'}
        
        # Calculate partial amounts
        close_fraction = percentage / 100
        
        direction = position['direction']
        if direction == 'LONG':
            actual_exit = exit_price * (1 - self.slippage)
        else:
            actual_exit = exit_price * (1 + self.slippage)
        
        # Calculate P&L for closed portion
        entry_price = position['entry_price']
        total_size_coins = position['position_size_coins']
        close_size_coins = total_size_coins * close_fraction
        
        if direction == 'LONG':
            pnl = (actual_exit - entry_price) * close_size_coins
        else:
            pnl = (entry_price - actual_exit) * close_size_coins
        
        # Calculate fees
        close_value = close_size_coins * actual_exit
        exit_fee = close_value * self.taker_fee
        
        # Net P&L (proportional entry fee)
        entry_fee_portion = position['entry_fee'] * close_fraction
        net_pnl = pnl - entry_fee_portion - exit_fee
        
        # Update position (reduce size)
        old_size_usdt = position['position_size_usdt']
        old_size_coins = position['position_size_coins']
        old_margin = position['margin_used']
        
        position['position_size_coins'] = old_size_coins * (1 - close_fraction)
        position['position_size_usdt'] = old_size_usdt * (1 - close_fraction)
        
        # Release margin proportionally
        margin_released = old_margin * close_fraction
        position['margin_used'] = old_margin - margin_released
        
        # Update account
        self.margin_used -= margin_released
        self.balance += net_pnl
        self.realized_pnl += net_pnl
        
        # Track partial close
        position['partial_closes'].append({
            'percentage': percentage,
            'size_closed_coins': round(close_size_coins, 6),
            'exit_price': round(actual_exit, 2),
            'gross_pnl': round(pnl, 2),
            'net_pnl': round(net_pnl, 2),
            'closed_at': datetime.now(),
            'reason': reason
        })
        
        logger.info(
            f"Partial close {percentage}% of {position['symbol']} {direction} "
            f"@ ${actual_exit:.2f} → P&L: ${net_pnl:+,.2f} ({reason})"
        )
        
        return {
            'success': True,
            'net_pnl': round(net_pnl, 2),
            'remaining_size_usdt': round(position['position_size_usdt'], 2),
            'remaining_percentage': round((1 - close_fraction) * 100, 1)
        }
    
    def close_all_positions(self, reason: str = 'CLOSE_ALL'):
        """Close all open positions"""
        for position in self.open_positions.copy():
            self.close_position(
                position['position_id'],
                reason=reason
            )
    
    def _save_trade(self, trade: Dict):
        """Save trade to file"""
        filename = f"trade_{trade['position_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.data_dir / filename
        
        # Convert datetime to string
        trade_copy = trade.copy()
        trade_copy['opened_at'] = trade_copy['opened_at'].isoformat()
        trade_copy['closed_at'] = trade_copy['closed_at'].isoformat()
        
        with open(filepath, 'w') as f:
            json.dump(trade_copy, f, indent=2)
    
    def get_statistics(self) -> Dict:
        """Get trading statistics"""
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_win': 0,
                'avg_loss': 0
            }
        
        wins = [t for t in self.closed_trades if t['net_pnl'] > 0]
        losses = [t for t in self.closed_trades if t['net_pnl'] <= 0]
        
        total_trades = len(self.closed_trades)
        win_count = len(wins)
        loss_count = len(losses)
        
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
        
        avg_win = sum(t['net_pnl'] for t in wins) / win_count if wins else 0
        avg_loss = sum(t['net_pnl'] for t in losses) / loss_count if losses else 0
        
        total_pnl = sum(t['net_pnl'] for t in self.closed_trades)
        
        return {
            'total_trades': total_trades,
            'wins': win_count,
            'losses': loss_count,
            'win_rate': round(win_rate, 2),
            'total_pnl': round(total_pnl, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'largest_win': round(max((t['net_pnl'] for t in wins), default=0), 2),
            'largest_loss': round(min((t['net_pnl'] for t in losses), default=0), 2)
        }
    
    def reset(self):
        """Reset account to initial state"""
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.margin_used = 0.0
        self.unrealized_pnl = 0.0
        self.realized_pnl = 0.0
        self.open_positions = []
        self.closed_trades = []
        self.position_id_counter = 1
        self.max_positions = max_positions
        
        logger.info("Paper trading account reset")


# Convenience function
def get_paper_trading_engine(
    initial_balance: float = 1000.0,
    leverage: float = 20.0
) -> PaperTradingEngine:
    """
    Factory function to create PaperTradingEngine
    
    Args:
        initial_balance: Starting balance
        leverage: Max leverage
        
    Returns:
        PaperTradingEngine instance
    """
    return PaperTradingEngine(initial_balance, leverage)


if __name__ == "__main__":
    """Test paper trading engine"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("Testing Paper Trading Engine")
    print("=" * 70)
    
    # Initialize engine
    print("\n[1] Initializing paper trading engine...")
    engine = get_paper_trading_engine(initial_balance=1000.0, leverage=20.0)
    print("✅ Engine initialized")
    
    # Show initial state
    print("\n[2] Initial account state:")
    state = engine.get_account_state()
    print(f"   Balance:      ${state['balance']:,.2f}")
    print(f"   Equity:       ${state['equity']:,.2f}")
    print(f"   Margin Free:  ${state['margin_free']:,.2f}")
    
    # Open a position
    print("\n[3] Opening LONG position...")
    result = engine.open_position(
        symbol='BTCUSDT',
        direction='LONG',
        entry_price=66000.0,
        position_size_usdt=500.0,
        leverage=5.0,
        stop_loss=65500.0,
        take_profit={'tp1': {'price': 67000.0, 'allocation': 50}}
    )
    
    if result['success']:
        print("   ✅ Position opened!")
        pos = result['position']
        print(f"   ID:           {pos['position_id']}")
        print(f"   Entry:        ${pos['entry_price']:,.2f}")
        print(f"   Size:         ${pos['position_size_usdt']:,.2f}")
        print(f"   Margin:       ${pos['margin_used']:,.2f}")
        print(f"   Stop Loss:    ${pos['stop_loss']:,.2f}")
    
    # Update with new price
    print("\n[4] Updating position (price moved to $66,500)...")
    engine.update_positions({'BTCUSDT': 66500.0})
    
    state = engine.get_account_state()
    print(f"   Unrealized P&L: ${state['unrealized_pnl']:+,.2f}")
    print(f"   Equity:         ${state['equity']:,.2f}")
    
    # Close position
    print("\n[5] Closing position...")
    close_result = engine.close_position(
        position_id=1,
        exit_price=66500.0,
        reason='MANUAL'
    )
    
    if close_result['success']:
        trade = close_result['trade']
        print("   ✅ Position closed!")
        print(f"   Exit:         ${trade['exit_price']:,.2f}")
        print(f"   Gross P&L:    ${trade['gross_pnl']:+,.2f}")
        print(f"   Net P&L:      ${trade['net_pnl']:+,.2f}")
    
    # Show final state
    print("\n[6] Final account state:")
    state = engine.get_account_state()
    print(f"   Balance:      ${state['balance']:,.2f}")
    print(f"   Realized P&L: ${state['realized_pnl']:+,.2f}")
    print(f"   Total Trades: {state['total_trades']}")
    
    # Show statistics
    print("\n[7] Trading statistics:")
    stats = engine.get_statistics()
    print(f"   Total Trades: {stats['total_trades']}")
    print(f"   Win Rate:     {stats['win_rate']:.1f}%")
    print(f"   Total P&L:    ${stats['total_pnl']:+,.2f}")
    
    print("\n" + "=" * 70)
    print("✅ Paper trading engine test complete!")
    print("=" * 70)