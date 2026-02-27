-- ============================================================
-- Migration 006: Setup Blog Schema & Seed Data
-- ============================================================

-- 1. Create Table
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

-- 2. Create Indexes
CREATE INDEX IF NOT EXISTS idx_blog_posts_slug ON blog_posts (slug);
CREATE INDEX IF NOT EXISTS idx_blog_posts_published ON blog_posts (published_at DESC);

-- 3. Enable RLS
ALTER TABLE blog_posts ENABLE ROW LEVEL SECURITY;

-- 4. Create Policy (Public Read)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'blog_posts' AND policyname = 'Public can view blog posts'
    ) THEN
        CREATE POLICY "Public can view blog posts" ON blog_posts FOR SELECT TO anon, authenticated USING (true);
    END IF;
END
$$;

-- 5. Insert Sample Post (Seeding)
INSERT INTO blog_posts (slug, title, summary, content, published_at)
VALUES (
  'tech-skills-report-feb-2026',
  'Market Insights: Top Skills in Demand (February 2026)',
  'A curated analysis of the most sought-after technical skills across startups and enterprise tech jobs.',
  '# Market Update: February 2026

The job market is shifting rapidly towards AI-native development skills. Based on our analysis of active job postings on Ottobon, here are the key trends:

## Top 3 Growing Skills
1. **Agentic Frameworks** (LangChain, AutoGen)
2. **PostgreSQL / pgvector**
3. **Next.js App Router**

## Salary Insights
Software Engineers with RAG (Retrieval Augmented Generation) experience are seeing a premium in base salary offers compared to standard backend roles.

## Conclusion
Providers should consider updating their profiles to highlight experience with LLM orchestration and vector databases.',
  NOW()
)
ON CONFLICT (slug) DO NOTHING;
