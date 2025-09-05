#!/usr/bin/env python3

"""
Production Seeding Script
Seeds the database with initial scanning configurations for production use.
"""

import asyncio
import asyncpg
import uuid
import os
import sys
import json
from datetime import datetime

async def create_default_scanning_config(conn):
    """Create the default Swedish consulting scanning configuration"""
    
    # Check if any configs exist
    existing = await conn.fetchval("SELECT COUNT(*) FROM scanning_configs")
    if existing > 0:
        print(f"Found {existing} existing scanning configurations, skipping default config creation")
        return
    
    config_id = uuid.uuid4()
    
    # Swedish consulting market configuration
    query = """
        INSERT INTO scanning_configs (
            config_name,
            description,
            target_skills,
            target_roles,
            seniority_levels,
            target_locations,
            languages,
            contract_durations,
            onsite_modes,
            is_active
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING config_id
    """
    
    result = await conn.fetchval(
        query,
        "Swedish Consulting Market - Default",
        "Default configuration for Swedish consulting market scanning focusing on tech roles",
        # target_skills - common Swedish tech stack
        [
            "Python", "Java", "C#", ".NET", "JavaScript", "React", "Angular", "Vue.js",
            "Azure", "AWS", "Docker", "Kubernetes", "DevOps", "CI/CD", 
            "SQL", "PostgreSQL", "MongoDB", "Redis",
            "SAP", "Power BI", "Dynamics 365", "SharePoint",
            "Scrum", "Agile", "REST", "GraphQL", "Microservices"
        ],
        # target_roles - Swedish consulting roles
        [
            "Systemutvecklare", "System Developer", "Full Stack Developer", 
            "Backend Developer", "Frontend Developer",
            "DevOps Engineer", "Cloud Architect", "Solution Architect",
            "Tech Lead", "Scrum Master", "Product Owner",
            "Data Engineer", "Data Analyst", "Business Analyst",
            "SAP Konsult", "SAP Consultant", ".NET Utvecklare", ".NET Developer",
            "Java Utvecklare", "Java Developer"
        ],
        # seniority_levels
        ["Junior", "Medior", "Senior", "Expert", "Lead", "Architect"],
        # target_locations - major Swedish cities
        [
            "Stockholm", "Göteborg", "Malmö", "Uppsala", "Västerås", 
            "Örebro", "Linköping", "Helsingborg", "Jönköping", "Norrköping",
            "Remote", "Distans", "Hemarbete"
        ],
        # languages
        ["Svenska", "Swedish", "Engelska", "English"],
        # contract_durations
        ["1-3 månader", "3-6 månader", "6-12 månader", "1+ år", "Tillsvidare"],
        # onsite_modes
        ["onsite", "remote", "hybrid", "distans", "på plats", "hybridarbete"],
        # is_active
        True
    )
    
    config_id = result  # Use the returned UUID
    print(f"✅ Created default scanning configuration: {result}")
    
    # Create source overrides for each data source
    sources = [
        {
            "source_name": "brainville",
            "overrides": {
                "search_terms": ["konsult", "utvecklare", "developer", "architect"],
                "max_pages": 5,
                "rate_limit_delay": 2.0
            }
        },
        {
            "source_name": "linkedin", 
            "overrides": {
                "keywords": ["Contract", "Interim", "Consultant", "Konsult"],
                "location_codes": ["se:0"], # Sweden
                "experience_levels": ["2", "3", "4", "5"] # Mid to Senior
            }
        },
        {
            "source_name": "cinode",
            "overrides": {
                "categories": ["IT", "Technology", "Development"],
                "min_duration_months": 3
            }
        }
    ]
    
    for source in sources:
        override_query = """
            INSERT INTO source_config_overrides (
                config_id,
                source_name,
                parameter_overrides,
                is_enabled
            ) VALUES ($1, $2, $3, $4)
        """
        await conn.execute(
            override_query,
            config_id,
            source["source_name"],
            json.dumps(source["overrides"]),
            True
        )
        print(f"✅ Created source override for {source['source_name']}")
    
    return config_id

