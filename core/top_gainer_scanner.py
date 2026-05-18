"""
NEXUS v2.0 - Near-High Scanner (LONG only)
SHORT logic = PENDING - focus LONG first!
"""
import requests, logging
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)

class TopGainerScanner:
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
        """Near 24h HIGH - LONG only!"""
        try:
            r = requests.get(
                f"{self.base_url}/fapi/v1/ticker/24hr",
                timeout=10)
            tickers = r.json()

            near_high = []
            fallback = []

            for t in tickers:
                sym = t["symbol"]
                if not sym.endswith("USDT"):
                    continue
                try:
                    change = float(t["priceChangePercent"])
                    vol = float(t["quoteVolume"])
                    price = float(t["lastPrice"])
                    high = float(t["highPrice"])
                except:
                    continue

                if change > max_change or                    vol < min_volume_usd:
                    continue

                dist = (high-price)/high*100                     if high > 0 else 999

                if change >= min_change and                    dist <= max_dist_from_high:
                    near_high.append({
                        "symbol": sym,
                        "change_24h": change,
                        "volume_usd": vol,
                        "price": price,
                        "dist_from_high": dist,
                        "mode": "NEAR_HIGH",
                    })
                elif change >= fallback_min_change                      and dist <= 10.0:
                    fallback.append({
                        "symbol": sym,
                        "change_24h": change,
                        "volume_usd": vol,
                        "price": price,
                        "dist_from_high": dist,
                        "mode": "TOP_GAINER",
                    })

            near_high.sort(
                key=lambda x: x["change_24h"],
                reverse=True)
            fallback.sort(
                key=lambda x: x["change_24h"],
                reverse=True)

            final = near_high[:top_n]
            if len(final) < 10:
                existing = {c["symbol"] for c in final}
                for fb in fallback:
                    if fb["symbol"] not in existing:
                        final.append(fb)
                        existing.add(fb["symbol"])
                    if len(final) >= top_n:
                        break

            nh = len([c for c in final
                      if c["mode"]=="NEAR_HIGH"])
            fb_c = len([c for c in final
                        if c["mode"]=="TOP_GAINER"])

            logger.info(
                f"🔍 SCAN: {nh} near-high + "
                f"{fb_c} fallback = "
                f"{len(final)} total")

            for c in final:
                flag = "🎯" if c["mode"]=="NEAR_HIGH"                        else "📈"
                logger.info(
                    f"  {flag} {c['symbol']:12} | "
                    f"+{c['change_24h']:6.2f}% | "
                    f"dist:{c['dist_from_high']:.1f}%")

            return [c["symbol"] for c in final]

        except Exception as e:
            logger.error(f"Scanner error: {e}")
            return []

    def should_refresh(self, last_refresh, interval_hours=4):
        if last_refresh is None:
            return True
        hours = (datetime.now()-last_refresh
                 ).total_seconds()/3600
        return hours >= interval_hours
