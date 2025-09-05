# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Enterprise AI Agent for Senior Consultant Assignment Matching in the Swedish market. The system targets **executive-level consultants** (C-level, architects, transformation leaders) and matches them with high-value assignments from enterprise clients and executive search firms.

### Original Requirements (Updated for Senior Focus)

**Target Data Sources:**
- **Executive Search**: Michael Page, Heidrick & Struggles, Korn Ferry (C-level placements)
- **Senior Consultant Brokers**: Cinode (premium desk), eWork (senior track), Brainville (management)
- **Enterprise Direct**: Karolinska, SEB, Swedbank, Volvo (transformation programs)
- **Public Sector**: Visma Opic, Kommers Annons (architect/leadership roles)
- **MVP Priority**: Brainville + Cinode (authenticated) + LinkedIn (premium)

**Matching Criteria (Executive Focus):**
- **Role/title**: Enterprise Architect, Business Architect, Interim CTO/CIO, Program Manager
- **Seniority**: Senior/Executive only (15+ years, C-level, architecture leads)
- **Strategic skills**: Digital Transformation, Change Management, Enterprise Architecture
- **Leadership scope**: Team size, P&L responsibility, board reporting
- **Languages**: Swedish/English/Nordic (Danish, Norwegian common for executives)
- **Geography**: Hybrid/onsite for C-level, remote possible for architects
- **Rate expectations**: 1,200-1,800 SEK/hour range

**Deliverables:**
- Daily scanning at 07:00 for C-level opportunities
- Weekly executive market analysis (Fridays)
- Monday morning executive opportunity brief
- Reports include: new senior assignments, executive matching scores, enterprise client prospects

## Project Overview

This Swedish senior consultant matching system ingests executive-level job listings and matches them with high-level consultant profiles using embeddings optimized for strategic language and executive-weighted scoring algorithms.

## Architecture

Enterprise-grade system with authenticated scraping for executive assignments:

**Core Services:**
- **DatabaseRepository** (`app/repo.py`): PostgreSQL + pgvector, optimized for senior consultant profiles
- **EmbeddingService** (`app/embeddings.py`): OpenAI embeddings tuned for strategic/leadership language
- **MatchingService** (`app/matching.py`): Executive-weighted scoring: semantic (35%), seniority (25%), role (15%), industry (10%), leadership (10%), location (5%)
- **ReportingService** (`app/reports.py`): Executive opportunity reports with prospect company tracking

**Scraping Infrastructure:**
- **BasePlaywrightScraper** (`app/scrapers/base_playwright.py`): Browser automation base class
- **PlaywrightMCPClient** (`app/scrapers/playwright_client.py`): SSE-based MCP communication
- **CinodeScraper** (`app/scrapers/cinode.py`): Authenticated Cinode premium access
- **BrainvilleScraper** (`app/scrapers/brainville.py`): Management consulting assignments

**Web UI** (`app/templates/`, `app/frontend.py`):
- Full dashboard at `/consultant/` with HTMX + Tailwind CSS
- Executive job browsing, AI matching, scraper control

**Data Flow:**
1. Executive jobs ingested via authenticated scrapers → company normalization → job storage
2. Strategic text prepared → embeddings optimized for leadership language → pgvector storage
3. Matching prioritizes seniority/leadership → applies executive weights → detailed scoring

## Key Commands

### Testing Scrapers
```bash
# Test connectivity to executive platforms
python scripts/test_scraper.py --scraper connectivity

# Test Brainville management assignments
python scripts/test_scraper.py --scraper brainville

# Test Cinode premium with authentication
python scripts/test_scraper.py --scraper cinode

# Test all scrapers including authenticated
python scripts/test_scraper.py --scraper all --verbose
```

### Adding Senior Consultants
```bash
# Add Magnus Andersson-type profiles
docker-compose exec api python scripts/add_senior_consultants.py

# Import from CSV with senior consultants
docker-compose exec api python scripts/import_consultants.py senior_consultants.csv
```

### Development Setup
```bash
# Copy environment with authentication
cp .env.example .env
# Edit .env to set:
# - OPENAI_API_KEY (better for executive terminology)
# - CINODE_USERNAME/PASSWORD (premium access)
# - PLAYWRIGHT_ENABLED=true

# Start all services including Playwright MCP
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f playwright_mcp

# Seed with senior consultant data
docker-compose exec api python scripts/add_senior_consultants.py
```

### Web UI Access
```bash
# Full dashboard for executive assignments
http://localhost:8001/consultant/

# Direct pages:
http://localhost:8001/consultant/jobs         # Senior job listings
http://localhost:8001/consultant/consultants  # Executive profiles
http://localhost:8001/consultant/matches      # AI matching
http://localhost:8001/consultant/scanner      # Scraper control
```

## Code Architecture Details

### Database Schema (Executive Optimized)

The schema includes senior-specific fields:
- **consultants**: Added `seniority`, `years_experience`, `certifications`, `rate_expectations`
- **jobs**: Added `min_years_experience`, `budget_range`, `leadership_scope`
- **companies**: Tracks enterprise clients vs brokers
- **job_consultant_matches**: Includes `seniority_score`, `leadership_score`

### Embedding Pipeline (Strategic Language)

The `EmbeddingService` is optimized for executive terminology:
- Emphasizes strategic keywords: "transformation", "architecture", "leadership"
- Weights industry experience and certifications higher
- Includes leadership scope in text preparation

