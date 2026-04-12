"""
Open Interest Module
====================

Analyzes Open Interest trends for crypto futures.

OI Analysis:
- Rising OI + Rising Price = Strong bullish (new longs)
- Rising OI + Falling Price = Strong bearish (new shorts)
- Falling OI + Rising Price = Short squeeze (weak bullish)
- Falling OI + Falling Price = Long liquidation (weak bearish)

Author: NEXUS Elite
Version: 1.0.0
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class OpenInterest:
    """Open Interest analyzer for crypto futures"""

    def __init__(self):
        """Initialize Open Interest analyzer"""
        logger.info("OpenInterest initialized (Binance Futures)")

    def analyze(
        self,
        symbol: str,
        current_price: float,
        binance_client=None
    ) -> Dict:
        """
        Analyze Open Interest trends

        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            current_price: Current price
            binance_client: Binance client instance

        Returns:
            dict: OI analysis with scoring
        """
        try:
            if binance_client is None:
                logger.warning("No Binance client provided for OI analysis")
                return self._empty_result()

            # Fetch OI history (5m intervals, last 20 periods = 100 min)
            oi_history = binance_client.get_open_interest_hist(
                symbol=symbol,
                period='5m',
                limit=20
            )

            if not oi_history or len(oi_history) < 10:
                logger.warning(f"Insufficient OI data for {symbol}")
                return self._empty_result()

            # Calculate OI trend
            oi_trend = self._calculate_oi_trend(oi_history)

            # Analyze OI vs Price relationship
            analysis = self._analyze_oi_price_relationship(
                oi_trend=oi_trend,
                oi_history=oi_history
            )

            # Generate signal
            signal = self._generate_signal(analysis)

            return {
                'oi_current': float(oi_history[-1]['sumOpenInterest']),
                'oi_change_pct': oi_trend['change_pct'],
                'oi_direction': oi_trend['direction'],
                'relationship': analysis['relationship'],
                'strength': analysis['strength'],
                'signal': signal,
                'raw_data': {
                    'oldest_oi': oi_trend['oldest_oi'],
                    'latest_oi': oi_trend['latest_oi']
                }
            }

        except Exception as e:
            logger.error(f"OI analysis error for {symbol}: {e}")
            return self._empty_result()

    def _calculate_oi_trend(self, oi_history: list) -> Dict:
        """
        Calculate OI trend from history

        Args:
            oi_history: List of OI historical data

        Returns:
            dict: OI trend analysis
        """
        oldest_oi = float(oi_history[0]['sumOpenInterest'])
        latest_oi = float(oi_history[-1]['sumOpenInterest'])

        change_pct = ((latest_oi - oldest_oi) / oldest_oi) * 100

        # Determine direction
        if change_pct > 1.0:
            direction = 'strongly_rising'
        elif change_pct > 0.3:
            direction = 'rising'
        elif change_pct < -1.0:
            direction = 'strongly_falling'
        elif change_pct < -0.3:
            direction = 'falling'
        else:
            direction = 'stable'

        return {
            'oldest_oi': oldest_oi,
            'latest_oi': latest_oi,
            'change_pct': change_pct,
            'direction': direction
        }

    def _analyze_oi_price_relationship(
        self,
        oi_trend: Dict,
        oi_history: list
    ) -> Dict:
        """
        Analyze OI vs Price relationship

        Returns:
            dict: Relationship analysis
        """
        oi_direction = oi_trend['direction']
        oi_change = oi_trend['change_pct']

        # Analyze OI + Price relationship
        # Note: We use OI direction as proxy for strength
        # Actual price direction would come from price analysis

        if oi_direction in ['rising', 'strongly_rising']:
            # Rising OI = New positions opening
            relationship = 'increasing_interest'
            strength = 'strong' if oi_change > 1.0 else 'moderate'

        elif oi_direction in ['falling', 'strongly_falling']:
            # Falling OI = Positions closing/liquidations
            relationship = 'decreasing_interest'
            strength = 'weak'

        else:
            # Stable OI = No major changes
            relationship = 'stable'
            strength = 'neutral'

        return {
            'relationship': relationship,
            'strength': strength
        }

    def _generate_signal(self, analysis: Dict) -> Dict:
        """
        Generate trading signal from OI analysis

        Args:
            analysis: OI analysis data

        Returns:
            dict: Signal with score
        """
        score = 0
        components = {}

        relationship = analysis['relationship']
        strength = analysis['strength']

        # Scoring logic
        if relationship == 'increasing_interest':
            if strength == 'strong':
                score = 5  # Strong new interest
                components['oi_trend'] = 'strong_rising'
            elif strength == 'moderate':
                score = 3  # Moderate new interest
                components['oi_trend'] = 'rising'
        elif relationship == 'decreasing_interest':
            score = -2  # Positions closing (caution)
            components['oi_trend'] = 'falling'
        else:
            score = 0  # Neutral
            components['oi_trend'] = 'stable'

        # Direction (for T0 scoring - bullish bias on rising OI)
        if relationship == 'increasing_interest':
            direction = 'bullish'  # New positions = opportunity
        elif relationship == 'decreasing_interest':
            direction = 'bearish'  # Closing positions = caution
        else:
            direction = 'neutral'

        return {
            'score': score,
            'direction': direction,
            'components': components,
            'max_score': 5
        }

    def _empty_result(self) -> Dict:
        """Return empty/neutral result"""
        return {
            'oi_current': 0,
            'oi_change_pct': 0,
            'oi_direction': 'unknown',
            'relationship': 'unknown',
            'strength': 'neutral',
            'signal': {
                'score': 0,
                'direction': 'neutral',
                'components': {},
                'max_score': 5
            },
            'raw_data': {
                'oldest_oi': 0,
                'latest_oi': 0
            }
        }


# Singleton
_oi = None


def get_open_interest() -> OpenInterest:
    """Get singleton OpenInterest instance"""
    global _oi
    if _oi is None:
        _oi = OpenInterest()
    return _oi
