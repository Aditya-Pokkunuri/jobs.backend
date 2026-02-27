-- ============================================================
-- Migration: External Job Ingestion (v0.2.1)
-- Date: 2026-02-12
-- Description: Adds columns to support scraped/external job
--              listings and creates the system ingestion user.
-- ============================================================

-- 1. New columns on jobs table
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS external_id       TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS external_apply_url TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS company_name      TEXT DEFAULT 'ottobon';

-- 2. Compound unique constraint: prevents duplicate imports
--    Same external_id from different companies won't collide
ALTER TABLE jobs ADD CONSTRAINT uq_external_job UNIQUE (company_name, external_id);

-- 3. System user that "owns" all ingested/scraped jobs
INSERT INTO users (id, email, role, full_name)
VALUES (
  '00000000-0000-4000-a000-000000000001',
  'system-ingestion@ottobon.cloud',
  'provider',
  'External Job Ingestion'
)
ON CONFLICT (id) DO NOTHING;
