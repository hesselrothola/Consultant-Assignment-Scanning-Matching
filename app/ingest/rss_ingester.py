import feedparser
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging
import re

from app.models import JobIn
from app.ingest.base import BaseIngester

logger = logging.getLogger(__name__)


class RSSIngester(BaseIngester):
    """Ingest jobs from RSS feeds."""
    
    def __init__(self, feed_url: str, source_name: str):
        super().__init__(source_name)
        self.feed_url = feed_url
    
    async def fetch_jobs(self) -> List[JobIn]:
        """Fetch jobs from RSS feed."""
        try:
            # Parse RSS feed
            feed = feedparser.parse(self.feed_url)
            
            if feed.bozo:
                logger.error(f"Error parsing RSS feed: {feed.bozo_exception}")
                return []
            
            jobs = []
            for entry in feed.entries:
                job = await self._parse_entry(entry)
                if job:
                    jobs.append(job)
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error fetching RSS feed {self.feed_url}: {e}")
            return []
    
    async def _parse_entry(self, entry: Any) -> Optional[JobIn]:
        """Parse RSS entry into JobIn model."""
        try:
            # Extract basic fields
            title = entry.get('title', '')
            url = entry.get('link', '')
            description = entry.get('summary', '') or entry.get('description', '')
            
            # Generate external ID from URL or guid
            external_id = entry.get('id') or entry.get('guid') or url
            
            # Parse published date
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published = datetime.fromtimestamp(
                    feedparser._parse_date(entry.published).timestamp(),
                    tz=timezone.utc
                )
            
            # Extract company from title or description
            company = self._extract_company(title, description)
            
            # Extract location
            location = self._extract_location(description)
            
            # Extract skills
            skills = self._extract_skills(description)
            
            # Create raw data
            raw_data = {
                'title': title,
                'url': url,
                'description': description,
                'published': published.isoformat() if published else None,
                'source': 'rss',
                'feed_url': self.feed_url
            }
            
            return JobIn(
                external_id=external_id,
                source=self.source_name,
                title=title,
                company=company,
                location=location,
                description=description,
                skills=skills,
                url=url,
                raw_data=raw_data
            )
            
        except Exception as e:
            logger.error(f"Error parsing RSS entry: {e}")
            return None
    
    def _extract_company(self, title: str, description: str) -> Optional[str]:
        """Extract company name from title or description."""
        # Common patterns for company names
        patterns = [
            r'(?:hos|at|för|@)\s+([A-Z][A-Za-z0-9\s&]+)',
            r'([A-Z][A-Za-z0-9\s&]+)\s+(?:söker|seeks|looking)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title + ' ' + description)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location from text."""
        # Common Swedish cities and regions
        locations = [
            'Stockholm', 'Göteborg', 'Gothenburg', 'Malmö', 'Uppsala',
            'Linköping', 'Örebro', 'Västerås', 'Helsingborg', 'Norrköping',
            'Jönköping', 'Umeå', 'Lund', 'Sundsvall', 'Karlstad',
            'Remote', 'Distans'
        ]
        
        text_lower = text.lower()
        for location in locations:
            if location.lower() in text_lower:
                return location
        
        return None
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract technical skills from text."""
        # Common technical skills and technologies
        skill_keywords = [
            # Programming languages
            'Python', 'Java', 'JavaScript', 'TypeScript', 'C#', 'C++',
            'Go', 'Rust', 'Kotlin', 'Swift', 'Ruby', 'PHP', 'Scala',
            
            # Frameworks
            'React', 'Angular', 'Vue', 'Django', 'Flask', 'FastAPI',
            'Spring', 'Node.js', '.NET', 'Rails', 'Laravel',
            
            # Databases
            'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Elasticsearch',
            'SQL', 'NoSQL', 'Oracle', 'SQL Server',
            
            # Cloud & DevOps
            'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Jenkins',
            'CI/CD', 'Terraform', 'Ansible', 'Linux',
            
            # Data & AI
            'Machine Learning', 'AI', 'Data Science', 'TensorFlow',
            'PyTorch', 'Pandas', 'NumPy', 'Spark', 'Hadoop',
            
            # Other
            'REST', 'GraphQL', 'Microservices', 'Agile', 'Scrum',
            'Git', 'DevOps', 'Cloud', 'Security', 'Testing'
        ]
        
        found_skills = []
        text_lower = text.lower()
        
        for skill in skill_keywords:
            if skill.lower() in text_lower:
                found_skills.append(skill)
        
        return found_skills