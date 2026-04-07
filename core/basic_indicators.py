"""
NEXUS Bot - Basic Technical Indicators
Calculates essential technical indicators (EMA, RSI, ATR, Volume)
"""

import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

# Setup logging
logger = logging.getLogger(__name__)


class BasicIndicators:
    """
    Calculates basic technical indicators
    - EMA (Exponential Moving Average)
    - RSI (Relative Strength Index)
    - ATR (Average True Range)
    - Volume analysis
    """
    
    def __init__(
        self,
        ema_periods: List[int] = [20, 50, 200],
        rsi_period: int = 14,
        atr_period: int = 14,
        volume_period: int = 20
    ):
        """
        Initialize basic indicators calculator
        
        Args:
            ema_periods: EMA periods to calculate
            rsi_period: RSI period
            atr_period: ATR period
            volume_period: Volume average period
        """
        self.ema_periods = ema_periods
        self.rsi_period = rsi_period
        self.atr_period = atr_period
        self.volume_period = volume_period
        
        logger.info(
            f"BasicIndicators initialized "
            f"(EMAs={ema_periods}, RSI={rsi_period}, ATR={atr_period})"
        )
    
    def calculate_all(self, candles_df: pd.DataFrame) -> Dict:
        """
        Calculate all indicators at once
        
        Args:
            candles_df: DataFrame with OHLCV data
            
        Returns:
            dict: All indicator values
        """
        result = {}
        
        # Calculate each indicator
        result['emas'] = self.calculate_emas(candles_df)
        result['rsi'] = self.calculate_rsi(candles_df)
        result['atr'] = self.calculate_atr(candles_df)
        result['volume'] = self.analyze_volume(candles_df)
        result['ma_alignment'] = self.check_ma_alignment(result['emas'])
        
        return result
    
    def calculate_emas(self, candles_df: pd.DataFrame) -> Dict[int, float]:
        """
        Calculate EMAs for all periods
        
        Args:
            candles_df: DataFrame with close prices
            
        Returns:
            dict: {period: ema_value}
        """
        emas = {}
        
        for period in self.ema_periods:
            if len(candles_df) < period:
                emas[period] = None
                continue
            
            ema = candles_df['close'].ewm(span=period, adjust=False).mean()
            emas[period] = ema.iloc[-1]
        
        return emas
    
    def calculate_rsi(self, candles_df: pd.DataFrame) -> Dict:
        """
        Calculate RSI (Relative Strength Index)
        
        Args:
            candles_df: DataFrame with close prices
            
        Returns:
            dict: RSI data
        """
        if len(candles_df) < self.rsi_period + 1:
            return {
                'value': None,
                'overbought': False,
                'oversold': False,
                'signal': 'NEUTRAL'
            }
        
        # Calculate price changes
        close = candles_df['close']
        delta = close.diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gain/loss
        avg_gain = gain.ewm(span=self.rsi_period, adjust=False).mean()
        avg_loss = loss.ewm(span=self.rsi_period, adjust=False).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        current_rsi = rsi.iloc[-1]
        
        # Interpret RSI
        overbought = current_rsi >= 70
        oversold = current_rsi <= 30
        
        if oversold:
            signal = 'OVERSOLD'
        elif overbought:
            signal = 'OVERBOUGHT'
        else:
            signal = 'NEUTRAL'
        
        return {
            'value': round(current_rsi, 2),
            'overbought': overbought,
            'oversold': oversold,
            'signal': signal
        }
    
    def calculate_atr(self, candles_df: pd.DataFrame) -> Dict:
        """
        Calculate ATR (Average True Range)
        
        Args:
            candles_df: DataFrame with OHLC data
            
        Returns:
            dict: ATR data
        """
        if len(candles_df) < self.atr_period + 1:
            return {
                'value': None,
                'percent': None
            }
        
        high = candles_df['high']
        low = candles_df['low']
        close = candles_df['close'].shift(1)
        
        # True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR = EMA of True Range
        atr = true_range.ewm(span=self.atr_period, adjust=False).mean()
        
        current_atr = atr.iloc[-1]
        current_price = candles_df['close'].iloc[-1]
        atr_percent = (current_atr / current_price) * 100
        
        return {
            'value': round(current_atr, 2),
            'percent': round(atr_percent, 2)
        }
    
    def analyze_volume(self, candles_df: pd.DataFrame) -> Dict:
        """
        Analyze volume characteristics
        
        Args:
            candles_df: DataFrame with volume data
            
        Returns:
            dict: Volume analysis
        """
        if len(candles_df) < self.volume_period:
            return {
                'current': None,
                'average': None,
                'ratio': None,
                'is_high': False
            }
        
        current_volume = candles_df['volume'].iloc[-1]
        avg_volume = candles_df['volume'].tail(self.volume_period).mean()
        
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        is_high_volume = volume_ratio >= 1.5  # 50% above average
        
        return {
            'current': round(current_volume, 2),
            'average': round(avg_volume, 2),
            'ratio': round(volume_ratio, 2),
            'is_high': is_high_volume
        }
    
    def check_ma_alignment(self, emas: Dict[int, float]) -> Dict:
        """
        Check moving average alignment (trend confirmation)
        
        Args:
            emas: EMA values from calculate_emas
            
        Returns:
            dict: Alignment analysis
        """
        # Need at least 2 EMAs
        valid_emas = {k: v for k, v in emas.items() if v is not None}
        
        if len(valid_emas) < 2:
            return {
                'aligned': False,
                'direction': 'NEUTRAL',
                'strength': 0
            }
        
        # Sort EMAs by period
        sorted_emas = sorted(valid_emas.items())
        
        # Check bullish alignment (faster > slower)
        bullish_aligned = all(
            sorted_emas[i][1] > sorted_emas[i+1][1]
            for i in range(len(sorted_emas) - 1)
        )
        
        # Check bearish alignment (faster < slower)
        bearish_aligned = all(
            sorted_emas[i][1] < sorted_emas[i+1][1]
            for i in range(len(sorted_emas) - 1)
        )
        
        if bullish_aligned:
            direction = 'BULLISH'
            aligned = True
            strength = 100
        elif bearish_aligned:
            direction = 'BEARISH'
            aligned = True
            strength = 100
        else:
            direction = 'NEUTRAL'
            aligned = False
            strength = 0
        
        return {
            'aligned': aligned,
            'direction': direction,
            'strength': strength
        }
    
    def get_trend_direction(
        self,
        candles_df: pd.DataFrame,
        ema_period: int = 20
    ) -> str:
        """
        Get simple trend direction based on price vs EMA
        
        Args:
            candles_df: DataFrame with close prices
            ema_period: EMA period to use
            
        Returns:
            str: 'BULLISH', 'BEARISH', or 'NEUTRAL'
        """
        if len(candles_df) < ema_period:
            return 'NEUTRAL'
        
        current_price = candles_df['close'].iloc[-1]
        ema = candles_df['close'].ewm(span=ema_period, adjust=False).mean().iloc[-1]
        
        if current_price > ema * 1.005:  # 0.5% above
            return 'BULLISH'
        elif current_price < ema * 0.995:  # 0.5% below
            return 'BEARISH'
        else:
            return 'NEUTRAL'


