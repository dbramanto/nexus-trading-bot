#!/usr/bin/env python3
"""
Multi-Threshold Backtest - FIXED VERSION
Tests: 45, 50, 52.5, 55, 57.5, 60
Period: 3 months (Jan-Mar 2026)
Runtime: 4-6 hours
"""
from backtesting.backtesting_engine import BacktestingEngine
from datetime import datetime
import pandas as pd
import logging
import json
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backtest.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_threshold_test(engine, symbols, start_date, end_date, threshold, run_name):
    """Run backtest with specific threshold"""
    
    logger.info("=" * 70)
    logger.info(f"TESTING THRESHOLD: {threshold}")
    logger.info("=" * 70)
    
    # Reset scans/trades
    engine.all_scans = []
    engine.all_trades = []
    
    # Set threshold in scoring engine
    if engine.scoring_engine:
        engine.scoring_engine.thresholds['weak'] = threshold
        logger.info(f"✅ Set scoring threshold to {threshold}")
    else:
        logger.error("❌ Scoring engine not initialized!")
        return None
    
    # Run backtest
    try:
        engine.run_backtest(symbols, start_date, end_date)
    except Exception as e:
        logger.error(f"❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Calculate metrics
    scans = len(engine.all_scans)
    signals = len(engine.all_trades)
    signal_rate = (signals / scans * 100) if scans > 0 else 0
    
    results = {
        'threshold': threshold,
        'scans': scans,
        'signals': signals,
        'signal_rate': signal_rate
    }
    
    # Calculate stats if trades exist
    if signals > 0:
        trades_df = pd.DataFrame(engine.all_trades)
        
        # Basic stats
        results['avg_score'] = float(trades_df['score'].mean())
        results['max_score'] = float(trades_df['score'].max())
        results['min_score'] = float(trades_df['score'].min())
        
        # Save detailed results
        output_dir = f"data/backtest_results/{run_name}/threshold_{threshold}"
        os.makedirs(output_dir, exist_ok=True)
        
        trades_df.to_parquet(f"{output_dir}/trades.parquet")
        
        # Score distribution
        results['score_distribution'] = {
            '55-60': int(len(trades_df[trades_df['score'].between(55, 60)])),
            '60-65': int(len(trades_df[trades_df['score'].between(60, 65)])),
            '65-70': int(len(trades_df[trades_df['score'].between(65, 70)])),
            '70-75': int(len(trades_df[trades_df['score'].between(70, 75)])),
            '75-80': int(len(trades_df[trades_df['score'].between(75, 80)])),
            '80-85': int(len(trades_df[trades_df['score'].between(80, 85)])),
            '85+': int(len(trades_df[trades_df['score'] >= 85]))
        }
        
        # Top symbols
        top_symbols = trades_df['symbol'].value_counts().head(5).to_dict()
        results['top_symbols'] = {k: int(v) for k, v in top_symbols.items()}
        
        logger.info(f"\n📊 RESULTS:")
        logger.info(f"   Signals: {signals:,} ({signal_rate:.2f}%)")
        logger.info(f"   Avg score: {results['avg_score']:.1f}")
        logger.info(f"   Score range: {results['min_score']:.1f} - {results['max_score']:.1f}")
        
    else:
        results['avg_score'] = 0
        results['max_score'] = 0
        results['min_score'] = 0
        results['score_distribution'] = {}
        results['top_symbols'] = {}
        
        logger.info(f"\n📊 RESULTS:")
        logger.info(f"   ❌ NO SIGNALS at threshold {threshold}")
    
    return results


def main():
    logger.info("=" * 70)
    logger.info("MULTI-THRESHOLD BACKTEST - STARTING")
    logger.info("=" * 70)
    
    # Configuration
    thresholds = [45, 50, 52.5, 55, 57.5, 60]
    
    symbols = [
        'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
        'DOGEUSDT', 'ADAUSDT', 'TRXUSDT', 'AVAXUSDT', 'DOTUSDT',
        'LINKUSDT', 'LTCUSDT', 'UNIUSDT', 'ATOMUSDT', 'MATICUSDT'
    ]
    
    # 3 months for faster testing
    start_date = '2026-01-01'
    end_date = '2026-03-31'
    
    run_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info(f"Run ID: {run_name}")
    logger.info(f"Symbols: {len(symbols)}")
    logger.info(f"Period: {start_date} to {end_date} (3 months)")
    logger.info(f"Thresholds to test: {thresholds}")
    logger.info(f"Expected runtime: 4-6 hours")
    logger.info("=" * 70)
    
    # Initialize engine
    engine = BacktestingEngine()
    
    # Load historical data ONCE
    logger.info("\n[STEP 1] Loading historical data...")
    historical_data = engine.load_historical_data(symbols, ['15m', '30m', '1h'])
    engine.historical_data = historical_data
    logger.info(f"✅ Loaded {len(historical_data)} symbols")
    
    # Initialize NEXUS components ONCE
    logger.info("\n[STEP 2] Initializing NEXUS components...")
    engine.initialize_nexus_components()
    logger.info("✅ NEXUS components ready")
    
    start_time = datetime.now()
    all_results = []
    
    # Test each threshold
    logger.info("\n[STEP 3] Running threshold tests...")
    for i, threshold in enumerate(thresholds, 1):
        logger.info(f"\n{'='*70}")
        logger.info(f"[{i}/{len(thresholds)}] Testing threshold: {threshold}")
        logger.info(f"{'='*70}")
        
        result = run_threshold_test(
            engine, symbols, start_date, end_date, threshold, run_name
        )
        
        if result:
            all_results.append(result)
        
        # Estimate remaining time
        elapsed = (datetime.now() - start_time).total_seconds()
        avg_per_threshold = elapsed / i
        remaining = avg_per_threshold * (len(thresholds) - i)
        
        logger.info(f"\n⏱️  Elapsed: {elapsed/60:.1f}m | Remaining: ~{remaining/60:.1f}m")
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    # Save summary
    output_dir = f"data/backtest_results/{run_name}"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(f"{output_dir}/summary.json", 'w') as f:
        json.dump(all_results, f, indent=2)
    
    # Print comparison
    logger.info("\n" + "=" * 70)
    logger.info("🎉 MULTI-THRESHOLD BACKTEST COMPLETE!")
    logger.info("=" * 70)
    logger.info(f"Duration: {duration}")
    logger.info(f"\n📊 COMPARISON TABLE:")
    logger.info("-" * 70)
    logger.info(f"{'Threshold':<12} {'Signals':<10} {'Rate':<10} {'Avg Score':<12}")
    logger.info("-" * 70)
    
    for r in all_results:
        logger.info(
            f"{r['threshold']:<12} "
            f"{r['signals']:<10,} "
            f"{r['signal_rate']:<10.2f}% "
            f"{r['avg_score']:<12.1f}"
        )
    
    logger.info("-" * 70)
    
    # Recommendations
    logger.info("\n💡 RECOMMENDATIONS:")
    
    # Find threshold with best balance
    valid_results = [r for r in all_results if r['signals'] > 0]
    
    if valid_results:
        # Sort by signal rate
        sorted_by_rate = sorted(valid_results, key=lambda x: x['signal_rate'], reverse=True)
        
        # Find sweet spot
        for r in sorted_by_rate:
            if r['signal_rate'] >= 1.0 and r['avg_score'] >= 60:
                logger.info(f"✅ Recommended threshold: {r['threshold']}")
                logger.info(f"   → Signal rate: {r['signal_rate']:.2f}%")
                logger.info(f"   → Avg score: {r['avg_score']:.1f}")
                break
        else:
            logger.info(f"⚠️ No ideal threshold found")
            logger.info(f"   Best signal rate: {sorted_by_rate[0]['threshold']} ({sorted_by_rate[0]['signal_rate']:.2f}%)")
    
    logger.info(f"\n✅ Results saved to: {output_dir}/")
    logger.info(f"   - summary.json")
    logger.info(f"   - threshold_*/trades.parquet")
    logger.info(f"   - backtest.log")


if __name__ == "__main__":
    main()
