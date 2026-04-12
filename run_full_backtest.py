#!/usr/bin/env python3
"""
Run Full 6-Month Backtest
Expected: ~200K scans, ~15K signals
Runtime: 2-4 hours
"""

from backtesting.backtesting_engine import BacktestingEngine
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 70)
    logger.info("FULL 6-MONTH BACKTEST - STARTING")
    logger.info("=" * 70)
    
    # Initialize engine
    engine = BacktestingEngine()
    
    # All 15 symbols (excluding MATICUSDT - no data)
    symbols = [
        'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
        'DOGEUSDT', 'ADAUSDT', 'TRXUSDT', 'AVAXUSDT', 'DOTUSDT',
        'LINKUSDT', 'LTCUSDT', 'UNIUSDT', 'ATOMUSDT'
    ]
    
    # 6 months: Oct 12, 2025 - Apr 10, 2026
    start_date = '2025-10-12'
    end_date = '2026-04-10'
    
    logger.info(f"Symbols: {len(symbols)}")
    logger.info(f"Period: {start_date} to {end_date}")
    logger.info(f"Expected scans: ~200,000")
    logger.info(f"Expected signals: ~15,000")
    logger.info("=" * 70)
    
    start_time = datetime.now()
    
    # Run backtest
    engine.run_backtest(symbols, start_date, end_date)
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    logger.info("=" * 70)
    logger.info("🎉 FULL BACKTEST COMPLETE!")
    logger.info(f"Duration: {duration}")
    logger.info(f"Scans recorded: {len(engine.all_scans):,}")
    logger.info(f"Signals found: {len(engine.all_trades):,}")
    logger.info("=" * 70)
    
    # Summary stats
    if len(engine.all_trades) > 0:
        import pandas as pd
        trades_df = pd.DataFrame(engine.all_trades)
        
        logger.info("\n📊 QUICK SUMMARY:")
        logger.info(f"Signal rate: {len(engine.all_trades)/len(engine.all_scans)*100:.2f}%")
        logger.info(f"Avg score: {trades_df['score'].mean():.1f}")
        logger.info(f"Max score: {trades_df['score'].max():.1f}")
        logger.info(f"\nTop 3 symbols:")
        top_symbols = trades_df['symbol'].value_counts().head(3)
        for symbol, count in top_symbols.items():
            logger.info(f"  {symbol}: {count:,} signals")
    
    logger.info("\n✅ Results saved to data/backtest_results/")
    logger.info("   - scans.parquet")
    logger.info("   - trades.parquet")

if __name__ == "__main__":
    main()
