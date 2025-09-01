"""
Base scraper class for all assignment portal scrapers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import asyncio
import logging
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import hashlib
import json

from app.models import JobIn, OnsiteMode

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for job assignment scrapers."""
    
    def __init__(self, source_name: str, base_url: str):
        self.source_name = source_name
        self.base_url = base_url
        self.session: Optional[httpx.AsyncClient] = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'sv-SE,sv;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.rate_limit_delay = 1.0  # Seconds between requests
        self.last_request_time = 0
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = httpx.AsyncClient(
            headers=self.headers,
            timeout=30.0,
            follow_redirects=True
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.aclose()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_page(self, url: str, **kwargs) -> httpx.Response:
        """Fetch a page with rate limiting and retry logic."""
        # Rate limiting
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        
        if not self.session:
            raise RuntimeError("Scraper must be used as async context manager")
        
        logger.debug(f"Fetching {url}")
        response = await self.session.get(url, **kwargs)
        response.raise_for_status()
        
        self.last_request_time = asyncio.get_event_loop().time()
        return response
    
    @abstractmethod
    async def scrape_listings(self) -> List[Dict[str, Any]]:
        """Scrape job listings from the portal. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def parse_listing(self, listing_html: Any) -> Optional[Dict[str, Any]]:
        """Parse a single job listing. Must be implemented by subclasses."""
        pass
    
    async def scrape(self) -> List[JobIn]:
        """Main scraping method that returns JobIn models."""
        try:
            raw_listings = await self.scrape_listings()
            jobs = []
            
            for listing_data in raw_listings:
                job = self.create_job_model(listing_data)
                if job:
                    jobs.append(job)
            
            logger.info(f"Scraped {len(jobs)} jobs from {self.source_name}")
            return jobs
            
        except Exception as e:
            logger.error(f"Error scraping {self.source_name}: {e}")
            return []
    
    def create_job_model(self, data: Dict[str, Any]) -> Optional[JobIn]:
        """Convert scraped data to JobIn model."""
        try:
            # Generate unique job ID from URL or title+company
            uid_source = data.get('url', '') or f"{data.get('title', '')}-{data.get('company', '')}"
            job_uid = hashlib.md5(uid_source.encode()).hexdigest()
            
            # Parse onsite mode
            onsite_mode = self.parse_onsite_mode(data.get('location', ''), data.get('description', ''))
            
            # Extract location parts
            location_city, location_country = self.parse_location(data.get('location', ''))
            
            # Parse skills from description and requirements
            skills = self.extract_skills(
                data.get('description', ''),
                data.get('requirements', ''),
                data.get('title', '')
            )
            
            # Parse languages
            languages = self.extract_languages(
                data.get('description', ''),
                data.get('requirements', '')
            )
            
            # Determine role and seniority from title
            role, seniority = self.parse_role_and_seniority(data.get('title', ''))
            
            return JobIn(
                job_uid=f"{self.source_name}_{job_uid}",
                source=self.source_name,
                title=data.get('title', ''),
                description=data.get('description'),
                skills=skills,
                role=role,
                seniority=seniority,
                languages=languages,
                location_city=location_city,
                location_country=location_country,
                onsite_mode=onsite_mode,
                duration=data.get('duration'),
                start_date=self.parse_date(data.get('start_date')),
                company=data.get('company'),
                broker=data.get('broker'),
                url=data.get('url', ''),
                posted_at=self.parse_date(data.get('posted_at')),
                raw_json=data
            )
            
        except Exception as e:
            logger.error(f"Error creating job model: {e}")
            return None
    
    def parse_onsite_mode(self, location: str, description: str) -> Optional[OnsiteMode]:
        """Determine onsite mode from location and description."""
        text = f"{location} {description}".lower()
        
        if any(term in text for term in ['remote', 'distans', 'hemma', 'distributed']):
            return OnsiteMode.REMOTE
        elif any(term in text for term in ['hybrid', 'delvis', 'partial', 'flexibel']):
            return OnsiteMode.HYBRID
        elif any(term in text for term in ['onsite', 'on-site', 'kontor', 'office']):
            return OnsiteMode.ONSITE
        
        return None
    
    def parse_location(self, location_str: str) -> tuple[Optional[str], str]:
        """Parse location string into city and country."""
        if not location_str:
            return None, "Sweden"
        
        # Common Swedish cities
        swedish_cities = [
            'Stockholm', 'Göteborg', 'Gothenburg', 'Malmö', 'Uppsala',
            'Västerås', 'Örebro', 'Linköping', 'Helsingborg', 'Jönköping',
            'Norrköping', 'Lund', 'Umeå', 'Gävle', 'Borås', 'Sundsvall',
            'Eskilstuna', 'Södertälje', 'Karlstad', 'Täby', 'Växjö'
        ]
        
        location_lower = location_str.lower()
        for city in swedish_cities:
            if city.lower() in location_lower:
                return city, "Sweden"
        
        # Check for other Nordic countries
        if any(term in location_lower for term in ['norge', 'norway', 'oslo', 'bergen']):
            return location_str, "Norway"
        elif any(term in location_lower for term in ['danmark', 'denmark', 'copenhagen', 'köpenhamn']):
            return location_str, "Denmark"
        elif any(term in location_lower for term in ['finland', 'helsinki', 'helsingfors']):
            return location_str, "Finland"
        
        # Default to location as-is with Sweden as country
        return location_str, "Sweden"
    
    def extract_skills(self, description: str, requirements: str, title: str) -> List[str]:
        """Extract technical skills from text."""
        text = f"{title} {description} {requirements}".lower()
        found_skills = []
        
        # Comprehensive skill keywords
        skill_patterns = {
            # Programming Languages
            'Python', 'Java', 'JavaScript', 'TypeScript', 'C#', '.NET', 'C++',
            'Go', 'Golang', 'Rust', 'Kotlin', 'Swift', 'Ruby', 'PHP', 'Scala',
            'R', 'MATLAB', 'Perl', 'Bash', 'PowerShell', 'SQL', 'T-SQL',
            
            # Frontend
            'React', 'Angular', 'Vue', 'Vue.js', 'Svelte', 'Next.js', 'Nuxt',
            'HTML', 'CSS', 'SASS', 'LESS', 'Tailwind', 'Bootstrap', 'jQuery',
            'Redux', 'MobX', 'RxJS', 'WebPack', 'Vite', 'GraphQL',
            
            # Backend
            'Node.js', 'Express', 'NestJS', 'Django', 'Flask', 'FastAPI',
            'Spring', 'Spring Boot', 'ASP.NET', 'Rails', 'Laravel', 'Symfony',
            'Gin', 'Echo', 'Fiber', 'Actix',
            
            # Databases
            'PostgreSQL', 'MySQL', 'MariaDB', 'MongoDB', 'Redis', 'Elasticsearch',
            'Cassandra', 'DynamoDB', 'CosmosDB', 'Oracle', 'SQL Server', 'SQLite',
            'Neo4j', 'InfluxDB', 'Snowflake', 'BigQuery',
            
            # Cloud & DevOps
            'AWS', 'Azure', 'GCP', 'Google Cloud', 'Docker', 'Kubernetes', 'K8s',
            'Jenkins', 'GitLab', 'GitHub Actions', 'CircleCI', 'Travis CI',
            'Terraform', 'Ansible', 'Puppet', 'Chef', 'CloudFormation',
            'Helm', 'ArgoCD', 'Prometheus', 'Grafana', 'ELK', 'Datadog',
            
            # Data & AI
            'Machine Learning', 'ML', 'AI', 'Deep Learning', 'TensorFlow',
            'PyTorch', 'Scikit-learn', 'Keras', 'Pandas', 'NumPy', 'Spark',
            'Hadoop', 'Kafka', 'Airflow', 'Databricks', 'MLflow', 'Kubeflow',
            
            # Mobile
            'iOS', 'Android', 'React Native', 'Flutter', 'Xamarin', 'Ionic',
            'Swift', 'Objective-C', 'Kotlin', 'Java',
            
            # Other Technologies
            'Microservices', 'REST', 'SOAP', 'gRPC', 'WebSocket', 'OAuth',
            'SAML', 'JWT', 'Blockchain', 'Ethereum', 'Solidity',
            'SAP', 'Salesforce', 'ServiceNow', 'SharePoint', 'Dynamics',
            'Linux', 'Unix', 'Windows Server', 'VMware', 'Hyper-V',
            'Agile', 'Scrum', 'Kanban', 'DevOps', 'CI/CD', 'Git'
        }
        
        for skill in skill_patterns:
            # Check for word boundaries to avoid false matches
            import re
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, text):
                found_skills.append(skill)
        
        return list(set(found_skills))  # Remove duplicates
    
    def extract_languages(self, description: str, requirements: str) -> List[str]:
        """Extract language requirements from text."""
        text = f"{description} {requirements}".lower()
        languages = []
        
        language_patterns = {
            'Swedish': ['swedish', 'svenska', 'svensk'],
            'English': ['english', 'engelska'],
            'Norwegian': ['norwegian', 'norska', 'norsk'],
            'Danish': ['danish', 'danska', 'dansk'],
            'Finnish': ['finnish', 'finska', 'finsk'],
            'German': ['german', 'tyska', 'deutsch'],
            'French': ['french', 'franska', 'français'],
            'Spanish': ['spanish', 'spanska', 'español']
        }
        
        for language, patterns in language_patterns.items():
            if any(pattern in text for pattern in patterns):
                languages.append(language)
        
        # Default to Swedish and English if none found (Swedish market assumption)
        if not languages:
            languages = ['Swedish', 'English']
        
        return languages
    
    def parse_role_and_seniority(self, title: str) -> tuple[Optional[str], Optional[str]]:
        """Extract role and seniority from job title."""
        title_lower = title.lower()
        
        # Role patterns
        role_patterns = {
            'Backend Developer': ['backend', 'back-end'],
            'Frontend Developer': ['frontend', 'front-end'],
            'Full Stack Developer': ['fullstack', 'full-stack', 'full stack'],
            'DevOps Engineer': ['devops', 'dev ops'],
            'Data Engineer': ['data engineer'],
            'Data Scientist': ['data scientist'],
            'ML Engineer': ['ml engineer', 'machine learning engineer'],
            'Cloud Architect': ['cloud architect'],
            'Solution Architect': ['solution architect', 'lösningsarkitekt'],
            'Software Architect': ['software architect', 'arkitekt'],
            'Tech Lead': ['tech lead', 'technical lead', 'teknisk ledare'],
            'Scrum Master': ['scrum master'],
            'Project Manager': ['project manager', 'projektledare'],
            'Product Owner': ['product owner', 'produktägare'],
            'QA Engineer': ['qa', 'test', 'quality'],
            'Security Engineer': ['security', 'säkerhet'],
            'Platform Engineer': ['platform engineer'],
            'Site Reliability Engineer': ['sre', 'site reliability'],
            'Mobile Developer': ['mobile', 'ios', 'android'],
            'Embedded Developer': ['embedded'],
            'Consultant': ['konsult', 'consultant']
        }
        
        role = None
        for role_name, patterns in role_patterns.items():
            if any(pattern in title_lower for pattern in patterns):
                role = role_name
                break
        
        # If no specific role found, try generic
        if not role:
            if 'developer' in title_lower or 'utvecklare' in title_lower:
                role = 'Software Developer'
            elif 'engineer' in title_lower or 'ingenjör' in title_lower:
                role = 'Software Engineer'
        
        # Seniority patterns
        seniority = None
        if any(term in title_lower for term in ['senior', 'sr.', 'lead', 'principal', 'staff']):
            seniority = 'Senior'
        elif any(term in title_lower for term in ['junior', 'jr.', 'entry']):
            seniority = 'Junior'
        elif any(term in title_lower for term in ['mid', 'medior']):
            seniority = 'Mid'
        
        return role, seniority
    
    def parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse various date formats."""
        if not date_str:
            return None
        
        date_formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%d.%m.%Y',
            '%B %d, %Y',
            '%d %B %Y',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        
        # Try Swedish month names
        swedish_months = {
            'januari': 'January', 'februari': 'February', 'mars': 'March',
            'april': 'April', 'maj': 'May', 'juni': 'June',
            'juli': 'July', 'augusti': 'August', 'september': 'September',
            'oktober': 'October', 'november': 'November', 'december': 'December'
        }
        
        date_str_en = date_str
        for sv, en in swedish_months.items():
            date_str_en = date_str_en.replace(sv, en)
        
        if date_str_en != date_str:
            for fmt in ['%d %B %Y', '%B %d, %Y']:
                try:
                    return datetime.strptime(date_str_en, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None