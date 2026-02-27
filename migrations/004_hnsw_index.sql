-- ============================================================
-- Migration 004: pgvector HNSW Indexes
-- ============================================================
-- Problem: cosine similarity queries (<=>) on 1536-dimensional
-- vectors trigger full sequential scans on every match request.
--
-- Fix: HNSW (Hierarchical Navigable Small World) indexes provide
-- sub-millisecond approximate nearest-neighbor lookups.
--
-- Parameters:
--   m = 16              — graph fanout (higher = better recall, more RAM)
--   ef_construction = 64 — build-time search depth (higher = slower build, better index)
--
-- These defaults balance recall accuracy (~99%) against build cost.
-- ============================================================

-- Ensure pgvector extension is enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- HNSW index on jobs.embedding for match queries
-- Used by: POST /jobs/{id}/match (cosine similarity between user resume and job)
CREATE INDEX IF NOT EXISTS idx_jobs_embedding_hnsw
    ON jobs
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- HNSW index on users.resume_embedding for future nearest-job queries
-- Enables server-side "find best jobs for this user" without full scan
CREATE INDEX IF NOT EXISTS idx_users_resume_embedding_hnsw
    ON users
    USING hnsw (resume_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ============================================================
-- Note: After creating HNSW indexes, the database will need to
-- build the index graph. For large tables (>10k rows), this may
-- take a few minutes. The table remains queryable during build.
-- ============================================================
