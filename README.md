# Consultant Assignment Matching System

An intelligent system for ingesting Swedish consulting assignments and matching them with consultants using embeddings and multi-factor scoring.

## Features

- **Multi-source ingestion**: RSS feeds, HTML parsing, API integration
- **Smart matching**: Embeddings-based similarity with weighted scoring
- **PostgreSQL + pgvector**: Efficient vector similarity search
- **FastAPI backend**: Modern async Python API
- **n8n integration**: Ready-to-use webhook endpoints
- **Automated reporting**: Daily/weekly reports for Slack/Teams

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Sources   │────▶│   FastAPI   │────▶│ PostgreSQL  │
│ RSS/HTML/API│     │   Backend   │     │  + pgvector │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │  Embeddings │
                    │   Service   │
                    └─────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- OpenAI API key (for OpenAI embeddings) or use local embeddings

### Setup

1. Clone the repository:
```bash
git clone <repo-url>
cd consultant-assignment-matching
```

2. Set environment variables:
```bash
# Create .env file
cat > .env << EOF
EMBEDDING_BACKEND=openai  # or "local" for sentence-transformers
OPENAI_API_KEY=your-api-key-here  # if using OpenAI
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/consultant_matching
EOF
```

3. Start services with Docker:
```bash
docker-compose up -d
```

4. Seed the database with sample data:
```bash
# With Docker
docker-compose exec api python scripts/dev_seed.py

# Or locally
pip install -r requirements.txt
python scripts/dev_seed.py
```

5. Access the API:
- API: http://localhost:8001
- Interactive docs: http://localhost:8001/docs
- Database: localhost:5433 (user: postgres, pass: postgres)

## API Endpoints

### Job Management

**Upsert Single Job**
```bash
curl -X POST http://localhost:8001/jobs/upsert \
  -H "Content-Type: application/json" \
  -d '{
    "source": "manual",
    "title": "Senior Python Developer",
    "company": "TechCorp AB",
    "location": "Stockholm",
    "skills": ["Python", "FastAPI", "PostgreSQL"],
    "language_requirements": ["Swedish", "English"]
  }'
```

**Bulk Upsert Jobs**
```bash
curl -X POST http://localhost:8001/jobs/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "jobs": [
      {"source": "rss", "title": "DevOps Engineer", ...},
      {"source": "rss", "title": "Frontend Developer", ...}
    ]
  }'
```

### Consultant Management

**Upsert Consultant**
```bash
curl -X POST http://localhost:8001/consultants/upsert \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Anna Andersson",
    "email": "anna@example.com",
    "title": "Senior Developer",
    "skills": ["Python", "React", "PostgreSQL"],
    "languages": ["Swedish", "English"],
    "location": "Stockholm"
  }'
```

### Matching

**Run Matching Algorithm**
```bash
curl -X POST http://localhost:8001/match/run \
  -H "Content-Type: application/json" \
  -d '{
    "min_score": 0.6,
    "max_results": 5
  }'
```

### Reports

**Get Daily Report**
```bash
# JSON format
curl http://localhost:8001/reports/daily

# Slack format
curl http://localhost:8001/reports/daily/slack

# Teams format
curl http://localhost:8001/reports/weekly/teams
```

### Ingestion

**Ingest from RSS**
```bash
curl -X POST http://localhost:8001/ingest/rss \
  -H "Content-Type: application/json" \
  -d '{
    "feed_url": "https://example.com/jobs.rss",
    "source_name": "example_rss"
  }'
```

**Parse HTML**
```bash
curl -X POST http://localhost:8001/parse/custom_source \
  -H "Content-Type: application/json" \
  -d '{
    "html_content": "<html>...</html>"
  }'
```

## n8n Integration

### Webhook Endpoints

The system provides dedicated n8n webhook endpoints for easy integration:

**Job Ingestion Webhook**
```json
POST http://localhost:8001/n8n/ingest
{
  "source": "n8n_workflow",
  "jobs": [
    {
      "title": "Python Developer",
      "company": "Tech AB",
      "location": "Stockholm",
      "description": "...",
      "skills": ["Python", "Django"]
    }
  ]
}
```

**Matching Webhook**
```json
POST http://localhost:8001/n8n/match
{
  "job_ids": ["uuid1", "uuid2"],
  "min_score": 0.7,
  "max_results": 3
}
```

### n8n Workflow Examples

