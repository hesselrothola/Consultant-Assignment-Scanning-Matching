import os
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx

from app.models import (
    Job, JobIn, Consultant, ConsultantIn,
    Company, CompanyIn, Broker, BrokerIn,
    MatchRequest, MatchResult, ReportSummary
)
from app.repo import DatabaseRepository
from app.embeddings import EmbeddingService
from app.matching import MatchingService
from app.reports import ReportingService
from app.scheduler import ScannerScheduler
from app.parse.html_parser import GenericHTMLParser
from app.ingest.rss_ingester import RSSIngester
from app.scrapers import BrainvilleScraper, CinodeScraper, EworkScraper
from app.config import settings, SCRAPER_CONFIGS
from app.auth_routes import router as auth_router
from app.auth import get_current_user, require_user, User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
db_repo: Optional[DatabaseRepository] = None
embedding_service: Optional[EmbeddingService] = None
matching_service: Optional[MatchingService] = None
reporting_service: Optional[ReportingService] = None
scanner_scheduler: Optional[ScannerScheduler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global db_repo, embedding_service, matching_service, reporting_service, scanner_scheduler
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/consultant_matching")
    
    db_repo = DatabaseRepository(db_url)
    await db_repo.init()
    
    embedding_service = EmbeddingService()
    matching_service = MatchingService(db_repo, embedding_service)
    reporting_service = ReportingService(db_repo)
    
    # Initialize and start scheduler
    scanner_scheduler = ScannerScheduler(
        db_repo=db_repo,
        embedding_service=embedding_service,
        matching_service=matching_service,
        reporting_service=reporting_service
    )
    
    # Start scheduler if enabled
    scheduler_enabled = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
    if scheduler_enabled:
        await scanner_scheduler.start()
        logger.info("Scanner scheduler started")
    else:
        logger.info("Scanner scheduler disabled")
    
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    if scanner_scheduler and scanner_scheduler.is_running:
        await scanner_scheduler.stop()
        logger.info("Scanner scheduler stopped")
    
    if db_repo:
        await db_repo.close()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Consultant Assignment Matching API",
    version="1.0.0",
    description="API for ingesting job assignments and matching with consultants",
    lifespan=lifespan
)


# Dependency to get DB repository
def get_db() -> DatabaseRepository:
    if not db_repo:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return db_repo


def get_embedding_service() -> EmbeddingService:
    if not embedding_service:
        raise HTTPException(status_code=500, detail="Embedding service not initialized")
    return embedding_service


def get_matching_service() -> MatchingService:
    if not matching_service:
        raise HTTPException(status_code=500, detail="Matching service not initialized")
    return matching_service


def get_reporting_service() -> ReportingService:
    if not reporting_service:
        raise HTTPException(status_code=500, detail="Reporting service not initialized")
    return reporting_service


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/jobs/upsert", response_model=Job)
async def upsert_job(
    job: JobIn,
    background_tasks: BackgroundTasks,
    db: DatabaseRepository = Depends(get_db),
    embeddings: EmbeddingService = Depends(get_embedding_service)
):
    """Upsert a job (create or update)."""
    try:
        # Handle company if provided
        if job.company_id is None and hasattr(job, 'company_name') and job.company_name:
            company = await db.get_company_by_name(job.company_name)
            if not company:
                company = await db.upsert_company(CompanyIn(
                    normalized_name=job.company_name.lower().strip(),
                    aliases=[job.company_name]
                ))
            job.company_id = company.company_id
        
        # Handle broker if provided
        if job.broker_id is None and hasattr(job, 'broker_name') and job.broker_name:
            broker = await db.get_broker_by_name(job.broker_name)
            if not broker:
                broker = await db.upsert_broker(BrokerIn(name=job.broker_name))
            job.broker_id = broker.broker_id
        
        # Save job to database
        saved_job = await db.upsert_job(job)
        
        # Create embedding in background
        async def create_job_embedding():
            try:
                job_text = embeddings.prepare_job_text(job.model_dump())
                embedding = await embeddings.create_embedding(job_text)
                await db.store_job_embedding(saved_job.job_id, embedding)
            except Exception as e:
                logger.error(f"Error creating embedding for job {saved_job.job_id}: {e}")
        
        background_tasks.add_task(create_job_embedding)
        
        return saved_job
        
    except Exception as e:
        logger.error(f"Error upserting job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/bulk", response_model=List[Job])
