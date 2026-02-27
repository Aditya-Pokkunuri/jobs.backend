# Ottobon Jobs — Deployment and Security Guide

---

## 1. Overview

This guide covers how to set up the Ottobon Jobs platform from scratch, configure all external services, and understand the security measures in place. It is written for developers and DevOps engineers.

---

## 2. Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.10+ | 3.12+ |
| Node.js | 18+ | 20+ |
| npm | 9+ | 10+ |
| Git | Any recent version | Latest |
| Supabase Account | Free tier | Pro tier for production |
| OpenAI API Key | Any plan | Pay-as-you-go with GPT-4o-mini access |

---

## 3. Supabase Setup

### 3.1 Create a Project

1. Go to [supabase.com](https://supabase.com) and create an account
2. Click "New Project"
3. Choose an organization and set:
   - Project name: `ottobon-jobs`
   - Database password: (save this securely)
   - Region: Choose the closest to your users
4. Wait for provisioning to complete

### 3.2 Apply Database Schema

1. Open the SQL Editor in your Supabase dashboard
2. Run these files in order:

| Step | File | Purpose |
|------|------|---------|
| 1 | `backend/schema.sql` | Base tables, enums, and `match_jobs()` function |
| 2 | `backend/migrations/003_cron_locks.sql` | Distributed cron lock table |
| 3 | `backend/migrations/004_hnsw_index.sql` | HNSW vector index for fast similarity search |
| 4 | `backend/migrations/005_rls_policies.sql` | Row Level Security policies |

### 3.3 Create Storage Bucket

1. Go to Storage in the Supabase dashboard
2. Click "New Bucket"
3. Name: `resumes`
4. Set to "Private" (files are accessed via signed URLs)

### 3.4 Collect Keys

From the Supabase dashboard (Settings → API), collect:

| Key | Where to Find | Purpose |
|-----|---------------|---------|
| `SUPABASE_URL` | Project URL | Base URL for all Supabase API calls |
| `SUPABASE_KEY` | `anon` key | Public key for frontend auth |
| `SUPABASE_SERVICE_ROLE_KEY` | `service_role` key | Backend key (bypasses RLS) |
| `SUPABASE_JWT_SECRET` | JWT Settings | For verifying JWT tokens server-side |

---

## 4. OpenAI Setup

1. Go to [platform.openai.com](https://platform.openai.com) and create an account
2. Navigate to API Keys and generate a new key
3. Save the key as `OPENAI_API_KEY`
4. Ensure your account has access to:
   - `gpt-4o-mini` (for enrichment and chat)
   - `text-embedding-3-small` (for vector embeddings)

---

## 5. Environment Variables

### 5.1 Backend (.env)

Create a file at `backend/.env` with the following:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret
OPENAI_API_KEY=sk-your-openai-key
APP_NAME=jobs.ottobon.cloud
DEBUG=false
```

### 5.2 Frontend (.env)

Create a file at `Frontend/.env` with the following:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

For production, change `VITE_API_BASE_URL` to your deployed backend URL.

---

## 6. Local Development Setup

### 6.1 Backend

```bash
# Navigate to the backend directory
cd backend

# Create a Python virtual environment
python -m venv venv

# Activate the virtual environment
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the development server
uvicorn main:app --reload
```

The backend will be available at `http://localhost:8000`.
API documentation: `http://localhost:8000/docs`

### 6.2 Frontend

```bash
# Navigate to the frontend directory
cd Frontend

# Install dependencies
npm install

# Start the development server
npm run dev -- --host
```

The frontend will be available at `http://localhost:5173`.

### 6.3 Verify Everything Works

1. Open `http://localhost:8000/` → should return `{"status": "ok"}`
2. Open `http://localhost:8000/docs` → Swagger UI should load
3. Open `http://localhost:5173/login` → Login page should render
4. Register a new user → Check the Supabase users table for the new record

---

## 7. Production Deployment

### 7.1 Backend Deployment Options

| Platform | Command | Notes |
|----------|---------|-------|
| Render.com | Deploy as a Python web service | Set start command to `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Railway | Connect GitHub repo → auto-deploy | Set root directory to `backend/` |
| AWS EC2 | Manual setup with Nginx reverse proxy | Use Gunicorn with Uvicorn workers |
| Docker | Build with provided Dockerfile | Expose port 8000 |

### 7.2 Frontend Deployment Options

| Platform | Command | Notes |
|----------|---------|-------|
| Vercel | Connect GitHub repo → auto-deploy | Framework: Vite, output: `dist/` |
| Netlify | Connect GitHub repo, set build command | Build: `npm run build`, publish: `dist/` |
| Cloudflare Pages | Connect GitHub repo → auto-deploy | Set root to `Frontend/` |

### 7.3 Production Checklist

| Item | Status | Notes |
|------|--------|-------|
| Backend CORS configuration | Required | Restrict origins to your frontend domain |
| HTTPS enabled | Required | All production traffic must be encrypted |
| Environment variables set | Required | Never commit `.env` files to Git |
| Database migrations applied | Required | Run all migrations in Supabase SQL Editor |
| Storage bucket created | Required | Create "resumes" bucket in Supabase |
| Supabase RLS enabled | Recommended | Apply `005_rls_policies.sql` |
| HNSW index created | Recommended | Apply `004_hnsw_index.sql` for performance |
| Multiple workers configured | Recommended | Use `--workers N` with Uvicorn/Gunicorn |

---

## 8. Security Measures

### 8.1 Authentication

| Layer | Mechanism | Detail |
|-------|-----------|--------|
| Frontend | Supabase Auth SDK | Handles registration, login, session management |
| Backend | JWT Verification | Every protected endpoint verifies the JWT signature |
| Token Refresh | Automatic | Supabase SDK auto-refreshes expired tokens |
| Session Storage | In-memory | Tokens are stored in the browser session (not localStorage) |

### 8.2 Authorization

| Role | Capabilities |
|------|-------------|
| Seeker | View active jobs, upload resume, match analysis, AI chat |
| Provider | All seeker capabilities + create jobs, view own listings, trigger ingestion |
| Admin | All capabilities + Control Tower takeover, ingestion management, re-enrichment |

Protection is enforced at three levels:
1. **Frontend:** `ProtectedRoute` component restricts page access by role
2. **Backend:** Route handlers check `current_user.role` before executing
3. **Database:** RLS policies restrict data access at the PostgreSQL level

### 8.3 Data Protection

| Measure | Description |
|---------|-------------|
| Row Level Security (RLS) | PostgreSQL enforces that seekers only see active jobs and providers only access their own data |
| Service Role Key | Backend uses a privileged key that bypasses RLS — only trusted server-side code has this key |
| Signed URLs | Resume files are accessed via time-limited signed URLs (15-minute expiry) |
| Input Validation | Pydantic models enforce strict input validation on all API endpoints |
| File Validation | Resume uploads are validated for extension and minimum content length |

### 8.4 API Security

| Measure | Description |
|---------|-------------|
| CORS | Configured in FastAPI middleware (restrict origins in production) |
| Rate Limiting | Not currently implemented — recommended for production (use FastAPI Limiter) |
| Error Handling | Errors return minimal information to prevent information leakage |
| Retry Logic | Frontend Axios interceptor retries 503 errors up to 3 times with backoff |

### 8.5 Infrastructure Security

| Measure | Description |
|---------|-------------|
| HTTPS | Required for production (TLS terminates at the load balancer or reverse proxy) |
| Environment Variables | Secrets stored in `.env` files excluded from Git via `.gitignore` |
| Database Encryption | Supabase provides encryption at rest and in transit |
| Key Rotation | OpenAI and Supabase keys should be rotated periodically |

---

## 9. Monitoring and Observability

### Current Logging

| Component | Logging Method |
|-----------|---------------|
| Backend | Python `logging` module with INFO level by default |
| Scheduler | Logs lock acquisition, task execution, and completion |
| Ingestion | Logs per-source statistics (fetched, new, skipped, errors) |
| Re-enrichment | Logs per-batch progress and individual job results |

### Recommended Additions for Production

| Tool | Purpose |
|------|---------|
| Sentry | Error tracking and alerting |
| Prometheus + Grafana | Metrics dashboards for API latency, error rates |
| Supabase Logs | Database query performance monitoring |
| CloudWatch / Datadog | Infrastructure monitoring for server health |

---

## 10. Backup and Recovery

| Area | Strategy |
|------|----------|
| Database | Supabase provides automatic daily backups (Pro plan) |
| Resume Files | Stored in Supabase Storage with redundancy |
| Application Code | Git version control (GitHub/GitLab) |
| Environment Config | Store secrets in a vault or encrypted secrets manager |
| Disaster Recovery | Re-deploy from Git, re-apply migrations, restore from Supabase backup |
