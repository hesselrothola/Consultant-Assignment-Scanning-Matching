"""
Automated scanning scheduler using APScheduler.
Manages daily scanning tasks for the AI consultant assignment scanner.
"""

import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.scrapers import BrainvilleScraper
from app.repo import DatabaseRepository
from app.embeddings import EmbeddingService
from app.matching import MatchingService
from app.reports import ReportingService
from app.notifications.email import EmailNotificationService
from app.notifications.teams import TeamsNotificationService

logger = logging.getLogger(__name__)


class ScannerScheduler:
    """
    Automated scanner scheduler that handles:
    - Daily scanning at 07:00 CET using active scanning configurations
    - Weekly report generation on Fridays at 16:00  
    - Monday morning report compilation at 08:00
    - Adaptive parameter learning and optimization
    """
    
    def __init__(self, 
                 db_repo: DatabaseRepository,
                 embedding_service: EmbeddingService,
                 matching_service: MatchingService,
                 reporting_service: ReportingService):
        self.db_repo = db_repo
        self.embedding_service = embedding_service
        self.matching_service = matching_service
        self.reporting_service = reporting_service
        
        # Initialize notification services
        self.email_service = EmailNotificationService()
        self.teams_service = TeamsNotificationService()
        
        # Initialize scheduler
        self.scheduler = AsyncIOScheduler(timezone="Europe/Stockholm")
        self.is_running = False
        
        # Configuration
        self.enabled_sources = {
            'brainville': BrainvilleScraper,
            # Add other scrapers as they're implemented:
            # 'cinode': CinodeScraper,
            # 'linkedin': LinkedInScraper,
        }
    
    async def start(self):
        """Start the scheduler with all configured jobs."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        try:
            # Schedule daily scanning at 07:00 CET
            self.scheduler.add_job(
                self.run_daily_scan,
                trigger=CronTrigger(hour=7, minute=0, timezone="Europe/Stockholm"),
                id="daily_scan",
                name="Daily Assignment Scanning",
                replace_existing=True,
                max_instances=1
            )
            
            # Schedule weekly report generation on Fridays at 16:00
            self.scheduler.add_job(
                self.generate_weekly_report,
                trigger=CronTrigger(day_of_week='fri', hour=16, minute=0, timezone="Europe/Stockholm"),
                id="weekly_report",
                name="Weekly Report Generation",
                replace_existing=True,
                max_instances=1
            )
            
            # Schedule Monday morning reports at 08:00
            self.scheduler.add_job(
                self.generate_monday_brief,
                trigger=CronTrigger(day_of_week='mon', hour=8, minute=0, timezone="Europe/Stockholm"),
                id="monday_brief",
                name="Monday Morning Brief",
                replace_existing=True,
                max_instances=1
            )
            
            # Schedule configuration optimization (daily at 02:00)
            self.scheduler.add_job(
                self.optimize_configurations,
                trigger=CronTrigger(hour=2, minute=0, timezone="Europe/Stockholm"),
                id="config_optimization",
                name="Configuration Optimization",
                replace_existing=True,
                max_instances=1
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info("Scanner scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    async def stop(self):
        """Stop the scheduler gracefully."""
        if not self.is_running:
            return
        
        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("Scanner scheduler stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    async def run_daily_scan(self):
        """
        Execute daily scanning using active configurations.
        This is the main automated scanning task.
        """
        scan_start = datetime.now(timezone.utc)
        logger.info("Starting daily automated scan")
        
        try:
            # Get all active scanning configurations
            active_configs = await self.db_repo.get_active_scanning_configs()
            
            if not active_configs:
                logger.warning("No active scanning configurations found")
                return
            
            total_jobs_found = 0
            total_matches_generated = 0
            
            # Run scanning with each active configuration
            for config in active_configs:
                logger.info(f"Running scan with configuration: {config['config_name']}")
                
                try:
                    # Apply configuration parameters to scrapers
                    jobs_found, matches_generated = await self._scan_with_config(config)
                    total_jobs_found += jobs_found
                    total_matches_generated += matches_generated
                    
                    # Log performance for this configuration
                    await self._log_config_performance(
                        config['config_id'],
                        jobs_found,
                        matches_generated,
                        scan_start.date()
                    )
                    
                except Exception as e:
                    logger.error(f"Error scanning with config {config['config_name']}: {e}")
                    continue
            
            # Log overall ingestion summary
            scan_duration = datetime.now(timezone.utc) - scan_start
            logger.info(f"Daily scan completed: {total_jobs_found} jobs found, "
                       f"{total_matches_generated} matches generated in {scan_duration}")
            
        except Exception as e:
            logger.error(f"Daily scan failed: {e}")
            raise
    
    async def _scan_with_config(self, config) -> tuple[int, int]:
        """
        Run all enabled scrapers using the specified configuration parameters.
        Returns (jobs_found, matches_generated).
        """
        jobs_found = 0
        matches_generated = 0
        
        # Get source-specific overrides for this configuration
        source_overrides = await self.db_repo.get_source_config_overrides(config['config_id'])
        override_dict = {override['source_name']: override for override in source_overrides}
        
        # Run each enabled scraper
        for source_name, scraper_class in self.enabled_sources.items():
            if source_name in override_dict and not override_dict[source_name]['is_enabled']:
                logger.info(f"Skipping disabled source: {source_name}")
                continue
            
            try:
                logger.info(f"Scanning source: {source_name}")
                
                # Configure scraper with global + source-specific parameters
                scraper_params = self._build_scraper_params(config, override_dict.get(source_name))
                
                # Run the scraper
                async with scraper_class(**scraper_params) as scraper:
                    jobs = await scraper.scrape()
                    jobs_found += len(jobs)
                    
                    # Store jobs in database
                    if jobs:
                        stored_jobs = await self.db_repo.upsert_jobs(jobs)
                        logger.info(f"Stored {len(stored_jobs)} jobs from {source_name}")
                        
                        # Generate matches for new jobs
                        new_matches = await self._generate_matches_for_jobs(stored_jobs)
                        matches_generated += len(new_matches)
                        
                        # Update source performance metrics
                        await self._update_source_performance(
                            config['config_id'], 
                            source_name, 
                            len(jobs), 
                            len(new_matches)
                        )
                
            except Exception as e:
                logger.error(f"Error scanning {source_name}: {e}")
                continue
        
        return jobs_found, matches_generated
    
    def _build_scraper_params(self, config, source_override=None) -> Dict[str, Any]:
        """Build scraper parameters from configuration and overrides."""
        params = {
            'target_skills': config['target_skills'],
            'target_roles': config['target_roles'],
            'target_locations': config['target_locations'],
            'languages': config['languages'],
        }
        
        # Apply source-specific overrides
        if source_override and source_override['parameter_overrides']:
            params.update(source_override['parameter_overrides'])
        
        return params
    
    async def _generate_matches_for_jobs(self, jobs) -> List:
        """Generate matches for a list of jobs and return new matches."""
        all_matches = []
        
        for job in jobs:
            try:
                matches = await self.matching_service.find_matches_for_job(job.job_id)
                all_matches.extend(matches)
            except Exception as e:
                logger.error(f"Error generating matches for job {job.job_id}: {e}")
                continue
        
        return all_matches
    
    async def _log_config_performance(self, config_id: UUID, jobs_found: int, 
                                    matches_generated: int, test_date) -> None:
        """Log performance metrics for a configuration."""
        quality_score = matches_generated / max(jobs_found, 1) if jobs_found > 0 else 0
        
        performance_log = {
            'config_id': config_id,
            'test_date': test_date,
            'jobs_found': jobs_found,
            'matches_generated': matches_generated,
            'quality_score': quality_score,
        }
        
        await self.db_repo.log_config_performance(performance_log)
    
    async def _update_source_performance(self, config_id: UUID, source_name: str, 
                                       jobs_found: int, matches_generated: int) -> None:
        """Update performance metrics for a specific source."""
        success_rate = matches_generated / max(jobs_found, 1) if jobs_found > 0 else 0
        
        await self.db_repo.update_source_performance(
            config_id, 
            source_name, 
            success_rate, 
            matches_generated,
            datetime.now(timezone.utc)
        )
    
    async def generate_weekly_report(self):
        """Generate and deliver weekly report on Fridays."""
        logger.info("Generating weekly report")
        
        try:
            # Generate weekly summary
            report = await self.reporting_service.generate_weekly_report()
            
            # Send to configured channels (Slack/Teams)
            await self._deliver_weekly_report(report)
            
            logger.info("Weekly report generated and delivered successfully")
            
        except Exception as e:
            logger.error(f"Weekly report generation failed: {e}")
    
    async def generate_monday_brief(self):
        """Generate Monday morning brief with weekend summary."""
        logger.info("Generating Monday morning brief")
        
        try:
            # Generate brief summary
            brief = await self.reporting_service.generate_monday_brief()
            
            # Send to configured channels
            await self._deliver_monday_brief(brief)
            
            logger.info("Monday brief generated and delivered successfully")
            
        except Exception as e:
            logger.error(f"Monday brief generation failed: {e}")
    
    async def optimize_configurations(self):
        """Optimize scanning configurations based on performance data."""
        logger.info("Starting configuration optimization")
        
        try:
            # Analyze performance of all configurations
            configs = await self.db_repo.get_all_scanning_configs()
            
            for config in configs:
                await self._optimize_single_config(config)
            
            logger.info("Configuration optimization completed")
            
        except Exception as e:
            logger.error(f"Configuration optimization failed: {e}")
    
    async def _optimize_single_config(self, config):
        """Optimize a single configuration based on its performance history."""
        try:
            # Get recent performance data (last 30 days)
            performance_data = await self.db_repo.get_config_performance_history(
                config['config_id'], 
                days=30
            )
            
            if not performance_data:
                return
            
            # Simple optimization: adjust parameters based on success patterns
            # This is where machine learning algorithms would be applied
            avg_quality_score = sum(p['quality_score'] or 0 for p in performance_data) / len(performance_data)
            
            # Update configuration performance score
            await self.db_repo.update_config_performance_score(
                config['config_id'], 
                avg_quality_score
            )
            
            # Learn from high-performing parameters
            await self._extract_learning_parameters(config, performance_data)
            
        except Exception as e:
            logger.error(f"Error optimizing config {config['config_name']}: {e}")
    
    async def _extract_learning_parameters(self, config, performance_data):
        """Extract and store high-performing parameters for future use."""
        # Identify best performing periods
        best_performers = [p for p in performance_data if (p['quality_score'] or 0) > 0.7]
        
        if not best_performers:
            return
        
        # Extract common parameters from best performers
        # This is simplified - in a real system, you'd use ML to identify patterns
        for param_name in ['target_skills', 'target_roles', 'target_locations']:
            param_values = config.get(param_name, [])
            
            for value in param_values:
                # Store as learned parameter
                await self.db_repo.upsert_learning_parameter(
                    parameter_name=param_name,
                    parameter_value=value,
                    effectiveness_score=max(p['quality_score'] or 0 for p in best_performers),
                    learned_from_config_id=config['config_id']
                )
    
    async def _deliver_weekly_report(self, report):
        """Deliver weekly report to configured channels."""
        delivered = False
        
        # Send via email if configured
        if self.email_service.is_configured():
            email_sent = await self.email_service.send_weekly_report(report)
            if email_sent:
                logger.info("Weekly report sent via email")
                delivered = True
        
        # Send via Teams if configured
        if self.teams_service.is_configured():
            teams_sent = await self.teams_service.send_weekly_report(report)
            if teams_sent:
                logger.info("Weekly report sent via Teams")
                delivered = True
        
        if not delivered:
            logger.warning("No notification channels configured for weekly report")
    
    async def _deliver_monday_brief(self, brief):
        """Deliver Monday brief to configured channels."""
        delivered = False
        
        # Send via email if configured
        if self.email_service.is_configured():
            email_sent = await self.email_service.send_monday_brief(brief)
            if email_sent:
                logger.info("Monday brief sent via email")
                delivered = True
        
        # Send via Teams if configured
        if self.teams_service.is_configured():
            teams_sent = await self.teams_service.send_monday_brief(brief)
            if teams_sent:
                logger.info("Monday brief sent via Teams")
                delivered = True
        
        if not delivered:
            logger.warning("No notification channels configured for Monday brief")
    
    # Manual trigger methods for testing
    async def trigger_scan_now(self, config_id: Optional[UUID] = None):
        """Manually trigger a scan for testing purposes."""
        logger.info("Manual scan triggered")
        
        if config_id:
            config = await self.db_repo.get_scanning_config(config_id)
            if config:
                await self._scan_with_config(config)
        else:
            await self.run_daily_scan()
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status and next run times."""
        if not self.is_running:
            return {"status": "stopped"}
        
        jobs_status = []
        for job in self.scheduler.get_jobs():
            jobs_status.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return {
            "status": "running",
            "jobs": jobs_status
        }