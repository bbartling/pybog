-- Fix schema issues

-- Add state column to sessions if it doesn't exist
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS state VARCHAR(50) DEFAULT 'idle';

-- Create document_embeddings without vector type for now
CREATE TABLE IF NOT EXISTS document_embeddings (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    document_session_id INTEGER REFERENCES document_sessions(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding TEXT, -- Store as JSON text for now
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index
CREATE INDEX IF NOT EXISTS idx_embeddings_session_id ON document_embeddings(session_id);

-- Fix views
CREATE OR REPLACE VIEW session_overview AS
SELECT 
    s.session_id,
    s.name,
    COALESCE(s.state, 'idle') as state,
    s.created_at,
    s.updated_at,
    s.last_activity,
    COUNT(DISTINCT m.message_id) as message_count,
    COUNT(DISTINCT f.file_id) as file_count,
    COUNT(DISTINCT a.analysis_id) as analysis_count,
    COUNT(DISTINCT b.bog_id) as bog_count,
    COUNT(DISTINCT ds.id) as document_count,
    COUNT(DISTINCT we.execution_id) as workflow_count,
    BOOL_OR(we.status = 'waiting') as has_waiting_workflow,
    s.metadata
FROM sessions s
LEFT JOIN messages m ON s.session_id = m.session_id
LEFT JOIN files f ON s.session_id = f.session_id
LEFT JOIN analysis_results a ON s.session_id = a.session_id
LEFT JOIN bog_files b ON s.session_id = b.session_id
LEFT JOIN document_sessions ds ON s.session_id = ds.session_id
LEFT JOIN workflow_executions we ON s.session_id = we.session_id
GROUP BY s.session_id, s.name, s.state, s.created_at, s.updated_at, s.last_activity, s.metadata;

CREATE OR REPLACE VIEW active_workflows AS
SELECT 
    we.session_id,
    we.execution_id,
    we.workflow_name,
    we.status,
    we.started_at,
    we.resume_url,
    we.wait_node_name,
    s.name as session_name,
    COALESCE(s.state, 'idle') as session_state
FROM workflow_executions we
JOIN sessions s ON we.session_id = s.session_id
WHERE we.status IN ('running', 'waiting');
