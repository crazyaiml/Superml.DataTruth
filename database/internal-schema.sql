-- DataTruth Internal Database Schema
-- This database stores DataTruth application metadata, NOT user data
-- User data resides in external databases configured via connections
-- PostgreSQL 14+

-- ============================================
-- SYSTEM CONFIGURATION
-- ============================================

-- System configuration - Stores application settings (API keys, etc.)
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    is_sensitive BOOLEAN DEFAULT false,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100)
);

-- ============================================
-- USERS & AUTHENTICATION
-- ============================================

-- Users table - DataTruth application users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Roles table
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT false, -- System roles cannot be deleted
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Permissions table
CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    resource VARCHAR(100) NOT NULL, -- 'connection', 'query', 'user', etc.
    action VARCHAR(50) NOT NULL, -- 'create', 'read', 'update', 'delete', 'execute'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User-Role mapping (many-to-many)
CREATE TABLE IF NOT EXISTS user_roles (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by INTEGER REFERENCES users(id),
    PRIMARY KEY (user_id, role_id)
);

-- Role-Permission mapping (many-to-many)
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by INTEGER REFERENCES users(id),
    PRIMARY KEY (role_id, permission_id)
);

-- ============================================
-- DATA CONNECTIONS
-- ============================================

-- Database connections - External data sources users will query
CREATE TABLE IF NOT EXISTS connections (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    connection_type VARCHAR(50) NOT NULL, -- 'postgresql', 'mysql', 'snowflake', etc.
    
    -- Connection details (encrypted in production)
    host VARCHAR(255),
    port INTEGER,
    database_name VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    password_encrypted TEXT NOT NULL, -- Should be encrypted at rest
    schema_name VARCHAR(100) DEFAULT 'public',
    
    -- Connection configuration
    connection_string TEXT, -- For databases that use connection strings
    additional_params JSONB, -- Extra parameters (SSL, timeout, etc.)
    
    -- Status and metadata
    is_active BOOLEAN DEFAULT true,
    last_discovered TIMESTAMP, -- Last time schema was discovered
    table_count INTEGER DEFAULT 0,
    relationship_count INTEGER DEFAULT 0,
    
    -- Access control
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Auditing
    last_accessed TIMESTAMP,
    access_count INTEGER DEFAULT 0
);