async def bulk_upsert_jobs(
    jobs: List[JobIn],
    background_tasks: BackgroundTasks,
    db: DatabaseRepository = Depends(get_db),
    embeddings: EmbeddingService = Depends(get_embedding_service)
):
    """Bulk upsert multiple jobs."""
    saved_jobs = []
    
    for job in jobs:
        try:
            saved_job = await db.upsert_job(job)
            saved_jobs.append(saved_job)
            
            # Create embedding in background
            async def create_job_embedding(job_id, job_data):
                try:
                    job_text = embeddings.prepare_job_text(job_data)
                    embedding = await embeddings.create_embedding(job_text)
                    await db.store_job_embedding(job_id, embedding)
                except Exception as e:
                    logger.error(f"Error creating embedding for job {job_id}: {e}")
            
            background_tasks.add_task(
                create_job_embedding,
                saved_job.id,
                job.model_dump()
            )
            
        except Exception as e:
            logger.error(f"Error upserting job: {e}")
    
    return saved_jobs


@app.post("/api/consultants/upload-cv")
async def upload_consultant_cv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: DatabaseRepository = Depends(get_db)
):
    """Upload and parse a CV file to create a new consultant."""
    import tempfile
    import shutil
    from app.cv_parser import parse_and_add_consultant
    
    # Validate file type
    allowed_extensions = ['.pdf', '.docx', '.doc', '.txt']
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Save uploaded file temporarily
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        # Parse CV and add consultant
        result = await parse_and_add_consultant(tmp_path, db)
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        
        return result
        
    except Exception as e:
        logger.error(f"CV upload failed: {e}")
        # Clean up temp file if it exists
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/consultants/upsert", response_model=Consultant)
async def upsert_consultant(
    consultant: ConsultantIn,
    background_tasks: BackgroundTasks,
    db: DatabaseRepository = Depends(get_db),
    embeddings: EmbeddingService = Depends(get_embedding_service)
):
    """Upsert a consultant (create or update)."""
    try:
        # Save consultant to database
        saved_consultant = await db.upsert_consultant(consultant)
        
        # Create embedding in background
        async def create_consultant_embedding():
            try:
                consultant_text = embeddings.prepare_consultant_text(consultant.model_dump())
                embedding = await embeddings.create_embedding(consultant_text)
                await db.store_consultant_embedding(saved_consultant.consultant_id, embedding)
            except Exception as e:
                logger.error(f"Error creating embedding for consultant {saved_consultant.consultant_id}: {e}")
        
        background_tasks.add_task(create_consultant_embedding)
        
        return saved_consultant
        
    except Exception as e:
        logger.error(f"Error upserting consultant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/match/run")
async def run_matching(
    request: MatchRequest,
    matching: MatchingService = Depends(get_matching_service),
    db: DatabaseRepository = Depends(get_db)
):
    """Run matching algorithm for specified jobs and consultants."""
    try:
        matches = await matching.run_matching(
            job_ids=request.job_ids,
            consultant_ids=request.consultant_ids,
            min_score=request.min_score,
            max_results=request.max_results
        )
        
        # Fetch full details for response
        results = []
        for match in matches:
            job = await db.get_job(match.job_id)
            consultant = await db.get_consultant(match.consultant_id)
            
            results.append(MatchResult(
                job=job,
                consultant=consultant,
                match=match
            ))
        
        return results
        
    except Exception as e:
        logger.error(f"Error running matching: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reports/daily", response_model=ReportSummary)
