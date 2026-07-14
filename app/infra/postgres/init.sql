-- WicScan Risk Manager — PostgreSQL initialization
-- Extensions required by the application

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Enable row-level security support
ALTER DATABASE wicscan SET timezone TO 'UTC';
