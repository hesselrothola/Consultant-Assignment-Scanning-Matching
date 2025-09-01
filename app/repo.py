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