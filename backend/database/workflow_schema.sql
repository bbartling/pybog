-- Workflow management schema for PyBOG backend
-- Stores workflow states, review items, and state transitions

-- Session workflows table
CREATE TABLE IF NOT EXISTS session_workflows (
    session_id VARCHAR(255) PRIMARY KEY,
    workflow_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for efficient workflow queries
CREATE INDEX IF NOT EXISTS idx_session_workflows_updated_at 
ON session_workflows(updated_at);

-- Index for workflow state queries
CREATE INDEX IF NOT EXISTS idx_session_workflows_state 
ON session_workflows USING GIN ((workflow_data->'current_state'));

-- Review items table (for detailed tracking and history)
CREATE TABLE IF NOT EXISTS review_items (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    review_type VARCHAR(50) NOT NULL,
    state VARCHAR(50) NOT NULL,
    review_data JSONB NOT NULL,
    user_feedback TEXT,
    decision VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

-- Indexes for review items
CREATE INDEX IF NOT EXISTS idx_review_items_session_id 
ON review_items(session_id);

CREATE INDEX IF NOT EXISTS idx_review_items_type_state 
ON review_items(review_type, state);

CREATE INDEX IF NOT EXISTS idx_review_items_created_at 
ON review_items(created_at);

-- Workflow state transitions table (for audit trail)
CREATE TABLE IF NOT EXISTS workflow_transitions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    from_state VARCHAR(50) NOT NULL,
    to_state VARCHAR(50) NOT NULL,
    trigger VARCHAR(100) NOT NULL,
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

-- Indexes for workflow transitions
CREATE INDEX IF NOT EXISTS idx_workflow_transitions_session_id 
ON workflow_transitions(session_id);

CREATE INDEX IF NOT EXISTS idx_workflow_transitions_timestamp 
ON workflow_transitions(timestamp);

CREATE INDEX IF NOT EXISTS idx_workflow_transitions_states 
ON workflow_transitions(from_state, to_state);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_workflow_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update updated_at on session_workflows
DROP TRIGGER IF EXISTS trigger_update_workflow_updated_at ON session_workflows;
CREATE TRIGGER trigger_update_workflow_updated_at
    BEFORE UPDATE ON session_workflows
    FOR EACH ROW
    EXECUTE FUNCTION update_workflow_updated_at();

-- View for active workflows with current state
CREATE OR REPLACE VIEW active_workflows AS
SELECT 
    session_id,
    workflow_data->>'current_state' as current_state,
    jsonb_array_length(workflow_data->'pending_reviews') as pending_reviews_count,
    jsonb_array_length(workflow_data->'completed_reviews') as completed_reviews_count,
    created_at,
    updated_at
FROM session_workflows
WHERE workflow_data->>'current_state' != 'idle'
  AND workflow_data->>'current_state' != 'complete'
  AND workflow_data->>'current_state' != 'failed';

-- View for workflow statistics
CREATE OR REPLACE VIEW workflow_stats AS
SELECT 
    workflow_data->>'current_state' as state,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_duration_seconds
FROM session_workflows
GROUP BY workflow_data->>'current_state';

-- Function to get workflow status
CREATE OR REPLACE FUNCTION get_workflow_status(p_session_id VARCHAR(255))
RETURNS TABLE(
    session_id VARCHAR(255),
    current_state VARCHAR(50),
    pending_reviews_count INTEGER,
    completed_reviews_count INTEGER,
    progress_percent NUMERIC,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        sw.session_id,
        sw.workflow_data->>'current_state' as current_state,
        jsonb_array_length(sw.workflow_data->'pending_reviews') as pending_reviews_count,
        jsonb_array_length(sw.workflow_data->'completed_reviews') as completed_reviews_count,
        CASE sw.workflow_data->>'current_state'
            WHEN 'idle' THEN 0.0
            WHEN 'extracting_text' THEN 10.0
            WHEN 'awaiting_text_review' THEN 25.0
            WHEN 'analyzing' THEN 50.0
            WHEN 'awaiting_analysis_review' THEN 75.0
            WHEN 'generating_bog' THEN 90.0
            WHEN 'complete' THEN 100.0
            ELSE NULL
        END as progress_percent,
        sw.created_at,
        sw.updated_at
    FROM session_workflows sw
    WHERE sw.session_id = p_session_id;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old completed workflows (older than 30 days)
CREATE OR REPLACE FUNCTION cleanup_old_workflows()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM session_workflows
    WHERE workflow_data->>'current_state' IN ('complete', 'failed')
      AND updated_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE session_workflows IS 'Stores complete workflow state for each session';
COMMENT ON TABLE review_items IS 'Detailed tracking of individual review items';
COMMENT ON TABLE workflow_transitions IS 'Audit trail of workflow state transitions';
COMMENT ON VIEW active_workflows IS 'Currently active workflows (not idle, complete, or failed)';
COMMENT ON VIEW workflow_stats IS 'Statistics about workflow states and durations';
COMMENT ON FUNCTION get_workflow_status IS 'Get comprehensive workflow status for a session';
COMMENT ON FUNCTION cleanup_old_workflows IS 'Cleanup old completed workflows to save space';