-- Migration script to unify the new schema with existing n8n workflow requirements
-- This ensures backward compatibility with n8n workflows while supporting new features

-- 1. First ensure sessions table exists with both old and new fields
CREATE TABLE IF NOT EXISTS sessions (
    id UUID DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) UNIQUE NOT NULL PRIMARY KEY,
    name VARCHAR(255) NOT NULL DEFAULT 'New Session',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    current_state VARCHAR(50) DEFAULT 'idle', -- n8n expects this
    state VARCHAR(50) DEFAULT 'idle', -- new schema field
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 2. Create hvac_analysis_state table for n8n compatibility
CREATE TABLE IF NOT EXISTS hvac_analysis_state (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    state VARCHAR(50) NOT NULL DEFAULT 'processing',
    analysis_data JSONB,
    bog_data JSONB,
    feedback TEXT,
    message_id VARCHAR(255), -- Link to messages
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create session_messages table (n8n expects this exact name)
CREATE TABLE IF NOT EXISTS session_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES sessions(session_id) ON DELETE CASCADE,
    message_id VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Create unified messages table (new schema)
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id VARCHAR(255) UNIQUE NOT NULL,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL CHECK (type IN ('user', 'assistant', 'system')),
    message_type VARCHAR(50),
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 5. Create session_bog_files table (n8n expects this)
CREATE TABLE IF NOT EXISTS session_bog_files (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES sessions(session_id) ON DELETE CASCADE,
    analysis_id INTEGER REFERENCES hvac_analysis_state(id),
    bog_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    download_url TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 6. Create bog_files table (new schema)
CREATE TABLE IF NOT EXISTS bog_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bog_id VARCHAR(255) UNIQUE NOT NULL,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    message_id VARCHAR(255),
    filename VARCHAR(255) NOT NULL,
    file_path TEXT,
    download_url TEXT,
    content JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 7. Create files table for uploads
CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id VARCHAR(255) UNIQUE NOT NULL,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    message_id VARCHAR(255),
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(100),
    file_size BIGINT,
    storage_path TEXT,
    upload_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 8. Create analysis_results table (new schema, coexists with hvac_analysis_state)
CREATE TABLE IF NOT EXISTS analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id VARCHAR(255) UNIQUE NOT NULL,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    message_id VARCHAR(255),
    analysis_data JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 9. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_activity ON sessions(last_activity DESC);
CREATE INDEX IF NOT EXISTS idx_session_state ON hvac_analysis_state(session_id, state);
CREATE INDEX IF NOT EXISTS idx_hvac_updated_at ON hvac_analysis_state(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_session_messages ON session_messages(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_files_session_id ON files(session_id);
CREATE INDEX IF NOT EXISTS idx_bog_files_session ON session_bog_files(session_id, generated_at);
CREATE INDEX IF NOT EXISTS idx_analysis_session_id ON analysis_results(session_id);

-- 10. Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_sessions_updated_at ON sessions;
CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_hvac_analysis_updated_at ON hvac_analysis_state;
CREATE TRIGGER update_hvac_analysis_updated_at BEFORE UPDATE ON hvac_analysis_state
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_analysis_updated_at ON analysis_results;
CREATE TRIGGER update_analysis_updated_at BEFORE UPDATE ON analysis_results
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 11. Create view that unifies both message tables for querying
CREATE OR REPLACE VIEW unified_messages AS
SELECT 
    COALESCE(m.message_id, sm.message_id) as message_id,
    COALESCE(m.session_id, sm.session_id) as session_id,
    COALESCE(m.type, sm.type) as type,
    m.message_type,
    COALESCE(m.content, sm.content) as content,
    COALESCE(m.timestamp, sm.created_at) as timestamp,
    COALESCE(m.metadata, sm.metadata) as metadata
FROM messages m
FULL OUTER JOIN session_messages sm ON m.message_id = sm.message_id;

-- 12. Create view that unifies BOG files from both tables
CREATE OR REPLACE VIEW unified_bog_files AS
SELECT 
    COALESCE(bf.bog_id, CAST(sbf.id AS VARCHAR)) as bog_id,
    COALESCE(bf.session_id, sbf.session_id) as session_id,
    COALESCE(bf.filename, sbf.bog_name) as filename,
    COALESCE(bf.file_path, sbf.file_path) as file_path,
    COALESCE(bf.download_url, sbf.download_url) as download_url,
    COALESCE(bf.created_at, sbf.generated_at) as created_at,
    COALESCE(bf.metadata, sbf.metadata) as metadata
FROM bog_files bf
FULL OUTER JOIN session_bog_files sbf ON bf.session_id = sbf.session_id 
    AND bf.file_path = sbf.file_path;

-- 13. Create sync triggers to keep both message tables in sync
CREATE OR REPLACE FUNCTION sync_messages_to_session_messages()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO session_messages (session_id, message_id, type, content, metadata, created_at)
        VALUES (NEW.session_id, NEW.message_id, NEW.type, NEW.content, NEW.metadata, NEW.timestamp)
        ON CONFLICT (message_id) DO UPDATE
        SET content = EXCLUDED.content,
            metadata = EXCLUDED.metadata;
    ELSIF TG_OP = 'UPDATE' THEN
        UPDATE session_messages 
        SET content = NEW.content,
            metadata = NEW.metadata
        WHERE message_id = NEW.message_id;
    ELSIF TG_OP = 'DELETE' THEN
        DELETE FROM session_messages WHERE message_id = OLD.message_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS sync_messages_trigger ON messages;
CREATE TRIGGER sync_messages_trigger
AFTER INSERT OR UPDATE OR DELETE ON messages
FOR EACH ROW EXECUTE FUNCTION sync_messages_to_session_messages();

-- 14. Create sync trigger for BOG files
CREATE OR REPLACE FUNCTION sync_bog_files()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- Check if we need to create a session_bog_files entry
        INSERT INTO session_bog_files (session_id, bog_name, file_path, download_url, generated_at, metadata)
        VALUES (NEW.session_id, NEW.filename, NEW.file_path, NEW.download_url, NEW.created_at, NEW.metadata)
        ON CONFLICT DO NOTHING;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS sync_bog_files_trigger ON bog_files;
CREATE TRIGGER sync_bog_files_trigger
AFTER INSERT ON bog_files
FOR EACH ROW EXECUTE FUNCTION sync_bog_files();

-- 15. Grant appropriate permissions (adjust user as needed)
GRANT ALL ON ALL TABLES IN SCHEMA public TO pybog;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO pybog;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO pybog;
