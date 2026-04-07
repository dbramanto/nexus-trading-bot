"""
NEXUS Bot - Performance Tracker
Tracks and analyzes trading performance metrics
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json
import csv

# Setup logging
logger = logging.getLogger(__name__)


class PerformanceTracker:
    """
    Tracks trading performance and calculates metrics
    
    Metrics:
    - Win rate, profit factor, average win/loss
    - Total P&L, ROI, drawdown
    - Best/worst trades
    - Consecutive wins/losses
    - Daily/weekly/monthly summaries
    """
    
    def __init__(
        self,
        initial_balance: float = 1000.0,
        data_dir: str = 'data/performance'
    ):
        """
        Initialize performance tracker
        
        Args:
            initial_balance: Starting account balance
            data_dir: Directory for performance data
        """
        self.initial_balance = initial_balance
        self.data_dir = Path(data_dir)
        
        # Performance data
        self.trades: List[Dict] = []
        self.daily_snapshots: List[Dict] = []
        
        # Running metrics
        self.peak_balance = initial_balance
        self.current_balance = initial_balance
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        
        # Create data directory
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"PerformanceTracker initialized "
            f"(initial_balance=${initial_balance:,.2f})"
        )
    
    def add_trade(self, trade: Dict):
        """
        Add a completed trade to tracking
        
        Args:
            trade: Trade data from PaperTradingEngine
        """
        # Extract relevant data
        trade_record = {
            'trade_id': trade.get('position_id'),
            'symbol': trade.get('symbol'),
            'direction': trade.get('direction'),
            'entry_price': trade.get('entry_price'),
            'exit_price': trade.get('exit_price'),
            'position_size': trade.get('position_size_usdt'),
            'net_pnl': trade.get('net_pnl'),
            'gross_pnl': trade.get('gross_pnl'),
            'entry_fee': trade.get('entry_fee'),
            'exit_fee': trade.get('exit_fee'),
            'opened_at': trade.get('opened_at'),
            'closed_at': trade.get('closed_at'),
            'close_reason': trade.get('close_reason'),
            'stop_loss': trade.get('stop_loss'),
            'initial_stop_loss': trade.get('initial_stop_loss'),
            'partial_closes': trade.get('partial_closes', [])
        }
        
        self.trades.append(trade_record)
        
        # Update balance tracking
        self.current_balance += trade_record['net_pnl']
        
        # Update peak and drawdown
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
            self.current_drawdown = 0.0
        else:
            drawdown = (self.peak_balance - self.current_balance) / self.peak_balance * 100
            self.current_drawdown = drawdown
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
        
        logger.info(
            f"Trade recorded: {trade_record['symbol']} "
            f"P&L: ${trade_record['net_pnl']:+,.2f}"
        )
    
    def get_trade_metrics(self) -> Dict:
        """
        Calculate trade-related metrics
        
        Returns:
            dict: Trade metrics
        """
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'best_trade': 0.0,
                'worst_trade': 0.0
            }
        
        # Separate wins and losses
        wins = [t for t in self.trades if t['net_pnl'] > 0]
        losses = [t for t in self.trades if t['net_pnl'] <= 0]
        
        total_trades = len(self.trades)
        winning_trades = len(wins)
        losing_trades = len(losses)
        
        # Win rate
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Average win/loss
        avg_win = sum(t['net_pnl'] for t in wins) / winning_trades if wins else 0
        avg_loss = sum(t['net_pnl'] for t in losses) / losing_trades if losses else 0
        
        # Profit factor
        gross_profit = sum(t['net_pnl'] for t in wins)
        gross_loss = abs(sum(t['net_pnl'] for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Best/worst
        best_trade = max(t['net_pnl'] for t in self.trades)
        worst_trade = min(t['net_pnl'] for t in self.trades)
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'best_trade': round(best_trade, 2),
            'worst_trade': round(worst_trade, 2)
        }
    
    def get_account_metrics(self) -> Dict:
        """
        Calculate account-related metrics
        
        Returns:
            dict: Account metrics
        """
        total_pnl = self.current_balance - self.initial_balance
        roi = (total_pnl / self.initial_balance * 100) if self.initial_balance > 0 else 0
        
        return {
            'initial_balance': round(self.initial_balance, 2),
            'current_balance': round(self.current_balance, 2),
            'peak_balance': round(self.peak_balance, 2),
            'total_pnl': round(total_pnl, 2),
            'roi': round(roi, 2),
            'max_drawdown': round(self.max_drawdown, 2),
            'current_drawdown': round(self.current_drawdown, 2)
        }
    
    def get_risk_metrics(self) -> Dict:
        """
        Calculate risk-related metrics
        
        Returns:
            dict: Risk metrics
        """
        if not self.trades:
            return {
                'max_consecutive_wins': 0,
                'max_consecutive_losses': 0,
                'current_streak': 0,
                'streak_type': None
            }
        
        # Calculate consecutive streaks
        max_wins = 0
        max_losses = 0
        current_streak = 0
        streak_type = None
        
        temp_wins = 0
        temp_losses = 0
        
        for trade in self.trades:
            if trade['net_pnl'] > 0:
                temp_wins += 1
                temp_losses = 0
                if temp_wins > max_wins:
                    max_wins = temp_wins
            else:
                temp_losses += 1
                temp_wins = 0
                if temp_losses > max_losses:
                    max_losses = temp_losses
        
        # Current streak
        if temp_wins > 0:
            current_streak = temp_wins
            streak_type = 'WIN'
        elif temp_losses > 0:
            current_streak = temp_losses
            streak_type = 'LOSS'
        
        return {
            'max_consecutive_wins': max_wins,
            'max_consecutive_losses': max_losses,
            'current_streak': current_streak,
            'streak_type': streak_type
        }
    
    def get_complete_summary(self) -> Dict:
        """
        Get complete performance summary
        
        Returns:
            dict: Complete summary
        """
        return {
            'trade_metrics': self.get_trade_metrics(),
            'account_metrics': self.get_account_metrics(),
            'risk_metrics': self.get_risk_metrics(),
            'generated_at': datetime.now().isoformat()
        }
    
    def take_daily_snapshot(self):
        """
        Take daily account snapshot
        """
        snapshot = {
            'date': datetime.now().date().isoformat(),
            'balance': self.current_balance,
            'equity': self.current_balance,
            'trades_today': len([
                t for t in self.trades
                if t['closed_at'].date() == datetime.now().date()
            ]),
            'pnl_today': sum([
                t['net_pnl'] for t in self.trades
                if t['closed_at'].date() == datetime.now().date()
            ])
        }
        
        self.daily_snapshots.append(snapshot)
        logger.info(f"Daily snapshot taken: ${snapshot['balance']:,.2f}")
    
    def get_period_summary(
        self,
        period: str = 'daily'
    ) -> Dict:
        """
        Get summary for a specific period
        
        Args:
            period: 'daily', 'weekly', or 'monthly'
            
        Returns:
            dict: Period summary
        """
        now = datetime.now()
        
        if period == 'daily':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'weekly':
            start_date = now - timedelta(days=7)
        elif period == 'monthly':
            start_date = now - timedelta(days=30)
        else:
            start_date = now - timedelta(days=1)
        
        # Filter trades in period
        period_trades = [
            t for t in self.trades
            if t['closed_at'] >= start_date
        ]
        
        if not period_trades:
            return {
                'period': period,
                'trades': 0,
                'pnl': 0.0,
                'win_rate': 0.0
            }
        
        # Calculate metrics
        wins = [t for t in period_trades if t['net_pnl'] > 0]
        total_pnl = sum(t['net_pnl'] for t in period_trades)
        win_rate = (len(wins) / len(period_trades) * 100) if period_trades else 0
        
        return {
            'period': period,
            'start_date': start_date.isoformat(),
            'end_date': now.isoformat(),
            'trades': len(period_trades),
            'wins': len(wins),
            'losses': len(period_trades) - len(wins),
            'pnl': round(total_pnl, 2),
            'win_rate': round(win_rate, 2)
        }
    
    def export_to_csv(self, filename: str = 'trades.csv'):
        """
        Export trades to CSV file
        
        Args:
            filename: Output filename
        """
        filepath = self.data_dir / filename
        
        if not self.trades:
            logger.warning("No trades to export")
            return
        
        # Define CSV headers
        headers = [
            'trade_id', 'symbol', 'direction', 'entry_price', 'exit_price',
            'position_size', 'net_pnl', 'opened_at', 'closed_at', 'close_reason'
        ]
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            
            for trade in self.trades:
                row = {k: trade.get(k) for k in headers}
                # Convert datetime to string
                row['opened_at'] = str(row['opened_at'])
                row['closed_at'] = str(row['closed_at'])
                writer.writerow(row)
        
        logger.info(f"Trades exported to {filepath}")
    
    def export_summary_to_json(self, filename: str = 'summary.json'):
        """
        Export summary to JSON file
        
        Args:
            filename: Output filename
        """
        filepath = self.data_dir / filename
        
        summary = self.get_complete_summary()
        
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Summary exported to {filepath}")
    
    def reset(self):
        """Reset all tracking data"""
        self.trades = []
        self.daily_snapshots = []
        self.peak_balance = self.initial_balance
        self.current_balance = self.initial_balance
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        
        logger.info("Performance tracker reset")


# Convenience function
def get_performance_tracker(
    initial_balance: float = 1000.0
) -> PerformanceTracker:
    """
    Factory function to create PerformanceTracker
    
    Args:
        initial_balance: Starting balance
        
    Returns:
        PerformanceTracker instance
    """
    return PerformanceTracker(initial_balance)


if __name__ == "__main__":
    """Test performance tracker"""
    
    from datetime import datetime, timedelta
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("Testing Performance Tracker")
    print("=" * 70)
    
    # Initialize tracker
    print("\n[1] Initializing performance tracker...")
    tracker = get_performance_tracker(initial_balance=1000.0)
    print("✅ Tracker initialized")
    
    # Simulate some trades
    print("\n[2] Simulating trades...")
    
    base_time = datetime.now()
    
    # Trade 1: Win
    trade1 = {
        'position_id': 1,
        'symbol': 'BTCUSDT',
        'direction': 'LONG',
        'entry_price': 66000.0,
        'exit_price': 66500.0,
        'position_size_usdt': 250.0,
        'net_pnl': 10.0,
        'gross_pnl': 11.0,
        'entry_fee': 0.5,
        'exit_fee': 0.5,
        'opened_at': base_time - timedelta(hours=2),
        'closed_at': base_time - timedelta(hours=1),
        'close_reason': 'TAKE_PROFIT_1',
        'stop_loss': 65500.0,
        'initial_stop_loss': 65500.0,
        'partial_closes': []
    }
    tracker.add_trade(trade1)
    print("   ✅ Trade 1: +$10.00 (WIN)")
    
    # Trade 2: Loss
    trade2 = {
        'position_id': 2,
        'symbol': 'ETHUSDT',
        'direction': 'SHORT',
        'entry_price': 3500.0,
        'exit_price': 3520.0,
        'position_size_usdt': 250.0,
        'net_pnl': -5.0,
        'gross_pnl': -4.0,
        'entry_fee': 0.5,
        'exit_fee': 0.5,
        'opened_at': base_time - timedelta(minutes=90),
        'closed_at': base_time - timedelta(minutes=30),
        'close_reason': 'STOP_LOSS',
        'stop_loss': 3520.0,
        'initial_stop_loss': 3520.0,
        'partial_closes': []
    }
    tracker.add_trade(trade2)
    print("   ✅ Trade 2: -$5.00 (LOSS)")
    
    # Trade 3: Win
    trade3 = {
        'position_id': 3,
        'symbol': 'BTCUSDT',
        'direction': 'LONG',
        'entry_price': 66200.0,
        'exit_price': 67000.0,
        'position_size_usdt': 250.0,
        'net_pnl': 15.0,
        'gross_pnl': 16.0,
        'entry_fee': 0.5,
        'exit_fee': 0.5,
        'opened_at': base_time - timedelta(minutes=20),
        'closed_at': base_time - timedelta(minutes=5),
        'close_reason': 'TAKE_PROFIT_2',
        'stop_loss': 65900.0,
        'initial_stop_loss': 65900.0,
        'partial_closes': []
    }
    tracker.add_trade(trade3)
    print("   ✅ Trade 3: +$15.00 (WIN)")
    
    # Get metrics
    print("\n[3] Calculating performance metrics...")
    
    print("\n" + "=" * 70)
    print("PERFORMANCE SUMMARY")
    print("=" * 70)
    
    # Trade metrics
    trade_metrics = tracker.get_trade_metrics()
    print("\n📊 TRADE METRICS:")
    print(f"   Total Trades:     {trade_metrics['total_trades']}")
    print(f"   Winning Trades:   {trade_metrics['winning_trades']}")
    print(f"   Losing Trades:    {trade_metrics['losing_trades']}")
    print(f"   Win Rate:         {trade_metrics['win_rate']}%")
    print(f"   Avg Win:          ${trade_metrics['avg_win']:+,.2f}")
    print(f"   Avg Loss:         ${trade_metrics['avg_loss']:+,.2f}")
    print(f"   Profit Factor:    {trade_metrics['profit_factor']:.2f}")
    print(f"   Best Trade:       ${trade_metrics['best_trade']:+,.2f}")
    print(f"   Worst Trade:      ${trade_metrics['worst_trade']:+,.2f}")
    
    # Account metrics
    account_metrics = tracker.get_account_metrics()
    print("\n💰 ACCOUNT METRICS:")
    print(f"   Initial Balance:  ${account_metrics['initial_balance']:,.2f}")
    print(f"   Current Balance:  ${account_metrics['current_balance']:,.2f}")
    print(f"   Peak Balance:     ${account_metrics['peak_balance']:,.2f}")
    print(f"   Total P&L:        ${account_metrics['total_pnl']:+,.2f}")
    print(f"   ROI:              {account_metrics['roi']:+.2f}%")
    print(f"   Max Drawdown:     {account_metrics['max_drawdown']:.2f}%")
    print(f"   Current Drawdown: {account_metrics['current_drawdown']:.2f}%")
    
    # Risk metrics
    risk_metrics = tracker.get_risk_metrics()
    print("\n📉 RISK METRICS:")
    print(f"   Max Consecutive Wins:   {risk_metrics['max_consecutive_wins']}")
    print(f"   Max Consecutive Losses: {risk_metrics['max_consecutive_losses']}")
    print(f"   Current Streak:         {risk_metrics['current_streak']} {risk_metrics['streak_type'] or ''}")
    
    # Export
    print("\n[4] Exporting data...")
    tracker.export_to_csv('test_trades.csv')
    tracker.export_summary_to_json('test_summary.json')
    print("✅ Data exported")
    
    print("\n" + "=" * 70)
    print("✅ Performance tracker test complete!")
    print("=" * 70)