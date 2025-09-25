# Swedish Consultant Assignment Scanning & Matching System

🔍 **SCANNING-FIRST DASHBOARD** - Continuously monitors Swedish consultant assignment portals with layered matching, analytics, and intelligence features.

**🌐 Live Dashboard:** https://n8n.cognova.net/consultant/

## Current Status (September 2025)

⚠️ **SYSTEM AT 10% CAPACITY** - Focus shifted to core scanning functionality
- Running on production server (91.98.72.10)
- Basic authentication system operational
- Core scanning infrastructure for Swedish consultant portals
- PostgreSQL + pgvector foundation ready
- Docker containerized deployment

### Login Credentials
- **Username:** `admin`
- **Password:** `admin`
- **URL:** https://n8n.cognova.net/auth/login

## System Overview

**Scanning-first web dashboard** that continuously monitors Swedish consultant assignment portals, surfaces results within the application, and layers on matching, analytics, recommendations, and company intelligence.

**Core Principle:** Scanning must operate even if no consultant CVs exist; configuration lives in the UI so operators can tune criteria before any matching data is present.

### System Phases

- **Phase 1 – Core Scanning:** Verama → Cinode → Keyman with shared configuration UI, scheduler control, and in-app monitoring
- **Phase 2 – Matching & Consultant Management:** Activate consultant profiles, CV ingestion, embeddings, and matching workflows
- **Phase 3 – Intelligence & Operations:** Expand analytics dashboards, company intelligence tracking, alert/recommendation centers

## Architecture

### Production Environment
- **Server:** 91.98.72.10 (Ubuntu)
- **Containers:**
  - `consultant_api` (FastAPI + Python) - Port 8002
  - `consultant_postgres` (PostgreSQL 16 + pgvector) - Port 5444
  - `consultant_redis` (Cache) - Port 6390
- **Web Server:** Nginx proxy with SSL
- **Scheduler:** APScheduler for automated scanning (07:00 daily)

### Current Scanning Priorities

1. **Verama** – Investigate and prefer official/API access; use Playwright automation only when no stable endpoint exists
2. **Cinode** – Support authenticated scraping/API access under shared configuration contract
3. **Keyman** – Add coverage once shared configuration plumbing is in place
4. **Additional sources** – Brainville, Emagine, Onsiter, A Society, Nikita, TietoEVRY, Visma Opic, Kommers, LinkedIn, Uptrail, Freelance Finance

**Configuration:** All scanners read shared criteria from `scanning_configs` + `source_config_overrides` for centralized operator control.

### Core Components

**🔍 Scanning Infrastructure:**
- Base HTTP and Playwright abstractions
- Shared configuration system
- Rate limiting and authentication management
- Automated scheduling with UI controls

**📊 Data Foundation:**
- PostgreSQL + pgvector for embeddings
- Job ingestion and logging
- Configuration management tables
- Future matching and analytics support

## Architecture Components

### Core Services
- **DatabaseRepository (`app/repo.py`)** – Async access to Postgres + pgvector, managing jobs, consultants, embeddings, matches, ingestion logs, and scanning config tables
- **EmbeddingService (`app/embeddings.py`)** – Wraps OpenAI or deterministic local embeddings; currently uses simple text preparation
- **MatchingService (`app/matching.py`)** – Creates embeddings on demand, scores matches (cosine, skills, role, language, geo)
- **ReportingService (`app/reports.py`)** – Aggregates jobs/matches/skills/source stats; powers dashboard analytics
- **Scheduler (`app/scheduler.py`)** – APScheduler orchestration for daily/weekly scans, weekly reports, Monday briefs, optimization routines
- **Scrapers (`app/scrapers/`)** – Base HTTP and Playwright abstractions plus current implementations for Brainville, Cinode, and Verama/eWork

### Web Interface
- **Auth (`app/auth.py`, `app/auth_routes.py`)** – JWT-based login with admin/manager/viewer roles, password hashing, refresh tokens
- **Web UI (`app/frontend.py`, `app/templates/`)** – HTMX/Tailwind dashboard at `/consultant/...` with scanning controls, job listings, configuration pages
- **Scanner Control:** UI control at `/consultant/scanner` for scheduling and monitoring
- **Configuration Management:** Shared scanning criteria configuration via web interface

## Key Commands

### Server Operations
```bash
# Run FastAPI on the server
ssh <user>@91.98.72.10 "cd /opt/Consultant-Assignment-Scanning-Matching && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

# Execute existing scrapers manually
curl -X POST http://91.98.72.10:8000/scrape/brainville
curl -X POST http://91.98.72.10:8000/scrape/verama
curl -X POST http://91.98.72.10:8000/scrape/cinode

# Regenerate requirements lock if deps change
pip-compile requirements.in
```

