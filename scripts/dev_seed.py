#!/usr/bin/env python3
"""
Development seed script to load consultants from CSV and create embeddings.
"""

import asyncio
import csv
import os
import sys
from pathlib import Path
from datetime import date, datetime
from typing import List, Dict, Any

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.models import ConsultantIn, JobIn, CompanyIn, BrokerIn, OnsiteMode
from app.repo import DatabaseRepository
from app.embeddings import EmbeddingService


async def load_consultants_from_csv(file_path: str) -> List[ConsultantIn]:
    """Load consultants from CSV file."""
    consultants = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Parse skills (assume comma-separated)
            skills = []
            if row.get('skills'):
                skills = [s.strip() for s in row['skills'].split(',')]
            
            # Parse languages (assume comma-separated)
            languages = []
            if row.get('languages'):
                languages = [l.strip() for l in row['languages'].split(',')]
            
            # Parse availability date
            availability_from = None
            if row.get('availability_from') or row.get('availability_date'):
                try:
                    date_str = row.get('availability_from') or row.get('availability_date')
                    availability_from = datetime.strptime(date_str, '%Y-%m-%d').date()
                except:
                    pass
            
            # Parse onsite mode
            onsite_mode = None
            if row.get('onsite_mode'):
                mode = row['onsite_mode'].lower()
                if mode in ['remote', 'onsite', 'hybrid']:
                    onsite_mode = OnsiteMode(mode)
            
            consultant = ConsultantIn(
                name=row['name'],
                role=row.get('role'),
                seniority=row.get('seniority'),
                skills=skills,
                languages=languages,
                location_city=row.get('location_city') or row.get('location'),
                location_country=row.get('location_country', 'Sweden'),
                onsite_mode=onsite_mode,
                availability_from=availability_from,
                notes=row.get('notes') or row.get('cv_text', ''),
                profile_url=row.get('profile_url') or row.get('linkedin_url'),
                active=row.get('active', 'true').lower() == 'true'
            )
            
            consultants.append(consultant)
    
    return consultants


async def create_sample_consultants() -> List[ConsultantIn]:
    """Create sample consultants if no CSV provided."""
    return [
        ConsultantIn(
            name="Anna Andersson",
            role="Full Stack Developer",
            seniority="Senior",
            skills=["Python", "React", "PostgreSQL", "Docker", "AWS"],
            languages=["Swedish", "English"],
            location_city="Stockholm",
            location_country="Sweden",
            onsite_mode=OnsiteMode.HYBRID,
            availability_from=date(2024, 1, 15),
            notes="Experienced full stack developer with 8 years in web development...",
            active=True
        ),
        ConsultantIn(
            name="Erik Eriksson",
            role="DevOps Engineer",
            seniority="Senior",
            skills=["Kubernetes", "Terraform", "Jenkins", "AWS", "Python"],
            languages=["Swedish", "English"],
            location_city="Göteborg",
            location_country="Sweden",
            onsite_mode=OnsiteMode.REMOTE,
            availability_from=date(2024, 2, 1),
            notes="DevOps specialist focused on cloud infrastructure and CI/CD...",
            active=True
        ),
        ConsultantIn(
            name="Maria Nilsson",
            role="Data Scientist",
            seniority="Mid",
            skills=["Python", "Machine Learning", "TensorFlow", "SQL", "Spark"],
            languages=["Swedish", "English", "German"],
            location_city="Malmö",
            location_country="Sweden",
            onsite_mode=OnsiteMode.HYBRID,
            availability_from=date(2024, 1, 1),
            notes="Data scientist with expertise in machine learning and big data...",
            active=True
        ),
        ConsultantIn(
            name="Johan Johansson",
            role="Frontend Developer",
            seniority="Mid",
            skills=["React", "TypeScript", "CSS", "Next.js", "GraphQL"],
            languages=["Swedish", "English"],
            location_city="Stockholm",
            location_country="Sweden",
            onsite_mode=OnsiteMode.ONSITE,
            availability_from=date(2024, 1, 20),
            notes="Frontend specialist with focus on modern React applications...",
            active=True
        ),
        ConsultantIn(
            name="Sara Svensson",
            role="Backend Developer",
            seniority="Senior",
            skills=["Java", "Spring", "PostgreSQL", "Microservices", "Docker"],
            languages=["Swedish", "English"],
            location_city="Uppsala",
            location_country="Sweden",
            onsite_mode=OnsiteMode.HYBRID,
            availability_from=date(2024, 2, 15),
            notes="Backend developer specializing in Java and microservices...",
            active=True
        )
    ]


