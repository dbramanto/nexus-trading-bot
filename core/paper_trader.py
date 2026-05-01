"""
NEXUS v2.0 - Paper Trading Engine
Simulates trade execution without real capital
"""

import logging
from execution.telegram_notifier import TelegramNotifier
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
        
        # Send entry notification
        try:
            notifier = TelegramNotifier()
            msg = (
                f"🟢 *ENTRY*\n\n"
                f"Symbol: {symbol}\n"
                f"Side: {trade['side']}\n"
                f"Entry: ${trade['entry_price']:.4f}\n"
                f"TP: ${trade['take_profit']:.4f}\n"
                f"SL: ${trade['stop_loss']:.4f}\n"
                f"Score: {trade['p2_score']:.1f}"
            )
            notifier.send(msg)
        except Exception as e:
            logger.warning(f"Entry notification failed: {e}")
        
        logger.info(
            f"📄 OPEN {trade['side']} {symbol} @ ${trade['entry_price']:.4f} | "
            f"SL: ${trade['stop_loss']:.4f} | TP: ${trade['take_profit']:.4f} | "
            f"Score: {trade['p2_score']:.1f}"
        )
        
        return trade
    
    def check_exits(self, current_prices: Dict[str, float], max_hold_hours: int = 4):
        """
        Check exit conditions for all open positions
        
        Args:
            current_prices: Dict of symbol -> current price
            max_hold_hours: Maximum hold time before force exit
        """
        
        symbols_to_close = []
        
        for symbol, trade in self.open_positions.items():
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            
            # Check SL
            if trade['side'] == 'LONG':
                if current_price <= trade['stop_loss']:
                    symbols_to_close.append((symbol, current_price, 'SL_HIT'))
                elif current_price >= trade['take_profit']:
                    symbols_to_close.append((symbol, current_price, 'TP_HIT'))
            else:  # SHORT
                if current_price >= trade['stop_loss']:
                    symbols_to_close.append((symbol, current_price, 'SL_HIT'))
                elif current_price <= trade['take_profit']:
                    symbols_to_close.append((symbol, current_price, 'TP_HIT'))
            
            # Check max hold time
            duration = (datetime.now() - trade['entry_time']).total_seconds() / 3600
            if duration >= max_hold_hours:
                symbols_to_close.append((symbol, current_price, 'MAX_HOLD'))
        
        # Close positions
        for symbol, exit_price, reason in symbols_to_close:
            self.close_position(symbol, exit_price, reason)
    
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
        
        # Send exit notification
        try:
            notifier = TelegramNotifier()
            emoji = "✅" if trade['outcome'] == "WIN" else "❌"
            msg = (
                f"{emoji} *EXIT*\n\n"
                f"Symbol: {symbol}\n"
                f"PnL: ${trade['pnl_usd']:+.2f}\n"
                f"Outcome: {trade['outcome']}\n"
                f"Reason: {reason}"
            )
            notifier.send(msg)
        except Exception as e:
            logger.warning(f"Exit notification failed: {e}")
        
        # Log
        emoji = "✅" if pnl_usd > 0 else "❌"
        logger.info(
            f"📄 {emoji} CLOSE {symbol} @ ${exit_price:.4f} | {reason} | "
            f"PnL: ${pnl_usd:+.2f} ({pnl_pct:+.2f}%)"
        )
        
        return trade
    
    def get_stats(self) -> Dict:
        """Get trading statistics"""
        
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0
            }
        
        wins = [t for t in self.closed_trades if t['outcome'] == 'WIN']
        losses = [t for t in self.closed_trades if t['outcome'] == 'LOSS']
        
        return {
            'total_trades': len(self.closed_trades),
            'win_rate': (len(wins) / len(self.closed_trades)) * 100,
            'total_pnl': sum(t['pnl_usd'] for t in self.closed_trades),
            'avg_win': sum(t['pnl_usd'] for t in wins) / len(wins) if wins else 0,
            'avg_loss': sum(t['pnl_usd'] for t in losses) / len(losses) if losses else 0
        }
