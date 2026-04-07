"""
NEXUS Bot - Daily Session Manager
Manages daily trading sessions with UTC timezone and 5% loss limit
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class DailySessionManager:
    """
    Manages daily trading sessions
    
    Features:
    - UTC timezone (display WIB)
    - Daily P&L tracking
    - 5% daily loss limit
    - Midnight reset (00:00 UTC)
    - Session history
    """
    
    def __init__(
        self,
        initial_balance: float,
        daily_loss_limit_percent: float = 5.0,
        data_dir: str = 'data/sessions'
    ):
        """
        Initialize daily session manager
        
        Args:
            initial_balance: Starting account balance
            daily_loss_limit_percent: Max daily loss % (default 5%)
            data_dir: Directory for session data
        """
        self.initial_balance = initial_balance
        self.daily_loss_limit_percent = daily_loss_limit_percent
        self.data_dir = Path(data_dir)
        
        # Create data directory
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Current session state
        self.session_start_time = None
        self.session_start_balance = initial_balance
        self.current_balance = initial_balance
        self.daily_pnl = 0.0
        self.trades_today = 0
        self.is_trading_suspended = False
        
        # Session history
        self.sessions = []
        
        # Start first session
        self._start_new_session()
        
        logger.info(
            f"DailySessionManager initialized "
            f"(balance=${initial_balance:,.2f}, limit={daily_loss_limit_percent}%)"
        )
    
    def _start_new_session(self):
        """Start a new daily session"""
        now_utc = datetime.now(timezone.utc)
        
        self.session_start_time = now_utc
        self.session_start_balance = self.current_balance
        self.daily_pnl = 0.0
        self.trades_today = 0
        self.is_trading_suspended = False
        
        logger.info(
            f"New session started: "
            f"{self._format_datetime(now_utc)} "
            f"(Balance: ${self.session_start_balance:,.2f})"
        )
    
    def _format_datetime(self, dt: datetime) -> str:
        """
        Format datetime as UTC + WIB
        
        Args:
            dt: datetime object (UTC)
            
        Returns:
            str: Formatted string "YYYY-MM-DD HH:MM UTC (HH:MM WIB)"
        """
        # UTC
        utc_str = dt.strftime('%Y-%m-%d %H:%M UTC')
        
        # WIB = UTC + 7 hours
        wib_dt = dt + timedelta(hours=7)
        wib_str = wib_dt.strftime('%H:%M WIB')
        
        return f"{utc_str} ({wib_str})"
    
    def check_daily_reset(self) -> bool:
        """
        Check if midnight UTC has passed and reset if needed
        
        Returns:
            bool: True if reset occurred
        """
        now_utc = datetime.now(timezone.utc)
        
        # Get midnight UTC for current day
        midnight_today = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # If session started before today's midnight, need reset
        if self.session_start_time < midnight_today:
            self._end_current_session()
            self._start_new_session()
            return True
        
        return False
    
    def update_balance(self, new_balance: float):
        """
        Update current balance and calculate daily P&L
        
        Args:
            new_balance: New account balance
        """
        self.current_balance = new_balance
        self.daily_pnl = new_balance - self.session_start_balance
        
        # Check if daily loss limit hit
        self._check_daily_loss_limit()
    
    def record_trade(self):
        """Record that a trade was executed today"""
        self.trades_today += 1
    
    def _check_daily_loss_limit(self):
        """Check if daily loss limit has been hit"""
        if self.daily_pnl >= 0:
            # Profit or breakeven - no limit
            self.is_trading_suspended = False
            return
        
        # Calculate daily loss percentage
        daily_loss_percent = abs(self.daily_pnl / self.session_start_balance * 100)
        
        if daily_loss_percent >= self.daily_loss_limit_percent:
            if not self.is_trading_suspended:
                self.is_trading_suspended = True
                
                logger.warning(
                    f"⛔ DAILY LOSS LIMIT HIT! "
                    f"Loss: ${self.daily_pnl:.2f} ({daily_loss_percent:.2f}%) "
                    f"Limit: {self.daily_loss_limit_percent}%"
                )
    
    def can_trade(self) -> tuple:
        """
        Check if trading is allowed
        
        Returns:
            tuple: (can_trade: bool, reason: str)
        """
        # Check for daily reset first
        self.check_daily_reset()
        
        # Check if suspended
        if self.is_trading_suspended:
            next_reset = self._get_next_reset_time()
            return False, f"Daily loss limit hit. Trading resumes at {self._format_datetime(next_reset)}"
        
        return True, ""
    
    def _get_next_reset_time(self) -> datetime:
        """Get next midnight UTC reset time"""
        now_utc = datetime.now(timezone.utc)
        
        # Next midnight UTC
        tomorrow = now_utc + timedelta(days=1)
        next_midnight = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        
        return next_midnight
    
    def _end_current_session(self):
        """End current session and save to history"""
        session_data = {
            'date': self.session_start_time.strftime('%Y-%m-%d'),
            'start_time': self.session_start_time.isoformat(),
            'start_balance': self.session_start_balance,
            'end_balance': self.current_balance,
            'daily_pnl': self.daily_pnl,
            'daily_pnl_percent': (self.daily_pnl / self.session_start_balance * 100) if self.session_start_balance > 0 else 0,
            'trades_count': self.trades_today,
            'limit_hit': self.is_trading_suspended
        }
        
        self.sessions.append(session_data)
        
        # Save to file
        self._save_session(session_data)
        
        logger.info(
            f"Session ended: "
            f"P&L ${session_data['daily_pnl']:+.2f} "
            f"({session_data['daily_pnl_percent']:+.2f}%) "
            f"Trades: {session_data['trades_count']}"
        )
    
    def _save_session(self, session_data: Dict):
        """Save session data to file"""
        date_str = session_data['date']
        filename = f"session_{date_str}.json"
        filepath = self.data_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(session_data, f, indent=2)
    
    def get_session_summary(self) -> Dict:
        """
        Get current session summary
        
        Returns:
            dict: Session summary
        """
        daily_loss_percent = 0
        if self.session_start_balance > 0:
            daily_loss_percent = (self.daily_pnl / self.session_start_balance * 100)
        
        # Calculate remaining until limit
        remaining_loss_dollars = 0
        remaining_loss_percent = 0
        
        if self.daily_pnl < 0:
            limit_dollars = self.session_start_balance * (self.daily_loss_limit_percent / 100)
            remaining_loss_dollars = limit_dollars - abs(self.daily_pnl)
            remaining_loss_percent = self.daily_loss_limit_percent - abs(daily_loss_percent)
        else:
            limit_dollars = self.session_start_balance * (self.daily_loss_limit_percent / 100)
            remaining_loss_dollars = limit_dollars
            remaining_loss_percent = self.daily_loss_limit_percent
        
        return {
            'session_date': self.session_start_time.strftime('%Y-%m-%d'),
            'session_start': self._format_datetime(self.session_start_time),
            'start_balance': self.session_start_balance,
            'current_balance': self.current_balance,
            'daily_pnl': self.daily_pnl,
            'daily_pnl_percent': daily_loss_percent,
            'trades_today': self.trades_today,
            'daily_loss_limit': self.daily_loss_limit_percent,
            'remaining_loss_dollars': remaining_loss_dollars,
            'remaining_loss_percent': remaining_loss_percent,
            'is_suspended': self.is_trading_suspended,
            'next_reset': self._format_datetime(self._get_next_reset_time()) if self.is_trading_suspended else None
        }
    
    def get_recent_sessions(self, count: int = 7) -> list:
        """
        Get recent session history
        
        Args:
            count: Number of recent sessions to return
            
        Returns:
            list: Recent sessions
        """
        return self.sessions[-count:] if self.sessions else []


# Convenience function
def get_daily_session_manager(
    initial_balance: float,
    daily_loss_limit: float = 5.0
) -> DailySessionManager:
    """
    Factory function to create DailySessionManager
    
    Args:
        initial_balance: Starting balance
        daily_loss_limit: Daily loss limit %
        
    Returns:
        DailySessionManager instance
    """
    return DailySessionManager(initial_balance, daily_loss_limit)


if __name__ == "__main__":
    """Test daily session manager"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("Testing Daily Session Manager")
    print("=" * 70)
    
    # Initialize
    print("\n[1] Initializing session manager...")
    manager = get_daily_session_manager(initial_balance=1000.0, daily_loss_limit=5.0)
    print("✅ Session manager initialized")
    
    # Show initial state
    print("\n[2] Initial session summary:")
    summary = manager.get_session_summary()
    print(f"   Session Date: {summary['session_date']}")
    print(f"   Session Start: {summary['session_start']}")
    print(f"   Start Balance: ${summary['start_balance']:,.2f}")
    print(f"   Daily Limit: -{summary['daily_loss_limit']:.1f}%")
    print(f"   Remaining: ${summary['remaining_loss_dollars']:.2f} ({summary['remaining_loss_percent']:.1f}%)")
    
    # Simulate some losses
    print("\n[3] Simulating trades...")
    
    # Trade 1: -$20 loss
    manager.update_balance(980.0)
    manager.record_trade()
    summary = manager.get_session_summary()
    print(f"   After Trade 1: ${summary['current_balance']:,.2f} "
          f"(Daily P&L: ${summary['daily_pnl']:+.2f} / {summary['daily_pnl_percent']:+.2f}%)")
    
    can_trade, reason = manager.can_trade()
    print(f"   Can Trade: {can_trade}")
    
    # Trade 2: -$15 loss
    manager.update_balance(965.0)
    manager.record_trade()
    summary = manager.get_session_summary()
    print(f"   After Trade 2: ${summary['current_balance']:,.2f} "
          f"(Daily P&L: ${summary['daily_pnl']:+.2f} / {summary['daily_pnl_percent']:+.2f}%)")
    
    can_trade, reason = manager.can_trade()
    print(f"   Can Trade: {can_trade}")
    
    # Trade 3: -$20 loss (will hit 5% limit)
    manager.update_balance(945.0)
    manager.record_trade()
    summary = manager.get_session_summary()
    print(f"   After Trade 3: ${summary['current_balance']:,.2f} "
          f"(Daily P&L: ${summary['daily_pnl']:+.2f} / {summary['daily_pnl_percent']:+.2f}%)")
    
    can_trade, reason = manager.can_trade()
    print(f"   Can Trade: {can_trade}")
    if not can_trade:
        print(f"   Reason: {reason}")
    
    # Show final summary
    print("\n[4] Final session summary:")
    summary = manager.get_session_summary()
    print(f"   Trades Today: {summary['trades_today']}")
    print(f"   Daily P&L: ${summary['daily_pnl']:+,.2f} ({summary['daily_pnl_percent']:+.2f}%)")
    print(f"   Suspended: {summary['is_suspended']}")
    if summary['is_suspended']:
        print(f"   Next Reset: {summary['next_reset']}")
    
    print("\n" + "=" * 70)
    print("✅ Daily session manager test complete!")
    print("=" * 70)