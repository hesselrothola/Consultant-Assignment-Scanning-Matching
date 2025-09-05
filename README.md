# Enterprise Consultant Assignment Matching System

AI-powered platform for matching **senior-level consultants** (C-level, architects, transformation leaders) with executive assignments in the Swedish consulting market.

## Target Consultant Profiles

This system is optimized for **executive and senior technical consultants** with 10-20+ years experience:
- **Management**: Interim CTO/CIO, Digital Transformation Leaders, Change Managers
- **Architecture**: Enterprise Architects, Business Architects, Solution Architects  
- **Leadership**: Program Managers, R&D Directors, Head of Development
- **Specialists**: Senior Data Architects, BI Strategy Leads, Agile Coaches

Typical rate expectations: **1,200-1,800 SEK/hour**

## Features

- **Multi-source job ingestion** from executive search firms and enterprise clients
- **Authenticated scraping** via Playwright MCP for Cinode, LinkedIn premium jobs
- **AI-powered matching** optimized for strategic/leadership language
- **Seniority filtering** to exclude junior positions automatically
- **Executive search focus** targeting high-value transformation assignments
- **Automated reports** highlighting C-level and architecture opportunities
- **Company intelligence** tracking enterprise clients and executive recruiters

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/consultant-matching.git
cd consultant-matching

# Copy environment configuration
cp .env.example .env
# Edit .env to set:
#   - OPENAI_API_KEY (for embeddings)
#   - CINODE_USERNAME / CINODE_PASSWORD (for authenticated scraping)
#   - PLAYWRIGHT_ENABLED=true (for JavaScript sites)

# Start all services including Playwright MCP
docker-compose up -d

# Add senior consultant profiles
docker-compose exec api python scripts/add_senior_consultants.py

# Test Cinode scraper for executive assignments
docker-compose exec api python scripts/test_scraper.py --scraper cinode
```

## API Endpoints

### Executive Jobs
- `POST /api/jobs` - Ingest C-level/architect positions
- `GET /api/jobs?seniority=senior` - List senior-level assignments
- `GET /api/jobs/{id}` - Get assignment details with rate expectations

### Senior Consultants  
- `POST /api/consultants` - Add enterprise consultant profile
- `GET /api/consultants?seniority=senior` - List executive consultants
- `GET /api/consultants/{id}` - Get consultant with certifications/MBA

### Strategic Matching
- `POST /api/match/job/{job_id}` - Match executives to transformation roles
- `GET /api/matches/job/{job_id}?min_score=0.7` - High-confidence matches only

### Executive Reports
- `POST /api/reports/daily` - Daily C-level opportunity scan
- `POST /api/reports/weekly` - Weekly executive market analysis
- `GET /api/reports/prospects` - Top enterprise clients hiring

### Authenticated Scrapers
- `POST /api/scrapers/cinode/run` - Scan Cinode premium assignments
- `POST /api/scrapers/linkedin/run` - Scan LinkedIn executive positions
- `GET /api/scrapers/status` - Check scraper authentication status

## Web UI Dashboard

Access the full-featured web dashboard at: **http://localhost:8001/consultant/**

- **Dashboard**: Executive assignment overview and analytics
- **Jobs**: Browse and filter senior-level positions
- **Consultants**: Manage enterprise consultant profiles
- **Matches**: AI-powered matching with detailed scoring
- **Scanner**: Control authenticated scrapers
- **Reports**: Daily/weekly executive market analysis
- **Configuration**: System settings and scraper credentials

## Configuration

### Environment Variables

```env
# Embedding Service (optimized for strategic language)
EMBEDDING_BACKEND=openai  # Better for executive terminology
OPENAI_API_KEY=your-api-key-here

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/consultant_matching

# Authenticated Scraping (Executive Platforms)
PLAYWRIGHT_ENABLED=true
CINODE_USERNAME=your-email@company.com  
CINODE_PASSWORD=your-password
LINKEDIN_USERNAME=premium-account@company.com
LINKEDIN_PASSWORD=your-password

