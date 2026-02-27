# Ottobon Jobs — Database Schema and Migrations

---

## 1. Overview

The platform uses **Supabase** (managed PostgreSQL) as its primary data store. The database includes 5 tables, 2 custom enums, 1 custom function, vector indexes (HNSW), and Row Level Security (RLS) policies.

**Extensions:** `vector` (pgvector for embedding storage and similarity search)

---

## 2. Enums

### user_role

Defines the three roles in the system.

| Value | Description |
|-------|-------------|
| `seeker` | Job seeker (default) |
| `provider` | Job poster/employer |
| `admin` | Platform administrator |

### chat_status

Defines the state of a chat session.

| Value | Description |
|-------|-------------|
| `active_ai` | AI is currently handling messages (default) |
| `active_human` | A human admin has taken over |
| `closed` | Session is no longer active |

---

## 3. Tables

### 3.1 users

Stores user profiles and resume data.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| `id` | uuid | `auth.uid()` | PRIMARY KEY | Links to Supabase Auth user |
| `email` | text | — | UNIQUE, NOT NULL | User's email address |
| `role` | user_role | `'seeker'` | — | User's platform role |
| `full_name` | text | NULL | — | Display name |
| `resume_text` | text | NULL | — | Extracted text from uploaded resume |
| `resume_embedding` | vector(384) | NULL | — | Vector representation of resume text |
| `resume_file_url` | text | NULL | — | Storage path for uploaded resume file |
| `resume_file_name` | text | NULL | — | Original filename of uploaded resume |
| `created_at` | timestamptz | `now()` | — | Account creation timestamp |

**Notes:**
- The `id` defaults to `auth.uid()`, tying each row to the Supabase Auth user
- `resume_embedding` is stored as a 384-dimension vector (used by `text-embedding-3-small`)
- `resume_text` is populated during resume upload after text extraction

---

### 3.2 jobs

Stores job listings with AI-generated enrichment data.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| `id` | uuid | `gen_random_uuid()` | PRIMARY KEY | Auto-generated job ID |
| `provider_id` | uuid | — | REFERENCES users(id) | ID of the user who created the job |
| `title` | text | — | NOT NULL | Job title |
| `description_raw` | text | — | NOT NULL | Full job description |
| `skills_required` | jsonb | NULL | — | Array of required skills |
| `resume_guide_generated` | jsonb | NULL | — | AI-generated resume optimization tips (5 tips) |
| `prep_guide_generated` | jsonb | NULL | — | AI-generated interview prep questions (5 questions) |
| `embedding` | vector(384) | NULL | — | Vector representation of job description |
| `description_hash` | text | NULL | — | SHA-256 hash for deduplication cost savings |
| `status` | text | `'active'` | — | Job status: processing, active |
| `company_name` | text | NULL | — | Company name (set by scrapers) |
| `external_id` | text | NULL | — | External job ID from career site |
| `external_apply_url` | text | NULL | — | Link to apply on the company's site |
| `created_at` | timestamptz | `now()` | — | Job creation timestamp |

**Notes:**
- `description_hash` is a SHA-256 digest used to detect identical descriptions across different sources, enabling AI cost savings by copying existing enrichment data
- `embedding` is populated during the enrichment pipeline
- Status changes: `processing` → `active` once enrichment completes

---

### 3.3 chat_sessions

Stores real-time chat sessions between seekers and the AI/admin.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| `id` | uuid | `gen_random_uuid()` | PRIMARY KEY | Auto-generated session ID |
| `user_id` | uuid | — | REFERENCES users(id) | The seeker who owns this session |
| `status` | chat_status | `'active_ai'` | — | Current session mode |
| `conversation_log` | jsonb | `'[]'::jsonb` | — | Array of message objects |
| `created_at` | timestamptz | `now()` | — | Session creation timestamp |

**conversation_log format:**
```json
[
  {
    "role": "user",
    "content": "How do I improve my resume for this role?",
    "timestamp": "2026-02-17T10:00:00Z"
  },
  {
    "role": "assistant",
    "content": "Based on your experience with React...",
    "timestamp": "2026-02-17T10:00:05Z"
  }
]
```

---

### 3.4 scraping_logs

Tracks each scraping run for monitoring and debugging.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| `id` | uuid | `gen_random_uuid()` | PRIMARY KEY | Auto-generated log ID |
| `source_name` | text | — | NOT NULL | Scraper name: deloitte, pwc, kpmg, ey |
| `status` | text | `'running'` | — | Run status: running, completed, failed |
| `jobs_fetched` | integer | 0 | — | Total jobs fetched from source |
| `jobs_new` | integer | 0 | — | New jobs inserted |
| `jobs_skipped` | integer | 0 | — | Duplicate jobs skipped |
| `errors` | integer | 0 | — | Number of errors during run |
| `started_at` | timestamptz | `now()` | — | Run start timestamp |
| `completed_at` | timestamptz | NULL | — | Run completion timestamp |

---

### 3.5 cron_locks

