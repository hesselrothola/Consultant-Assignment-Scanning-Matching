"""
Email notification service for sending reports and alerts.
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailNotificationService:
    """
    Service for sending email notifications with reports.
    Supports HTML formatting and attachments.
    """
    
    def __init__(self):
        # Email configuration from environment variables
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_user)
        self.to_emails = os.getenv("TO_EMAILS", "").split(",")  # Comma-separated list
        self.use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        
    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return bool(self.smtp_host and self.smtp_user and self.smtp_password and self.to_emails)
    
    async def send_daily_report(self, report: Dict[str, Any]) -> bool:
        """
        Send daily scanning report via email.
        """
        if not self.is_configured():
            logger.warning("Email service not configured")
            return False
        
        try:
            subject = f"Daily Consultant Scanning Report - {datetime.now().strftime('%Y-%m-%d')}"
            html_body = self._format_daily_report_html(report)
            
            return await self.send_email(
                subject=subject,
                html_body=html_body,
                recipients=self.to_emails
            )
        except Exception as e:
            logger.error(f"Failed to send daily email report: {e}")
            return False
    
    async def send_weekly_report(self, report: Dict[str, Any]) -> bool:
        """
        Send weekly analysis report via email.
        """
        if not self.is_configured():
            logger.warning("Email service not configured")
            return False
        
        try:
            subject = f"Weekly Consultant Market Analysis - Week {datetime.now().strftime('%V, %Y')}"
            html_body = self._format_weekly_report_html(report)
            
            return await self.send_email(
                subject=subject,
                html_body=html_body,
                recipients=self.to_emails
            )
        except Exception as e:
            logger.error(f"Failed to send weekly email report: {e}")
            return False
    
    async def send_monday_brief(self, brief: Dict[str, Any]) -> bool:
        """
        Send Monday morning brief via email.
        """
        if not self.is_configured():
            logger.warning("Email service not configured")
            return False
        
        try:
            subject = f"Monday Morning Brief - {datetime.now().strftime('%Y-%m-%d')}"
            html_body = self._format_monday_brief_html(brief)
            
            return await self.send_email(
                subject=subject,
                html_body=html_body,
                recipients=self.to_emails,
                priority="high"
            )
        except Exception as e:
            logger.error(f"Failed to send Monday brief: {e}")
            return False
    
    async def send_email(self, 
                        subject: str, 
                        html_body: str,
                        recipients: List[str],
                        plain_text: Optional[str] = None,
                        attachments: List[Dict[str, Any]] = None,
                        priority: str = "normal") -> bool:
        """
        Send an email with HTML content and optional attachments.
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(recipients)
            
            # Set priority
            if priority == "high":
                msg['X-Priority'] = '1'
                msg['X-MSMail-Priority'] = 'High'
                msg['Importance'] = 'High'
            
            # Add plain text part
            if plain_text:
                text_part = MIMEText(plain_text, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # Add HTML part
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Add attachments if any
            if attachments:
                for attachment in attachments:
                    self._add_attachment(msg, attachment)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {recipients}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _format_daily_report_html(self, report: Dict[str, Any]) -> str:
        """Format daily report as HTML."""
        new_jobs = report.get('new_jobs', 0)
        total_matches = report.get('total_matches', 0)
        high_quality_matches = report.get('high_quality_matches', 0)
        top_consultants = report.get('top_consultants', [])
        sources = report.get('sources_breakdown', {})
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #ecf0f1; border-radius: 5px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #3498db; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background: #34495e; color: white; }}
                .footer {{ margin-top: 30px; padding: 15px; background: #ecf0f1; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Daily Scanning Report</h1>
                <p>{datetime.now().strftime('%A, %B %d, %Y')}</p>
            </div>
            
            <div class="content">
                <h2>Key Metrics</h2>
                <div>
                    <div class="metric">
                        <div>New Assignments</div>
                        <div class="metric-value">{new_jobs}</div>
                    </div>
                    <div class="metric">
                        <div>Total Matches</div>
                        <div class="metric-value">{total_matches}</div>
                    </div>
                    <div class="metric">
                        <div>High Quality Matches</div>
                        <div class="metric-value">{high_quality_matches}</div>
                    </div>
                </div>
                
                <h2>Top Matched Consultants</h2>
                <table>
                    <tr>
                        <th>Consultant</th>
                        <th>Matches</th>
                        <th>Avg Score</th>
                    </tr>
                    {"".join([f'''
                    <tr>
                        <td>{c.get('name', 'N/A')}</td>
                        <td>{c.get('match_count', 0)}</td>
                        <td>{c.get('avg_score', 0):.2%}</td>
                    </tr>
                    ''' for c in top_consultants[:5]])}
                </table>
                
                <h2>Sources Breakdown</h2>
                <table>
                    <tr>
                        <th>Source</th>
                        <th>Jobs Found</th>
                    </tr>
                    {"".join([f'''
                    <tr>
                        <td>{source}</td>
                        <td>{count}</td>
                    </tr>
                    ''' for source, count in sources.items()])}
                </table>
            </div>
            
            <div class="footer">
                <p>Generated by AI Consultant Scanner | Automated Daily Report</p>
            </div>
        </body>
        </html>
        """
        return html
    
    def _format_weekly_report_html(self, report: Dict[str, Any]) -> str:
        """Format weekly report as HTML with trends and analysis."""
        total_jobs = report.get('total_jobs', 0)
        week_over_week = report.get('week_over_week_change', 0)
        top_skills = report.get('top_skills', [])
        placement_rate = report.get('placement_rate', 0)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #27ae60; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .trend {{ color: {('#27ae60' if week_over_week > 0 else '#e74c3c')}; font-weight: bold; }}
                .insight {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid #3498db; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background: #2ecc71; color: white; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📈 Weekly Market Analysis</h1>
                <p>Week {datetime.now().strftime('%V, %Y')}</p>
            </div>
            
            <div class="content">
                <h2>Weekly Summary</h2>
                <p>Total assignments processed: <strong>{total_jobs}</strong></p>
                <p>Week-over-week change: <span class="trend">{week_over_week:+.1%}</span></p>
                <p>Placement success rate: <strong>{placement_rate:.1%}</strong></p>
                
                <div class="insight">
                    <h3>🔍 Key Insight</h3>
                    <p>The market shows {"increased" if week_over_week > 0 else "decreased"} demand this week, 
                    particularly in {', '.join([s['skill'] for s in top_skills[:3]]) if top_skills else 'various technologies'}.</p>
                </div>
                
                <h2>Most In-Demand Skills</h2>
                <table>
                    <tr>
                        <th>Skill</th>
                        <th>Mentions</th>
                        <th>Trend</th>
                    </tr>
                    {"".join([f'''
                    <tr>
                        <td>{skill.get('skill', 'N/A')}</td>
                        <td>{skill.get('count', 0)}</td>
                        <td>{skill.get('trend', 'stable')}</td>
                    </tr>
                    ''' for skill in top_skills[:10]])}
                </table>
                
                <h2>Recommendations</h2>
                <ul>
                    <li>Focus on consultants with {top_skills[0]['skill'] if top_skills else 'trending'} skills</li>
                    <li>{"Increase scanning frequency" if week_over_week > 0.1 else "Maintain current scanning pace"}</li>
                    <li>Review consultant availability for high-demand areas</li>
                </ul>
            </div>
            
            <div class="footer">
                <p>Generated by AI Consultant Scanner | Weekly Strategic Report</p>
            </div>
        </body>
        </html>
        """
        return html
    
    def _format_monday_brief_html(self, brief: Dict[str, Any]) -> str:
        """Format Monday morning brief as HTML."""
        weekend_jobs = brief.get('weekend_jobs', 0)
        urgent_matches = brief.get('urgent_matches', [])
        week_priorities = brief.get('week_priorities', [])
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #3498db; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .urgent {{ background: #ffe5e5; padding: 10px; border-radius: 5px; margin: 10px 0; }}
                .priority {{ background: #e8f4f8; padding: 10px; margin: 5px 0; border-left: 3px solid #3498db; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>☕ Monday Morning Brief</h1>
                <p>{datetime.now().strftime('%B %d, %Y')}</p>
            </div>
            
            <div class="content">
                <h2>Weekend Activity</h2>
                <p><strong>{weekend_jobs}</strong> new assignments posted over the weekend</p>
                
                {"<h2>⚡ Urgent Matches Requiring Action</h2>" if urgent_matches else ""}
                {"".join([f'''
                <div class="urgent">
                    <strong>{match.get('consultant_name')}</strong> → {match.get('job_title')}<br>
                    Company: {match.get('company')}<br>
                    Match Score: {match.get('score', 0):.0%}
                </div>
                ''' for match in urgent_matches[:5]])}
                
                <h2>This Week's Priorities</h2>
                {"".join([f'''
                <div class="priority">
                    ✓ {priority}
                </div>
                ''' for priority in week_priorities])}
                
                <p><em>Have a productive week!</em></p>
            </div>
        </body>
        </html>
        """
        return html
    
    def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """Add an attachment to the email."""
        try:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment['content'])
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {attachment["filename"]}'
            )
            msg.attach(part)
        except Exception as e:
            logger.error(f"Failed to add attachment: {e}")