async def get_daily_report(
    reporting: ReportingService = Depends(get_reporting_service)
):
    """Get daily report."""
    try:
        report = await reporting.generate_daily_report()
        return report
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reports/weekly", response_model=ReportSummary)
async def get_weekly_report(
    reporting: ReportingService = Depends(get_reporting_service)
):
    """Get weekly report."""
    try:
        report = await reporting.generate_weekly_report()
        return report
    except Exception as e:
        logger.error(f"Error generating weekly report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reports/daily/slack")
async def get_daily_report_slack(
    reporting: ReportingService = Depends(get_reporting_service)
):
    """Get daily report formatted for Slack."""
    try:
        report = await reporting.generate_daily_report()
        slack_message = reporting.format_slack_message(report)
        return slack_message
    except Exception as e:
        logger.error(f"Error generating Slack report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reports/weekly/teams")
async def get_weekly_report_teams(
    reporting: ReportingService = Depends(get_reporting_service)
):
    """Get weekly report formatted for Microsoft Teams."""
    try:
        report = await reporting.generate_weekly_report()
        teams_card = reporting.format_teams_message(report)
        return teams_card
    except Exception as e:
        logger.error(f"Error generating Teams report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/parse/{source}")
async def parse_html(
    source: str,
    html_content: str
):
    """Parse HTML content to extract jobs."""
    try:
        parser = GenericHTMLParser(source)
        jobs = parser.parse_job_listing(html_content)
        return jobs
    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/rss")
async def ingest_from_rss(
    feed_url: str,
    source_name: str,
    background_tasks: BackgroundTasks,
    db: DatabaseRepository = Depends(get_db),
    embeddings: EmbeddingService = Depends(get_embedding_service)
):
    """Ingest jobs from RSS feed."""
    try:
        # Create ingestion log
        log_id = await db.create_ingestion_log(source_name, feed_url)
        
        async with RSSIngester(feed_url, source_name) as ingester:
            jobs = await ingester.fetch_jobs()
        
        jobs_new = 0
        jobs_updated = 0
        
        for job in jobs:
            try:
                # Check if job exists
                existing_job = None
                if job.external_id:
                    # Would need to add a method to get job by external_id
                    pass
                
                saved_job = await db.upsert_job(job)
                
                if existing_job:
                    jobs_updated += 1
                else:
                    jobs_new += 1
                
                # Create embedding in background
                async def create_job_embedding(job_id, job_data):
                    try:
                        job_text = embeddings.prepare_job_text(job_data)
                        embedding = await embeddings.create_embedding(job_text)
                        await db.store_job_embedding(
                            job_id,
                            embedding,
                            embeddings.model_version
                        )
                    except Exception as e:
                        logger.error(f"Error creating embedding: {e}")
                
                background_tasks.add_task(
                    create_job_embedding,
                    saved_job.id,
                    job.model_dump()
                )
                
            except Exception as e:
                logger.error(f"Error processing job: {e}")
        
        # Update ingestion log
        await db.update_ingestion_log(
            log_id,
            status="completed",
            jobs_found=len(jobs),
            jobs_new=jobs_new,
            jobs_updated=jobs_updated
        )
        
        return {
            "status": "success",
            "jobs_found": len(jobs),
            "jobs_new": jobs_new,
            "jobs_updated": jobs_updated
        }
        
    except Exception as e:
        logger.error(f"Error ingesting from RSS: {e}")
        if log_id:
            await db.update_ingestion_log(
                log_id,
                status="failed",
                error_message=str(e)
            )
        raise HTTPException(status_code=500, detail=str(e))


