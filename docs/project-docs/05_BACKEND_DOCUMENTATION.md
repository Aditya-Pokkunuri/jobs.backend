# Ottobon Jobs — Backend Documentation

---

## 1. Overview

The backend is a Python FastAPI application that serves as the core of the Ottobon Jobs platform. It handles all API requests, business logic, AI processing, real-time chat, and background job scheduling. The codebase follows a strict Hexagonal Architecture (Ports and Adapters) pattern.

**Entry point:** `backend/main.py`
**Framework:** FastAPI with Uvicorn (ASGI)
**Python version:** 3.12+

---

## 2. Application Entry Point

**File:** `backend/main.py`

The main application sets up:
- FastAPI instance with title, description, and version
- Lifespan manager that starts the scheduler on startup and stops it on shutdown
- CORS middleware (currently allows all origins for development)
- Six routers: users, jobs, matching, chat, admin, ingestion
- Health check endpoint: `GET /` returns `{"status": "ok"}`

---

## 3. Configuration

**File:** `backend/app/config.py`

Uses pydantic-settings to load and validate environment variables from a `.env` file.

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `SUPABASE_URL` | string | Yes | Supabase project URL |
| `SUPABASE_KEY` | string | Yes | Anon key (client-facing) |
| `SUPABASE_SERVICE_ROLE_KEY` | string | Yes | Service role key (bypasses RLS) |
| `SUPABASE_JWT_SECRET` | string | Yes | JWT signing secret for token verification |
| `OPENAI_API_KEY` | string | Yes | OpenAI API key for GPT and Embeddings |
| `APP_NAME` | string | No | Default: "jobs.ottobon.cloud" |
| `DEBUG` | boolean | No | Default: false |

The settings object is created as a singleton and imported wherever needed.

---

## 4. Dependency Injection Container

**File:** `backend/app/dependencies.py`

This file wires abstract Ports to concrete Adapters. It acts as the single place where you configure which implementation to use for each interface.

| Function | Returns | Adapter Used |
|----------|---------|-------------|
| `get_db()` | DatabasePort | SupabaseAdapter |
| `get_ai_service()` | AIPort | OpenAIAdapter |
| `get_embedding_service()` | EmbeddingPort | OpenAIEmbeddingAdapter |
| `get_storage()` | StoragePort | SupabaseStorageAdapter |
| `get_document_parser()` | DocumentPort | DocumentAdapter |
| `get_scraper(name)` | ScraperPort | Resolved from registry |
| `get_all_scrapers()` | list[ScraperPort] | All registered scrapers |

**Scraper Registry:**
```
deloitte → DeloitteAdapter
pwc      → PwCAdapter
kpmg     → KPMGAdapter
ey       → EYAdapter
```

Adapter instances are cached using `@lru_cache` to avoid creating new connections on every request.

---

## 5. Domain Models

**File:** `backend/app/domain/models.py`

All data transfer objects are defined as Pydantic models. They have no I/O or side effects — they are pure data containers.

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `UserProfile` | Response for user profile endpoint | id, email, role, full_name, resume_text |
| `ResumeUploadResponse` | Confirmation after resume upload | message, characters_extracted |
| `ResumeDownloadResponse` | Signed URL for resume download | download_url |
| `JobCreate` | Request body for creating a job | title (min 3 chars), description_raw (min 20 chars), skills_required |
| `JobDetail` | Full job response with AI data | id, title, description_raw, skills, resume_guide, prep_guide, company_name |
| `JobFeedItem` | Lightweight job for feed listing | id, title, skills, status, created_at, company_name |
| `JobCreateResponse` | Confirmation after job creation | id, message |
| `MatchResult` | Match analysis response | job_id, similarity_score (0-1), gap_detected (boolean) |
| `AIEnrichment` | Structured AI output (via Instructor) | resume_guide (5 tips), prep_questions (5 questions) |
| `ChatMessage` | Single chat message | role, content, timestamp |
| `ChatSessionInfo` | Chat session metadata | id, user_id, status, created_at |
| `TakeoverRequest` | Admin takeover request | session_id |

---

## 6. Services (Business Logic Layer)

