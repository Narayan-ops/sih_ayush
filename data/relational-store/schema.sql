-- IP-SAKTI Sahayak: immutable operational records.
-- This schema is deliberately append-only for audit and consent events.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    jurisdiction TEXT NOT NULL CHECK (jurisdiction IN ('india', 'international')),
    provider TEXT NOT NULL DEFAULT 'self_hosted' CHECK (provider = 'self_hosted'),
    classification_state JSONB,
    original_query TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS consent_log (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(session_id),
    provider TEXT NOT NULL,
    consented BOOLEAN NOT NULL,
    consent_type TEXT NOT NULL,
    scope TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(session_id),
    query TEXT NOT NULL,
    retrieved_chunk_ids JSONB NOT NULL,
    model_version TEXT NOT NULL,
    provider_used TEXT NOT NULL,
    corpus_version TEXT NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS escalation_log (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(session_id),
    escalation_type TEXT NOT NULL,
    reason TEXT NOT NULL,
    facilitator_id TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS audit_log_session_timestamp_idx ON audit_log (session_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS consent_log_session_timestamp_idx ON consent_log (session_id, timestamp DESC);
