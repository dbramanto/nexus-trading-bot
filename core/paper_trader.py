"""
NEXUS v2.0 - Paper Trading Engine
Simulates trade execution without real capital
"""

import logging
import pandas as pd
from datetime import datetime
from typing import Dict, Optional
import os

logger = logging.getLogger(__name__)

class PaperTrader:
    """
    Paper trading engine for risk-free testing
    Tracks positions, calculates PnL, logs all trades
    """
    
    def __init__(self, initial_balance: float = 10000):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.open_positions = {}
        self.closed_trades = []
        
        logger.info(f"📄 Paper Trader initialized: ${initial_balance:,.2f} balance")
    
    def open_position(self, signal: Dict) -> Optional[Dict]:
        """
        Open a paper position
        
        Args:
            signal: Signal dict with symbol, bias, price, sl, tp, etc.
        
        Returns:
            Trade dict or None if already open
        """
        
        symbol = signal['symbol']
        
        # Check if position already open
        if symbol in self.open_positions:
            logger.warning(f"📄 Position already open on {symbol}, skipping")
            return None
        
        trade = {
            'symbol': symbol,
            'side': signal['bias'],
            'entry_price': signal['current_price'],
            'entry_time': datetime.now(),
            'size_usd': signal.get('position_size', 100),
            'leverage': signal.get('leverage', 2),
            'stop_loss': signal['sl_price'],
            'take_profit': signal['tp_price'],
            
            # P1/P2 data for analysis
            'p1_snapshot': signal.get('p1_snapshot', {}),
            'p2_score': signal.get('score', 0),
            'p2_grade': signal.get('grade', 'UNKNOWN'),
            
            # Outcome (filled on close)
            'exit_price': None,
            'exit_time': None,
            'exit_reason': None,
            'pnl_usd': None,
            'pnl_pct': None,
            'outcome': None,
        }
        
        self.open_positions[symbol] = trade
        
        logger.info(
            f"📄 OPEN {trade['side']} {symbol} @ ${trade['entry_price']:.4f} | "
            f"SL: ${trade['stop_loss']:.4f} | TP: ${trade['take_profit']:.4f} | "
            f"Score: {trade['p2_score']:.1f}"
        )
        
        return trade
    
    def check_exits(self, current_prices: Dict[str, float], max_hold_hours: int = 4):
        """
        Check all open positions for exit conditions
        
        Args:
            current_prices: Dict of {symbol: current_price}
            max_hold_hours: Maximum hold time in hours
        """
        
        for symbol in list(self.open_positions.keys()):
            trade = self.open_positions[symbol]
            current_price = current_prices.get(symbol)
            
            if current_price is None:
                continue
            
            # Check stop loss / take profit
            if trade['side'] == 'LONG':
                if current_price <= trade['stop_loss']:
                    self.close_position(symbol, current_price, 'SL_HIT')
                elif current_price >= trade['take_profit']:
                    self.close_position(symbol, current_price, 'TP_HIT')
            
            elif trade['side'] == 'SHORT':
                if current_price >= trade['stop_loss']:
                    self.close_position(symbol, current_price, 'SL_HIT')
                elif current_price <= trade['take_profit']:
                    self.close_position(symbol, current_price, 'TP_HIT')
            
            # Check max hold time
            hours_held = (datetime.now() - trade['entry_time']).total_seconds() / 3600
            if hours_held >= max_hold_hours:
                self.close_position(symbol, current_price, 'MAX_HOLD')
    
    def close_position(self, symbol: str, exit_price: float, reason: str) -> Dict:
        """
        Close a position and calculate PnL
        
        Args:
            symbol: Symbol to close
            exit_price: Exit price
            reason: Exit reason (SL_HIT, TP_HIT, MAX_HOLD)
        
        Returns:
            Closed trade dict
        """
        
        trade = self.open_positions.pop(symbol)
        
        # Calculate PnL
        entry = trade['entry_price']
        
        if trade['side'] == 'LONG':
            pnl_pct = ((exit_price - entry) / entry) * 100
        else:  # SHORT
            pnl_pct = ((entry - exit_price) / entry) * 100
        
        # Apply leverage
        pnl_pct *= trade['leverage']
        
        # Calculate USD PnL
        pnl_usd = trade['size_usd'] * (pnl_pct / 100)
        
        # Update balance
        self.balance += pnl_usd
        
        # Fill outcome fields
        trade['exit_price'] = exit_price
        trade['exit_time'] = datetime.now()
        trade['exit_reason'] = reason
        trade['pnl_usd'] = pnl_usd
        trade['pnl_pct'] = pnl_pct
        trade['outcome'] = 'WIN' if pnl_usd > 0 else 'LOSS'
        
        # Hold duration
        duration = (trade['exit_time'] - trade['entry_time']).total_seconds() / 3600
        trade['hold_hours'] = duration
        
        self.closed_trades.append(trade)
        
        # Log
        emoji = "✅" if pnl_usd > 0 else "❌"
        logger.info(
            f"📄 {emoji} CLOSE {symbol} @ ${exit_price:.4f} | {reason} | "
            f"PnL: ${pnl_usd:+.2f} ({pnl_pct:+.1f}%) | "
            f"Hold: {duration:.1f}h | Balance: ${self.balance:,.2f}"
        )
        
        # Save trade
        self.save_trade(trade)
        
        return trade
    
    def save_trade(self, trade: Dict):
        """
        Save closed trade to CSV
        
        Args:
            trade: Closed trade dict
        """
        
        output_file = 'data/paper_trades_top_gainers.csv'
        
        # Flatten for CSV
        flat_trade = {
            'symbol': trade['symbol'],
            'side': trade['side'],
            'entry_price': trade['entry_price'],
            'exit_price': trade['exit_price'],
            'entry_time': trade['entry_time'].isoformat(),
            'exit_time': trade['exit_time'].isoformat(),
            'exit_reason': trade['exit_reason'],
            'size_usd': trade['size_usd'],
            'leverage': trade['leverage'],
            'stop_loss': trade['stop_loss'],
            'take_profit': trade['take_profit'],
            'pnl_usd': trade['pnl_usd'],
            'pnl_pct': trade['pnl_pct'],
            'outcome': trade['outcome'],
            'hold_hours': trade['hold_hours'],
            'p2_score': trade['p2_score'],
            'p2_grade': trade['p2_grade'],
        }
        
        # Append to CSV
        df = pd.DataFrame([flat_trade])
        
        file_exists = os.path.exists(output_file)
        df.to_csv(output_file, mode='a', header=not file_exists, index=False)
    
    def get_stats(self) -> Dict:
        """
        Get paper trading statistics
        
        Returns:
            Stats dict with WR, PnL, etc.
        """
        
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'balance': self.balance,
                'roi': 0,
            }
        
        total = len(self.closed_trades)
        wins = sum(1 for t in self.closed_trades if t['outcome'] == 'WIN')
        total_pnl = sum(t['pnl_usd'] for t in self.closed_trades)
        
        return {
            'total_trades': total,
            'wins': wins,
            'losses': total - wins,
            'win_rate': wins / total * 100,
            'total_pnl': total_pnl,
            'balance': self.balance,
            'roi': (self.balance - self.initial_balance) / self.initial_balance * 100,
        }
