"""
NEXUS v2.0 - Single Symbol Backtest
Test BTC 3-month historical data untuk verify module + pattern.
"""
import sys
sys.path.insert(0, "/home/nexus/nexus_bot")

import pandas as pd
import logging
from backtesting.engine import BacktestEngine
from core.p1_analyst import build_indicator_manager
from core.p2_supervisor.scoring_engine import ScoringEngine
from core.p3_manager.strategy_logic import StrategyLogic
from config.strategy_config import NexusConfig

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("=== NEXUS BACKTEST — BTCUSDT 3 MONTHS ===\n")
    
    # Load data
    df = pd.read_csv('data/historical/BTCUSDT_15m_3month.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    logger.info(f"Loaded {len(df)} candles")
    logger.info(f"Period: {df['timestamp'].min()} to {df['timestamp'].max()}\n")
    
    # Initialize components
    config = NexusConfig()
    p1_manager = build_indicator_manager()
    p2_engine = ScoringEngine(config)
    p3_logic = StrategyLogic(config)
    bt_engine = BacktestEngine(config, initial_balance=1000.0)
    
    # Run backtest
    logger.info("Running backtest...\n")
    result = bt_engine.run(df, p1_manager, p2_engine, p3_logic, symbol="BTCUSDT")
    
    # Extract trades
    trades = result.get('trades', [])
    
    if not trades:
        logger.warning("No trades generated!")
        return
    
    # Save results
    df_trades = pd.DataFrame(trades)
    output_file = 'data/backtest_btc_3month.csv'
    df_trades.to_csv(output_file, index=False)
    
    logger.info(f"=== BACKTEST COMPLETE ===")
    logger.info(f"Total trades: {len(trades)}")
    logger.info(f"Results saved: {output_file}\n")
    
    # Quick stats
    wins = len(df_trades[df_trades['exit_reason'] == 'TP'])
    losses = len(df_trades[df_trades['exit_reason'] == 'SL'])
    wr = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
    
    logger.info(f"WIN: {wins}")
    logger.info(f"LOSS: {losses}")
    logger.info(f"WIN RATE: {wr:.1f}%")

if __name__ == "__main__":
    main()
