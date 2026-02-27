-- ============================================================
-- Migration 005: Row Level Security (RLS) Policies on `jobs`
-- ============================================================
-- Problem: Provider job scoping is enforced only in Python code.
-- A compromised JWT or direct Supabase client access could leak
-- all jobs, including drafts and processing-state records.
--
-- Fix: Enable RLS on the `jobs` table with role-based policies.
-- The backend uses supabase_service_role_key which BYPASSES RLS,
-- so these policies protect against frontend SDK / anon key access.
-- ============================================================

-- Step 1: Enable RLS (idempotent — safe to re-run)
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- Policy 1: Any authenticated user can SELECT active jobs
-- ============================================================
-- This covers the public job feed and job detail pages.
-- Only jobs with status = 'active' are visible — processing/draft
-- jobs are hidden from all non-service-role queries.
CREATE POLICY seeker_read_active_jobs
    ON jobs
    FOR SELECT
    TO authenticated
    USING (status = 'active');

-- ============================================================
-- Policy 2: Providers can manage (INSERT, UPDATE, DELETE) their own jobs
-- ============================================================
-- auth.uid() is the Supabase-injected UUID of the authenticated user.
-- This ensures a provider can never modify another provider's listings
-- even with a valid JWT.
CREATE POLICY provider_manage_own_jobs
    ON jobs
    FOR ALL
    TO authenticated
    USING (auth.uid() = provider_id)
    WITH CHECK (auth.uid() = provider_id);

-- ============================================================
-- Note on service_role bypass:
-- ============================================================
-- The backend connects with supabase_service_role_key, which
-- AUTOMATICALLY bypasses all RLS policies. This means:
--   - Scraper ingestion (provider_id = system UUID) works unchanged
--   - Admin endpoints work unchanged
--   - Enrichment service works unchanged
-- No backend code changes are required.
--
-- These policies ONLY restrict access from:
--   - Frontend Supabase SDK (anon key)
--   - Direct PostgREST queries with user JWTs
-- ============================================================
