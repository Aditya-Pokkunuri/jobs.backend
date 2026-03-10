-- ============================================================
-- Data Migration: Personal Supabase → Org Supabase
-- ============================================================
-- Purpose: Copy all data from old tables (personal) to new
--          *_jobs tables (org) without touching other org tables.
--
-- Tables: 7 total (no mock_interviews)
--   users → users_jobs
--   jobs → jobs_jobs
--   chat_sessions → chat_sessions_jobs
--   cron_locks → cron_locks_jobs  (SKIP — transient, scheduler recreates)
--   scraping_logs → scraping_logs_jobs
--   blog_posts → blog_posts_jobs
--   learning_resources → learning_resources_jobs
--
-- Strategy:
--   STEP 1 — Export CSVs from PERSONAL Supabase (SQL Editor)
--   STEP 2 — Import CSVs into ORG Supabase (Table Editor)
--         OR paste data as INSERT statements below
-- ============================================================


-- ╔══════════════════════════════════════════════════════════╗
-- ║  STEP 1: EXPORT — Run on PERSONAL Supabase SQL Editor   ║
-- ║  Click "Download CSV" on each result set                 ║
-- ╚══════════════════════════════════════════════════════════╝

-- 1. Users (export first — other tables depend on user IDs)
SELECT id, email, role, full_name, resume_text,
       resume_file_url, resume_file_name, created_at
FROM users;
-- NOTE: resume_embedding (vector) may not export cleanly via CSV.
-- If you need embeddings, re-generate them after import.

-- 2. Jobs
SELECT id, provider_id, title, description_raw, skills_required,
       resume_guide_generated, prep_guide_generated,
       description_hash, status, company_name,
       external_id, external_apply_url, created_at
FROM jobs;
-- NOTE: embedding (vector) column excluded — re-generate after import.

-- 3. Chat Sessions
SELECT id, user_id, status, conversation_log, created_at
FROM chat_sessions;

-- 4. Scraping Logs
SELECT id, source_name, status, jobs_found, jobs_new, jobs_skipped,
       error_count, error_message, traceback, started_at, finished_at
FROM scraping_logs;

-- 5. Blog Posts
SELECT id, slug, title, summary, content, image_url, published_at, created_at
FROM blog_posts;

-- 6. Learning Resources
SELECT id, skill_name, resource_type, title, url, created_at
FROM learning_resources;

-- (cron_locks — SKIP, not needed)


-- ╔══════════════════════════════════════════════════════════╗
-- ║  STEP 2: IMPORT — Run on ORG Supabase                   ║
-- ║                                                          ║
-- ║  Option A: Table Editor → [table] → Import → upload CSV  ║
-- ║  Option B: Paste INSERT statements below                  ║
-- ╚══════════════════════════════════════════════════════════╝
--
-- IMPORT ORDER (foreign keys):
--   1. users_jobs        ← no deps
--   2. jobs_jobs         ← provider_id refs users_jobs
--   3. chat_sessions_jobs← user_id refs users_jobs
--   4–6. rest            ← no deps, any order
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. users → users_jobs  (IMPORT FIRST)
-- ─────────────────────────────────────────────────────────────
-- Paste your exported user rows here:
INSERT INTO users_jobs (id, email, role, full_name, resume_text, resume_file_url, resume_file_name, created_at)
VALUES
    -- ('uuid', 'email', 'seeker', 'name', 'resume...', 'url', 'file.pdf', '2026-01-01T00:00:00Z')
;


-- ─────────────────────────────────────────────────────────────
-- 2. jobs → jobs_jobs  (IMPORT SECOND)
-- ─────────────────────────────────────────────────────────────
INSERT INTO jobs_jobs (id, provider_id, title, description_raw, skills_required, resume_guide_generated, prep_guide_generated, description_hash, status, company_name, external_id, external_apply_url, created_at)
VALUES
    -- ('uuid', 'provider_uuid', 'title', 'desc', '["skill"]'::jsonb, '...'::jsonb, '...'::jsonb, 'hash', 'active', 'company', 'ext_id', 'url', '2026-01-01T00:00:00Z')
;


-- ─────────────────────────────────────────────────────────────
-- 3. chat_sessions → chat_sessions_jobs  (IMPORT THIRD)
-- ─────────────────────────────────────────────────────────────
INSERT INTO chat_sessions_jobs (id, user_id, status, conversation_log, created_at)
VALUES
    -- ('uuid', 'user_uuid', 'active_ai', '[]'::jsonb, '2026-01-01T00:00:00Z')
;


-- ─────────────────────────────────────────────────────────────
-- 4. scraping_logs → scraping_logs_jobs
-- ─────────────────────────────────────────────────────────────
INSERT INTO scraping_logs_jobs (id, source_name, status, jobs_found, jobs_new, jobs_skipped, error_count, error_message, traceback, started_at, finished_at)
VALUES
    -- ('uuid', 'deloitte', 'success', 50, 10, 40, 0, NULL, NULL, '2026-01-01T00:00:00Z', '2026-01-01T00:05:00Z')
;


-- ─────────────────────────────────────────────────────────────
-- 5. blog_posts → blog_posts_jobs
-- ─────────────────────────────────────────────────────────────
INSERT INTO blog_posts_jobs (id, slug, title, summary, content, image_url, published_at, created_at)
VALUES
    -- ('uuid', 'my-post', 'Title', 'Summary', '# Content', NULL, '2026-01-01', '2026-01-01')
;


-- ─────────────────────────────────────────────────────────────
-- 6. learning_resources → learning_resources_jobs
-- ─────────────────────────────────────────────────────────────
INSERT INTO learning_resources_jobs (id, skill_name, resource_type, title, url, created_at)
VALUES
    -- ('uuid', 'Docker', 'youtube', 'Docker Course', 'https://...', '2026-01-01')
;


-- ============================================================
-- STEP 3: VERIFY — Run on ORG Supabase after all imports
-- ============================================================
SELECT 'users_jobs' AS table_name, COUNT(*) AS row_count FROM users_jobs
UNION ALL SELECT 'jobs_jobs', COUNT(*) FROM jobs_jobs
UNION ALL SELECT 'chat_sessions_jobs', COUNT(*) FROM chat_sessions_jobs
UNION ALL SELECT 'scraping_logs_jobs', COUNT(*) FROM scraping_logs_jobs
UNION ALL SELECT 'blog_posts_jobs', COUNT(*) FROM blog_posts_jobs
UNION ALL SELECT 'learning_resources_jobs', COUNT(*) FROM learning_resources_jobs
ORDER BY table_name;
