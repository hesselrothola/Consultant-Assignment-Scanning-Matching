from typing import List, Optional, Dict, Any
from selectolax.parser import HTMLParser
import re
from datetime import datetime, date
import logging

from app.models import JobIn

logger = logging.getLogger(__name__)


class GenericHTMLParser:
    """Generic HTML parser for job listings."""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
    
    def parse_job_listing(self, html: str, url: str = None) -> List[JobIn]:
        """Parse HTML content to extract job listings."""
        parser = HTMLParser(html)
        jobs = []
        
        # Try different common job listing selectors
        selectors = [
            'article.job-listing',
            'div.job-item',
            'li.job-card',
            'div.vacancy',
            'div.assignment',
            'article.posting',
            'div[class*="job"]',
            'div[class*="assignment"]'
        ]
        
        job_elements = None
        for selector in selectors:
            job_elements = parser.css(selector)
            if job_elements:
                break
        
        if not job_elements:
            # Try to parse as single job page
            job = self._parse_single_job(parser, url)
            if job:
                jobs.append(job)
        else:
            # Parse multiple job listings
            for element in job_elements:
                job = self._parse_job_element(element, url)
                if job:
                    jobs.append(job)
        
        return jobs
    
    def _parse_job_element(self, element, base_url: str = None) -> Optional[JobIn]:
        """Parse individual job element."""
        try:
            # Extract title
            title = self._extract_title(element)
            if not title:
                return None
            
            # Extract URL
            url = self._extract_url(element, base_url)
            
            # Extract company
            company = self._extract_company(element)
            
            # Extract location
            location = self._extract_location(element)
            
            # Extract description
            description = self._extract_description(element)
            
            # Extract requirements
            requirements = self._extract_requirements(element)
            
            # Extract skills
            skills = self._extract_skills(element)
            
            # Extract dates
            start_date, end_date = self._extract_dates(element)
            
            # Generate external ID
            external_id = self._generate_external_id(url or title)
            
            return JobIn(
                external_id=external_id,
                source=self.source_name,
                title=title,
                company=company,
                location=location,
                description=description,
                requirements=requirements,
                skills=skills,
                start_date=start_date,
                end_date=end_date,
                url=url,
                raw_data={'html_source': True}
            )
            
        except Exception as e:
            logger.error(f"Error parsing job element: {e}")
            return None
    
    def _parse_single_job(self, parser: HTMLParser, url: str = None) -> Optional[JobIn]:
        """Parse a single job page."""
        try:
            # Extract from common meta tags or structured data
            title = self._extract_meta_property(parser, 'og:title') or \
                    self._extract_text(parser, 'h1')
            
            if not title:
                return None
            
            description = self._extract_meta_property(parser, 'og:description') or \
                         self._extract_text(parser, 'div.description, div.job-description')
            
            company = self._extract_text(parser, '.company-name, .employer')
            location = self._extract_text(parser, '.location, .job-location')
            
            # Extract structured data if available
            structured_data = self._extract_structured_data(parser)
            if structured_data:
                title = structured_data.get('title', title)
                company = structured_data.get('hiringOrganization', {}).get('name', company)
                location = structured_data.get('jobLocation', {}).get('address', {}).get('addressLocality', location)
            
            skills = self._extract_skills_from_text(description)
            
            return JobIn(
                external_id=self._generate_external_id(url or title),
                source=self.source_name,
                title=title,
                company=company,
                location=location,
                description=description,
                skills=skills,
                url=url,
                raw_data={'single_page': True}
            )
            
        except Exception as e:
            logger.error(f"Error parsing single job page: {e}")
            return None
    
    def _extract_title(self, element) -> Optional[str]:
        """Extract job title."""
        selectors = [
            'h2', 'h3', 'h4',
            '.job-title', '.title',
            'a[class*="title"]',
            '[class*="heading"]'
        ]
        
        for selector in selectors:
            title_elem = element.css_first(selector)
            if title_elem:
                return title_elem.text(strip=True)
        
        return None
    
    def _extract_url(self, element, base_url: str = None) -> Optional[str]:
        """Extract job URL."""
        link = element.css_first('a[href]')
        if link:
            href = link.attributes.get('href')
            if href:
                if base_url and not href.startswith('http'):
                    # Make URL absolute
                    from urllib.parse import urljoin
                    return urljoin(base_url, href)
                return href
        return None
    
    def _extract_company(self, element) -> Optional[str]:
        """Extract company name."""
        selectors = [
            '.company', '.employer',
            '[class*="company"]',
            '[class*="employer"]'
        ]
        
        for selector in selectors:
            company_elem = element.css_first(selector)
            if company_elem:
                return company_elem.text(strip=True)
        
        return None
    
    def _extract_location(self, element) -> Optional[str]:
        """Extract job location."""
        selectors = [
            '.location', '.place',
            '[class*="location"]',
            '[class*="place"]'
        ]
        
        for selector in selectors:
            location_elem = element.css_first(selector)
            if location_elem:
                return location_elem.text(strip=True)
        
        return None
    
    def _extract_description(self, element) -> Optional[str]:
        """Extract job description."""
        selectors = [
            '.description', '.summary',
            '[class*="description"]',
            '[class*="summary"]',
            'p'
        ]
        
        descriptions = []
        for selector in selectors:
            desc_elems = element.css(selector)
            for desc_elem in desc_elems:
                text = desc_elem.text(strip=True)
                if text and len(text) > 50:  # Filter out short texts
                    descriptions.append(text)
        
        return ' '.join(descriptions) if descriptions else None
    
    def _extract_requirements(self, element) -> Optional[str]:
        """Extract job requirements."""
        selectors = [
            '.requirements', '.qualifications',
            '[class*="requirement"]',
            '[class*="qualification"]'
        ]
        
        for selector in selectors:
            req_elem = element.css_first(selector)
            if req_elem:
                return req_elem.text(strip=True)
        
        return None
    
    def _extract_skills(self, element) -> List[str]:
        """Extract skills from element."""
        skills = []
        
        # Look for skill tags
        skill_selectors = [
            '.skill', '.tag',
            '[class*="skill"]',
            '[class*="tag"]'
        ]
        
        for selector in skill_selectors:
            skill_elems = element.css(selector)
            for skill_elem in skill_elems:
                skill = skill_elem.text(strip=True)
                if skill and len(skill) < 50:  # Filter out long texts
                    skills.append(skill)
        
        # Also extract from description
        desc = self._extract_description(element)
        if desc:
            skills.extend(self._extract_skills_from_text(desc))
        
        return list(set(skills))  # Remove duplicates
    
    def _extract_skills_from_text(self, text: str) -> List[str]:
        """Extract skills from free text."""
        if not text:
            return []
        
        # Common technical skills
        skill_patterns = [
            r'\b(?:Python|Java|JavaScript|TypeScript|C#|C\+\+|Go|Rust|Kotlin|Swift|Ruby|PHP|Scala)\b',
            r'\b(?:React|Angular|Vue|Django|Flask|FastAPI|Spring|Node\.js|\.NET|Rails|Laravel)\b',
            r'\b(?:PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|SQL|NoSQL|Oracle)\b',
            r'\b(?:AWS|Azure|GCP|Docker|Kubernetes|Jenkins|CI/CD|Terraform|Ansible)\b',
            r'\b(?:Machine Learning|AI|Data Science|TensorFlow|PyTorch|Pandas|NumPy)\b',
            r'\b(?:REST|GraphQL|Microservices|Agile|Scrum|Git|DevOps|Cloud)\b'
        ]
        
        skills = []
        for pattern in skill_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            skills.extend(matches)
        
        return list(set(skills))
    
    def _extract_dates(self, element) -> tuple[Optional[date], Optional[date]]:
        """Extract start and end dates."""
        date_text = element.text()
        
        # Look for date patterns
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'(\d{1,2}\s+\w+\s+\d{4})'
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, date_text)
            for match in matches:
                try:
                    # Try to parse date
                    parsed_date = datetime.strptime(match, '%Y-%m-%d').date()
                    dates.append(parsed_date)
                except:
                    pass
        
        if len(dates) >= 2:
            return min(dates), max(dates)
        elif len(dates) == 1:
            return dates[0], None
        
        return None, None
    
    def _extract_text(self, parser: HTMLParser, selector: str) -> Optional[str]:
        """Extract text from parser using selector."""
        elem = parser.css_first(selector)
        if elem:
            return elem.text(strip=True)
        return None
    
    def _extract_meta_property(self, parser: HTMLParser, property: str) -> Optional[str]:
        """Extract meta property content."""
        meta = parser.css_first(f'meta[property="{property}"]')
        if meta:
            return meta.attributes.get('content')
        return None
    
    def _extract_structured_data(self, parser: HTMLParser) -> Optional[Dict[str, Any]]:
        """Extract JSON-LD structured data."""
        script = parser.css_first('script[type="application/ld+json"]')
        if script:
            try:
                import json
                data = json.loads(script.text())
                if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                    return data
            except:
                pass
        return None
    
    def _generate_external_id(self, seed: str) -> str:
        """Generate external ID from seed string."""
        import hashlib
        return hashlib.md5(seed.encode()).hexdigest()