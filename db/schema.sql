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
  embedding vector(1536),
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
  embedding vector(1536),
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

-- Unified AI Scanner Configuration System
CREATE TABLE IF NOT EXISTS scanning_configs (
  config_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  config_name TEXT UNIQUE NOT NULL,
  description TEXT,
  -- Global search parameters applied across all sources
  target_skills TEXT[] DEFAULT '{}',
  target_roles TEXT[] DEFAULT '{}',
  seniority_levels TEXT[] DEFAULT '{}',
  target_locations TEXT[] DEFAULT '{}',
  languages TEXT[] DEFAULT '{}',
  contract_durations TEXT[] DEFAULT '{}',
  onsite_modes TEXT[] DEFAULT '{}',
  -- Performance tracking
  total_matches_generated INT DEFAULT 0,
  successful_placements INT DEFAULT 0,
  last_match_score NUMERIC(5,4),
  performance_score NUMERIC(5,4) DEFAULT 0,
  -- Configuration metadata
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Per-source configuration overrides
CREATE TABLE IF NOT EXISTS source_config_overrides (
  override_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  config_id UUID REFERENCES scanning_configs(config_id) ON DELETE CASCADE,
  source_name TEXT NOT NULL,
  -- Source-specific parameter overrides (JSON for flexibility)
  parameter_overrides JSONB DEFAULT '{}',
  -- Source-specific performance metrics
  last_run_at TIMESTAMPTZ,
  success_rate NUMERIC(5,4) DEFAULT 0,
  avg_matches_per_run NUMERIC(8,2) DEFAULT 0,
  is_enabled BOOLEAN DEFAULT TRUE,
  UNIQUE(config_id, source_name)
);

-- Configuration performance history for A/B testing and optimization
CREATE TABLE IF NOT EXISTS config_performance_log (
  log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  config_id UUID REFERENCES scanning_configs(config_id) ON DELETE CASCADE,
  source_name TEXT,
  test_date DATE NOT NULL,
  jobs_found INT DEFAULT 0,
  matches_generated INT DEFAULT 0,
  quality_score NUMERIC(5,4),
  consultant_interest_rate NUMERIC(5,4),
  placement_rate NUMERIC(5,4),
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Adaptive learning parameters tracking
CREATE TABLE IF NOT EXISTS learning_parameters (
  param_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  parameter_name TEXT NOT NULL,
  parameter_value TEXT NOT NULL,
  effectiveness_score NUMERIC(5,4) DEFAULT 0,
  usage_count INT DEFAULT 0,
  last_used_at TIMESTAMPTZ,
  learned_from_config_id UUID REFERENCES scanning_configs(config_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(parameter_name, parameter_value)
);

CREATE INDEX IF NOT EXISTS idx_jobs_posted_at ON jobs(posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_source   ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_jobs_company  ON jobs(company_id);
CREATE INDEX IF NOT EXISTS idx_jobs_broker   ON jobs(broker_id);
CREATE INDEX IF NOT EXISTS idx_jobs_gin_skills        ON jobs USING GIN (skills);
CREATE INDEX IF NOT EXISTS idx_consultants_gin_skills ON consultants USING GIN (skills);
CREATE INDEX IF NOT EXISTS idx_jobemb_vec       ON job_embeddings USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_consultantemb_vec ON consultant_embeddings USING hnsw (embedding vector_cosine_ops);

-- Indexes for scanning configuration system
CREATE INDEX IF NOT EXISTS idx_scanning_configs_active ON scanning_configs(is_active);
CREATE INDEX IF NOT EXISTS idx_scanning_configs_performance ON scanning_configs(performance_score DESC);
CREATE INDEX IF NOT EXISTS idx_source_overrides_config ON source_config_overrides(config_id);
CREATE INDEX IF NOT EXISTS idx_source_overrides_source ON source_config_overrides(source_name);
CREATE INDEX IF NOT EXISTS idx_config_performance_log_date ON config_performance_log(test_date DESC);
CREATE INDEX IF NOT EXISTS idx_config_performance_log_config ON config_performance_log(config_id);
CREATE INDEX IF NOT EXISTS idx_learning_params_name ON learning_parameters(parameter_name);
CREATE INDEX IF NOT EXISTS idx_learning_params_effectiveness ON learning_parameters(effectiveness_score DESC);