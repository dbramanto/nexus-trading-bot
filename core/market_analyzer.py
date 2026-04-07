"""
Market Analyzer
Analyzes overall market conditions and generates insights
"""

import logging
from typing import Dict, List, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """Analyze market conditions across all scanned symbols"""
    
    def __init__(self):
        logger.info("MarketAnalyzer initialized")
    
    def analyze_market_condition(self, scan_results: List[Dict]) -> Dict:
        """
        Analyze overall market condition from scan results
        
        Args:
            scan_results: List of scan results with scores and analysis
            
        Returns:
            dict: Market condition analysis
        """
        if not scan_results:
            return self._empty_analysis()
        
        # Extract scores
        scores = []
        for result in scan_results:
            if result.get('best_score'):
                scores.append(result['best_score'])
        
        if not scores:
            return self._empty_analysis()
        
        # Calculate statistics
        avg_score = np.mean(scores)
        max_score = max(scores)
        min_score = min(scores)
        
        # Determine trend (simplified - based on avg score range)
        trend = self._determine_trend(avg_score, scores)
        
        # Determine volatility (based on score variance)
        volatility = self._determine_volatility(scores)
        
        # Determine confluence strength
        confluence = self._determine_confluence(avg_score)
        
        # Generate insight
        insight = self._generate_insight(trend, volatility, confluence, max_score)
        
        return {
            'avg_score': avg_score,
            'max_score': max_score,
            'min_score': min_score,
            'trend': trend,
            'volatility': volatility,
            'confluence': confluence,
            'insight': insight
        }
    
    def _determine_trend(self, avg_score: float, scores: List[float]) -> str:
        """Determine market trend based on scores"""
        # Simplified trend detection
        # In reality, would use actual EMA/price data
        
        if avg_score > 35:
            return "Trending"
        elif avg_score > 25:
            return "Mixed"
        else:
            return "Ranging"
    
    def _determine_volatility(self, scores: List[float]) -> str:
        """Determine volatility based on score variance"""
        std = np.std(scores)
        
        if std > 8:
            return "High"
        elif std > 4:
            return "Medium"
        else:
            return "Low"
    
    def _determine_confluence(self, avg_score: float) -> str:
        """Determine confluence strength"""
        if avg_score > 40:
            return "Strong"
        elif avg_score > 25:
            return "Moderate"
        else:
            return "Weak"
    
    def _generate_insight(self, trend: str, volatility: str, 
                         confluence: str, max_score: float) -> str:
        """Generate actionable insight based on conditions"""
        insights = []
        
        # Trend insights
        if trend == "Ranging":
            insights.append("Market consolidating")
        elif trend == "Trending":
            insights.append("Directional movement detected")
        
        # Score insights
        if max_score < 45:
            insights.append("No quality setups")
        elif max_score < 55:
            insights.append("Watch for threshold break")
        else:
            insights.append("Signal detected!")
        
        # Volatility insights
        if volatility == "Low":
            insights.append("Wait for breakout")
        elif volatility == "High":
            insights.append("Active price action")
        
        # Confluence insights
        if confluence == "Weak":
            insights.append("Patience required")
        
        return " • ".join(insights) if insights else "Monitoring market"
    
    def _empty_analysis(self) -> Dict:
        """Return empty analysis when no data"""
        return {
            'avg_score': 0,
            'max_score': 0,
            'min_score': 0,
            'trend': 'Unknown',
            'volatility': 'Unknown',
            'confluence': 'Unknown',
            'insight': 'No scan data available'
        }
