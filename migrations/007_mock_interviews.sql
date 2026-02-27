-- Migration 007: Mock Interviews Table
-- Purpose: Store AI-driven mock interview transcripts, scorecards, and expert feedback.

CREATE TABLE IF NOT EXISTS mock_interviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    transcript JSONB DEFAULT '[]'::jsonb NOT NULL,
    ai_scorecard JSONB, -- Stores {technical_accuracy, clarity, confidence, summary_notes}
    expert_feedback TEXT,
    status TEXT NOT NULL DEFAULT 'in_progress', -- in_progress, completed, pending_review, reviewed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Note: active_human status in chat_sessions is deprecated at the application level.
-- chat_status enum is left as-is to avoid migration complexity.

-- 1. Enable RLS
ALTER TABLE mock_interviews ENABLE ROW LEVEL SECURITY;

-- 2. Drop existing policies if they exist (for idempotency)
DROP POLICY IF EXISTS "Users can view own mock interviews" ON mock_interviews;
DROP POLICY IF EXISTS "Admins can view all mock interviews" ON mock_interviews;
DROP POLICY IF EXISTS "Users can start own mock interviews" ON mock_interviews;
DROP POLICY IF EXISTS "Admins can update mock interviews" ON mock_interviews;

-- 3. Define Policies

-- Seekers can see their own interviews
CREATE POLICY "Users can view own mock interviews" 
ON mock_interviews FOR SELECT 
TO authenticated
USING (auth.uid() = user_id);

-- Seekers can insert their own interviews
CREATE POLICY "Users can start own mock interviews" 
ON mock_interviews FOR INSERT 
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- Admins can access everything
CREATE POLICY "Admins can view all mock interviews" 
ON mock_interviews FOR ALL 
TO authenticated 
USING (
  EXISTS (
    SELECT 1 FROM users 
    WHERE users.id = auth.uid() 
    AND users.role = 'admin'
  )
);
