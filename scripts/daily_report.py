#!/usr/bin/env python3
"""
NEXUS Daily Report - 07:00 WIB Summary
Sends Telegram notification with yesterday's performance
"""

import sys
sys.path.insert(0, '/home/nexus/nexus_bot')

import pandas as pd
from datetime import datetime, timedelta
from execution.telegram_notifier import TelegramNotifier

def generate_daily_report():
    """Generate and send daily performance report"""
    
    try:
        # Load trades
        df = pd.read_csv('data/paper_trades_top_gainers.csv')
        df['exit_time'] = pd.to_datetime(df['exit_time'])
        
        # Yesterday's data
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_trades = df[df['exit_time'].dt.date == yesterday.date()]
        
        # Overall stats
        total_trades = len(df)
        total_wins = len(df[df['outcome'] == 'WIN'])
        total_wr = total_wins / total_trades * 100 if total_trades > 0 else 0
        total_pnl = df['pnl_usd'].sum()
        
        # Yesterday stats
        yesterday_count = len(yesterday_trades)
        yesterday_wins = len(yesterday_trades[yesterday_trades['outcome'] == 'WIN'])
        yesterday_wr = yesterday_wins / yesterday_count * 100 if yesterday_count > 0 else 0
        yesterday_pnl = yesterday_trades['pnl_usd'].sum() if yesterday_count > 0 else 0
        
        # Build report
        report = f"""📊 *NEXUS DAILY REPORT*
Date: {yesterday.strftime('%Y-%m-%d')}

*Yesterday:*
Trades: {yesterday_count}
Win Rate: {yesterday_wr:.1f}%
PnL: ${yesterday_pnl:+.2f}

*Overall Progress:*
Total: {total_trades}/100 trades
Win Rate: {total_wr:.1f}%
Total PnL: ${total_pnl:+.2f}

*Status:* {'✅ On track' if total_trades >= 50 else '⏳ Collecting data'}
"""
        
        # Send notification - CORRECT method is send()
        notifier = TelegramNotifier()
        notifier.send(report)
        
        print(f"✅ Daily report sent: {yesterday_count} trades yesterday, {total_trades} total")
        
    except Exception as e:
        print(f"❌ Error generating daily report: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    generate_daily_report()
