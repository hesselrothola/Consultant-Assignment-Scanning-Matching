# Tasks/Todo - Consultant Assignment Scanning & Matching System

## Focus: eWork Scraping, CV Upload, and Accurate Matching

## Priority Tasks (Immediate Implementation)

### 1. eWork Scraper - PRIMARY FOCUS
- [ ] Test current eWork scraper implementation
- [ ] Fix any authentication issues
- [ ] Ensure proper filtering for Swedish senior consultant roles
- [ ] Add error handling and retry logic
- [ ] Test scheduled scanning (daily 07:00)
- [ ] Verify data is properly stored in database

### 2. CV Upload & AI Processing
- [ ] Test existing CV upload feature (reportedly working per CLAUDE.md)
- [ ] Verify AI parsing with OpenAI GPT-4
- [ ] Test PDF, DOCX, TXT file support
- [ ] Ensure consultant profiles are correctly extracted
- [ ] Add validation for required fields
- [ ] Test manual editing of AI-parsed data

### 3. Matching Accuracy
- [ ] Verify embedding service is using OpenAI (better for executive terminology)
- [ ] Test executive-weighted scoring algorithm
- [ ] Ensure seniority filter works (10+ years, senior titles)
- [ ] Validate rate expectations matching (1,200-1,800 SEK/hour)
- [ ] Test skill matching for strategic terms
- [ ] Verify language matching (Swedish/English/Nordic)

### 4. Future Scrapers (After eWork is stable)
- [ ] Prepare Cinode scraper with authentication
- [ ] Prepare Keyman scraper implementation

### 5. Reporting System (Instead of Slack/Teams)
- [ ] Create in-system daily report page
- [ ] Add weekly executive market analysis view
- [ ] Implement Monday morning brief as dashboard widget
- [ ] Add export functionality (PDF/CSV)

## Implementation Steps

### Step 1: Test eWork Scraper (NOW)
```bash
# On server 91.98.72.10
docker exec consultant_api python scripts/test_scraper.py --scraper ework --verbose
```

### Step 2: Verify CV Upload
- Test upload interface at /consultant/consultants
- Upload sample CV
- Check AI parsing results
- Verify database storage

### Step 3: Test Matching
- Add consultant via CV upload
- Run eWork scraper
- Check matching results
- Verify scoring accuracy

## Success Criteria
1. eWork scraper runs daily and fetches Swedish consultant jobs
2. CV upload works with AI parsing for all formats
3. Matching algorithm accurately identifies relevant opportunities
4. System generates useful reports without external notifications

## Notes
- ALL work on server 91.98.72.10
- Keep changes minimal and focused
- Test each component thoroughly before moving on
- Document any issues found

## Review Section
(To be filled after implementation)
## Review Section - Implementation Complete

### ✅ eWork Scraper - WORKING
- Successfully tested and operational
- Scraped 20 Swedish consultant jobs
- Fixed context manager issue (needs `async with`)
- Endpoint `/scrape/ework` working perfectly
- Jobs properly saved to database

### ⚠️ CV Upload - NEEDS FIX
- Endpoint exists at `/api/consultants/upload-cv`
- Dependencies installed (PyPDF2, python-docx)
- OpenAI API key configured
- Issue: Internal server error during parsing (needs debugging)
- Workaround: Manual consultant creation available

### ✅ System Integration
- All containers running on server (except playwright_mcp)
- API accessible at https://n8n.cognova.net/consultant/
- Login working (admin/admin123)
- Database operational

### Next Steps
1. Fix CV upload parsing error
2. Test matching algorithm with scraped jobs
3. Set up daily scanning schedule
4. Create in-system reports

### Key Findings
- eWork API working well for Swedish jobs
- System architecture solid
- Need to fix CV parser for full functionality
EOF"