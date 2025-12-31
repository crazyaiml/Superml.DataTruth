-- Migration: Add connection example queries table
-- This allows admins to generate and manage example queries for each connection

CREATE TABLE IF NOT EXISTS connection_example_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id VARCHAR NOT NULL REFERENCES connections(id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    icon TEXT DEFAULT '📊',
    description TEXT,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast lookups by connection
CREATE INDEX idx_example_queries_connection ON connection_example_queries(connection_id, is_active, display_order);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_example_query_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_example_query_timestamp
    BEFORE UPDATE ON connection_example_queries
    FOR EACH ROW
    EXECUTE FUNCTION update_example_query_updated_at();

-- Add comment
COMMENT ON TABLE connection_example_queries IS 'Admin-generated example queries for each connection, created via LLM based on schema analysis';
