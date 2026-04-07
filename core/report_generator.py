"""
NEXUS Report Generator
Generates daily, weekly, and monthly trading reports
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate trading performance reports"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.reports_dir = self.data_dir / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        self.daily_reports_file = self.reports_dir / "daily_reports.json"
        self.weekly_reports_file = self.reports_dir / "weekly_reports.json"
        self.monthly_reports_file = self.reports_dir / "monthly_reports.json"
        
        logger.info("ReportGenerator initialized")
    
    def generate_daily_report(self, session_data: Dict) -> Dict:
        """
        Generate daily report from session data
        
        Args:
            session_data: Today's session data
            
        Returns:
            dict: Daily report
        """
        report = {
            'date': session_data.get('date', 'N/A'),
            'start_balance': session_data.get('start_balance', 0),
            'end_balance': session_data.get('balance', 0),
            'pnl': session_data.get('pnl', 0),
            'pnl_percent': session_data.get('pnl_percent', 0),
            'trades': session_data.get('trades', 0),
            'wins': session_data.get('wins', 0),
            'losses': session_data.get('losses', 0),
            'win_rate': session_data.get('win_rate', 0),
            'scans': session_data.get('scans', 0),
            'signals': session_data.get('signals', 0),
            'best_score': session_data.get('best_score', 0),
            'best_symbol': session_data.get('best_symbol', 'N/A'),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Save to file
        self._save_daily_report(report)
        
        logger.info(f"Daily report generated for {report['date']}")
        return report
    
    def generate_weekly_report(self) -> Dict:
        """
        Generate weekly report from last 7 daily reports
        
        Returns:
            dict: Weekly report
        """
        daily_reports = self._load_daily_reports()
        
        if not daily_reports:
            logger.warning("No daily reports found for weekly report")
            return {}
        
        # Get last 7 days
        recent_reports = daily_reports[-7:]
        
        # Aggregate data
        total_pnl = sum(r.get('pnl', 0) for r in recent_reports)
        total_trades = sum(r.get('trades', 0) for r in recent_reports)
        total_wins = sum(r.get('wins', 0) for r in recent_reports)
        total_losses = sum(r.get('losses', 0) for r in recent_reports)
        total_scans = sum(r.get('scans', 0) for r in recent_reports)
        total_signals = sum(r.get('signals', 0) for r in recent_reports)
        
        start_balance = recent_reports[0].get('start_balance', 0) if recent_reports else 0
        end_balance = recent_reports[-1].get('end_balance', 0) if recent_reports else 0
        
        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        pnl_percent = ((end_balance - start_balance) / start_balance * 100) if start_balance > 0 else 0
        
        # Find best day
        best_day = max(recent_reports, key=lambda x: x.get('pnl', 0)) if recent_reports else {}
        worst_day = min(recent_reports, key=lambda x: x.get('pnl', 0)) if recent_reports else {}
        
        report = {
            'week_start': recent_reports[0].get('date', 'N/A') if recent_reports else 'N/A',
            'week_end': recent_reports[-1].get('date', 'N/A') if recent_reports else 'N/A',
            'days_count': len(recent_reports),
            'start_balance': start_balance,
            'end_balance': end_balance,
            'total_pnl': total_pnl,
            'pnl_percent': pnl_percent,
            'total_trades': total_trades,
            'total_wins': total_wins,
            'total_losses': total_losses,
            'win_rate': win_rate,
            'total_scans': total_scans,
            'total_signals': total_signals,
            'best_day': {
                'date': best_day.get('date', 'N/A'),
                'pnl': best_day.get('pnl', 0)
            },
            'worst_day': {
                'date': worst_day.get('date', 'N/A'),
                'pnl': worst_day.get('pnl', 0)
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Save to file
        self._save_weekly_report(report)
        
        logger.info(f"Weekly report generated for {report['week_start']} to {report['week_end']}")
        return report
    
    def generate_monthly_report(self) -> Dict:
        """
        Generate monthly report from weekly reports
        
        Returns:
            dict: Monthly report
        """
        weekly_reports = self._load_weekly_reports()
        
        if not weekly_reports:
            logger.warning("No weekly reports found for monthly report")
            return {}
        
        # Get last 4-5 weeks
        recent_reports = weekly_reports[-5:]
        
        # Aggregate data
        total_pnl = sum(r.get('total_pnl', 0) for r in recent_reports)
        total_trades = sum(r.get('total_trades', 0) for r in recent_reports)
        total_wins = sum(r.get('total_wins', 0) for r in recent_reports)
        total_losses = sum(r.get('total_losses', 0) for r in recent_reports)
        
        start_balance = recent_reports[0].get('start_balance', 0) if recent_reports else 0
        end_balance = recent_reports[-1].get('end_balance', 0) if recent_reports else 0
        
        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        pnl_percent = ((end_balance - start_balance) / start_balance * 100) if start_balance > 0 else 0
        
        # Find best week
        best_week = max(recent_reports, key=lambda x: x.get('total_pnl', 0)) if recent_reports else {}
        worst_week = min(recent_reports, key=lambda x: x.get('total_pnl', 0)) if recent_reports else {}
        
        report = {
            'month_start': recent_reports[0].get('week_start', 'N/A') if recent_reports else 'N/A',
            'month_end': recent_reports[-1].get('week_end', 'N/A') if recent_reports else 'N/A',
            'weeks_count': len(recent_reports),
            'start_balance': start_balance,
            'end_balance': end_balance,
            'total_pnl': total_pnl,
            'pnl_percent': pnl_percent,
            'total_trades': total_trades,
            'total_wins': total_wins,
            'total_losses': total_losses,
            'win_rate': win_rate,
            'best_week': {
                'period': f"{best_week.get('week_start', 'N/A')} - {best_week.get('week_end', 'N/A')}",
                'pnl': best_week.get('total_pnl', 0)
            },
            'worst_week': {
                'period': f"{worst_week.get('week_start', 'N/A')} - {worst_week.get('week_end', 'N/A')}",
                'pnl': worst_week.get('total_pnl', 0)
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Save to file
        self._save_monthly_report(report)
        
        logger.info(f"Monthly report generated for {report['month_start']} to {report['month_end']}")
        return report
    
    def _save_daily_report(self, report: Dict):
        """Save daily report to file"""
        reports = self._load_daily_reports()
        reports.append(report)
        
        with open(self.daily_reports_file, 'w') as f:
            json.dump(reports, f, indent=2)
    
    def _save_weekly_report(self, report: Dict):
        """Save weekly report to file"""
        reports = self._load_weekly_reports()
        reports.append(report)
        
        with open(self.weekly_reports_file, 'w') as f:
            json.dump(reports, f, indent=2)
    
    def _save_monthly_report(self, report: Dict):
        """Save monthly report to file"""
        reports = self._load_monthly_reports()
        reports.append(report)
        
        with open(self.monthly_reports_file, 'w') as f:
            json.dump(reports, f, indent=2)
    
    def _load_daily_reports(self) -> List[Dict]:
        """Load daily reports from file"""
        if not self.daily_reports_file.exists():
            return []
        
        with open(self.daily_reports_file, 'r') as f:
            return json.load(f)
    
    def _load_weekly_reports(self) -> List[Dict]:
        """Load weekly reports from file"""
        if not self.weekly_reports_file.exists():
            return []
        
        with open(self.weekly_reports_file, 'r') as f:
            return json.load(f)
    
    def _load_monthly_reports(self) -> List[Dict]:
        """Load monthly reports from file"""
        if not self.monthly_reports_file.exists():
            return []
        
        with open(self.monthly_reports_file, 'r') as f:
            return json.load(f)
