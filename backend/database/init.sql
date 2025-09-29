-- PyBOG Database Schema
-- Complete schema with all required tables

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    state TEXT DEFAULT 'idle',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    type TEXT NOT NULL, -- 'user', 'assistant', 'system', 'error'
    content TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    UNIQUE(message_id)
);

-- Session files table (legacy)
CREATE TABLE IF NOT EXISTS session_files (
    file_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    message_id TEXT,
    filename TEXT NOT NULL,
    mime_type TEXT,
    file_size BIGINT,
    file_path TEXT NOT NULL,
    uploaded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Unified files table (preferred)
CREATE TABLE IF NOT EXISTS files (
    file_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    message_id TEXT,
    filename TEXT NOT NULL,
    file_type TEXT,
    file_size BIGINT,
    storage_path TEXT NOT NULL,
    metadata JSONB,
    upload_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_files_session_id ON files(session_id);
CREATE INDEX IF NOT EXISTS idx_files_upload_time ON files(upload_time DESC);

-- Analysis table
CREATE TABLE IF NOT EXISTS analysis (
    session_id TEXT PRIMARY KEY REFERENCES sessions(session_id) ON DELETE CASCADE,
    state TEXT DEFAULT 'pending',
    data JSONB,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- BOG files table
CREATE TABLE IF NOT EXISTS bog_files (
    bog_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_session_files_session_id ON session_files(session_id);
CREATE INDEX IF NOT EXISTS idx_session_files_message_id ON session_files(message_id);
CREATE INDEX IF NOT EXISTS idx_bog_files_session_id ON bog_files(session_id);

-- Update trigger for sessions.updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_sessions_updated_at 
    BEFORE UPDATE ON sessions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Additional tables required by n8n workflow nodes
-- Compatibility table for analysis state storage from n8n
CREATE TABLE IF NOT EXISTS hvac_analysis_state (
    session_id TEXT PRIMARY KEY REFERENCES sessions(session_id) ON DELETE CASCADE,
    analysis_data JSONB,
    state TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Compatibility table for logging messages from n8n
CREATE TABLE IF NOT EXISTS session_messages (
    message_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    role TEXT,
    message_type TEXT,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_session_messages_session_id ON session_messages(session_id);
