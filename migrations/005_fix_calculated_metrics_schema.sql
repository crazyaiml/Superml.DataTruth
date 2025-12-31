-- Migration: Fix calculated_metrics table schema to support connections
-- This adds the missing connection_id column and renames columns to match the API expectations

-- Add connection_id column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'calculated_metrics' 
                   AND column_name = 'connection_id') THEN
        ALTER TABLE calculated_metrics ADD COLUMN connection_id VARCHAR(255);
    END IF;
END $$;

-- Rename 'name' to 'metric_name' if it hasn't been renamed yet
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'calculated_metrics' 
               AND column_name = 'name') 
    AND NOT EXISTS (SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'calculated_metrics' 
                    AND column_name = 'metric_name') THEN
        ALTER TABLE calculated_metrics RENAME COLUMN name TO metric_name;
    END IF;
END $$;

-- Rename 'category' to 'base_table' if it hasn't been renamed yet
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'calculated_metrics' 
               AND column_name = 'category') 
    AND NOT EXISTS (SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'calculated_metrics' 
                    AND column_name = 'base_table') THEN
        ALTER TABLE calculated_metrics RENAME COLUMN category TO base_table;
    END IF;
END $$;

-- Drop the old unique constraint on 'name' if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.table_constraints 
               WHERE constraint_name = 'calculated_metrics_name_key' 
               AND table_name = 'calculated_metrics') THEN
        ALTER TABLE calculated_metrics DROP CONSTRAINT calculated_metrics_name_key;
    END IF;
END $$;

-- Add composite unique constraint for connection_id + metric_name
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'calculated_metrics_connection_metric_key' 
                   AND table_name = 'calculated_metrics') THEN
        ALTER TABLE calculated_metrics 
        ADD CONSTRAINT calculated_metrics_connection_metric_key 
        UNIQUE (connection_id, metric_name);
    END IF;
END $$;

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_calculated_metrics_connection_id ON calculated_metrics(connection_id);
CREATE INDEX IF NOT EXISTS idx_calculated_metrics_base_table ON calculated_metrics(base_table);

-- Drop old index on category if it exists
DROP INDEX IF EXISTS idx_calculated_metrics_category;

-- Add format_type column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'calculated_metrics' 
                   AND column_name = 'format_type') THEN
        ALTER TABLE calculated_metrics ADD COLUMN format_type VARCHAR(50) DEFAULT 'number';
    END IF;
END $$;

-- Update trigger name references
DROP TRIGGER IF EXISTS update_calculated_metrics_updated_at ON calculated_metrics;
CREATE TRIGGER update_calculated_metrics_updated_at
    BEFORE UPDATE ON calculated_metrics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
