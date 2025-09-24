#!/usr/bin/env python3
"""
Run all configured scrapers based on config/scraper_config.yaml
"""

import asyncio
import json
import logging
import yaml
from datetime import datetime
import sys
import os
from typing import List, Dict, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scrapers import EworkScraper, BrainvilleScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config() -> Dict[str, Any]:
    """Load scraper configuration from YAML file."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config', 'scraper_config.yaml'
    )
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


async def run_ework_scraper(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Run eWork scraper with configuration."""
    ework_config = config['scrapers']['ework']
    
    if not ework_config.get('enabled', False):
        logger.info("eWork scraper is disabled in configuration")
        return []
    
    logger.info("Starting eWork scraper...")
    logger.info(f"Countries: {ework_config.get('countries', ['SE'])}")
    logger.info(f"Languages: {ework_config.get('languages', ['SV', 'EN'])}")
    
    async with EworkScraper(
        countries=ework_config.get('countries', ['SE']),
        languages=ework_config.get('languages', ['SV', 'EN'])
    ) as scraper:
        scraper.max_pages = ework_config.get('max_pages', 5)
        listings = await scraper.scrape_listings()
        
    logger.info(f"eWork: Found {len(listings)} jobs")
    return listings


async def run_brainville_scraper(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Run Brainville scraper with configuration."""
    brainville_config = config['scrapers']['brainville']
    
    if not brainville_config.get('enabled', False):
        logger.info("Brainville scraper is disabled in configuration")
        return []
    
    logger.info("Starting Brainville scraper...")
    
    async with BrainvilleScraper() as scraper:
        scraper.max_pages = brainville_config.get('max_pages', 10)
        listings = await scraper.scrape_listings()
        
    logger.info(f"Brainville: Found {len(listings)} jobs")
    return listings


async def main():
    """Main function to run all scrapers."""
    logger.info("=" * 60)
    logger.info("Starting Senior Consultant Job Scraping")
    logger.info("=" * 60)
    
    # Load configuration
    config = load_config()
    
    # Run all enabled scrapers
    all_listings = []
    
    # Run scrapers in parallel for efficiency
    tasks = []
    
    if config['scrapers']['ework'].get('enabled', False):
        tasks.append(run_ework_scraper(config))
    
    if config['scrapers']['brainville'].get('enabled', False):
        tasks.append(run_brainville_scraper(config))
    
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Scraper failed: {result}")
            elif result:
                all_listings.extend(result)
    
    # Summary statistics
    logger.info("\n" + "=" * 60)
    logger.info("SCRAPING SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total jobs found: {len(all_listings)}")
    
    if all_listings:
        # Count by source
        sources = {}
        for job in all_listings:
            source = job.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        
        logger.info("\nJobs by source:")
        for source, count in sources.items():
            logger.info(f"  {source}: {count}")
        
        # Count by country
        countries = {}
        for job in all_listings:
            country = job.get('location_country', 'Unknown')
            countries[country] = countries.get(country, 0) + 1
        
        logger.info("\nJobs by country:")
        for country, count in sorted(countries.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {country}: {count}")
        
        # Count by seniority
        seniorities = {}
        for job in all_listings:
            seniority = job.get('seniority', 'Unknown')
            seniorities[seniority] = seniorities.get(seniority, 0) + 1
        
        logger.info("\nJobs by seniority:")
        for seniority, count in sorted(seniorities.items()):
            logger.info(f"  {seniority}: {count}")
        
        # Save to JSON file with timestamp
        output_file = f"all_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_listings, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"\n💾 All {len(all_listings)} jobs saved to {output_file}")
        
        # Show sample jobs
        logger.info("\n📋 Sample jobs (first 3):")
        for i, job in enumerate(all_listings[:3], 1):
            logger.info(f"\n--- Job {i} ---")
            logger.info(f"Source: {job.get('source', 'N/A')}")
            logger.info(f"Title: {job.get('title', 'N/A')}")
            logger.info(f"Company: {job.get('company', 'N/A')}")
            logger.info(f"Location: {job.get('location_city', 'N/A')}, {job.get('location_country', 'N/A')}")
            logger.info(f"Seniority: {job.get('seniority', 'N/A')}")
            logger.info(f"URL: {job.get('url', 'N/A')}")
    
    else:
        logger.warning("No jobs found from any scraper")
    
    logger.info("\n✅ Scraping complete!")


if __name__ == "__main__":
    asyncio.run(main())