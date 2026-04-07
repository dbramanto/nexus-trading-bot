"""
NEXUS Bot - Universe Scanner
Scans multiple trading symbols and ranks opportunities
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import time

from execution.binance_client import BinanceClientWrapper
from core.indicator_manager import IndicatorManager
from core.scoring_engine import ScoringEngine

# Setup logging
logger = logging.getLogger(__name__)


class UniverseScanner:
    """
    Scans multiple symbols and ranks trading opportunities
    
    Features:
    - Multi-symbol scanning
    - Volume/liquidity filtering
    - Opportunity ranking by score
    - Top N selection
    """
    
    def __init__(
        self,
        binance_client: BinanceClientWrapper,
        indicator_manager: IndicatorManager,
        scoring_engine: ScoringEngine,
        min_volume_24h: float = 100_000_000,  # $100M
        min_price: float = 1.0,
        max_symbols: int = 50
    ):
        """
        Initialize universe scanner
        
        Args:
            binance_client: Binance client
            indicator_manager: Indicator manager
            scoring_engine: Scoring engine
            min_volume_24h: Minimum 24h volume (USDT)
            min_price: Minimum price
            max_symbols: Maximum symbols to scan
        """
        self.client = binance_client
        self.indicator_manager = indicator_manager
        self.scoring_engine = scoring_engine
        self.min_volume_24h = min_volume_24h
        self.min_price = min_price
        self.max_symbols = max_symbols
        
        logger.info(
            f"UniverseScanner initialized "
            f"(min_volume=${min_volume_24h:,.0f}, max_symbols={max_symbols})"
        )
    
    def get_filtered_universe(self) -> List[str]:
        """
        Get filtered list of tradeable symbols
        
        Filters:
        - USDT pairs only
        - Volume > min_volume_24h
        - Price > min_price
        - Active trading
        
        Returns:
            list: Filtered symbol list
        """
        logger.info("Fetching symbol universe...")
        
        # Get all USDT futures pairs
        all_symbols = self.client.get_futures_symbols()
        
        # Filter symbols
        filtered = []
        
        for symbol in all_symbols[:self.max_symbols * 2]:  # Get extra for filtering
            try:
                # Get 24h ticker
                ticker = self.client.get_24h_ticker(symbol)
                
                if not ticker:
                    continue
                
                # Extract data
                volume_24h = float(ticker.get('quoteVolume', 0))
                last_price = float(ticker.get('lastPrice', 0))
                
                # Apply filters
                if volume_24h < self.min_volume_24h:
                    continue
                
                if last_price < self.min_price:
                    continue
                
                filtered.append(symbol)
                
                # Stop if we have enough
                if len(filtered) >= self.max_symbols:
                    break
                    
            except Exception as e:
                logger.debug(f"Error filtering {symbol}: {e}")
                continue
        
        logger.info(f"Filtered universe: {len(filtered)} symbols")
        return filtered
    
    def scan_symbol(
        self,
        symbol: str,
        timeframe: str = '15m'
    ) -> Optional[Dict]:
        """
        Scan a single symbol and calculate score
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe for analysis
            
        Returns:
            dict: Scan result or None
        """
        try:
            # Analyze symbol
            analysis = self.indicator_manager.analyze_symbol(symbol, timeframe)
            
            # Calculate scores
            long_score = self.scoring_engine.calculate_score(analysis, 'LONG')
            short_score = self.scoring_engine.calculate_score(analysis, 'SHORT')
            
            # Determine best direction
            if long_score['total_score'] > short_score['total_score']:
                best_score = long_score
                direction = 'LONG'
            else:
                best_score = short_score
                direction = 'SHORT'
            
            result = {
                'symbol': symbol,
                'timeframe': timeframe,
                'direction': direction,
                'score': best_score['total_score'],
                'grade': best_score['grade'],
                'long_score': long_score['total_score'],
                'short_score': short_score['total_score'],
                'current_price': analysis['current_price'],
                'has_consolidation': analysis.get('consolidation') is not None,
                'scanned_at': datetime.now()
            }
            
            logger.debug(
                f"Scanned {symbol}: {direction} {result['score']:.1f} ({result['grade']})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")
            return None
    
    def scan_universe(
        self,
        symbols: Optional[List[str]] = None,
        timeframe: str = '15m',
        min_score: float = 55.0
    ) -> List[Dict]:
        """
        Scan multiple symbols and rank opportunities
        
        Args:
            symbols: List of symbols (None = use filtered universe)
            timeframe: Timeframe for analysis
            min_score: Minimum score to include
            
        Returns:
            list: Ranked opportunities (best first)
        """
        logger.info("Starting universe scan...")
        
        # Get symbols if not provided
        if symbols is None:
            symbols = self.get_filtered_universe()
        
        logger.info(f"Scanning {len(symbols)} symbols on {timeframe}...")
        
        results = []
        
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"[{i}/{len(symbols)}] Scanning {symbol}...")
            
            result = self.scan_symbol(symbol, timeframe)
            
            if result and result['score'] >= min_score:
                results.append(result)
                logger.info(
                    f"  ✅ {symbol}: {result['direction']} "
                    f"{result['score']:.1f} ({result['grade']})"
                )
            elif result:
                logger.info(f"  ⏭️  {symbol}: Score {result['score']:.1f} (below threshold)")
            
            # Small delay to avoid rate limits
            time.sleep(0.1)
        
        # Sort by score (highest first)
        results.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(
            f"Scan complete: {len(results)} opportunities found "
            f"(from {len(symbols)} symbols scanned)"
        )
        
        return results
    
    def get_top_opportunities(
        self,
        count: int = 5,
        timeframe: str = '15m',
        min_score: float = 55.0
    ) -> List[Dict]:
        """
        Get top N trading opportunities
        
        Args:
            count: Number of top opportunities to return
            timeframe: Timeframe for analysis
            min_score: Minimum score threshold
            
        Returns:
            list: Top opportunities
        """
        # Scan universe
        all_opportunities = self.scan_universe(
            symbols=None,
            timeframe=timeframe,
            min_score=min_score
        )
        
        # Return top N
        return all_opportunities[:count]
    
    def format_opportunities_table(
        self,
        opportunities: List[Dict]
    ) -> str:
        """
        Format opportunities as a table
        
        Args:
            opportunities: List of opportunities
            
        Returns:
            str: Formatted table
        """
        if not opportunities:
            return "No opportunities found"
        
        lines = []
        lines.append("=" * 80)
        lines.append("TRADING OPPORTUNITIES (Ranked by Score)")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"{'Rank':<6} {'Symbol':<12} {'Dir':<6} {'Score':<8} {'Grade':<10} {'Price':<12}")
        lines.append("-" * 80)
        
        for i, opp in enumerate(opportunities, 1):
            lines.append(
                f"{i:<6} "
                f"{opp['symbol']:<12} "
                f"{opp['direction']:<6} "
                f"{opp['score']:>6.1f}  "
                f"{opp['grade']:<10} "
                f"${opp['current_price']:>10,.2f}"
            )
        
        lines.append("=" * 80)
        
        return "\n".join(lines)


# Convenience function
def get_universe_scanner(
    binance_client: BinanceClientWrapper,
    indicator_manager: IndicatorManager,
    scoring_engine: ScoringEngine,
    max_symbols: int = 50
) -> UniverseScanner:
    """
    Factory function to create UniverseScanner
    
    Args:
        binance_client: Binance client
        indicator_manager: Indicator manager
        scoring_engine: Scoring engine
        max_symbols: Maximum symbols to scan
        
    Returns:
        UniverseScanner instance
    """
    return UniverseScanner(
        binance_client,
        indicator_manager,
        scoring_engine,
        max_symbols=max_symbols
    )


if __name__ == "__main__":
    """Test universe scanner"""
    
    import os
    from dotenv import load_dotenv
    from execution.binance_client import get_binance_client
    from core.indicator_manager import get_indicator_manager
    from core.scoring_engine import get_scoring_engine
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("Testing Universe Scanner")
    print("=" * 70)
    
    # Load credentials
    load_dotenv()
    
    # Initialize components
    print("\n[1] Initializing components...")
    
    client = get_binance_client(testnet=False)
    indicator_manager = get_indicator_manager(client)
    scoring_engine = get_scoring_engine()
    
    scanner = get_universe_scanner(
        client,
        indicator_manager,
        scoring_engine,
        max_symbols=10  # Scan only 10 symbols for testing
    )
    
    print("✅ Components initialized")
    
    # Test with specific symbols
    print("\n[2] Testing with specific symbols...")
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
    
    results = scanner.scan_universe(
        symbols=test_symbols,
        timeframe='15m',
        min_score=0  # Include all scores for testing
    )
    
    print(f"\n✅ Scanned {len(test_symbols)} symbols")
    
    # Display results
    print("\n" + "=" * 70)
    print("SCAN RESULTS")
    print("=" * 70)
    
    if results:
        print(scanner.format_opportunities_table(results))
    else:
        print("\n❌ No opportunities found")
    
    # Show detailed breakdown for best opportunity
    if results:
        best = results[0]
        print("\n" + "=" * 70)
        print("BEST OPPORTUNITY DETAILS")
        print("=" * 70)
        print(f"\nSymbol:        {best['symbol']}")
        print(f"Direction:     {best['direction']}")
        print(f"Score:         {best['score']:.1f}/100")
        print(f"Grade:         {best['grade']}")
        print(f"LONG Score:    {best['long_score']:.1f}")
        print(f"SHORT Score:   {best['short_score']:.1f}")
        print(f"Price:         ${best['current_price']:,.2f}")
        print(f"Consolidation: {'YES' if best['has_consolidation'] else 'NO'}")
    
    print("\n" + "=" * 70)
    print("✅ Universe scanner test complete!")
    print("=" * 70)
    print("\n💡 This scanner can find the best trading opportunities")
    print("   across multiple symbols automatically!")