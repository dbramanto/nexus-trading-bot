"""
NEXUS v2.0 - LONG-only Momentum Trading with Telegram Notifications
Single data fetch, shared P1 processing
"""

import sys
sys.path.insert(0, '/home/nexus/nexus_bot')

import time
import logging
from datetime import datetime
import pandas as pd

from config.strategy_config import NexusConfig, TopGainerMode
from core.top_gainer_scanner import TopGainerScanner
from core.paper_trader import PaperTrader
from core.p1_analyst import build_indicator_manager
from core.p2_supervisor.scoring_engine import ScoringEngine
from core.p3_manager.strategy_logic import StrategyLogic
from core.p4_auditor.trade_logger import TradeLogger
from execution.binance_client import BinanceClientWrapper
from execution.telegram_notifier import TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class NexusRunner:
    """
    OPTIMIZED: Single data fetch, shared P1 processing
    """
    
    def __init__(self):
        self.config = NexusConfig()
        self.tg_config = TopGainerMode()
        
        self.client = BinanceClientWrapper(testnet=self.config.trading.api_testnet)
        self.telegram = TelegramNotifier(enabled=True, mode_prefix="[NEXUS]")
        self.p1 = build_indicator_manager()
        self.p2 = ScoringEngine(self.config)
        self.p3 = StrategyLogic(self.config)
        self.p4_log = TradeLogger()
        
        # Stable symbols (feature disabled)
        # Stable trading disabled (zero trades in 68+ trades)
# [LEGACY]         self.stable_symbols = []  # Stable trading disabled (zero activity)
        
        # Top gainer symbols
        self.tg_scanner = TopGainerScanner()
        self.tg_symbols = []
        self.tg_last_refresh = None
        # Separate traders for fair A/B comparison
# [LEGACY]         self.stable_trader = None  # Stable trading disabled
        self.tg_trader = PaperTrader(initial_balance=10000)      # Top Gainers: Top gainers
        
        self.cycle_count = 0
        self.last_hourly_check = datetime.now().replace(minute=0, second=0, microsecond=0)
        self.last_daily_check = datetime.now().date()
        
        logger.info("="*80)
        logger.info("NEXUS NEXUS v2.0 INITIALIZED (OPTIMIZED)")
        logger.info("="*80)
# [LEGACY]         logger.info(f"Stable: {len(self.stable_symbols)} stable coins")
        logger.info(f"Top Gainers: Top {self.tg_config.top_n} gainers (paper)")
        logger.info("="*80)
        
        # Send startup notification
        self.telegram.send(
            "🚀 *NEXUS NEXUS v2.0 STARTED*\n\n"
# [LEGACY]             f"Stable: {len(self.stable_symbols)} stable coins (shadow)\n"
            f"Top Gainers: Top {self.tg_config.top_n} gainers (paper)\n"
            f"Cycle: Every 15 minutes\n"
            f"Deployed: {datetime.now().strftime('%Y-%m-%d %H:%M WIB')}"
        )
    
    def _fetch_df(self, symbol, interval="15m", limit=100):
        """Fetch and convert klines to DataFrame"""
        klines = self.client.get_futures_candles(symbol, interval, limit)
        
        rows = [
            {
                "timestamp": pd.to_datetime(k[0], unit="ms"),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5])
            }
            for k in klines
        ]
        
        df = pd.DataFrame(rows).set_index("timestamp")
        return df
    
    def refresh_top_gainers(self):
        """Refresh top gainer list every 4 hours"""
        should_refresh = (
            self.tg_last_refresh is None or
            (datetime.now() - self.tg_last_refresh).total_seconds() / 3600 >= self.tg_config.refresh_interval_hours
        )
        
        if should_refresh:
            logger.info("🔄 Refreshing top gainers...")
            self.tg_symbols = self.tg_scanner.get_top_gainers(
                top_n=self.tg_config.top_n,
                min_change=self.tg_config.min_24h_change,
                max_change=self.tg_config.max_24h_change,
                min_volume_usd=self.tg_config.min_volume_usd
            )
            self.tg_last_refresh = datetime.now()
            logger.info(f"✓ {len(self.tg_symbols)} top gainers found")
    
    def run_cycle(self):
        """
        OPTIMIZED CYCLE:
        1. Get unique symbols (stable + top gainers)
        2. Fetch data ONCE per symbol
        3. P1 analyze ONCE per symbol
        4. Route to Stable and/or Top Gainers
        """
        self.cycle_count += 1
        
        logger.info("")
        logger.info("="*80)
        logger.info(f"CYCLE {self.cycle_count} | {datetime.now().strftime('%H:%M:%S WIB')}")
        logger.info("="*80)
        
        # Refresh top gainers if needed
        self.refresh_top_gainers()
        
        # === OPTIMIZATION: Get unique symbols ===
        all_symbols = set(self.tg_symbols)  # Top Gainers only
