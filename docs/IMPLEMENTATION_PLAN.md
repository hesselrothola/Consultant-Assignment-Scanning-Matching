# Implementation Plan - Next Steps

## Current Status

### ✅ Completed Components
- Core database schema with PostgreSQL + pgvector
- Basic FastAPI endpoints for jobs and consultants
- Dual embedding service (OpenAI text-embedding-3-large / local sentence-transformers)
- Weighted matching algorithm (45% cosine, 25% skills, 15% role, 10% language, 5% geography)
- Report generation framework with Slack/Teams formatting
- Docker deployment setup with separate ports
- n8n webhook endpoints

### ❌ Missing Critical Components
- Web scrapers for priority sources (Brainville, Cinode, LinkedIn)
- Scheduling system for automated scanning
- Production-ready notification delivery
- Admin dashboard for management
- Analytics and trend detection

## Phase 1: Data Ingestion - MVP Priority

### 1.1 Implement Web Scrapers for Priority Sources
**Brainville Scraper**
- Use httpx for async HTTP requests
- Parse with selectolax for HTML extraction
- Extract: title, company, location, skills, duration, description
- Handle pagination and rate limiting

**Cinode Marketplace Integration**
- Implement API client if available
- Fallback to web scraping if needed
- Map Cinode's data model to our schema

**LinkedIn Contract/Interim Scraper**
- Focus on "Contract" and "Interim" tagged positions
- Extract consultant-friendly assignments
- Handle authentication and anti-scraping measures

### 1.2 Enhance Job Parsing
- **Swedish Company Patterns**: Recognize AB, Aktiebolag, HB patterns
- **Broker Detection**: Identify eWork, ProData, ZeroChaos mentions
- **Skill Extraction**: Add Swedish tech terms, certifications
- **Structured Data**: Parse duration (3-6 months), start dates, budget ranges

## Phase 2: Automation & Scheduling

### 2.1 Add Scheduling System
```python
# Implement with APScheduler
- Daily scanning at 07:00 CET
- Weekly compilation on Fridays at 16:00
- Monday morning reports at 08:00
- Configurable per-source scanning intervals
```

### 2.2 n8n Workflow Integration
- Create reusable n8n workflow templates
- Error handling with exponential backoff
- Dead letter queue for failed jobs
- Monitoring dashboard in n8n

## Phase 3: Enhanced Matching & Analytics

### 3.1 Improve Matching Logic
- **Availability Matching**: Compare consultant availability_from with job start_date
- **Status Tracking**: Add consultant states (available/benched/assigned)
- **Performance Tracking**: Store match outcomes (applied/interviewed/placed)
- **Prospect Scoring**: Rank companies by match frequency and success rate

### 3.2 Analytics & Insights
```sql
-- Trending analysis queries
- Top brokers by assignment volume
- Technology demand trends over time
- Skill gap analysis (demanded vs available)
- Geographic heat maps of opportunities
```

## Phase 4: User Interface & Notifications

### 4.1 Admin Dashboard
- **Tech Stack**: FastAPI + HTMX + Alpine.js (lightweight, no build step)
- **Features**:
  - Filter assignments: "Show only SAP assignments in Stockholm"
  - Consultant CRUD with bulk import
  - Manual match override
  - Report customization UI

### 4.2 Notification System
**Slack Integration**
```python
- Daily summary at 07:30
- Weekly analysis on Fridays
- Perfect match alerts (>95% score)
- New high-value assignment alerts
```

**Teams Integration**
- Adaptive cards for rich formatting
- Interactive buttons for quick actions
- Thread-based discussion per assignment

## Phase 5: Production Readiness

### 5.1 Data Quality & Monitoring
- **Duplicate Detection**: Use job_uid and fuzzy matching
- **Validation Pipeline**: Verify required fields, format consistency
- **Health Monitoring**: Track scraper success rates, response times
- **Metrics Dashboard**: Grafana for system metrics

