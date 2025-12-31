-- Migration: Add user activity tracking for personalized query suggestions
-- This stores chat queries, responses, and user interactions to train suggestion engine

-- User activity log for tracking queries and responses
CREATE TABLE IF NOT EXISTS user_activity (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activity_type VARCHAR(50) NOT NULL, -- 'query', 'chat', 'suggestion_click', 'feedback'
    query_text TEXT, -- User's query or chat message
    response_data JSONB, -- Full response including SQL, results, metadata
    suggestion_clicked TEXT, -- If they clicked a suggestion, which one
    feedback_rating INTEGER, -- 1-5 rating if provided
    metadata JSONB DEFAULT '{}', -- Additional context (role, preferences at time of query)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_user_activity_user_id ON user_activity(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_type ON user_activity(activity_type);
CREATE INDEX IF NOT EXISTS idx_user_activity_created_at ON user_activity(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_activity_user_type ON user_activity(user_id, activity_type);

-- Query patterns table to store learned patterns per role/user
CREATE TABLE IF NOT EXISTS query_patterns (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR(50) NOT NULL, -- 'role_based', 'user_specific', 'global'
    target_id VARCHAR(100), -- user_id or role name
    query_template TEXT NOT NULL, -- Template query text
    frequency INTEGER DEFAULT 1, -- How often this pattern appears
    success_rate FLOAT DEFAULT 1.0, -- How often queries succeed (0-1)
    avg_response_time FLOAT, -- Average response time in seconds
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}', -- Additional pattern info (metrics used, filters, etc.)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for pattern queries
CREATE INDEX IF NOT EXISTS idx_query_patterns_type ON query_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_query_patterns_target ON query_patterns(target_id);
CREATE INDEX IF NOT EXISTS idx_query_patterns_frequency ON query_patterns(frequency DESC);
CREATE INDEX IF NOT EXISTS idx_query_patterns_success ON query_patterns(success_rate DESC);

-- Personalized suggestions cache
CREATE TABLE IF NOT EXISTS suggestion_cache (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    context_hash VARCHAR(64) NOT NULL, -- Hash of context (role, prefs, partial_query)
    suggestions JSONB NOT NULL, -- Array of suggestion objects
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '1 hour'),
    hit_count INTEGER DEFAULT 0 -- How many times this was used
);

-- Indexes for suggestion cache
CREATE INDEX IF NOT EXISTS idx_suggestion_cache_user_id ON suggestion_cache(user_id);
CREATE INDEX IF NOT EXISTS idx_suggestion_cache_hash ON suggestion_cache(context_hash);
CREATE INDEX IF NOT EXISTS idx_suggestion_cache_expires ON suggestion_cache(expires_at);

-- User preferences for suggestions
CREATE TABLE IF NOT EXISTS user_suggestion_preferences (
    user_id VARCHAR(100) PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    preferred_query_types JSONB DEFAULT '[]', -- ['comparison', 'trend', 'ranking', 'aggregation']
    excluded_metrics JSONB DEFAULT '[]', -- Metrics to exclude from suggestions
    preferred_metrics JSONB DEFAULT '[]', -- Metrics to prioritize
    preferred_dimensions JSONB DEFAULT '[]', -- Dimensions to prioritize
    show_advanced_queries BOOLEAN DEFAULT FALSE, -- Show complex multi-step queries
    max_suggestions INTEGER DEFAULT 6, -- How many suggestions to show
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Comments for documentation
COMMENT ON TABLE user_activity IS 'Tracks all user queries, chats, and interactions for personalized suggestions';
COMMENT ON TABLE query_patterns IS 'Learned query patterns from user activity, aggregated by role/user';
COMMENT ON TABLE suggestion_cache IS 'Cache for generated suggestions to reduce LLM API calls';
COMMENT ON TABLE user_suggestion_preferences IS 'User-specific preferences for query suggestions';

COMMENT ON COLUMN user_activity.activity_type IS 'Type of activity: query, chat, suggestion_click, feedback';
COMMENT ON COLUMN user_activity.response_data IS 'Full response including SQL, results, execution time, etc.';
COMMENT ON COLUMN user_activity.metadata IS 'Context at time of query: role, department, active goals, etc.';

COMMENT ON COLUMN query_patterns.pattern_type IS 'Scope: role_based (all users with role), user_specific, or global';
COMMENT ON COLUMN query_patterns.query_template IS 'Template with placeholders like {metric}, {dimension}, {timeframe}';
COMMENT ON COLUMN query_patterns.success_rate IS 'Percentage of queries (0-1) that executed successfully';

COMMENT ON COLUMN suggestion_cache.context_hash IS 'MD5 hash of (user_id + role + preferences + partial_query)';
COMMENT ON COLUMN suggestion_cache.expires_at IS 'Cache expires after 1 hour by default';
