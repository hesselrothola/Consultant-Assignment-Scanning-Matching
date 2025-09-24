"""
eWork (Verama) job portal scraper.
Focuses on senior and expert-level consultant assignments.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import logging
import re
import json
import asyncio

from app.models import JobIn, OnsiteMode
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class EworkScraper(BaseScraper):
    """
    Scraper for eWork/Verama consulting assignments.
    Focuses on Swedish and Nordic senior consultant positions.
    """
    
    def __init__(
        self,
        countries: Optional[List[str]] = None,
        languages: Optional[List[str]] = None,
        seniority_levels: Optional[List[str]] = None,
        target_roles: Optional[List[str]] = None,
        target_keywords: Optional[List[str]] = None,
        onsite_modes: Optional[List[str]] = None,
        target_locations: Optional[List[str]] = None
    ):
        """
        Initialize eWork scraper with configurable filters.
        
        Args:
            countries: List of country codes to filter by (e.g., ['SE', 'NO', 'DK', 'FI'])
                      Default is Sweden only
            languages: List of language codes (e.g., ['SV', 'EN', 'NO', 'DA', 'FI'])
                      Default is Swedish and English
        """
        super().__init__(
            source_name="ework",
            base_url="https://app.verama.com"
        )
        self.api_base = f"{self.base_url}/api/public"
        self.job_listings_url = f"{self.api_base}/job-requests"
        self.max_pages = 5  # Limit pages to scrape
        
        # Filters provided via configuration/overrides
        self.countries = countries or ["SE"]
        self.languages = [lang.upper() for lang in (languages or ["SV", "EN"])]
        self.levels = [level.upper() for level in (seniority_levels or ["SENIOR", "EXPERT"])]
        self.level_set = set(self.levels)
        self.target_roles = target_roles or []
        self.target_keywords = target_keywords or target_roles or []
        self.onsite_modes = [mode.lower() for mode in (onsite_modes or ["onsite", "hybrid", "remote"])]
        self.onsite_mode_set = set(self.onsite_modes)
        self.target_locations = [loc.lower() for loc in (target_locations or [])]
        self.location_set = set(self.target_locations)

        # Map country codes to country names used by eWork
        self.country_mapping = {
            "SE": "Sverige",
            "NO": "Norge", 
            "DK": "Danmark",
            "FI": "Finland",
            "PL": "Polen",  # Remove if you don't have Polish consultants
            "DE": "Tyskland",
            "NL": "Nederländerna",
            "GB": "Storbritannien"
        }
        
        # Filters for senior/expert positions
        self.default_params = {
            "languages": self.languages,
            "level": self.levels,
            "sort": "firstDayOfApplications,DESC",  # Latest first
            "size": 50  # Jobs per page
        }
    
    async def scrape_listings(self) -> List[Dict[str, Any]]:
        """Scrape job listings from eWork/Verama."""
        all_listings = []
        
        try:
            page = 1
            while page <= self.max_pages:
                # Build request parameters
                params = {
                    **self.default_params,
                    "page": page
                }
                
                # Add multiple language parameters
                url = f"{self.job_listings_url}?"
                for lang in params["languages"]:
                    url += f"languages={lang}&"
                for level in params["level"]:
                    url += f"level={level}&"
                url += f"page={params['page']}&size={params['size']}&sort={params['sort']}"
                
                logger.info(f"Fetching eWork page {page}: {url}")
                
                response = await self.fetch_page(url)
                
                # Parse JSON response
                data = response.json()
                
                if not data or "content" not in data:
                    logger.warning(f"No content in response for page {page}")
                    break
                
                jobs = data.get("content", [])
                
                if not jobs:
                    logger.info(f"No more jobs found on page {page}")
                    break
                
                for job_data in jobs:
                    parsed_job = self.parse_job(job_data)
                    if parsed_job:
                        # Filter by country if configured
                        if not self.should_include_job(parsed_job):
                            continue

                        if not self.matches_seniority(parsed_job):
                            continue

                        if not self.matches_target_profile(parsed_job):
                            continue

                        all_listings.append(parsed_job)
                
                # Check if there are more pages
                if data.get("last", True):
                    break
                
                page += 1
                
                # Rate limiting
                await asyncio.sleep(self.rate_limit_delay)
            
            logger.info(f"Scraped {len(all_listings)} listings from eWork")
            
        except Exception as e:
            logger.error(f"Error scraping eWork listings: {e}")
        
        return all_listings
    
    def parse_job(self, job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single job from the API response."""
        try:
            if not job_data:
                return None
                
            parsed = {}
            
            # Extract basic info
            parsed['job_uid'] = f"ework_{job_data.get('id', '')}"
            parsed['source'] = self.source_name
            parsed['title'] = job_data.get('title', '')
            parsed['url'] = f"{self.base_url}/job-requests/{job_data.get('id', '')}"
            
            # Reference number
            parsed['reference'] = job_data.get('systemId', '')
            
            # Company info - using client or legalEntityClient
            client = job_data.get('client', {}) or {}
            legal_client = job_data.get('legalEntityClient', {}) or {}
            parsed['company'] = client.get('name', legal_client.get('name', ''))
            
            # Location info from locations array
            locations = job_data.get('locations', [])
            if locations:
                location = locations[0]  # Take first location
                parsed['location_city'] = location.get('city', '')
                parsed['location_country'] = location.get('country', 'Sweden')
            else:
                parsed['location_city'] = ''
                parsed['location_country'] = 'Sweden'
            
            # Parse onsite mode based on remoteness field
            remoteness = job_data.get('remoteness', 0)
            if remoteness == 100:
                parsed['onsite_mode'] = OnsiteMode.REMOTE.value
            elif remoteness > 0:
                parsed['onsite_mode'] = OnsiteMode.HYBRID.value
            else:
                parsed['onsite_mode'] = OnsiteMode.ONSITE.value
            
            # Skills from skills array
            skills = []
            for skill_obj in job_data.get('skills', []):
                if isinstance(skill_obj, dict) and 'skill' in skill_obj:
                    skill_name = skill_obj['skill'].get('name', '')
                    if skill_name:
                        skills.append(skill_name)
            parsed['skills'] = skills
            
            # Languages - might need to be fetched separately or hardcoded based on filter
            parsed['languages'] = ['Swedish', 'English']  # Based on our filter
            
            # Seniority level
            level = job_data.get('level', '')
            parsed['seniority'] = level
            
            # Role extraction from title
            parsed['role'] = self.extract_role_from_title(parsed['title'])
            
            # Duration from start/end dates
            start_date = job_data.get('startDate', '')
            end_date = job_data.get('endDate', '')
            if start_date and end_date:
                parsed['duration'] = f"{start_date} to {end_date}"
            
            # Start date
            if start_date:
                try:
                    # Parse date in format YYYY-MM-DD
                    from datetime import datetime
                    parsed['start_date'] = datetime.strptime(start_date, '%Y-%m-%d')
                except:
                    pass
            
            # Posted date from firstDayOfApplications
            posted_str = job_data.get('firstDayOfApplications', job_data.get('createdDate'))
            if posted_str:
                try:
                    parsed['posted_at'] = datetime.fromisoformat(posted_str.replace('Z', '+00:00'))
                except:
                    pass
            
            # Rate/budget info
            rate_info = job_data.get('rate', {}) or {}
            if rate_info:
                currency = rate_info.get('currency', 'SEK')
                max_rate = rate_info.get('maxRate')
                rate_type = rate_info.get('clientRateType', 'HOURLY')
                if max_rate:
                    parsed['rate'] = f"{max_rate} {currency}/{rate_type.lower()}"
                else:
                    parsed['rate'] = f"{currency}/{rate_type.lower()}"
            
            # Hours per week
            hours = job_data.get('hoursPerWeek')
            if hours:
                parsed['hours_per_week'] = hours
            
            # Store raw data for reference
            parsed['raw_json'] = job_data
            
            return parsed if parsed.get('title') else None
            
        except Exception as e:
            logger.error(f"Error parsing eWork job: {e}")
            logger.error(f"Job data: {job_data}")
            return None
    
    def extract_skills_from_text(self, text: str) -> List[str]:
        """Extract potential skills from requirement text."""
        if not text:
            return []
        
        # Common skill patterns for senior consultants
        skill_patterns = [
            r'\b(Python|Java|C\+\+|C#|JavaScript|TypeScript|Go|Rust|Kotlin|Swift)\b',
            r'\b(React|Angular|Vue|Node\.js|Django|Flask|Spring|\.NET|Rails)\b',
            r'\b(AWS|Azure|GCP|Docker|Kubernetes|Terraform|Jenkins|GitLab)\b',
            r'\b(PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|Kafka)\b',
            r'\b(Agile|Scrum|SAFe|DevOps|CI/CD|Microservices|REST|GraphQL)\b',
            r'\b(Machine Learning|AI|Data Science|Analytics|BI|ETL)\b',
            r'\b(Architecture|Design Patterns|System Design|Integration)\b',
            r'\b(Project Management|Team Lead|Technical Lead|Architect)\b'
        ]
        
        skills = []
        for pattern in skill_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            skills.extend(matches)
        
        return list(set(skills))
    
    def should_include_job(self, job: Dict[str, Any]) -> bool:
        """
        Check if job should be included based on country filter.
        
        Args:
            job: Parsed job data
            
        Returns:
            True if job should be included, False otherwise
        """
        # Country filter
        if self.countries:
            job_country = (job.get('location_country') or "").lower()
            country_match = False

            for country_code in self.countries:
                country_name = self.country_mapping.get(country_code, country_code)
                if country_code.lower() in job_country or country_name.lower() in job_country:
                    country_match = True
                    break

                country_variations = {
                    "SE": ["sweden", "sverige", "se"],
                    "NO": ["norway", "norge", "no"],
                    "DK": ["denmark", "danmark", "dk"],
                    "FI": ["finland", "suomi", "fi"],
                    "PL": ["poland", "polen", "polska", "pl"],
                }

                if country_code in country_variations:
                    if any(variation in job_country for variation in country_variations[country_code]):
                        country_match = True
                        break

            if not country_match:
                return False

        # Onsite mode filter
        if self.onsite_mode_set:
            job_mode = (job.get('onsite_mode') or "").lower()
            if job_mode and job_mode not in self.onsite_mode_set:
                return False

        # Location filter
        if self.location_set:
            job_city = (job.get('location_city') or "").lower()
            job_location_text = f"{job_city} {(job.get('location_country') or '').lower()}"
            if job_location_text:
                if not any(loc in job_location_text for loc in self.location_set):
                    # Allow remote/hybrid listings even if city not matched
                    job_mode = (job.get('onsite_mode') or "").lower()
                    if job_mode not in ("remote", "hybrid"):
                        return False

        return True

    def matches_seniority(self, job: Dict[str, Any]) -> bool:
        """Verify that the job seniority matches desired executive levels."""
        if not self.levels:
            return True
        job_level = job.get('seniority')
        if not job_level:
            return False
        return job_level.upper() in self.level_set

    def matches_target_profile(self, job: Dict[str, Any]) -> bool:
        """Check whether the job aligns with executive target roles/keywords."""
        keywords = [kw.lower() for kw in (self.target_keywords or []) if kw]
        roles = [role.lower() for role in (self.target_roles or []) if role]
        search_terms = keywords or roles
        if not search_terms:
            return True

        text_parts = [job.get('title', ''), job.get('role', '')]
        if job.get('skills'):
            text_parts.append(' '.join(job['skills']))

        raw = job.get('raw_json') or {}
        for key in ('missionDescription', 'requirementDescription', 'description', 'descriptionText'):
            value = raw.get(key)
            if value:
                text_parts.append(value)

        haystack = ' '.join(text_parts).lower()
        return any(term in haystack for term in search_terms)
    
    def parse_listing(self, listing_element) -> Optional[Dict[str, Any]]:
        """Parse a single job listing element - not used for API-based scraper."""
        # This method is required by the abstract base class but not used
        # since we're using the API directly instead of HTML parsing
        return None
    
    def extract_role_from_title(self, title: str) -> str:
        """Extract role category from job title."""
        title_lower = title.lower()
        
        # Senior role mappings
        role_mappings = {
            'architect': 'Architect',
            'lead': 'Technical Lead',
            'manager': 'Manager',
            'konsult': 'Consultant',
            'developer': 'Developer',
            'engineer': 'Engineer',
            'analyst': 'Analyst',
            'specialist': 'Specialist',
            'expert': 'Expert',
            'senior': 'Senior Consultant',
            'projektledare': 'Project Manager',
            'chef': 'Manager',
            'director': 'Director',
            'head': 'Head'
        }
        
        for keyword, role in role_mappings.items():
            if keyword in title_lower:
                return role
        
        return 'Consultant'
    
    async def convert_to_job_model(self, job_data: Dict[str, Any]) -> Optional[JobIn]:
        """Convert parsed job data to JobIn model."""
        try:
            # Ensure required fields
            if not job_data.get('job_uid') or not job_data.get('url'):
                return None
            
            return JobIn(
                job_uid=job_data['job_uid'],
                source=job_data['source'],
                title=job_data.get('title', ''),
                description=job_data.get('description'),
                skills=job_data.get('skills', []),
                role=job_data.get('role'),
                seniority=job_data.get('seniority'),
                languages=job_data.get('languages', []),
                location_city=job_data.get('location_city'),
                location_country=job_data.get('location_country', 'SE'),
                onsite_mode=job_data.get('onsite_mode'),
                duration=job_data.get('duration'),
                start_date=job_data.get('start_date'),
                url=job_data['url'],
                posted_at=job_data.get('posted_at'),
                raw_json=job_data.get('raw_json', {})
            )
            
        except Exception as e:
            logger.error(f"Error converting to JobIn model: {e}")
            return None
