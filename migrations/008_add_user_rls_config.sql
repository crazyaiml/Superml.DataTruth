-- Migration: Add User RLS Configuration
-- Description: Add tables to store user-level RLS filters and permissions per connection
-- Date: 2025-12-31

-- Table: user_rls_filters
-- Stores row-level security filters for users per connection
CREATE TABLE IF NOT EXISTS user_rls_filters (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    connection_id INTEGER NOT NULL REFERENCES database_connections(id) ON DELETE CASCADE,
    table_name VARCHAR(255) NOT NULL,
    column_name VARCHAR(255) NOT NULL,
    operator VARCHAR(50) NOT NULL CHECK (operator IN ('=', '!=', '>', '<', '>=', '<=', 'IN', 'NOT IN', 'LIKE', 'NOT LIKE', 'IS NULL', 'IS NOT NULL')),
    filter_value TEXT,  -- JSON for complex values like arrays
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    
    -- Ensure unique filter per user/connection/table/column combination
    UNIQUE(user_id, connection_id, table_name, column_name)
);

-- Table: user_connection_roles
-- Maps users to roles per connection (e.g., Analyst for Connection 1, Viewer for Connection 2)
CREATE TABLE IF NOT EXISTS user_connection_roles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    connection_id INTEGER NOT NULL REFERENCES database_connections(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('ADMIN', 'ANALYST', 'VIEWER', 'EXTERNAL', 'CUSTOM')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    
    -- Ensure unique role per user/connection
    UNIQUE(user_id, connection_id)
);

-- Table: user_table_permissions
-- Stores table-level permissions for users per connection
CREATE TABLE IF NOT EXISTS user_table_permissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    connection_id INTEGER NOT NULL REFERENCES database_connections(id) ON DELETE CASCADE,
    table_name VARCHAR(255) NOT NULL,
    can_read BOOLEAN DEFAULT TRUE,
    can_write BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT FALSE,
    allowed_columns TEXT,  -- JSON array of allowed column names, NULL means all
    denied_columns TEXT,   -- JSON array of denied column names
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    
    -- Ensure unique permission per user/connection/table
    UNIQUE(user_id, connection_id, table_name)
);

-- Table: rls_configuration_audit
-- Audit log for RLS configuration changes
CREATE TABLE IF NOT EXISTS rls_configuration_audit (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    connection_id INTEGER NOT NULL REFERENCES database_connections(id),
    action VARCHAR(50) NOT NULL CHECK (action IN ('CREATE', 'UPDATE', 'DELETE', 'ACTIVATE', 'DEACTIVATE')),
    entity_type VARCHAR(50) NOT NULL CHECK (entity_type IN ('RLS_FILTER', 'ROLE', 'TABLE_PERMISSION')),
    entity_id INTEGER NOT NULL,
    old_value TEXT,  -- JSON of old values
    new_value TEXT,  -- JSON of new values
    performed_by INTEGER NOT NULL REFERENCES users(id),
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT
);

-- Indexes for performance
CREATE INDEX idx_user_rls_filters_user ON user_rls_filters(user_id);
CREATE INDEX idx_user_rls_filters_connection ON user_rls_filters(connection_id);
CREATE INDEX idx_user_rls_filters_active ON user_rls_filters(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_user_rls_filters_table ON user_rls_filters(table_name);

CREATE INDEX idx_user_connection_roles_user ON user_connection_roles(user_id);
CREATE INDEX idx_user_connection_roles_connection ON user_connection_roles(connection_id);
CREATE INDEX idx_user_connection_roles_active ON user_connection_roles(is_active) WHERE is_active = TRUE;

CREATE INDEX idx_user_table_permissions_user ON user_table_permissions(user_id);
CREATE INDEX idx_user_table_permissions_connection ON user_table_permissions(connection_id);
CREATE INDEX idx_user_table_permissions_active ON user_table_permissions(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_user_table_permissions_table ON user_table_permissions(table_name);

CREATE INDEX idx_rls_audit_user ON rls_configuration_audit(user_id);
CREATE INDEX idx_rls_audit_connection ON rls_configuration_audit(connection_id);
CREATE INDEX idx_rls_audit_performed_by ON rls_configuration_audit(performed_by);
CREATE INDEX idx_rls_audit_performed_at ON rls_configuration_audit(performed_at DESC);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_rls_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_user_rls_filters_updated_at
    BEFORE UPDATE ON user_rls_filters
    FOR EACH ROW
    EXECUTE FUNCTION update_rls_updated_at();

CREATE TRIGGER update_user_connection_roles_updated_at
    BEFORE UPDATE ON user_connection_roles
    FOR EACH ROW
    EXECUTE FUNCTION update_rls_updated_at();

CREATE TRIGGER update_user_table_permissions_updated_at
    BEFORE UPDATE ON user_table_permissions
    FOR EACH ROW
    EXECUTE FUNCTION update_rls_updated_at();

-- Grant permissions (adjust as needed)
GRANT SELECT, INSERT, UPDATE, DELETE ON user_rls_filters TO datatruth_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON user_connection_roles TO datatruth_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON user_table_permissions TO datatruth_user;
GRANT SELECT, INSERT ON rls_configuration_audit TO datatruth_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO datatruth_user;

-- Sample data for testing
-- User: Bhanu (Analyst, Region 1)
-- Assuming user_id=1 for Bhanu, connection_id=1
INSERT INTO user_connection_roles (user_id, connection_id, role, created_by)
VALUES (1, 1, 'ANALYST', 1)
ON CONFLICT (user_id, connection_id) DO NOTHING;

INSERT INTO user_rls_filters (user_id, connection_id, table_name, column_name, operator, filter_value, created_by)
VALUES (1, 1, 'companies', 'region', '=', '"Region 1"', 1)
ON CONFLICT (user_id, connection_id, table_name, column_name) DO NOTHING;

-- User: ANBCD (Analyst, Region 2)
-- Assuming user_id=2 for ANBCD, connection_id=1
-- Note: You'll need to create this user first if it doesn't exist
-- INSERT INTO users (username, email, full_name) VALUES ('anbcd', 'anbcd@example.com', 'ANBCD User');

-- Uncomment after creating user with id=2:
-- INSERT INTO user_connection_roles (user_id, connection_id, role, created_by)
-- VALUES (2, 1, 'ANALYST', 1)
-- ON CONFLICT (user_id, connection_id) DO NOTHING;

-- INSERT INTO user_rls_filters (user_id, connection_id, table_name, column_name, operator, filter_value, created_by)
-- VALUES (2, 1, 'companies', 'region', '=', '"Region 2"', 1)
-- ON CONFLICT (user_id, connection_id, table_name, column_name) DO NOTHING;

COMMENT ON TABLE user_rls_filters IS 'Stores row-level security filters for users per database connection';
COMMENT ON TABLE user_connection_roles IS 'Maps users to roles per database connection for granular access control';
COMMENT ON TABLE user_table_permissions IS 'Stores table and column-level permissions for users per connection';
COMMENT ON TABLE rls_configuration_audit IS 'Audit log for all RLS configuration changes';
