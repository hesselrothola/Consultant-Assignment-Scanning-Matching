"""
Frontend routes for the consultant matching system
Uses FastAPI with HTMX for dynamic interactions without heavy JavaScript
"""

import re

from fastapi import APIRouter, Request, Form, Query, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List
import os
from datetime import datetime, timezone
from uuid import UUID
# from app.auth import get_current_user, require_user  # Removed to avoid circular imports

from app.repo import (
    DEFAULT_EXECUTIVE_LANGUAGES,
    DEFAULT_EXECUTIVE_LOCATIONS,
    DEFAULT_EXECUTIVE_ONSITE,
    DEFAULT_EXECUTIVE_ROLES,
    DEFAULT_EXECUTIVE_SENIORITY,
    DEFAULT_EXECUTIVE_SKILLS,
    DEFAULT_VERAMA_COUNTRIES,
    DEFAULT_VERAMA_LEVELS,
)

router = APIRouter(prefix="/consultant", tags=["frontend"])

# Setup Jinja2 templates
templates = Jinja2Templates(directory="app/templates")


def _split_to_list(value: str, *, to_upper: bool = False, to_lower: bool = False) -> List[str]:
    """Split textarea or comma-separated input into a list of unique strings."""
    if not value:
        return []

    items = []
    for part in re.split(r'[\n,]', value):
        cleaned = part.strip()
        if not cleaned:
            continue
        if to_upper:
            cleaned = cleaned.upper()
        elif to_lower:
            cleaned = cleaned.lower()
        items.append(cleaned)

    # Preserve order while removing duplicates
    seen = set()
    unique_items = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        unique_items.append(item)
    return unique_items


