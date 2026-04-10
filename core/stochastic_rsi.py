"""
Stochastic RSI Module
=====================

Stochastic RSI combines Stochastic oscillator with RSI
for more sensitive overbought/oversold detection.

Formula:
StochRSI = (RSI - RSI_low) / (RSI_high - RSI_low)
where RSI_low/high are min/max RSI over period

Range: 0-100 (or 0-1)
Overbought: >80
Oversold: <20

Author: NEXUS Elite
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class StochasticRSI:
    """Stochastic RSI calculator for momentum analysis"""
    
    def __init__(
        self,
        rsi_period: int = 14,
        stoch_period: int = 14,
        smooth_k: int = 3,
        smooth_d: int = 3,
        overbought: float = 80,
        oversold: float = 20
    ):
        """
        Initialize Stochastic RSI
        
        Args:
            rsi_period: RSI calculation period (default 14)
            stoch_period: Stochastic period (default 14)
            smooth_k: %K smoothing (default 3)
            smooth_d: %D smoothing (default 3)
            overbought: Overbought threshold (default 80)
            oversold: Oversold threshold (default 20)
        """
        self.rsi_period = rsi_period
        self.stoch_period = stoch_period
        self.smooth_k = smooth_k
        self.smooth_d = smooth_d
        self.overbought = overbought
        self.oversold = oversold
        
        logger.info(
            f"StochasticRSI initialized "
            f"(RSI={rsi_period}, Stoch={stoch_period}, "
            f"OB={overbought}, OS={oversold})"
        )
    
    def calculate(self, df: pd.DataFrame) -> Dict:
        """
        Calculate Stochastic RSI
        
        Args:
            df: DataFrame with close prices
            
        Returns:
            dict: StochRSI values and signals
        """
        try:
            min_bars = self.rsi_period + self.stoch_period + 10
            if len(df) < min_bars:
                logger.warning(
                    f"Insufficient data for StochRSI "
                    f"(need {min_bars}, got {len(df)})"
                )
                return self._empty_result()
            
            # Calculate RSI first
            rsi = self._calculate_rsi(df['close'])
            
            # Calculate Stochastic of RSI
            stoch_rsi = self._calculate_stochastic(rsi, self.stoch_period)
            
            # Smooth %K
            k_line = stoch_rsi.rolling(window=self.smooth_k).mean()
            
            # Smooth %D
            d_line = k_line.rolling(window=self.smooth_d).mean()
            
            # Current values
            current_k = k_line.iloc[-1]
            current_d = d_line.iloc[-1]
            
            # Determine state
            if current_k > self.overbought:
                state = 'overbought'
            elif current_k < self.oversold:
                state = 'oversold'
            else:
                state = 'neutral'
            
            # Check for crosses
            kd_cross = self._check_cross(k_line, d_line)
            
            # Check for divergence (basic)
            divergence = self._check_divergence(df['close'], stoch_rsi)
            
            result = {
                'k_line': current_k,
                'd_line': current_d,
                'rsi': rsi.iloc[-1],
                'state': state,
                'kd_cross': kd_cross,
                'divergence': divergence,
                'momentum': 'bullish' if current_k > current_d else 'bearish'
            }
            
            # Generate signal
            result['signal'] = self._generate_signal(result)
            
            return result
            
        except Exception as e:
            logger.error(f"StochRSI calculation error: {e}")
            return self._empty_result()
    
    def _calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_stochastic(self, series: pd.Series, period: int) -> pd.Series:
        """Calculate Stochastic oscillator"""
        min_val = series.rolling(window=period).min()
        max_val = series.rolling(window=period).max()
        stoch = ((series - min_val) / (max_val - min_val)) * 100
        return stoch
    
    def _check_cross(self, k: pd.Series, d: pd.Series) -> str:
        """Check for %K/%D cross"""
        if len(k) < 2 or len(d) < 2:
            return 'none'
        
        k_above = k.iloc[-1] > d.iloc[-1]
        k_above_prev = k.iloc[-2] > d.iloc[-2]
        
        if k_above and not k_above_prev:
            return 'bullish'
        elif not k_above and k_above_prev:
            return 'bearish'
        return 'none'
    
    def _check_divergence(self, price: pd.Series, stoch: pd.Series) -> str:
        """Simple divergence detection"""
        if len(price) < 20 or len(stoch) < 20:
            return 'none'
        
        # Check last 10 candles
        price_trend = price.iloc[-10:].is_monotonic_increasing
        stoch_trend = stoch.iloc[-10:].is_monotonic_increasing
        
        # Bullish divergence: price down, stoch up
        if not price_trend and stoch_trend:
            return 'bullish'
        # Bearish divergence: price up, stoch down
        elif price_trend and not stoch_trend:
            return 'bearish'
        
        return 'none'
    
    def _generate_signal(self, data: Dict) -> Dict:
        """Generate trading signal"""
        strength = 0
        components = {}
        
        # Component 1: Overbought/Oversold (+2/-2)
        if data['state'] == 'oversold':
            strength += 2
            components['state'] = 'oversold_bounce'
        elif data['state'] == 'overbought':
            strength -= 2
            components['state'] = 'overbought_reversal'
        
        # Component 2: K/D Cross (+2/-2)
        if data['kd_cross'] == 'bullish':
            strength += 2
            components['cross'] = 'bullish'
        elif data['kd_cross'] == 'bearish':
            strength -= 2
            components['cross'] = 'bearish'
        
        # Component 3: Divergence (+1/-1)
        if data['divergence'] == 'bullish':
            strength += 1
            components['divergence'] = 'bullish'
        elif data['divergence'] == 'bearish':
            strength -= 1
            components['divergence'] = 'bearish'
        
        # Direction
        if strength >= 2:
            direction = 'long'
        elif strength <= -2:
            direction = 'short'
        else:
            direction = 'neutral'
        
        return {
            'strength': strength,
            'direction': direction,
            'components': components
        }
    
    def _empty_result(self) -> Dict:
        """Return empty result"""
        return {
            'k_line': 50,
            'd_line': 50,
            'rsi': 50,
            'state': 'neutral',
            'kd_cross': 'none',
            'divergence': 'none',
            'momentum': 'neutral',
            'signal': {
                'strength': 0,
                'direction': 'neutral',
                'components': {}
            }
        }


# Singleton
_stoch_rsi = None

def get_stochastic_rsi() -> StochasticRSI:
    """Get singleton StochasticRSI instance"""
    global _stoch_rsi
    if _stoch_rsi is None:
        _stoch_rsi = StochasticRSI()
    return _stoch_rsi
