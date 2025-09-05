from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from collections import Counter
import logging

from app.repo import DatabaseRepository
from app.models import ReportSummary

logger = logging.getLogger(__name__)


class ReportingService:
    def __init__(self, db_repo: DatabaseRepository):
        self.db = db_repo
    
    async def generate_daily_report(self) -> ReportSummary:
        """Generate daily report for the last 24 hours."""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=1)
        
        return await self._generate_report(start_time, end_time)
    
    async def generate_weekly_report(self) -> ReportSummary:
        """Generate weekly report for the last 7 days."""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=7)
        
        return await self._generate_report(start_time, end_time)
    
    async def _generate_report(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> ReportSummary:
        """Generate report for specified time period."""
        
        async with self.db.pool.acquire() as conn:
            # Get job statistics
            job_stats = await self._get_job_statistics(conn, start_time, end_time)
            
            # Get match statistics
            match_stats = await self._get_match_statistics(conn, start_time, end_time)
            
            # Get top consultants
            top_consultants = await self._get_top_consultants(conn, start_time, end_time)
            
            # Get top skills
            top_skills = await self._get_top_skills(conn, start_time, end_time)
            
            # Get source breakdown
            sources_breakdown = await self._get_sources_breakdown(conn, start_time, end_time)
            
            return ReportSummary(
                period_start=start_time,
                period_end=end_time,
                total_jobs=job_stats['total'],
                new_jobs=job_stats['new'],
                total_matches=match_stats['total'],
                high_quality_matches=match_stats['high_quality'],
                top_consultants=top_consultants,
                top_skills=top_skills,
                sources_breakdown=sources_breakdown
            )
    
    async def _get_job_statistics(
        self,
        conn,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, int]:
        """Get job statistics for the period."""
        
        # Total jobs
        total_query = """
            SELECT COUNT(*) as count
            FROM jobs
            WHERE scraped_at >= $1 AND scraped_at < $2
        """
        total_result = await conn.fetchrow(total_query, start_time, end_time)
        
        # New jobs (created in period)
        new_query = """
            SELECT COUNT(*) as count
            FROM jobs
            WHERE scraped_at >= $1 AND scraped_at < $2
        """
        new_result = await conn.fetchrow(new_query, start_time, end_time)
        
        return {
            'total': total_result['count'],
            'new': new_result['count']
        }
    
    async def _get_match_statistics(
        self,
        conn,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, int]:
        """Get match statistics for the period."""
        
        # Total matches
        total_query = """
            SELECT COUNT(*) as count
            FROM job_consultant_matches
            WHERE created_at >= $1 AND created_at < $2
        """
        total_result = await conn.fetchrow(total_query, start_time, end_time)
        
        # High quality matches (score >= 0.8)
        high_quality_query = """
            SELECT COUNT(*) as count
            FROM job_consultant_matches
            WHERE created_at >= $1 AND created_at < $2
            AND score >= 0.8
        """
        high_quality_result = await conn.fetchrow(high_quality_query, start_time, end_time)
        
        return {
            'total': total_result['count'],
            'high_quality': high_quality_result['count']
        }
    
    async def _get_top_consultants(
        self,
        conn,
        start_time: datetime,
        end_time: datetime,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get top performing consultants for the period."""
        
        query = """
            SELECT 
                c.consultant_id,
                c.name,
                c.role,
                COUNT(m.job_id) as match_count,
                AVG(m.score) as avg_score,
                MAX(m.score) as max_score
            FROM consultants c
            JOIN job_consultant_matches m ON c.consultant_id = m.consultant_id
            WHERE m.created_at >= $1 AND m.created_at < $2
            GROUP BY c.consultant_id, c.name, c.role
            ORDER BY match_count DESC, avg_score DESC
            LIMIT $3
        """
        
        results = await conn.fetch(query, start_time, end_time, limit)
        
        return [
            {
                'id': str(row['consultant_id']),
                'name': row['name'],
                'title': row['role'],
                'match_count': row['match_count'],
                'avg_score': float(row['avg_score']) if row['avg_score'] else 0,
                'max_score': float(row['max_score']) if row['max_score'] else 0
            }
            for row in results
        ]
    
    async def _get_top_skills(
        self,
        conn,
        start_time: datetime,
        end_time: datetime,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get most demanded skills for the period."""
        
        query = """
            SELECT skills
            FROM jobs
            WHERE scraped_at >= $1 AND scraped_at < $2
            AND skills IS NOT NULL
        """
        
        results = await conn.fetch(query, start_time, end_time)
        
        # Count skill occurrences
        skill_counter = Counter()
        for row in results:
            if row['skills']:
                for skill in row['skills']:
                    skill_counter[skill] += 1
        
        # Get top skills
        top_skills = skill_counter.most_common(limit)
        
        return [
            {'skill': skill, 'count': count}
            for skill, count in top_skills
        ]
    
    async def _get_sources_breakdown(
        self,
        conn,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, int]:
        """Get job counts by source for the period."""
        
        query = """
            SELECT source, COUNT(*) as count
            FROM jobs
            WHERE scraped_at >= $1 AND scraped_at < $2
            GROUP BY source
            ORDER BY count DESC
        """
        
        results = await conn.fetch(query, start_time, end_time)
        
        return {row['source']: row['count'] for row in results}
    
    def format_slack_message(self, report: ReportSummary) -> Dict[str, Any]:
        """Format report as Slack message."""
        
        period_str = f"{report.period_start.strftime('%Y-%m-%d')} to {report.period_end.strftime('%Y-%m-%d')}"
        
        # Build message blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 Consultant Matching Report"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Period:* {period_str}"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*New Jobs:*\n{report.new_jobs}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Matches:*\n{report.total_matches}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*High Quality Matches:*\n{report.high_quality_matches}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Match Rate:*\n{(report.high_quality_matches/report.total_matches*100):.1f}%" if report.total_matches > 0 else "*Match Rate:*\n0%"
                    }
                ]
            }
        ]
        
        # Add top consultants
        if report.top_consultants:
            consultant_text = "*Top Consultants:*\n"
            for i, consultant in enumerate(report.top_consultants[:3], 1):
                consultant_text += f"{i}. {consultant['name']} - {consultant['match_count']} matches (avg: {consultant['avg_score']:.2f})\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": consultant_text
                }
            })
        
        # Add top skills
        if report.top_skills:
            skills_text = "*Most Demanded Skills:*\n"
            skills_list = ", ".join([f"{s['skill']} ({s['count']})" for s in report.top_skills[:5]])
            skills_text += skills_list
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": skills_text
                }
            })
        
        return {
            "blocks": blocks,
            "text": f"Consultant Matching Report for {period_str}"
        }
    
    def format_teams_message(self, report: ReportSummary) -> Dict[str, Any]:
        """Format report as Microsoft Teams adaptive card."""
        
        period_str = f"{report.period_start.strftime('%Y-%m-%d')} to {report.period_end.strftime('%Y-%m-%d')}"
        
        card = {
            "type": "AdaptiveCard",
            "version": "1.0",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "📊 Consultant Matching Report",
                    "weight": "bolder",
                    "size": "large"
                },
                {
                    "type": "TextBlock",
                    "text": f"Period: {period_str}",
                    "wrap": True
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {
                            "title": "New Jobs:",
                            "value": str(report.new_jobs)
                        },
                        {
                            "title": "Total Matches:",
                            "value": str(report.total_matches)
                        },
                        {
                            "title": "High Quality Matches:",
                            "value": str(report.high_quality_matches)
                        },
                        {
                            "title": "Match Rate:",
                            "value": f"{(report.high_quality_matches/report.total_matches*100):.1f}%" if report.total_matches > 0 else "0%"
                        }
                    ]
                }
            ]
        }
        
        # Add top consultants
        if report.top_consultants:
            consultant_items = []
            for consultant in report.top_consultants[:3]:
                consultant_items.append({
                    "type": "TextBlock",
                    "text": f"• {consultant['name']} - {consultant['match_count']} matches (avg: {consultant['avg_score']:.2f})",
                    "wrap": True
                })
            
            card["body"].extend([
                {
                    "type": "TextBlock",
                    "text": "**Top Consultants:**",
                    "weight": "bolder"
                },
                *consultant_items
            ])
        
        # Add top skills
        if report.top_skills:
            skills_text = ", ".join([f"{s['skill']} ({s['count']})" for s in report.top_skills[:5]])
            card["body"].extend([
                {
                    "type": "TextBlock",
                    "text": "**Most Demanded Skills:**",
                    "weight": "bolder"
                },
                {
                    "type": "TextBlock",
                    "text": skills_text,
                    "wrap": True
                }
            ])
        
        return card