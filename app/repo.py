import asyncpg
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date
import json
from decimal import Decimal

from app.models import (
    Job, JobIn, Consultant, ConsultantIn,
    Company, CompanyIn, Broker, BrokerIn,
    JobConsultantMatch, IngestionLog,
    SkillAlias, RoleAlias
)


DEFAULT_EXECUTIVE_ROLES = [
    "Interim CTO",
    "Interim CIO",
    "Chief Digital Officer",
    "Transformation Director",
    "Enterprise Architect",
    "Business Architect",
    "Solution Architect",
    "Data Architect",
    "Program Manager",
    "Program Director",
    "Change Manager",
    "Change Lead",
    "Transformation Lead",
    "M&A Integration Lead",
    "Head of Development",
    "Head of Engineering",
    "Head of R&D",
    "R&D Director",
    "Engineering Director",
    "Engineering VP",
    "Technology Director",
    "Chief Architect",
    "Digital Transformation Manager",
    "Head of Digital",
    "Program Leader"
]

DEFAULT_EXECUTIVE_SKILLS = [
    "Digital Transformation",
    "Change Management",
    "Enterprise Architecture",
    "Program Leadership",
    "Strategic Planning",
    "Technology Strategy",
    "M&A Integration",
    "Innovation Management"
]

DEFAULT_EXECUTIVE_LOCATIONS = [
    "Stockholm",
    "Göteborg",
    "Gothenburg",
    "Malmö",
    "Remote",
    "Hybrid"
]

DEFAULT_EXECUTIVE_LANGUAGES = ["SV", "EN"]
DEFAULT_EXECUTIVE_SENIORITY = ["Senior", "Executive", "C-level"]
DEFAULT_EXECUTIVE_ONSITE = ["onsite", "hybrid", "remote"]
DEFAULT_VERAMA_LEVELS = ["SENIOR", "EXPERT"]
DEFAULT_VERAMA_COUNTRIES = ["SE"]


