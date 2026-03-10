-- ============================================================
-- Org Supabase: Full Schema Setup for Jobs Project
-- ============================================================
-- Run this entire file in the ORG Supabase SQL Editor.
-- All tables use the _jobs suffix to avoid conflicts with
-- other org projects sharing the same Supabase instance.
--
-- Safe to re-run (uses IF NOT EXISTS / IF EXISTS checks).
-- ============================================================


-- ═══════════════════════════════════════════════════════════
-- 0. Extensions & Enums
-- ═══════════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS vector;

-- NOTE: Using TEXT + CHECK instead of custom ENUMs to avoid
-- conflicts with existing enums in the shared org database.


-- ═══════════════════════════════════════════════════════════
-- 1. users_jobs
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS users_jobs (
    id                UUID PRIMARY KEY DEFAULT auth.uid(),
    email             TEXT UNIQUE NOT NULL,
    role              TEXT DEFAULT 'seeker' CHECK (role IN ('seeker', 'provider', 'admin')),
    full_name         TEXT,
    resume_text       TEXT,
    resume_embedding  vector(384),
    resume_file_url   TEXT,
    resume_file_name  TEXT,
    password          TEXT,
    created_at        TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE users_jobs ENABLE ROW LEVEL SECURITY;


-- ═══════════════════════════════════════════════════════════
-- 2. jobs_jobs
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS jobs_jobs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id             UUID REFERENCES users_jobs(id),
    title                   TEXT NOT NULL,
    description_raw         TEXT NOT NULL,
    skills_required         JSONB,
    resume_guide_generated  JSONB,
    prep_guide_generated    JSONB,
    embedding               vector(384),
    description_hash        TEXT,
    status                  TEXT DEFAULT 'active',
    company_name            TEXT,
    external_id             TEXT,
    external_apply_url      TEXT,
    archived_at             TIMESTAMPTZ DEFAULT NULL,
    created_at              TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE jobs_jobs ENABLE ROW LEVEL SECURITY;

-- RLS: Authenticated users can read active jobs
CREATE POLICY seeker_read_active_jobs_jobs
    ON jobs_jobs
    FOR SELECT
    TO authenticated
    USING (status = 'active');

-- RLS: Providers can manage their own jobs
CREATE POLICY provider_manage_own_jobs_jobs
    ON jobs_jobs
    FOR ALL
    TO authenticated
    USING (auth.uid() = provider_id)
    WITH CHECK (auth.uid() = provider_id);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_jobs_jobs_description_hash
    ON jobs_jobs (description_hash);

CREATE INDEX IF NOT EXISTS idx_jobs_jobs_archived_at
    ON jobs_jobs (archived_at);

CREATE INDEX IF NOT EXISTS idx_jobs_jobs_embedding_hnsw
    ON jobs_jobs
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);