# [LEGACY]         logger.info(f"📊 Scanning {len(all_symbols)} unique symbols (stable={len(self.stable_symbols)}, tg={len(self.tg_symbols)}, overlap={len(self.stable_symbols)+len(self.tg_symbols)-len(all_symbols)})")
        
        # Counters
        stable_signals = 0
        tg_signals = 0
        
        # Check exits for BOTH traders
        # Stable: Stable symbols
        # Stable exit check disabled
        
        # Top Gainers: Top gainers
        if self.tg_trader.open_positions:
            current_prices = {}
            for sym in self.tg_trader.open_positions.keys():
                try:
                    klines = self.client.get_futures_candles(sym, "15m", 1)
                    if klines:
                        current_prices[sym] = float(klines[-1][4])
                except:
                    pass
            self.tg_trader.check_exits(current_prices, self.tg_config.max_hold_hours)
        
        # === SINGLE LOOP: Fetch + Process ONCE per symbol ===
        for symbol in all_symbols:
            try:
                # 1. Fetch data ONCE
                df = self._fetch_df(symbol, "15m", 100)
                
                # 2. P1 analyze ONCE (expensive!)
                p1_rep = self.p1.run_all(df, self.config, symbol=symbol)
                # Inject symbol for P2 context
                # 3. P2 score ONCE
                ctx = self.p2.score(p1_rep.get("modules", p1_rep))
                
                # 4. P3 evaluate ONCE
                dec = self.p3.evaluate(ctx, circuit_breaker_active=False)
                
                # Extract common data

                # === LONG-ONLY MODE (Strategic Decision) ===
                # Skip BEARISH signals (SHORT not aligned with top gainer momentum)
                # See STRATEGY_CLARITY.md for rationale
                if ctx.get("bias") == "BEARISH":
                    logger.info(f"⏭️  {symbol} SHORT skipped (LONG-only momentum strategy)")
                    continue

                action = dec.get('action', 'NO_TRADE')
                score = ctx.get('score', 0)
                grade = ctx.get('grade', 'NO_TRADE')
                current_price = float(df.iloc[-1]['close'])
                
                # === Stable: If symbol in stable list ===

                # === SHADOW LOGGING FOR ML ===
                self.p4_log.log_shadow(
                    symbol=symbol,
                    direction=action if action != 'WAIT' else 'N/A',
                    potential_entry=current_price,
                    potential_sl=0,
                    potential_tp=0,
                    potential_lot=0,
                    score=score,
                    grade=grade,
                    bias=ctx.get('bias', 'NEUTRAL'),
                    reject_reason=dec.get('reason', 'NO_TRADE') if action == 'WAIT' else '',
                    p1_snapshot=ctx.get('p1_snapshot', {}),
                    ml_features={
                        'regime': ctx.get('regime', 'UNKNOWN'),
                        'threshold_used': ctx.get('threshold_used', 0),
                        'score_t0': ctx.get('tier_breakdown', {}).get('t0', 0),
                        'score_t1': ctx.get('tier_breakdown', {}).get('t1', 0),
                        'score_t2': ctx.get('tier_breakdown', {}).get('t2', 0),
                    },
                    score_breakdown=ctx.get('tier_breakdown', {}),
                    bias_reason={}
                )

                # Stable entry logic disabled
                if symbol in self.tg_symbols:
                    # Skip if position already open
                    if symbol in self.tg_trader.open_positions:
                        continue
                    
                    if action in ['LONG', 'SHORT']:
                        tg_signals += 1
                        
                        # Calculate SL/TP
                        sl_pct = self.tg_config.stop_loss_pct / 100
                        tp_pct = self.tg_config.take_profit_pct / 100
                        
                        if action == 'LONG':
                            sl = current_price * (1 - sl_pct)
                            tp = current_price * (1 + tp_pct)
                            bias = 'LONG'
                        else:
                            sl = current_price * (1 + sl_pct)
                            tp = current_price * (1 - tp_pct)
                            bias = 'SHORT'
                        
                        # Open paper position
                        signal = {
                            'symbol': symbol,
                            'bias': bias,
                            'current_price': current_price,
                            'sl_price': sl,
                            'tp_price': tp,
                            # === ADAPTIVE POSITION SIZING ===
                            # Conservative: 5% of balance, inverse leverage
                            'current_balance': self.tg_trader.balance,
                            'target_position_pct': 0.05,
                            'target_position': self.tg_trader.balance * 0.05,
                            'adaptive_leverage': 3 if score >= 70 else (2 if score >= 60 else 1),
                            'position_size': self.tg_trader.balance * 0.05,
                            'leverage': 3 if score >= 70 else (2 if score >= 60 else 1),
                            'p1_snapshot': p1_rep.get('modules', {}),
                            'score': score,
                            'grade': grade,
                        }
                        
                        self.tg_trader.open_position(signal)
                        
                        # DISABLED - Telegram notification for paper trade
                        # self.telegram.send(
                        # f"🚀 *Top Gainers Paper Trade*\n\n"
                        # f"Action: OPEN {bias}\n"
                        # f"Symbol: {symbol}\n"
                        # f"Entry: ${current_price:.4f}\n"
                        # f"SL: ${sl:.4f} (-{self.tg_config.stop_loss_pct}%)\n"
                        # f"TP: ${tp:.4f} (+{self.tg_config.take_profit_pct}%)\n"
                        # f"Score: {score:.1f} | Grade: {grade}"
                        # )
            
            except Exception as e:
                import traceback
                logger.error(f"Error processing {symbol}: {e}")
                logger.error(traceback.format_exc())
                continue
        
        # Stats
        # stable_stats disabled
        tg_stats = self.tg_trader.get_stats()
        
        logger.info("")
        logger.info(f"✓ Cycle {self.cycle_count} complete:")
        logger.info(f"  📊 TRADES: {tg_signals} new | Open={len(self.tg_trader.open_positions)} Closed={tg_stats['total_trades']} WR={tg_stats['win_rate']:.1f}% PnL=${tg_stats['total_pnl']:+.2f}")
        logger.info("="*80)
        
        # Hourly summary via Telegram
    

    def send_daily_report(self):
        """Send daily report at 07:00 WIB"""
        import pandas as pd
        
        tg_stats = self.tg_trader.get_stats()
        current_date = datetime.now().date()
        
        try:
            df = pd.read_csv('data/paper_trades_top_gainers.csv')
            df['entry_time'] = pd.to_datetime(df['entry_time'], format='mixed')
            yesterday = current_date - pd.Timedelta(days=1)
            yesterday_trades = df[df['entry_time'].dt.date == yesterday]
            yesterday_closed = yesterday_trades[yesterday_trades['outcome'].notna()]
            
            if len(yesterday_closed) > 0:
                y_wins = len(yesterday_closed[yesterday_closed['outcome']=='WIN'])
                y_wr = (y_wins/len(yesterday_closed))*100
                y_pnl = yesterday_closed['pnl_usd'].sum()
                yesterday_summary = f"📅 Yesterday: {len(yesterday_closed)} trades | WR {y_wr:.1f}% | PnL ${y_pnl:+.2f}\n\n"
            else:
                yesterday_summary = "📅 Yesterday: No closed trades\n\n"
        except:
            yesterday_summary = ""
        
        self.telegram.send(
            f"☀️ *Daily Report*\n\n"
            f"{yesterday_summary}"
            f"📊 Total: {tg_stats['total_trades']} | WR {tg_stats['win_rate']:.1f}% | PnL ${tg_stats['total_pnl']:+.2f}"
        )
        logger.info("📰 Daily report sent")

    def send_hourly_report(self):
        """Send hourly report at top of hour"""
        tg_stats = self.tg_trader.get_stats()
        
        self.telegram.send(
            f"📈 *Hourly Summary*\n\n"
            f"🕐 {datetime.now().strftime('%H:00 WIB')}\n\n"
            f"🟢 Open: {tg_stats['open_positions']} | Closed: {tg_stats['closed_trades']}\n"
            f"WR: {tg_stats['win_rate']:.1f}% | PnL: ${tg_stats['total_pnl']:+.2f}"
        )
        logger.info("📊 Hourly report sent")

    def run(self):
        """Main loop"""
        logger.info("🚀 Starting NEXUS NEXUS (OPTIMIZED)...")
        logger.info("Press Ctrl+C to stop")
        logger.info("")
        
        try:
            while True:
                self.run_cycle()
                
                logger.info("⏳ Sleeping 15 minutes...")
                time.sleep(900)
        
        except KeyboardInterrupt:
            logger.info("")
            logger.info("="*80)
            logger.info("STOPPING NEXUS v2.0")
            logger.info("="*80)
            
            stats = self.paper_trader.get_stats()
            logger.info(f"Paper Trading Results:")
            logger.info(f"  Total trades: {stats['total_trades']}")
            logger.info(f"  Win rate: {stats['win_rate']:.1f}%")
            logger.info(f"  Total PnL: ${stats['total_pnl']:+.2f}")
            logger.info(f"  ROI: {stats['roi']:+.1f}%")
            logger.info("="*80)
            
            # Final telegram notification
            self.telegram.send(
                f"🛑 *NEXUS NEXUS v2.0 STOPPED*\n\n"
                f"Paper Trading Final Results:\n"
                f"Total trades: {stats['total_trades']}\n"
                f"Win rate: {stats['win_rate']:.1f}%\n"
                f"PnL: ${stats['total_pnl']:+.2f}\n"
                f"ROI: {stats['roi']:+.1f}%\n\n"
                f"Stopped: {datetime.now().strftime('%Y-%m-%d %H:%M WIB')}"
            )
        
        except Exception as e:
            logger.error(f"FATAL ERROR: {e}", exc_info=True)
            
            # Error notification
            self.telegram.send(
                f"❌ *NEXUS NEXUS v2.0 CRASHED*\n\n"
                f"Error: {str(e)[:200]}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M WIB')}\n\n"
                f"⚠️ Check logs immediately!"
            )
            raise

if __name__ == '__main__':
    runner = NexusRunner()
    runner.run()
