-- Initialize pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Initialize pg_trgm extension for trigram-based text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE scoratis TO scoratis;
