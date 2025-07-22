-- Setup for route embeddings
-- Creates a separate vectors schema for scalable embedding storage

-- Create vectors schema
CREATE SCHEMA IF NOT EXISTS vectors;

-- Enable pgvector extension (assuming it's available)
-- Note: This may need to be run by a superuser
-- CREATE EXTENSION IF NOT EXISTS vector;

-- Route embeddings table - stores multiple types of embeddings per route
CREATE TABLE IF NOT EXISTS vectors.route_embeddings (
    id SERIAL PRIMARY KEY,
    route_id INTEGER NOT NULL REFERENCES routes.Routes(id),
    content_type TEXT NOT NULL, -- 'full_route', 'community_context', 'user_context'
    content_source TEXT NOT NULL, -- The actual text that was embedded
    embedding vector(1536), -- OpenAI text-embedding-3-small dimensions
    metadata JSONB, -- Searchable metadata (grade, type, area, etc.)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Only one embedding per route per content type
    UNIQUE(route_id, content_type)
);

-- Performance indexes for vector similarity search
-- Note: ivfflat requires pgvector extension
-- CREATE INDEX IF NOT EXISTS route_embeddings_embedding_idx 
-- ON vectors.route_embeddings 
-- USING ivfflat (embedding vector_cosine_ops) 
-- WITH (lists = 100);

-- Standard indexes for filtering
CREATE INDEX IF NOT EXISTS route_embeddings_route_id_idx 
ON vectors.route_embeddings (route_id);

CREATE INDEX IF NOT EXISTS route_embeddings_content_type_idx 
ON vectors.route_embeddings (content_type);

-- GIN index for metadata filtering
CREATE INDEX IF NOT EXISTS route_embeddings_metadata_idx 
ON vectors.route_embeddings 
USING gin (metadata);

-- Track embedding generation progress
CREATE TABLE IF NOT EXISTS vectors.embedding_generation_log (
    id SERIAL PRIMARY KEY,
    route_id INTEGER NOT NULL REFERENCES routes.Routes(id),
    content_type TEXT NOT NULL,
    status TEXT NOT NULL, -- 'pending', 'processing', 'completed', 'failed'
    error_message TEXT,
    tokens_used INTEGER,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- View for easy access to routes needing embeddings
CREATE OR REPLACE VIEW vectors.routes_needing_embeddings AS
SELECT 
    r.id,
    r.route_name,
    r.yds_rating,
    r.route_type,
    r.region,
    r.main_area,
    CASE 
        WHEN re.route_id IS NULL THEN 'missing'
        WHEN re.updated_at < r.insert_date THEN 'stale'
        ELSE 'current'
    END as embedding_status
FROM routes.Routes r
LEFT JOIN vectors.route_embeddings re ON r.id = re.route_id AND re.content_type = 'full_route'
WHERE re.route_id IS NULL OR re.updated_at < r.insert_date
ORDER BY r.id;