Prevents duplicate scheduled tasks when running multiple server workers.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| `lock_name` | text | — | PRIMARY KEY | Unique lock identifier (e.g., "daily_ingestion") |
| `locked_by` | text | — | NOT NULL | Identifier of the worker that holds the lock |
| `locked_at` | timestamptz | `now()` | — | When the lock was acquired |
| `expires_at` | timestamptz | — | NOT NULL | When the lock automatically expires (TTL) |

**How it works:**
1. A worker tries to INSERT a lock row
2. If the row already exists and has not expired, the INSERT fails → worker skips the task
3. If the row is expired, it is replaced (upserted) → worker acquires the lock
4. After the task completes, the lock row is deleted

---

## 4. Functions

### match_jobs()

A stored PostgreSQL function for batch similarity search.

```sql
create or replace function match_jobs(
  query_embedding vector(384),
  match_count int default 10
)
returns table (id uuid, similarity float)
language plpgsql as $$
begin
  return query
    select jobs.id, 1 - (jobs.embedding <=> query_embedding) as similarity
    from jobs
    where jobs.embedding is not null
    order by jobs.embedding <=> query_embedding
    limit match_count;
end;
$$;
```

**What it does:**
- Takes a query vector and an optional count
- Returns job IDs with their cosine similarity score (0 to 1)
- Uses the `<=>` operator for cosine distance
- Filters out jobs with no embedding
- Ordered by most similar first

---

## 5. Indexes

### HNSW Vector Index

**Migration:** `004_hnsw_index.sql`

```sql
CREATE INDEX IF NOT EXISTS idx_jobs_embedding_hnsw
ON public.jobs USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**Purpose:** Enables sub-millisecond approximate nearest-neighbor search on job embeddings. Without this index, every similarity query would do a full sequential scan of all 1536-dimension vectors.

**Parameters:**
| Parameter | Value | Meaning |
|-----------|-------|---------|
| `m` | 16 | Max connections per node in the HNSW graph (higher = more accurate but slower build) |
| `ef_construction` | 64 | Candidate queue size during index build (higher = better quality index) |
| `vector_cosine_ops` | — | Optimized for cosine distance (`<=>` operator) |

---

## 6. Row Level Security (RLS)

**Migration:** `005_rls_policies.sql`

RLS policies enforce data access rules at the database level, providing defense-in-depth beyond application-level checks.

### Jobs Table Policies

**RLS is enabled on the `jobs` table.**

| Policy Name | Action | Role | Rule | Description |
|-------------|--------|------|------|-------------|
| `seeker_view_active_jobs` | SELECT | seeker | `status = 'active'` | Seekers can only see active jobs |
| `provider_manage_own_jobs` | ALL | provider | `auth.uid() = provider_id` | Providers can only access their own jobs |

### How RLS Works

```
┌─────────────────────────────────────────────────┐
│ Application sends query: SELECT * FROM jobs     │
├─────────────────────────────────────────────────┤
│ PostgreSQL checks:                              │
│   1. Is RLS enabled? → Yes                      │
│   2. What is auth.uid()? → user's JWT           │
│   3. What is the user's role?                   │
│   4. Apply the matching policy filter            │
│   5. Return only rows that pass                 │
└─────────────────────────────────────────────────┘
```

**Important:** The backend uses a `service_role_key` which bypasses RLS entirely. This is intentional — server-side code is trusted. RLS protects against direct database access and provides a safety net.

---

## 7. Migration Files

All migrations are in `backend/migrations/` and should be run in order via the Supabase SQL Editor.

| Order | File | Purpose |
|-------|------|---------|
| 1 | `schema.sql` | Base schema: tables, enums, `match_jobs()` function |
| 2 | `003_cron_locks.sql` | Create the `cron_locks` table for distributed scheduling |
| 3 | `004_hnsw_index.sql` | Add HNSW index on `jobs.embedding` for fast vector search |
| 4 | `005_rls_policies.sql` | Enable RLS on `jobs` table with seeker/provider policies |

### How to Run Migrations

1. Open the Supabase Dashboard for your project
2. Navigate to the SQL Editor
3. Copy and paste each migration file in order
4. Click "Run" for each one
5. Verify in the Table Editor that changes are applied

---

## 8. Entity Relationship Diagram

```
┌──────────────┐     provider_id     ┌──────────────┐
│    users     │────────────────────►│     jobs     │
│              │  (1 user : N jobs)  │              │
│  id (PK)     │                    │  id (PK)     │
│  email       │                    │  provider_id  │
│  role        │                    │  title        │
│  full_name   │                    │  description  │
│  resume_text │                    │  embedding    │
│  resume_emb  │                    │  status       │
└──────┬───────┘                    └──────────────┘
       │
       │ user_id
       │ (1 user : N sessions)
       ▼
┌──────────────┐
│ chat_sessions│
│              │
│  id (PK)     │
│  user_id     │
│  status      │
│  conv_log    │
└──────────────┘

┌──────────────┐                    ┌──────────────┐
│scraping_logs │                    │  cron_locks  │
│              │                    │              │
│  id (PK)     │                    │ lock_name(PK)│
│  source_name │                    │  locked_by   │
│  status      │                    │  locked_at   │
│  jobs_fetched│                    │  expires_at  │
└──────────────┘                    └──────────────┘
```
