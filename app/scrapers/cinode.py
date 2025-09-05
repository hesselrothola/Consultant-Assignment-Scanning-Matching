"""
Cinode marketplace scraper using Playwright browser automation.
Handles authentication and JavaScript-rendered content.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import asyncio
import re

from app.models import JobIn, OnsiteMode
from app.scrapers.base_playwright import BasePlaywrightScraper

logger = logging.getLogger(__name__)


class CinodeScraper(BasePlaywrightScraper):
    """
    Scraper for Cinode marketplace using browser automation.
    Requires authentication to access job listings.
    """
    
    def __init__(self, mcp_client, username: str, password: str):
        super().__init__(
            source_name="cinode",
            base_url="https://www.cinode.com",
            mcp_client=mcp_client,
            username=username,
            password=password
        )
        self.marketplace_url = "https://www.cinode.com/marketplace"
        self.login_url = "https://www.cinode.com/login"
    
    async def login(self):
        """
        Perform login to Cinode marketplace.
        """
        try:
            logger.info("Logging into Cinode...")
            
            # Navigate to login page
            await self.navigate_to(self.login_url)
            await asyncio.sleep(2)  # Wait for page load
            
            # Get page snapshot to find login form elements
            snapshot = await self.get_page_snapshot()
            
            # Find username/email input
            email_input = await self._find_element_in_snapshot(
                snapshot,
                ["input[type='email']", "input[name='email']", "input[name='username']", "#email"]
            )
            
            if email_input:
                await self.type_text(
                    ref=email_input['ref'],
                    text=self.username,
                    element_description="Email/username input field"
                )
            
            # Find password input
            password_input = await self._find_element_in_snapshot(
                snapshot,
                ["input[type='password']", "input[name='password']", "#password"]
            )
            
            if password_input:
                await self.type_text(
                    ref=password_input['ref'],
                    text=self.password,
                    element_description="Password input field"
                )
            
            # Find and click login button
            login_button = await self._find_element_in_snapshot(
                snapshot,
                ["button[type='submit']", "input[type='submit']", ".login-button", "#login-button"]
            )
            
            if login_button:
                await self.click_element(
                    ref=login_button['ref'],
                    element_description="Login submit button"
                )
            else:
                # Try submitting via Enter key on password field
                await self.type_text(
                    ref=password_input['ref'],
                    text="",
                    element_description="Password field",
                    submit=True
                )
            
            # Wait for login to complete
            await asyncio.sleep(3)
            
            # Check if login was successful by looking for dashboard elements
            logged_in = await self.wait_for_element(text="Marketplace", timeout=10)
            
            if logged_in:
                self.logged_in = True
                logger.info("Successfully logged into Cinode")
            else:
                # Check for error messages
                error_check = await self.evaluate_javascript("""
                    () => {
                        const errors = document.querySelectorAll('.error-message, .alert-danger, [role="alert"]');
                        return errors.length > 0 ? errors[0].textContent : null;
                    }
                """)
                
                if error_check:
                    logger.error(f"Login failed with error: {error_check}")
                else:
                    logger.error("Login failed - could not find marketplace after login")
                
                raise Exception("Failed to login to Cinode")
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            raise
    
    async def scrape_assignments(self, max_pages: int = 5) -> List[JobIn]:
        """
        Scrape job assignments from Cinode marketplace.
        """
        jobs = []
        
        try:
            # Ensure we're logged in
            if not self.logged_in:
                await self.login()
            
            # Navigate to marketplace
            await self.navigate_to(self.marketplace_url)
            await asyncio.sleep(3)  # Wait for initial load
            
            # Apply Swedish market filter if available
            await self._apply_filters()
            
            for page in range(1, max_pages + 1):
                logger.info(f"Scraping Cinode page {page}/{max_pages}")
                
                # Extract jobs from current page
                page_jobs = await self._extract_jobs_from_page()
                
                if not page_jobs:
                    logger.info("No more jobs found, stopping pagination")
                    break
                
                # Convert to JobIn models
                for raw_job in page_jobs:
                    try:
                        job_model = self.parse_job_to_model(raw_job)
                        jobs.append(job_model)
                    except Exception as e:
                        logger.error(f"Failed to parse job: {e}")
                        continue
                
                # Go to next page
                if page < max_pages:
                    has_next = await self.handle_pagination(page)
                    if not has_next:
                        logger.info("No more pages available")
                        break
            
            logger.info(f"Scraped {len(jobs)} jobs from Cinode")
            
        except Exception as e:
            logger.error(f"Error scraping Cinode: {e}")
        
        return jobs
    
    async def _apply_filters(self):
        """Apply filters for Swedish market and relevant assignments."""
        try:
            # Look for filter buttons/dropdowns
            filter_script = """
                () => {
                    // Try to find and click Swedish/Sweden filter
                    const swedenFilters = document.querySelectorAll(
                        '[data-country="SE"], [data-location="Sweden"], 
                        button:contains("Sweden"), label:contains("Sverige")'
                    );
                    
                    if (swedenFilters.length > 0) {
                        swedenFilters[0].click();
                        return true;
                    }
                    
                    // Look for location dropdown
                    const locationSelect = document.querySelector(
                        'select[name="location"], select[name="country"], #location-filter'
                    );
                    
                    if (locationSelect) {
                        locationSelect.value = 'Sweden';
                        locationSelect.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                    
                    return false;
                }
            """
            
            applied = await self.evaluate_javascript(filter_script)
            if applied:
                await asyncio.sleep(2)  # Wait for filter to apply
                logger.info("Applied Swedish market filter")
            
        except Exception as e:
            logger.warning(f"Could not apply filters: {e}")
    
    async def _extract_jobs_from_page(self) -> List[Dict[str, Any]]:
        """Extract job data from current Cinode marketplace page."""
        extraction_script = """
            () => {
                const jobs = [];
                
                // Try multiple possible selectors for job cards
                const jobCards = document.querySelectorAll(
                    '.assignment-card, .job-listing, .marketplace-item, 
                    [data-testid="assignment-card"], article.assignment'
                );
                
                jobCards.forEach(card => {
                    try {
                        // Extract job details - adjust selectors based on actual Cinode HTML
                        const job = {
                            title: card.querySelector('.assignment-title, .job-title, h2, h3')?.textContent?.trim(),
                            company: card.querySelector('.company-name, .client-name, .organization')?.textContent?.trim(),
                            location: card.querySelector('.location, .assignment-location')?.textContent?.trim(),
                            description: card.querySelector('.description, .assignment-description, .summary')?.textContent?.trim(),
                            duration: card.querySelector('.duration, .assignment-duration')?.textContent?.trim(),
                            start_date: card.querySelector('.start-date, .assignment-start')?.textContent?.trim(),
                            rate: card.querySelector('.rate, .assignment-rate')?.textContent?.trim(),
                            skills: [],
                            url: card.querySelector('a')?.href || window.location.href
                        };
                        
                        // Extract skills if available
                        const skillElements = card.querySelectorAll('.skill-tag, .competence, .tech-stack span');
                        skillElements.forEach(skill => {
                            const skillText = skill.textContent?.trim();
                            if (skillText) {
                                job.skills.push(skillText);
                            }
                        });
                        
                        // Extract remote/onsite mode
                        const modeText = card.querySelector('.work-mode, .remote-status')?.textContent?.trim();
                        if (modeText) {
                            job.onsite_mode = modeText;
                        }
                        
                        // Extract posted date
                        const postedElement = card.querySelector('.posted-date, time, .published');
                        if (postedElement) {
                            job.posted_at = postedElement.getAttribute('datetime') || postedElement.textContent?.trim();
                        }
                        
                        // Only add if we have at least a title
                        if (job.title) {
                            jobs.push(job);
                        }
                    } catch (e) {
                        console.error('Error extracting job:', e);
                    }
                });
                
                return jobs;
            }
        """
        
        jobs = await self.evaluate_javascript(extraction_script)
        return jobs or []
    
    async def handle_pagination(self, current_page: int) -> bool:
        """Handle Cinode marketplace pagination."""
        next_page_script = """
            () => {
                // Look for next page button
                const nextButton = document.querySelector(
                    '.pagination-next, [aria-label="Next page"], 
                    button:contains("Next"), a.next-page, 
                    .paginator button:last-child:not(:disabled)'
                );
                
                if (nextButton && !nextButton.disabled && !nextButton.classList.contains('disabled')) {
                    nextButton.click();
                    return true;
                }
                
                // Check for numbered pagination
                const pageButtons = document.querySelectorAll('.pagination button, .page-number');
                const currentPageNum = """ + str(current_page + 1) + """;
                
                for (const btn of pageButtons) {
                    if (btn.textContent?.trim() === String(currentPageNum)) {
                        btn.click();
                        return true;
                    }
                }
                
                // Check for "Load more" button
                const loadMore = document.querySelector(
                    'button:contains("Load more"), button:contains("Visa fler")'
                );
                
                if (loadMore && !loadMore.disabled) {
                    loadMore.click();
                    return true;
                }
                
                return false;
            }
        """
        
        has_next = await self.evaluate_javascript(next_page_script)
        
        if has_next:
            await asyncio.sleep(3)  # Wait for new page to load
            return True
        
        return False
    
    async def _find_element_in_snapshot(
        self,
        snapshot: Dict[str, Any],
        selectors: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Find element in accessibility snapshot using selectors.
        Returns element with ref for interaction.
        """
        # This is a simplified version - the actual MCP snapshot
        # structure would need to be parsed properly
        # For now, try to find elements using JavaScript
        
        for selector in selectors:
            find_script = f"""
                () => {{
                    const element = document.querySelector('{selector}');
                    if (element) {{
                        // Generate a unique ref for the element
                        const ref = 'element_' + Math.random().toString(36).substr(2, 9);
                        element.setAttribute('data-mcp-ref', ref);
                        return {{
                            ref: ref,
                            found: true,
                            tagName: element.tagName,
                            text: element.textContent?.trim()
                        }};
                    }}
                    return null;
                }}
            """
            
            result = await self.evaluate_javascript(find_script)
            if result and result.get('found'):
                return result
        
        return None
    
    def parse_job_to_model(self, raw_job: Dict[str, Any]) -> JobIn:
        """Convert Cinode job data to JobIn model."""
        # Parse location
        location = raw_job.get('location', '')
        location_parts = location.split(',') if location else []
        location_city = location_parts[0].strip() if location_parts else None
        location_country = location_parts[-1].strip() if len(location_parts) > 1 else 'Sweden'
        
        # Parse duration (e.g., "6 månader" -> "6 months")
        duration = raw_job.get('duration', '')
        if 'månad' in duration.lower():
            duration = duration.replace('månader', 'months').replace('månad', 'month')
        
        # Parse start date
        start_date = None
        start_date_str = raw_job.get('start_date', '')
        if start_date_str:
            # Handle Swedish date formats
            if 'omgående' in start_date_str.lower() or 'asap' in start_date_str.lower():
                start_date = datetime.now(timezone.utc).date()
            else:
                start_date = self.parse_date(start_date_str)
        
        return JobIn(
            job_uid=self._generate_job_uid(raw_job),
            source=self.source_name,
            title=raw_job.get('title', 'Unknown'),
            description=raw_job.get('description'),
            skills=raw_job.get('skills', []) or self.extract_skills(raw_job.get('description', '')),
            role=self.extract_role_from_title(raw_job.get('title', '')),
            seniority=self.extract_seniority(raw_job.get('title', '')),
            languages=self.extract_languages(raw_job),
            location_city=location_city,
            location_country=location_country,
            onsite_mode=self.parse_onsite_mode(raw_job.get('onsite_mode')),
            duration=duration,
            start_date=start_date,
            company_id=None,  # Will be resolved by the API
            broker_id=None,  # Cinode is the broker
            url=raw_job.get('url', self.marketplace_url),
            posted_at=self.parse_date(raw_job.get('posted_at')),
            raw_json=raw_job
        )
    
    def extract_role_from_title(self, title: str) -> Optional[str]:
        """Extract role from job title."""
        if not title:
            return None
        
        title_lower = title.lower()
        
        # Common IT roles
        role_keywords = {
            'developer': ['developer', 'utvecklare', 'programmerare'],
            'architect': ['architect', 'arkitekt'],
            'engineer': ['engineer', 'ingenjör'],
            'consultant': ['consultant', 'konsult'],
            'analyst': ['analyst', 'analytiker'],
            'manager': ['manager', 'chef', 'ledare'],
            'designer': ['designer', 'ux', 'ui'],
            'tester': ['tester', 'qa', 'quality'],
            'devops': ['devops', 'sre', 'platform'],
            'data': ['data scientist', 'data engineer', 'data analyst']
        }
        
        for role, keywords in role_keywords.items():
            if any(keyword in title_lower for keyword in keywords):
                return role
        
        return 'consultant'  # Default for Cinode
    
    def extract_languages(self, raw_job: Dict[str, Any]) -> List[str]:
        """Extract language requirements."""
        languages = []
        
        # Check description for language mentions
        text = (raw_job.get('description', '') + ' ' + raw_job.get('title', '')).lower()
        
        if any(word in text for word in ['svenska', 'swedish', 'sweden']):
            languages.append('Swedish')
        
        if any(word in text for word in ['english', 'engelska']):
            languages.append('English')
        
        return languages if languages else ['Swedish', 'English']  # Default for Swedish market