### Executive Matching Algorithm

The `MatchingService` uses executive-specific weights:
1. **Seniority Filter**: Excludes non-senior automatically
2. **Strategic Similarity**: 35% weight on leadership language
3. **Experience Match**: 25% weight on years/level match
4. **Industry Bonus**: 10% for relevant sector experience
5. **Leadership Scope**: 10% for team/budget responsibility

### Playwright MCP Integration

For authenticated executive platforms:
- **playwright_mcp service**: Runs Chrome in Docker with security hardening
- **BasePlaywrightScraper**: Abstract class for browser automation
- **CinodeScraper**: Handles login flow and premium job extraction
- **SSE protocol**: Real-time browser control via MCP

### Senior Consultant Configuration

**Profiles** (`config/consultant_profiles.md`):
- Swedish executive titles mapping
- Seniority indicators and filters
- Rate expectation ranges
- Red/green flags for assignments

**Keywords** (`config/senior_consultant_keywords.md`):
- C-level and architecture terms
- Strategic skill requirements
- Industry-specific terminology
- Leadership scope indicators

## Important Implementation Notes

### Executive Assignment Filtering
Jobs are automatically filtered for seniority:
1. Minimum 10+ years experience requirement
2. Senior/Lead/Chief/Head titles prioritized
3. Junior/Entry positions excluded
4. Strategic/transformation roles scored higher

### Authentication Management
Cinode and LinkedIn require authentication:
- Credentials stored in `.env`
- Playwright MCP handles session persistence
- Automatic re-login on session expiry
- Rate limiting to avoid detection

### Port Configuration
Default development ports:
- PostgreSQL: 5433
- Redis: 6380
- API: 8001
- Playwright MCP: 8931

### Environment Variables (Executive Setup)
Critical settings:
- `EMBEDDING_BACKEND`: Use "openai" for better executive language
- `OPENAI_API_KEY`: Required for strategic embeddings
- `CINODE_USERNAME/PASSWORD`: Premium platform access
- `PLAYWRIGHT_ENABLED`: Must be true for authenticated scrapers

## Typical Consultant Profile

**Magnus Andersson** - Enterprise Architect / Business Architect
- 20+ years experience
- Former CTO, Interim CTO multiple companies
- Executive MBA
- Expertise: Digital Strategy, Enterprise Architecture, Change Management
- Industries: Healthcare (Karolinska), Finance (Postgirot), AgriTech (DeLaval)
- Languages: Swedish, English, Danish, Norwegian
- Rate: 1,500-1,800 SEK/hour

## Implementation Status (September 2025)

### ✅ Completed Components

**Core Infrastructure:**
- ✅ FastAPI backend with PostgreSQL + pgvector
- ✅ EmbeddingService with OpenAI integration  
- ✅ MatchingService with executive-weighted scoring
- ✅ DatabaseRepository with full CRUD operations
- ✅ Docker containerization (API, DB, Redis)
- ✅ APScheduler for automated scanning (07:00 daily)

**Web Scraping System:**
- ✅ Base Playwright scraper infrastructure with rate limiting
- ✅ Playwright MCP integration for browser automation
- ✅ Brainville scraper fully implemented and tested
- ✅ Cinode scraper with authentication capability
- ✅ Scraper API endpoints and testing tools

**User Interface:**
- ✅ Complete dark theme UI with glass morphism effects
- ✅ Executive dashboard with real-time stats
- ✅ User management system (admin/manager/viewer roles)
- ✅ Job/consultant/match management pages
- ✅ Professional login page with gradient design

**Deployment:**
- ✅ Deployed on server 91.98.72.10
- ✅ Running on internal ports (API:8002, DB:5444, Redis:6390)
- ✅ Nginx proxy configured via n8n.cognova.net
- ✅ HTTPS access through existing SSL infrastructure

### 🔄 Current Issues

**Authentication Problem:**
- 🔄 Login page accessible at https://n8n.cognova.net/auth/login
- 🔄 Admin credentials work but login doesn't complete properly
- 🔄 JWT token signature verification failing
- 🔄 Cookie-based session not persisting through nginx proxy

**Access URLs:**
- **Login:** https://n8n.cognova.net/auth/login
- **Dashboard:** https://n8n.cognova.net/consultant/
- **Admin Credentials:** admin / admin123

### 📋 Tomorrow's Priority

**Fix Authentication Flow:**
1. Debug JWT secret key consistency between creation and validation
2. Check cookie domain/path settings for n8n.cognova.net proxy
3. Verify nginx proxy headers for authentication
4. Test end-to-end login → dashboard flow

**Container Status:**
- ✅ consultant_api (FastAPI - running)
- ✅ consultant_postgres (DB - running)  
- ✅ consultant_redis (Cache - running)
- ❌ consultant_playwright_mcp (failed, non-critical)

### 🎯 Executive Profile Target

**Typical Senior Consultant:**
- **Magnus Andersson**: 20+ years, Enterprise/Business Architect
- Former CTO/Interim CTO, Executive MBA
- Rate: 1,500-1,800 SEK/hour
- Industries: Healthcare, Finance, AgriTech, Digital Transformation

### 🚀 Next Features (After Auth Fix)

- LinkedIn premium scraper for executive roles
- Slack/Teams notification delivery system
- Weekly executive market analysis reports
- Company prospect scoring for enterprise clients
- Public procurement integration (Visma Opic)