### 5.2 Security & Compliance
- **Authentication**: JWT tokens with refresh mechanism
- **Rate Limiting**: Per-endpoint and per-user limits
- **GDPR Compliance**:
  - Consultant consent tracking
  - Data retention policies
  - Export/deletion capabilities
- **Audit Logging**: Track all data access and modifications

## Immediate Next Actions

### Priority Implementation Tasks
1. **Create Brainville Scraper Module**
   ```python
   app/scrapers/brainville.py
   - Parse job listings
   - Handle pagination
   - Extract structured data
   ```

2. **Implement Scheduled Job Scanning**
   ```python
   app/scheduler.py
   - APScheduler setup
   - Configurable intervals
   - Error recovery
   ```

3. **Add Slack Webhook for Daily Reports**
   ```python
   app/notifications/slack.py
   - Format reports as Slack blocks
   - Send to configured webhook
   - Handle delivery failures
   ```

4. **Create Consultant CSV Import with Validation**
   ```python
   scripts/import_consultants.py
   - Validate required fields
   - Normalize data formats
   - Generate embeddings
   ```

5. **Set Up Production Monitoring**
   - Sentry for error tracking
   - Prometheus metrics
   - Uptime monitoring

## Technical Architecture Additions

### New Modules Structure
```
app/
├── scrapers/
│   ├── __init__.py
│   ├── base.py          # Abstract scraper class
│   ├── brainville.py
│   ├── cinode.py
│   └── linkedin.py
├── scheduler/
│   ├── __init__.py
│   ├── tasks.py         # Scheduled task definitions
│   └── manager.py       # APScheduler management
├── notifications/
│   ├── __init__.py
│   ├── slack.py
│   ├── teams.py
│   └── email.py
└── analytics/
    ├── __init__.py
    ├── trends.py        # Trend analysis
    └── insights.py      # Business insights
```

### Configuration Management
```python
# app/config.py
class Settings:
    # Scraping intervals
    BRAINVILLE_INTERVAL = "0 7 * * *"  # Daily at 07:00
    CINODE_INTERVAL = "0 7 * * *"
    LINKEDIN_INTERVAL = "0 8 * * *"     # Staggered to avoid load
    
    # Notification settings
    SLACK_WEBHOOK_URL = env("SLACK_WEBHOOK_URL")
    TEAMS_WEBHOOK_URL = env("TEAMS_WEBHOOK_URL")
    
    # Matching thresholds
    PERFECT_MATCH_THRESHOLD = 0.95
    HIGH_QUALITY_THRESHOLD = 0.80
    MIN_MATCH_THRESHOLD = 0.60
```

## Success Metrics

### KPIs to Track
1. **Ingestion Metrics**
   - Jobs ingested per day/source
   - Scraping success rate
   - Data quality score

2. **Matching Metrics**
   - Matches generated per consultant
   - Match accuracy (feedback-based)
   - Time to match

3. **Business Metrics**
   - Consultants placed via system
   - Revenue attributed to matches
   - User engagement with reports

## Risk Mitigation

### Technical Risks
- **Scraping Blocks**: Implement rotating proxies, respect robots.txt
- **API Rate Limits**: Add exponential backoff, request queuing
- **Data Quality**: Validation at every stage, manual review queue

### Business Risks
- **GDPR Compliance**: Legal review, consent management
- **Competitive Information**: Secure data handling, access controls
- **Consultant Privacy**: Anonymization options, opt-out mechanism

## Implementation Flow

The phases should be implemented in order, with each phase building on the previous:

1. **Data Ingestion**: Get data flowing into the system
2. **Automation**: Make it run automatically
3. **Enhanced Matching**: Improve match quality
4. **User Interface**: Make it accessible
5. **Production Readiness**: Make it reliable

This plan transforms the current foundation into a production-ready system that fully meets the original requirements for automated consultant assignment scanning and matching in the Swedish market.