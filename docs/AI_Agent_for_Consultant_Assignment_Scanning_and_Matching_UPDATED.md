# AI Agent for Consultant Assignment Scanning and Matching - Web Dashboard System

**Purpose:** Deliver an AI-driven web application that prioritises automated scanning of the Swedish consulting market, presents all insights directly inside the dashboard, and still supports the broader management, analytics, and matching features described for the full system. Scanning capabilities must work even when no consultant CVs are available; configurable criteria and source coverage come first, with other functions layered on top.

---

## 1. Data Sources to Monitor (Scanning-First Focus)

**Immediate priorities (in order):**
1. **Verama (formerly eWork)** – attempt official/API access first (investigate available endpoints); fall back to headless Playwright only if no reliable API exists.
   - Current scraper hits `https://app.verama.com/api/public/job-requests` (no auth required); confirm long-term stability and document any required headers.
2. **Cinode Marketplace** – prefer authenticated API integration; provide Playwright automation fallback.
3. **Keyman** – investigate API options; otherwise rely on Playwright-based portal automation.

**Secondary expansion targets (implemented after the top three are stable):**
- Emagine (https://emagine-consulting.se/)
- Brainville
- Onsiter
- A Society
- Nikita
- TietoEVRY RFP portals
- Visma Opic (public procurements)
- Kommers Annons
- LinkedIn (contract/interim roles)
- Uptrail
- Freelance Finance
- Future enhancement: press releases and project news monitoring

> **Note:** All sources must consume the same scanning configuration so that criteria can be tuned centrally regardless of whether matching data exists yet.

---

## 2. Scanning Services Architecture

### API Scanning Service (Preferred)
- Uses official APIs when available for structured responses and stable pagination.
- Handles authentication, throttling, retries, and error recovery.
- Shares configuration parameters with the UI so manual adjustments instantly affect API queries.

### Headless Playwright Service (Fallback)
- Automates login, filtering, and pagination for portals without APIs.
- Captures screenshots and HTML snapshots for debugging when selectors change.
- Obeys the same configuration objects as the API service to minimise divergence.

### Unified Manual Criteria Configuration
- Accessible even when the consultant database is empty.
- Stored in the `scanning_configs` tables and managed through `/consultant/scanner` and `/consultant/config`.
- Includes:
  - Skill/technology keywords
  - Role/title keywords
  - Seniority levels (Junior, Mid, Senior, Lead, Principal)
  - Geography and onsite mode (Stockholm, Göteborg, Malmö, Remote, Hybrid, etc.)
  - Language requirements
  - Contract duration bands
  - Source-specific overrides (e.g., Verama-specific filters)
- Immediate effect on active scanners; changes are logged for auditing.

---

## 3. Consultant Database Management (Dashboard-Centric)

The consultant module remains part of the system but is decoupled from scanning so criteria can run independently. When used, it provides:
- Profile CRUD interface with role, seniority, technology stack, languages, geography, work-mode preferences, availability, and notes.
- CV upload/parsing to accelerate profile onboarding.
- Active/inactive toggles without affecting ongoing scans.

---

## 4. Web Dashboard Output System (In-App Only)

All insights live in the web interface—there are no Slack, Teams, email, or third-party messaging integrations.

### Authentication & User Roles
- Secure login page with branded UI (FastAPI + HTMX) for `/auth/login`.
- Role-based access (admin, manager, viewer) managed via JWT tokens (see `app/auth.py`, `app/auth_routes.py`).
- Session management with refresh tokens, password hashing (bcrypt), and audit logging for user activity.
- Admin-only interface at `/consultant/users` for managing accounts, roles, and status toggles.

### Main Dashboard (`/consultant/dashboard`)
- **Today’s Discoveries**: latest assignments aggregated from the top-priority sources with drill-down links.
- **Priority Actions**: companies/brokers to focus on today based on volume and filtering, tracked entirely in the UI.
- **Smart Matching Insights**: when consultant data exists, the best matches appear with contextual reasoning; when it doesn’t, the panel highlights “scanning only” status.

### Jobs Page (`/consultant/jobs`)
- Filter by source, date, location, skills, seniority, contract duration, and custom tags.
- View raw posting details, original links, and any associated scanner metadata.
- Trigger manual rescan for specific jobs or sources from the same page.

### Consultants Page (`/consultant/consultants`)
- Manage profiles, availability, and matching readiness.
- Review which jobs each consultant currently matches (if data is available).

### Analytics Page (`/consultant/analytics`)
- Visualise demand trends, source performance, and scanning throughput.
- Provide insights even without consultant matches (e.g., “Top skills requested this week”).

### Companies Page (`/consultant/companies`)
- Track recurring clients/brokers, capture outreach notes, and compare assignment volumes over time.

### Recommendations & Alerts (`/consultant/recommendations`, `/consultant/alerts`)
- In-app notifications for perfect matches or significant market shifts.
- Keep a historical log of alerts without sending external messages.

---

## 5. Automated Scheduling & Monitoring

- APScheduler orchestrates daily (07:00 CET) and weekly scans.
- Execution status, next runs, and recent logs surface inside `/consultant/scanner`—no emails or chat alerts.
- Manual overrides allow one-off scans or pausing specific sources while others continue.

---

## 6. Implementation Priorities (Scanning First)

### Phase 1 – Core Scanning & Dashboard
1. Confirm Verama API availability; implement API client or Playwright fallback for credentials-based access.
2. Build robust configuration UI that works without consultant data.
3. Implement Cinode and Keyman scanners following the same configuration contracts.
4. Populate `/consultant/dashboard`, `/consultant/jobs`, and `/consultant/scanner` with real Verama data streams.

### Phase 2 – Matching & Extended Sources
1. Integrate consultant management and matching workflows using existing embeddings/matching services.
2. Add Brainville and Emagine sources (API first, Playwright fallback).
3. Extend analytics and recommendations pages with combined source insights.

### Phase 3 – Advanced Intelligence
1. Introduce adaptive configuration tuning and parameter A/B testing.
2. Add market intelligence (company trend analysis, technology momentum).
3. Layer in predictive scoring and workflow automation entirely within the dashboard.

---

## 7. Centralised Web Configuration & Learning

### Admin Configuration (`/consultant/config`, `/consultant/config/{id}`)
- Manage active/inactive configs, adjust parameters, review change history.
- Apply per-source overrides for the top-priority feeds.
- Provide quick duplication and rollback tools.

### Learning & Optimisation (`/consultant/analytics` extensions)
- Track conversion metrics once matching is active (jobs found, matches generated, placements).
- Surface what skill/role combinations yield the richest results—even before consultants are added.

---

## 8. System Responsibilities Recap

- **Scanning** is the first-class concern: Verama → Cinode → Keyman, then additional sources.
- **Configuration** must operate independently of consultant data so the scanning pipeline is never blocked.
- **Dashboard** remains the single interface for operations, analysis, matching, and alerts—no external messaging channels.
- **Matching & Analytics** remain part of the system scope, ready to be activated once scanning is stable and consultant data is available.
