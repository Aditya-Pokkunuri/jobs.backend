-- Add password column to public.users table (as requested by user)
-- WARNING: Storing plain text passwords is a security risk.
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS password TEXT;
