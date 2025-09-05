"""
Base Playwright scraper class using MCP server for browser automation.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import asyncio
import logging
import json
import hashlib
from tenacity import retry, stop_after_attempt, wait_exponential

from app.models import JobIn, OnsiteMode

logger = logging.getLogger(__name__)


class BasePlaywrightScraper(ABC):
    """
    Abstract base class for Playwright-based scrapers using MCP server.
    Designed for sites requiring JavaScript rendering and authentication.
    """
    
    def __init__(
        self,
        source_name: str,
        base_url: str,
        mcp_client: Any,  # PlaywrightMCPClient instance
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        self.source_name = source_name
        self.base_url = base_url
        self.mcp_client = mcp_client
        self.username = username
        self.password = password
        self.rate_limit_delay = 2.0  # Slower for browser automation
        self.last_action_time = 0
        self.logged_in = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        # Check if we need to login
        if self.username and self.password and not self.logged_in:
            await self.login()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Optionally save session state
        pass
    
    @abstractmethod
    async def login(self):
        """
        Implement login flow for authenticated sites.
        Should set self.logged_in = True on success.
        """
        pass
    
    @abstractmethod
    async def scrape_assignments(self, max_pages: int = 5) -> List[JobIn]:
        """
        Main scraping method to fetch job assignments.
        Returns list of JobIn models.
        """
        pass
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def navigate_to(self, url: str) -> bool:
        """Navigate to URL with retry logic."""
        try:
            result = await self.mcp_client.execute_tool(
                "browser_navigate",
                {"url": url}
            )
            await self._rate_limit()
            return True
        except Exception as e:
            logger.error(f"Navigation failed to {url}: {e}")
            raise
    
    async def wait_for_element(
        self,
        selector: str = None,
        text: str = None,
        timeout: int = 10
    ) -> bool:
        """Wait for element to appear on page."""
        try:
            params = {"time": timeout}
            if text:
                params["text"] = text
            
            result = await self.mcp_client.execute_tool(
                "browser_wait_for",
                params
            )
            return True
        except Exception as e:
            logger.warning(f"Element wait failed: {e}")
            return False
    
    async def click_element(self, ref: str, element_description: str) -> bool:
        """Click on element using MCP browser_click tool."""
        try:
            result = await self.mcp_client.execute_tool(
                "browser_click",
                {
                    "ref": ref,
                    "element": element_description
                }
            )
            await self._rate_limit()
            return True
        except Exception as e:
            logger.error(f"Click failed on {element_description}: {e}")
            return False
    
    async def type_text(
        self,
        ref: str,
        text: str,
        element_description: str,
        submit: bool = False
    ) -> bool:
        """Type text into input field."""
        try:
            result = await self.mcp_client.execute_tool(
                "browser_type",
                {
                    "ref": ref,
                    "text": text,
                    "element": element_description,
                    "submit": submit
                }
            )
            await self._rate_limit()
            return True
        except Exception as e:
            logger.error(f"Type failed in {element_description}: {e}")
            return False
    
    async def get_page_snapshot(self) -> Dict[str, Any]:
        """Get accessibility snapshot of current page."""
        try:
            result = await self.mcp_client.execute_tool(
                "browser_snapshot",
                {}
            )
            return result
        except Exception as e:
            logger.error(f"Snapshot failed: {e}")
            return {}
    
    async def evaluate_javascript(
        self,
        function: str,
        element_ref: Optional[str] = None
    ) -> Any:
        """Execute JavaScript on page or element."""
        try:
            params = {"function": function}
            if element_ref:
                params["ref"] = element_ref
                params["element"] = "target element"
            
            result = await self.mcp_client.execute_tool(
                "browser_evaluate",
                params
            )
            return result
        except Exception as e:
            logger.error(f"JavaScript evaluation failed: {e}")
            return None
    
    async def extract_job_data(self) -> List[Dict[str, Any]]:
        """
        Extract job data from current page using JavaScript.
        Override this for site-specific extraction logic.
        """
        extraction_script = """
        () => {
            const jobs = [];
            // Site-specific extraction logic goes here
            // This is a placeholder - override in subclass
            document.querySelectorAll('.job-listing').forEach(job => {
                jobs.push({
                    title: job.querySelector('.title')?.textContent?.trim(),
                    company: job.querySelector('.company')?.textContent?.trim(),
                    location: job.querySelector('.location')?.textContent?.trim(),
                    description: job.querySelector('.description')?.textContent?.trim(),
                    url: job.querySelector('a')?.href
                });
            });
            return jobs;
        }
        """
        return await self.evaluate_javascript(extraction_script) or []
    
    async def handle_pagination(self, page_number: int) -> bool:
        """
        Handle pagination navigation.
        Returns True if next page exists and was loaded.
        """
        # Default implementation - override for specific sites
        next_button_script = """
        () => {
            const nextBtn = document.querySelector('[aria-label="Next page"], .next-page, [rel="next"]');
            if (nextBtn && !nextBtn.disabled) {
                nextBtn.click();
                return true;
            }
            return false;
        }
        """
        
        has_next = await self.evaluate_javascript(next_button_script)
        if has_next:
            await asyncio.sleep(2)  # Wait for page load
            return True
        return False
    
    async def _rate_limit(self):
        """Implement rate limiting between actions."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_action_time
        
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        
        self.last_action_time = asyncio.get_event_loop().time()
    
    def _generate_job_uid(self, job_data: Dict[str, Any]) -> str:
        """Generate unique ID for job posting."""
        unique_string = f"{self.source_name}:{job_data.get('company', '')}:{job_data.get('title', '')}:{job_data.get('location', '')}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:16]
    
    def parse_job_to_model(self, raw_job: Dict[str, Any]) -> JobIn:
        """
        Convert raw scraped data to JobIn model.
        Override for site-specific parsing.
        """
        return JobIn(
            job_uid=self._generate_job_uid(raw_job),
            source=self.source_name,
            title=raw_job.get('title', 'Unknown'),
            description=raw_job.get('description'),
            skills=self.extract_skills(raw_job.get('description', '')),
            role=raw_job.get('role'),
            seniority=self.extract_seniority(raw_job.get('title', '')),
            languages=raw_job.get('languages', []),
            location_city=raw_job.get('location_city'),
            location_country=raw_job.get('location_country', 'Sweden'),
            onsite_mode=self.parse_onsite_mode(raw_job.get('onsite_mode')),
            duration=raw_job.get('duration'),
            start_date=self.parse_date(raw_job.get('start_date')),
            url=raw_job.get('url', self.base_url),
            posted_at=self.parse_date(raw_job.get('posted_at')),
            raw_json=raw_job
        )
    
    def extract_skills(self, text: str) -> List[str]:
        """Extract skills from text - can be overridden."""
        if not text:
            return []
        
        # Common tech skills to look for
        skills_keywords = [
            'Python', 'Java', 'JavaScript', 'TypeScript', 'C#', '.NET', 'React',
            'Angular', 'Vue', 'Node.js', 'AWS', 'Azure', 'GCP', 'Docker',
            'Kubernetes', 'SQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Git',
            'CI/CD', 'DevOps', 'Agile', 'Scrum', 'REST', 'GraphQL', 'Terraform'
        ]
        
        found_skills = []
        text_lower = text.lower()
        
        for skill in skills_keywords:
            if skill.lower() in text_lower:
                found_skills.append(skill)
        
        return list(set(found_skills))
    
    def extract_seniority(self, title: str) -> Optional[str]:
        """Extract seniority level from job title."""
        if not title:
            return None
        
        title_lower = title.lower()
        
        if any(word in title_lower for word in ['senior', 'lead', 'principal', 'staff']):
            return 'senior'
        elif any(word in title_lower for word in ['junior', 'entry']):
            return 'junior'
        elif any(word in title_lower for word in ['mid-level', 'intermediate']):
            return 'mid-level'
        
        return 'mid-level'  # Default
    
    def parse_onsite_mode(self, mode_text: Optional[str]) -> Optional[OnsiteMode]:
        """Parse onsite mode from text."""
        if not mode_text:
            return None
        
        mode_lower = mode_text.lower()
        
        if 'remote' in mode_lower or 'distans' in mode_lower:
            return OnsiteMode.REMOTE
        elif 'hybrid' in mode_lower:
            return OnsiteMode.HYBRID
        elif 'onsite' in mode_lower or 'kontor' in mode_lower:
            return OnsiteMode.ONSITE
        
        return None
    
    def parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime - override for specific formats."""
        if not date_str:
            return None
        
        # Add date parsing logic as needed
        return None