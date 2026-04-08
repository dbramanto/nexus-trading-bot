"""
NEXUS Bot - Forward Test Runner
Complete automated trading system with Telegram notifications
"""

import os
import sys
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List
from dotenv import load_dotenv

# Import all components
from execution.binance_client import get_binance_client
from execution.paper_trading_engine import get_paper_trading_engine
from execution.performance_tracker import get_performance_tracker
from execution.universe_scanner import get_universe_scanner
from execution.trade_execution_manager import get_trade_execution_manager
from execution.daily_session_manager import get_daily_session_manager
from execution.telegram_notifier import get_telegram_notifier
from core.report_generator import ReportGenerator
from core.market_analyzer import MarketAnalyzer


from core.indicator_manager import get_indicator_manager
from core.scoring_engine import get_scoring_engine
from core.signal_generator import get_signal_generator
from core.position_calculator import get_position_calculator
from core.trade_validator import get_trade_validator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/nexus_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ForwardTestRunner:
    """
    Complete forward testing system
    
    Features:
    - Universe scanning (best symbol selection)
    - Single position trading
    - Daily session management (UTC reset)
    - Telegram notifications
    - Performance tracking
    - Automated execution
    """
    
    def __init__(
        self,
        initial_balance: float = 1000.0,
        symbols: List[str] = None,
        mode: str = 'paper'
    ):
        """
        Initialize forward test runner
        
        Args:
            initial_balance: Starting balance
            symbols: List of symbols to scan
            mode: Trading mode ('paper' or 'live')
        """
        self.initial_balance = initial_balance
        self.mode = mode
        self.symbols = symbols
        # Heartbeat tracking
        self.last_heartbeat = datetime.now(timezone.utc)
        self.heartbeat_interval = 4 * 3600  # 4 hours
        self.scans_since_heartbeat = 0
        self.best_score_since_heartbeat = 0.0
        self.best_symbol_since_heartbeat = ""
        self.best_direction_since_heartbeat = ""
        self.scan_results_since_heartbeat = []
        logger.info("=" * 70)
        logger.info("NEXUS BOT - FORWARD TEST RUNNER")
        logger.info("=" * 70)
        logger.info(f"Mode: {mode.upper()}")
        logger.info(f"Initial Balance: ${initial_balance:,.2f}")
        logger.info(f"Symbols: {', '.join(self.symbols)}")
        
        # Initialize all components
        self._initialize_components()
        
        logger.info("=" * 70)
        logger.info("All components initialized successfully!")
        logger.info("=" * 70)
    
    def _initialize_components(self):
        """Initialize all trading components"""
        
        logger.info("\n[1/11] Initializing Binance client...")
        self.client = get_binance_client(testnet=False)
        
        logger.info("[2/11] Initializing paper trading engine...")
        self.paper_engine = get_paper_trading_engine(
            initial_balance=self.initial_balance
        )
        
        logger.info("[3/11] Initializing daily session manager...")
        self.session_manager = get_daily_session_manager(
            initial_balance=self.initial_balance,
            daily_loss_limit=5.0
        )
        
        logger.info("[4/11] Initializing Telegram notifier...")
        self.telegram = get_telegram_notifier(mode_prefix="[PAPER]")
                
        # Initialize report generator
        logger.info("[5/13] Initializing report generator...")
        self.report_generator = ReportGenerator()
        
        # Initialize market analyzer
        logger.info("[6/13] Initializing market analyzer...")
        self.market_analyzer = MarketAnalyzer()


        logger.info("[7/13] Initializing indicator manager...")
        self.indicator_manager = get_indicator_manager(self.client)
        
        logger.info("[8/13] Initializing scoring engine...")
        self.scoring_engine = get_scoring_engine()
        
        logger.info("[9/13] Initializing signal generator...")
        self.signal_generator = get_signal_generator()
        
        logger.info("[10/13] Initializing position calculator...")
        self.position_calculator = get_position_calculator(
            risk_per_trade=1.0,
            min_leverage=10.0,
            max_leverage=20.0,
            max_position_percent=25.0
        )
        
        logger.info("[11/13] Initializing trade validator...")
        self.trade_validator = get_trade_validator(
            session_manager=self.session_manager,
            min_signal_grade='WEAK'
        )
        
        logger.info("[12/13] Initializing universe scanner...")
        self.universe_scanner = get_universe_scanner(
            self.client,
            self.indicator_manager,
            self.scoring_engine
        )
        
        logger.info("[13/13] Initializing trade execution manager...")
        self.execution_manager = get_trade_execution_manager(
            self.client,
            self.paper_engine,
            self.indicator_manager,
            self.scoring_engine,
            self.signal_generator,
            self.position_calculator,
            self.trade_validator
        )
        
        # Send bot started notification
        self._send_bot_started_notification()
    
    def _send_bot_started_notification(self):
        """Send bot started notification to Telegram"""
        now_utc = datetime.now(timezone.utc)
        wib_time = now_utc.replace(tzinfo=None)  # Remove timezone for display
        
        config = {
            'mode': 'Paper Trading',
            'balance': self.initial_balance,
            'symbols': [s.replace('USDT', '') for s in self.symbols],
            'risk_per_trade': 1,
            'max_position': 25,
            'min_leverage': 10,
            'max_leverage': 20,
            'daily_limit': 5,
            'start_time': f"{now_utc.strftime('%Y-%m-%d %H:%M UTC')} ({(wib_time.hour + 7) % 24:02d}:{wib_time.minute:02d} WIB)"
        }
        
        self.telegram.notify_bot_started(config)
    
    def run_single_cycle(self) -> Dict:
        """
        Run single trading cycle
        
        Returns:
            dict: Cycle result
        """
        logger.info("\n" + "=" * 70)
        logger.info("STARTING TRADING CYCLE")
        logger.info("=" * 70)
        
        cycle_result = {
            'timestamp': datetime.now(timezone.utc),
            'action': None,
            'symbol': None,
            'reason': None,
            'best_score': 0.0,
            'best_symbol': ''
        }
        
        try:
            # Check daily reset
            if self.session_manager.check_daily_reset():
                logger.info("Daily reset occurred - new session started")
                self._send_daily_reset_notification()
            
            # Check if can trade (daily loss limit)
            can_trade, reason = self.session_manager.can_trade()
            if not can_trade:
                logger.warning(f"Trading suspended: {reason}")
                cycle_result['action'] = 'SUSPENDED'
                cycle_result['reason'] = reason
                return cycle_result
            
            # Check if position already open (single position mode)
            if self.execution_manager.has_open_position():
                logger.info("Position already open - skipping new trade")
                
                # Update existing position
                current_prices = self._get_current_prices()
                self.execution_manager.update_positions(current_prices)
                
                cycle_result['action'] = 'POSITION_OPEN'
                cycle_result['reason'] = 'Single position mode - waiting for close'
                return cycle_result
            
            # Scan universe for best opportunity
            logger.info(f"Scanning {len(self.symbols)} symbols...")
            
            # Get ALL results (min_score=0) for market analysis
            all_scan_results = self.universe_scanner.scan_universe(
                self.symbols,
                timeframe='15m',
                min_score=0  # Get all scores, not just >=55
            )
            
            # Also get opportunities (>=55) for trading
            scan_results = [r for r in all_scan_results if r.get('score', 0) >= 55]
            
            # scan_results has opportunities (>=55), all_scan_results has everything
            opportunities = scan_results if isinstance(scan_results, list) else []
            
            # Extract from ALL scan results for market analysis
            if all_scan_results:
                best_opp = all_scan_results[0]  # Already sorted by scanner
                cycle_result['best_score'] = best_opp.get('score', 0)
                cycle_result['best_symbol'] = best_opp.get('symbol', '')
                cycle_result['best_direction'] = best_opp.get('direction', '')
                cycle_result['all_scores'] = [opp.get('score', 0) for opp in all_scan_results]
            
            if not opportunities:
                logger.info("No opportunities found")
                cycle_result['action'] = 'NO_SIGNAL'
                cycle_result['reason'] = 'No symbols above threshold'
                
                # Send no signal notification (optional, every 10 cycles)
                # self.telegram.notify_no_signal(scan_results, self._get_account_summary())
                
                return cycle_result
                
            # Get best opportunity
            best = opportunities[0]
            logger.info(f"Best opportunity: {best['symbol']} (score: {best['score']:.1f})")
            cycle_result['best_score'] = best['score']
            cycle_result['best_symbol'] = best['symbol']
            
            # Execute trade for best symbol
            result = self.execution_manager.execute_trading_cycle(
                best['symbol'],
                timeframe='15m'
            )
            
            cycle_result['action'] = result['action']
            cycle_result['symbol'] = result['symbol']
            cycle_result['reason'] = result.get('reason', 'N/A')
            
            # Send notifications based on result
            if result['action'] == 'EXECUTED':
                self._send_trade_opened_notification(result)
                self.session_manager.record_trade()
            
            # Update session balance
            account_state = self.paper_engine.get_account_state()
            self.session_manager.update_balance(account_state['balance'])
            
        except Exception as e:
            logger.error(f"Cycle error: {e}", exc_info=True)
            cycle_result['action'] = 'ERROR'
            cycle_result['reason'] = str(e)
            
            # Send error notification
            error_info = {
                'type': 'Trading Cycle Error',
                'component': 'ForwardTestRunner',
                'message': str(e),
                'impact': 'Cycle skipped',
                'action': 'Continuing to next cycle',
                'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
            }
            self.telegram.notify_error(error_info)
        
        return cycle_result
    
    def _get_current_prices(self) -> Dict[str, float]:
        """Get current prices for all symbols"""
        prices = {}
        for symbol in self.symbols:
            try:
                ticker = self.client.get_ticker(symbol)
                prices[symbol] = float(ticker['lastPrice'])
            except Exception as e:
                logger.error(f"Error getting price for {symbol}: {e}")
        return prices
    
    def _get_account_summary(self) -> Dict:
        """Get account summary for notifications"""
        account = self.paper_engine.get_account_state()
        session = self.session_manager.get_session_summary()
        
        return {
            'balance': account['balance'],
            'daily_pnl': session['daily_pnl'],
            'daily_pnl_percent': session['daily_pnl_percent'],
            'open_positions': account['open_positions'],
            'trades_today': session['trades_today'],
            'wins_today': 0,  # TODO: Track from performance tracker
            'losses_today': 0,
            'daily_limit': session['daily_loss_limit']
        }
    
    def _send_trade_opened_notification(self, result: Dict):
        """Send trade opened notification"""
        # Get position details
        position = self.execution_manager.get_open_position()
        if not position:
            return
        
        trade_info = {
            'symbol': result['symbol'],
            'direction': result['direction'],
            'entry_price': position['entry_price'],
            'position_size': position['position_size_usdt'],
            'position_percent': (position['position_size_usdt'] / self.session_manager.current_balance * 100),
            'leverage': position['leverage'],
            'sl_price': position['stop_loss'],
            'sl_percent': ((position['stop_loss'] - position['entry_price']) / position['entry_price'] * 100),
            'tp1_price': position['take_profit']['tp1'],
            'tp1_percent': ((position['take_profit']['tp1'] - position['entry_price']) / position['entry_price'] * 100),
            'tp2_price': position['take_profit']['tp2'],
            'tp2_percent': ((position['take_profit']['tp2'] - position['entry_price']) / position['entry_price'] * 100),
            'tp3_price': position['take_profit']['tp3'],
            'tp3_percent': ((position['take_profit']['tp3'] - position['entry_price']) / position['entry_price'] * 100),
            'score': result.get('signal_score', 0),
            'grade': result.get('signal_grade', 'N/A'),
            'setup_type': 'Consolidation Breakout',
            'reason': 'Score above threshold',
            'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        }
        
        account_info = self._get_account_summary()
        
        self.telegram.notify_trade_opened(trade_info, account_info)
    
    def _send_daily_reset_notification(self):
        """Send daily reset notification"""
        sessions = self.session_manager.get_recent_sessions(count=1)
        
        if sessions:
            yesterday = sessions[0]
        else:
            yesterday = {
                'date': 'N/A',
                'start_balance': self.initial_balance,
                'end_balance': self.initial_balance,
                'pnl': 0,
                'pnl_percent': 0,
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0
            }
        
        session_summary = self.session_manager.get_session_summary()
        
        today = {
            'date': session_summary['session_date'],
            'balance': session_summary['start_balance'],
            'daily_limit': session_summary['remaining_loss_dollars'],
            'daily_limit_percent': session_summary['daily_loss_limit'],
            'cumulative_pnl': 0,  # TODO: Track
            'cumulative_roi': 0,
            'total_trades': 0,
            'overall_win_rate': 0,
            'days_traded': len(self.session_manager.sessions) + 1
        }
        
        self.telegram.notify_daily_reset(yesterday, today)
    
    def run_continuous(self, cycle_interval: int = 300):
        """
        Run continuous forward testing
        
        Args:
            cycle_interval: Seconds between cycles (default: 300 = 5 min)
        """
        logger.info("\n" + "=" * 70)
        logger.info("STARTING CONTINUOUS FORWARD TESTING")
        logger.info("=" * 70)
        logger.info(f"Cycle Interval: {cycle_interval} seconds")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 70)
        
        cycle_count = 0
        
        try:
            while True:
                cycle_count += 1
                logger.info(f"\nCycle #{cycle_count}")
                
                # Run cycle
                result = self.run_single_cycle()

                # Heartbeat tracking
                self.scans_since_heartbeat += 1
                
                # Track scan results for market analysis
                if result.get('best_score'):
                    self.scan_results_since_heartbeat.append(result)
                    
                    if result['best_score'] > self.best_score_since_heartbeat:
                        self.best_score_since_heartbeat = result['best_score']
                        self.best_symbol_since_heartbeat = result.get('best_symbol', '')
                        self.best_direction_since_heartbeat = result.get('best_direction', '')
                
                # Send heartbeat at 4H candle close (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC)
                if self._should_send_heartbeat():
                    self._send_heartbeat()
                
                # Check if it's time to send reports
                self._check_and_send_reports()

                logger.info(f"Cycle result: {result['action']}")
                if result.get('symbol'):
                    logger.info(f"Symbol: {result['symbol']}")
                if result.get('reason'):
                    logger.info(f"Reason: {result['reason']}")
                
                # Show account state
                account = self.paper_engine.get_account_state()
                session = self.session_manager.get_session_summary()
                
                logger.info(f"\nAccount: ${account['balance']:,.2f}")
                logger.info(f"Today's P&L: ${session['daily_pnl']:+,.2f} ({session['daily_pnl_percent']:+.2f}%)")
                logger.info(f"Open Positions: {account['open_positions']}")
                
                # Wait for next cycle
                logger.info(f"\nWaiting {cycle_interval} seconds for next cycle...")
                time.sleep(cycle_interval)
                
        except KeyboardInterrupt:
            logger.info("\n" + "=" * 70)
            logger.info("STOPPING BOT (Keyboard Interrupt)")
            logger.info("=" * 70)
            self._show_final_summary()
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            self._show_final_summary()

    
    def _should_send_heartbeat(self) -> bool:
        """Check if it's time to send heartbeat (aligned with 4H candle close)"""
        now_utc = datetime.now(timezone.utc)
        current_hour = now_utc.hour
        current_minute = now_utc.minute
        
        # 4H candle closes at: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC
        candle_close_hours = [0, 4, 8, 12, 16, 20]
        
        # Check if current hour is a candle close hour
        if current_hour not in candle_close_hours:
            return False
        
        # Check if we're within the first 5 minutes of the hour
        if current_minute >= 5:
            return False
        
        # Check if we already sent heartbeat this hour
        last_heartbeat_hour = self.last_heartbeat.hour
        if current_hour == last_heartbeat_hour:
            return False
        
        return True

    def _send_heartbeat(self):
        """Send periodic heartbeat notification with market analysis"""
        try:
            now_utc = datetime.now(timezone.utc)
            wib_hour = (now_utc.hour + 7) % 24
            
            # Analyze market condition
            market_analysis = self.market_analyzer.analyze_market_condition(
                self.scan_results_since_heartbeat
            )
            
            # Format gap to threshold
            gap = self.best_score_since_heartbeat - 55
            gap_text = f"{gap:+.1f}" if self.best_score_since_heartbeat > 0 else "N/A"
            
            # Build enhanced message
            message = f"""━━━━━━━━━━━━━━━━━━━━━━━━
✅ MARKET WATCH
Candle: 4H Close ({wib_hour:02d}:00 WIB)
━━━━━━━━━━━━━━━━━━━━━━━━

📊 SCANNING
{self.scans_since_heartbeat} scans | 15 coins | 15m TF

🎯 BEST: {self.best_symbol_since_heartbeat} {self.best_direction_since_heartbeat}
Score: {self.best_score_since_heartbeat:.1f}/55 ({self.best_score_since_heartbeat/55*100:.0f}%) | Gap: {gap_text}

📈 MARKET: {market_analysis['trend']}
Trend: {market_analysis['trend']} | Vol: {market_analysis['volatility']}
Avg score: {market_analysis['avg_score']:.1f} | {market_analysis['confluence']} setup

💰 ACCOUNT
${self.paper_engine.get_account_state()['balance']:,.2f} | {self.paper_engine.get_account_state()['open_positions']} pos | +$0 today

💡 INSIGHT
{market_analysis['insight']}

⏰ Next: {((wib_hour + 4) % 24):02d}:00 WIB
━━━━━━━━━━━━━━━━━━━━━━━━"""
            
            self.telegram.send_message(message)
            logger.info(f"Heartbeat sent (4H close at {wib_hour:02d}:00 WIB)")
            
            # Reset counters
            self.scans_since_heartbeat = 0
            self.best_score_since_heartbeat = 0.0
            self.best_symbol_since_heartbeat = ""
            self.best_direction_since_heartbeat = ""
            self.scan_results_since_heartbeat = []
            self.last_heartbeat = now_utc
            
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
    def _check_and_send_reports(self):
        """Check if it's time to send reports and send them"""
        try:
            now_utc = datetime.now(timezone.utc)
            current_date = now_utc.date()
            current_time = now_utc.time()
            
            # Check if it's midnight UTC (within 5-minute window)
            is_midnight = current_time.hour == 0 and current_time.minute < 5
            
            if not is_midnight:
                return
            
            # Daily report (every day at 00:00 UTC)
            logger.info("Generating daily report...")
            session_data = self.session_manager.get_session_summary()
            daily_report = self.report_generator.generate_daily_report(session_data)
            self.telegram.notify_daily_report(daily_report)
            logger.info("Daily report sent")
            
            # Weekly report (Sunday only)
            if now_utc.weekday() == 6:  # Sunday = 6
                logger.info("Generating weekly report...")
                weekly_report = self.report_generator.generate_weekly_report()
                if weekly_report:
                    self.telegram.notify_weekly_report(weekly_report)
                    logger.info("Weekly report sent")
            
            # Monthly report (1st day of month only)
            if current_date.day == 1:
                logger.info("Generating monthly report...")
                monthly_report = self.report_generator.generate_monthly_report()
                if monthly_report:
                    self.telegram.notify_monthly_report(monthly_report)
                    logger.info("Monthly report sent")
                    
        except Exception as e:
            logger.error(f"Error checking/sending reports: {e}")


    def _show_final_summary(self):
        """Show final performance summary"""
        logger.info("\n" + "=" * 70)
        logger.info("FINAL SUMMARY")
        logger.info("=" * 70)
        
        account = self.paper_engine.get_account_state()
        stats = self.paper_engine.get_statistics()
        session = self.session_manager.get_session_summary()
        
        logger.info(f"\nFinal Balance: ${account['balance']:,.2f}")
        logger.info(f"Total P&L: ${account['balance'] - self.initial_balance:+,.2f}")
        logger.info(f"ROI: {((account['balance'] - self.initial_balance) / self.initial_balance * 100):+.2f}%")
        
        logger.info(f"\nTotal Trades: {stats['total_trades']}")
        logger.info(f"Win Rate: {stats['win_rate']:.1f}%")
        if stats['total_trades'] > 0:
            logger.info(f"Profit Factor: {stats.get('profit_factor', 0.0):.2f}")
        
        logger.info(f"\nToday's Trades: {session['trades_today']}")
        logger.info(f"Today's P&L: ${session['daily_pnl']:+,.2f} ({session['daily_pnl_percent']:+.2f}%)")
        
        logger.info("\n" + "=" * 70)


def main():
    """Main entry point"""
    
    # Load environment variables
    load_dotenv()
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Configuration
    INITIAL_BALANCE = 1000.0
    SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
    'DOGEUSDT', 'ADAUSDT', 'TRXUSDT', 'AVAXUSDT', 'DOTUSDT',
    'LINKUSDT', 'MATICUSDT', 'LTCUSDT', 'UNIUSDT', 'ATOMUSDT'
]
    CYCLE_INTERVAL = 300  # 5 minutes
    
    # Initialize runner
    runner = ForwardTestRunner(
        initial_balance=INITIAL_BALANCE,
        symbols=SYMBOLS,
        mode='paper'
    )
    
    # Run continuous testing
    runner.run_continuous(cycle_interval=CYCLE_INTERVAL)


if __name__ == "__main__":
    main()
