-- PyBOG FastAPI Unified Database Schema
-- Clean schema for FastAPI backend replacing n8n workflows
-- Supports sessions, chat history, file storage (BYTEA + file_path), and analysis

-- ==================== Core Session Management ====================

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==================== Chat History and Conversations ====================

CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    session_id TEXT REFERENCES sessions(session_id) ON DELETE CASCADE,
    message_type TEXT NOT NULL CHECK (message_type IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==================== File Storage (Hybrid BYTEA + File Path) ====================

CREATE TABLE IF NOT EXISTS files (
    id SERIAL PRIMARY KEY,
    session_id TEXT REFERENCES sessions(session_id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    original_name TEXT NOT NULL,
    mime_type TEXT,
    file_type TEXT NOT NULL CHECK (file_type IN ('upload', 'bog', 'analysis', 'document')),
    file_data BYTEA, -- File content for files <10MB, NULL for larger files with file_path
    file_path TEXT, -- Fallback for larger files stored on disk
    file_size BIGINT NOT NULL,
    state TEXT NOT NULL DEFAULT 'queued' CHECK (state IN ('queued', 'processing', 'finalizing', 'complete', 'failed')),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    archived_at TIMESTAMPTZ -- For cleanup strategy: Archive BYTEA data after 30 days, purge after 90 days
);

-- ==================== Analysis Results with State Machine ====================

CREATE TABLE IF NOT EXISTS analysis_results (
    id SERIAL PRIMARY KEY,
    session_id TEXT REFERENCES sessions(session_id) ON DELETE CASCADE,
    input_file_id INTEGER REFERENCES files(id),
    bog_file_id INTEGER REFERENCES files(id),
    state TEXT NOT NULL DEFAULT 'queued' CHECK (state IN ('queued', 'processing', 'finalizing', 'complete', 'failed')),
    analysis_data JSONB NOT NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ==================== Indexes for Performance ====================

-- Session indexes
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at DESC);

-- Chat message indexes
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_type ON chat_messages(message_type);

-- File indexes
CREATE INDEX IF NOT EXISTS idx_files_session_id ON files(session_id);
CREATE INDEX IF NOT EXISTS idx_files_state ON files(state);
CREATE INDEX IF NOT EXISTS idx_files_file_type ON files(file_type);
CREATE INDEX IF NOT EXISTS idx_files_created_at ON files(created_at DESC);

-- File cleanup indexes (critical for retention strategy)
CREATE INDEX IF NOT EXISTS idx_files_cleanup ON files(created_at, archived_at) WHERE file_data IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_files_archive_candidates ON files(created_at) WHERE file_data IS NOT NULL AND archived_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_files_purge_candidates ON files(archived_at) WHERE archived_at IS NOT NULL;

-- Analysis result indexes
CREATE INDEX IF NOT EXISTS idx_analysis_session_id ON analysis_results(session_id);
CREATE INDEX IF NOT EXISTS idx_analysis_state ON analysis_results(state);
CREATE INDEX IF NOT EXISTS idx_analysis_input_file ON analysis_results(input_file_id);
CREATE INDEX IF NOT EXISTS idx_analysis_bog_file ON analysis_results(bog_file_id);
CREATE INDEX IF NOT EXISTS idx_analysis_created_at ON analysis_results(created_at DESC);

-- ==================== Triggers ====================

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update trigger to sessions table
DROP TRIGGER IF EXISTS update_sessions_updated_at ON sessions;
CREATE TRIGGER update_sessions_updated_at 
    BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==================== Views for Common Queries ====================

-- Session overview with file and analysis counts
CREATE OR REPLACE VIEW session_overview AS
SELECT 
    s.session_id,
    s.name,
    s.created_at,
    s.updated_at,
    COUNT(DISTINCT cm.id) as message_count,
    COUNT(DISTINCT f.id) as file_count,
    COUNT(DISTINCT CASE WHEN f.file_type = 'upload' THEN f.id END) as upload_count,
    COUNT(DISTINCT CASE WHEN f.file_type = 'bog' THEN f.id END) as bog_count,
    COUNT(DISTINCT ar.id) as analysis_count,
    COUNT(DISTINCT CASE WHEN ar.state = 'complete' THEN ar.id END) as completed_analysis_count,
    COUNT(DISTINCT CASE WHEN ar.state IN ('queued', 'processing', 'finalizing') THEN ar.id END) as active_analysis_count,
    s.metadata
FROM sessions s
LEFT JOIN chat_messages cm ON s.session_id = cm.session_id
LEFT JOIN files f ON s.session_id = f.session_id
LEFT JOIN analysis_results ar ON s.session_id = ar.session_id
GROUP BY s.session_id, s.name, s.created_at, s.updated_at, s.metadata
ORDER BY s.updated_at DESC;

-- Active analysis processes
CREATE OR REPLACE VIEW active_analysis AS
SELECT 
    ar.id,
    ar.session_id,
    ar.state,
    ar.created_at,
    s.name as session_name,
    f_input.filename as input_filename,
    f_input.file_size as input_file_size,
    f_bog.filename as bog_filename
FROM analysis_results ar
JOIN sessions s ON ar.session_id = s.session_id
LEFT JOIN files f_input ON ar.input_file_id = f_input.id
LEFT JOIN files f_bog ON ar.bog_file_id = f_bog.id
WHERE ar.state IN ('queued', 'processing', 'finalizing')
ORDER BY ar.created_at ASC;

-- File cleanup candidates
CREATE OR REPLACE VIEW file_cleanup_candidates AS
SELECT 
    id,
    session_id,
    filename,
    file_size,
    created_at,
    archived_at,
    CASE 
        WHEN archived_at IS NULL AND created_at < NOW() - INTERVAL '30 days' THEN 'archive'
        WHEN archived_at IS NOT NULL AND archived_at < NOW() - INTERVAL '90 days' THEN 'purge'
        ELSE 'keep'
    END as cleanup_action,
    CASE 
        WHEN archived_at IS NULL THEN EXTRACT(DAYS FROM NOW() - created_at)
        ELSE EXTRACT(DAYS FROM NOW() - archived_at)
    END as days_old
FROM files 
WHERE file_data IS NOT NULL
ORDER BY created_at ASC;

-- ==================== Functions for File Management ====================

-- Function to get file storage type
CREATE OR REPLACE FUNCTION get_file_storage_type(file_id INTEGER)
RETURNS TEXT AS $$
DECLARE
    has_bytea BOOLEAN;
    has_path BOOLEAN;
BEGIN
    SELECT 
        file_data IS NOT NULL,
        file_path IS NOT NULL
    INTO has_bytea, has_path
    FROM files 
    WHERE id = file_id;
    
    IF has_bytea THEN
        RETURN 'bytea';
    ELSIF has_path THEN
        RETURN 'file_path';
    ELSE
        RETURN 'none';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to archive old BYTEA files (sets archived_at timestamp)
CREATE OR REPLACE FUNCTION archive_old_bytea_files(threshold_days INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    UPDATE files 
    SET archived_at = NOW()
    WHERE file_data IS NOT NULL 
      AND archived_at IS NULL
      AND created_at < NOW() - (threshold_days || ' days')::INTERVAL;
    
    GET DIAGNOSTICS archived_count = ROW_COUNT;
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;

-- Function to purge archived files (removes BYTEA data)
CREATE OR REPLACE FUNCTION purge_archived_files(threshold_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    purged_count INTEGER;
BEGIN
    UPDATE files 
    SET file_data = NULL
    WHERE file_data IS NOT NULL 
      AND archived_at IS NOT NULL
      AND archived_at < NOW() - (threshold_days || ' days')::INTERVAL;
    
    GET DIAGNOSTICS purged_count = ROW_COUNT;
    RETURN purged_count;
END;
$$ LANGUAGE plpgsql;

-- ==================== Sample Data for Testing ====================

-- Insert a sample session for testing
INSERT INTO sessions (session_id, name, metadata) 
VALUES ('test-session-1', 'Test Session', '{"created_by": "system", "purpose": "testing"}')
ON CONFLICT (session_id) DO NOTHING;

-- Insert sample chat messages
INSERT INTO chat_messages (session_id, message_type, content, metadata)
VALUES 
    ('test-session-1', 'user', 'Hello, I need help analyzing an HVAC document.', '{}'),
    ('test-session-1', 'assistant', 'I''d be happy to help you analyze your HVAC document. Please upload the file and I''ll get started.', '{}')
ON CONFLICT DO NOTHING;

-- ==================== Permissions ====================

-- Grant permissions to pybog user
GRANT ALL ON ALL TABLES IN SCHEMA public TO pybog;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO pybog;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO pybog;
GRANT USAGE ON SCHEMA public TO pybog;