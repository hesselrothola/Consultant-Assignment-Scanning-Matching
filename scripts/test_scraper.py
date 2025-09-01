#!/usr/bin/env python3
"""
Test script for web scrapers.
Run this to test scraping functionality without affecting the database.
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import json
import argparse

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.scrapers import BrainvilleScraper
from app.config import settings, SCRAPER_CONFIGS


async def test_brainville():
    """Test Brainville scraper."""
    print("\n" + "="*60)
    print("Testing Brainville Scraper")
    print("="*60)
    
    async with BrainvilleScraper() as scraper:
        # Override max_pages for testing
        scraper.max_pages = 2  # Only scrape first 2 pages for testing
        
        print(f"Base URL: {scraper.base_url}")
        print(f"Source: {scraper.source_name}")
        print(f"Rate limit: {scraper.rate_limit_delay}s between requests")
        print(f"Max pages: {scraper.max_pages}")
        print()
        
        try:
            jobs = await scraper.scrape()
            
            print(f"\n✅ Successfully scraped {len(jobs)} jobs")
            
            if jobs:
                print("\nFirst 3 jobs:")
                print("-" * 40)
                
                for i, job in enumerate(jobs[:3], 1):
                    print(f"\n{i}. {job.title}")
                    print(f"   Company: {job.company or 'N/A'}")
                    print(f"   Location: {job.location_city or 'N/A'}, {job.location_country}")
                    print(f"   Duration: {job.duration or 'N/A'}")
                    print(f"   Skills: {', '.join(job.skills[:5]) if job.skills else 'N/A'}")
                    print(f"   Languages: {', '.join(job.languages) if job.languages else 'N/A'}")
                    print(f"   URL: {job.url}")
                    
                    if job.description:
                        desc_preview = job.description[:150] + "..." if len(job.description) > 150 else job.description
                        print(f"   Description: {desc_preview}")
                
                # Save to file for inspection
                output_file = f"scraped_jobs_brainville_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(
                        [job.dict() for job in jobs],
                        f,
                        indent=2,
                        ensure_ascii=False,
                        default=str
                    )
                print(f"\n💾 Full results saved to: {output_file}")
                
                # Statistics
                print("\nStatistics:")
                print(f"  Total jobs: {len(jobs)}")
                print(f"  Jobs with skills: {sum(1 for j in jobs if j.skills)}")
                print(f"  Jobs with company: {sum(1 for j in jobs if j.company)}")
                print(f"  Jobs with duration: {sum(1 for j in jobs if j.duration)}")
                print(f"  Jobs with description: {sum(1 for j in jobs if j.description)}")
                
                # Top skills
                all_skills = []
                for job in jobs:
                    if job.skills:
                        all_skills.extend(job.skills)
                
                if all_skills:
                    from collections import Counter
                    skill_counts = Counter(all_skills)
                    print("\nTop 10 skills found:")
                    for skill, count in skill_counts.most_common(10):
                        print(f"  {skill}: {count}")
                
            else:
                print("⚠️  No jobs found. This could mean:")
                print("  - The website structure has changed")
                print("  - The site is blocking scrapers")
                print("  - Network issues")
                print("  - No current job listings")
                
        except Exception as e:
            print(f"\n❌ Error during scraping: {e}")
            import traceback
            traceback.print_exc()


async def test_scraper_connectivity():
    """Test basic connectivity to scraper targets."""
    print("\n" + "="*60)
    print("Testing Scraper Connectivity")
    print("="*60)
    
    import httpx
    
    sites = [
        ("Brainville", "https://www.brainville.com"),
        ("Cinode", "https://www.cinode.com"),
        ("LinkedIn", "https://www.linkedin.com"),
        ("eWork", "https://www.eworkgroup.com"),
        ("Onsiter", "https://www.onsiter.com"),
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, url in sites:
            try:
                response = await client.get(url, follow_redirects=True)
                status = "✅" if response.status_code == 200 else f"⚠️  Status: {response.status_code}"
                print(f"{name:15} {url:35} {status}")
            except Exception as e:
                print(f"{name:15} {url:35} ❌ Error: {str(e)[:30]}")


async def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test web scrapers")
    parser.add_argument(
        "--scraper",
        choices=["brainville", "all", "connectivity"],
        default="connectivity",
        help="Which scraper to test"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    print(f"\n🔍 Consultant Assignment Scraper Test")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.scraper == "connectivity":
        await test_scraper_connectivity()
    elif args.scraper == "brainville":
        await test_brainville()
    elif args.scraper == "all":
        await test_scraper_connectivity()
        await test_brainville()
        # Add other scrapers as they're implemented
    
    print("\n✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(main())