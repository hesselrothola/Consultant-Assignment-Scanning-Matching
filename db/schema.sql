-- PostgreSQL 16 + pgvector schema for consultant assignment matching

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS skill_aliases (
  canonical TEXT NOT NULL,
  alias     TEXT NOT NULL,
  PRIMARY KEY (canonical, alias)
);

CREATE TABLE IF NOT EXISTS role_aliases (
  canonical TEXT NOT NULL,
  alias     TEXT NOT NULL,
  PRIMARY KEY (canonical, alias)
);

CREATE TABLE IF NOT EXISTS companies (
  company_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  normalized_name TEXT UNIQUE NOT NULL,
  aliases TEXT[] DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS brokers (
  broker_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT UNIQUE NOT NULL,
  portal_url TEXT
);

CREATE TABLE IF NOT EXISTS jobs (
  job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  job_uid TEXT UNIQUE NOT NULL,
  source TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  skills TEXT[] DEFAULT '{}',
  role TEXT,
  seniority TEXT,
  languages TEXT[] DEFAULT '{}',
  location_city TEXT,
  location_country TEXT,
  onsite_mode TEXT CHECK (onsite_mode IN ('onsite','remote','hybrid') OR onsite_mode IS NULL),
  duration TEXT,
  start_date DATE,
  company_id UUID REFERENCES companies(company_id),
  broker_id UUID REFERENCES brokers(broker_id),
  url TEXT NOT NULL,
  posted_at TIMESTAMPTZ,
  scraped_etag TEXT,
  scraped_last_modified TEXT,
  scraped_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  raw_json JSONB
);

CREATE TABLE IF NOT EXISTS job_embeddings (
  job_id UUID PRIMARY KEY REFERENCES jobs(job_id) ON DELETE CASCADE,
  embedding vector(3072),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS consultants (
  consultant_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  role TEXT,
  seniority TEXT,
  skills TEXT[] DEFAULT '{}',
  languages TEXT[] DEFAULT '{}',
  location_city TEXT,
  location_country TEXT,
  onsite_mode TEXT CHECK (onsite_mode IN ('onsite','remote','hybrid') OR onsite_mode IS NULL),
  availability_from DATE,
  notes TEXT,
  profile_url TEXT,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS consultant_embeddings (
  consultant_id UUID PRIMARY KEY REFERENCES consultants(consultant_id) ON DELETE CASCADE,
  embedding vector(3072),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS job_consultant_matches (
  job_id UUID REFERENCES jobs(job_id) ON DELETE CASCADE,
  consultant_id UUID REFERENCES consultants(consultant_id) ON DELETE CASCADE,
  score NUMERIC(5,4) NOT NULL,
  reason_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (job_id, consultant_id)
);

CREATE TABLE IF NOT EXISTS ingestion_log (
  run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source TEXT NOT NULL,
  status TEXT NOT NULL,
  found_count INT DEFAULT 0,
  upserted_count INT DEFAULT 0,
  skipped_count INT DEFAULT 0,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_jobs_posted_at ON jobs(posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_source   ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_jobs_company  ON jobs(company_id);
CREATE INDEX IF NOT EXISTS idx_jobs_broker   ON jobs(broker_id);
CREATE INDEX IF NOT EXISTS idx_jobs_gin_skills        ON jobs USING GIN (skills);
CREATE INDEX IF NOT EXISTS idx_consultants_gin_skills ON consultants USING GIN (skills);
CREATE INDEX IF NOT EXISTS idx_jobemb_vec       ON job_embeddings USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_consultantemb_vec ON consultant_embeddings USING ivfflat (embedding vector_cosine_ops);