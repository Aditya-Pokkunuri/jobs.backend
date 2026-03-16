-- Migration: Add qualification and experience to jobs_jobs
ALTER TABLE jobs_jobs ADD COLUMN IF NOT EXISTS qualification TEXT;
ALTER TABLE jobs_jobs ADD COLUMN IF NOT EXISTS experience TEXT;
