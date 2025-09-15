#!/usr/bin/env python3
"""
Configure scanning parameters based on existing consultant profiles.
This ensures we only scan for jobs that match our consultants' skills.
Uses AI to understand and expand skill relationships.
"""

import os
import sys
import asyncio
from typing import List, Set, Dict
from collections import Counter
import openai

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.repo import DatabaseRepository
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def analyze_consultant_profiles():
    """Analyze consultant profiles to extract skills and roles."""
    db = DatabaseRepository(db_url=settings.database_url)
    await db.init()
    
    try:
        # Get all active consultants
        consultants = await db.get_consultants(active_only=True, limit=1000)
        
        if not consultants:
            logger.warning("No active consultants found in database")
            return None
            
        logger.info(f"Found {len(consultants)} active consultants")
        
        # Aggregate skills across all consultants
        all_skills = []
        all_roles = []
        all_languages = []
        all_locations = []
        seniority_levels = []
        
        for consultant in consultants:
            if consultant.skills:
                all_skills.extend(consultant.skills)
            
            if consultant.role:
                all_roles.append(consultant.role)
            
            if consultant.languages:
                all_languages.extend(consultant.languages)
            
            if consultant.location_city:
                all_locations.append(consultant.location_city)
                
            if consultant.seniority:
                seniority_levels.append(consultant.seniority)
        
        # Get most common skills (top 30)
        skill_counts = Counter(all_skills)
        top_skills = [skill for skill, _ in skill_counts.most_common(30)]
        
        # Get unique roles
        unique_roles = list(set(all_roles))
        
        # Get unique languages
        unique_languages = list(set(all_languages))
        
        # Get unique locations  
        unique_locations = list(set(all_locations))
        
        # Get unique seniority levels
        unique_seniority = list(set(seniority_levels))
        
        logger.info(f"Extracted from consultants:")
        logger.info(f"  - {len(top_skills)} top skills: {', '.join(top_skills[:10])}...")
        logger.info(f"  - {len(unique_roles)} roles: {', '.join(unique_roles[:5])}...")
        logger.info(f"  - {len(unique_languages)} languages: {', '.join(unique_languages)}")
        logger.info(f"  - {len(unique_locations)} locations: {', '.join(unique_locations[:5])}...")
        logger.info(f"  - Seniority levels: {', '.join(unique_seniority)}")
        
        return {
            'skills': top_skills,
            'roles': unique_roles,
            'languages': unique_languages,
            'locations': unique_locations,
            'seniority_levels': unique_seniority
        }
        
    finally:
        await db.close()


async def expand_skills_with_ai(skills: List[str]) -> Dict[str, List[str]]:
    """Use AI to understand and expand skill relationships."""
    
    if not settings.openai_api_key:
        logger.warning("OpenAI API key not configured, skipping AI skill expansion")
        return {"original": skills, "expanded": [], "categories": {}}
    
    openai.api_key = settings.openai_api_key
    
    prompt = f"""Analyze these technical skills from consultant profiles and provide:
1. Related skills that employers might search for
2. Alternative names/versions (e.g., JS for JavaScript)
3. Skill categories (e.g., Frontend, Backend, Cloud, Database)
4. Complementary skills often required together

Skills to analyze:
{', '.join(skills[:30])}

Return a JSON with:
- expanded_skills: list of additional related skills to search for
- skill_aliases: dict mapping skills to alternative names
- categories: dict mapping categories to skills
- skill_combinations: list of skill groups that often go together

Focus on Swedish IT consulting market."""

    try:
        client = openai.OpenAI(api_key=settings.openai_api_key)
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert in IT skills and the Swedish consulting market."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        
        logger.info("AI skill expansion completed:")
        logger.info(f"  - Added {len(result.get('expanded_skills', []))} related skills")
        logger.info(f"  - Found {len(result.get('skill_aliases', {}))} skill aliases")
        logger.info(f"  - Categorized into {len(result.get('categories', {}))} groups")
        
        return result
        
    except Exception as e:
        logger.error(f"AI skill expansion failed: {e}")
        return {"original": skills, "expanded": [], "categories": {}}


async def analyze_skill_demand():
    """Analyze which skills are most in-demand based on recent job postings."""
    db = DatabaseRepository(db_url=settings.database_url)
    await db.init()
    
    try:
        # Get skills from recent jobs
        async with db.pool.acquire() as conn:
            recent_jobs = await conn.fetch("""
                SELECT skills, posted_at
                FROM jobs
                WHERE posted_at > NOW() - INTERVAL '30 days'
                AND skills IS NOT NULL
            """)
        
        skill_frequency = Counter()
        for job in recent_jobs:
            if job['skills']:
                skill_frequency.update(job['skills'])
        
        top_demanded = skill_frequency.most_common(20)
        logger.info("Top in-demand skills from recent jobs:")
        for skill, count in top_demanded:
            logger.info(f"  - {skill}: {count} jobs")
            
        return [skill for skill, _ in top_demanded]
        
    finally:
        await db.close()