**Daily Ingestion Workflow**
1. Schedule Trigger (daily at 9 AM)
2. HTTP Request to fetch job listings
3. Transform data to match schema
4. POST to `/n8n/ingest`
5. POST to `/n8n/match` for new jobs
6. Send results to Slack/Teams

**RSS Feed Monitor**
1. RSS Feed Trigger
2. Transform RSS items
3. POST to `/n8n/ingest`
4. If new jobs found, trigger matching
5. Format and send notifications

## Matching Algorithm

The system uses a weighted multi-factor matching approach:

| Factor | Weight | Description |
|--------|--------|-------------|
| Cosine Similarity | 45% | Embedding-based semantic similarity |
| Skills Match | 25% | Direct and fuzzy skill matching |
| Role Match | 15% | Seniority level compatibility |
| Language Match | 10% | Language requirements fulfillment |
| Geographic Match | 5% | Location proximity |

### Scoring Details

- **Cosine Similarity**: Uses OpenAI `text-embedding-3-large` or local sentence-transformers
- **Skills Match**: Exact matches get full score, fuzzy matches (>80% similarity) get partial credit
- **Role Match**: Compares seniority levels (Junior/Mid/Senior) with experience years
- **Language Match**: Percentage of required languages the consultant speaks
- **Geographic Match**: Same city (100%), same region (70%), remote option (60%)

## Database Schema

Key tables:
- `jobs`: Assignment listings with metadata
- `consultants`: Consultant profiles
- `job_embeddings`: Vector embeddings for jobs (3072 dimensions)
- `consultant_embeddings`: Vector embeddings for consultants
- `job_consultant_matches`: Match results with scores and reasons
- `ingestion_logs`: Track ingestion runs

## Development

### Local Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set up pre-commit hooks (optional)
pip install pre-commit
pre-commit install

# Run locally
uvicorn app.main:app --reload
```

### Testing

```bash
# Run tests
pytest tests/

# With coverage
pytest --cov=app tests/
```

### Adding New Ingestion Sources

1. Create new ingester in `app/ingest/`:
```python
from app.ingest.base import BaseIngester

class CustomIngester(BaseIngester):
    async def fetch_jobs(self) -> List[JobIn]:
        # Implementation
        pass
```

2. Add parsing logic in `app/parse/` if needed

3. Create API endpoint in `app/main.py`

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5433/consultant_matching` |
| `EMBEDDING_BACKEND` | `openai` or `local` | `openai` |
| `OPENAI_API_KEY` | OpenAI API key (if using OpenAI) | - |
| `REDIS_URL` | Redis connection (optional) | `redis://localhost:6380` |

### Docker Compose Override

For production settings, create `docker-compose.override.yml`:
```yaml
version: '3.8'
services:
  api:
    environment:
      - EMBEDDING_BACKEND=local
    restart: always
```

## Monitoring

### Health Check
```bash
curl http://localhost:8001/health
```

### Logs
```bash
# API logs
docker-compose logs -f api

# Database logs
docker-compose logs -f postgres
```

## Troubleshooting

### Common Issues

1. **Database connection failed**
   - Ensure PostgreSQL is running: `docker-compose ps`
   - Check credentials in DATABASE_URL

2. **Embedding creation slow**
   - Consider using local embeddings instead of OpenAI
   - Set `EMBEDDING_BACKEND=local`

3. **Out of memory with local embeddings**
   - Sentence-transformers models can be memory intensive
   - Use OpenAI embeddings or reduce batch sizes

## Implementation Status

### Current Phase: Foundation Complete ✅
The core system architecture is in place with database, API, embeddings, and matching algorithms implemented.

### Next Steps: Production Features 🚧
See [Implementation Plan](docs/IMPLEMENTATION_PLAN.md) for the detailed roadmap:

1. **Data Ingestion**: Implement Brainville, Cinode, LinkedIn scrapers
2. **Automation**: Add scheduling and daily scanning
3. **Enhanced Matching**: Improve analytics and scoring
4. **User Interface**: Admin dashboard and filters
5. **Production**: Monitoring, security, and hardening

Priority items to implement:
- Web scrapers for Swedish consulting portals
- Daily automated scanning at 07:00 CET
- Slack/Teams webhook delivery
- Admin dashboard for assignment filtering
- Company prospect scoring

## License

MIT

## Support

For issues or questions, please open a GitHub issue.