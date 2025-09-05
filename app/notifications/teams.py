"""
Microsoft Teams notification service using webhook connectors.
"""

import os
import logging
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TeamsNotificationService:
    """
    Service for sending notifications to Microsoft Teams via webhooks.
    Uses Adaptive Cards for rich formatting.
    """
    
    def __init__(self):
        # Teams webhook URL from environment
        self.webhook_url = os.getenv("TEAMS_WEBHOOK_URL", "")
        self.timeout = int(os.getenv("TEAMS_TIMEOUT", "30"))
        
    def is_configured(self) -> bool:
        """Check if Teams service is properly configured."""
        return bool(self.webhook_url)
    
    async def send_daily_report(self, report: Dict[str, Any]) -> bool:
        """
        Send daily scanning report to Teams channel.
        """
        if not self.is_configured():
            logger.warning("Teams webhook not configured")
            return False
        
        try:
            card = self._create_daily_report_card(report)
            return await self.send_card(card)
        except Exception as e:
            logger.error(f"Failed to send daily Teams report: {e}")
            return False
    
    async def send_weekly_report(self, report: Dict[str, Any]) -> bool:
        """
        Send weekly analysis report to Teams channel.
        """
        if not self.is_configured():
            logger.warning("Teams webhook not configured")
            return False
        
        try:
            card = self._create_weekly_report_card(report)
            return await self.send_card(card)
        except Exception as e:
            logger.error(f"Failed to send weekly Teams report: {e}")
            return False
    
    async def send_monday_brief(self, brief: Dict[str, Any]) -> bool:
        """
        Send Monday morning brief to Teams channel.
        """
        if not self.is_configured():
            logger.warning("Teams webhook not configured")
            return False
        
        try:
            card = self._create_monday_brief_card(brief)
            return await self.send_card(card)
        except Exception as e:
            logger.error(f"Failed to send Monday Teams brief: {e}")
            return False
    
    async def send_card(self, card: Dict[str, Any]) -> bool:
        """
        Send an Adaptive Card to Teams webhook.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.webhook_url,
                    json=card,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    logger.info("Teams notification sent successfully")
                    return True
                else:
                    logger.error(f"Teams webhook returned {response.status_code}: {response.text}")
                    return False
                    
        except httpx.TimeoutException:
            logger.error("Teams webhook request timed out")
            return False
        except Exception as e:
            logger.error(f"Failed to send Teams notification: {e}")
            return False
    
    def _create_daily_report_card(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Create an Adaptive Card for daily report."""
        new_jobs = report.get('new_jobs', 0)
        total_matches = report.get('total_matches', 0)
        high_quality_matches = report.get('high_quality_matches', 0)
        top_consultants = report.get('top_consultants', [])[:3]
        sources = report.get('sources_breakdown', {})
        
        # Build facts for sources
        source_facts = [
            {"title": source, "value": str(count)}
            for source, count in sources.items()
        ]
        
        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": [
                            {
                                "type": "Container",
                                "style": "emphasis",
                                "items": [
                                    {
                                        "type": "ColumnSet",
                                        "columns": [
                                            {
                                                "type": "Column",
                                                "width": "auto",
                                                "items": [
                                                    {
                                                        "type": "Image",
                                                        "url": "https://img.icons8.com/fluency/48/000000/analytics.png",
                                                        "size": "Medium"
                                                    }
                                                ]
                                            },
                                            {
                                                "type": "Column",
                                                "width": "stretch",
                                                "items": [
                                                    {
                                                        "type": "TextBlock",
                                                        "text": "Daily Scanning Report",
                                                        "weight": "Bolder",
                                                        "size": "Large"
                                                    },
                                                    {
                                                        "type": "TextBlock",
                                                        "text": datetime.now().strftime('%A, %B %d, %Y'),
                                                        "isSubtle": True,
                                                        "spacing": "None"
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                "type": "Container",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": "📊 **Key Metrics**",
                                        "size": "Medium",
                                        "weight": "Bolder"
                                    },
                                    {
                                        "type": "ColumnSet",
                                        "columns": [
                                            {
                                                "type": "Column",
                                                "width": "stretch",
                                                "items": [
                                                    {
                                                        "type": "TextBlock",
                                                        "text": "New Jobs",
                                                        "isSubtle": True
                                                    },
                                                    {
                                                        "type": "TextBlock",
                                                        "text": str(new_jobs),
                                                        "size": "Large",
                                                        "weight": "Bolder",
                                                        "color": "Accent"
                                                    }
                                                ]
                                            },
                                            {
                                                "type": "Column",
                                                "width": "stretch",
                                                "items": [
                                                    {
                                                        "type": "TextBlock",
                                                        "text": "Total Matches",
                                                        "isSubtle": True
                                                    },
                                                    {
                                                        "type": "TextBlock",
                                                        "text": str(total_matches),
                                                        "size": "Large",
                                                        "weight": "Bolder",
                                                        "color": "Good"
                                                    }
                                                ]
                                            },
                                            {
                                                "type": "Column",
                                                "width": "stretch",
                                                "items": [
                                                    {
                                                        "type": "TextBlock",
                                                        "text": "High Quality",
                                                        "isSubtle": True
                                                    },
                                                    {
                                                        "type": "TextBlock",
                                                        "text": str(high_quality_matches),
                                                        "size": "Large",
                                                        "weight": "Bolder",
                                                        "color": "Good"
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                "type": "Container",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": "🏆 **Top Matched Consultants**",
                                        "size": "Medium",
                                        "weight": "Bolder"
                                    },
                                    *[
                                        {
                                            "type": "TextBlock",
                                            "text": f"• {c.get('name', 'N/A')} - {c.get('match_count', 0)} matches ({c.get('avg_score', 0):.0%} avg)",
                                            "wrap": True
                                        }
                                        for c in top_consultants
                                    ]
                                ]
                            },
                            {
                                "type": "Container",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": "📍 **Sources Breakdown**",
                                        "size": "Medium",
                                        "weight": "Bolder"
                                    },
                                    {
                                        "type": "FactSet",
                                        "facts": source_facts
                                    }
                                ]
                            }
                        ],
                        "actions": [
                            {
                                "type": "Action.OpenUrl",
                                "title": "View Full Report",
                                "url": os.getenv("REPORT_URL", "https://example.com/reports")
                            }
                        ]
                    }
                }
            ]
        }
        
        return card
    
    def _create_weekly_report_card(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Create an Adaptive Card for weekly report."""
        total_jobs = report.get('total_jobs', 0)
        week_over_week = report.get('week_over_week_change', 0)
        top_skills = report.get('top_skills', [])[:5]
        placement_rate = report.get('placement_rate', 0)
        
        # Determine trend color and icon
        trend_color = "Good" if week_over_week > 0 else "Attention"
        trend_icon = "📈" if week_over_week > 0 else "📉"
        
        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": [
                            {
                                "type": "Container",
                                "style": "good",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": "📈 Weekly Market Analysis",
                                        "weight": "Bolder",
                                        "size": "Large"
                                    },
                                    {
                                        "type": "TextBlock",
                                        "text": f"Week {datetime.now().strftime('%V, %Y')}",
                                        "isSubtle": True
                                    }
                                ]
                            },
                            {
                                "type": "Container",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": "**Weekly Summary**",
                                        "size": "Medium",
                                        "weight": "Bolder"
                                    },
                                    {
                                        "type": "FactSet",
                                        "facts": [
                                            {"title": "Total Assignments", "value": str(total_jobs)},
                                            {"title": "Week-over-Week", "value": f"{trend_icon} {week_over_week:+.1%}"},
                                            {"title": "Placement Rate", "value": f"{placement_rate:.1%}"}
                                        ]
                                    }
                                ]
                            },
                            {
                                "type": "Container",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": "**🔥 Most In-Demand Skills**",
                                        "size": "Medium",
                                        "weight": "Bolder"
                                    },
                                    {
                                        "type": "ColumnSet",
                                        "columns": [
                                            {
                                                "type": "Column",
                                                "width": "stretch",
                                                "items": [
                                                    {
                                                        "type": "TextBlock",
                                                        "text": "\n".join([
                                                            f"{i+1}. {skill.get('skill', 'N/A')}"
                                                            for i, skill in enumerate(top_skills)
                                                        ]),
                                                        "wrap": True
                                                    }
                                                ]
                                            },
                                            {
                                                "type": "Column",
                                                "width": "auto",
                                                "items": [
                                                    {
                                                        "type": "TextBlock",
                                                        "text": "\n".join([
                                                            f"({skill.get('count', 0)})"
                                                            for skill in top_skills
                                                        ]),
                                                        "isSubtle": True
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                "type": "Container",
                                "style": "accent",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": "💡 **Key Insight**",
                                        "weight": "Bolder"
                                    },
                                    {
                                        "type": "TextBlock",
                                        "text": f"The market shows {'increased' if week_over_week > 0 else 'decreased'} demand this week. "
                                                f"Focus on consultants with {top_skills[0]['skill'] if top_skills else 'trending'} expertise.",
                                        "wrap": True
                                    }
                                ]
                            }
                        ],
                        "actions": [
                            {
                                "type": "Action.OpenUrl",
                                "title": "View Detailed Analysis",
                                "url": os.getenv("REPORT_URL", "https://example.com/reports/weekly")
                            }
                        ]
                    }
                }
            ]
        }
        
        return card
    
    def _create_monday_brief_card(self, brief: Dict[str, Any]) -> Dict[str, Any]:
        """Create an Adaptive Card for Monday morning brief."""
        weekend_jobs = brief.get('weekend_jobs', 0)
        urgent_matches = brief.get('urgent_matches', [])[:3]
        week_priorities = brief.get('week_priorities', [])[:5]
        
        # Build urgent matches section
        urgent_items = []
        for match in urgent_matches:
            urgent_items.append({
                "type": "Container",
                "style": "attention",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": f"**{match.get('consultant_name')}** → {match.get('job_title')}",
                        "wrap": True
                    },
                    {
                        "type": "TextBlock",
                        "text": f"Company: {match.get('company')} | Score: {match.get('score', 0):.0%}",
                        "isSubtle": True,
                        "size": "Small",
                        "wrap": True
                    }
                ]
            })
        
        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": [
                            {
                                "type": "Container",
                                "style": "accent",
                                "items": [
                                    {
                                        "type": "ColumnSet",
                                        "columns": [
                                            {
                                                "type": "Column",
                                                "width": "auto",
                                                "items": [
                                                    {
                                                        "type": "TextBlock",
                                                        "text": "☕",
                                                        "size": "ExtraLarge"
                                                    }
                                                ]
                                            },
                                            {
                                                "type": "Column",
                                                "width": "stretch",
                                                "items": [
                                                    {
                                                        "type": "TextBlock",
                                                        "text": "Monday Morning Brief",
                                                        "weight": "Bolder",
                                                        "size": "Large"
                                                    },
                                                    {
                                                        "type": "TextBlock",
                                                        "text": datetime.now().strftime('%B %d, %Y'),
                                                        "isSubtle": True,
                                                        "spacing": "None"
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                "type": "Container",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": f"**Weekend Activity**: {weekend_jobs} new assignments posted",
                                        "wrap": True
                                    }
                                ]
                            },
                            {
                                "type": "Container",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": "⚡ **Urgent Matches Requiring Action**",
                                        "weight": "Bolder",
                                        "size": "Medium"
                                    },
                                    *urgent_items
                                ] if urgent_matches else []
                            },
                            {
                                "type": "Container",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": "📋 **This Week's Priorities**",
                                        "weight": "Bolder",
                                        "size": "Medium"
                                    },
                                    *[
                                        {
                                            "type": "TextBlock",
                                            "text": f"✓ {priority}",
                                            "wrap": True
                                        }
                                        for priority in week_priorities
                                    ]
                                ]
                            },
                            {
                                "type": "Container",
                                "style": "good",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": "Have a productive week! 🚀",
                                        "horizontalAlignment": "Center",
                                        "weight": "Lighter"
                                    }
                                ]
                            }
                        ],
                        "actions": [
                            {
                                "type": "Action.OpenUrl",
                                "title": "Open Dashboard",
                                "url": os.getenv("DASHBOARD_URL", "https://example.com/dashboard")
                            }
                        ]
                    }
                }
            ]
        }
        
        return card