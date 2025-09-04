-- Create the analysis state tracking table
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

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_session_state ON hvac_analysis_state(session_id, state);
CREATE INDEX IF NOT EXISTS idx_updated_at ON hvac_analysis_state(updated_at DESC);

-- Optional: Create chat memory table if not exists
CREATE TABLE IF NOT EXISTS hvac_chat_memory (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    message_id VARCHAR(255),
    role VARCHAR(50),
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

