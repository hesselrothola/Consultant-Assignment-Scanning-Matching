# CLAUDE.md

Guidance for Claude Code when contributing to this repository.

## Project Purpose & Focus

Build a scanning-first web dashboard that continuously monitors Swedish consultant assignment portals, surfaces the results inside the application, and layers on matching, analytics, recommendations, and company intelligence. Scanning must operate even if no consultant CVs exist; configuration lives in the UI so operators can tune criteria before any matching data is present.

## System Scope & Phasing

- **Phase 1 – Core Scanning:** Verama → Cinode → Keyman with shared configuration UI, scheduler control, and in-app monitoring.
- **Phase 2 – Matching & Consultant Management:** Activate consultant profiles, CV ingestion, embeddings, and matching workflows; ensure jobs/matches pages stay in sync.
- **Phase 3 – Intelligence & Operations:** Expand analytics dashboards, company intelligence tracking, alert/recommendation centres, and adaptive configuration learning.

All phases share the same dashboard foundation; later stages depend on stable scanning but are part of the product vision and should be considered when designing APIs and data models.

## Current Scanning Priorities

1. **Verama** – investigate and prefer official/API access; use Playwright automation only when no stable endpoint exists.
2. **Cinode** – support authenticated scraping/API access under the same configuration contract.
3. **Keyman** – add coverage once shared configuration plumbing is in place.
4. Additional sources (Brainville, Emagine, Onsiter, A Society, Nikita, TietoEVRY, Visma Opic, Kommers, LinkedIn, Uptrail, Freelance Finance) follow after top-three parity.

All scanners must read shared criteria from `scanning_configs` + `source_config_overrides` so operators can refine searches centrally.

## Architecture Overview

- **DatabaseRepository (`app/repo.py`)** – Async access to Postgres + pgvector, managing jobs, consultants, embeddings, matches, ingestion logs, and scanning config tables.
- **EmbeddingService (`app/embeddings.py`)** – Wraps OpenAI or deterministic local embeddings; currently uses simple text preparation that can be enhanced later.
- **MatchingService (`app/matching.py`)** – Creates embeddings on demand, scores matches (cosine, skills, role, language, geo). Adjust weights/logic as future phases call for richer analytics or executive scoring.
- **ReportingService (`app/reports.py`)** – Aggregates jobs/matches/skills/source stats; extend to power dashboard analytics, company insights, and recommendations.
- **Scheduler (`app/scheduler.py`)** – APScheduler orchestration for daily/weekly scans, weekly reports, Monday briefs, optimisation routines. UI control at `/consultant/scanner`.
- **Scrapers (`app/scrapers/`)** – Base HTTP and Playwright abstractions plus current implementations for Brainville, Cinode, and Verama. New scrapers must honour shared configuration inputs and emit `JobIn` objects.
- **Auth (`app/auth.py`, `app/auth_routes.py`)** – JWT-based login with admin/manager/viewer roles, password hashing, refresh tokens, and user management pages.
- **Web UI (`app/frontend.py`, `app/templates/`)** – HTMX/Tailwind dashboard at `/consultant/…`, including login page, jobs list, consultants management, configuration pages, scanner controls, analytics stubs, company views, and placeholders for recommendations/alerts. All user-facing insights stay inside the web app—no Slack/Teams/email integrations.

## Scanning & Configuration Expectations

- Make new scanners configurable via the shared tables and expose controls in the UI.
- Ensure scanning can run without consultants; matching features should gracefully report "no consultant data" rather than block scans.
- Prefer API integrations when possible; Playwright is a fallback and should log screenshots/snapshots for debugging.
- Keep rate limits and authentication details in `.env` (see `config/scraper_config.yaml` for defaults).

## Matching, Analytics & Operations

- Matching, analytics, company intelligence, recommendations, and alerting modules are part of the system; design changes should consider their data needs even when implementing scanning tasks.
- When enriching matching logic, coordinate weight changes, new fields, or schema migrations with actual database structures (no phantom columns).
- Reporting should evolve to feed in-app dashboards (`/consultant/analytics`, `/consultant/companies`, `/consultant/recommendations`, `/consultant/alerts`) rather than external messaging.
- Future adaptive configuration and learning features rely on accurate ingestion logs and performance metrics—keep those endpoints tidy.

## Key Commands

```bash
# Run FastAPI on the server (example via SSH)
ssh <user>@91.98.72.10 "cd /opt/Consultant-Assignment-Scanning-Matching && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

# Execute existing scrapers manually
curl -X POST http://91.98.72.10:8000/scrape/brainville
curl -X POST http://91.98.72.10:8000/scrape/verama
curl -X POST http://91.98.72.10:8000/scrape/cinode

# Regenerate requirements lock if deps change
pip-compile requirements.in
```

Adjust commands as tooling evolves; keep docs consistent with actual scripts.


## Deployment & Environment

- Primary environment runs on managed server **91.98.72.10**; coordinate deployments and troubleshooting against that host.
- Do not start long-running services on local laptops unless explicitly instructed—align work with the server environment.
- Use provided Docker/docker-compose tooling when interacting with the server stack.
- When invoking API endpoints or dashboards, point clients to http://91.98.72.10:<port> rather than localhost on your development machine.
## Implementation Notes & TODO Alignment

- Remove reliance on Teams/email notifications from scheduler delivery flows and build equivalent in-app alert panels.
- Flesh out `/consultant/jobs` filters, analytics dashboards, company tracking, and recommendation/alert views per the updated system spec.
- Prioritise implementing Verama → Cinode → Keyman pipelines before expanding to other sources, but keep downstream modules in mind when shaping schemas and APIs. Confirm Verama API usage (`https://app.verama.com/api/public/job-requests`) is stable and capture any auth/header requirements for production.
- Finish Cinode integration (authenticated API/Playwright) and implement Keyman scraper with shared configuration + UI controls.
- When adding new functionality, update both this file and `docs/AI_Agent_for_Consultant_Assignment_Scanning_and_Matching_UPDATED.md` to stay in sync.

## Contact & Credentials Hygiene

- Store API keys and login details in `.env`; never commit secrets.
- Respect portal terms of service; include rate limiting and backoff strategies in scrapers.

By keeping these guidelines aligned with the full dashboard vision—scanning first, intelligence layered next—we ensure contributions strengthen the entire system lifecycle.