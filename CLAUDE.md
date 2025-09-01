# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

This is an AI Agent for Consultant Assignment Scanning and Matching in the Swedish consulting market. The system automatically scans for new assignments, matches them against available consultants, and suggests which companies or brokers to contact for placements.

### Original Requirements

**Target Data Sources:**
- **Consultant Brokers**: eWork, ZeroChaos/ProData, Cinode Marketplace, Brainville, Onsiter, A Society, Nikita, Keyman, TietoEVRY
- **Public Procurement**: Visma Opic, Kommers Annons
- **Job Sites**: LinkedIn (Contract/Interim roles), Uptrail, Freelance Finance
- **MVP Priority**: Brainville + Cinode + LinkedIn

**Matching Criteria:**
- Role/title (e.g., .NET developer, data engineer, solution architect)
- Seniority level (junior, mid-level, senior)
- Tech stack (Python, Azure, SAP, Java, React, etc.)
- Language requirements (Swedish/English)
- Geography/onsite vs remote

**Deliverables:**
- Daily scanning at 07:00
- Weekly report (Fridays) with trends and analysis
- Monday morning Teams/Slack brief summary
- Reports include: new assignments (24-48h), matching suggestions, top 10 prospect companies/brokers

## Project Overview

This Swedish consultant assignment matching system ingests job listings from multiple sources and matches them with consultant profiles using embeddings and multi-factor scoring algorithms. The system is designed for deployment alongside n8n for workflow automation.

## Architecture

The system uses a modular FastAPI backend with PostgreSQL 16 + pgvector for vector similarity search:

**Core Services:**
- **DatabaseRepository** (`app/repo.py`): Handles all database operations using asyncpg, manages companies/brokers with automatic alias normalization
- **EmbeddingService** (`app/embeddings.py`): Dual-mode embeddings supporting OpenAI text-embedding-3-large or local sentence-transformers
- **MatchingService** (`app/matching.py`): Weighted multi-factor matching with cosine similarity (45%), skills (25%), role (15%), language (10%), geography (5%)
- **ReportingService** (`app/reports.py`): Generates daily/weekly reports in JSON, Slack, and Teams formats
- **Web Scrapers** (`app/scrapers/`): Modular scraping system with base class, currently implements Brainville with rate limiting

**Data Flow:**
1. Jobs ingested via RSS/HTML/API → normalized company/broker creation → job storage
2. Job/consultant text prepared → embeddings generated → stored in pgvector tables
3. Matching runs vector similarity search → applies weighted scoring → stores results with detailed reasoning

## Key Commands

### Testing Scrapers
```bash
# Test connectivity to all scraping targets
python scripts/test_scraper.py --scraper connectivity

# Test Brainville scraper (saves JSON output)
python scripts/test_scraper.py --scraper brainville

# Test all scrapers
python scripts/test_scraper.py --scraper all --verbose
```

### Development Setup
```bash
# Copy environment configuration
cp .env.example .env
# Edit .env to set OPENAI_API_KEY (or use EMBEDDING_BACKEND=local)

# Start all services (PostgreSQL, Redis, API)
docker-compose up -d

# View logs
docker-compose logs -f api

# Seed database with sample data
docker-compose exec api python scripts/dev_seed.py

# Or seed with CSV file
docker-compose exec api python scripts/dev_seed.py /path/to/consultants.csv
```

### Local Development (without Docker)
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql://postgres:postgres@localhost:5433/consultant_matching
export EMBEDDING_BACKEND=local  # or openai
export OPENAI_API_KEY=your-key  # if using openai

# Run API locally
uvicorn app.main:app --reload --port 8001

# Run seed script locally
python scripts/dev_seed.py
```

### Deployment to Server
```bash
# Server deployment uses different ports to avoid conflicts:
# - PostgreSQL: 5434 (instead of 5433)
# - Redis: 6380 (instead of 6379)
# - API: 8002 (instead of 8001)

# Deploy to remote server
scp -r . root@91.98.72.10:/root/consultant-matching
ssh root@91.98.72.10 "cd /root/consultant-matching && docker-compose up -d"
```

### Database Management
```bash
# Access PostgreSQL
docker-compose exec postgres psql -U postgres -d consultant_matching

# Run schema migrations
docker-compose exec postgres psql -U postgres -d consultant_matching < db/schema.sql

