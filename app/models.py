from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class OnsiteMode(str, Enum):
    ONSITE = "onsite"
    REMOTE = "remote"
    HYBRID = "hybrid"


class IngestionStatus(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


# Skill and Role Aliases
class SkillAlias(BaseModel):
    canonical: str
    alias: str


class RoleAlias(BaseModel):
    canonical: str
    alias: str


# Company models
class CompanyIn(BaseModel):
    normalized_name: str
    aliases: List[str] = Field(default_factory=list)


class Company(CompanyIn):
    company_id: UUID
    
    model_config = ConfigDict(from_attributes=True)


# Broker models
class BrokerIn(BaseModel):
    name: str
    portal_url: Optional[str] = None


class Broker(BrokerIn):
    broker_id: UUID
    
    model_config = ConfigDict(from_attributes=True)


# Job models
class JobIn(BaseModel):
    job_uid: str
    source: str
    title: str
    description: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    role: Optional[str] = None
    seniority: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    location_city: Optional[str] = None
    location_country: Optional[str] = None
    onsite_mode: Optional[OnsiteMode] = None
    duration: Optional[str] = None
    start_date: Optional[date] = None
    company_id: Optional[UUID] = None
    broker_id: Optional[UUID] = None
    url: str
    posted_at: Optional[datetime] = None
    scraped_etag: Optional[str] = None
    scraped_last_modified: Optional[str] = None
    raw_json: Optional[Dict[str, Any]] = None


class Job(JobIn):
    job_id: UUID
    scraped_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Consultant models
class ConsultantIn(BaseModel):
    name: str
    role: Optional[str] = None
    seniority: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    location_city: Optional[str] = None
    location_country: Optional[str] = None
    onsite_mode: Optional[OnsiteMode] = None
    availability_from: Optional[date] = None
    notes: Optional[str] = None
    profile_url: Optional[str] = None
    active: bool = True


class Consultant(ConsultantIn):
    consultant_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Embedding models
class JobEmbedding(BaseModel):
    job_id: UUID
    embedding: List[float]
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ConsultantEmbedding(BaseModel):
    consultant_id: UUID
    embedding: List[float]
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Match models
class MatchReason(BaseModel):
    summary: str
    skills_matched: List[str]
    skills_missing: List[str]
    language_match: bool
    location_match: bool
    seniority_match: bool
    onsite_match: bool
    availability_match: bool
    strengths: List[str]
    concerns: List[str]


class JobConsultantMatch(BaseModel):
    job_id: UUID
    consultant_id: UUID
    score: Decimal
    reason_json: Dict[str, Any]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MatchResult(BaseModel):
    job: Job
    consultant: Consultant
    match: JobConsultantMatch
    
    model_config = ConfigDict(from_attributes=True)


class MatchRequest(BaseModel):
    job_ids: Optional[List[UUID]] = None
    consultant_ids: Optional[List[UUID]] = None
    min_score: float = 0.5
    max_results: int = 10


# Ingestion log models
class IngestionLog(BaseModel):
    run_id: UUID
    source: str
    status: str
    found_count: int = 0
    upserted_count: int = 0
    skipped_count: int = 0
    started_at: datetime
    finished_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# Report models
class ReportSummary(BaseModel):
    period_start: datetime
    period_end: datetime
    total_jobs: int
    new_jobs: int
    total_matches: int
    high_quality_matches: int
    top_consultants: List[Dict[str, Any]]
    top_skills: List[Dict[str, Any]]
    sources_breakdown: Dict[str, int]