# Convenience function
def get_basic_indicators(
    ema_periods: List[int] = [20, 50, 200],
    rsi_period: int = 14
) -> BasicIndicators:
    """
    Factory function to create BasicIndicators
    
    Args:
        ema_periods: EMA periods
        rsi_period: RSI period
        
    Returns:
        BasicIndicators instance
    """
    return BasicIndicators(ema_periods, rsi_period)


if __name__ == "__main__":
    """Test basic indicators"""
    
    import os
    from datetime import datetime
    from dotenv import load_dotenv
    from execution.binance_client import get_binance_client
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("Testing Basic Indicators")
    print("=" * 70)
    
    # Load credentials
    load_dotenv()
    
    # Initialize Binance client
    print("\n[1] Initializing Binance client...")
    client = get_binance_client(testnet=False)
    print("✅ Client initialized")
    
    # Fetch BTC candles
    print("\n[2] Fetching BTC 15m candles (last 200)...")
    klines = client.get_klines('BTCUSDT', '15m', limit=200)
    
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
    print(f"✅ Fetched {len(df)} candles")
    print(f"   Latest close: ${df['close'].iloc[-1]:,.2f}")
    
    # Initialize indicators
    print("\n[3] Initializing indicators...")
    indicators = get_basic_indicators(ema_periods=[20, 50, 200])
    print("✅ Indicators initialized")
    
    # Calculate all indicators
    print("\n[4] Calculating all indicators...")
    result = indicators.calculate_all(df)
    
    print("\n✅ ALL INDICATORS CALCULATED!")
    print("\n   " + "─" * 68)
    
    # Show EMAs
    print("\n   📊 EXPONENTIAL MOVING AVERAGES:")
    for period, value in sorted(result['emas'].items()):
        if value:
            current_price = df['close'].iloc[-1]
            diff = current_price - value
            diff_percent = (diff / value) * 100
            print(f"   EMA {period:3d}: ${value:>10,.2f} (Price {diff_percent:>+6.2f}%)")
    
    # Show RSI
    rsi = result['rsi']
    print(f"\n   📈 RELATIVE STRENGTH INDEX (RSI):")
    print(f"   Value:      {rsi['value']:>6.2f}")
    print(f"   Signal:     {rsi['signal']:>10s}")
    print(f"   Overbought: {'✅ YES' if rsi['overbought'] else '❌ NO'}")
    print(f"   Oversold:   {'✅ YES' if rsi['oversold'] else '❌ NO'}")
    
    # Show ATR
    atr = result['atr']
    print(f"\n   📏 AVERAGE TRUE RANGE (ATR):")
    print(f"   Value:      ${atr['value']:>10,.2f}")
    print(f"   Percent:    {atr['percent']:>6.2f}% of price")
    
    # Show Volume
    volume = result['volume']
    print(f"\n   🔊 VOLUME ANALYSIS:")
    print(f"   Current:    {volume['current']:>15,.2f}")
    print(f"   Average:    {volume['average']:>15,.2f}")
    print(f"   Ratio:      {volume['ratio']:>6.2f}x")
    print(f"   High Vol:   {'✅ YES' if volume['is_high'] else '❌ NO'}")
    
    # Show MA Alignment
    ma_align = result['ma_alignment']
    print(f"\n   🎯 MOVING AVERAGE ALIGNMENT:")
    print(f"   Aligned:    {'✅ YES' if ma_align['aligned'] else '❌ NO'}")
    print(f"   Direction:  {ma_align['direction']:>10s}")
    print(f"   Strength:   {ma_align['strength']:>3.0f}/100")
    
    # Get trend
    trend = indicators.get_trend_direction(df, ema_period=20)
    print(f"\n   📊 OVERALL TREND (20 EMA):")
    print(f"   Direction:  {trend:>10s}")
    
    print("\n   " + "─" * 68)
    
    print("\n" + "=" * 70)
    print("✅ Basic indicators test complete!")
    print("=" * 70)