async def create_sample_jobs(db: DatabaseRepository):
    """Create sample jobs for testing."""
    
    # Create sample companies
    tech_company = await db.upsert_company(CompanyIn(
        normalized_name="techcorp ab",
        aliases=["TechCorp AB", "TechCorp"]
    ))
    
    cloud_company = await db.upsert_company(CompanyIn(
        normalized_name="cloudsolutions ab",
        aliases=["CloudSolutions AB", "CloudSolutions"]
    ))
    
    web_company = await db.upsert_company(CompanyIn(
        normalized_name="webdesign ab",
        aliases=["WebDesign AB", "WebDesign"]
    ))
    
    # Create sample broker
    broker = await db.upsert_broker(BrokerIn(
        name="TechRecruit",
        portal_url="https://techrecruit.se"
    ))
    
    sample_jobs = [
        JobIn(
            job_uid="job-001",
            source="sample",
            title="Senior Python Developer",
            role="Backend Developer",
            seniority="Senior",
            description="We are looking for a senior Python developer to join our team...",
            skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
            languages=["Swedish", "English"],
            location_city="Stockholm",
            location_country="Sweden",
            onsite_mode=OnsiteMode.HYBRID,
            duration="6 months",
            company_id=tech_company.company_id,
            broker_id=broker.broker_id,
            url="https://example.com/job-001"
        ),
        JobIn(
            job_uid="job-002",
            source="sample",
            title="DevOps Engineer",
            role="DevOps Engineer",
            seniority="Mid",
            description="DevOps engineer needed for cloud infrastructure projects...",
            skills=["Kubernetes", "AWS", "Terraform", "Jenkins"],
            languages=["English"],
            location_city="Göteborg",
            location_country="Sweden",
            onsite_mode=OnsiteMode.REMOTE,
            duration="12 months",
            company_id=cloud_company.company_id,
            url="https://example.com/job-002"
        ),
        JobIn(
            job_uid="job-003",
            source="sample",
            title="Frontend React Developer",
            role="Frontend Developer",
            seniority="Mid",
            description="Frontend developer with React expertise needed...",
            skills=["React", "TypeScript", "CSS", "GraphQL"],
            languages=["Swedish", "English"],
            location_city="Stockholm",
            location_country="Sweden",
            onsite_mode=OnsiteMode.ONSITE,
            duration="9 months",
            company_id=web_company.company_id,
            url="https://example.com/job-003"
        )
    ]
    
    for job in sample_jobs:
        await db.upsert_job(job)
    
    print(f"Created {len(sample_jobs)} sample jobs")


async def main():
    """Main function to seed the database."""
    
    # Get database URL from environment or use default
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/consultant_matching")
    
    # Initialize services
    db = DatabaseRepository(db_url)
    await db.init()
    
    embeddings = EmbeddingService()
    
    try:
        # Check if CSV file is provided
        csv_file = None
        if len(sys.argv) > 1:
            csv_file = sys.argv[1]
            if not os.path.exists(csv_file):
                print(f"CSV file not found: {csv_file}")
                csv_file = None
        
        # Load consultants
        if csv_file:
            print(f"Loading consultants from {csv_file}...")
            consultants = await load_consultants_from_csv(csv_file)
        else:
            print("No CSV file provided, creating sample consultants...")
            consultants = await create_sample_consultants()
        
        print(f"Loaded {len(consultants)} consultants")
        
        # Save consultants and create embeddings
        for i, consultant in enumerate(consultants, 1):
            print(f"Processing consultant {i}/{len(consultants)}: {consultant.name}")
            
            # Save consultant
            saved_consultant = await db.upsert_consultant(consultant)
            
            # Create embedding
            consultant_text = embeddings.prepare_consultant_text(consultant.model_dump())
            embedding = await embeddings.create_embedding(consultant_text)
            
            # Store embedding
            await db.store_consultant_embedding(
                saved_consultant.consultant_id,
                embedding
            )
        
        print(f"Successfully created {len(consultants)} consultants with embeddings")
        
        # Create sample jobs
        print("\nCreating sample jobs...")
        await create_sample_jobs(db)
        
        # Create embeddings for jobs
        jobs = await db.get_jobs(limit=100)
        for job in jobs:
            job_text = embeddings.prepare_job_text(job.model_dump())
            embedding = await embeddings.create_embedding(job_text)
            await db.store_job_embedding(job.job_id, embedding)
        
        print(f"Created embeddings for {len(jobs)} jobs")
        
        print("\n✅ Database seeding completed successfully!")
        print("\nYou can now:")
        print("1. Start the API: docker-compose up")
        print("2. Access the API at: http://localhost:8001")
        print("3. View API docs at: http://localhost:8001/docs")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    finally:
        await db.close()


if __name__ == "__main__":
    print("Consultant Assignment Matching - Development Seed Script")
    print("=" * 50)
    
    # Check for OpenAI API key if using OpenAI backend
    if os.getenv("EMBEDDING_BACKEND", "openai").lower() == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            print("Warning: OPENAI_API_KEY not set. Using local embeddings instead.")
            os.environ["EMBEDDING_BACKEND"] = "local"
    
    asyncio.run(main())