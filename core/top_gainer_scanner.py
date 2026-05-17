"""
NEXUS v2.0 - Top Gainer Scanner (HYBRID: Near High + Top Gainers)
 
UPGRADE: Near 24h High = Better entry timing!
  
OLD (Top Gainers only):
  Detect coin SETELAH pump besar (+20-50%)
  Entry delay: 1-4 jam setelah breakout!
  Avg dist dari peak: 3.45% (sudah pullback!)

NEW (Near High Hybrid):
  Detect coin yang MASIH near 24h high
  = Momentum belum habis!
  = Avg dist dari peak: 0.94% (masih fresh!)
  = Entry 1-4 jam LEBIH AWAL!

AUDIT DATA (May 17, 2026):
  AIAUSDT top gainer +22% tapi dist 26.7% dari peak!
  = Nexus entry saat sudah downtrend!
  New High would catch at +5% (1-4h earlier!)
  
HYBRID LOGIC:
  Primary: Near 24h high coins (dist < 3%)
  Sorted: by % gain descending
  Fallback: Top gainers if < 10 candidates
  = Best of both worlds!
"""

import requests
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

class TopGainerScanner:
    """
    HYBRID Scanner: Near 24h High + Top Gainers fallback
    Primary: Coins still near 24h high = fresh momentum!
    Fallback: Classic top gainers if insufficient candidates
    """
    
    def __init__(self):
        self.base_url = "https://fapi.binance.com"
    
    def get_top_gainers(
        self,
        top_n: int = 20,
        min_change: float = 5.0,
        max_change: float = 150.0,
        min_volume_usd: float = 1_000_000,
        max_dist_from_high: float = 3.0,
        fallback_min_change: float = 15.0,
    ) -> List[str]:
        """
        HYBRID: Near 24h High primary, Top Gainers fallback
        
        Args:
            top_n: Number of coins to return
            min_change: Minimum 24h % change (lowered to 5%!)
            max_change: Maximum 24h % change
            min_volume_usd: Minimum 24h volume USD
            max_dist_from_high: Max % distance from 24h high
            fallback_min_change: Min change for fallback mode
        
        Returns:
            List of symbols
        """
        try:
            url = f"{self.base_url}/fapi/v1/ticker/24hr"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            tickers = response.json()
            
            near_high_coins = []
            top_gainer_coins = []
            
            for ticker in tickers:
                symbol = ticker["symbol"]
                
                if not symbol.endswith("USDT"):
                    continue
                
                try:
                    change_pct = float(ticker["priceChangePercent"])
                    volume_usd = float(ticker["quoteVolume"])
                    price = float(ticker["lastPrice"])
                    high_24h = float(ticker["highPrice"])
                    low_24h = float(ticker["lowPrice"])
                except (ValueError, KeyError):
                    continue
                
                # Basic filters
                if change_pct > max_change:
                    continue
                if volume_usd < min_volume_usd:
                    continue
                
                # Distance from 24h high
                dist_from_high = 0
                if high_24h > 0:
                    dist_from_high = (high_24h - price
                                     ) / high_24h * 100
                
                # PRIMARY: Near High candidates
                # Must be: gain > 5% AND near high < 3%
                if change_pct >= min_change and                    dist_from_high <= max_dist_from_high:
                    near_high_coins.append({
                        "symbol": symbol,
                        "change_24h": change_pct,
                        "volume_usd": volume_usd,
                        "price": price,
                        "dist_from_high": dist_from_high,
                        "mode": "NEAR_HIGH",
                    })
                
                # FALLBACK: Classic top gainers
                elif change_pct >= fallback_min_change:
                    top_gainer_coins.append({
                        "symbol": symbol,
                        "change_24h": change_pct,
                        "volume_usd": volume_usd,
                        "price": price,
                        "dist_from_high": dist_from_high,
                        "mode": "TOP_GAINER",
                    })
            
            # Sort both by % gain
            near_high_coins.sort(
                key=lambda x: x["change_24h"], reverse=True)
            top_gainer_coins.sort(
                key=lambda x: x["change_24h"], reverse=True)
            
            # HYBRID LOGIC:
            # Use near high primary
            # Fill with top gainers if < 10 candidates
            final_coins = near_high_coins[:top_n]
            
            if len(final_coins) < 10:
                # Fallback: add top gainers
                existing_syms = {c["symbol"] for c in final_coins}
                for tg in top_gainer_coins:
                    if tg["symbol"] not in existing_syms:
                        final_coins.append(tg)
                        existing_syms.add(tg["symbol"])
                    if len(final_coins) >= top_n:
                        break
                logger.info(
                    f"⚠️ Near-high candidates < 10, "
                    f"using fallback top gainers!")
            
            # Log results
            near_count = len([c for c in final_coins
                              if c["mode"]=="NEAR_HIGH"])
            tg_count = len([c for c in final_coins
                            if c["mode"]=="TOP_GAINER"])
            
            logger.info(
                f"🔍 HYBRID SCAN: "
                f"{near_count} near-high + "
                f"{tg_count} top-gainers = "
                f"{len(final_coins)} total")
            
            for c in final_coins:
                mode_flag = "🎯" if c["mode"]=="NEAR_HIGH"                            else "📈"
                logger.info(
                    f"  {mode_flag} {c['symbol']:12} | "
                    f"+{c['change_24h']:6.2f}% | "
                    f"dist:{c['dist_from_high']:.1f}% | "
                    f"Vol:${c['volume_usd']/1e6:.1f}M")
            
            return [c["symbol"] for c in final_coins]
        
        except Exception as e:
            logger.error(f"Scanner error: {e}")
            return []
    
    def should_refresh(
        self,
        last_refresh: datetime,
        interval_hours: int = 4
    ) -> bool:
        if last_refresh is None:
            return True
        hours_since = (
            datetime.now() - last_refresh
        ).seconds / 3600
        return hours_since >= interval_hours
