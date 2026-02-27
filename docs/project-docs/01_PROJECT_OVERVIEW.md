# Ottobon Jobs — Project Overview

---

## 1. What is Ottobon Jobs?

Ottobon Jobs is an AI-powered recruitment platform built to bridge the gap between job seekers and employers. The platform goes beyond traditional job boards by offering intelligent features that help candidates understand exactly what a role demands, how well they fit, and what steps they need to take to become a strong applicant.

The platform is accessible at **jobs.ottobon.cloud**.

---

## 2. The Problem We Solve

Traditional job boards have three major shortcomings:

1. **No Guidance** — Candidates see a job listing but receive no help understanding whether they are qualified or how to improve.
2. **No Personalization** — Every user sees the same generic job description regardless of their background.
3. **No Support** — Once a candidate finds a gap in their skills, they are left on their own to figure out next steps.

Ottobon Jobs addresses all three by combining automated job scraping, AI-generated career advice, and real-time human coaching into a single platform.

---

## 3. Key Features

### For Job Seekers
- **Job Feed** — Browse entry-level and intern positions scraped from Big 4 consulting firms (Deloitte, PwC, KPMG, EY).
- **Resume Upload** — Upload a PDF or DOCX resume. The system extracts text and generates a vector embedding for intelligent matching.
- **Enhanced Match Analysis** — See a percentage score showing fit, plus a **Gap Analysis** that identifies specific missing skills and provides **Learning Recommendations** (Upskill Bridge).
- **Resume Tailoring** — Automatically rewrite resume bullet points to align with a specific job description using AI.
- **4-Pillar Job Detail** — Every job listing is enriched with Description, Skills Required, Interview Prep Questions, and Resume Optimization Tips, plus an **Estimated Salary Range**.
- **Market Insights** — Access "Big 4 Campus Watch," an AI-generated weekly digest of the latest hiring trends and career news.
- **AI Career Coach** — Chat in real time with an AI assistant that gives personalized career advice based on your resume and target job.

### For Job Providers
- **Job Posting** — Create and manage job listings with title, description, and required skills.
- **AI Enrichment** — Every posted job is automatically enriched with interview prep questions, resume tips, and salary estimation.
- **Listings Dashboard** — View and manage all posted jobs in one place.

### For Admins
- **Control Tower** — Monitor active chat sessions. When a candidate asks a complex question the AI cannot handle, an admin can "tap in" and take over the conversation as a human agent.
- **Ingestion & Content Management** — Manually trigger job scraping or generate AI blog posts and market trend reports based on real-time RSS feeds.
- **Re-Enrichment** — Batch re-run AI enrichment for jobs that failed initial processing or require data backfilling.

---

## 4. Target Users

| User Type | Description | Example |
|-----------|-------------|---------|
| **Job Seeker** | Students, fresh graduates, and early-career professionals looking for entry-level roles or internships | A computer science student applying for a Full Stack Engineer internship |
| **Job Provider** | Employers or HR teams posting positions and seeking qualified candidates | A consulting firm posting an Analyst role |
| **Platform Admin** | Ottobon team members managing the platform, monitoring chats, and triggering data ingestion | An operations manager overseeing the Control Tower |

---

## 5. How It Works — End to End

### Step 1: Jobs Are Ingested & Market Data Fetched
Automated schedulers scrape job listings from Deloitte, PwC, KPMG, and EY daily at 10:00 PM IST. Simultaneously, the **Market News Service** pulls real-time career news to power the Market Insights section.

### Step 2: Jobs Are Enriched
Each new job is sent through an AI pipeline (using **Instructor** for structured output) that generates:
- 5 tailored interview preparation questions
- 5 resume optimization tips
- An estimated salary range
- A 1536-dimension vector embedding of the job description

### Step 3: Seekers Browse and Match
Seekers browse the job feed and upload their resume. The platform computes a cosine similarity score. If a gap is detected, the AI performs a deep **Gap Analysis** and maps missing skills to available learning resources.

### Step 4: Seekers Optimize & Prepare
Seekers can use the **Resume Tailoring** tool to refine their applications. They can also chat with the AI Career Coach for personalized guidance or review the AI-generated interview prep questions.

### Step 5: Human "Tap-In" Support
If the AI-human boundary is reached during coaching, a human admin can take over the chat in real time via the Control Tower.

---

## 6. Technology Summary

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.12+) |
| Frontend | React 18 + Vite |
| Database | Supabase (PostgreSQL + pgvector) |
| AI | OpenAI GPT-4o-mini (via Instructor) + text-embedding-3-small |
| File Storage | Supabase Storage |
| Authentication | Supabase Auth (JWT) |
| Scheduling | APScheduler with distributed locking |

---

## 7. Project Structure

```
Jobs/
├── backend/                    # FastAPI application
│   ├── main.py                 # Entry point
│   ├── app/
│   │   ├── adapters/           # Concrete implementations (Supabase, OpenAI, etc.)
│   │   ├── agents/             # AI Agents (Blog, Ingestion)
│   │   ├── domain/             # Pydantic models and enums
│   │   ├── ports/              # Abstract interfaces (ABCs)
│   │   ├── routers/            # API route handlers
│   │   ├── scraper/            # Job scraper adapters
│   │   ├── services/           # Business logic (Service Layer Pattern)
│   │   ├── config.py           # Environment configuration
│   │   ├── dependencies.py     # Dependency injection container
│   │   └── scheduler.py        # Background task scheduler
│   ├── migrations/             # SQL migration scripts
│   └── schema.sql              # Base database schema
│
├── Frontend/                   # React application
│   ├── src/
│   │   ├── api/                # Axios HTTP client modules
│   │   ├── components/         # Reusable UI components
│   │   ├── context/            # React Context (Auth)
│   │   ├── hooks/              # Custom hooks (useAuth, useWebSocket)
│   │   ├── pages/              # Page components by role
│   │   └── utils/              # Constants and helpers
│   └── index.html
│
└── docs/                       # Project documentation
```

---

## 8. Current Status

The platform is fully functional in a development environment with the following capabilities:
- **Core Platform**: Registration, login, and role-based access control.
- **Automated Ingestion**: Scrapers for Big 4 career sites and real-time news RSS feeds.
- **AI Enrichment**: Salary estimation, prep guides, and vector embeddings.
- **Upskill Bridge**: Automatic gap detection with learning resource mapping.
- **Resume Optimization**: Resume text extraction, embedding, and AI-driven tailoring.
- **Real-time Interaction**: WebSocket-powered AI Career Coach with admin takeover.
- **Architecture**: Enterprise-hardened with Service Layer Pattern, distributed locks, and RLS.
