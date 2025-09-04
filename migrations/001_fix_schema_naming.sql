-- Migration 001: Fix Schema Naming Issues and Add Indexes
-- Purpose: Standardize column names to snake_case and add performance indexes

-- Start transaction for atomic changes
BEGIN;

-- 1. Drop the duplicate camelCase column if it exists
ALTER TABLE hvac_chat_memory DROP COLUMN IF EXISTS "sessionId";

-- 2. Ensure session_id column exists and is properly typed
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'hvac_chat_memory' 
        AND column_name = 'session_id'
    ) THEN
        ALTER TABLE hvac_chat_memory ADD COLUMN session_id TEXT NOT NULL DEFAULT '';
    END IF;
END$$;

-- 3. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_hvac_chat_memory_session_id 
    ON hvac_chat_memory(session_id);

CREATE INDEX IF NOT EXISTS idx_hvac_chat_memory_session_state 
    ON hvac_chat_memory(session_id, state);

CREATE INDEX IF NOT EXISTS idx_hvac_chat_memory_created_at 
    ON hvac_chat_memory(created_at DESC);

-- 4. Create indexes on hvac_files table
CREATE INDEX IF NOT EXISTS idx_hvac_files_session_id 
    ON hvac_files(session_id);

CREATE INDEX IF NOT EXISTS idx_hvac_files_created_at 
    ON hvac_files(created_at DESC);

-- 5. Add missing columns if they don't exist
ALTER TABLE hvac_chat_memory 
    ADD COLUMN IF NOT EXISTS human_message TEXT,
    ADD COLUMN IF NOT EXISTS ai_message TEXT,
    ADD COLUMN IF NOT EXISTS data JSONB,
    ADD COLUMN IF NOT EXISTS result_data JSONB,
    ADD COLUMN IF NOT EXISTS state TEXT NOT NULL DEFAULT 'new',
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- 6. Create a trigger to auto-update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_hvac_chat_memory_updated_at ON hvac_chat_memory;

CREATE TRIGGER update_hvac_chat_memory_updated_at
    BEFORE UPDATE ON hvac_chat_memory
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 7. Standardize any existing data
UPDATE hvac_chat_memory 
SET session_id = COALESCE(session_id, '')
WHERE session_id IS NULL;

-- 8. Add NOT NULL constraint after data is cleaned
ALTER TABLE hvac_chat_memory 
    ALTER COLUMN session_id SET NOT NULL;

COMMIT;

-- Verify the schema changes
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'hvac_chat_memory'
ORDER BY ordinal_position;
