-- Create missing hvac_chat_memory table for compatibility

CREATE TABLE IF NOT EXISTS hvac_chat_memory (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    message JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_hvac_chat_memory_session ON hvac_chat_memory(session_id);
CREATE INDEX IF NOT EXISTS idx_hvac_chat_memory_created ON hvac_chat_memory(created_at DESC);