# Backup database
docker-compose exec postgres pg_dump -U postgres consultant_matching > backup.sql
```

## Code Architecture Details

### Database Schema Design

The schema (`db/schema.sql`) uses normalized tables with automatic company/broker management:
- **skill_aliases/role_aliases**: Canonical mapping for fuzzy matching
- **companies**: Normalized company names with aliases array
- **brokers**: Recruitment agency management
- **jobs/consultants**: Core entities with TEXT[] arrays for skills/languages
- **job_embeddings/consultant_embeddings**: vector(3072) for similarity search
- **job_consultant_matches**: Stores match results with detailed JSON reasoning

### Embedding Pipeline

The system (`app/embeddings.py`) supports dual backends:
- **OpenAI**: Uses text-embedding-3-large (3072 dimensions), requires API key
- **Local**: Uses sentence-transformers all-mpnet-base-v2, pads to 3072 dimensions

Text preparation methods in `EmbeddingService`:
- `prepare_job_text()`: Formats job details for embedding
- `prepare_consultant_text()`: Formats consultant profile for embedding

### Matching Algorithm Implementation

The `MatchingService` (`app/matching.py`) implements sophisticated matching:
1. **Vector Search**: Uses pgvector's <=> operator for cosine distance
2. **Skills Matching**: Exact match scoring with fuzzy fallback using Levenshtein distance
3. **Role Compatibility**: Maps seniority levels to experience ranges
4. **Geographic Scoring**: City > Region > Remote with configurable weights
5. **Language Requirements**: Percentage-based scoring for required languages

### API Endpoint Patterns

All endpoints in `app/main.py` follow consistent patterns:
- **Upsert Operations**: Auto-create companies/brokers from job data
- **Background Tasks**: Async embedding generation after data insertion
- **n8n Webhooks**: Dedicated `/n8n/*` endpoints with webhook-friendly payloads
- **Report Generation**: Multiple format outputs (JSON/Slack/Teams) from single service

### Ingestion Sources

Multiple ingestion systems for different data sources:

**Web Scrapers** (`app/scrapers/`):
- **BaseScraper**: Abstract base class with rate limiting, retry logic, skill extraction
- **BrainvilleScraper**: Complete implementation for Brainville consulting portal
- Includes Swedish-specific parsing for companies, locations, dates

**Feed Ingestion** (`app/ingest/`):
- **BaseIngester**: Abstract class defining interface
- **RSSIngester**: Feedparser-based RSS/Atom feed processing

**HTML Parsing** (`app/parse/`):
- Custom parsers for HTML extraction using selectolax

## Important Implementation Notes

### Company/Broker Normalization
Jobs can specify company names as strings - the system automatically:
1. Normalizes the name (lowercase, removes AB/Ltd suffixes)
2. Creates or finds existing company record
3. Associates job with company_id

### Port Configuration
Default development ports (docker-compose.yml):
- PostgreSQL: 5433
- Redis: 6380
- API: 8001

Server deployment ports (to avoid conflicts):
- PostgreSQL: 5434
- Redis: 6380
- API: 8002

### n8n Integration Points
The system expects n8n workflows to POST to:
- `/n8n/ingest`: Bulk job ingestion
- `/n8n/match`: Trigger matching for specific jobs
- `/n8n/report`: Generate and send reports

### Environment Variables
Critical settings in .env:
- `EMBEDDING_BACKEND`: "openai" or "local" - determines embedding service
- `OPENAI_API_KEY`: Required only if EMBEDDING_BACKEND=openai
- `DATABASE_URL`: PostgreSQL connection string with pgvector extension

### Error Handling Patterns
- Database operations use try/except with proper connection cleanup
- Embedding failures logged but don't block job insertion
- Matching continues even if individual match calculations fail
- API endpoints return appropriate HTTP status codes with detail messages

## Implementation Roadmap

See `docs/IMPLEMENTATION_PLAN.md` for the detailed roadmap covering:
- **Phase 1**: Data ingestion scrapers (Brainville, Cinode, LinkedIn)
- **Phase 2**: Automation & scheduling with APScheduler
- **Phase 3**: Enhanced matching & analytics
- **Phase 4**: User interface & notifications
- **Phase 5**: Production readiness & monitoring

Latest Progress:
- ✅ Brainville web scraper fully implemented
- ✅ Base scraper infrastructure with rate limiting
- ✅ Scraper API endpoints and testing tools
- ✅ Configuration system with Swedish settings

Next priorities to implement:
- Automated daily scanning at 07:00 (APScheduler)
- Cinode and LinkedIn scrapers
- Slack/Teams notification delivery
- Admin dashboard for filtering and management
- Trend analysis and company prospect scoring