-- PyBOG Unified Database Schema
-- Comprehensive schema supporting n8n workflows and frontend requirements

-- ==================== Core Session Management ====================

CREATE TABLE IF NOT EXISTS sessions (
    id UUID DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) UNIQUE NOT NULL PRIMARY KEY,
    name VARCHAR(255) NOT NULL DEFAULT 'New Session',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    state VARCHAR(50) DEFAULT 'idle',
    metadata JSONB DEFAULT '{}'::jsonb
);

-- ==================== Message System ====================

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id VARCHAR(255) UNIQUE NOT NULL,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL CHECK (type IN ('user', 'assistant', 'system')),
    message_type VARCHAR(50) CHECK (message_type IN ('status', 'analysis', 'artifact', 'processing', 'error', 'approval', 'workflow')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- ==================== File Management ====================

CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id VARCHAR(255) UNIQUE NOT NULL,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    message_id VARCHAR(255) REFERENCES messages(message_id) ON DELETE SET NULL,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(100),
    file_size BIGINT,
    storage_path TEXT,
    upload_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- ==================== Analysis System ====================

CREATE TABLE IF NOT EXISTS analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id VARCHAR(255) UNIQUE NOT NULL,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    message_id VARCHAR(255) REFERENCES messages(message_id) ON DELETE SET NULL,
    analysis_data JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'awaiting_review', 'approved', 'rejected', 'complete')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==================== BOG Generation ====================

CREATE TABLE IF NOT EXISTS bog_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bog_id VARCHAR(255) UNIQUE NOT NULL,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    message_id VARCHAR(255) REFERENCES messages(message_id) ON DELETE SET NULL,
    filename VARCHAR(255) NOT NULL,
    file_path TEXT,
    download_url TEXT,
    content JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- ==================== N8N Workflow Tables ====================

-- Document ingestion sessions (from n8n workflows)
CREATE TABLE IF NOT EXISTS document_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    document_name VARCHAR(500),
    document_path TEXT,
    extracted_text TEXT,
    extraction_method VARCHAR(100),
    processing_status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Conversation history (from n8n chat workflow)
CREATE TABLE IF NOT EXISTS conversation_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    message_id VARCHAR(255) UNIQUE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'function')),
    content TEXT NOT NULL,
    function_name VARCHAR(255),
    function_response TEXT,
    tokens_used INTEGER,
    model_used VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Document embeddings (for semantic search)
CREATE TABLE IF NOT EXISTS document_embeddings (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    document_session_id INTEGER REFERENCES document_sessions(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(1536), -- OpenAI embedding dimension
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- HVAC components extracted from documents
CREATE TABLE IF NOT EXISTS hvac_components (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    analysis_id VARCHAR(255) REFERENCES analysis_results(analysis_id) ON DELETE CASCADE,
    component_type VARCHAR(100) NOT NULL,
    component_name VARCHAR(255) NOT NULL,
    model VARCHAR(255),
    specifications JSONB,
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    location TEXT,
    relationships JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Workflow execution tracking
CREATE TABLE IF NOT EXISTS workflow_executions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    execution_id VARCHAR(255) UNIQUE NOT NULL,
    workflow_id VARCHAR(255) NOT NULL,
    workflow_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'running' CHECK (status IN ('running', 'waiting', 'completed', 'failed', 'cancelled')),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    resume_url TEXT,
    wait_node_id VARCHAR(255),
    wait_node_name VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Approval tracking
CREATE TABLE IF NOT EXISTS approval_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    execution_id VARCHAR(255) REFERENCES workflow_executions(execution_id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL CHECK (action IN ('approve', 'reject', 'modify')),
    feedback TEXT,
    modifications JSONB,
    approved_by VARCHAR(255),
    approved_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- ==================== Indexes for Performance ====================

-- Session indexes
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_state ON sessions(state);

-- Message indexes
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(type, message_type);

-- File indexes
CREATE INDEX IF NOT EXISTS idx_files_session_id ON files(session_id);
CREATE INDEX IF NOT EXISTS idx_files_message_id ON files(message_id);

-- Analysis indexes
CREATE INDEX IF NOT EXISTS idx_analysis_session_id ON analysis_results(session_id);
CREATE INDEX IF NOT EXISTS idx_analysis_status ON analysis_results(status);

-- BOG file indexes
CREATE INDEX IF NOT EXISTS idx_bog_files_session_id ON bog_files(session_id);

-- Document session indexes
CREATE INDEX IF NOT EXISTS idx_document_sessions_session_id ON document_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_document_sessions_status ON document_sessions(processing_status);

-- Conversation history indexes
CREATE INDEX IF NOT EXISTS idx_conversation_history_session_id ON conversation_history(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_created_at ON conversation_history(created_at DESC);

-- Embedding indexes (for similarity search)
CREATE INDEX IF NOT EXISTS idx_embeddings_session_id ON document_embeddings(session_id);
-- CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON document_embeddings USING ivfflat (embedding vector_cosine_ops);

-- HVAC component indexes
CREATE INDEX IF NOT EXISTS idx_hvac_components_session_id ON hvac_components(session_id);
CREATE INDEX IF NOT EXISTS idx_hvac_components_type ON hvac_components(component_type);

-- Workflow execution indexes
CREATE INDEX IF NOT EXISTS idx_workflow_executions_session_id ON workflow_executions(session_id);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_status ON workflow_executions(status);

-- Approval history indexes
CREATE INDEX IF NOT EXISTS idx_approval_history_session_id ON approval_history(session_id);
CREATE INDEX IF NOT EXISTS idx_approval_history_execution_id ON approval_history(execution_id);

-- ==================== Triggers ====================

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update trigger to relevant tables
CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_analysis_updated_at BEFORE UPDATE ON analysis_results
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_document_sessions_updated_at BEFORE UPDATE ON document_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==================== Views ====================

-- Unified session view with all related counts
CREATE OR REPLACE VIEW session_overview AS
SELECT 
    s.session_id,
    s.name,
    s.state,
    s.created_at,
    s.updated_at,
    s.last_activity,
    COUNT(DISTINCT m.message_id) as message_count,
    COUNT(DISTINCT f.file_id) as file_count,
    COUNT(DISTINCT a.analysis_id) as analysis_count,
    COUNT(DISTINCT b.bog_id) as bog_count,
    COUNT(DISTINCT ds.id) as document_count,
    COUNT(DISTINCT we.execution_id) as workflow_count,
    MAX(we.status = 'waiting') as has_waiting_workflow,
    s.metadata
FROM sessions s
LEFT JOIN messages m ON s.session_id = m.session_id
LEFT JOIN files f ON s.session_id = f.session_id
LEFT JOIN analysis_results a ON s.session_id = a.session_id
LEFT JOIN bog_files b ON s.session_id = b.session_id
LEFT JOIN document_sessions ds ON s.session_id = ds.session_id
LEFT JOIN workflow_executions we ON s.session_id = we.session_id
GROUP BY s.session_id, s.name, s.state, s.created_at, s.updated_at, s.last_activity, s.metadata;

-- Active workflows view
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
    s.state as session_state
FROM workflow_executions we
JOIN sessions s ON we.session_id = s.session_id
WHERE we.status IN ('running', 'waiting');

-- ==================== Permissions ====================

GRANT ALL ON ALL TABLES IN SCHEMA public TO pybog;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO pybog;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO pybog;