async def create_sample_consultants(conn):
    """Create sample consultant profiles for testing"""
    
    # Check if any consultants exist
    existing = await conn.fetchval("SELECT COUNT(*) FROM consultants")
    if existing > 0:
        print(f"Found {existing} existing consultants, skipping sample consultant creation")
        return
    
    sample_consultants = [
        {
            "name": "Erik Andersson",
            "role": "Senior Full Stack Developer",
            "seniority": "Senior",
            "skills": ["Python", "React", "PostgreSQL", "AWS", "Docker"],
            "languages": ["Svenska", "English"],
            "location_city": "Stockholm",
            "location_country": "Sweden",
            "onsite_mode": "hybrid",
            "notes": "Experienced full-stack developer with strong Python and React skills. Available for consulting assignments."
        },
        {
            "name": "Anna Svensson",
            "role": "DevOps Engineer", 
            "seniority": "Senior",
            "skills": ["Kubernetes", "Azure", "Terraform", "CI/CD", "Python"],
            "languages": ["Svenska", "English"],
            "location_city": "Göteborg",
            "location_country": "Sweden", 
            "onsite_mode": "remote",
            "notes": "DevOps specialist with extensive Azure and Kubernetes experience. Prefers remote work."
        },
        {
            "name": "Lars Johansson",
            "role": "SAP Consultant",
            "seniority": "Expert", 
            "skills": ["SAP", "ABAP", "SAP Fiori", "S/4HANA", "Integration"],
            "languages": ["Svenska", "English", "German"],
            "location_city": "Malmö",
            "location_country": "Sweden",
            "onsite_mode": "onsite",
            "notes": "SAP expert with 15+ years experience. Specialized in S/4HANA migrations and integrations."
        }
    ]
    
    for consultant_data in sample_consultants:
        query = """
            INSERT INTO consultants (
                name, role, seniority, skills, languages,
                location_city, location_country, onsite_mode, notes, active
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING consultant_id
        """
        result = await conn.fetchval(
            query,
            consultant_data["name"],
            consultant_data["role"],
            consultant_data["seniority"],
            consultant_data["skills"],
            consultant_data["languages"],
            consultant_data["location_city"], 
            consultant_data["location_country"],
            consultant_data["onsite_mode"],
            consultant_data["notes"],
            True
        )
        print(f"✅ Created sample consultant: {consultant_data['name']} ({result})")

async def create_skill_aliases(conn):
    """Create common skill aliases for better matching"""
    
    # Check if any aliases exist
    existing = await conn.fetchval("SELECT COUNT(*) FROM skill_aliases")
    if existing > 0:
        print(f"Found {existing} existing skill aliases, skipping creation")
        return
    
    skill_mappings = {
        "JavaScript": ["JS", "Javascript", "ECMAScript"],
        "TypeScript": ["TS", "Typescript"],
        "Python": ["Py", "Python3"],
        "C#": ["CSharp", "C-Sharp", "DotNet"],
        ".NET": ["dotnet", "dot-net", "Microsoft.NET"],
        "PostgreSQL": ["Postgres", "PostGres", "PgSQL"],
        "Kubernetes": ["K8s", "k8s"],
        "Docker": ["Containerization", "Containers"],
        "React": ["ReactJS", "React.js"],
        "Angular": ["AngularJS", "Angular.js"],
        "Vue": ["VueJS", "Vue.js"],
        "Node.js": ["NodeJS", "Node"],
        "MongoDB": ["Mongo", "NoSQL"],
        "Redis": ["Cache", "In-memory"],
        "AWS": ["Amazon Web Services"],
        "Azure": ["Microsoft Azure"],
        "DevOps": ["Dev-Ops", "Development Operations"],
        "CI/CD": ["Continuous Integration", "Continuous Deployment"],
        "REST": ["RESTful", "REST API"],
        "GraphQL": ["Graph QL", "GQL"]
    }
    
    for canonical, aliases in skill_mappings.items():
        for alias in aliases:
            await conn.execute(
                "INSERT INTO skill_aliases (canonical, alias) VALUES ($1, $2)",
                canonical, alias
            )
        print(f"✅ Created {len(aliases)} aliases for {canonical}")

async def create_role_aliases(conn):
    """Create common role aliases for better matching"""
    
    # Check if any aliases exist
    existing = await conn.fetchval("SELECT COUNT(*) FROM role_aliases")
    if existing > 0:
        print(f"Found {existing} existing role aliases, skipping creation")
        return
    
    role_mappings = {
        "System Developer": ["Systemutvecklare", "Software Developer", "Utvecklare"],
        "Full Stack Developer": ["Fullstack Developer", "Full-Stack Developer"],
        "Backend Developer": ["Back-end Developer", "Server Developer"],
        "Frontend Developer": ["Front-end Developer", "UI Developer"],
        "DevOps Engineer": ["DevOps Specialist", "Site Reliability Engineer", "SRE"],
        "Solution Architect": ["Solutions Architect", "System Architect"],
        "Tech Lead": ["Technical Lead", "Development Lead", "Team Lead"],
        "Product Owner": ["PO", "Product Manager"],
        "Scrum Master": ["Agile Coach", "SM"],
        "Data Engineer": ["Data Pipeline Engineer", "ETL Developer"],
        "SAP Consultant": ["SAP Konsult", "SAP Specialist", "SAP Developer"]
    }
    
    for canonical, aliases in role_mappings.items():
        for alias in aliases:
            await conn.execute(
                "INSERT INTO role_aliases (canonical, alias) VALUES ($1, $2)",
                canonical, alias
            )
        print(f"✅ Created {len(aliases)} aliases for {canonical}")

async def main():
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/consultant_matching")
    
    print("🚀 Starting production database seeding...")
    print(f"Connecting to: {database_url}")
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Create initial data
        await create_skill_aliases(conn)
        await create_role_aliases(conn)
        config_id = await create_default_scanning_config(conn)
        await create_sample_consultants(conn)
        
        print("\n🎉 Production seeding completed successfully!")
        print(f"Default scanning configuration ID: {config_id}")
        print("\nNext steps:")
        print("1. Configure environment variables (OPENAI_API_KEY, SMTP settings)")
        print("2. Test the scheduler endpoints")
        print("3. Run manual scan to validate the system")
        
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            await conn.close()

if __name__ == "__main__":
    asyncio.run(main())