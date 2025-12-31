-- DataTruth Internal Database - Seed Data
-- Creates initial admin user and sample data for development

-- ============================================
-- CREATE ADMIN USER
-- ============================================

-- Insert default admin user (password: admin123 - CHANGE IN PRODUCTION!)
-- Password hash generated with: bcrypt.hashpw("admin123".encode(), bcrypt.gensalt())
INSERT INTO users (username, email, password_hash, full_name, is_active, is_superuser) VALUES
    ('admin', 'admin@datatruth.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LS2LsVCLvAT6', 'System Administrator', true, true)
ON CONFLICT (username) DO NOTHING;

-- Insert sample analyst user (password: analyst123)
INSERT INTO users (username, email, password_hash, full_name, is_active, is_superuser) VALUES
    ('analyst', 'analyst@datatruth.local', '$2b$12$EixZE3qvZj8WBOKxR.6VwO8k9XYWj5L3F5xLxH5XKXvPy5NWXKfbC', 'Data Analyst', true, false)
ON CONFLICT (username) DO NOTHING;

-- Insert sample viewer user (password: viewer123)
INSERT INTO users (username, email, password_hash, full_name, is_active, is_superuser) VALUES
    ('viewer', 'viewer@datatruth.local', '$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'Read Only User', true, false)
ON CONFLICT (username) DO NOTHING;

-- ============================================
-- ASSIGN ROLES TO USERS
-- ============================================

-- Assign admin role to admin user
INSERT INTO user_roles (user_id, role_id, assigned_by)
SELECT u.id, r.id, u.id
FROM users u
CROSS JOIN roles r
WHERE u.username = 'admin' AND r.name = 'admin'
ON CONFLICT DO NOTHING;

-- Assign analyst role to analyst user
INSERT INTO user_roles (user_id, role_id, assigned_by)
SELECT u.id, r.id, (SELECT id FROM users WHERE username = 'admin')
FROM users u
CROSS JOIN roles r
WHERE u.username = 'analyst' AND r.name = 'analyst'
ON CONFLICT DO NOTHING;

-- Assign viewer role to viewer user
INSERT INTO user_roles (user_id, role_id, assigned_by)
SELECT u.id, r.id, (SELECT id FROM users WHERE username = 'admin')
FROM users u
CROSS JOIN roles r
WHERE u.username = 'viewer' AND r.name = 'viewer'
ON CONFLICT DO NOTHING;

-- ============================================
-- SAMPLE CONNECTION (Optional - for testing)
-- ============================================

-- Sample connection to the external demo database
-- NOTE: In production, users will create these through the UI
INSERT INTO connections (
    id, 
    name, 
    description, 
    connection_type,
    host,
    port,
    database_name,
    username,
    password_encrypted,
    schema_name,
    is_active,
    created_by
) VALUES (
    'demo-sales-db',
    'Demo Sales Database',
    'Sample database with sales transactions (for testing)',
    'postgresql',
    'localhost',
    5432,
    'datatruth_external', -- This is the EXTERNAL database, not the internal one
    'datatruth_readonly',
    'datatruth_readonly', -- In production, this should be encrypted!
    'public',
    true,
    (SELECT id FROM users WHERE username = 'admin')
)
ON CONFLICT (id) DO NOTHING;

-- Grant connection access to all users for testing
INSERT INTO connection_permissions (connection_id, user_id, permission_level, granted_by)
SELECT 
    'demo-sales-db',
    u.id,
    CASE 
        WHEN u.username = 'admin' THEN 'admin'
        WHEN u.username = 'analyst' THEN 'write'
        ELSE 'read'
    END,
    (SELECT id FROM users WHERE username = 'admin')
FROM users u
WHERE u.username IN ('admin', 'analyst', 'viewer')
ON CONFLICT DO NOTHING;

-- ============================================
-- SAMPLE AUDIT LOG ENTRIES
-- ============================================

INSERT INTO audit_log (user_id, action, resource_type, resource_id, status, details)
VALUES
    ((SELECT id FROM users WHERE username = 'admin'), 
     'create_user', 
     'user', 
     (SELECT id::text FROM users WHERE username = 'analyst'),
     'success',
     '{"created_username": "analyst", "role": "analyst"}'::jsonb),
    ((SELECT id FROM users WHERE username = 'admin'), 
     'create_connection', 
     'connection', 
     'demo-sales-db',
     'success',
     '{"connection_name": "Demo Sales Database", "connection_type": "postgresql"}'::jsonb)
ON CONFLICT DO NOTHING;

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Show created users and their roles
DO $$
DECLARE
    user_count INTEGER;
    admin_exists BOOLEAN;
BEGIN
    SELECT COUNT(*) INTO user_count FROM users;
    SELECT EXISTS(SELECT 1 FROM users WHERE username = 'admin' AND is_superuser = true) INTO admin_exists;
    
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'DataTruth Internal Database - Seed Complete';
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'Total users created: %', user_count;
    RAISE NOTICE 'Admin user exists: %', admin_exists;
    RAISE NOTICE '';
    RAISE NOTICE 'DEFAULT CREDENTIALS (CHANGE IN PRODUCTION!):';
    RAISE NOTICE '  Admin:   username=admin,   password=admin123';
    RAISE NOTICE '  Analyst: username=analyst, password=analyst123';
    RAISE NOTICE '  Viewer:  username=viewer,  password=viewer123';
    RAISE NOTICE '';
    RAISE NOTICE 'Sample connection created: demo-sales-db';
    RAISE NOTICE '  Target database: datatruth_external';
    RAISE NOTICE '  Users can query this through the UI';
    RAISE NOTICE '===========================================';
END $$;
