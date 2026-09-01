-- IP-SAKTI Sahayak PostgreSQL migration. Safe to run repeatedly.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID,
    jurisdiction VARCHAR(20) NOT NULL CHECK (jurisdiction IN ('india', 'international')),
    formulation_class VARCHAR(50), provider TEXT NOT NULL DEFAULT 'self_hosted' CHECK (provider = 'self_hosted'),
    classification_state JSONB, original_query TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ
);
-- Upgrade the legacy session schema used by early builds.
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'self_hosted';
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS classification_state JSONB;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS original_query TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS audit_trail (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), session_id UUID REFERENCES sessions(session_id) ON DELETE SET NULL,
    corpus_version TEXT NOT NULL, chunk_ids TEXT[] NOT NULL DEFAULT '{}', model_version TEXT, provider_used TEXT,
    confidence_score VARCHAR(20), citation_count INTEGER NOT NULL DEFAULT 0, response_text TEXT, query_text TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb, timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE audit_trail ADD COLUMN IF NOT EXISTS query_text TEXT;

CREATE TABLE IF NOT EXISTS consent_logs (
    consent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    consent_type VARCHAR(50) NOT NULL, provider_name VARCHAR(100), scope TEXT NOT NULL, granted BOOLEAN NOT NULL DEFAULT true,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(), metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE IF NOT EXISTS escalation_log (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), session_id UUID NOT NULL REFERENCES sessions(session_id),
    escalation_type TEXT NOT NULL, reason TEXT NOT NULL, facilitator_id TEXT, timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS user_roles (user_id UUID PRIMARY KEY, role TEXT NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS audit_trail_session_timestamp_idx ON audit_trail (session_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS consent_logs_session_timestamp_idx ON consent_logs (session_id, timestamp DESC);
