from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import httpx
from selectolax.parser import HTMLParser
import logging

from app.models import JobIn

logger = logging.getLogger(__name__)


class BaseIngester(ABC):
    """Base class for all job ingestion sources."""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @abstractmethod
    async def fetch_jobs(self) -> List[JobIn]:
        """Fetch jobs from the source."""
        pass
    
    async def fetch_html(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL."""
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def parse_html(self, html: str) -> HTMLParser:
        """Parse HTML content."""
        return HTMLParser(html)
    
    def extract_text(self, element, selector: str, default: str = "") -> str:
        """Extract text from element using CSS selector."""
        if not element:
            return default
        
        found = element.css_first(selector)
        if found:
            return found.text(strip=True)
        return default
    
    def extract_all_text(self, element, selector: str) -> List[str]:
        """Extract all text matching selector."""
        if not element:
            return []
        
        return [el.text(strip=True) for el in element.css(selector)]