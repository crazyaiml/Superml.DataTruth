-- SuperML DataTruth - Sample Data
-- This file seeds the database with test data

-- Insert Companies
INSERT INTO companies (id, name, industry, country) VALUES
(1, 'Acme Corporation', 'Technology', 'USA'),
(2, 'Global Solutions Inc', 'Consulting', 'UK'),
(3, 'TechStart Ventures', 'Technology', 'Canada'),
(4, 'Enterprise Systems', 'Software', 'USA'),
(5, 'Innovation Labs', 'R&D', 'Germany');

-- Insert Clients
INSERT INTO clients (id, name, company_id, type, region) VALUES
(1, 'Acme HQ', 1, 'enterprise', 'North America'),
(2, 'Acme EU', 1, 'enterprise', 'Europe'),
(3, 'Global Solutions US', 2, 'mid-market', 'North America'),
(4, 'Global Solutions UK', 2, 'enterprise', 'Europe'),
(5, 'TechStart Main', 3, 'smb', 'North America'),
(6, 'Enterprise Systems West', 4, 'enterprise', 'North America'),
(7, 'Enterprise Systems East', 4, 'mid-market', 'North America'),
(8, 'Innovation Labs Berlin', 5, 'mid-market', 'Europe'),
(9, 'Innovation Labs Munich', 5, 'smb', 'Europe'),
(10, 'Acme APAC', 1, 'mid-market', 'Asia Pacific');

-- Insert Agents
INSERT INTO agents (id, name, email, region, team, hire_date, status) VALUES
(1, 'Alice Johnson', 'alice.johnson@example.com', 'North America', 'Enterprise', '2020-01-15', 'active'),
(2, 'Bob Smith', 'bob.smith@example.com', 'North America', 'SMB', '2019-03-20', 'active'),
(3, 'Carol Williams', 'carol.williams@example.com', 'Europe', 'Enterprise', '2021-06-10', 'active'),
(4, 'David Brown', 'david.brown@example.com', 'Europe', 'Mid-Market', '2020-11-05', 'active'),
(5, 'Eve Davis', 'eve.davis@example.com', 'North America', 'Enterprise', '2018-09-12', 'active'),
(6, 'Frank Miller', 'frank.miller@example.com', 'Asia Pacific', 'SMB', '2022-02-28', 'active'),
(7, 'Grace Wilson', 'grace.wilson@example.com', 'North America', 'Mid-Market', '2019-07-18', 'inactive'),
(8, 'Henry Moore', 'henry.moore@example.com', 'Europe', 'Enterprise', '2021-01-22', 'active');

-- Insert Transactions for 2023-2024
-- Q1 2023
INSERT INTO transactions (transaction_date, agent_id, client_id, company_id, amount, cost, status, transaction_type, category) VALUES
('2023-01-15', 1, 1, 1, 150000, 45000, 'completed', 'sale', 'Software License'),
('2023-01-20', 2, 5, 3, 25000, 8000, 'completed', 'sale', 'Consulting'),
('2023-02-10', 3, 4, 2, 200000, 60000, 'completed', 'renewal', 'Software License'),
('2023-02-15', 4, 8, 5, 75000, 22500, 'completed', 'sale', 'R&D Services'),
('2023-03-05', 5, 6, 4, 300000, 90000, 'completed', 'upsell', 'Enterprise Suite'),
('2023-03-20', 1, 2, 1, 180000, 54000, 'completed', 'renewal', 'Software License');

-- Q2 2023
INSERT INTO transactions (transaction_date, agent_id, client_id, company_id, amount, cost, status, transaction_type, category) VALUES
('2023-04-10', 2, 5, 3, 30000, 9000, 'completed', 'renewal', 'Consulting'),
('2023-04-25', 3, 4, 2, 250000, 75000, 'completed', 'upsell', 'Advisory Services'),
('2023-05-15', 4, 9, 5, 40000, 12000, 'completed', 'sale', 'R&D Services'),
('2023-05-20', 5, 7, 4, 120000, 36000, 'completed', 'sale', 'Software License'),
('2023-06-10', 1, 1, 1, 160000, 48000, 'completed', 'upsell', 'Premium Support'),
('2023-06-28', 8, 4, 2, 220000, 66000, 'completed', 'renewal', 'Consulting');

-- Q3 2023
INSERT INTO transactions (transaction_date, agent_id, client_id, company_id, amount, cost, status, transaction_type, category) VALUES
('2023-07-08', 2, 5, 3, 35000, 10500, 'completed', 'upsell', 'Training'),
('2023-07-22', 3, 2, 1, 190000, 57000, 'completed', 'renewal', 'Software License'),
('2023-08-12', 4, 8, 5, 80000, 24000, 'completed', 'renewal', 'R&D Services'),
('2023-08-30', 5, 6, 4, 350000, 105000, 'completed', 'renewal', 'Enterprise Suite'),
('2023-09-15', 1, 1, 1, 170000, 51000, 'completed', 'sale', 'Cloud Services'),
('2023-09-25', 8, 4, 2, 240000, 72000, 'completed', 'upsell', 'Strategic Consulting');