The Service Layer serves as the **"brain"** of the application, orchestrating business logic while remaining isolated from transport (HTTP) and infrastructure (SQL/AI). For a deep dive into the architecture and DI patterns, see the [Service Layer Pattern](file:///C:/Users/adity/Desktop/Ottobon/Jobs/docs/SERVICE_LAYER_PATTERN.md) guide.

### Core Objectives:
- **Isolation**: Prevents API routers from becoming bloated.
- **Reusability**: Logic can be triggered by API, CLI, or background tasks.
- **Atomicity**: Coordinates multiple ports as a single business unit.

---

### 6.1 AuthService

**File:** `backend/app/services/auth_service.py`

Handles JWT verification and user session management.

- **`get_current_user`** — FastAPI dependency that:
  1. Extracts the Bearer token from the Authorization header
  2. Decodes and verifies the JWT using the Supabase JWT secret
  3. Looks up the user in the database
  4. If the user does not exist (first login), auto-provisions a new record
  5. Returns the complete user dictionary

### 6.2 UserService

**File:** `backend/app/services/user_service.py`

Handles user profile management and resume processing.

- **`get_profile(user_id)`** — Fetches the user record from the database
- **`process_resume(user_id, file)`** — Full resume processing pipeline:
  1. Sanitize filename and generate a unique path
  2. Upload the original file to Supabase Storage
  3. Extract text (offloaded to threadpool via `asyncio.to_thread`)
  4. Generate embedding via OpenAI
  5. Save file URL, text, and embedding to the user record
- **`get_resume_download_url(user_id)`** — Generates a 15-minute signed download URL

### 6.3 JobService

**File:** `backend/app/services/job_service.py`

Handles job CRUD operations.

- **`create_job(provider_id, title, description, skills)`** — Inserts a new job with status "processing"
- **`get_details(job_id)`** — Fetches full job details
- **`list_by_provider(provider_id)`** — Lists all jobs for a provider
- **`list_feed(skip, limit)`** — Paginated list of active jobs

### 6.4 EnrichmentService

**File:** `backend/app/services/enrichment_service.py`

Orchestrates the AI enrichment pipeline for each job.

- **`enrich_job(job_id)`** — Three-step enrichment:
  1. Call OpenAI to generate structured output (5 resume tips + 5 prep questions)
  2. Generate a 1536-dimension embedding of the job description
  3. Save both to the job record

The AI call uses the Instructor library for structured output, ensuring the response always conforms to the `AIEnrichment` Pydantic model.

### 6.5 MatchingService

**File:** `backend/app/services/matching_service.py`

Computes semantic similarity between a user's resume and a job listing.

- **`calculate_match(user_id, job_id)`** — Steps:
  1. Fetch user's `resume_embedding` and job's `embedding`
  2. Parse vectors (Supabase may return pgvector strings)
  3. Calculate cosine similarity
  4. Return score (0.0 to 1.0) with gap flag (threshold: 0.7)

### 6.6 ChatService

**File:** `backend/app/services/chat_service.py`

Manages chat sessions and message routing between AI and human agents.

- **`handle_message(session_id, text)`** — Routes messages based on session mode:
  - **AI mode**: Builds user context from resume → calls OpenAI → saves both messages to conversation log
  - **Human mode**: Saves user message only, returns None (admin responds separately)
- **`_build_user_context(user)`** — Creates a rich system prompt with the candidate's name and resume content
- **`get_recent_history(session_id, count)`** — Returns last N messages for WebSocket reconnection
- **`takeover(session_id)`** — Switches session from AI to human mode
- **`admin_reply(session_id, text)`** — Admin sends a message directly into the conversation

### 6.7 IngestionService

**File:** `backend/app/services/ingestion_service.py`

Manages the end-to-end job ingestion pipeline with resilience.

- **`ingest_jobs(scraper)`** — Full pipeline:
  1. Create scraping log entry (status: "running")
  2. Fetch jobs from the external scraper
  3. Deduplicate by (company_name, external_id)
  4. SHA-256 hash check for AI cost savings
  5. Insert new jobs and trigger enrichment
  6. Finalize scraping log with statistics

System ingestion uses a fixed provider ID: `00000000-0000-4000-a000-000000000001`

---

## 7. Adapters (External I/O Layer)

### 7.1 SupabaseAdapter (DatabasePort)

**File:** `backend/app/adapters/supabase_adapter.py`

Implements all database operations using the Supabase Python client.

| Method | Description |
|--------|-------------|
| `get_user(id)` | Fetch user by ID |
| `upsert_user(id, data)` | Create or update user record |
| `create_job(data)` | Insert a new job |
| `get_job(id)` | Fetch job by ID |
| `update_job(id, data)` | Partial update of a job |
| `list_jobs_by_provider(id)` | All jobs for a provider |
| `list_active_jobs(skip, limit)` | Paginated active job feed |
| `find_job_by_external_id(company, ext_id)` | Dedup lookup |
| `find_job_by_description_hash(hash)` | AI cost dedup lookup |
| `create_chat_session(user_id)` | Create new chat session |
| `get_chat_session(id)` | Fetch chat session |
| `update_chat_session(id, data)` | Update session state/log |
| `insert_scraping_log(data)` | Create scraping run log |
| `update_scraping_log(id, data)` | Finalize scraping log |

### 7.2 OpenAIAdapter (AIPort)

**File:** `backend/app/adapters/openai_adapter.py`

- **`generate_enrichment(description, skills)`** — Uses Instructor + GPT-4o-mini to produce structured `AIEnrichment` output (5 resume tips + 5 questions)
- **`chat(messages, user_context)`** — Conversational response for the Career Coach

### 7.3 OpenAIEmbeddingAdapter (EmbeddingPort)

**File:** `backend/app/adapters/openai_embedding.py`

- **`encode(text)`** — Calls OpenAI's `text-embedding-3-small` model → returns a list of 1536 floats

### 7.4 SupabaseStorageAdapter (StoragePort)

**File:** `backend/app/adapters/supabase_storage_adapter.py`

- **`upload_file(bucket, path, bytes, content_type)`** — Uploads a file to Supabase Storage
- **`get_signed_url(bucket, path, expires_in)`** — Generates a time-limited download URL

### 7.5 DocumentAdapter (DocumentPort)

**File:** `backend/app/adapters/document_adapter.py`

- **`extract_text(file_bytes, file_extension)`** — Routes to PDF or DOCX parser
- **`_extract_pdf(bytes)`** — Uses pypdf to extract text from all pages
- **`_extract_docx(bytes)`** — Uses python-docx to extract text from all paragraphs
- Both parsers are offloaded to a threadpool via `asyncio.to_thread()` to prevent blocking the event loop

### 7.6 Scraper Adapters (ScraperPort)

| Adapter | File | Target Site |
|---------|------|-------------|
| DeloitteAdapter | `backend/app/scraper/deloitte_adapter.py` | Deloitte India Careers |
| PwCAdapter | `backend/app/scraper/pwc_adapter.py` | PwC India Careers |
| KPMGAdapter | `backend/app/scraper/kpmg_adapter.py` | KPMG India Careers |
| EYAdapter | `backend/app/scraper/ey_adapter.py` | EY India Careers |

All scrapers implement `fetch_jobs()` which returns a list of dictionaries with: `title`, `company_name`, `external_id`, `description_raw`, `skills_required`, `external_apply_url`.

---

## 8. Scheduler

**File:** `backend/app/scheduler.py`

- Uses APScheduler's AsyncIOScheduler with a CronTrigger
- Runs daily at 10:00 PM IST (Asia/Kolkata timezone)
- Acquires a distributed lock before executing (prevents duplicate runs with multiple workers)
- Lock uses a `cron_locks` Supabase table with a 30-minute TTL
- Falls back gracefully if the migration has not been applied

---

## 9. Ports (Abstract Interfaces)

All ports are Python ABC classes with `@abstractmethod` declarations. They define the contract that adapters must fulfill.

| Port | File | Methods |
|------|------|---------|
| DatabasePort | `backend/app/ports/database_port.py` | 14 methods covering users, jobs, chat, scraping logs |
| AIPort | `backend/app/ports/ai_port.py` | generate_enrichment, chat |
| EmbeddingPort | `backend/app/ports/embedding_port.py` | encode |
| StoragePort | `backend/app/ports/storage_port.py` | upload_file, get_signed_url |
| DocumentPort | `backend/app/ports/document_port.py` | extract_text, supported_extensions |
| ScraperPort | `backend/app/scraper/scraper_port.py` | fetch_jobs |
