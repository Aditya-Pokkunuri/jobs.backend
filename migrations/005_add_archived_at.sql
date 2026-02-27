-- Add archived_at column to jobs table if it doesn't exist
ALTER TABLE jobs 
ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ DEFAULT NULL;

-- Index for performance (optional but recommended)
CREATE INDEX IF NOT EXISTS idx_jobs_archived_at ON jobs(archived_at);
