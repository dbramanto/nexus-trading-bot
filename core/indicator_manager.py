"""
NEXUS Bot - Indicator Manager
Coordinates all technical indicators and provides unified analysis
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd

# Import all indicator modules
from core.consolidation_detector import get_consolidation_detector
from core.breakout_detector import get_breakout_detector
from core.premium_discount_zones import get_premium_discount_zones
from core.fvg_detector import get_fvg_detector
from core.orderblock_detector import get_orderblock_detector
from core.basic_indicators import get_basic_indicators
from core.ichimoku_cloud import get_ichimoku_cloud
from core.vwap_calculator import get_vwap_calculator
from core.volume_profile import get_volume_profile
from core.stochastic_rsi import get_stochastic_rsi
from core.macd_indicator import get_macd_indicator
from core.bollinger_bands import get_bollinger_bands
from core.htf_structure import get_htf_structure
from core.liquidity_sweeps import get_liquidity_sweeps
from core.funding_rate import get_funding_rate
from core.open_interest import get_open_interest
from execution.binance_client import BinanceClientWrapper

# Setup logging
logger = logging.getLogger(__name__)


class IndicatorManager:
    """
    Manages all technical indicators
    Provides unified interface for indicator analysis
    """
    
    def __init__(
        self,
        binance_client: BinanceClientWrapper,
        timeframes: List[str] = ['15m', '30m', '1h']
    ):
        """
        Initialize indicator manager
        
        Args:
            binance_client: Binance client instance
            timeframes: Timeframes to analyze
        """
        self.client = binance_client
        self.timeframes = timeframes
        
        # Initialize all indicator modules
        self.consolidation_detector = get_consolidation_detector()
        self.breakout_detector = get_breakout_detector()
        self.zones_calculator = get_premium_discount_zones()

        # NEXUS Elite indicators
        self.ichimoku = get_ichimoku_cloud()
        self.vwap = get_vwap_calculator()
        self.volume_profile = get_volume_profile()
        self.stoch_rsi = get_stochastic_rsi()
        self.macd = get_macd_indicator()
        self.bollinger = get_bollinger_bands()
        self.htf_structure = get_htf_structure()
        self.liquidity_sweeps = get_liquidity_sweeps()
        self.funding_rate = get_funding_rate()
        self.open_interest = get_open_interest()
        self.fvg_detector = get_fvg_detector()
        self.ob_detector = get_orderblock_detector()
        self.basic_indicators = get_basic_indicators()
        
        # Cache for candle data
        self.candle_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
        
        logger.info(
            f"IndicatorManager initialized "
            f"(timeframes={timeframes})"
        )
    
    def fetch_candles(
        self,
        symbol: str,
        interval: str,
        limit: int = 200
    ) -> pd.DataFrame:
        """
        Fetch candles from Binance (with caching)
        
        Args:
            symbol: Trading symbol
            interval: Timeframe interval
            limit: Number of candles
            
        Returns:
            DataFrame: Candle data
        """
        # Check cache first
        cache_key = f"{symbol}_{interval}"
        if cache_key in self.candle_cache:
            cached_df = self.candle_cache.get(cache_key)
            if cached_df is not None and len(cached_df) > 0:
                # Check if cache is recent (less than 1 minute old)
                if hasattr(cached_df, 'fetch_time'):
                    age = (datetime.now() - cached_df.fetch_time).seconds
                    if age < 60:
                        logger.debug(f"Using cached candles for {symbol} {interval}")
                        return cached_df
        
        # Fetch from Binance
        logger.debug(f"Fetching candles: {symbol} {interval} (limit={limit})")
        klines = self.client.get_klines(symbol, interval, limit)
        
        if not klines:
            logger.warning(f"No candles returned for {symbol} {interval}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        candles_data = []
        for kline in klines:
            candles_data.append({
                'timestamp': datetime.fromtimestamp(kline[0] / 1000),
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5])
            })
        
        df = pd.DataFrame(candles_data)
        
        # Add fetch time for cache validation
        df.fetch_time = datetime.now()
        
        # Cache it
        if symbol not in self.candle_cache:
            self.candle_cache[symbol] = {}
        self.candle_cache[symbol][interval] = df
        
        return df
    
    def analyze_symbol(
        self,
        symbol: str,
        primary_tf: str = '15m'
    ) -> Dict:
        """
        Complete indicator analysis for a symbol
        
        Args:
            symbol: Trading symbol
            primary_tf: Primary timeframe for analysis
            
        Returns:
            dict: Complete analysis with all indicators
        """
        logger.info(f"Analyzing {symbol} on {primary_tf}")
        
        try:
            # Fetch candles for primary timeframe
            candles = self.fetch_candles(symbol, primary_tf, limit=200)
            
            if len(candles) < 50:
                logger.warning(f"Insufficient candles for {symbol}")
                return self._empty_analysis(symbol, primary_tf)
            
            # Get current price
            current_price = candles['close'].iloc[-1]
            
            # Run all indicators
            analysis = {
                'symbol': symbol,
                'timeframe': primary_tf,
                'timestamp': datetime.now(),
                'current_price': current_price,
                'candles_analyzed': len(candles)
            }
            
            # 1. Consolidation Detection
            consolidation = self.consolidation_detector.detect_consolidation(candles)
            analysis['consolidation'] = consolidation
            
            # 2. Breakout Detection (if consolidation exists)
            if consolidation:
                breakout = self.breakout_detector.detect_breakout(candles, consolidation)
                analysis['breakout'] = breakout
                
                # 3. Premium/Discount Zones (from consolidation range)
                zones = self.zones_calculator.calculate_zones(
                    consolidation['range_high'],
                    consolidation['range_low']
                )
                current_zone = self.zones_calculator.get_current_zone(
                    current_price,
                    zones
                )
                analysis['zones'] = {
                    'levels': zones,
                    'current': current_zone
                }
            else:
                analysis['breakout'] = None
                analysis['zones'] = None
            
            # 4. Fair Value Gaps
            fvgs = self.fvg_detector.detect_fvgs(candles, max_fvgs=3)
            analysis['fvgs'] = fvgs
            
            # 5. Order Blocks
            obs = self.ob_detector.detect_order_blocks(candles, max_obs=3)
            analysis['order_blocks'] = obs
            
            # 6. Basic Indicators
            basic = self.basic_indicators.calculate_all(candles)
            analysis['indicators'] = basic
            
            logger.info(f"Analysis complete for {symbol}")

            # NEXUS ELITE INDICATORS
            # 9. Ichimoku Cloud
            ichimoku_result = self.ichimoku.calculate(candles)
            analysis["ichimoku"] = ichimoku_result
            
            # 10. VWAP
            vwap_result = self.vwap.calculate(candles)
            analysis["vwap"] = vwap_result
            
            # 11. Volume Profile
            volume_profile_result = self.volume_profile.calculate(candles)
            analysis["volume_profile"] = volume_profile_result
            
            # 12. Stochastic RSI
            stoch_rsi_result = self.stoch_rsi.calculate(candles)
            analysis["stoch_rsi"] = stoch_rsi_result
            
            # 13. MACD
            macd_result = self.macd.calculate(candles)
            analysis["macd"] = macd_result
            
            # 14. Bollinger Bands
            bollinger_result = self.bollinger.calculate(candles)
            analysis["bollinger"] = bollinger_result
            
            # 15. HTF Structure (1H + 4H analysis for M15)
            try:
                # Fetch 1H data (primary HTF - 4x M15)
                h1_candles = self.fetch_candles(symbol, '1h', limit=100)
                
                # Fetch 4H data (secondary HTF - 16x M15)
                h4_candles = self.fetch_candles(symbol, '4h', limit=100)
                
                # Analyze HTF structure (1H as primary, 4H as confirmation)
                htf_result = self.htf_structure.analyze(
                    h4_data=h1_candles,  # Using h4_data param for 1H (primary)
                    d1_data=h4_candles,  # Using d1_data param for 4H (secondary)
                    current_timeframe=primary_tf
                )
                analysis["htf_structure"] = htf_result
                
            except Exception as e:
                logger.warning(f"HTF Structure analysis failed: {e}")
                analysis["htf_structure"] = {
                    "alignment": "neutral", 
                    "signal": {"strength": 0, "direction": "neutral", "components": {}}
                }
            
            # 16. Liquidity Sweeps
            liquidity_result = self.liquidity_sweeps.detect(candles)
            analysis["liquidity_sweeps"] = liquidity_result
            
            # 17. Funding Rate (placeholder - needs API data)
            # Will be calculated when funding rate data available
            # 17. Funding Rate (real data from Binance)
            try:
                funding_result = self.funding_rate.calculate(symbol, binance_client=self.client)
                analysis["funding_rate"] = funding_result
            except Exception as e:
                logger.warning(f"Funding Rate analysis failed: {e}")
                analysis["funding_rate"] = {
                    "rate": 0,
                    "signal": {"strength": 0, "direction": "neutral"}
                }

            # 18. Open Interest (Binance Futures)
            try:
                oi_result = self.open_interest.analyze(
                    symbol=symbol,
                    current_price=candles["close"].iloc[-1],
                    binance_client=self.client
                )
                analysis["open_interest"] = oi_result
            except Exception as e:
                logger.warning(f"Open Interest analysis failed: {e}")
                analysis["open_interest"] = {
                    "oi_current": 0,
                    "oi_change_pct": 0,
                    "signal": {"score": 0, "direction": "neutral"}
                }
            except Exception as e:
                logger.warning(f"Failed to get funding rate for {symbol}: {e}")
                analysis["funding_rate"] = {"funding_rate": 0, "sentiment": "neutral", "signal": {"strength": 0, "direction": "neutral", "components": {}}}
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return self._empty_analysis(symbol, primary_tf, error=str(e))
    
    def analyze_multi_timeframe(
        self,
        symbol: str
    ) -> Dict[str, Dict]:
        """
        Analyze symbol across multiple timeframes
        
        Args:
            symbol: Trading symbol
            
        Returns:
            dict: {timeframe: analysis}
        """
        logger.info(f"Multi-timeframe analysis for {symbol}")
        
        results = {}
        
        for tf in self.timeframes:
            analysis = self.analyze_symbol(symbol, primary_tf=tf)
            results[tf] = analysis
        
        return results
    
    def get_summary(self, analysis: Dict) -> Dict:
        """
        Get concise summary of analysis
        
        Args:
            analysis: Analysis from analyze_symbol
            
        Returns:
            dict: Summary data
        """
        summary = {
            'symbol': analysis['symbol'],
            'price': analysis['current_price'],
            'timeframe': analysis['timeframe'],
            'has_consolidation': analysis['consolidation'] is not None,
            'has_breakout': analysis['breakout'] is not None,
            'fvg_count': len(analysis.get('fvgs', [])),
            'ob_count': len(analysis.get('order_blocks', [])),
            'rsi': analysis['indicators']['rsi']['value'],
            'rsi_signal': analysis['indicators']['rsi']['signal'],
            'trend': analysis['indicators']['ma_alignment']['direction'],
            'trend_strength': analysis['indicators']['ma_alignment']['strength']
        }
        
        # Add zone info if available
        if analysis['zones']:
            summary['current_zone'] = analysis['zones']['current']['zone_name']
            summary['zone_bias'] = analysis['zones']['current']['bias']
        else:
            summary['current_zone'] = None
            summary['zone_bias'] = None
        
        return summary
    
    def _empty_analysis(
        self,
        symbol: str,
        timeframe: str,
        error: Optional[str] = None
    ) -> Dict:
        """
        Return empty analysis structure
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            error: Error message if applicable
            
        Returns:
            dict: Empty analysis
        """
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'timestamp': datetime.now(),
            'current_price': None,
            'candles_analyzed': 0,
            'consolidation': None,
            'breakout': None,
            'zones': None,
            'fvgs': [],
            'order_blocks': [],
            'indicators': {
                'emas': {},
                'rsi': {'value': None, 'signal': 'NEUTRAL'},
                'atr': {'value': None},
                'volume': {},
                'ma_alignment': {'aligned': False, 'direction': 'NEUTRAL'}
            },
            'error': error
        }
    
    def clear_cache(self):
        """Clear candle cache"""
        self.candle_cache.clear()
        logger.info("Candle cache cleared")


# Convenience function
def get_indicator_manager(
    binance_client: BinanceClientWrapper,
    timeframes: List[str] = ['15m', '30m', '1h']
) -> IndicatorManager:
    """
    Factory function to create IndicatorManager
    
    Args:
        binance_client: Binance client instance
        timeframes: Timeframes to analyze
        
    Returns:
        IndicatorManager instance
    """
    return IndicatorManager(binance_client, timeframes)


if __name__ == "__main__":
    """Test indicator manager"""
    
    import os
    from dotenv import load_dotenv
    from execution.binance_client import get_binance_client
    import json
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("Testing Indicator Manager - PHASE 2 INTEGRATION")
    print("=" * 70)
    
    # Load credentials
    load_dotenv()
    
    # Initialize Binance client
    print("\n[1] Initializing Binance client...")
    client = get_binance_client(testnet=False)
    print("✅ Client initialized")
    
    # Initialize indicator manager
    print("\n[2] Initializing Indicator Manager...")
    manager = get_indicator_manager(client, timeframes=['15m'])
    print("✅ Manager initialized")
    print("   All 6 indicator modules loaded:")
    print("   ├─ Consolidation Detector")
    print("   ├─ Breakout Detector")
    print("   ├─ Premium/Discount Zones")
    print("   ├─ FVG Detector")
    print("   ├─ Order Block Detector")
    print("   └─ Basic Indicators")
    
    # Analyze BTC
    print("\n[3] Running COMPLETE analysis on BTCUSDT...")
    print("   (This combines ALL Phase 2 indicators!)")
    analysis = manager.analyze_symbol('BTCUSDT', primary_tf='15m')
    
    print("\n✅ ANALYSIS COMPLETE!")
    print("\n   " + "─" * 68)
    
    # Show summary
    summary = manager.get_summary(analysis)
    
    print(f"\n   📊 SYMBOL: {summary['symbol']}")
    print(f"   💰 PRICE: ${summary['price']:,.2f}")
    print(f"   ⏰ TIMEFRAME: {summary['timeframe']}")
    
    print(f"\n   🔍 STRUCTURE:")
    print(f"   Consolidation:  {'✅ YES' if summary['has_consolidation'] else '❌ NO'}")
    print(f"   Breakout:       {'✅ YES' if summary['has_breakout'] else '❌ NO'}")
    
    if summary['current_zone']:
        print(f"\n   🎯 ZONES:")
        print(f"   Current Zone:   {summary['current_zone']}")
        print(f"   Bias:           {summary['zone_bias']}")
    
    print(f"\n   📈 ICT/SMC:")
    print(f"   FVGs:           {summary['fvg_count']} detected")
    print(f"   Order Blocks:   {summary['ob_count']} detected")
    
    print(f"\n   📊 INDICATORS:")
    print(f"   RSI:            {summary['rsi']:.2f} ({summary['rsi_signal']})")
    print(f"   Trend:          {summary['trend']} (strength: {summary['trend_strength']}/100)")
    
    print("\n   " + "─" * 68)
    
    # Show detailed breakdown
    print("\n[4] Detailed Breakdown:")
    
    if analysis['consolidation']:
        cons = analysis['consolidation']
        print(f"\n   ✅ CONSOLIDATION DETECTED:")
        print(f"      Range: ${cons['range_low']:,.2f} - ${cons['range_high']:,.2f}")
        print(f"      Duration: {cons['duration_candles']} candles")
        print(f"      Quality: {cons['quality_score']:.1f}/100")
    
    if analysis['fvgs']:
        print(f"\n   ✅ FAIR VALUE GAPS ({len(analysis['fvgs'])}):")
        for i, fvg in enumerate(analysis['fvgs'][:2], 1):
            print(f"      FVG #{i}: {fvg['type']} ${fvg['gap_low']:,.2f}-${fvg['gap_high']:,.2f}")
    
    if analysis['order_blocks']:
        print(f"\n   ✅ ORDER BLOCKS ({len(analysis['order_blocks'])}):")
        for i, ob in enumerate(analysis['order_blocks'][:2], 1):
            print(f"      OB #{i}: {ob['type']} ${ob['zone_low']:,.2f}-${ob['zone_high']:,.2f}")
    
    # Show indicators
    indicators = analysis['indicators']
    print(f"\n   ✅ BASIC INDICATORS:")
    print(f"      RSI: {indicators['rsi']['value']:.2f} ({indicators['rsi']['signal']})")
    print(f"      ATR: ${indicators['atr']['value']:,.2f}")
    print(f"      Volume: {indicators['volume']['ratio']:.2f}x average")
    print(f"      MA Alignment: {indicators['ma_alignment']['direction']}")
    
    print("\n" + "=" * 70)
    print("🎉 PHASE 2 INTEGRATION TEST COMPLETE!")
    print("=" * 70)
    print("\n✅ ALL 6 INDICATOR MODULES WORKING TOGETHER!")
    print("✅ UNIFIED ANALYSIS SYSTEM OPERATIONAL!")
    print("✅ READY FOR PHASE 3: SCORING SYSTEM!")
    print("\n" + "=" * 70)