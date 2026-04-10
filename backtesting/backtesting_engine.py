#!/usr/bin/env python3
"""
Backtesting Engine for NEXUS

Replays historical candles and simulates NEXUS trading logic.
Records all scans, signals, and trades for ML training.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
import pandas as pd
from tqdm import tqdm
from backtesting.historical_adapter import HistoricalDataAdapter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BacktestingEngine:
    """
    Replay historical data through NEXUS system
    """
    
    def __init__(
        self,
        data_dir: str = 'data/historical',
        output_dir: str = 'data/backtest_results'
    ):
        """
        Initialize backtesting engine
        
        Args:
            data_dir: Directory with historical CSV files
            output_dir: Directory to save backtest results
        """
        self.data_dir = data_dir
        self.output_dir = output_dir
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Will be initialized when running backtest
        self.indicator_manager = None
        self.scoring_engine = None
        self.signal_generator = None
        
        # Results storage
        self.all_scans = []
        self.all_trades = []
        
        logger.info(f"BacktestingEngine initialized")
        logger.info(f"Data dir: {data_dir}")
        logger.info(f"Output dir: {output_dir}")
    
    def load_historical_data(
        self,
        symbols: List[str],
        intervals: List[str]
    ) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Load historical CSV files
        
        Args:
            symbols: List of trading pairs
            intervals: List of timeframes
        
        Returns:
            Nested dict: {symbol: {interval: DataFrame}}
        """
        logger.info("Loading historical data...")
        data = {}
        
        for symbol in symbols:
            data[symbol] = {}
            
            for interval in intervals:
                filepath = os.path.join(self.data_dir, f"{symbol}_{interval}.csv")
                
                if not os.path.exists(filepath):
                    logger.warning(f"File not found: {filepath}")
                    continue
                
                df = pd.read_csv(filepath)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # Skip empty files (like MATICUSDT)
                if len(df) == 0:
                    logger.warning(f"Empty file: {filepath}")
                    continue
                
                data[symbol][interval] = df
                logger.info(f"Loaded {symbol} {interval}: {len(df)} candles")
        
        logger.info(f"✅ Loaded data for {len(data)} symbols")
        
        # Store for adapter use
        self.historical_data = data
        
        return data
    
    def initialize_nexus_components(self):
        """
        Initialize NEXUS components for analysis
        
        This will import and initialize:
        - IndicatorManager
        - ScoringEngine  
        - SignalGenerator
        """
        logger.info("Initializing NEXUS components...")
        
        # Import NEXUS modules
        from core.indicator_manager import IndicatorManager
        from core.scoring_engine import ScoringEngine
        from core.signal_generator import SignalGenerator
        from binance.client import Client
        
        # Initialize Binance client (for API info, not trading)
        binance_client = Client("", "")  # Empty keys OK for public data
        
        # Initialize
        self.indicator_manager = IndicatorManager(
            binance_client=binance_client,
            timeframes=['15m', '30m', '1h']
        )
        self.scoring_engine = ScoringEngine()
        self.signal_generator = SignalGenerator()
        
        logger.info("✅ NEXUS components initialized")

        # Create historical data adapter
        self.adapter = HistoricalDataAdapter(self.historical_data)
        
        # Inject adapter into IndicatorManager
        self.adapter.inject_into_indicator_manager(self.indicator_manager)
        
        logger.info("✅ Historical adapter configured")
    
    def get_candles_at_timestamp(
        self,
        data: Dict[str, Dict[str, pd.DataFrame]],
        timestamp: pd.Timestamp,
        lookback: int = 100
    ) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Get candles up to timestamp for all symbols and intervals
        
        Args:
            data: Full historical data
            timestamp: Current timestamp
            lookback: Number of candles to include
        
        Returns:
            Candles dict: {symbol: {interval: DataFrame}}
        """
        candles = {}
        
        for symbol, intervals_data in data.items():
            candles[symbol] = {}
            
            for interval, df in intervals_data.items():
                # Get candles up to timestamp
                mask = df['timestamp'] <= timestamp
                recent = df[mask].tail(lookback)
                
                if len(recent) > 0:
                    candles[symbol][interval] = recent
        
        return candles
    
    def run_backtest(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        initial_balance: float = 1000.0
    ):
        """
        Run complete backtest
        
        Args:
            symbols: List of trading pairs
            start_date: Start date 'YYYY-MM-DD'
            end_date: End date 'YYYY-MM-DD'
            initial_balance: Starting balance
        """
        logger.info("=" * 70)
        logger.info("STARTING BACKTEST")
        logger.info("=" * 70)
        logger.info(f"Symbols: {len(symbols)}")
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Initial Balance: ${initial_balance:,.2f}")
        logger.info("=" * 70)
        
        # Load data
        intervals = ['15m', '30m', '1h', '4h']
        data = self.load_historical_data(symbols, intervals)
        
        # Initialize NEXUS
        self.initialize_nexus_components()
        
        # Get 15m timestamps (primary timeframe)
        # Use first symbol with 15m data
        primary_symbol = None
        for symbol in symbols:
            if '15m' in data.get(symbol, {}):
                primary_symbol = symbol
                break
        
        if not primary_symbol:
            logger.error("No 15m data found for any symbol!")
            return
        
        timestamps = data[primary_symbol]['15m']['timestamp']
        
        # Filter by date range
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        timestamps = timestamps[(timestamps >= start_dt) & (timestamps <= end_dt)]
        
        logger.info(f"Processing {len(timestamps)} timestamps...")
        logger.info("=" * 70)
        
        # Process each timestamp with progress bar
        for timestamp in tqdm(timestamps, desc="Backtesting"):
            # Get candles at this timestamp
            current_candles = self.get_candles_at_timestamp(data, timestamp)
            
            # Set current timestamp in adapter
            self.adapter.set_timestamp(timestamp)
            
            # Analyze each symbol
            for symbol in symbols:
                if symbol not in current_candles:
                    continue
                
                try:
                    # Run NEXUS analysis
                    self._analyze_symbol(symbol, current_candles[symbol], timestamp)
                    
                except Exception as e:
                    logger.error(f"Error analyzing {symbol} at {timestamp}: {e}")
                    continue
        
        logger.info("=" * 70)
        logger.info("✅ BACKTEST COMPLETE!")
        logger.info(f"Total scans: {len(self.all_scans)}")
        logger.info(f"Total trades: {len(self.all_trades)}")
        logger.info("=" * 70)
        
        # Save results
        self._save_results()
    
    def _analyze_symbol(
        self,
        symbol: str,
        candles: Dict[str, pd.DataFrame],
        timestamp: pd.Timestamp
    ):
        """
        Analyze single symbol at timestamp
        
        Args:
            symbol: Trading pair
            candles: Candles dict {interval: DataFrame}
            timestamp: Current timestamp
        """
        # Skip if missing required timeframes
        if '15m' not in candles:
            return
        
        # Run indicator analysis
        analysis = self.indicator_manager.analyze_symbol(
            symbol=symbol
        )
        
        # Calculate scores
        score_long = self.scoring_engine.calculate_score(analysis, 'LONG')
        score_short = self.scoring_engine.calculate_score(analysis, 'SHORT')
        
        # Record scan
        scan_data = {
            'timestamp': timestamp,
            'symbol': symbol,
            'score_long': score_long['total_score'],
            'score_short': score_short['total_score'],
            'grade_long': score_long['grade'],
            'grade_short': score_short['grade'],
            # Add key indicator values for ML training
            'price': candles['15m']['close'].iloc[-1],
            'ema_20': analysis.get('ema_20'),
            'rsi': analysis.get('rsi'),
            'atr': analysis.get('atr'),
            # More indicators can be added here
        }
        
        self.all_scans.append(scan_data)
        
        # Check for signals (score ≥55)
        best_score = max(score_long['total_score'], score_short['total_score'])
        
        if best_score >= 55:
            direction = 'LONG' if score_long['total_score'] > score_short['total_score'] else 'SHORT'
            
            # Record signal
            signal_data = {
                'timestamp': timestamp,
                'symbol': symbol,
                'direction': direction,
                'score': best_score,
                'entry_price': candles['15m']['close'].iloc[-1],
                # Note: Full trade simulation will be added later
            }
            
            self.all_trades.append(signal_data)
            
            logger.info(
                f"Signal: {symbol} {direction} @ {timestamp} "
                f"Score: {best_score:.1f}"
            )
    
    def _save_results(self):
        """Save backtest results to files"""
        # Save scans
        scans_df = pd.DataFrame(self.all_scans)
        scans_file = os.path.join(self.output_dir, 'scans.parquet')
        scans_df.to_parquet(scans_file)
        logger.info(f"💾 Saved scans: {scans_file}")
        
        # Save trades
        if self.all_trades:
            trades_df = pd.DataFrame(self.all_trades)
            trades_file = os.path.join(self.output_dir, 'trades.parquet')
            trades_df.to_parquet(trades_file)
            logger.info(f"💾 Saved trades: {trades_file}")


if __name__ == "__main__":
    # Example usage
    engine = BacktestingEngine()
    
    symbols = [
        'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
        'DOGEUSDT', 'ADAUSDT', 'TRXUSDT', 'AVAXUSDT', 'DOTUSDT',
        'LINKUSDT', 'LTCUSDT', 'UNIUSDT', 'ATOMUSDT'
    ]
    
    # Run backtest on last month
    from datetime import timedelta
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    engine.run_backtest(symbols, start_date, end_date)
