-- Migration 002: Scraper Resilience + AI Cost Optimization
-- Run this in the Supabase SQL Editor.

-- ═══════════════════════════════════════════════════════════
-- 1. scraping_logs table — persists every scraping run result
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS scraping_logs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_name   TEXT NOT NULL,           -- 'deloitte', 'pwc', 'kpmg', 'ey'
    status        TEXT NOT NULL DEFAULT 'running',  -- 'success' | 'partial' | 'failed'
    jobs_found    INT DEFAULT 0,
    jobs_new      INT DEFAULT 0,
    jobs_skipped  INT DEFAULT 0,
    error_count   INT DEFAULT 0,
    error_message TEXT,                    -- NULL on success
    traceback     TEXT,                    -- Full Python traceback on failure
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at   TIMESTAMPTZ
);

-- Index for quick lookups by source
CREATE INDEX IF NOT EXISTS idx_scraping_logs_source
    ON scraping_logs (source_name, started_at DESC);

-- ═══════════════════════════════════════════════════════════
-- 2. description_hash column on jobs — SHA-256 deduplication
-- ═══════════════════════════════════════════════════════════
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS description_hash TEXT;

CREATE INDEX IF NOT EXISTS idx_jobs_description_hash
    ON jobs (description_hash);

-- Backfill existing jobs (safe to re-run)
UPDATE jobs
SET description_hash = encode(sha256(description_raw::bytea), 'hex')
WHERE description_hash IS NULL
  AND description_raw IS NOT NULL;
