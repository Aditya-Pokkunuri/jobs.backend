-- Create learning_resources table
CREATE TABLE IF NOT EXISTS learning_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_name TEXT NOT NULL UNIQUE,
    resource_type TEXT DEFAULT 'youtube',
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Enable RLS
ALTER TABLE learning_resources ENABLE ROW LEVEL SECURITY;

-- Allow read access to all authenticated users
CREATE POLICY "Enable read access for all users" ON learning_resources
    FOR SELECT
    TO authenticated
    USING (true);

-- Seed data
INSERT INTO learning_resources (skill_name, title, url) VALUES
    ('Docker', 'Docker for Beginners: Full Course', 'https://www.youtube.com/watch?v=3c-iBn73dDE'),
    ('React', 'React JS - React Tutorial for Beginners', 'https://www.youtube.com/watch?v=Ke90Tje7VS0'),
    ('Python', 'Python for Beginners - Full Course', 'https://www.youtube.com/watch?v=_uQrJ0TkZlc'),
    ('Node.js', 'Node.js and Express.js - Full Course', 'https://www.youtube.com/watch?v=Oe421EPjeBE'),
    ('AWS', 'AWS Certified Cloud Practitioner - Full Course', 'https://www.youtube.com/watch?v=SOTamWNgDKc')
ON CONFLICT (skill_name) DO NOTHING;