### API Endpoints
```
GET  /consultant/                    # Main dashboard
GET  /consultant/jobs               # Job listings
GET  /consultant/scanner            # Scanner controls
POST /auth/login                    # Authentication
GET  /health                        # System health

# Scraper endpoints
POST /scrape/brainville            # Manual scraping
POST /scrape/verama                 # Verama scraping
POST /scrape/cinode                # Cinode scraping
GET  /scheduler/status             # Check automation status
```

## Technology Stack

**Backend:**
- FastAPI (Python web framework)
- PostgreSQL 16 with pgvector extension
- OpenAI embeddings for semantic matching
- Redis for caching and sessions
- APScheduler for automated tasks

**Frontend:**
- Server-side rendered HTML with Jinja2 templates
- Tailwind CSS with dark theme
- HTMX for dynamic interactions
- Glass morphism design system
- Font Awesome icons

**Infrastructure:**
- Docker & Docker Compose
- Nginx reverse proxy
- SSL/HTTPS with Let's Encrypt
- Ubuntu 20.04 LTS server

## Scanning Configuration & Expectations

### Configuration Principles
- New scanners must be configurable via shared tables (`scanning_configs` + `source_config_overrides`)
- Expose controls in the UI for operator tuning
- Scanning can run without consultants; matching features should gracefully report "no consultant data"
- Prefer API integrations when possible; Playwright is a fallback
- Log screenshots/snapshots for debugging
- Keep rate limits and authentication details in `.env`

### Data Sources Priority
1. **Verama** - Investigate official/API access first; Playwright fallback
2. **Cinode** - Authenticated scraping/API access under shared configuration contract
3. **Keyman** - Add coverage once shared configuration plumbing is in place
4. **Additional sources** - Brainville, Emagine, Onsiter, A Society, Nikita, TietoEVRY, Visma Opic, Kommers, LinkedIn, Uptrail, Freelance Finance

## Deployment Information

### Server Details
- **Host:** 91.98.72.10
- **OS:** Ubuntu with Docker
- **Database:** PostgreSQL with pgvector for embeddings
- **Ports:** API (8002), DB (5444), Redis (6390)
- **SSL:** Managed through existing nginx configuration

### Environment Configuration
```env
# Core Settings
DATABASE_URL=postgresql://postgres:postgres@consultant_postgres:5432/consultant_matching
OPENAI_API_KEY=configured
SECRET_KEY=production-secret

# Scraper Authentication
CINODE_USERNAME=configured
CINODE_PASSWORD=configured
PLAYWRIGHT_ENABLED=true

# Scheduling
SCHEDULER_ENABLED=true
SCAN_TIME=07:00
```

## Implementation Notes & TODO Alignment

### Current Focus Areas
- Remove reliance on Teams/email notifications from scheduler delivery flows and build equivalent in-app alert panels
- Flesh out `/consultant/jobs` filters, analytics dashboards, company tracking, and recommendation/alert views per the updated system spec
- Prioritize implementing Verama → Cinode → Keyman pipelines before expanding to other sources
- Confirm Verama API usage (`https://app.verama.com/api/public/job-requests`) is stable and capture any auth/header requirements for production
- Keep downstream modules (matching, analytics, company intelligence, recommendations, alerting) in mind when shaping schemas and APIs

### Future Development
- **Matching & Analytics:** Matching logic coordinates weight changes, new fields, or schema migrations with actual database structures
- **Reporting:** Should evolve to feed in-app dashboards rather than external messaging
- **Adaptive Configuration:** Future learning features rely on accurate ingestion logs and performance metrics

## Security & Compliance

- Store API keys and login details in `.env`; never commit secrets
- Respect portal terms of service; include rate limiting and backoff strategies in scrapers
- JWT-based authentication with role-based access (admin/manager/viewer)
- HTTPS/SSL encryption for all communications
- Input validation and SQL injection protection

## Support & Issues

For system issues or feature requests:
1. Check the live dashboard: https://n8n.cognova.net/consultant/
2. Review logs via docker-compose logs on server 91.98.72.10
3. Database queries via PostgreSQL admin tools
4. System health at /health endpoint
5. Scanner status and controls at `/consultant/scanner`

---

**Status:** ⚠️ 10% Capacity - Scanning Foundation | **Last Updated:** September 2025 | **Focus:** Core scanning infrastructure with future matching/analytics layers