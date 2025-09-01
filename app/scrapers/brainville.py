"""
Brainville job portal scraper.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging
import re
from selectolax.parser import HTMLParser
import json

from .base import BaseScraper
from app.models import JobIn

logger = logging.getLogger(__name__)


class BrainvilleScraper(BaseScraper):
    """Scraper for Brainville consulting assignments."""
    
    def __init__(self):
        super().__init__(
            source_name="brainville",
            base_url="https://www.brainville.com"
        )
        self.listings_url = f"{self.base_url}/konsultuppdrag"
        self.max_pages = 10  # Limit pages to scrape
    
    async def scrape_listings(self) -> List[Dict[str, Any]]:
        """Scrape job listings from Brainville."""
        all_listings = []
        
        try:
            # Start with the main listings page
            page = 1
            while page <= self.max_pages:
                url = f"{self.listings_url}?page={page}" if page > 1 else self.listings_url
                
                response = await self.fetch_page(url)
                html = HTMLParser(response.text)
                
                # Find job listing elements (adjust selectors based on actual HTML structure)
                # Note: These selectors are placeholders - need to inspect actual Brainville HTML
                listings = html.css('.assignment-item, .job-listing, .consultant-assignment')
                
                if not listings:
                    # Try alternative selectors
                    listings = html.css('article.assignment, div.assignment-card, div.listing')
                
                if not listings:
                    logger.warning(f"No listings found on page {page}")
                    break
                
                for listing in listings:
                    listing_data = self.parse_listing(listing)
                    if listing_data:
                        # Fetch additional details if there's a detail page
                        if listing_data.get('url'):
                            detailed_data = await self.fetch_job_details(listing_data['url'])
                            if detailed_data:
                                listing_data.update(detailed_data)
                        
                        all_listings.append(listing_data)
                
                # Check if there's a next page
                next_button = html.css_first('.pagination .next, a[rel="next"], .next-page')
                if not next_button or 'disabled' in (next_button.attributes.get('class', '')):
                    break
                
                page += 1
                
                # Small delay between pages to be respectful
                import asyncio
                await asyncio.sleep(self.rate_limit_delay)
            
            logger.info(f"Scraped {len(all_listings)} listings from Brainville")
            
        except Exception as e:
            logger.error(f"Error scraping Brainville listings: {e}")
        
        return all_listings
    
    def parse_listing(self, listing_element) -> Optional[Dict[str, Any]]:
        """Parse a single job listing element."""
        try:
            data = {}
            
            # Title extraction (adjust selectors based on actual HTML)
            title_elem = listing_element.css_first('h2, h3, .title, .assignment-title')
            if title_elem:
                data['title'] = title_elem.text(strip=True)
            
            # URL extraction
            link_elem = listing_element.css_first('a[href*="/uppdrag/"], a[href*="/assignment/"], a.title-link')
            if link_elem:
                href = link_elem.attributes.get('href', '')
                if href:
                    data['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
            
            # Company extraction
            company_elem = listing_element.css_first('.company, .client, .customer, .företag')
            if company_elem:
                data['company'] = company_elem.text(strip=True)
            
            # Location extraction
            location_elem = listing_element.css_first('.location, .city, .ort, .plats')
            if location_elem:
                data['location'] = location_elem.text(strip=True)
            
            # Duration extraction
            duration_elem = listing_element.css_first('.duration, .omfattning, .period')
            if duration_elem:
                data['duration'] = duration_elem.text(strip=True)
            
            # Start date extraction
            start_elem = listing_element.css_first('.start-date, .startdatum, .start')
            if start_elem:
                data['start_date'] = start_elem.text(strip=True)
            
            # Posted date extraction
            posted_elem = listing_element.css_first('.posted-date, .published, .publicerad')
            if posted_elem:
                data['posted_at'] = posted_elem.text(strip=True)
            
            # Brief description from listing
            desc_elem = listing_element.css_first('.description, .summary, .beskrivning')
            if desc_elem:
                data['brief_description'] = desc_elem.text(strip=True)
            
            # Skills/tags extraction
            skill_elements = listing_element.css('.skill, .tag, .kompetens, .tech-stack span')
            if skill_elements:
                data['skills_preview'] = [elem.text(strip=True) for elem in skill_elements]
            
            # Check if this is through a broker
            if listing_element.css_first('.broker, .förmedlare'):
                data['broker'] = 'Brainville'
            
            return data if data.get('title') else None
            
        except Exception as e:
            logger.error(f"Error parsing listing element: {e}")
            return None
    
    async def fetch_job_details(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed information from job detail page."""
        try:
            response = await self.fetch_page(url)
            html = HTMLParser(response.text)
            
            data = {}
            
            # Full description
            desc_elem = html.css_first('.job-description, .assignment-description, .full-description, article.description')
            if desc_elem:
                # Get text content, preserving some structure
                desc_lines = []
                for elem in desc_elem.css('p, li, div'):
                    text = elem.text(strip=True)
                    if text:
                        desc_lines.append(text)
                data['description'] = '\n'.join(desc_lines)
            
            # Requirements section
            req_elem = html.css_first('.requirements, .krav, .qualifications')
            if req_elem:
                req_lines = []
                for elem in req_elem.css('p, li'):
                    text = elem.text(strip=True)
                    if text:
                        req_lines.append(text)
                data['requirements'] = '\n'.join(req_lines)
            
            # Additional metadata that might only be on detail page
            metadata_sections = html.css('.metadata, .assignment-info, .job-meta')
            for section in metadata_sections:
                # Look for key-value pairs
                for item in section.css('div, span, li'):
                    text = item.text(strip=True)
                    if ':' in text:
                        key, value = text.split(':', 1)
                        key = key.strip().lower()
                        value = value.strip()
                        
                        if 'omfattning' in key or 'duration' in key:
                            data['duration'] = value
                        elif 'start' in key:
                            data['start_date'] = value
                        elif 'ort' in key or 'location' in key or 'plats' in key:
                            data['location'] = value
                        elif 'kund' in key or 'company' in key or 'företag' in key:
                            data['company'] = value
                        elif 'roll' in key or 'role' in key:
                            data['role'] = value
                        elif 'takt' in key or 'procent' in key or 'extent' in key:
                            data['extent'] = value
                        elif 'längd' in key or 'length' in key:
                            data['duration'] = value
            
            # Contact information (might be useful for broker info)
            contact_elem = html.css_first('.contact, .kontakt, .consultant-info')
            if contact_elem:
                contact_text = contact_elem.text(strip=True)
                if 'brainville' in contact_text.lower():
                    data['broker'] = 'Brainville'
            
            # Skills from detail page (might be more comprehensive)
            skill_section = html.css_first('.skills, .kompetenser, .tech-requirements')
            if skill_section:
                skills = []
                for skill_elem in skill_section.css('span, li, .skill-tag'):
                    skill = skill_elem.text(strip=True)
                    if skill and len(skill) < 50:  # Avoid long text being marked as skill
                        skills.append(skill)
                if skills:
                    data['detailed_skills'] = skills
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching job details from {url}: {e}")
            return None
    
    def create_job_model(self, data: Dict[str, Any]) -> Optional[JobIn]:
        """Override to handle Brainville-specific data structure."""
        # Merge skills from preview and detailed page
        all_skills = []
        if data.get('skills_preview'):
            all_skills.extend(data['skills_preview'])
        if data.get('detailed_skills'):
            all_skills.extend(data['detailed_skills'])
        
        # Remove the temporary skill fields and add merged one
        if 'skills_preview' in data:
            del data['skills_preview']
        if 'detailed_skills' in data:
            del data['detailed_skills']
        
        # Combine brief and full description
        full_description = ''
        if data.get('brief_description'):
            full_description = data['brief_description']
        if data.get('description'):
            full_description = f"{full_description}\n\n{data['description']}" if full_description else data['description']
        
        data['description'] = full_description
        if 'brief_description' in data:
            del data['brief_description']
        
        # Extract skills from description and requirements if we didn't find explicit skills
        if not all_skills:
            all_skills = self.extract_skills(
                data.get('description', ''),
                data.get('requirements', ''),
                data.get('title', '')
            )
        
        data['skills'] = list(set(all_skills))  # Remove duplicates
        
        # Set broker if not already set
        if not data.get('broker'):
            data['broker'] = 'Brainville'
        
        # Parse duration to standard format
        if data.get('duration'):
            data['duration'] = self.parse_duration(data['duration'])
        
        return super().create_job_model(data)
    
    def parse_duration(self, duration_str: str) -> str:
        """Parse Swedish duration strings to standard format."""
        duration_lower = duration_str.lower()
        
        # Extract months
        months_match = re.search(r'(\d+)\s*(?:mån|month)', duration_lower)
        if months_match:
            months = int(months_match.group(1))
            return f"{months} months"
        
        # Extract weeks
        weeks_match = re.search(r'(\d+)\s*(?:veck|week)', duration_lower)
        if weeks_match:
            weeks = int(weeks_match.group(1))
            return f"{weeks} weeks"
        
        # Look for date ranges (e.g., "Jan 2024 - Jun 2024")
        if '-' in duration_str or '–' in duration_str:
            return duration_str
        
        # Look for percentage/extent and convert to assumed duration
        if '%' in duration_str or 'procent' in duration_lower:
            return f"{duration_str} (extent)"
        
        # Return as-is if we can't parse it
        return duration_str