-- Q4 2023
INSERT INTO transactions (transaction_date, agent_id, client_id, company_id, amount, cost, status, transaction_type, category) VALUES
('2023-10-10', 2, 5, 3, 45000, 13500, 'completed', 'sale', 'Implementation'),
('2023-10-20', 3, 4, 2, 280000, 84000, 'completed', 'renewal', 'Advisory Services'),
('2023-11-08', 4, 9, 5, 50000, 15000, 'completed', 'upsell', 'Premium R&D'),
('2023-11-25', 5, 7, 4, 140000, 42000, 'completed', 'renewal', 'Software License'),
('2023-12-10', 1, 1, 1, 200000, 60000, 'completed', 'renewal', 'Premium Support'),
('2023-12-20', 8, 2, 1, 210000, 63000, 'completed', 'sale', 'Software License');

-- Q1 2024
INSERT INTO transactions (transaction_date, agent_id, client_id, company_id, amount, cost, status, transaction_type, category) VALUES
('2024-01-12', 1, 1, 1, 180000, 54000, 'completed', 'renewal', 'Software License'),
('2024-01-25', 2, 5, 3, 50000, 15000, 'completed', 'renewal', 'Consulting'),
('2024-02-15', 3, 4, 2, 300000, 90000, 'completed', 'renewal', 'Advisory Services'),
('2024-02-28', 4, 8, 5, 90000, 27000, 'completed', 'upsell', 'R&D Services'),
('2024-03-10', 5, 6, 4, 380000, 114000, 'completed', 'renewal', 'Enterprise Suite'),
('2024-03-22', 6, 10, 1, 120000, 36000, 'completed', 'sale', 'APAC Expansion');

-- Q2 2024
INSERT INTO transactions (transaction_date, agent_id, client_id, company_id, amount, cost, status, transaction_type, category) VALUES
('2024-04-08', 1, 2, 1, 220000, 66000, 'completed', 'upsell', 'Premium Support'),
('2024-04-20', 2, 5, 3, 55000, 16500, 'completed', 'upsell', 'Advanced Training'),
('2024-05-15', 3, 4, 2, 320000, 96000, 'completed', 'upsell', 'Strategic Advisory'),
('2024-05-28', 4, 9, 5, 60000, 18000, 'completed', 'renewal', 'R&D Services'),
('2024-06-10', 5, 7, 4, 160000, 48000, 'completed', 'renewal', 'Software License'),
('2024-06-25', 8, 4, 2, 340000, 102000, 'completed', 'renewal', 'Consulting');

-- Q3 2024
INSERT INTO transactions (transaction_date, agent_id, client_id, company_id, amount, cost, status, transaction_type, category) VALUES
('2024-07-12', 1, 1, 1, 230000, 69000, 'completed', 'renewal', 'Cloud Services'),
('2024-07-28', 2, 5, 3, 60000, 18000, 'completed', 'renewal', 'Implementation'),
('2024-08-15', 3, 2, 1, 250000, 75000, 'completed', 'upsell', 'Enterprise Features'),
('2024-08-30', 4, 8, 5, 100000, 30000, 'completed', 'renewal', 'R&D Services'),
('2024-09-12', 5, 6, 4, 420000, 126000, 'completed', 'renewal', 'Enterprise Suite'),
('2024-09-28', 6, 10, 1, 150000, 45000, 'completed', 'upsell', 'APAC Services');

-- Q4 2024 (partial)
INSERT INTO transactions (transaction_date, agent_id, client_id, company_id, amount, cost, status, transaction_type, category) VALUES
('2024-10-10', 1, 1, 1, 240000, 72000, 'completed', 'renewal', 'Software License'),
('2024-10-22', 2, 5, 3, 65000, 19500, 'completed', 'upsell', 'Support Package'),
('2024-11-08', 3, 4, 2, 360000, 108000, 'completed', 'renewal', 'Advisory Services'),
('2024-11-20', 4, 9, 5, 70000, 21000, 'completed', 'upsell', 'Premium R&D'),
('2024-12-05', 5, 7, 4, 180000, 54000, 'completed', 'renewal', 'Software License');

-- Add some pending/cancelled transactions for testing filters
INSERT INTO transactions (transaction_date, agent_id, client_id, company_id, amount, cost, status, transaction_type, category) VALUES
('2024-12-15', 1, 1, 1, 100000, 30000, 'pending', 'sale', 'Future Deal'),
('2024-11-01', 2, 5, 3, 40000, 12000, 'cancelled', 'sale', 'Cancelled Deal');

-- Update sequences
SELECT setval('companies_id_seq', (SELECT MAX(id) FROM companies));
SELECT setval('clients_id_seq', (SELECT MAX(id) FROM clients));
SELECT setval('agents_id_seq', (SELECT MAX(id) FROM agents));
SELECT setval('transactions_id_seq', (SELECT MAX(id) FROM transactions));