# Redis (for caching executive search results)
REDIS_URL=redis://localhost:6380
```

### Senior Consultant Matching Weights

The system uses specialized weights for executive matching:

```python
{
    "semantic_similarity": 0.35,  # Strategic language understanding
    "seniority_match": 0.25,      # Must be senior/C-level
    "role_compatibility": 0.15,   # Architecture/management fit
    "industry_experience": 0.10,  # Domain expertise bonus
    "leadership_scope": 0.10,     # Team/budget responsibility
    "location_flexibility": 0.05  # Less critical for executives
}
```

## Architecture

The system uses enterprise-grade architecture with authenticated scraping:

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   n8n       │────▶│   FastAPI    │────▶│  PostgreSQL  │
│  Workflows  │     │   Backend    │     │   + pgvector │
└─────────────┘     └──────────────┘     └──────────────┘
                           │
                    ┌──────▼──────┐
                    │  Services:   │
                    ├──────────────┤
                    │ OpenAI API   │ (Executive language embeddings)
                    │ Playwright   │ (Cinode/LinkedIn auth)
                    │ MCP Server   │ (Browser automation)
                    └──────────────┘
                           │
                    ┌──────▼──────┐
                    │ Data Sources │
                    ├──────────────┤
                    │ Cinode       │ (Premium assignments)
                    │ LinkedIn     │ (Executive positions)
                    │ Brainville   │ (Management consulting)
                    │ eWork        │ (Senior desk)
                    └──────────────┘
```

### Playwright MCP Integration

For authenticated sites requiring JavaScript rendering:

1. **Playwright MCP Server** runs in Docker with Chrome
2. **BasePlaywrightScraper** provides browser automation interface
3. **CinodeScraper** handles login and premium job extraction
4. **SSE Communication** for real-time browser control

## Typical Consultant Profile Example

**Magnus Andersson** - Enterprise Architect / Business Architect
- 20+ years experience
- Former CTO, Interim CTO multiple companies
- Executive MBA
- Expertise: Digital Strategy, Enterprise Architecture, Change Management
- Industries: Healthcare (Karolinska), Finance (Postgirot), AgriTech (DeLaval)
- Languages: Swedish, English, Danish, Norwegian
- Rate: 1,500-1,800 SEK/hour

## Target Assignment Examples

✅ **Good Matches:**
- "Interim CTO för digital transformation" (6-12 months)
- "Enterprise Architect för molnmigration" (12+ months)  
- "Programledare strategisk digitalisering" (9 months)
- "Business Architect för fusionsintegration" (6 months)

❌ **Filtered Out:**
- "Junior .NET utvecklare" 
- "React developer 2-5 års erfarenhet"
- "IT Support specialist"
- "Scrum Master första uppdraget"

## n8n Integration

### Webhook Endpoints

The system provides dedicated n8n webhook endpoints for workflow automation:

**Job Ingestion Webhook**
```json
POST http://localhost:8001/n8n/ingest
{
  "source": "n8n_workflow",
  "jobs": [{
    "title": "Interim CTO",
    "company": "Enterprise AB",
    "seniority": "senior",
    "min_years_experience": 15
  }]
}
```

**Matching Webhook**
```json
POST http://localhost:8001/n8n/match
{
  "job_ids": ["uuid1", "uuid2"],
  "min_score": 0.7,
  "seniority_filter": "senior"
}
```

## Development

### Testing Scrapers
```bash
# Test connectivity to all scraping targets
python scripts/test_scraper.py --scraper connectivity

# Test Brainville scraper (saves JSON output)
python scripts/test_scraper.py --scraper brainville

# Test Cinode authenticated scraper
python scripts/test_scraper.py --scraper cinode

# Test all scrapers
python scripts/test_scraper.py --scraper all --verbose
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

## Implementation Status

### ✅ Completed Components
- Core database schema with PostgreSQL + pgvector
- FastAPI backend with executive-focused endpoints
- Web UI dashboard with Tailwind CSS + HTMX
- Dual embedding service optimized for strategic language
- Weighted matching algorithm for senior profiles
- Brainville web scraper with rate limiting
- Playwright MCP integration for authenticated sites
- Cinode scraper with login capability
- Configuration system for Swedish market

### 🚧 In Progress
See [Implementation Plan](docs/IMPLEMENTATION_PLAN.md) for roadmap:

1. **Data Ingestion**: ✅ Brainville, Cinode | ⏳ LinkedIn scrapers
2. **Automation**: Add APScheduler for daily 07:00 scanning
3. **Enhanced Matching**: Improve executive scoring algorithms
4. **Notifications**: Slack/Teams integration for reports
5. **Production**: Security hardening and monitoring

### 📋 Next Priority Tasks
- Implement automated daily scanning at 07:00
- Add LinkedIn premium job scraper
- Create Slack/Teams notification delivery
- Add trend analysis for executive market
- Implement company prospect scoring

## License

MIT

## Support

For issues or questions, please open a GitHub issue.