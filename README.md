# Swedish Enterprise Consultant Assignment Matching System

🚀 **LIVE SYSTEM** - AI-powered platform for matching senior-level consultants with executive assignments in the Swedish consulting market.

**🌐 Live Dashboard:** https://n8n.cognova.net/consultant/

## Current Status (September 2025)

✅ **DEPLOYED & OPERATIONAL**
- Running on production server (91.98.72.10)
- Full authentication system working
- Dark theme dashboard with glass morphism design
- Automated job scanning and AI matching
- PostgreSQL + pgvector for semantic search
- Docker containerized deployment

### Login Credentials
- **Username:** `admin`
- **Password:** `admin`
- **URL:** https://n8n.cognova.net/auth/login

## System Overview

This enterprise-grade system targets **senior consultants and executives** with 15+ years experience:

**Target Profiles:**
- **C-Level:** Interim CTO/CIO, Chief Digital Officers, Transformation Directors
- **Enterprise Architects:** Business/Solution/Data Architects with strategic roles
- **Program Leaders:** Digital transformation, change management, M&A integration
- **Technical Executives:** Head of Development, R&D Directors, Engineering VPs

**Rate Range:** 1,200-1,800 SEK/hour for executive assignments

## Architecture

### Production Environment
- **Server:** 91.98.72.10 (Ubuntu)
- **Containers:**
  - `consultant_api` (FastAPI + Python) - Port 8002
  - `consultant_postgres` (PostgreSQL 16 + pgvector) - Port 5444
  - `consultant_redis` (Cache) - Port 6390
- **Web Server:** Nginx proxy with SSL
- **Scheduler:** APScheduler for automated scanning (07:00 daily)

### Key Features

**🔍 Multi-Source Job Ingestion:**
- Brainville (Management consulting assignments)
- Cinode (Premium authenticated access)
- eWork/Verama (Senior consultant track)
- Manual job upload with AI parsing

**🤖 AI-Powered Matching:**
- OpenAI embeddings optimized for strategic language
- Executive-weighted scoring algorithm
- Semantic similarity for leadership skills
- Seniority and industry filtering

**📊 Executive Dashboard:**
- Real-time assignment statistics
- Company prospect tracking
- Consultant profile management
- Match scoring and recommendations
- Automated report generation

## Web Dashboard Features

### Main Sections
- **📈 Dashboard:** Executive metrics, recent matches, market trends
- **💼 Jobs:** Browse senior assignments, filter by industry/location
- **👥 Consultants:** Manage executive profiles, skills, certifications
- **🎯 Matches:** AI-powered matching with detailed scoring explanations
- **🔍 Scanner:** Control automated scrapers, view scraping status
- **📋 Reports:** Daily briefs, weekly market analysis
- **⚙️ Configuration:** System settings, scraper credentials

### Authentication & Security
- JWT-based authentication with HTTP-only cookies
- Role-based access (admin/manager/viewer)
- Session management with auto-logout
- Secure password hashing (bcrypt)

## API Endpoints

### Core Functionality
```
GET  /consultant/                    # Main dashboard
GET  /consultant/jobs               # Job listings
GET  /consultant/consultants        # Consultant profiles
GET  /consultant/matches            # Matching results
POST /auth/login                    # Authentication
GET  /health                        # System health
```

### Data Management
```
POST /jobs/upsert                   # Add/update jobs
POST /consultants                   # Add consultants
POST /match/job/{id}                # Generate matches
GET  /reports/summary               # Executive reports
```

### Scraper Control
```
POST /scrape/brainville            # Manual scraping
GET  /scheduler/status             # Check automation
POST /scheduler/start              # Start scheduling
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

## Data Sources

### Active Scrapers
1. **Brainville** - Management consulting assignments
2. **Cinode** - Premium platform with authentication
3. **eWork/Verama** - Senior consultant marketplace

### Planned Integrations
- LinkedIn premium job scraping
- Michael Page executive search
- Heidrick & Struggles C-level positions
- Enterprise client direct feeds

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

## Matching Algorithm

### Executive-Weighted Scoring
1. **Strategic Similarity** (35%) - Leadership language matching
2. **Seniority Match** (25%) - Years experience + role level
3. **Role Alignment** (15%) - Title and responsibility match
4. **Industry Experience** (10%) - Sector-specific knowledge
5. **Leadership Scope** (10%) - Team size, P&L responsibility
6. **Location Preference** (5%) - Geographic matching

### Filtering Criteria
- Minimum 15 years experience for executive roles
- Strategic keywords: transformation, architecture, interim, change
- Rate expectations: 1,200+ SEK/hour
- Seniority indicators: Head of, Chief, Director, VP, Architect

## Monitoring & Maintenance

### Automated Operations
- **Daily Scanning:** 07:00 CET job ingestion
- **Weekly Reports:** Friday executive market analysis
- **Monday Briefs:** Weekly opportunity summaries
- **Health Checks:** System status monitoring

### Manual Operations
- Consultant profile management via web dashboard
- Manual job upload and parsing
- Scraper credential updates
- Match quality review and tuning

## Security & Compliance

- Secure authentication with role-based access
- HTTPS/SSL encryption for all communications
- Database credentials encrypted and rotated
- Session management with secure cookies
- Input validation and SQL injection protection

## Support & Issues

For system issues or feature requests:
1. Check the live dashboard: https://n8n.cognova.net/consultant/
2. Review logs via docker-compose logs
3. Database queries via PostgreSQL admin tools
4. System health at /health endpoint

---

**Status:** ✅ Production Ready | **Last Updated:** September 2025 | **Version:** 1.0.0