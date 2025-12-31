-- Migration: Add chat session persistence
-- Description: Adds tables to store chat conversations and messages

-- Chat sessions - represents a conversation thread
CREATE TABLE IF NOT EXISTS chat_sessions (
    id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    connection_id VARCHAR(100), -- Which database connection was used
    title VARCHAR(255), -- Auto-generated from first message or user-set
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    is_archived BOOLEAN DEFAULT false,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT fk_chat_user FOREIGN KEY (user_id) REFERENCES users(username) ON DELETE CASCADE,
    CONSTRAINT fk_chat_connection FOREIGN KEY (connection_id) REFERENCES connections(id) ON DELETE SET NULL
);

-- Chat messages - individual messages in a conversation
CREATE TABLE IF NOT EXISTS chat_messages (
    id VARCHAR(100) PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Query-related data (for assistant messages)
    sql_query TEXT,
    result_data JSONB, -- Actual query results (limited size)
    result_metadata JSONB, -- Column names, types, row count, etc.
    
    -- Message metadata
    token_count INTEGER,
    processing_time_ms INTEGER,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT fk_message_session FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_updated 
    ON chat_sessions(user_id, updated_at DESC);
    
CREATE INDEX IF NOT EXISTS idx_chat_sessions_connection 
    ON chat_sessions(connection_id) 
    WHERE connection_id IS NOT NULL;
    
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created 
    ON chat_messages(session_id, created_at ASC);

-- Function to update session metadata on message insert
CREATE OR REPLACE FUNCTION update_chat_session_on_message()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE chat_sessions
    SET 
        updated_at = NEW.created_at,
        last_message_at = NEW.created_at,
        message_count = message_count + 1,
        -- Auto-generate title from first user message (first 50 chars)
        title = CASE 
            WHEN title IS NULL AND NEW.role = 'user' 
            THEN LEFT(NEW.content, 50) || CASE WHEN LENGTH(NEW.content) > 50 THEN '...' ELSE '' END
            ELSE title
        END
    WHERE id = NEW.session_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update session metadata
DROP TRIGGER IF EXISTS trigger_update_chat_session ON chat_messages;
CREATE TRIGGER trigger_update_chat_session
    AFTER INSERT ON chat_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_chat_session_on_message();

-- Insert test comment to verify migration
COMMENT ON TABLE chat_sessions IS 'Stores user chat conversation sessions';
COMMENT ON TABLE chat_messages IS 'Stores individual messages within chat sessions';
