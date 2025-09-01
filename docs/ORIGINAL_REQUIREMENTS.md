# AI Agent for Consultant Assignment Scanning and Matching

## Purpose
Build an AI-driven agent that automatically scans the Swedish consulting market for new assignments, matches these against our available consultants, and provides suggestions on which companies or consultant brokers we should contact to place our consultants.

## 1. Data Sources to Monitor (scraping / API / newsletters)

### Consultant brokers with assignment portals:
- eWork
- ZeroChaos / ProData
- Cinode Marketplace
- Brainville
- Onsiter
- A Society
- Nikita
- Keyman
- TietoEVRY (has certain open RFP portals)

### Public framework agreements/procurements:
- Visma Opic
- Kommers Annons

### Job sites with freelance and consulting assignments:
- LinkedIn (especially "Contract / Interim" tagged roles)
- Uptrail (consulting roles)
- Freelance Finance

### Optional later step: 
Track competing companies/press releases for new projects, e.g., "new large SAP projects"

## 2. Consultant Data to Match Against
- All Nordic consultants. No database exists to match against today.
- Metadata to use for matching:
  - Role / title (e.g., .NET developer, data engineer, solution architect)
  - Seniority level (junior, mid-level, senior)
  - Tech stack (Python, Azure, SAP, Java, React, etc.)
  - Language requirements (Swedish/English)
  - Geography / onsite vs remote

## 3. Output / Deliverables

### Report Structure:
- New assignments (last 24–48h) with brief summary, link, and tagged consultants who match
- Matching suggestions: X assignments that are most relevant for our available consultants
- Prospect list: top 10 companies or brokers we should contact, based on number of relevant assignments and history

### Format: 
Brief table or list in Teams/Slack every Monday morning (for quick overview)

## 4. Frequency
- Daily scanning (once per day, e.g., at 07:00)
- Weekly compilation (Friday) with more analysis: trends, which brokers have the most assignments, which technologies are most in demand, gaps in our consultant offering

## 5. Desired Features (in the future)
- Simple interface where salespeople can filter: "Show only SAP assignments in Stockholm"
- History: see which companies/brokers repeatedly advertise
- Recommendations: "X consultant should be matched against Y company" with reasoning
- Alert function: push notification for assignments with perfect match (100%)

## 6. Prioritization (first delivery)
- Brainville + Cinode + LinkedIn scraping (MVP)
- Matching against benched consultants
- Daily report in Slack/Teams
- Weekly report with trends