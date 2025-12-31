-- =============================================================================
-- DataTruth Database Initialization Script
-- =============================================================================
-- This script initializes the internal DataTruth database with all required
-- schemas, tables, indexes, and default data.
--
-- Run this script as the database admin user:
--   psql -U datatruth_admin -d datatruth_internal -f init_database.sql
--
-- =============================================================================

-- Create application user if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'datatruth_app') THEN
        CREATE ROLE datatruth_app WITH LOGIN PASSWORD 'CHANGE_ME_APP_PASSWORD';
    END IF;
END
$$;

-- Grant necessary privileges
GRANT CONNECT ON DATABASE datatruth_internal TO datatruth_app;
GRANT USAGE ON SCHEMA public TO datatruth_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO datatruth_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO datatruth_app;

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- Users table - DataTruth application users
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(100) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'analyst',
    goals TEXT[] DEFAULT '{}',
    department VARCHAR(100),
    preferences JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- Database connections - External data sources users will query
CREATE TABLE IF NOT EXISTS connections (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL,
    config JSONB NOT NULL,
    created_by VARCHAR(100) REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_connections_type ON connections(type);
CREATE INDEX IF NOT EXISTS idx_connections_created_by ON connections(created_by);
CREATE INDEX IF NOT EXISTS idx_connections_is_active ON connections(is_active);

-- Field mappings - AI-generated semantic mappings
CREATE TABLE IF NOT EXISTS field_mappings (
    id SERIAL PRIMARY KEY,
    connection_id VARCHAR(100) REFERENCES connections(id) ON DELETE CASCADE,
    table_name VARCHAR(255) NOT NULL,
    column_name VARCHAR(255) NOT NULL,
    semantic_type VARCHAR(100),
    description TEXT,
    sample_values TEXT[],
    data_type VARCHAR(50),
    is_metric BOOLEAN DEFAULT FALSE,
    is_dimension BOOLEAN DEFAULT FALSE,
    aggregation VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(connection_id, table_name, column_name)
);

CREATE INDEX IF NOT EXISTS idx_field_mappings_connection ON field_mappings(connection_id);
CREATE INDEX IF NOT EXISTS idx_field_mappings_table ON field_mappings(table_name);
CREATE INDEX IF NOT EXISTS idx_field_mappings_semantic ON field_mappings(semantic_type);

-- Calculated metrics - User-defined computed metrics
CREATE TABLE IF NOT EXISTS calculated_metrics (
    id SERIAL PRIMARY KEY,
    connection_id VARCHAR(255),
    metric_name VARCHAR(100) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    formula TEXT NOT NULL,
    data_type VARCHAR(50) DEFAULT 'NUMERIC',
    aggregation VARCHAR(50) DEFAULT 'SUM',
    base_table VARCHAR(100),
    format_type VARCHAR(50) DEFAULT 'number',
    synonyms TEXT[] DEFAULT '{}',
    dependencies TEXT[] DEFAULT '{}',
    created_by VARCHAR(100) REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE (connection_id, metric_name)
);

CREATE INDEX IF NOT EXISTS idx_calculated_metrics_connection_id ON calculated_metrics(connection_id);
CREATE INDEX IF NOT EXISTS idx_calculated_metrics_base_table ON calculated_metrics(base_table);
CREATE INDEX IF NOT EXISTS idx_calculated_metrics_created_by ON calculated_metrics(created_by);
CREATE INDEX IF NOT EXISTS idx_calculated_metrics_is_active ON calculated_metrics(is_active);

-- Audit log - Track all system actions
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    status VARCHAR(50),
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at DESC);

-- =============================================================================
-- USER ACTIVITY TRACKING (Migration 004)
-- =============================================================================