async def create_scanning_config(profile_data):
    """Create or update scanning configuration based on consultant profiles."""
    db = DatabaseRepository(db_url=settings.database_url)
    await db.init()
    
    try:
        config_name = "Consultant-Based Auto Configuration"
        
        # Check if config already exists
        async with db.pool.acquire() as conn:
            existing = await conn.fetch(
                "SELECT config_id FROM scanning_configs WHERE config_name = $1",
                config_name
            )
        
        config_data = {
            'config_name': config_name,
            'description': 'Automatically generated from consultant profiles',
            'target_skills': profile_data['skills'],
            'target_roles': profile_data['roles'],
            'target_locations': profile_data['locations'],
            'languages': profile_data['languages'],
            'is_active': True
        }
        
        if existing:
            # Update existing config
            async with db.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE scanning_configs 
                    SET target_skills = $2,
                        target_roles = $3,
                        target_locations = $4,
                        languages = $5,
                        updated_at = now()
                    WHERE config_name = $1
                """, config_name, 
                    config_data['target_skills'],
                    config_data['target_roles'], 
                    config_data['target_locations'],
                    config_data['languages'])
            logger.info(f"Updated existing scanning configuration")
        else:
            # Create new config
            async with db.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO scanning_configs 
                    (config_name, description, target_skills, target_roles, 
                     target_locations, languages, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, config_data['config_name'],
                    config_data['description'],
                    config_data['target_skills'],
                    config_data['target_roles'],
                    config_data['target_locations'],
                    config_data['languages'],
                    config_data['is_active'])
            logger.info(f"Created new scanning configuration")
            
        # Configure source-specific settings for eWork
        await configure_ework_settings(db, profile_data)
        
    finally:
        await db.close()


async def configure_ework_settings(db, profile_data):
    """Configure eWork-specific settings based on consultant locations."""
    # Determine which countries to scan based on consultant locations
    countries_to_scan = ['SE']  # Default to Sweden
    
    # Check if we have consultants in other Nordic countries
    nordic_cities = {
        'Oslo': 'NO',
        'Bergen': 'NO', 
        'Copenhagen': 'DK',
        'København': 'DK',
        'Helsinki': 'FI',
        'Espoo': 'FI'
    }
    
    for city in profile_data['locations']:
        if city in nordic_cities:
            country = nordic_cities[city]
            if country not in countries_to_scan:
                countries_to_scan.append(country)
    
    logger.info(f"eWork will scan countries: {countries_to_scan}")
    
    # Update eWork configuration in config file would go here
    # For now, just log the recommendation
    logger.info("Recommendation: Update app/config.py SCRAPER_CONFIGS['ework']['countries'] to:")
    logger.info(f"  countries: {countries_to_scan}")


async def main():
    """Main function to configure scanning from consultant profiles."""
    logger.info("="*60)
    logger.info("AI-POWERED SCANNING CONFIGURATION")
    logger.info("="*60)
    
    # Step 1: Analyze existing consultants
    logger.info("\n[1/4] Analyzing consultant profiles...")
    profile_data = await analyze_consultant_profiles()
    
    if not profile_data:
        logger.error("No consultant data to work with")
        return
    
    # Step 2: Use AI to expand and understand skills
    logger.info("\n[2/4] Using AI to expand skill understanding...")
    ai_expansion = await expand_skills_with_ai(profile_data['skills'])
    
    # Combine original and AI-expanded skills
    if ai_expansion.get('expanded_skills'):
        all_skills = profile_data['skills'] + ai_expansion['expanded_skills']
        # Remove duplicates while preserving order
        profile_data['skills'] = list(dict.fromkeys(all_skills))
        logger.info(f"Expanded skills from {len(profile_data['skills'])} to {len(all_skills)}")
    
    # Step 3: Analyze market demand (optional)
    logger.info("\n[3/4] Analyzing market demand...")
    try:
        in_demand_skills = await analyze_skill_demand()
        # Prioritize skills that are both in consultant profiles AND in demand
        common_skills = set(profile_data['skills']) & set(in_demand_skills)
        if common_skills:
            logger.info(f"Found {len(common_skills)} skills that match both consultants and market demand")
    except Exception as e:
        logger.warning(f"Could not analyze market demand: {e}")
    
    # Step 4: Create scanning configuration
    logger.info("\n[4/4] Creating scanning configuration...")
    await create_scanning_config(profile_data)
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("✅ SCANNING CONFIGURATION COMPLETE!")
    logger.info("="*60)
    logger.info("\nThe system will now intelligently scan for jobs matching:")
    logger.info(f"\n📋 SKILLS ({len(profile_data['skills'])} total):")
    logger.info(f"   Core: {', '.join(profile_data['skills'][:10])}...")
    
    if ai_expansion.get('categories'):
        logger.info(f"\n📊 SKILL CATEGORIES:")
        for category, skills in list(ai_expansion['categories'].items())[:5]:
            logger.info(f"   {category}: {', '.join(skills[:5])}")
    
    logger.info(f"\n👔 ROLES: {', '.join(profile_data['roles'][:5])}...")
    logger.info(f"📍 LOCATIONS: {', '.join(profile_data['locations'][:5])}...")
    logger.info(f"🗣️ LANGUAGES: {', '.join(profile_data['languages'])}")
    
    logger.info("\n🚀 Next Steps:")
    logger.info("   1. Configuration saved to database")
    logger.info("   2. Will be used in next scheduled scan (daily at 07:00)")
    logger.info("   3. You can trigger immediate scan at /consultant/scanner")
    logger.info("\n💡 The AI has enhanced skill matching to find more relevant jobs!")


if __name__ == "__main__":
    asyncio.run(main())