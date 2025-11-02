-- Initialize OSRS Diff database
-- This script runs when the PostgreSQL container starts for the first time

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set timezone
SET timezone = 'UTC';

-- Create indexes for better performance (will be managed by Alembic migrations later)
-- This is just a placeholder for any initial database setup