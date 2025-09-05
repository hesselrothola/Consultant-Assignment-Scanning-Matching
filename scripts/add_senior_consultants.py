#!/usr/bin/env python3
"""
Script to add high-level management and data specialist consultants to the system.
Tailored for senior profiles typical in Swedish consulting market.
"""

import asyncio
import os
import sys
from datetime import date
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.models import ConsultantIn
from app.repo import DatabaseRepository
from app.embeddings import EmbeddingService


# High-level consultant profiles template
SENIOR_CONSULTANTS = [
    {
        "name": "Magnus Andersson",
        "role": "Enterprise Architect / Business Architect",
        "seniority": "senior",
        "skills": [
            "Digital Strategy", "Enterprise Architecture", "Solution Architecture",
            "Change Management", "Agile Transformation", "Business Development",
            "Cloud Computing", "ERP Implementation", "Platform Modernization",
            "R&D Leadership", "Program Management", "Digital Transformation"
        ],
        "languages": ["Swedish", "English", "Danish", "Norwegian"],
        "location_city": "Stockholm",
        "location_country": "Sweden",
        "onsite_mode": "hybrid",
        "notes": "20+ years experience. Former CTO/Interim CTO. Executive MBA. Expertise in enterprise transformation, cloud strategy, and agile innovation. Industries: Healthcare, Finance, Agriculture Tech."
    },
    {
        "name": "Example Data Architect", 
        "role": "Data Architect",
        "seniority": "senior",
        "skills": [
            "Azure Data Platform", "Databricks", "Data Lake", "Data Warehouse",
            "ETL/ELT", "Data Governance", "Python", "SQL", "Power BI",
            "Solution Architecture", "Team Leadership"
        ],
        "languages": ["Swedish", "English"],
        "location_city": "Stockholm",
        "location_country": "Sweden",
        "onsite_mode": "hybrid",
        "notes": "12+ years experience. Certified Azure Solution Architect."
    },
    {
        "name": "Example BI Lead",
        "role": "BI Consultant", 
        "seniority": "senior",
        "skills": [
            "Power BI", "Tableau", "Qlik Sense", "Data Modeling",
            "Business Intelligence", "Analytics Strategy", "KPI Development",
            "SQL", "DAX", "Project Management"
        ],
        "languages": ["Swedish", "English"],
        "location_city": "Gothenburg",
        "location_country": "Sweden",
        "onsite_mode": "remote",
        "notes": "10+ years BI experience. Specialized in financial reporting."
    },
    {
        "name": "Example Interim CTO",
        "role": "Interim CTO",
        "seniority": "senior",
        "skills": [
            "Technology Strategy", "Digital Transformation", "Cloud Migration",
            "Vendor Management", "Budget Management", "Team Building",
            "Agile Transformation", "IT Governance", "Cyber Security"
        ],
        "languages": ["Swedish", "English", "German"],
        "location_city": "Stockholm",
        "location_country": "Sweden",
        "onsite_mode": "onsite",  # C-level often needs presence
        "notes": "20+ years experience. Interim CTO for multiple scale-ups."
    },
    {
        "name": "Example Program Manager",
        "role": "Program Manager",
        "seniority": "senior", 
        "skills": [
            "Program Management", "Portfolio Management", "SAFe", "Prince2",
            "Risk Management", "Stakeholder Management", "Business Analysis",
            "Digital Transformation", "Change Management"
        ],
        "languages": ["Swedish", "English"],
        "location_city": "Malmö",
        "location_country": "Sweden",
        "onsite_mode": "hybrid",
        "notes": "15+ years. Specialized in large-scale public sector transformations."
    }
]


async def add_senior_consultants():
    """Add high-level consultant profiles to the database."""
    
    # Initialize services
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/consultant_matching")
    
    db_repo = DatabaseRepository(db_url)
    await db_repo.init()
    
    embedding_service = EmbeddingService(
        backend=os.getenv("EMBEDDING_BACKEND", "openai"),
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    try:
        for consultant_data in SENIOR_CONSULTANTS:
            # Create consultant model
            consultant = ConsultantIn(
                name=consultant_data["name"],
                role=consultant_data["role"],
                seniority=consultant_data["seniority"],
                skills=consultant_data["skills"],
                languages=consultant_data["languages"],
                location_city=consultant_data["location_city"],
                location_country=consultant_data["location_country"],
                onsite_mode=consultant_data["onsite_mode"],
                availability_from=date.today(),  # Available immediately
                notes=consultant_data["notes"],
                active=True
            )
            
            # Insert into database
            db_consultant = await db_repo.upsert_consultant(consultant)
            print(f"✅ Added: {consultant.name} - {consultant.role}")
            
            # Generate embedding
            text = embedding_service.prepare_consultant_text(consultant.dict())
            embedding = await embedding_service.create_embedding(text)
            
            if embedding:
                await db_repo.store_consultant_embedding(
                    db_consultant.consultant_id,
                    embedding
                )
                print(f"   📊 Generated embedding for {consultant.name}")
        
        print("\n✨ Successfully added all senior consultants!")
        
        # Show summary
        total = await db_repo.get_consultants(active_only=True, limit=100)
        print(f"\n📈 Total active consultants in system: {len(total)}")
        
        # Count by seniority
        senior_count = sum(1 for c in total if c.seniority == 'senior')
        print(f"   - Senior level: {senior_count}")
        
    finally:
        await db_repo.close()


async def match_senior_profiles():
    """
    Test matching for senior profiles to see what kind of assignments match.
    """
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/consultant_matching")
    
    db_repo = DatabaseRepository(db_url)
    await db_repo.init()
    
    try:
        # Get recent jobs
        jobs = await db_repo.get_jobs(limit=20)
        consultants = await db_repo.get_consultants(active_only=True, limit=10)
        
        print("\n🔍 Testing matches for senior consultants:\n")
        
        for consultant in consultants:
            if consultant.seniority == 'senior':
                print(f"\n{consultant.name} ({consultant.role}):")
                
                # Find matching jobs
                matches = []
                for job in jobs:
                    # Simple keyword matching for demonstration
                    job_text = f"{job.title} {job.description or ''}".lower()
                    
                    # Check for senior indicators
                    senior_keywords = ['senior', 'lead', 'chef', 'manager', 'architect', 'strategic']
                    if any(keyword in job_text for keyword in senior_keywords):
                        matches.append(job)
                
                if matches:
                    for match in matches[:3]:  # Top 3 matches
                        print(f"   ✓ {match.title} at {match.location_city}")
                else:
                    print("   ❌ No suitable senior-level matches found")
                    
    finally:
        await db_repo.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "match":
        # Test matching
        asyncio.run(match_senior_profiles())
    else:
        # Add consultants
        asyncio.run(add_senior_consultants())