-- Connection access control - Who can use which connections
CREATE TABLE IF NOT EXISTS connection_permissions (
    connection_id VARCHAR(100) REFERENCES connections(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    permission_level VARCHAR(50) DEFAULT 'read', -- 'read', 'write', 'admin'
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by INTEGER REFERENCES users(id),
    PRIMARY KEY (connection_id, user_id)
);

-- ============================================
-- SCHEMA METADATA
-- ============================================

-- Discovered tables from external databases
CREATE TABLE IF NOT EXISTS discovered_tables (
    id SERIAL PRIMARY KEY,
    connection_id VARCHAR(100) REFERENCES connections(id) ON DELETE CASCADE,
    table_name VARCHAR(255) NOT NULL,
    schema_name VARCHAR(100) DEFAULT 'public',
    table_type VARCHAR(50), -- 'fact', 'dimension'
    row_count BIGINT,
    primary_keys TEXT[], -- Array of primary key columns
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (connection_id, schema_name, table_name)
);

-- Discovered columns from external databases
CREATE TABLE IF NOT EXISTS discovered_columns (
    id SERIAL PRIMARY KEY,
    table_id INTEGER REFERENCES discovered_tables(id) ON DELETE CASCADE,
    column_name VARCHAR(255) NOT NULL,
    data_type VARCHAR(100) NOT NULL,
    is_nullable BOOLEAN DEFAULT true,
    is_measure BOOLEAN DEFAULT false, -- Numeric/aggregatable
    is_dimension BOOLEAN DEFAULT false, -- Categorical
    default_aggregation VARCHAR(50), -- 'sum', 'avg', 'count', 'min', 'max'
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (table_id, column_name)
);

-- Discovered foreign key relationships
CREATE TABLE IF NOT EXISTS discovered_relationships (
    id SERIAL PRIMARY KEY,
    connection_id VARCHAR(100) REFERENCES connections(id) ON DELETE CASCADE,
    from_table VARCHAR(255) NOT NULL,
    from_column VARCHAR(255) NOT NULL,
    to_table VARCHAR(255) NOT NULL,
    to_column VARCHAR(255) NOT NULL,
    cardinality VARCHAR(10), -- '1:1', '1:N', 'N:1', 'N:N'
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (connection_id, from_table, from_column, to_table, to_column)
);

-- ============================================
-- FIELD MAPPINGS (AI-Generated)
-- ============================================

-- Business-friendly field mappings
CREATE TABLE IF NOT EXISTS field_mappings (
    id SERIAL PRIMARY KEY,
    connection_id VARCHAR(100) REFERENCES connections(id) ON DELETE CASCADE,
    table_name VARCHAR(255) NOT NULL,
    column_name VARCHAR(255) NOT NULL,
    
    -- Business metadata
    display_name VARCHAR(255) NOT NULL, -- "Transaction Amount" vs "amount"
    description TEXT,
    synonyms TEXT[], -- Alternative names for search
    category VARCHAR(100), -- Business category (sales, finance, etc.)
    
    -- Data characteristics
    is_measure BOOLEAN DEFAULT false,
    default_aggregation VARCHAR(50),
    format_string VARCHAR(100), -- Display format (e.g., "$#,##0.00")
    
    -- AI metadata
    ai_generated BOOLEAN DEFAULT false,
    confidence_score DECIMAL(3, 2), -- 0.00 to 1.00
    
    -- Versioning
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE (connection_id, table_name, column_name)
);

-- Aggregation rules - Pattern-based default aggregations
CREATE TABLE IF NOT EXISTS aggregation_rules (
    id SERIAL PRIMARY KEY,
    field_pattern VARCHAR(255) NOT NULL, -- Regex pattern like '*_amount'
    default_aggregation VARCHAR(50) NOT NULL, -- 'sum', 'avg', 'count', etc.
    description TEXT,
    priority INTEGER DEFAULT 0, -- Higher priority rules apply first
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (field_pattern)
);

-- Field mapping rules - Pattern-based name transformations
CREATE TABLE IF NOT EXISTS field_mapping_rules (
    id SERIAL PRIMARY KEY,
    technical_pattern VARCHAR(255) NOT NULL, -- Regex: '(.*)_amount'
    business_name_template VARCHAR(255) NOT NULL, -- Template: '\1 Amount'
    description_template TEXT,
    synonyms TEXT[],
    priority INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (technical_pattern)
);

-- ============================================
-- QUERY HISTORY & AUDIT
-- ============================================

-- Query execution history
CREATE TABLE IF NOT EXISTS query_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    connection_id VARCHAR(100) REFERENCES connections(id) ON DELETE SET NULL,
    
    -- Query details
    natural_language_query TEXT NOT NULL,
    generated_sql TEXT NOT NULL,
    execution_time_ms INTEGER,
    row_count INTEGER,
    status VARCHAR(50), -- 'success', 'error', 'timeout'
    error_message TEXT,
    
    -- Metadata
    query_intent VARCHAR(100), -- 'analytics', 'lookup', 'aggregation', etc.
    tables_accessed TEXT[],
    fields_accessed TEXT[],
    
    -- Timestamps
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit log for all actions
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL, -- 'create_connection', 'discover_schema', etc.
    resource_type VARCHAR(100) NOT NULL, -- 'connection', 'user', 'role', etc.
    resource_id VARCHAR(255),
    details JSONB, -- Additional context
    ip_address INET,
    user_agent TEXT,
    status VARCHAR(50), -- 'success', 'failure'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- SEMANTIC LAYER CACHE
-- ============================================

-- Cached semantic layer configurations
CREATE TABLE IF NOT EXISTS semantic_layer_cache (
    id SERIAL PRIMARY KEY,
    connection_id VARCHAR(100) REFERENCES connections(id) ON DELETE CASCADE,
    config_type VARCHAR(50) NOT NULL, -- 'entities', 'relationships', 'metrics'
    config_data JSONB NOT NULL,
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (connection_id, config_type, version)
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Users indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);

-- Connections indexes
CREATE INDEX idx_connections_type ON connections(connection_type);
CREATE INDEX idx_connections_is_active ON connections(is_active);
CREATE INDEX idx_connections_created_by ON connections(created_by);

-- Schema metadata indexes
CREATE INDEX idx_discovered_tables_connection ON discovered_tables(connection_id);
CREATE INDEX idx_discovered_columns_table ON discovered_columns(table_id);
CREATE INDEX idx_discovered_relationships_connection ON discovered_relationships(connection_id);

-- Field mappings indexes
CREATE INDEX idx_field_mappings_connection ON field_mappings(connection_id);
CREATE INDEX idx_field_mappings_table ON field_mappings(table_name);
CREATE INDEX idx_field_mappings_display_name ON field_mappings(display_name);
CREATE INDEX idx_field_mappings_ai_generated ON field_mappings(ai_generated);

-- Query history indexes
CREATE INDEX idx_query_history_user ON query_history(user_id);
CREATE INDEX idx_query_history_connection ON query_history(connection_id);
CREATE INDEX idx_query_history_executed_at ON query_history(executed_at);
CREATE INDEX idx_query_history_status ON query_history(status);

-- Audit log indexes
CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);

-- ============================================
-- INITIAL DATA
-- ============================================

-- Insert system roles
INSERT INTO roles (name, description, is_system) VALUES
    ('admin', 'Full system access - can manage users, roles, and all connections', true),
    ('analyst', 'Can create connections, discover schemas, and query data', true),
    ('viewer', 'Read-only access - can only view and query existing connections', true)
ON CONFLICT (name) DO NOTHING;

