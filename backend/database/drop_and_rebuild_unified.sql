-- DANGER: Destructive migration. Drops and recreates public schema objects for PyBOG.
-- Canonical PK is session_id across the system.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Drop views first (if exist)
DROP VIEW IF EXISTS unified_messages CASCADE;
DROP VIEW IF EXISTS unified_bog_files CASCADE;
DROP VIEW IF EXISTS session_overview CASCADE;
DROP VIEW IF EXISTS active_workflows CASCADE;
DROP VIEW IF EXISTS session_summary CASCADE;

-- Drop tables used by app/workflows (order matters)
DROP TABLE IF EXISTS document_embeddings CASCADE;
DROP TABLE IF EXISTS hvac_components CASCADE;
DROP TABLE IF EXISTS approval_history CASCADE;
DROP TABLE IF EXISTS workflow_executions CASCADE;
DROP TABLE IF EXISTS conversation_history CASCADE;
DROP TABLE IF EXISTS document_sessions CASCADE;

DROP TABLE IF EXISTS session_bog_files CASCADE;
DROP TABLE IF EXISTS hvac_analysis_state CASCADE;
DROP TABLE IF EXISTS session_messages CASCADE;
DROP TABLE IF EXISTS session_files CASCADE;

DROP TABLE IF EXISTS bog_files CASCADE;
DROP TABLE IF EXISTS analysis_results CASCADE;
DROP TABLE IF EXISTS files CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS hvac_chat_memory CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;

-- Recreate core tables
CREATE TABLE sessions (
  session_id VARCHAR(255) PRIMARY KEY,
  name VARCHAR(255) NOT NULL DEFAULT 'New Session',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  last_activity TIMESTAMPTZ DEFAULT NOW(),
  state VARCHAR(50) DEFAULT 'idle',
  metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id VARCHAR(255) UNIQUE NOT NULL,
  session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  type VARCHAR(50) NOT NULL CHECK (type IN ('user','assistant','system')),
  message_type VARCHAR(50),
  content TEXT NOT NULL,
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE files (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  file_id VARCHAR(255) UNIQUE NOT NULL,
  session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  message_id VARCHAR(255),
  filename VARCHAR(255) NOT NULL,
  file_type VARCHAR(100),
  file_size BIGINT,
  storage_path TEXT,
  upload_time TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE analysis_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id VARCHAR(255) UNIQUE NOT NULL,
  session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  message_id VARCHAR(255),
  analysis_data JSONB NOT NULL,
  status VARCHAR(50) DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE bog_files (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bog_id VARCHAR(255) UNIQUE NOT NULL,
  session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  message_id VARCHAR(255),
  filename VARCHAR(255) NOT NULL,
  file_path TEXT,
  download_url TEXT,
  content JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'::jsonb
);

-- Legacy/workflow compatibility tables
CREATE TABLE session_messages (
  id SERIAL PRIMARY KEY,
  session_id VARCHAR(255) REFERENCES sessions(session_id) ON DELETE CASCADE,
  message_id VARCHAR(255) UNIQUE NOT NULL,
  type VARCHAR(50) NOT NULL,
  content TEXT NOT NULL,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE hvac_analysis_state (
  id SERIAL PRIMARY KEY,
  session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  state VARCHAR(50) NOT NULL DEFAULT 'processing',
  analysis_data JSONB,
  bog_data JSONB,
  feedback TEXT,
  message_id VARCHAR(255),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE session_bog_files (
  id SERIAL PRIMARY KEY,
  session_id VARCHAR(255) REFERENCES sessions(session_id) ON DELETE CASCADE,
  analysis_id INTEGER REFERENCES hvac_analysis_state(id),
  bog_name VARCHAR(255) NOT NULL,
  file_path TEXT NOT NULL,
  download_url TEXT,
  generated_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'::jsonb
);

-- Legacy file registry (used by upload endpoint)
CREATE TABLE session_files (
  id SERIAL PRIMARY KEY,
  session_id VARCHAR(255) REFERENCES sessions(session_id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  mime_type TEXT,
  size BIGINT,
  path TEXT,
  uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

-- n8n chat memory table (used by get_session_state)
CREATE TABLE hvac_chat_memory (
  id SERIAL PRIMARY KEY,
  session_id VARCHAR(255) NOT NULL,
  role VARCHAR(50),
  content TEXT,
  state VARCHAR(50),
  data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_sessions_session_id ON sessions(session_id);
CREATE INDEX idx_sessions_updated_at ON sessions(updated_at DESC);
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp DESC);
CREATE INDEX idx_files_session_id ON files(session_id);
CREATE INDEX idx_analysis_session_id ON analysis_results(session_id);
CREATE INDEX idx_bog_files_session_id ON bog_files(session_id);
CREATE INDEX idx_session_messages ON session_messages(session_id, created_at);
CREATE INDEX idx_hvac_analysis_state ON hvac_analysis_state(session_id, updated_at DESC);

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_sessions_updated_at ON sessions;
CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_hvac_analysis_updated_at ON hvac_analysis_state;
CREATE TRIGGER update_hvac_analysis_updated_at BEFORE UPDATE ON hvac_analysis_state
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_analysis_updated_at ON analysis_results;
CREATE TRIGGER update_analysis_updated_at BEFORE UPDATE ON analysis_results
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Views
CREATE OR REPLACE VIEW unified_messages AS
SELECT 
  COALESCE(m.message_id, sm.message_id) AS message_id,
  COALESCE(m.session_id, sm.session_id) AS session_id,
  COALESCE(m.type, sm.type) AS type,
  m.message_type,
  COALESCE(m.content, sm.content) AS content,
  COALESCE(m.timestamp, sm.created_at) AS timestamp,
  COALESCE(m.metadata, sm.metadata) AS metadata
FROM messages m
FULL OUTER JOIN session_messages sm ON m.message_id = sm.message_id;

CREATE OR REPLACE VIEW unified_bog_files AS
SELECT 
  COALESCE(bf.bog_id, CAST(sbf.id AS VARCHAR)) AS bog_id,
  COALESCE(bf.session_id, sbf.session_id) AS session_id,
  COALESCE(bf.filename, sbf.bog_name) AS filename,
  COALESCE(bf.file_path, sbf.file_path) AS file_path,
  COALESCE(bf.download_url, sbf.download_url) AS download_url,
  COALESCE(bf.created_at, sbf.generated_at) AS created_at,
  COALESCE(bf.metadata, sbf.metadata) AS metadata
FROM bog_files bf
FULL OUTER JOIN session_bog_files sbf
  ON bf.session_id = sbf.session_id AND bf.file_path = sbf.file_path;

CREATE OR REPLACE VIEW session_overview AS
SELECT 
  s.session_id,
  s.name,
  s.state,
  s.created_at,
  s.updated_at,
  s.last_activity,
  COUNT(DISTINCT m.message_id) AS message_count,
  COUNT(DISTINCT f.file_id) AS file_count,
  COUNT(DISTINCT a.analysis_id) AS analysis_count,
  COUNT(DISTINCT b.bog_id) AS bog_count
FROM sessions s
LEFT JOIN messages m ON s.session_id = m.session_id
LEFT JOIN files f ON s.session_id = f.session_id
LEFT JOIN analysis_results a ON s.session_id = a.session_id
LEFT JOIN bog_files b ON s.session_id = b.session_id
GROUP BY s.session_id, s.name, s.state, s.created_at, s.updated_at, s.last_activity;