-- ═══════════════════════════════════════════════════════════
-- 3. chat_sessions_jobs
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS chat_sessions_jobs (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID REFERENCES users_jobs(id),
    status            TEXT DEFAULT 'active_ai' CHECK (status IN ('active_ai', 'active_human', 'closed')),
    conversation_log  JSONB DEFAULT '[]'::jsonb,
    created_at        TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE chat_sessions_jobs ENABLE ROW LEVEL SECURITY;


-- ═══════════════════════════════════════════════════════════
-- 4. scraping_logs_jobs
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS scraping_logs_jobs (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_name    TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'running',
    jobs_found     INT DEFAULT 0,
    jobs_new       INT DEFAULT 0,
    jobs_skipped   INT DEFAULT 0,
    error_count    INT DEFAULT 0,
    error_message  TEXT,
    traceback      TEXT,
    started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at    TIMESTAMPTZ
);

ALTER TABLE scraping_logs_jobs ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_scraping_logs_jobs_source
    ON scraping_logs_jobs (source_name, started_at DESC);


-- ═══════════════════════════════════════════════════════════
-- 5. cron_locks_jobs
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS cron_locks_jobs (
    lock_name    TEXT PRIMARY KEY,
    locked_by    TEXT,
    locked_at    TIMESTAMPTZ DEFAULT now(),
    locked_until TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE cron_locks_jobs ENABLE ROW LEVEL SECURITY;


-- ═══════════════════════════════════════════════════════════
-- 6. blog_posts_jobs
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS blog_posts_jobs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug          TEXT UNIQUE NOT NULL,
    title         TEXT NOT NULL,
    summary       TEXT,
    content       TEXT NOT NULL,
    image_url     TEXT,
    published_at  TIMESTAMPTZ DEFAULT now(),
    created_at    TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE blog_posts_jobs ENABLE ROW LEVEL SECURITY;

-- Public read access for blog posts
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'blog_posts_jobs'
          AND policyname = 'Public can view blog posts'
    ) THEN
        CREATE POLICY "Public can view blog posts"
            ON blog_posts_jobs
            FOR SELECT
            TO anon, authenticated
            USING (true);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_blog_posts_jobs_slug
    ON blog_posts_jobs (slug);

CREATE INDEX IF NOT EXISTS idx_blog_posts_jobs_published
    ON blog_posts_jobs (published_at DESC);


-- ═══════════════════════════════════════════════════════════
-- 7. learning_resources_jobs
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS learning_resources_jobs (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_name     TEXT NOT NULL UNIQUE,
    resource_type  TEXT DEFAULT 'youtube',
    title          TEXT NOT NULL,
    url            TEXT NOT NULL,
    created_at     TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE learning_resources_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable read access for all users"
    ON learning_resources_jobs
    FOR SELECT
    TO authenticated
    USING (true);


-- ═══════════════════════════════════════════════════════════
-- 8. HNSW Index on users_jobs.resume_embedding
-- ═══════════════════════════════════════════════════════════

CREATE INDEX IF NOT EXISTS idx_users_jobs_resume_embedding_hnsw
    ON users_jobs
    USING hnsw (resume_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);


-- ═══════════════════════════════════════════════════════════
-- 9. Functions
-- ═══════════════════════════════════════════════════════════

-- Distributed cron lock acquisition (used by scheduler.py)
CREATE OR REPLACE FUNCTION acquire_cron_lock(
    p_lock_name   TEXT,
    p_ttl_minutes INT DEFAULT 30
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    rows_affected INT;
BEGIN
    INSERT INTO cron_locks_jobs (lock_name, locked_at, locked_until)
    VALUES (
        p_lock_name,
        NOW(),
        NOW() + (p_ttl_minutes || ' minutes')::INTERVAL
    )
    ON CONFLICT (lock_name) DO UPDATE
        SET locked_at    = NOW(),
            locked_until = NOW() + (p_ttl_minutes || ' minutes')::INTERVAL
        WHERE cron_locks_jobs.locked_until < NOW();

    GET DIAGNOSTICS rows_affected = ROW_COUNT;
    RETURN rows_affected > 0;
END;
$$;


-- ═══════════════════════════════════════════════════════════
-- 10. Seed Data: Learning Resources
-- ═══════════════════════════════════════════════════════════

INSERT INTO learning_resources_jobs (skill_name, title, url) VALUES
    ('Docker', 'Docker for Beginners: Full Course', 'https://www.youtube.com/watch?v=3c-iBn73dDE'),
    ('React', 'React JS - React Tutorial for Beginners', 'https://www.youtube.com/watch?v=Ke90Tje7VS0'),
    ('Python', 'Python for Beginners - Full Course', 'https://www.youtube.com/watch?v=_uQrJ0TkZlc'),
    ('Node.js', 'Node.js and Express.js - Full Course', 'https://www.youtube.com/watch?v=Oe421EPjeBE'),
    ('AWS', 'AWS Certified Cloud Practitioner - Full Course', 'https://www.youtube.com/watch?v=SOTamWNgDKc')
ON CONFLICT (skill_name) DO NOTHING;


-- ═══════════════════════════════════════════════════════════
-- ✅ DONE — Verify table creation
-- ═══════════════════════════════════════════════════════════

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name LIKE '%_jobs'
ORDER BY table_name;