def _list_to_text(values: Optional[List[str]], separator: str = "\n") -> str:
    if not values:
        return ""
    return separator.join(values)

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_alt(request: Request):
    """Alternative dashboard route"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Consultant Matching Dashboard",
        "user": {"username": "admin", "role": "admin"}
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

    manual_config = await db_repo.ensure_manual_scanning_config()
    manual_override = manual_config.get('manual_override') or {}
    override_params = manual_override.get('parameter_overrides') or {}

    target_roles = manual_config.get('target_roles') or DEFAULT_EXECUTIVE_ROLES
    target_skills = manual_config.get('target_skills') or DEFAULT_EXECUTIVE_SKILLS
    target_locations = manual_config.get('target_locations') or DEFAULT_EXECUTIVE_LOCATIONS
    languages = manual_config.get('languages') or DEFAULT_EXECUTIVE_LANGUAGES
    onsite_modes = manual_config.get('onsite_modes') or DEFAULT_EXECUTIVE_ONSITE
    seniority_levels = manual_config.get('seniority_levels') or DEFAULT_EXECUTIVE_SENIORITY
    countries = override_params.get('countries') or DEFAULT_VERAMA_COUNTRIES
    levels = override_params.get('levels') or DEFAULT_VERAMA_LEVELS
    target_keywords = override_params.get('target_keywords') or target_roles

    manual_form = {
        "config_id": str(manual_config['config_id']),
        "target_roles_text": _list_to_text(target_roles),
        "target_skills_text": _list_to_text(target_skills),
        "target_keywords_text": _list_to_text(target_keywords),
        "target_locations_text": _list_to_text(target_locations),
        "languages_text": ', '.join(languages),
        "onsite_modes_text": ', '.join(onsite_modes),
        "seniority_levels_text": ', '.join(seniority_levels),
        "countries_text": ', '.join(countries),
        "levels_text": ', '.join(levels),
        "updated_at": manual_config.get('updated_at'),
    }

    return templates.TemplateResponse("scanner.html", {
        "request": request,
        "scheduler_status": status,
        "jobs": jobs,
        "recent_logs": recent_logs,
        "manual_form": manual_form,
        "manual_config": manual_config,
        "manual_override": override_params
    })


@router.post("/scanner/manual-config", response_class=HTMLResponse)
async def update_manual_scanner_config(
    request: Request,
    config_id: UUID = Form(...),
    target_roles: str = Form(""),
    target_keywords: str = Form(""),
    target_skills: str = Form(""),
    target_locations: str = Form(""),
    languages: str = Form(""),
    onsite_modes: str = Form(""),
    seniority_levels: str = Form(""),
    countries: str = Form(""),
    levels: str = Form("")
):
    """Update manual scanning criteria used by the Verama scraper."""
    from app.main import db_repo

    roles_list = _split_to_list(target_roles)
    keywords_list = _split_to_list(target_keywords)
    skills_list = _split_to_list(target_skills)
    locations_list = _split_to_list(target_locations)
    languages_list = _split_to_list(languages, to_upper=True)
    onsite_list = _split_to_list(onsite_modes, to_lower=True)
    seniority_list = _split_to_list(seniority_levels)
    countries_list = _split_to_list(countries, to_upper=True)
    levels_list = _split_to_list(levels, to_upper=True)

    if not roles_list:
        roles_list = DEFAULT_EXECUTIVE_ROLES
    if not keywords_list:
        keywords_list = roles_list
    if not skills_list:
        skills_list = DEFAULT_EXECUTIVE_SKILLS
    if not locations_list:
        locations_list = DEFAULT_EXECUTIVE_LOCATIONS
    if not languages_list:
        languages_list = DEFAULT_EXECUTIVE_LANGUAGES
    if not onsite_list:
        onsite_list = DEFAULT_EXECUTIVE_ONSITE
    if not seniority_list:
        seniority_list = DEFAULT_EXECUTIVE_SENIORITY
    if not countries_list:
        countries_list = DEFAULT_VERAMA_COUNTRIES
    if not levels_list:
        levels_list = DEFAULT_VERAMA_LEVELS

    overrides = {
        'countries': countries_list,
        'languages': languages_list,
        'levels': levels_list,
        'target_roles': roles_list,
        'target_keywords': keywords_list,
        'onsite_modes': onsite_list,
    }

    await db_repo.update_manual_scanning_config(
        config_id=config_id,
        target_skills=skills_list,
        target_roles=roles_list,
        seniority_levels=seniority_list,
        target_locations=locations_list,
        languages=languages_list,
        onsite_modes=onsite_list,
        contract_durations=[],
        source_overrides=overrides
    )

    return HTMLResponse(
        """
        <div class=\"text-green-400 text-sm mt-2\">Manual criteria saved. Future scans will use the updated settings.</div>
        """
    )

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

@router.get("/users", response_class=HTMLResponse)
async def users_management(request: Request):
    """User management page (admin only)"""
    # Check authentication
    auth_result = require_auth(request)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    
    # Check if user is admin
    if auth_result.get('role') != 'admin':
        return HTMLResponse(
            content="<h1>403 Forbidden</h1><p>Admin access required</p>",
            status_code=403
        )
    
    from app.main import db_repo
    
    # Get all users from database
    users = await db_repo.get_all_users()
    
    return templates.TemplateResponse("users.html", {
        "request": request,
        "title": "User Management",
        "user": auth_result,
        "users": users
    })

@router.post("/users/add", response_class=HTMLResponse)
async def add_user(
    request: Request,
    username: str = Form(...),
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...)
):
    """Add new user (admin only)"""
    # Check authentication
    auth_result = require_auth(request)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    
    # Check if user is admin
    if auth_result.get('role') != 'admin':
        return HTMLResponse(content="<h1>403 Forbidden</h1>", status_code=403)
    
    from app.main import db_repo
    from app.auth import get_password_hash
    
    # Hash the password
    hashed_password = get_password_hash(password)
    
    # Create user in database
    try:
        await db_repo.create_user(
            username=username,
            full_name=full_name,
            email=email,
            hashed_password=hashed_password,
            role=role,
            is_active=True
        )
    except Exception as e:
        return HTMLResponse(
            content=f"<script>alert('Error creating user: {str(e)}'); window.location.href='/consultant/users';</script>"
        )
    
    return RedirectResponse(url="/consultant/users", status_code=303)

@router.post("/users/{user_id}/reset-password", response_class=HTMLResponse)
async def reset_user_password(
    request: Request,
    user_id: UUID,
    new_password: str = Form(...)
):
    """Reset user password (admin only)"""
    # Check authentication
    auth_result = require_auth(request)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    
    # Check if user is admin
    if auth_result.get('role') != 'admin':
        return HTMLResponse(content="<h1>403 Forbidden</h1>", status_code=403)
    
    from app.main import db_repo
    from app.auth import get_password_hash
    
    # Hash the new password
    hashed_password = get_password_hash(new_password)
    
    # Update password in database
    try:
        await db_repo.update_user_password(user_id, hashed_password)
        return HTMLResponse(
            content="<div class='alert alert-success'>Password reset successfully!</div>",
            headers={"HX-Trigger": "password-reset-success"}
        )
    except Exception as e:
        return HTMLResponse(
            content=f"<div class='alert alert-danger'>Error: {str(e)}</div>",
            status_code=500
        )

@router.post("/users/{user_id}/toggle-active", response_class=HTMLResponse)
async def toggle_user_active(request: Request, user_id: UUID):
    """Toggle user active status (admin only)"""
    # Check authentication
    auth_result = require_auth(request)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    
    # Check if user is admin
    if auth_result.get('role') != 'admin':
        return HTMLResponse(content="<h1>403 Forbidden</h1>", status_code=403)
    
    from app.main import db_repo
    
    try:
        # Get current user status
        user = await db_repo.get_user_by_id(str(user_id))
        if user:
            # Toggle active status
            await db_repo.update_user_active_status(user_id, not user['is_active'])
            return HTMLResponse(
                content="<script>window.location.reload();</script>"
            )
        else:
            return HTMLResponse(content="User not found", status_code=404)
    except Exception as e:
        return HTMLResponse(
            content=f"<div class='alert alert-danger'>Error: {str(e)}</div>",
            status_code=500
        )

@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
async def edit_user_form(request: Request, user_id: UUID):
    """Get edit user form (admin only)"""
    # Check authentication
    auth_result = require_auth(request)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    
    # Check if user is admin
    if auth_result.get('role') != 'admin':
        return HTMLResponse(content="<h1>403 Forbidden</h1>", status_code=403)
    
    from app.main import db_repo
    
    user = await db_repo.get_user_by_id(str(user_id))
    if not user:
        return HTMLResponse(content="User not found", status_code=404)
    
    # Return edit form HTML (for HTMX)
    return f"""
    <div class="modal-content">
        <h3>Edit User: {user['username']}</h3>
        <form hx-post="/consultant/users/{user_id}/update" hx-target="#edit-result">
            <div class="form-group">
                <label>Full Name</label>
                <input type="text" name="full_name" value="{user['full_name']}" class="form-control">
            </div>
            <div class="form-group">
                <label>Email</label>
                <input type="email" name="email" value="{user['email']}" class="form-control">
            </div>
            <div class="form-group">
                <label>Role</label>
                <select name="role" class="form-control">
                    <option value="viewer" {"selected" if user['role'] == "viewer" else ""}>Viewer</option>
                    <option value="manager" {"selected" if user['role'] == "manager" else ""}>Manager</option>
                    <option value="admin" {"selected" if user['role'] == "admin" else ""}>Admin</option>
                </select>
            </div>
            <button type="submit" class="btn btn-primary">Update</button>
            <button type="button" onclick="closeEditModal()" class="btn btn-secondary">Cancel</button>
        </form>
        <div id="edit-result"></div>
    </div>
    """

@router.post("/users/{user_id}/update", response_class=HTMLResponse)
async def update_user(
    request: Request,
    user_id: UUID,
    full_name: str = Form(...),
    email: str = Form(...),
    role: str = Form(...)
):
    """Update user details (admin only)"""
    # Check authentication
    auth_result = require_auth(request)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    
    # Check if user is admin
    if auth_result.get('role') != 'admin':
        return HTMLResponse(content="<h1>403 Forbidden</h1>", status_code=403)
    
    from app.main import db_repo
    
    try:
        await db_repo.update_user(
            user_id=str(user_id),
            full_name=full_name,
            email=email,
            role=role
        )
        return HTMLResponse(
            content="<script>alert('User updated successfully!'); window.location.reload();</script>"
        )
    except Exception as e:
        return HTMLResponse(
            content=f"<div class='alert alert-danger'>Error: {str(e)}</div>",
            status_code=500
        )