class DatabaseRepository:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool = None
    
    async def init(self):
        self.pool = await asyncpg.create_pool(self.db_url)
    
    async def close(self):
        if self.pool:
            await self.pool.close()
    
    # Company operations
    async def upsert_company(self, company: CompanyIn) -> Company:
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO companies (normalized_name, aliases)
                VALUES ($1, $2)
                ON CONFLICT (normalized_name)
                DO UPDATE SET aliases = EXCLUDED.aliases
                RETURNING *
            """
            row = await conn.fetchrow(
                query,
                company.normalized_name,
                company.aliases if company.aliases else []
            )
            return Company(
                company_id=row['company_id'],
                normalized_name=row['normalized_name'],
                aliases=list(row['aliases']) if row['aliases'] else []
            )
    
    async def get_company_by_name(self, name: str) -> Optional[Company]:
        async with self.pool.acquire() as conn:
            query = """
                SELECT * FROM companies 
                WHERE normalized_name = $1 
                OR $1 = ANY(aliases)
            """
            row = await conn.fetchrow(query, name)
            if row:
                return Company(
                    company_id=row['company_id'],
                    normalized_name=row['normalized_name'],
                    aliases=list(row['aliases']) if row['aliases'] else []
                )
            return None
    
    # Broker operations
    async def upsert_broker(self, broker: BrokerIn) -> Broker:
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO brokers (name, portal_url)
                VALUES ($1, $2)
                ON CONFLICT (name)
                DO UPDATE SET portal_url = EXCLUDED.portal_url
                RETURNING *
            """
            row = await conn.fetchrow(
                query,
                broker.name,
                broker.portal_url
            )
            return Broker(
                broker_id=row['broker_id'],
                name=row['name'],
                portal_url=row['portal_url']
            )
    
    async def get_broker_by_name(self, name: str) -> Optional[Broker]:
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM brokers WHERE name = $1"
            row = await conn.fetchrow(query, name)
            if row:
                return Broker(
                    broker_id=row['broker_id'],
                    name=row['name'],
                    portal_url=row['portal_url']
                )
            return None
    
    # Job operations
    async def upsert_job(self, job: JobIn) -> Job:
        async with self.pool.acquire() as conn:
            skills = job.skills if job.skills else []
            languages = job.languages if job.languages else []
            
            query = """
                INSERT INTO jobs (
                    job_uid, source, title, description, skills, role, seniority,
                    languages, location_city, location_country, onsite_mode,
                    duration, start_date, company_id, broker_id, url,
                    posted_at, scraped_etag, scraped_last_modified, raw_json
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
                    $14, $15, $16, $17, $18, $19, $20
                )
                ON CONFLICT (job_uid)
                DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    skills = EXCLUDED.skills,
                    role = EXCLUDED.role,
                    seniority = EXCLUDED.seniority,
                    languages = EXCLUDED.languages,
                    location_city = EXCLUDED.location_city,
                    location_country = EXCLUDED.location_country,
                    onsite_mode = EXCLUDED.onsite_mode,
                    duration = EXCLUDED.duration,
                    start_date = EXCLUDED.start_date,
                    company_id = EXCLUDED.company_id,
                    broker_id = EXCLUDED.broker_id,
                    url = EXCLUDED.url,
                    posted_at = EXCLUDED.posted_at,
                    scraped_etag = EXCLUDED.scraped_etag,
                    scraped_last_modified = EXCLUDED.scraped_last_modified,
                    raw_json = EXCLUDED.raw_json,
                    scraped_at = now()
                RETURNING *
            """
            
            row = await conn.fetchrow(
                query,
                job.job_uid,
                job.source,
                job.title,
                job.description,
                skills,
                job.role,
                job.seniority,
                languages,
                job.location_city,
                job.location_country,
                job.onsite_mode.value if job.onsite_mode else None,
                job.duration,
                job.start_date,
                job.company_id,
                job.broker_id,
                job.url,
                job.posted_at,
                job.scraped_etag,
                job.scraped_last_modified,
                json.dumps(job.raw_json) if job.raw_json else None
            )
            
            return self._row_to_job(row)
    
    async def get_job(self, job_id: UUID) -> Optional[Job]:
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM jobs WHERE job_id = $1"
            row = await conn.fetchrow(query, job_id)
            return self._row_to_job(row) if row else None
    
    async def get_jobs(
        self,
        source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Job]:
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM jobs WHERE 1=1"
            params = []
            param_count = 0
            
            if source:
                param_count += 1
                query += f" AND source = ${param_count}"
                params.append(source)
            
            query += " ORDER BY posted_at DESC NULLS LAST, scraped_at DESC"
            
            param_count += 1
            query += f" LIMIT ${param_count}"
            params.append(limit)
            
            param_count += 1
            query += f" OFFSET ${param_count}"
            params.append(offset)
            
            rows = await conn.fetch(query, *params)
            return [self._row_to_job(row) for row in rows]
    
    # Consultant operations
    async def upsert_consultant(self, consultant: ConsultantIn) -> Consultant:
        async with self.pool.acquire() as conn:
            skills = consultant.skills if consultant.skills else []
            languages = consultant.languages if consultant.languages else []
            
            # Check if consultant exists (by name for simplicity)
            existing = await conn.fetchrow(
                "SELECT consultant_id FROM consultants WHERE name = $1",
                consultant.name
            )
            
            if existing:
                # Update existing consultant
                query = """
                    UPDATE consultants SET
                        role = $2,
                        seniority = $3,
                        skills = $4,
                        languages = $5,
                        location_city = $6,
                        location_country = $7,
                        onsite_mode = $8,
                        availability_from = $9,
                        notes = $10,
                        profile_url = $11,
                        active = $12,
                        updated_at = now()
                    WHERE consultant_id = $1
                    RETURNING *
                """
                row = await conn.fetchrow(
                    query,
                    existing['consultant_id'],
                    consultant.role,
                    consultant.seniority,
                    skills,
                    languages,
                    consultant.location_city,
                    consultant.location_country,
                    consultant.onsite_mode.value if consultant.onsite_mode else None,
                    consultant.availability_from,
                    consultant.notes,
                    consultant.profile_url,
                    consultant.active
                )
            else:
                # Insert new consultant
                query = """
                    INSERT INTO consultants (
                        name, role, seniority, skills, languages,
                        location_city, location_country, onsite_mode,
                        availability_from, notes, profile_url, active
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
                    )
                    RETURNING *
                """
                row = await conn.fetchrow(
                    query,
                    consultant.name,
                    consultant.role,
                    consultant.seniority,
                    skills,
                    languages,
                    consultant.location_city,
                    consultant.location_country,
                    consultant.onsite_mode.value if consultant.onsite_mode else None,
                    consultant.availability_from,
                    consultant.notes,
                    consultant.profile_url,
                    consultant.active
                )
            
            return self._row_to_consultant(row)
    
    async def get_consultant(self, consultant_id: UUID) -> Optional[Consultant]:
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM consultants WHERE consultant_id = $1"
            row = await conn.fetchrow(query, consultant_id)
            return self._row_to_consultant(row) if row else None
    
    async def get_consultants(
        self,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[Consultant]:
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM consultants WHERE 1=1"
            params = []
            param_count = 0
            
            if active_only:
                param_count += 1
                query += f" AND active = ${param_count}"
                params.append(True)
            
            query += " ORDER BY created_at DESC"
            
            param_count += 1
            query += f" LIMIT ${param_count}"
            params.append(limit)
            
            param_count += 1
            query += f" OFFSET ${param_count}"
            params.append(offset)
            
            rows = await conn.fetch(query, *params)
            return [self._row_to_consultant(row) for row in rows]
    
    # Embedding operations
    async def store_job_embedding(
        self,
        job_id: UUID,
        embedding: List[float]
    ):
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO job_embeddings (job_id, embedding)
                VALUES ($1, $2)
                ON CONFLICT (job_id)
                DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    updated_at = now()
            """
            await conn.execute(query, job_id, embedding)
    
    async def store_consultant_embedding(
        self,
        consultant_id: UUID,
        embedding: List[float]
    ):
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO consultant_embeddings (consultant_id, embedding)
                VALUES ($1, $2)
                ON CONFLICT (consultant_id)
                DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    updated_at = now()
            """
            await conn.execute(query, consultant_id, embedding)
    
    async def get_job_embedding(self, job_id: UUID) -> Optional[List[float]]:
        async with self.pool.acquire() as conn:
            query = "SELECT embedding FROM job_embeddings WHERE job_id = $1"
            row = await conn.fetchrow(query, job_id)
            return list(row['embedding']) if row and row['embedding'] else None
    
    async def get_consultant_embedding(self, consultant_id: UUID) -> Optional[List[float]]:
        async with self.pool.acquire() as conn:
            query = "SELECT embedding FROM consultant_embeddings WHERE consultant_id = $1"
            row = await conn.fetchrow(query, consultant_id)
            return list(row['embedding']) if row and row['embedding'] else None
    
    # Match operations
    async def upsert_match(
        self,
        job_id: UUID,
        consultant_id: UUID,
        score: float,
        reason_json: Dict[str, Any]
    ) -> JobConsultantMatch:
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO job_consultant_matches (
                    job_id, consultant_id, score, reason_json
                ) VALUES ($1, $2, $3, $4)
                ON CONFLICT (job_id, consultant_id)
                DO UPDATE SET
                    score = EXCLUDED.score,
                    reason_json = EXCLUDED.reason_json,
                    created_at = now()
                RETURNING *
            """
            
            row = await conn.fetchrow(
                query,
                job_id,
                consultant_id,
                score,
                json.dumps(reason_json)
            )
            
            return JobConsultantMatch(
                job_id=row['job_id'],
                consultant_id=row['consultant_id'],
                score=row['score'],
                reason_json=json.loads(row['reason_json']),
                created_at=row['created_at']
            )
    
    async def get_matches_for_job(
        self,
        job_id: UUID,
        min_score: float = 0.0,
        limit: int = 10
    ) -> List[JobConsultantMatch]:
        async with self.pool.acquire() as conn:
            query = """
                SELECT * FROM job_consultant_matches
                WHERE job_id = $1 AND score >= $2
                ORDER BY score DESC
                LIMIT $3
            """
            rows = await conn.fetch(query, job_id, min_score, limit)
            return [self._row_to_match(row) for row in rows]
    
    # Skill and role alias operations
    async def add_skill_alias(self, canonical: str, alias: str):
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO skill_aliases (canonical, alias)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
            """
            await conn.execute(query, canonical, alias)
    
    async def add_role_alias(self, canonical: str, alias: str):
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO role_aliases (canonical, alias)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
            """
            await conn.execute(query, canonical, alias)
    
    async def get_canonical_skill(self, skill: str) -> str:
        async with self.pool.acquire() as conn:
            query = """
                SELECT canonical FROM skill_aliases
                WHERE alias = $1
            """
            row = await conn.fetchrow(query, skill)
            return row['canonical'] if row else skill
    
    async def get_canonical_role(self, role: str) -> str:
        async with self.pool.acquire() as conn:
            query = """
                SELECT canonical FROM role_aliases
                WHERE alias = $1
            """
            row = await conn.fetchrow(query, role)
            return row['canonical'] if row else role
    
    # Ingestion log operations
    async def create_ingestion_log(
        self,
        source: str
    ) -> UUID:
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO ingestion_log (source, status)
                VALUES ($1, 'started')
                RETURNING run_id
            """
            row = await conn.fetchrow(query, source)
            return row['run_id']
    
    async def update_ingestion_log(
        self,
        run_id: UUID,
        status: str,
        found_count: int = 0,
        upserted_count: int = 0,
        skipped_count: int = 0
    ):
        async with self.pool.acquire() as conn:
            query = """
                UPDATE ingestion_log SET
                    status = $2,
                    found_count = $3,
                    upserted_count = $4,
                    skipped_count = $5,
                    finished_at = now()
                WHERE run_id = $1
            """
            await conn.execute(
                query,
                run_id,
                status,
                found_count,
                upserted_count,
                skipped_count
            )
    
    # Helper methods to convert database rows to models
    def _row_to_job(self, row) -> Job:
        return Job(
            job_id=row['job_id'],
            job_uid=row['job_uid'],
            source=row['source'],
            title=row['title'],
            description=row['description'],
            skills=list(row['skills']) if row['skills'] else [],
            role=row['role'],
            seniority=row['seniority'],
            languages=list(row['languages']) if row['languages'] else [],
            location_city=row['location_city'],
            location_country=row['location_country'],
            onsite_mode=row['onsite_mode'],
            duration=row['duration'],
            start_date=row['start_date'],
            company_id=row['company_id'],
            broker_id=row['broker_id'],
            url=row['url'],
            posted_at=row['posted_at'],
            scraped_etag=row['scraped_etag'],
            scraped_last_modified=row['scraped_last_modified'],
            scraped_at=row['scraped_at'],
            raw_json=json.loads(row['raw_json']) if row['raw_json'] else None
        )
    
    def _row_to_consultant(self, row) -> Consultant:
        return Consultant(
            consultant_id=row['consultant_id'],
            name=row['name'],
            role=row['role'],
            seniority=row['seniority'],
            skills=list(row['skills']) if row['skills'] else [],
            languages=list(row['languages']) if row['languages'] else [],
            location_city=row['location_city'],
            location_country=row['location_country'],
            onsite_mode=row['onsite_mode'],
            availability_from=row['availability_from'],
            notes=row['notes'],
            profile_url=row['profile_url'],
            active=row['active'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    
    def _row_to_match(self, row) -> JobConsultantMatch:
        return JobConsultantMatch(
            job_id=row['job_id'],
            consultant_id=row['consultant_id'],
            score=row['score'],
            reason_json=json.loads(row['reason_json']),
            created_at=row['created_at']
        )
    
    # Helper methods for scrapers
    async def get_or_create_company(self, company_name: str) -> Company:
        """Get existing company or create new one."""
        normalized_name = company_name.lower().strip()
        
        # Check if company exists
        existing = await self.get_company_by_name(normalized_name)
        if existing:
            return existing
        
        # Create new company
        return await self.upsert_company(CompanyIn(
            normalized_name=normalized_name,
            aliases=[company_name]
        ))
    
    async def get_or_create_broker(self, broker_name: str) -> Broker:
        """Get existing broker or create new one."""
        # Check if broker exists
        existing = await self.get_broker_by_name(broker_name)
        if existing:
            return existing
        
        # Create new broker
        return await self.upsert_broker(BrokerIn(name=broker_name))
    
    async def log_ingestion(
        self,
        source: str,
        status: str,
        found_count: int = 0,
        upserted_count: int = 0,
        skipped_count: int = 0,
        error: Optional[str] = None
    ) -> UUID:
        """Log an ingestion run."""
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO ingestion_log (
                    source, status, found_count, upserted_count, 
                    skipped_count, started_at, finished_at
                )
                VALUES ($1, $2, $3, $4, $5, now() - interval '1 second', now())
                RETURNING run_id
            """
            row = await conn.fetchrow(
                query,
                source,
                status,
                found_count,
                upserted_count,
                skipped_count
            )
            return row['run_id']
    
    async def get_recent_ingestion_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent ingestion logs."""
        async with self.pool.acquire() as conn:
            query = """
                SELECT 
                    run_id,
                    source,
                    status,
                    found_count,
                    upserted_count,
                    skipped_count,
                    started_at,
                    finished_at
                FROM ingestion_log
                ORDER BY started_at DESC
                LIMIT $1
            """
            rows = await conn.fetch(query, limit)
            results = []
            for row in rows:
                started_at = row['started_at']
                finished_at = row['finished_at']
                duration_seconds = None
                if started_at and finished_at:
                    duration_seconds = (finished_at - started_at).total_seconds()

                results.append({
                    'run_id': str(row['run_id']),
                    'source': row['source'],
                    'status': row['status'],
                    'found_count': row['found_count'],
                    'upserted_count': row['upserted_count'],
                    'skipped_count': row['skipped_count'],
                    'started_at': started_at,
                    'finished_at': finished_at,
                    'duration_seconds': duration_seconds
                })

            return results
    
    # User authentication methods
    async def create_user(self, username: str, email: str, full_name: str, 
                         hashed_password: str, role: str = 'viewer', is_active: bool = True) -> Dict[str, Any]:
        """Create a new user."""
        query = """
            INSERT INTO users (username, email, full_name, hashed_password, role, is_active)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING user_id, username, email, full_name, role, is_active, created_at
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, username, email, full_name, hashed_password, role, is_active)
            return dict(row)
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        query = """
            SELECT user_id, username, email, full_name, hashed_password, role, 
                   is_active, created_at, last_login
            FROM users
            WHERE username = $1
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, username)
            return dict(row) if row else None
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        query = """
            SELECT user_id, username, email, full_name, hashed_password, role, 
                   is_active, created_at, last_login
            FROM users
            WHERE user_id = $1
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, user_id)
            return dict(row) if row else None
    
    async def update_user(self, user_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Update user details."""
        # Build dynamic update query
        updates = []
        values = []
        param_count = 1
        
        for field, value in kwargs.items():
            if value is not None and field in ['email', 'full_name', 'role', 'is_active', 'hashed_password']:
                updates.append(f"{field} = ${param_count}")
                values.append(value)
                param_count += 1
        
        if not updates:
            return None
        
        values.append(user_id)
        query = f"""
            UPDATE users
            SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ${param_count}
            RETURNING user_id, username, email, full_name, role, is_active, created_at, updated_at
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *values)
            return dict(row) if row else None
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        query = "DELETE FROM users WHERE user_id = $1"
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, user_id)
            return result != "DELETE 0"
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users."""
        query = """
            SELECT user_id, username, email, full_name, role, is_active, 
                   created_at, last_login
            FROM users
            ORDER BY created_at DESC
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]
    
    async def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp."""
        query = "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = $1"
        async with self.pool.acquire() as conn:
            await conn.execute(query, user_id)
    
    async def update_user_password(self, user_id: UUID, hashed_password: str) -> bool:
        """Update user's password."""
        query = """
            UPDATE users 
            SET hashed_password = $2, updated_at = CURRENT_TIMESTAMP 
            WHERE user_id = $1
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, str(user_id), hashed_password)
            return result != "UPDATE 0"
    
    async def update_user_active_status(self, user_id: UUID, is_active: bool) -> bool:
        """Update user's active status."""
        query = """
            UPDATE users 
            SET is_active = $2, updated_at = CURRENT_TIMESTAMP 
            WHERE user_id = $1
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, str(user_id), is_active)
            return result != "UPDATE 0"
    
    async def log_user_action(self, user_id: str, action: str, resource_type: str = None,
                             resource_id: str = None, details: dict = None, ip_address: str = None):
        """Log user action for audit trail."""
        query = """
            INSERT INTO user_audit_log (user_id, action, resource_type, resource_id, details, ip_address)
            VALUES ($1, $2, $3, $4, $5, $6)
        """
        import json
        details_json = json.dumps(details) if details else None
        async with self.pool.acquire() as conn:
            await conn.execute(query, user_id, action, resource_type, resource_id, details_json, ip_address)

    # Scanning Configuration Operations
    async def get_active_scanning_configs(self) -> List[Dict[str, Any]]:
        """Get all active scanning configurations"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT 
                    config_id,
                    config_name,
                    description,
                    target_skills,
                    target_roles,
                    seniority_levels,
                    target_locations,
                    languages,
                    contract_durations,
                    onsite_modes,
                    total_matches_generated,
                    successful_placements,
                    last_match_score,
                    performance_score,
                    is_active,
                    created_at,
                    updated_at
                FROM scanning_configs
                WHERE is_active = true
                ORDER BY performance_score DESC
            """
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]

    async def get_all_scanning_configs(self) -> List[Dict[str, Any]]:
        """Get all scanning configurations (active and inactive)"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT 
                    config_id,
                    config_name,
                    description,
                    target_skills,
                    target_roles,
                    seniority_levels,
                    target_locations,
                    languages,
                    contract_durations,
                    onsite_modes,
                    total_matches_generated,
                    successful_placements,
                    last_match_score,
                    performance_score,
                    is_active,
                    created_at,
                    updated_at
                FROM scanning_configs
                ORDER BY performance_score DESC
            """
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]

    async def get_scanning_config(self, config_id: UUID) -> Optional[Dict[str, Any]]:
        """Get a specific scanning configuration by ID"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT 
                    config_id,
                    config_name,
                    description,
                    target_skills,
                    target_roles,
                    seniority_levels,
                    target_locations,
                    languages,
                    contract_durations,
                    onsite_modes,
                    total_matches_generated,
                    successful_placements,
                    last_match_score,
                    performance_score,
                    is_active,
                    created_at,
                    updated_at
                FROM scanning_configs
                WHERE config_id = $1
            """
            row = await conn.fetchrow(query, config_id)
            return dict(row) if row else None

    async def get_scanning_config_by_name(self, config_name: str) -> Optional[Dict[str, Any]]:
        """Fetch a scanning configuration by its unique name."""
        async with self.pool.acquire() as conn:
            query = """
                SELECT 
                    config_id,
                    config_name,
                    description,
                    target_skills,
                    target_roles,
                    seniority_levels,
                    target_locations,
                    languages,
                    contract_durations,
                    onsite_modes,
                    total_matches_generated,
                    successful_placements,
                    last_match_score,
                    performance_score,
                    is_active,
                    created_at,
                    updated_at
                FROM scanning_configs
                WHERE config_name = $1
            """
            row = await conn.fetchrow(query, config_name)
            return dict(row) if row else None

    async def create_scanning_config(self,
                                     config_name: str,
                                     description: str = "",
                                     target_skills: Optional[List[str]] = None,
                                     target_roles: Optional[List[str]] = None,
                                     seniority_levels: Optional[List[str]] = None,
                                     target_locations: Optional[List[str]] = None,
                                     languages: Optional[List[str]] = None,
                                     contract_durations: Optional[List[str]] = None,
                                     onsite_modes: Optional[List[str]] = None,
                                     is_active: bool = True) -> Dict[str, Any]:
        """Create a new scanning configuration."""
        async with self.pool.acquire() as conn:
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
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10
                )
                RETURNING 
                    config_id,
                    config_name,
                    description,
                    target_skills,
                    target_roles,
                    seniority_levels,
                    target_locations,
                    languages,
                    contract_durations,
                    onsite_modes,
                    total_matches_generated,
                    successful_placements,
                    last_match_score,
                    performance_score,
                    is_active,
                    created_at,
                    updated_at
            """
            row = await conn.fetchrow(
                query,
                config_name,
                description,
                target_skills or [],
                target_roles or [],
                seniority_levels or [],
                target_locations or [],
                languages or [],
                contract_durations or [],
                onsite_modes or [],
                is_active
            )
            return dict(row)

    async def get_source_config_overrides(self, config_id: UUID) -> List[Dict[str, Any]]:
        """Get source-specific configuration overrides for a scanning config"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT 
                    override_id,
                    config_id,
                    source_name,
                    parameter_overrides,
                    last_run_at,
                    success_rate,
                    avg_matches_per_run,
                    is_enabled
                FROM source_config_overrides
                WHERE config_id = $1 AND is_enabled = true
                ORDER BY source_name
            """
            rows = await conn.fetch(query, config_id)
            return [dict(row) for row in rows]

    async def get_source_override(self, config_id: UUID, source_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific source override."""
        async with self.pool.acquire() as conn:
            query = """
                SELECT 
                    override_id,
                    config_id,
                    source_name,
                    parameter_overrides,
                    last_run_at,
                    success_rate,
                    avg_matches_per_run,
                    is_enabled
                FROM source_config_overrides
                WHERE config_id = $1 AND source_name = $2
            """
            row = await conn.fetchrow(query, config_id, source_name)
            return dict(row) if row else None

    async def upsert_source_override(self,
                                     config_id: UUID,
                                     source_name: str,
                                     parameter_overrides: Dict[str, Any],
                                     is_enabled: bool = True) -> Dict[str, Any]:
        """Insert or update a source override."""
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO source_config_overrides (
                    config_id,
                    source_name,
                    parameter_overrides,
                    is_enabled,
                    last_run_at,
                    success_rate,
                    avg_matches_per_run
                ) VALUES (
                    $1, $2, $3, $4, NULL, NULL, NULL
                )
                ON CONFLICT (config_id, source_name)
                DO UPDATE SET
                    parameter_overrides = EXCLUDED.parameter_overrides,
                    is_enabled = EXCLUDED.is_enabled
                RETURNING 
                    override_id,
                    config_id,
                    source_name,
                    parameter_overrides,
                    last_run_at,
                    success_rate,
                    avg_matches_per_run,
                    is_enabled
            """
            row = await conn.fetchrow(
                query,
                config_id,
                source_name,
                json.dumps(parameter_overrides),
                is_enabled
            )
            return dict(row)

    async def ensure_manual_scanning_config(self) -> Dict[str, Any]:
        """Ensure a manual override scanning configuration exists and return it with overrides."""
        config_name = "Manual Executive Override"
        config = await self.get_scanning_config_by_name(config_name)

        if not config:
            config = await self.create_scanning_config(
                config_name=config_name,
                description="Manual executive scanning criteria",
                target_skills=DEFAULT_EXECUTIVE_SKILLS,
                target_roles=DEFAULT_EXECUTIVE_ROLES,
                seniority_levels=DEFAULT_EXECUTIVE_SENIORITY,
                target_locations=DEFAULT_EXECUTIVE_LOCATIONS,
                languages=DEFAULT_EXECUTIVE_LANGUAGES,
                onsite_modes=DEFAULT_EXECUTIVE_ONSITE,
                is_active=True
            )

        override = await self.get_source_override(config['config_id'], 'verama')
        if not override:
            override = await self.upsert_source_override(
                config_id=config['config_id'],
                source_name='verama',
                parameter_overrides={
                    'countries': DEFAULT_VERAMA_COUNTRIES,
                    'languages': DEFAULT_EXECUTIVE_LANGUAGES,
                    'levels': DEFAULT_VERAMA_LEVELS,
                    'target_roles': DEFAULT_EXECUTIVE_ROLES,
                    'target_keywords': DEFAULT_EXECUTIVE_ROLES,
                    'onsite_modes': DEFAULT_EXECUTIVE_ONSITE
                },
                is_enabled=True
            )

        config['manual_override'] = override
        return config

    async def update_manual_scanning_config(self,
                                            config_id: UUID,
                                            *,
                                            target_skills: List[str],
                                            target_roles: List[str],
                                            seniority_levels: List[str],
                                            target_locations: List[str],
                                            languages: List[str],
                                            onsite_modes: List[str],
                                            contract_durations: Optional[List[str]] = None,
                                            source_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Update manual scanning configuration and associated overrides."""
        async with self.pool.acquire() as conn:
            query = """
                UPDATE scanning_configs
                SET 
                    target_skills = $2,
                    target_roles = $3,
                    seniority_levels = $4,
                    target_locations = $5,
                    languages = $6,
                    contract_durations = $7,
                    onsite_modes = $8,
                    updated_at = now()
                WHERE config_id = $1
                RETURNING 
                    config_id,
                    config_name,
                    description,
                    target_skills,
                    target_roles,
                    seniority_levels,
                    target_locations,
                    languages,
                    contract_durations,
                    onsite_modes,
                    total_matches_generated,
                    successful_placements,
                    last_match_score,
                    performance_score,
                    is_active,
                    created_at,
                    updated_at
            """
            row = await conn.fetchrow(
                query,
                config_id,
                target_skills,
                target_roles,
                seniority_levels,
                target_locations,
                languages,
                contract_durations or [],
                onsite_modes
            )

        if source_overrides is not None:
            await self.upsert_source_override(
                config_id=config_id,
                source_name='verama',
                parameter_overrides=source_overrides,
                is_enabled=True
            )

        updated_config = dict(row)
        override = await self.get_source_override(config_id, 'ework')
        updated_config['manual_override'] = override
        return updated_config

    async def log_config_performance(self, performance_data: Dict[str, Any]):
        """Log performance metrics for a scanning configuration"""
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO config_performance_log (
                    config_id,
                    source_name,
                    test_date,
                    jobs_found,
                    matches_generated,
                    quality_score,
                    consultant_interest_rate,
                    placement_rate,
                    notes
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING log_id
            """
            await conn.fetchval(
                query,
                performance_data.get('config_id'),
                performance_data.get('source_name'),
                performance_data.get('test_date', datetime.now().date()),
                performance_data.get('jobs_found', 0),
                performance_data.get('matches_generated', 0),
                performance_data.get('quality_score'),
                performance_data.get('consultant_interest_rate'),
                performance_data.get('placement_rate'),
                performance_data.get('notes')
            )

    async def update_source_performance(self, config_id: UUID, source_name: str, performance_data: Dict[str, Any]):
        """Update performance metrics for a specific source override"""
        async with self.pool.acquire() as conn:
            query = """
                UPDATE source_config_overrides
                SET 
                    last_run_at = $3,
                    success_rate = $4,
                    avg_matches_per_run = $5
                WHERE config_id = $1 AND source_name = $2
            """
            await conn.execute(
                query,
                config_id,
                source_name,
                performance_data.get('last_run_at', datetime.now()),
                performance_data.get('success_rate'),
                performance_data.get('avg_matches_per_run')
            )

    async def get_config_performance_history(self, config_id: UUID, days: int = 30) -> List[Dict[str, Any]]:
        """Get performance history for a scanning configuration"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT 
                    log_id,
                    config_id,
                    source_name,
                    test_date,
                    jobs_found,
                    matches_generated,
                    quality_score,
                    consultant_interest_rate,
                    placement_rate,
                    notes,
                    created_at
                FROM config_performance_log
                WHERE config_id = $1 
                    AND test_date >= CURRENT_DATE - INTERVAL '%s days'
                ORDER BY test_date DESC
            """ % days
            rows = await conn.fetch(query, config_id)
            return [dict(row) for row in rows]

    async def update_config_performance_score(self, config_id: UUID, performance_score: float):
        """Update the overall performance score for a scanning configuration"""
        async with self.pool.acquire() as conn:
            query = """
                UPDATE scanning_configs
                SET 
                    performance_score = $2,
                    updated_at = now()
                WHERE config_id = $1
            """
            await conn.execute(query, config_id, performance_score)

    async def upsert_learning_parameter(self, param_name: str, param_value: str, effectiveness_score: float = 0.0, config_id: UUID = None):
        """Insert or update a learning parameter"""
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO learning_parameters (
                    parameter_name,
                    parameter_value,
                    effectiveness_score,
                    usage_count,
                    last_used_at,
                    learned_from_config_id
                ) VALUES ($1, $2, $3, 1, now(), $4)
                ON CONFLICT (parameter_name, parameter_value)
                DO UPDATE SET 
                    effectiveness_score = EXCLUDED.effectiveness_score,
                    usage_count = learning_parameters.usage_count + 1,
                    last_used_at = now(),
                    learned_from_config_id = COALESCE(EXCLUDED.learned_from_config_id, learning_parameters.learned_from_config_id)
                RETURNING param_id
            """
            return await conn.fetchval(query, param_name, param_value, effectiveness_score, config_id)

    async def upsert_jobs(self, jobs: List[JobIn]) -> List[Job]:
        """Bulk upsert multiple jobs"""
        result_jobs = []
        for job_in in jobs:
            job = await self.upsert_job(job_in)
            result_jobs.append(job)
        return result_jobs
