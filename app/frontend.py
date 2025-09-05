"""
Frontend routes for the consultant matching system
Uses FastAPI with HTMX for dynamic interactions without heavy JavaScript
"""

from fastapi import APIRouter, Request, Form, Query, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List
import os
from datetime import datetime, timezone
from uuid import UUID

router = APIRouter(tags=["frontend"])

# Setup Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard view"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Consultant Matching Dashboard"
    })

@router.get("/jobs", response_class=HTMLResponse)
async def jobs_list(
    request: Request,
    source: Optional[str] = None,
    limit: int = Query(20, le=100)
):
    """View and filter jobs"""
    from app.main import db_repo
    
    # Get jobs from database
    jobs = await db_repo.get_jobs(source=source, limit=limit)
    
    return templates.TemplateResponse("jobs.html", {
        "request": request,
        "jobs": jobs,
        "source": source,
        "limit": limit
    })

@router.get("/consultants", response_class=HTMLResponse) 
async def consultants_list(
    request: Request,
    active: Optional[bool] = True,
    limit: int = Query(20, le=100)
):
    """View and manage consultants"""
    from app.main import db_repo
    
    consultants = await db_repo.get_consultants(active_only=active, limit=limit)
    
    return templates.TemplateResponse("consultants.html", {
        "request": request,
        "consultants": consultants,
        "active": active,
        "limit": limit
    })

@router.get("/consultants/add", response_class=HTMLResponse)
async def consultant_add_form(request: Request):
    """Form to add new consultant"""
    return templates.TemplateResponse("consultant_form.html", {
        "request": request,
        "action": "add"
    })

@router.post("/consultants/add", response_class=HTMLResponse)
async def consultant_add(
    request: Request,
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    role: str = Form(...),
    seniority: str = Form(...),
    skills: str = Form(...),
    languages: str = Form(...),
    location_city: str = Form(...),
    location_country: str = Form("Sweden"),
    onsite_mode: str = Form(...),
    notes: Optional[str] = Form(None)
):
    """Add new consultant"""
    from app.main import db_repo, embedding_service
    from app.models import ConsultantIn
    
    # Parse comma-separated fields
    skills_list = [s.strip() for s in skills.split(",") if s.strip()]
    languages_list = [l.strip() for l in languages.split(",") if l.strip()]
    
    consultant_data = ConsultantIn(
        name=name,
        role=role,
        seniority=seniority,
        skills=skills_list,
        languages=languages_list,
        location_city=location_city,
        location_country=location_country,
        onsite_mode=onsite_mode,
        notes=notes,
        active=True
    )
    
    consultant = await db_repo.upsert_consultant(consultant_data)
    
    # Generate embeddings in background
    async def generate_embedding():
        text = embedding_service.prepare_consultant_text(consultant_data.dict())
        embedding = await embedding_service.create_embedding(text)
        if embedding:
            await db_repo.store_consultant_embedding(consultant.consultant_id, embedding)
    
    background_tasks.add_task(generate_embedding)
    
    # Return success message with HTMX redirect
    return f"""
    <div class="alert alert-success">
        Consultant {name} added successfully!
        <script>
            setTimeout(() => window.location.href = '/consultant/consultants', 1000);
        </script>
    </div>
    """

@router.get("/config", response_class=HTMLResponse)
async def config_view(request: Request):
    """View and manage scanning configurations"""
    from app.main import db_repo
    
    configs = await db_repo.get_all_scanning_configs()
    
    return templates.TemplateResponse("config.html", {
        "request": request,
        "configs": configs
    })

@router.get("/config/{config_id}", response_class=HTMLResponse)
async def config_details(request: Request, config_id: UUID):
    """View specific configuration details"""
    from app.main import db_repo
    
    config = await db_repo.get_scanning_config(config_id)
    overrides = await db_repo.get_source_config_overrides(config_id)
    performance = await db_repo.get_config_performance_history(config_id, days=7)
    
    return templates.TemplateResponse("config_details.html", {
        "request": request,
        "config": config,
        "overrides": overrides,
        "performance": performance
    })

@router.get("/scanner", response_class=HTMLResponse)
async def scanner_control(request: Request):
    """Scanner control panel"""
    from app.main import scanner_scheduler
    
    # Get scheduler status
    status = "running" if scanner_scheduler.scheduler.running else "stopped"
    jobs = scanner_scheduler.scheduler.get_jobs()
    
    # Get recent scan logs
    from app.main import db_repo
    recent_logs = await db_repo.get_recent_ingestion_logs(limit=10)
    
    return templates.TemplateResponse("scanner.html", {
        "request": request,
        "scheduler_status": status,
        "jobs": jobs,
        "recent_logs": recent_logs
    })

@router.post("/scanner/trigger", response_class=HTMLResponse)
async def trigger_scan(
    request: Request,
    background_tasks: BackgroundTasks,
    config_id: Optional[UUID] = Form(None)
):
    """Trigger manual scan"""
    from app.main import scanner_scheduler
    
    background_tasks.add_task(scanner_scheduler.trigger_scan_now, config_id)
    
    return """
    <div class="alert alert-info" id="scan-status">
        <div class="spinner-border spinner-border-sm me-2"></div>
        Scan triggered! Running in background...
    </div>
    <script>
        setTimeout(() => {
            document.getElementById('scan-status').innerHTML = 
                '<div class="alert alert-success">Scan initiated successfully!</div>';
        }, 2000);
    </script>
    """

@router.get("/matches", response_class=HTMLResponse)
async def matches_view(
    request: Request,
    job_id: Optional[UUID] = None,
    consultant_id: Optional[UUID] = None,
    min_score: float = Query(0.6, ge=0, le=1)
):
    """View matching results"""
    from app.main import db_repo
    
    matches = []
    if job_id:
        matches = await db_repo.get_matches_for_job(job_id, min_score)
    # Could add get_matches_for_consultant if needed
    
    return templates.TemplateResponse("matches.html", {
        "request": request,
        "matches": matches,
        "job_id": job_id,
        "consultant_id": consultant_id,
        "min_score": min_score
    })

@router.post("/matches/generate/{job_id}", response_class=HTMLResponse)
async def generate_matches(
    request: Request,
    background_tasks: BackgroundTasks,
    job_id: UUID
):
    """Generate matches for a specific job"""
    from app.main import db_repo, matching_service
    
    async def run_matching():
        job = await db_repo.get_job(job_id)
        if job:
            consultants = await db_repo.get_consultants(active_only=True, limit=100)
            for consultant in consultants:
                score, reasoning = await matching_service.calculate_match(job, consultant)
                if score > 0.5:  # Only store relevant matches
                    await db_repo.upsert_match(
                        job_id=job.job_id,
                        consultant_id=consultant.consultant_id,
                        score=score,
                        reasoning=reasoning
                    )
    
    background_tasks.add_task(run_matching)
    
    return """
    <div class="alert alert-info">
        Generating matches in background...
        <script>
            setTimeout(() => location.reload(), 3000);
        </script>
    </div>
    """

@router.get("/reports", response_class=HTMLResponse)
async def reports_view(request: Request):
    """View generated reports"""
    from app.main import reporting_service
    
    # Get latest reports
    daily_report = await reporting_service.generate_daily_report()
    weekly_report = await reporting_service.generate_weekly_report()
    
    return templates.TemplateResponse("reports.html", {
        "request": request,
        "daily_report": daily_report,
        "weekly_report": weekly_report,
        "generated_at": datetime.now(timezone.utc).isoformat()
    })