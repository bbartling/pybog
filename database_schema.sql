-- PyBOG HVAC analysis state table required by corrected n8n workflows
CREATE TABLE IF NOT EXISTS hvac_analysis_state (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    state VARCHAR(50) NOT NULL DEFAULT 'processing',
    analysis_data JSONB,
    bog_data JSONB,
    feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_session_state ON hvac_analysis_state(session_id, state);
CREATE INDEX IF NOT EXISTS idx_updated_at ON hvac_analysis_state(updated_at DESC);

-- Enhanced sessions table adjustments
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS name VARCHAR(255) DEFAULT 'New Session';
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS current_state VARCHAR(50) DEFAULT 'idle';
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Unified chat messages (combines frontend + n8n histories)
CREATE TABLE IF NOT EXISTS session_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES sessions(session_id) ON DELETE CASCADE,
    message_id VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Link analysis to messages
ALTER TABLE hvac_analysis_state ADD COLUMN IF NOT EXISTS message_id VARCHAR(255);

-- BOG file tracking
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

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_session_messages ON session_messages(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_bog_files_session ON session_bog_files(session_id, generated_at);
CREATE INDEX IF NOT EXISTS idx_sessions_activity ON sessions(last_activity DESC);

