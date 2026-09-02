-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create a sample table for storing embeddings
CREATE TABLE IF NOT EXISTS documents (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    content TEXT NOT NULL,
    metadata JSON,
    embedding vector (1536),
    fts TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('english', content)
    ) STORED,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- HNSW index for vector search
-- https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes
CREATE INDEX IF NOT EXISTS documents_embedding_idx ON documents USING hnsw (embedding vector_ip_ops);

-- Full-text search index
CREATE INDEX IF NOT EXISTS documents_fts_idx ON documents USING GIN (fts);

-- Create a GIN index on metadata for efficient JSON queries
CREATE INDEX IF NOT EXISTS documents_metadata_idx ON documents USING GIN (metadata);