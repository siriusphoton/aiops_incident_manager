-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Table 1: The Relational State Tracker for ITIL Problems
CREATE TABLE IF NOT EXISTS Active_Problems (
    parent_id VARCHAR(32) PRIMARY KEY, -- The ServiceNow sys_id of the parent incident
    incident_number VARCHAR(20) NOT NULL, -- e.g., INC0000052
    summary TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'Active',
    child_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table 2: The Vector Knowledge Base for SOPs
CREATE TABLE IF NOT EXISTS Knowledge_Base (
    id SERIAL PRIMARY KEY,
    sop_name VARCHAR(255) NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    -- 768 dimensions matches Google's text-embedding-004 model
    embedding vector(1024) 
);

-- Index for faster cosine similarity searches
CREATE INDEX ON Knowledge_Base USING hnsw (embedding vector_cosine_ops);