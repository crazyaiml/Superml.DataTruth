-- Migration: Add calculated_metrics table for complex metrics like profit
-- Date: 2025-12-29

-- Table for storing calculated/derived metrics
CREATE TABLE IF NOT EXISTS calculated_metrics (
    id SERIAL PRIMARY KEY,
    connection_id VARCHAR(100) REFERENCES connections(id) ON DELETE CASCADE,
    metric_name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    formula TEXT NOT NULL, -- SQL formula like 'SUM(amount - cost)'
    base_table VARCHAR(255) NOT NULL,
    aggregation VARCHAR(50), -- 'sum', 'avg', 'calculated', etc.
    data_type VARCHAR(50) DEFAULT 'decimal',
    format_type VARCHAR(50), -- 'currency', 'percentage', 'number'
    synonyms TEXT[], -- Alternative names
    filters JSONB, -- Array of filter conditions
    is_active BOOLEAN DEFAULT true,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (connection_id, metric_name)
);

-- Index for performance
CREATE INDEX idx_calculated_metrics_connection ON calculated_metrics(connection_id);
CREATE INDEX idx_calculated_metrics_active ON calculated_metrics(is_active);

-- Insert sample calculated metrics for demo-sales-db
INSERT INTO calculated_metrics (
    connection_id, metric_name, display_name, description, formula, 
    base_table, aggregation, data_type, format_type, synonyms, filters
) VALUES 
(
    'demo-sales-db',
    'profit',
    'Profit',
    'Total profit calculated as revenue minus cost',
    'SUM(transactions.amount - transactions.cost)',
    'transactions',
    'sum',
    'decimal',
    'currency',
    ARRAY['net_profit', 'earnings', 'margin_dollars', 'net income'],
    '[{"field": "status", "operator": "=", "value": "completed"}]'::jsonb
),
(
    'demo-sales-db',
    'revenue',
    'Revenue',
    'Total recognized revenue from completed transactions',
    'SUM(transactions.amount)',
    'transactions',
    'sum',
    'decimal',
    'currency',
    ARRAY['sales', 'income', 'turnover', 'receipts'],
    '[{"field": "status", "operator": "=", "value": "completed"}]'::jsonb
),
(
    'demo-sales-db',
    'profit_margin',
    'Profit Margin',
    'Profit as a percentage of revenue',
    '(SUM(transactions.amount - transactions.cost) / NULLIF(SUM(transactions.amount), 0)) * 100',
    'transactions',
    'calculated',
    'decimal',
    'percentage',
    ARRAY['margin', 'profit_percent', 'margin_percentage'],
    '[{"field": "status", "operator": "=", "value": "completed"}]'::jsonb
)
ON CONFLICT (connection_id, metric_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    formula = EXCLUDED.formula,
    updated_at = CURRENT_TIMESTAMP;
