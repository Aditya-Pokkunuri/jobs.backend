# jobs.ottobon.cloud — Backend Documentation

> **Version:** 0.3.0
> **Last Updated:** 2026-02-13
> **Stack:** FastAPI · Supabase (PostgreSQL + pgvector + Storage) · OpenAI · Python 3.10 · Crawl4AI · APScheduler

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture & SOLID Principles](#2-architecture--solid-principles)
3. [Directory Structure](#3-directory-structure)
4. [Database Schema](#4-database-schema)
5. [API Endpoints (15 Total)](#5-api-endpoints-15-total)
6. [Core Modules — Detailed Breakdown](#6-core-modules--detailed-breakdown)
7. [Job Ingestion & Scheduling](#7-job-ingestion--scheduling)
8. [AI Enrichment Pipeline](#8-ai-enrichment-pipeline)
9. [Resume Processing Pipeline](#9-resume-processing-pipeline)
10. [Control Tower — WebSocket Chat System](#10-control-tower--websocket-chat-system)
11. [Authentication Flow](#11-authentication-flow)
12. [Matching Engine](#12-matching-engine)
13. [Configuration & Environment](#13-configuration--environment)
14. [Setup & Run Instructions](#14-setup--run-instructions)
15. [Dependencies](#15-dependencies)
16. [API Testing Guide](#16-api-testing-guide)

---

## 1. Project Overview

**jobs.ottobon.cloud** is an Outcome-Driven Recruitment Ecosystem that connects job providers directly with job seekers. 

The platform operates on a **Hybrid Sourcing** model:
1.  **Direct Posting**: Providers post jobs via the platform.
2.  **Automated Ingestion**: A daily scheduler scrapes entry-level roles (0-2 years) from Big 4 firms (Deloitte, PwC, KPMG, EY).

### Core Features

| Feature | Description |
|---|---|
| **4-Pillar Generation** | For every job post (direct or scraped), AI automatically generates a Resume Optimization Guide (5 bullets) and an Interview Prep Roadmap (5 questions). |
| **Control Tower** | Real-time WebSocket chat where AI handles initial conversations, but a human admin can "tap in" and take over seamlessly. |
| **Skill Gap Analysis** | Vector-based cosine similarity between user resumes and job descriptions. Flags gaps when the match score falls below 0.7. |
| **Resume Storage** | Original resume files (PDF/DOCX) are stored in Supabase Storage with signed download URLs. Text is extracted and embedded for matching. |

### Roles

| Role | Capabilities |
|---|---|
| `seeker` | Upload resume (PDF/DOCX), browse jobs, check match scores, download resume, chat via WebSocket |
| `provider` | Post jobs (triggers AI enrichment), view their own listings |
| `admin` | Take over AI chat sessions, trigger manual ingestion, manage the Control Tower |

---

## 2. Architecture & SOLID Principles

The backend is built on a **Ports & Adapters (Hexagonal)** architecture with strict SOLID enforcement:

```
┌─────────────────────────────────────────────────────────┐
│                    ROUTERS (HTTP / WS)                   │
│  Thin layer — parse request → call service → respond    │
└───────────────────────────┬─────────────────────────────┘
                            │ calls
┌───────────────────────────▼─────────────────────────────┐
│                  SERVICES (Business Logic)               │
│  Orchestrates workflows, depends on PORTS only          │
└───────────────────────────┬─────────────────────────────┘
                            │ depends on
┌───────────────────────────▼─────────────────────────────┐
│               PORTS (Abstract Interfaces — ABCs)         │
│  AIPort · EmbeddingPort · DatabasePort · DocumentPort   │
│  StoragePort · ScraperPort                              │
└───────────────────────────┬─────────────────────────────┘
                            │ implemented by
┌───────────────────────────▼─────────────────────────────┐
│              ADAPTERS (Concrete Implementations)         │
│  OpenAI · Supabase · DocumentAdapter · Storage          │
│  DeloitteAdapter · PwCAdapter · KPMGAdapter · EYAdapter │
└─────────────────────────────────────────────────────────┘
```

### SOLID Mapping

| Principle | Implementation |
|---|---|
| **S — Single Responsibility** | Each file/class has exactly one concern. Routers contain zero business logic. Services handle only orchestration. Adapters handle only external I/O. |
| **O — Open/Closed** | To add a new AI provider (e.g., Anthropic, Ollama), create a new adapter implementing `AIPort`. Existing code remains untouched. |
| **L — Liskov Substitution** | Any class implementing `AIPort` can replace `OpenAIAdapter` without breaking the system. Same for all other ports. |
| **I — Interface Segregation** | Six small, focused ports instead of one large interface. Each port has 1–3 methods only. |
| **D — Dependency Inversion** | Services declare dependencies on abstract `Port` types. `dependencies.py` (the DI container) wires the concrete adapters at startup. |

---

## 3. Directory Structure

```
backend/
├── .env                          # Environment variables (SECRET — never commit)
├── .env.example                  # Template for required env vars
├── requirements.txt              # Python dependencies
├── main.py                       # FastAPI entry point
├── docs/                         # Documentation folder
│   ├── BACKEND_DOCUMENTATION.md  # This file
│   ├── SCRAPER_IMPLEMENTATION.md # Scraper specific docs
│   ├── API_TESTING_GUIDE.md      # Step-by-step API testing instructions
│   └── seed_test_data.sql        # SQL seed data
│
└── app/
    ├── __init__.py
    ├── config.py                 # pydantic-settings
    ├── dependencies.py           # DI container (ports → adapters)
    ├── scheduler.py              # APScheduler configuration
    │
    ├── domain/                   # ── Pure Data ──
    │   ├── enums.py              # UserRole, ChatStatus
    │   └── models.py             # Pydantic schemas
    │
    ├── ports/                    # ── Abstract Interfaces ──
    │   ├── ai_port.py            # generate_enrichment(), chat()
    │   ├── embedding_port.py     # encode()
    │   ├── database_port.py      # CRUD ops
    │   ├── document_port.py      # extract_text()
    │   ├── storage_port.py       # upload_file()
    │   └── scraper_port.py       # fetch_jobs() interface
    │
    ├── adapters/                 # ── Concrete Implementations ──
    │   ├── openai_adapter.py     # AIPort implementation
    │   ├── supabase_adapter.py   # DatabasePort implementation
    │   ├── ...                   # Other adapters
    │
    ├── scraper/                  # ── Web Scrapers ──
    │   ├── base_scraper.py       # Base class (Crawl4AI + BS4)
    │   ├── experience_filter.py  # 0-2 years logic
    │   ├── deloitte_adapter.py   # Deloitte implementation
    │   ├── pwc_adapter.py        # PwC implementation
    │   ├── kpmg_adapter.py       # KPMG implementation
    │   └── ey_adapter.py         # EY implementation
    │
    ├── services/                 # ── Business Logic ──
    │   ├── auth_service.py
    │   ├── user_service.py
    │   ├── job_service.py
    │   ├── ingestion_service.py  # Orchestrates scraping + saving
    │   ├── enrichment_service.py
    │   ├── matching_service.py
    │   └── chat_service.py
    │
    └── routers/                  # ── Thin HTTP/WS Layer ──
        ├── users.py
        ├── jobs.py
        ├── ingestion.py          # /admin/ingest/*
        ├── matching.py
        ├── chat.py
        └── admin.py
```

---

## 4. Database Schema

Three tables powered by Supabase (PostgreSQL 15+) with `pgvector` enabled.
One storage bucket for resume files.

### 4.1 `users`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | Linked to Supabase Auth user |
| `email` | TEXT (UNIQUE) | Required |
| `role` | ENUM | `seeker`, `provider`, `admin` |
| `resume_text` | TEXT | Extracted from PDF/DOCX |
| `resume_embedding` | VECTOR(384) | Generated by `text-embedding-3-small` |

### 4.2 `jobs`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | Auto-generated |
| `provider_id` | UUID (FK) | Who posted the job |
| `title` | TEXT | Required |
| `external_apply_url` | TEXT | For scraped jobs |
| `resume_guide_generated` | JSONB | AI output: 5 bullets |
| `prep_guide_generated` | JSONB | AI output: 5 questions |
| `embedding` | VECTOR(384) | Job description embedding |

### 4.3 `chat_sessions`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | Auto-generated |
| `status` | ENUM | `active_ai`, `active_human`, `closed` |
| `conversation_log` | JSONB | Array of message objects |

---

## 5. API Endpoints (15 Total)

### Admin & Ingestion
| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/admin/ingest/all` | ✓ (admin) | Trigger global ingestion (background task) |
| `POST` | `/admin/ingest/{source}` | ✓ (admin) | Trigger specific scraper (e.g., deloitte) |
| `POST` | `/admin/takeover` | ✓ (admin) | Switch chat to human mode |

### Users & Jobs
| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/users/me` | ✓ | Get profile |
| `POST` | `/users/resume` | ✓ | Upload PDF/DOCX |
| `GET` | `/users/me/resume` | ✓ | Get download URL |
| `POST` | `/jobs` | ✓ | Post new job |
| `GET` | `/jobs/feed` | ✗ | Public job feed |
| `GET` | `/jobs/{id}/details` | ✗ | Full job details |
| `POST` | `/jobs/{id}/match` | ✓ | Check fit score |

### Chat
| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/chat/sessions` | ✓ | Start session |
| `GET` | `/chat/sessions/{id}` | ✓ | Get info |
| `WS` | `/ws/chat/{session_id}` | ✗ | Real-time chat |

---

## 6. Core Modules — Detailed Breakdown

### 6.1 Dependency Injection (`app/dependencies.py`)
Central wiring. To add a new scraper, register it in `_SCRAPER_REGISTRY`.

### 6.2 Scrapers (`app/scraper/*`)
Inherit from `BaseScraper`. Use `crawl4ai` (Playwright) to fetch dynamic HTML, `BeautifulSoup` to parse, and `experience_filter.py` to select only 0-2 year roles.

### 6.3 Scheduling (`app/scheduler.py`)
Uses `APScheduler` (AsyncIO) to run `run_daily_ingestion()` every day at **10:00 PM IST**. Started via FastAPI lifespan events in `main.py`.

---

## 7. Job Ingestion & Scheduling

The system automatically scrapes jobs from Big 4 career pages.

### Workflow
1.  **Scheduler Trigger**: At 22:00 IST, `scheduler.py` wakes up.
2.  **Iterate Scrapers**: Loops through Deloitte, PwC, KPMG, EY adapters.
3.  **Fetch & Parse**:
    -   `crawl4ai` renders the page (handling React/Angular loading).
    -   `BeautifulSoup` extracts job cards.
    -   `experience_filter` drops senior roles.
4.  **Ingest Service**:
    -   Checks if job exists (by external ID).
    -   If new: Saves to DB → Triggers AI Enrichment.
    -   If exists: Updates status if needed.

---

## 8. AI Enrichment Pipeline

When a job is added (via API or Scraper):
1.  **Save to DB**.
2.  **Background Task**: `EnrichmentService` picks it up.
3.  **OpenAI Call**: Generates 5-bullet resume guide & 5-question interview prep.
4.  **Embedding**: Generates vector embedding for the description.
5.  **Update DB**: Saves enrichment data + embedding.

---

## 9. Resume Processing Pipeline

1.  **Upload**: User POSTs PDF/DOCX.
2.  **Storage**: Saved to `resumes` bucket (private).
3.  **Extract**: Text extracted via `pypdf` or `python-docx`.
4.  **Embed**: Text converted to 384-d vector.
5.  **Save**: User profile updated with text + embedding + file path.

---

## 10. Control Tower — WebSocket Chat System

Real-time chat with "Human Takeover" capability.
-   **AI Mode**: User chats with GPT-4o-mini.
-   **Human Mode**: Admin sends `POST /admin/takeover`. Subsequent user messages are ignored by AI and routed to Admin dashboard. Admin replies via WebSocket.

---

## 11. Authentication Flow

**Supabase Auth (JWT)**.
-   Client sends `Authorization: Bearer <token>`.
-   Middleware validates token with Supabase.
-   Resolves User ID to internal PostgreSQL UUID.

---

## 12. Matching Engine

**Cosine Similarity via `pgvector`**.
-   Compares `user.resume_embedding` vs `job.embedding`.
-   Score ≥ 0.7: Good match.
-   Score < 0.7: Gap detected.

---

## 13. Configuration & Environment

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Project URL |
| `SUPABASE_KEY` | Service Role / Anon Key |
| `OPENAI_API_KEY` | For AI & Embeddings |

---

## 14. Setup & Run Instructions

```bash
# 1. Setup venv
cd c:\Users\adity\Desktop\Jobs\backend
py -3.10 -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install deps (includes playwright)
pip install -r requirements.txt
playwright install

# 3. Environment
copy .env.example .env

# 4. Run Server
uvicorn main:app --reload

# 5. Admin Ingestion (Optional test)
# POST http://localhost:8000/admin/ingest/all
```

---

## 15. Dependencies

| Package | Purpose |
|---|---|
| `fastapi` | Web Framework |
| `supabase` | DB & Auth |
| `openai` | AI Intelligence |
| `crawl4ai` | **New**: Headless browsing for scrapers |
| `beautifulsoup4` | **New**: HTML parsing |
| `apscheduler` | **New**: Job scheduling |
| `instructor` | Structured AI outputs |
| `pgvector` | Vector DB support (DB side) |

---

## 16. API Testing Guide

See **[API_TESTING_GUIDE.md](./API_TESTING_GUIDE.md)** for detailed Curl/PowerShell examples.