-- Insert base permissions
INSERT INTO permissions (name, description, resource, action) VALUES
    -- User management
    ('manage_users', 'Create, update, and delete users', 'user', 'manage'),
    ('view_users', 'View user list and details', 'user', 'read'),
    
    -- Role management
    ('manage_roles', 'Create, update, and delete roles', 'role', 'manage'),
    ('assign_roles', 'Assign roles to users', 'role', 'assign'),
    
    -- Connection management
    ('create_connection', 'Create new data connections', 'connection', 'create'),
    ('edit_connection', 'Update existing connections', 'connection', 'update'),
    ('delete_connection', 'Delete connections', 'connection', 'delete'),
    ('view_connection', 'View connection details', 'connection', 'read'),
    ('discover_schema', 'Trigger schema discovery', 'connection', 'discover'),
    
    -- Query execution
    ('execute_query', 'Execute queries against connections', 'query', 'execute'),
    ('view_query_history', 'View query execution history', 'query', 'read'),
    
    -- Field mappings
    ('manage_field_mappings', 'Create and update field mappings', 'field_mapping', 'manage'),
    ('generate_ai_descriptions', 'Generate AI-powered field descriptions', 'field_mapping', 'generate'),
    
    -- Audit logs
    ('view_audit_logs', 'View system audit logs', 'audit', 'read')
ON CONFLICT (name) DO NOTHING;

-- Assign permissions to admin role
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'admin'
ON CONFLICT DO NOTHING;

-- Assign permissions to analyst role
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'analyst'
AND p.name IN (
    'view_users',
    'create_connection', 'edit_connection', 'view_connection', 'discover_schema',
    'execute_query', 'view_query_history',
    'manage_field_mappings', 'generate_ai_descriptions'
)
ON CONFLICT DO NOTHING;

-- Assign permissions to viewer role
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'viewer'
AND p.name IN ('view_connection', 'execute_query', 'view_query_history')
ON CONFLICT DO NOTHING;

-- Insert default aggregation rules
INSERT INTO aggregation_rules (field_pattern, default_aggregation, description, priority) VALUES
    ('*_amount', 'sum', 'Monetary amounts should be summed', 100),
    ('*_revenue', 'sum', 'Revenue fields should be summed', 100),
    ('*_price', 'sum', 'Price fields should be summed', 100),
    ('*_cost', 'sum', 'Cost fields should be summed', 100),
    ('*_count', 'sum', 'Count fields should be summed', 90),
    ('*_quantity', 'sum', 'Quantity fields should be summed', 90),
    ('*_rate', 'avg', 'Rate fields should be averaged', 80),
    ('*_percentage', 'avg', 'Percentage fields should be averaged', 80),
    ('*_score', 'avg', 'Score fields should be averaged', 80),
    ('*_id', 'count_distinct', 'ID fields should be counted distinctly', 70),
    ('*_key', 'count_distinct', 'Key fields should be counted distinctly', 70),
    ('*_date', 'count', 'Date fields should be counted', 60),
    ('*_timestamp', 'count', 'Timestamp fields should be counted', 60)
ON CONFLICT (field_pattern) DO NOTHING;

-- Insert default field mapping rules
INSERT INTO field_mapping_rules (technical_pattern, business_name_template, description_template, synonyms, priority) VALUES
    ('(.*)_amount', '\1 Amount', 'Total monetary value', ARRAY['value', 'sum'], 100),
    ('(.*)_revenue', '\1 Revenue', 'Total revenue generated', ARRAY['sales', 'income'], 100),
    ('(.*)_count', 'Number of \1', 'Total count', ARRAY['total', 'qty'], 90),
    ('(.*)_rate', '\1 Rate', 'Rate or percentage', ARRAY['%', 'percent'], 80),
    ('(.*)_id', '\1 ID', 'Unique identifier', ARRAY['identifier', 'key'], 70),
    ('(.*)_date', '\1 Date', 'Date value', ARRAY['day', 'time'], 60),
    ('(.*)_name', '\1 Name', 'Name or label', ARRAY['label', 'title'], 60)
ON CONFLICT (technical_pattern) DO NOTHING;

-- ============================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================

COMMENT ON TABLE users IS 'DataTruth application users (not customer data)';
COMMENT ON TABLE roles IS 'User roles for access control';
COMMENT ON TABLE permissions IS 'Granular permissions for actions';
COMMENT ON TABLE connections IS 'External database connections configured by users';
COMMENT ON TABLE discovered_tables IS 'Tables discovered from external databases';
COMMENT ON TABLE discovered_columns IS 'Columns discovered from external databases';
COMMENT ON TABLE discovered_relationships IS 'Foreign key relationships discovered';
COMMENT ON TABLE field_mappings IS 'Business-friendly field names and descriptions';
COMMENT ON TABLE query_history IS 'History of all executed queries';
COMMENT ON TABLE audit_log IS 'Audit trail for all system actions';

COMMENT ON COLUMN connections.password_encrypted IS 'Encrypted connection password - should use encryption at rest';
COMMENT ON COLUMN field_mappings.ai_generated IS 'Whether this mapping was generated by AI vs rules';
COMMENT ON COLUMN field_mappings.confidence_score IS 'AI confidence score from 0.00 to 1.00';
