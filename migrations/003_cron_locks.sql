-- ============================================================
-- Migration 003: Distributed Cron Locks
-- ============================================================
-- Prevents duplicate scheduled jobs when running multiple 
-- Uvicorn workers behind a load balancer.
--
-- How it works:
--   1. Each cron job (e.g. 'daily_ingestion') gets a row in cron_locks.
--   2. Before execution, a worker calls acquire_cron_lock(name, ttl).
--   3. The function atomically inserts/updates the lock row.
--   4. Only the first worker to claim the lock (locked_until < NOW())
--      gets TRUE back — all others get FALSE and skip execution.
--   5. The lock auto-expires after `ttl` minutes (crash recovery).
-- ============================================================

-- Table: one row per named cron job
CREATE TABLE IF NOT EXISTS cron_locks (
    lock_name   TEXT PRIMARY KEY,
    locked_by   TEXT,                          -- optional: worker identifier
    locked_at   TIMESTAMPTZ DEFAULT NOW(),
    locked_until TIMESTAMPTZ DEFAULT NOW()     -- expires immediately by default
);

-- No RLS needed — only accessed via service_role key from the backend.
-- Revoke anon/authenticated access for defense-in-depth.
ALTER TABLE cron_locks ENABLE ROW LEVEL SECURITY;
-- (No policies = deny all for non-service-role)

-- ============================================================
-- Function: acquire_cron_lock
-- ============================================================
-- Atomic lock acquisition using INSERT ... ON CONFLICT + conditional UPDATE.
-- Returns TRUE if the calling worker acquired the lock, FALSE otherwise.
--
-- Parameters:
--   p_lock_name   — unique identifier for the cron job (e.g. 'daily_ingestion')
--   p_ttl_minutes — how long the lock is held before auto-expiry (crash safety)
-- ============================================================
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
    -- Attempt to insert a new lock. If the lock_name already exists,
    -- only update if the existing lock has expired (locked_until < NOW()).
    INSERT INTO cron_locks (lock_name, locked_at, locked_until)
    VALUES (
        p_lock_name,
        NOW(),
        NOW() + (p_ttl_minutes || ' minutes')::INTERVAL
    )
    ON CONFLICT (lock_name) DO UPDATE
        SET locked_at    = NOW(),
            locked_until = NOW() + (p_ttl_minutes || ' minutes')::INTERVAL
        WHERE cron_locks.locked_until < NOW();   -- ← only if expired

    GET DIAGNOSTICS rows_affected = ROW_COUNT;

    -- ROW_COUNT = 1 means we either inserted or updated (lock acquired).
    -- ROW_COUNT = 0 means the ON CONFLICT matched but WHERE failed (lock held).
    RETURN rows_affected > 0;
END;
$$;