# n8n webhook endpoints
@app.post("/n8n/ingest")
async def n8n_ingest_webhook(
    data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: DatabaseRepository = Depends(get_db),
    embeddings: EmbeddingService = Depends(get_embedding_service)
):
    """n8n webhook for job ingestion."""
    try:
        # Extract jobs from n8n payload
        jobs_data = data.get("jobs", [])
        source = data.get("source", "n8n")
        
        saved_jobs = []
        for job_data in jobs_data:
            job = JobIn(**job_data)
            saved_job = await db.upsert_job(job)
            saved_jobs.append(saved_job)
            
            # Create embedding in background
            async def create_embedding(job_id, job_dict):
                try:
                    text = embeddings.prepare_job_text(job_dict)
                    embedding = await embeddings.create_embedding(text)
                    await db.store_job_embedding(job_id, embedding, embeddings.model_version)
                except Exception as e:
                    logger.error(f"Embedding error: {e}")
            
            background_tasks.add_task(create_embedding, saved_job.id, job_data)
        
        return {
            "status": "success",
            "jobs_processed": len(saved_jobs),
            "job_ids": [str(j.id) for j in saved_jobs]
        }
        
    except Exception as e:
        logger.error(f"n8n webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/n8n/match")
async def n8n_match_webhook(
    data: Dict[str, Any],
    matching: MatchingService = Depends(get_matching_service),
    db: DatabaseRepository = Depends(get_db)
):
    """n8n webhook for running matches."""
    try:
        job_ids = data.get("job_ids", [])
        min_score = data.get("min_score", 0.5)
        max_results = data.get("max_results", 5)
        
        # Convert string UUIDs to UUID objects
        job_uuids = [UUID(jid) for jid in job_ids] if job_ids else None
        
        matches = await matching.run_matching(
            job_ids=job_uuids,
            min_score=min_score,
            max_results=max_results
        )
        
        # Format for n8n
        results = []
        for match in matches:
            job = await db.get_job(match.job_id)
            consultant = await db.get_consultant(match.consultant_id)
            
            results.append({
                "job_title": job.title,
                "job_company": job.company,
                "consultant_name": consultant.name,
                "consultant_title": consultant.title,
                "match_score": float(match.match_score),
                "reason": match.reason_json
            })
        
        return {
            "status": "success",
            "matches": results
        }
        
    except Exception as e:
        logger.error(f"n8n match webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Scraper endpoints
@app.post("/scrape/brainville")
async def scrape_brainville(
    background_tasks: BackgroundTasks,
    db: DatabaseRepository = Depends(get_db),
    embeddings: EmbeddingService = Depends(get_embedding_service),
    max_pages: Optional[int] = None
):
    """Manually trigger Brainville scraping."""
    if not SCRAPER_CONFIGS.get("brainville", {}).get("enabled"):
        raise HTTPException(status_code=400, detail="Brainville scraper is disabled")
    
    try:
        async with BrainvilleScraper() as scraper:
            if max_pages:
                scraper.max_pages = max_pages
            
            # Scrape jobs
            jobs = await scraper.scrape()
            
            # Save jobs and create embeddings
            saved_jobs = []
            for job_in in jobs:
                # Handle company
                if job_in.company:
                    company = await db.get_or_create_company(job_in.company)
                    job_in.company_id = company.company_id
                
                # Handle broker
                if job_in.broker:
                    broker = await db.get_or_create_broker(job_in.broker)
                    job_in.broker_id = broker.broker_id
                
                # Save job
                saved_job = await db.upsert_job(job_in)
                saved_jobs.append(saved_job)
                
                # Create embedding in background
                async def create_job_embedding(job_id, job_data):
                    try:
                        job_text = embeddings.prepare_job_text(job_data)
                        embedding = await embeddings.create_embedding(job_text)
                        await db.store_job_embedding(job_id, embedding)
                    except Exception as e:
                        logger.error(f"Error creating embedding for job {job_id}: {e}")
                
                background_tasks.add_task(
                    create_job_embedding,
                    saved_job.job_id,
                    job_in.dict()
                )
            
            # Log ingestion
            await db.log_ingestion(
                source="brainville",
                status="success",
                found_count=len(jobs),
                upserted_count=len(saved_jobs)
            )
            
            return {
                "status": "success",
                "jobs_scraped": len(jobs),
                "jobs_saved": len(saved_jobs),
                "message": f"Successfully scraped {len(jobs)} jobs from Brainville"
            }
            
    except Exception as e:
        logger.error(f"Error scraping Brainville: {e}")
        
        # Log failed ingestion
        await db.log_ingestion(
            source="brainville",
            status="failed",
            error=str(e)
        )
        
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scrape/ework")
async def scrape_ework(
    background_tasks: BackgroundTasks,
    db: DatabaseRepository = Depends(get_db),
    embeddings: EmbeddingService = Depends(get_embedding_service),
    max_pages: Optional[int] = None,
    countries: Optional[List[str]] = None
):
    """Manually trigger eWork scraping."""
    try:
        # Use configured countries or default to Sweden
        target_countries = countries or ['SE']
        
        async with EworkScraper(countries=target_countries) as scraper:
            if max_pages:
                scraper.max_pages = max_pages
            
            jobs = await scraper.scrape_listings()
            
            saved_jobs = []
            for job_data in jobs:
                # Convert to JobIn model
                job_model = await scraper.convert_to_job_model(job_data)
                if job_model:
                    # Save to database
                    try:
                        saved_job = await db.upsert_job(job_model)
                        saved_jobs.append(saved_job)
                        
                        # Create embedding in background
                        async def create_job_embedding(job_id, job_dict):
                            try:
                                text = embeddings.prepare_job_text(job_dict)
                                embedding = await embeddings.create_embedding(text)
                                await db.store_job_embedding(
                                    job_id, 
                                    embedding, 
                                    embeddings.model_version
                                )
                            except Exception as e:
                                logger.error(f"Error creating embedding for job {job_id}: {e}")
                        
                        background_tasks.add_task(
                            create_job_embedding,
                            saved_job.job_id,
                            job_data
                        )
                        
                    except Exception as e:
                        logger.error(f"Error saving eWork job: {e}")
            
            # Log ingestion
            await db.log_ingestion(
                source="ework",
                status="success",
                found_count=len(jobs),
                upserted_count=len(saved_jobs)
            )
            
            return {
                "status": "success",
                "jobs_scraped": len(jobs),
                "jobs_saved": len(saved_jobs),
                "countries": target_countries,
                "message": f"Successfully scraped {len(jobs)} jobs from eWork"
            }
            
    except Exception as e:
        logger.error(f"Error scraping eWork: {e}")
        
        # Log failed ingestion
        await db.log_ingestion(
            source="ework",
            status="failed",
            error=str(e)
        )
        
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scrape/cinode")
async def scrape_cinode(
    background_tasks: BackgroundTasks,
    db: DatabaseRepository = Depends(get_db),
    embeddings: EmbeddingService = Depends(get_embedding_service),
    max_pages: Optional[int] = None
):
    """Manually trigger Cinode Market scraping."""
    try:
        async with CinodeScraper() as scraper:
            if max_pages:
                scraper.max_pages = max_pages
            
            # Scrape jobs
            jobs = await scraper.scrape()
            
            # Save jobs and create embeddings
            saved_jobs = []
            for job_in in jobs:
                # Handle company
                if job_in.company:
                    company = await db.get_or_create_company(job_in.company)
                    job_in.company_id = company.company_id
                
                # Handle broker
                if job_in.broker:
                    broker = await db.get_or_create_broker(job_in.broker)
                    job_in.broker_id = broker.broker_id
                
                # Save job
                saved_job = await db.upsert_job(job_in)
                saved_jobs.append(saved_job)
                
                # Create embedding in background
                async def create_job_embedding(job_id, job_data):
                    try:
                        job_text = embeddings.prepare_job_text(job_data)
                        embedding = await embeddings.create_embedding(job_text)
                        await db.store_job_embedding(job_id, embedding)
                    except Exception as e:
                        logger.error(f"Error creating embedding for job {job_id}: {e}")
                
                background_tasks.add_task(
                    create_job_embedding,
                    saved_job.job_id,
                    job_in.dict()
                )
            
            # Log successful ingestion
            await db.log_ingestion(
                source="cinode",
                status="completed",
                jobs_found=len(jobs),
                jobs_new=len(saved_jobs)
            )
            
            return {
                "status": "success",
                "jobs_scraped": len(jobs),
                "jobs_saved": len(saved_jobs),
                "message": f"Successfully scraped {len(jobs)} jobs from Cinode Market"
            }
            
    except Exception as e:
        logger.error(f"Error scraping Cinode: {e}")
        
        # Log failed ingestion
        await db.log_ingestion(
            source="cinode",
            status="failed",
            error=str(e)
        )
        
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/jobs")
async def ingest_jobs(
    jobs_data: List[JobIn],
    source: str,
    background_tasks: BackgroundTasks,
    db: DatabaseRepository = Depends(get_db),
    embeddings: EmbeddingService = Depends(get_embedding_service)
):
    """Generic endpoint to ingest multiple jobs from external sources."""
    try:
        saved_jobs = []
        
        for job_in in jobs_data:
            # Set source if not already set
            if not job_in.source:
                job_in.source = source
            
            # Handle company
            if job_in.company:
                company = await db.get_or_create_company(job_in.company)
                job_in.company_id = company.company_id
            
            # Handle broker  
            if job_in.broker:
                broker = await db.get_or_create_broker(job_in.broker)
                job_in.broker_id = broker.broker_id
            
            # Save job
            saved_job = await db.upsert_job(job_in)
            saved_jobs.append(saved_job)
            
            # Create embedding in background
            async def create_job_embedding(job_id, job_data):
                try:
                    job_text = embeddings.prepare_job_text(job_data)
                    embedding = await embeddings.create_embedding(job_text)
                    await db.store_job_embedding(job_id, embedding)
                except Exception as e:
                    logger.error(f"Error creating embedding for job {job_id}: {e}")
            
            background_tasks.add_task(
                create_job_embedding,
                saved_job.job_id,
                job_in.dict()
            )
        
        # Log successful ingestion
        await db.log_ingestion(
            source=source,
            status="completed",
            jobs_found=len(jobs_data),
            jobs_new=len(saved_jobs)
        )
        
        return {
            "status": "success",
            "jobs_received": len(jobs_data),
            "jobs_saved": len(saved_jobs),
            "message": f"Successfully ingested {len(saved_jobs)} jobs from {source}"
        }
        
    except Exception as e:
        logger.error(f"Error ingesting jobs from {source}: {e}")
        
        # Log failed ingestion
        await db.log_ingestion(
            source=source,
            status="failed",
            error=str(e)
        )
        
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/scrape/status")
async def get_scraper_status(
    db: DatabaseRepository = Depends(get_db)
):
    """Get status of all scrapers and recent ingestion history."""
    try:
        # Get recent ingestion logs
        recent_logs = await db.get_recent_ingestion_logs(limit=10)
        
        # Get scraper configurations
        scraper_status = {}
        for name, config in SCRAPER_CONFIGS.items():
            scraper_status[name] = {
                "enabled": config.get("enabled", False),
                "base_url": config.get("base_url", ""),
                "max_pages": config.get("max_pages", 10),
                "rate_limit": config.get("rate_limit", 1.0)
            }
        
        return {
            "scrapers": scraper_status,
            "recent_ingestions": recent_logs,
            "scraping_enabled": settings.scraping_enabled
        }
        
    except Exception as e:
        logger.error(f"Error getting scraper status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scrape/all")
async def scrape_all_sources(
    background_tasks: BackgroundTasks,
    db: DatabaseRepository = Depends(get_db),
    embeddings: EmbeddingService = Depends(get_embedding_service)
):
    """Trigger scraping from all enabled sources."""
    if not settings.scraping_enabled:
        raise HTTPException(status_code=400, detail="Scraping is globally disabled")
    
    results = {}
    
    # Scrape Brainville if enabled
    if SCRAPER_CONFIGS.get("brainville", {}).get("enabled"):
        try:
            async with BrainvilleScraper() as scraper:
                jobs = await scraper.scrape()
                
                saved_count = 0
                for job_in in jobs:
                    try:
                        # Handle company and broker
                        if job_in.company:
                            company = await db.get_or_create_company(job_in.company)
                            job_in.company_id = company.company_id
                        
                        if job_in.broker:
                            broker = await db.get_or_create_broker(job_in.broker)
                            job_in.broker_id = broker.broker_id
                        
                        # Save job
                        saved_job = await db.upsert_job(job_in)
                        saved_count += 1
                        
                        # Create embedding in background
                        async def create_embedding(job_id, job_data):
                            try:
                                text = embeddings.prepare_job_text(job_data)
                                emb = await embeddings.create_embedding(text)
                                await db.store_job_embedding(job_id, emb)
                            except Exception as e:
                                logger.error(f"Embedding error: {e}")
                        
                        background_tasks.add_task(create_embedding, saved_job.job_id, job_in.dict())
                        
                    except Exception as e:
                        logger.error(f"Error saving job: {e}")
                
                results["brainville"] = {
                    "status": "success",
                    "scraped": len(jobs),
                    "saved": saved_count
                }
                
                await db.log_ingestion(
                    source="brainville",
                    status="success",
                    found_count=len(jobs),
                    upserted_count=saved_count
                )
                
        except Exception as e:
            logger.error(f"Brainville scraping failed: {e}")
            results["brainville"] = {
                "status": "failed",
                "error": str(e)
            }
            await db.log_ingestion(
                source="brainville",
                status="failed",
                error=str(e)
            )
    
    # Add other scrapers here as they're implemented
    # if SCRAPER_CONFIGS.get("cinode", {}).get("enabled"):
    #     # Scrape Cinode...
    
    return {
        "status": "completed",
        "results": results,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Scheduler Management Endpoints
@app.get("/scheduler/status")
async def get_scheduler_status():
    """Get current scheduler status and next run times."""
    if not scanner_scheduler:
        return {"status": "not_initialized"}
    
    return scanner_scheduler.get_scheduler_status()


@app.post("/scheduler/scan/trigger")
async def trigger_manual_scan(
    config_id: Optional[UUID] = None,
    background_tasks: BackgroundTasks = None
):
    """Manually trigger a scan for testing purposes."""
    if not scanner_scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")
    
    try:
        if background_tasks:
            background_tasks.add_task(scanner_scheduler.trigger_scan_now, config_id)
            return {"status": "scan_triggered", "config_id": config_id}
        else:
            await scanner_scheduler.trigger_scan_now(config_id)
            return {"status": "scan_completed", "config_id": config_id}
    except Exception as e:
        logger.error(f"Manual scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@app.post("/scheduler/start")
async def start_scheduler():
    """Start the scheduler (admin only)."""
    if not scanner_scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")
    
    if scanner_scheduler.is_running:
        return {"status": "already_running"}
    
    try:
        await scanner_scheduler.start()
        return {"status": "started"}
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        raise HTTPException(status_code=500, detail=f"Start failed: {str(e)}")


@app.post("/scheduler/stop")
async def stop_scheduler():
    """Stop the scheduler (admin only)."""
    if not scanner_scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")
    
    if not scanner_scheduler.is_running:
        return {"status": "already_stopped"}
    
    try:
        await scanner_scheduler.stop()
        return {"status": "stopped"}
    except Exception as e:
        logger.error(f"Failed to stop scheduler: {e}")
        raise HTTPException(status_code=500, detail=f"Stop failed: {str(e)}")


# Include authentication router
app.include_router(auth_router)

# Include frontend router
from app.frontend import router as frontend_router
app.include_router(frontend_router)

# Root redirect based on auth status
@app.get("/")
async def root(current_user: Optional[User] = Depends(get_current_user)):
    """Root endpoint - redirect to dashboard if logged in, otherwise to login"""
    from fastapi.responses import RedirectResponse
    if current_user:
        return RedirectResponse(url="/consultant/", status_code=302)
    return RedirectResponse(url="/auth/login", status_code=302)

# Mount static files if needed
# app.mount("/static", StaticFiles(directory="app/static"), name="static")