-- User activity log for tracking queries and responses
CREATE TABLE IF NOT EXISTS user_activity (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activity_type VARCHAR(50) NOT NULL,
    query_text TEXT,
    response_data JSONB,
    suggestion_clicked TEXT,
    feedback_rating INTEGER CHECK (feedback_rating BETWEEN 1 AND 5),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_activity_user_id ON user_activity(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_type ON user_activity(activity_type);
CREATE INDEX IF NOT EXISTS idx_user_activity_created_at ON user_activity(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_activity_user_type ON user_activity(user_id, activity_type);

-- Query patterns table to store learned patterns per role/user
CREATE TABLE IF NOT EXISTS query_patterns (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR(50) NOT NULL,
    target_id VARCHAR(100),
    query_template TEXT NOT NULL,
    frequency INTEGER DEFAULT 1,
    success_rate FLOAT DEFAULT 1.0 CHECK (success_rate BETWEEN 0 AND 1),
    avg_response_time FLOAT,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_query_patterns_type ON query_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_query_patterns_target ON query_patterns(target_id);
CREATE INDEX IF NOT EXISTS idx_query_patterns_frequency ON query_patterns(frequency DESC);
CREATE INDEX IF NOT EXISTS idx_query_patterns_success ON query_patterns(success_rate DESC);

-- Personalized suggestions cache
CREATE TABLE IF NOT EXISTS suggestion_cache (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    context_hash VARCHAR(64) NOT NULL,
    suggestions JSONB NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '1 hour'),
    hit_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_suggestion_cache_user_id ON suggestion_cache(user_id);
CREATE INDEX IF NOT EXISTS idx_suggestion_cache_hash ON suggestion_cache(context_hash);
CREATE INDEX IF NOT EXISTS idx_suggestion_cache_expires ON suggestion_cache(expires_at);

-- User preferences for suggestions
CREATE TABLE IF NOT EXISTS user_suggestion_preferences (
    user_id VARCHAR(100) PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    preferred_query_types JSONB DEFAULT '[]',
    excluded_metrics JSONB DEFAULT '[]',
    preferred_metrics JSONB DEFAULT '[]',
    preferred_dimensions JSONB DEFAULT '[]',
    show_advanced_queries BOOLEAN DEFAULT FALSE,
    max_suggestions INTEGER DEFAULT 6 CHECK (max_suggestions BETWEEN 1 AND 12),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE users IS 'DataTruth application users with roles and preferences';
COMMENT ON TABLE connections IS 'External database connections configured by users';
COMMENT ON TABLE field_mappings IS 'AI-generated semantic mappings for database fields';
COMMENT ON TABLE calculated_metrics IS 'User-defined computed metrics with formulas';
COMMENT ON TABLE audit_log IS 'System audit trail for compliance and debugging';
COMMENT ON TABLE user_activity IS 'Tracks user queries and interactions for personalization';
COMMENT ON TABLE query_patterns IS 'Learned query patterns from user activity';
COMMENT ON TABLE suggestion_cache IS 'Cache for generated suggestions to reduce LLM costs';
COMMENT ON TABLE user_suggestion_preferences IS 'User-specific preferences for suggestions';

-- =============================================================================
-- DEFAULT DATA
-- =============================================================================

-- Create default admin user (password: admin123 - CHANGE IN PRODUCTION!)
INSERT INTO users (id, username, email, password_hash, full_name, role, is_active)
VALUES 
    ('admin-default', 'admin', 'admin@datatruth.local', 
     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEmu4W',  -- admin123
     'System Administrator', 'admin', TRUE)
ON CONFLICT (username) DO NOTHING;

-- Create sample analyst user (password: analyst123)
INSERT INTO users (id, username, email, password_hash, full_name, role, goals, is_active)
VALUES 
    ('analyst-demo', 'analyst', 'analyst@datatruth.local',
     '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn98fckGpF/3lZFpX3xXsL1J9u3e',  -- analyst123
     'Demo Analyst', 'analyst', 
     ARRAY['Discover insights in data', 'Ensure data quality', 'Generate reports'],
     TRUE)
ON CONFLICT (username) DO NOTHING;

-- Create sample calculated metrics
INSERT INTO calculated_metrics (connection_id, metric_name, display_name, description, formula, data_type, aggregation, base_table, format_type, synonyms, is_active)
VALUES 
    (NULL, 'profit', 'Profit', 'Net profit calculated as revenue minus costs', 
     'SUM(amount - cost)', 'NUMERIC', 'SUM', 'Financial', 'currency',
     ARRAY['net_profit', 'earnings', 'margin_dollars', 'net income'], TRUE),
    (NULL, 'revenue', 'Revenue', 'Total revenue from transactions',
     'SUM(amount)', 'NUMERIC', 'SUM', 'Financial', 'currency',
     ARRAY['sales', 'income', 'total_sales'], TRUE),
    (NULL, 'profit_margin', 'Profit Margin', 'Profit as percentage of revenue',
     '(SUM(amount - cost) / NULLIF(SUM(amount), 0)) * 100', 'NUMERIC', 'FORMULA', 'Financial', 'percentage',
     ARRAY['margin_percent', 'profit_percentage'], TRUE)
ON CONFLICT (connection_id, metric_name) DO NOTHING;

-- =============================================================================
-- FUNCTIONS & TRIGGERS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_connections_updated_at ON connections;
CREATE TRIGGER update_connections_updated_at
    BEFORE UPDATE ON connections
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_field_mappings_updated_at ON field_mappings;
CREATE TRIGGER update_field_mappings_updated_at
    BEFORE UPDATE ON field_mappings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_calculated_metrics_updated_at ON calculated_metrics;
CREATE TRIGGER update_calculated_metrics_updated_at
    BEFORE UPDATE ON calculated_metrics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_query_patterns_updated_at ON query_patterns;
CREATE TRIGGER update_query_patterns_updated_at
    BEFORE UPDATE ON query_patterns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to clean expired suggestion cache
CREATE OR REPLACE FUNCTION clean_expired_suggestion_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM suggestion_cache WHERE expires_at < CURRENT_TIMESTAMP;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- GRANT PERMISSIONS TO APPLICATION USER
-- =============================================================================

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO datatruth_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO datatruth_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO datatruth_app;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

DO $$
DECLARE
    table_count INTEGER;
    user_count INTEGER;
    admin_exists BOOLEAN;
BEGIN
    -- Count tables
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    
    -- Count users
    SELECT COUNT(*) INTO user_count FROM users;
    
    -- Check admin exists
    SELECT EXISTS(SELECT 1 FROM users WHERE username = 'admin') INTO admin_exists;
    
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE 'DataTruth Database Initialization Complete!';
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE 'Tables created: %', table_count;
    RAISE NOTICE 'Users created: %', user_count;
    RAISE NOTICE 'Admin user exists: %', admin_exists;
    RAISE NOTICE '';
    RAISE NOTICE 'Default credentials (CHANGE IN PRODUCTION!):';
    RAISE NOTICE '  Admin: username=admin, password=admin123';
    RAISE NOTICE '  Analyst: username=analyst, password=analyst123';
    RAISE NOTICE '=============================================================================';
END
$$;
