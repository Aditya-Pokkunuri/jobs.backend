-- ============================================================
-- Migration 004: Programmatic SEO (Blog Posts)
-- ============================================================

CREATE TABLE IF NOT EXISTS blog_posts (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug          TEXT UNIQUE NOT NULL,
    title         TEXT NOT NULL,
    summary       TEXT,
    content       TEXT NOT NULL, -- Markdown content
    image_url     TEXT,
    published_at  TIMESTAMPTZ DEFAULT NOW(),
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast slug lookups (public access)
CREATE INDEX IF NOT EXISTS idx_blog_posts_slug ON blog_posts (slug);
CREATE INDEX IF NOT EXISTS idx_blog_posts_published ON blog_posts (published_at DESC);

-- RLS: Public can read, only Service Role (Backend/Admin) can write
ALTER TABLE blog_posts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public can view blog posts"
ON blog_posts
FOR SELECT
TO anon, authenticated
USING (true);

-- (No insert/update policy needed for anon/authenticated, so they are denied by default)
