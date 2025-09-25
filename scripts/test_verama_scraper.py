#!/usr/bin/env python3
"""
Test script for eWork scraper.
"""

import asyncio
import json
import logging
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scrapers.ework import EworkScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_ework_scraper():
    """Test the eWork scraper."""
    
    logger.info("Starting eWork scraper test...")
    
    # Configure to only get Swedish assignments (or Nordic if you have consultants there)
    # Options: ['SE'] for Sweden only
    #          ['SE', 'NO', 'DK', 'FI'] for all Nordic countries
    #          ['SE', 'NO'] for Sweden and Norway only, etc.
    countries_filter = ['SE']  # Change this to match where your consultants are
    
    try:
        async with EworkScraper(countries=countries_filter) as scraper:
            logger.info(f"Target URL: {scraper.job_listings_url}")
            logger.info(f"Country filter: {countries_filter}")
            logger.info(f"Languages: Swedish/English")
            logger.info(f"Seniority: Senior/Expert level only")
            
            # Scrape listings
            listings = await scraper.scrape_listings()
        
        if listings:
            logger.info(f"\n✅ Successfully scraped {len(listings)} job listings from eWork!")
            
            # Display first 5 jobs
            logger.info("\n📋 Sample jobs (first 5):")
            for i, job in enumerate(listings[:5], 1):
                logger.info(f"\n--- Job {i} ---")
                logger.info(f"Title: {job.get('title', 'N/A')}")
                logger.info(f"Company: {job.get('company', 'N/A')}")
                logger.info(f"Location: {job.get('location_city', 'N/A')}, {job.get('location_country', 'N/A')}")
                logger.info(f"Seniority: {job.get('seniority', 'N/A')}")
                logger.info(f"Role: {job.get('role', 'N/A')}")
                logger.info(f"Remote: {job.get('onsite_mode', 'N/A')}")
                logger.info(f"Languages: {', '.join(job.get('languages', []))}")
                logger.info(f"Skills: {', '.join(job.get('skills', [])[:5])}...")
                logger.info(f"URL: {job.get('url', 'N/A')}")
            
            # Save to JSON file
            output_file = f"ework_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(listings, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"\n💾 All {len(listings)} jobs saved to {output_file}")
            
            # Statistics
            logger.info("\n📊 Statistics:")
            
            # Count by seniority
            seniorities = {}
            for job in listings:
                seniority = job.get('seniority', 'Unknown')
                seniorities[seniority] = seniorities.get(seniority, 0) + 1
            logger.info(f"By seniority: {seniorities}")
            
            # Count by location
            locations = {}
            for job in listings:
                location = job.get('location_city', 'Unknown')
                locations[location] = locations.get(location, 0) + 1
            logger.info(f"Top locations: {dict(sorted(locations.items(), key=lambda x: x[1], reverse=True)[:5])}")
            
            # Count by company
            companies = {}
            for job in listings:
                company = job.get('company', 'Unknown')
                companies[company] = companies.get(company, 0) + 1
            logger.info(f"Top companies: {dict(sorted(companies.items(), key=lambda x: x[1], reverse=True)[:5])}")
            
            # Count remote jobs
            remote_count = sum(1 for job in listings if job.get('onsite_mode') == 'remote')
            logger.info(f"Remote jobs: {remote_count}/{len(listings)}")
            
        else:
            logger.warning("❌ No listings found. The scraper may need authentication or the site structure may have changed.")
            
    except Exception as e:
        logger.error(f"❌ Error during scraping: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_ework_scraper())