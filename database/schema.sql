-- SuperML DataTruth - Sample Database Schema
-- PostgreSQL 14+

-- Note: Using existing PostgreSQL user instead of creating new one
-- If you need read-only access, create separate user manually

-- Companies table
CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    country VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Clients table
CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    company_id INTEGER REFERENCES companies(id),
    type VARCHAR(50), -- 'enterprise', 'mid-market', 'smb'
    region VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agents table
CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    region VARCHAR(100),
    team VARCHAR(100),
    hire_date DATE,
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'inactive'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    transaction_date DATE NOT NULL,
    agent_id INTEGER REFERENCES agents(id),
    client_id INTEGER REFERENCES clients(id),
    company_id INTEGER REFERENCES companies(id),
    amount DECIMAL(15, 2) NOT NULL,
    cost DECIMAL(15, 2) NOT NULL DEFAULT 0,
    status VARCHAR(50) DEFAULT 'completed', -- 'completed', 'pending', 'cancelled'
    transaction_type VARCHAR(50), -- 'sale', 'renewal', 'upsell'
    category VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_transactions_agent ON transactions(agent_id);
CREATE INDEX IF NOT EXISTS idx_transactions_client ON transactions(client_id);
CREATE INDEX IF NOT EXISTS idx_transactions_company ON transactions(company_id);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_clients_company ON clients(company_id);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);

-- Note: Grant permissions manually if using separate read-only user
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO your_readonly_user;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO your_readonly_user;

-- Comments for documentation
COMMENT ON TABLE companies IS 'Organizations that are our customers';
COMMENT ON TABLE clients IS 'Individual clients within companies';
COMMENT ON TABLE agents IS 'Sales agents who handle transactions';
COMMENT ON TABLE transactions IS 'Revenue and cost transactions';

COMMENT ON COLUMN transactions.amount IS 'Revenue amount in USD';
COMMENT ON COLUMN transactions.cost IS 'Cost of goods sold in USD';
COMMENT ON COLUMN transactions.status IS 'Only completed transactions count towards revenue';
