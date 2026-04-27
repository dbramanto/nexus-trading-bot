"""
NEXUS v2.0 - Dual Mode Forward Test Runner
With CORRECT klines to DataFrame conversion
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
from execution.binance_client import BinanceClientWrapper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('logs/nexus_dual_mode.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class DualModeRunner:
    """
    Run BOTH modes simultaneously:
    - MODE A: Stable coins (14 symbols, shadow mode)
    - MODE B: Top gainers (10 symbols, paper trading)
    """
    
    def __init__(self):
        self.config = NexusConfig()
        self.tg_config = TopGainerMode()
        
        # Initialize components (EXACT pattern from forward_test_runner.py)
        self.client = BinanceClientWrapper(testnet=self.config.trading.api_testnet)
        self.p1 = build_indicator_manager()
        self.p2 = ScoringEngine(self.config)
        self.p3 = StrategyLogic(self.config)
        
        # MODE A: Stable coins
        self.stable_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT',
            'XRPUSDT', 'ADAUSDT', 'AVAXUSDT', 'DOTUSDT',
            'MATICUSDT', 'LINKUSDT', 'UNIUSDT', 'ATOMUSDT',
            'LTCUSDT', 'ARBUSDT'
        ]
        
        # MODE B: Top gainers
        self.tg_scanner = TopGainerScanner()
        self.tg_symbols = []
        self.tg_last_refresh = None
        self.paper_trader = PaperTrader(initial_balance=10000)
        
        self.cycle_count = 0
        
        logger.info("="*80)
        logger.info("NEXUS DUAL MODE INITIALIZED")
        logger.info("="*80)
        logger.info(f"MODE A: {len(self.stable_symbols)} stable coins")
        logger.info(f"MODE B: Top {self.tg_config.top_n} gainers (paper)")
        logger.info("="*80)
    
    def _fetch_df(self, symbol, interval="15m", limit=200):
        """
        Convert raw klines to DataFrame
        EXACT method from forward_test_runner.py
        """
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
        """Refresh top gainer symbol list every 4 hours"""
        should_refresh = (
            self.tg_last_refresh is None or
            (datetime.now() - self.tg_last_refresh).total_seconds() / 3600 >= self.tg_config.refresh_interval_hours
        )
        
        if should_refresh:
            logger.info("🔄 Refreshing top gainer symbols...")
            self.tg_symbols = self.tg_scanner.get_top_gainers(
                top_n=self.tg_config.top_n,
                min_change=self.tg_config.min_24h_change,
                max_change=self.tg_config.max_24h_change,
                min_volume_usd=self.tg_config.min_volume_usd
            )
            self.tg_last_refresh = datetime.now()
            logger.info(f"✓ {len(self.tg_symbols)} top gainers found")
    
    def scan_symbol(self, symbol: str, mode: str):
        """
        Run P1 -> P2 -> P3 pipeline for one symbol
        Using EXACT pattern from forward_test_runner.py
        """
        try:
            # Get DataFrame (CORRECTED conversion)
            df = self._fetch_df(symbol, "15m", 200)
            
            # P1: Run all modules (EXACT pattern)
            p1_rep = self.p1.run_all(df, self.config)
            
            # P2: Score (EXACT pattern, cb_state=None for dual mode)
            ctx = self.p2.score(p1_rep, circuit_breaker_state=None)
            
            # P3: Evaluate (EXACT pattern)
            dec = self.p3.evaluate(ctx, circuit_breaker_active=False)
            
            # Extract results
            result = {
                'symbol': symbol,
                'mode': mode,
                'action': dec.get('action', 'NO_TRADE'),
                'score': ctx.get('score', 0),
                'grade': ctx.get('grade', 'NO_TRADE'),
                'bias': ctx.get('bias', 'NEUTRAL'),
                'current_price': float(df.iloc[-1]['close']),
                'p1_snapshot': p1_rep.get('modules', {}),
                'p2_context': ctx,
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")
            return {'action': 'NO_TRADE', 'symbol': symbol, 'mode': mode}
    
    def run_stable_mode(self):
        """MODE A: Scan stable coins (shadow mode)"""
        logger.info("📊 MODE A: Scanning stable coins...")
        signals = 0
        
        for symbol in self.stable_symbols:
            result = self.scan_symbol(symbol, 'STABLE')
            
            if result['action'] in ['OPEN_LONG', 'OPEN_SHORT']:
                signals += 1
                logger.info(
                    f"  ✅ STABLE: {result['action']} {symbol} | "
                    f"Score: {result['score']:.1f} | Grade: {result['grade']}"
                )
        
        logger.info(f"  MODE A complete: {signals} signals from {len(self.stable_symbols)} scans")
        return signals
    
    def run_top_gainer_mode(self):
        """MODE B: Paper trade top gainers"""
        logger.info("🚀 MODE B: Scanning top gainers...")
        
        if not self.tg_symbols:
            logger.info("  No top gainer symbols yet")
            return 0
        
        # Get current prices for exit checking
        current_prices = {}
        for sym in self.tg_symbols:
            try:
                klines = self.client.get_futures_candles(sym, "15m", 1)
                if klines:
                    current_prices[sym] = float(klines[-1][4])  # close price
            except:
                pass
        
        # Check exits on open positions
        self.paper_trader.check_exits(current_prices, self.tg_config.max_hold_hours)
        
        # Scan for new entries
        signals = 0
        for symbol in self.tg_symbols:
            # Skip if position already open
            if symbol in self.paper_trader.open_positions:
                continue
            
            result = self.scan_symbol(symbol, 'TOP_GAINER')
            
            if result['action'] in ['OPEN_LONG', 'OPEN_SHORT']:
                signals += 1
                
                # Calculate SL/TP
                price = result['current_price']
                sl_pct = self.tg_config.stop_loss_pct / 100
                tp_pct = self.tg_config.take_profit_pct / 100
                
                if result['action'] == 'OPEN_LONG':
                    sl = price * (1 - sl_pct)
                    tp = price * (1 + tp_pct)
                    bias = 'LONG'
                else:
                    sl = price * (1 + sl_pct)
                    tp = price * (1 - tp_pct)
                    bias = 'SHORT'
                
                # Create paper trade signal
                signal = {
                    'symbol': symbol,
                    'bias': bias,
                    'current_price': price,
                    'sl_price': sl,
                    'tp_price': tp,
                    'position_size': self.tg_config.position_size_usd,
                    'leverage': self.tg_config.leverage,
                    'p1_snapshot': result['p1_snapshot'],
                    'score': result['score'],
                    'grade': result['grade'],
                }
                
                self.paper_trader.open_position(signal)
        
        # Show stats
        stats = self.paper_trader.get_stats()
        logger.info(
            f"  MODE B complete: {signals} new signals | "
            f"Open: {len(self.paper_trader.open_positions)} | "
            f"Closed: {stats['total_trades']} | "
            f"WR: {stats['win_rate']:.1f}% | "
            f"PnL: ${stats['total_pnl']:+.2f}"
        )
        
        return signals
    
    def run_cycle(self):
        """Run one complete cycle"""
        self.cycle_count += 1
        
        logger.info("")
        logger.info("="*80)
        logger.info(f"CYCLE {self.cycle_count} | {datetime.now().strftime('%H:%M:%S WIB')}")
        logger.info("="*80)
        
        # Refresh top gainers if needed
        self.refresh_top_gainers()
        
        # Execute both modes
        stable_signals = self.run_stable_mode()
        tg_signals = self.run_top_gainer_mode()
        
        logger.info("")
        logger.info(f"✓ Cycle {self.cycle_count} complete | Stable: {stable_signals} | TopGainer: {tg_signals}")
        logger.info("="*80)
    
    def run(self):
        """Main loop"""
        logger.info("🚀 Starting NEXUS Dual Mode...")
        logger.info("Press Ctrl+C to stop")
        logger.info("")
        
        try:
            while True:
                self.run_cycle()
                
                logger.info("⏳ Sleeping 15 minutes...")
                time.sleep(900)  # 15 min
        
        except KeyboardInterrupt:
            logger.info("")
            logger.info("="*80)
            logger.info("STOPPING DUAL MODE")
            logger.info("="*80)
            
            # Final paper trading stats
            stats = self.paper_trader.get_stats()
            logger.info(f"Paper Trading Results:")
            logger.info(f"  Total trades: {stats['total_trades']}")
            logger.info(f"  Win rate: {stats['win_rate']:.1f}%")
            logger.info(f"  Total PnL: ${stats['total_pnl']:+.2f}")
            logger.info(f"  Final balance: ${stats['balance']:,.2f}")
            logger.info(f"  ROI: {stats['roi']:+.1f}%")
            logger.info("="*80)

if __name__ == '__main__':
    runner = DualModeRunner()
    runner.run()
