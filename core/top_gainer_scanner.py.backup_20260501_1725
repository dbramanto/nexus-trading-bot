"""
NEXUS v2.0 - Top Gainer Scanner
Scan Binance Futures for top performing coins (meme pumps)
"""

import requests
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

class TopGainerScanner:
    """
    Scans Binance Futures for top % gainers in 24h
    Filters by volume, age, and extremes
    """
    
    def __init__(self):
        self.base_url = "https://fapi.binance.com"
    
    def get_top_gainers(
        self,
        top_n: int = 10,
        min_change: float = 15.0,
        max_change: float = 150.0,
        min_volume_usd: float = 10_000_000
    ) -> List[str]:
        """
        Fetch top N gainers from Binance Futures
        
        Args:
            top_n: Number of top gainers to return
            min_change: Minimum 24h % change
            max_change: Maximum 24h % change (filter extreme pumps)
            min_volume_usd: Minimum 24h volume in USD
        
        Returns:
            List of symbols (e.g., ['BTCUSDT', 'ETHUSDT'])
        """
        
        try:
            # Get 24h ticker data
            url = f"{self.base_url}/fapi/v1/ticker/24hr"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            tickers = response.json()
            
            gainers = []
            
            for ticker in tickers:
                symbol = ticker['symbol']
                
                # Only USDT perpetuals
                if not symbol.endswith('USDT'):
                    continue
                
                try:
                    change_pct = float(ticker['priceChangePercent'])
                    volume_usd = float(ticker['quoteVolume'])
                except (ValueError, KeyError):
                    continue
                
                # Apply filters
                if change_pct < min_change:
                    continue
                
                if change_pct > max_change:
                    logger.debug(f"Skip {symbol}: Too extreme (+{change_pct:.1f}%)")
                    continue
                
                if volume_usd < min_volume_usd:
                    continue
                
                gainers.append({
                    'symbol': symbol,
                    'change_24h': change_pct,
                    'volume_usd': volume_usd,
                    'price': float(ticker['lastPrice']),
                })
            
            # Sort by % change descending
            gainers.sort(key=lambda x: x['change_24h'], reverse=True)
            
            # Take top N
            top_gainers = gainers[:top_n]
            
            # Log results
            logger.info(f"🔍 Top {len(top_gainers)} gainers found:")
            for g in top_gainers:
                logger.info(
                    f"  {g['symbol']:12} | +{g['change_24h']:6.2f}% | "
                    f"Vol: ${g['volume_usd']/1e6:.1f}M | Price: ${g['price']}"
                )
            
            return [g['symbol'] for g in top_gainers]
        
        except Exception as e:
            logger.error(f"Error fetching top gainers: {e}")
            return []
    
    def should_refresh(self, last_refresh: datetime, interval_hours: int = 4) -> bool:
        """
        Check if symbols should be refreshed
        
        Args:
            last_refresh: Last refresh timestamp
            interval_hours: Refresh interval in hours
        
        Returns:
            True if should refresh
        """
        
        if last_refresh is None:
            return True
        
        hours_since = (datetime.now() - last_refresh).seconds / 3600
        return hours_since >= interval_hours

