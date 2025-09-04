-- Migration 002: Reset schema to final aligned model
-- WARNING: Destructive migration — drops and recreates tables

BEGIN;

-- Drop legacy objects
DROP TABLE IF EXISTS hvac_chat_memory CASCADE;
DROP TABLE IF EXISTS hvac_files CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column();

-- Final hvac_chat_memory schema: aligns with n8n memory and API
CREATE TABLE hvac_chat_memory (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'message',
    data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Files table for optional file persistence
CREATE TABLE hvac_files (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    file_name TEXT NOT NULL,
    mime_type TEXT,
    size BIGINT,
    content BYTEA,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_hvac_chat_memory_session_id 
    ON hvac_chat_memory(session_id);

CREATE INDEX IF NOT EXISTS idx_hvac_chat_memory_session_state 
    ON hvac_chat_memory(session_id, state);

CREATE INDEX IF NOT EXISTS idx_hvac_chat_memory_created_at 
    ON hvac_chat_memory(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_hvac_files_session_id 
    ON hvac_files(session_id);

CREATE INDEX IF NOT EXISTS idx_hvac_files_created_at 
    ON hvac_files(created_at DESC);

-- updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_hvac_chat_memory_updated_at
    BEFORE UPDATE ON hvac_chat_memory
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMIT;

