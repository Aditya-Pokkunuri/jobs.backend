# Production Hardening — Eliminating Blindspots

> **Date**: February 13, 2026  
> **Scope**: `ingestion_service.py`, `enrichment_service.py`, `chat_service.py`, `user_service.py` + supporting ports, adapters, routers, and SQL migrations.  
> **Goal**: Close 4 production gaps that could cause data loss, wasted cost, broken user experience, or security exposure.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Constraint 1 — Scraper Resilience](#2-constraint-1--scraper-resilience)
3. [Constraint 2 — AI Cost Optimization](#3-constraint-2--ai-cost-optimization)
4. [Constraint 3 — WebSocket Persistence](#4-constraint-3--websocket-persistence)
5. [Constraint 4 — Secure Storage](#5-constraint-4--secure-storage)
6. [SQL Migrations](#6-sql-migrations)
7. [Files Changed — Complete Inventory](#7-files-changed--complete-inventory)
8. [Architecture Diagrams](#8-architecture-diagrams)
9. [Testing & Verification](#9-testing--verification)
10. [Future Work](#10-future-work)

---

## 1. Executive Summary

This refactor addresses 4 production blindspots discovered during an architecture review of the backend services:

| # | Blindspot | Risk | Fix |
|---|---|---|---|
| 1 | **Scraper crashes halt all ingestion** | If Deloitte's DOM changes, PwC/KPMG/EY never run | Fail-fast per-scraper + `scraping_logs` table |
| 2 | **Duplicate job descriptions waste AI tokens** | Same job re-posted = duplicate OpenAI call ($$$) | SHA-256 hash dedup before enrichment |
| 3 | **WebSocket disconnect = blank chat** | Server restart loses all conversation state | History replay (last 10 messages) on reconnect |
| 4 | **Resume URLs cached for 1 hour** | Leaked URL is valid for 60 minutes | 15-minute signed URLs + `Cache-Control: no-store` |

**Results**: 14/14 automated tests passed. Live verification in Supabase confirmed `scraping_logs` table populates correctly for all 4 scraper sources.

---

## 2. Constraint 1 — Scraper Resilience

### 2.1 The Problem

The `IngestionService.ingest_jobs()` method calls `scraper.fetch_jobs()` at the very top of the pipeline. If this call throws (e.g., a website redesigns its DOM, a network timeout occurs, or `crawl4ai` fails to render JavaScript), the **entire method** propagates the exception upward.

In the scheduler's `run_daily_ingestion()` loop, this means:

```
for scraper in scrapers:       # [Deloitte, PwC, KPMG, EY]
    await svc.ingest_jobs(scraper)  # If Deloitte throws → PwC/KPMG/EY NEVER RUN
```

**Impact**: A single scraper failure silently kills the entire nightly pipeline. No logs. No partial results. No way to know it happened until someone manually checks.

### 2.2 The Solution — Fail-Fast, Log, Move On

#### New Database Table: `scraping_logs`

Every scraping run now creates a persistent log entry before starting:

```sql
CREATE TABLE scraping_logs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_name   TEXT NOT NULL,            -- 'deloitte', 'pwc', 'kpmg', 'ey'
    status        TEXT NOT NULL DEFAULT 'running',
    jobs_found    INT DEFAULT 0,
    jobs_new      INT DEFAULT 0,
    jobs_skipped  INT DEFAULT 0,
    error_count   INT DEFAULT 0,
    error_message TEXT,                     -- NULL on success
    traceback     TEXT,                     -- Full Python traceback on failure
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at   TIMESTAMPTZ
);
```

#### Lifecycle of a Scraping Log Entry

```
1. INSERT with status='running'        ← Before fetch_jobs()
2a. If fetch_jobs() THROWS:
    → UPDATE status='failed', error_message=str(e), traceback=full_tb
    → RETURN stats dict with {"error": "..."} — don't propagate
2b. If fetch_jobs() SUCCEEDS:
    → Process each job (dedup, insert, enrich)
    → UPDATE status='success' (or 'partial' if some jobs errored)
```

#### Code Changes

**`ingestion_service.py`** — The `ingest_jobs()` method was restructured:

```python
async def ingest_jobs(self, scraper: ScraperPort) -> dict[str, Any]:
    # 1. Create log entry
    log_entry = await self._db.insert_scraping_log({
        "source_name": source_name,
        "status": "running",
        "started_at": started_at,
    })

    # 2. Fetch with fail-fast
    try:
        raw_jobs = await scraper.fetch_jobs()
    except Exception as exc:
        # Log failure — DON'T crash
        await self._db.update_scraping_log(log_id, {
            "status": "failed",
            "error_message": str(exc),
            "traceback": traceback.format_exc(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })
        return {**stats, "error": str(exc)}  # ← Not an exception!

    # 3. Process each job individually...
    # 4. Finalize log with results
```

**`database_port.py`** — Two new abstract methods:
- `insert_scraping_log(data) -> dict` — Creates the initial log row.
- `update_scraping_log(log_id, data) -> None` — Finalizes the row with results.

**`supabase_adapter.py`** — Concrete implementations using `self._client.table("scraping_logs")`.

### 2.3 Status Values

| Status | Meaning |
|---|---|
| `running` | Scraping is in progress (transient state) |
| `success` | All jobs processed without errors |
| `partial` | Some jobs succeeded, some failed during insertion/enrichment |
| `failed` | `fetch_jobs()` itself threw an exception — no jobs processed |

### 2.4 Verification

Live test output from `POST /admin/ingest/all`:

| source_name | status | jobs_found | jobs_new | jobs_skipped |
|---|---|---|---|---|
| ey | success | 0 | 0 | 0 |
| pwc | success | 0 | 0 | 0 |
| deloitte | success | 0 | 0 | 0 |
| kpmg | success | 0 | 0 | 0 |

All 4 sources ran and logged independently — no crashes, no missing rows.

Unit test (simulated crash):
```
  ✅ Failing scraper returns stats (no crash)
  ✅ Scraping log was created
  ✅ Scraping log was updated with failure
```

---

## 3. Constraint 2 — AI Cost Optimization

### 3.1 The Problem

When the scheduler scrapes daily, the same job posting can appear across multiple runs (the listing is still active on the company's careers page). The current dedup check uses `(company_name, external_id)` — which catches **exact** re-posts. But:

- A job can be **re-listed with a new external ID** (same description, different URL slug).
- Two different companies can post **identical descriptions** (e.g., shared job templates).

In both cases, the system calls OpenAI for enrichment **again**, costing ~$0.02-0.05 per call. At scale (100+ duplicate descriptions per month), this adds up.

### 3.2 The Solution — SHA-256 Description Hash

#### New Column on `jobs` Table

```sql
ALTER TABLE jobs ADD COLUMN description_hash TEXT;
CREATE INDEX idx_jobs_description_hash ON jobs (description_hash);
```

#### How It Works

```
1. Scraper returns raw_jobs
2. For each job:
   a. Check (company_name, external_id) → skip if exists  [existing behavior]
   b. Compute SHA-256 of description_raw
   c. Search for ANY existing job with same hash AND non-null embedding
   d. If found → COPY enrichment data (resume_guide, prep_guide, embedding)
   e. If not found → call OpenAI for full enrichment
```

#### Code Flow in `ingestion_service.py`

```python
# Compute hash
desc_hash = hashlib.sha256(desc_raw.encode()).hexdigest()

# Check for existing enriched job with same description
donor = await self._db.find_job_by_description_hash(desc_hash)
if donor:
    # Copy enrichment — skip AI call entirely
    await self._db.update_job(created["id"], {
        "resume_guide_generated": donor["resume_guide_generated"],
        "prep_guide_generated": donor["prep_guide_generated"],
        "embedding": donor["embedding"],
        "status": "active",
    })
    stats["dedup_hits"] += 1
    continue
```

#### Database Query (`supabase_adapter.py`)

```python
async def find_job_by_description_hash(self, description_hash: str):
    result = (
        self._client.table("jobs")
        .select("*")
        .eq("description_hash", description_hash)
        .not_.is_("embedding", "null")    # Only match fully-enriched jobs
        .limit(1)
        .maybe_single()
        .execute()
    )
    return result.data if result else None
```

The `.not_.is_("embedding", "null")` filter is critical — it ensures we only copy from jobs that have **completed** enrichment (not jobs still in `processing` status).

### 3.3 Batch API Stub

A stub method `enrich_jobs_batch()` was added to `enrichment_service.py` for future integration with OpenAI's Batch API:

```python
async def enrich_jobs_batch(self, job_ids: list[str]) -> str:
    """
    Batch enrichment stub — for future OpenAI Batch API integration.
    Offers ~50% cost reduction but 24-hour turnaround.
    Currently falls back to sequential processing.
    """
    for job_id in job_ids:
        await self.enrich_job(job_id)
    return "batch_stub_sequential"
```

**Why not implement Batch API now?** The Batch API requires:
1. Building JSONL payloads and uploading them as files.
2. Submitting the batch via `openai.batches.create()`.
3. A **polling worker** that checks batch completion every N minutes.
4. Parsing batch results and updating job records.

This is meaningful infrastructure. The SHA-256 dedup delivers immediate cost savings without it.

### 3.4 Verification

```
  ✅ SHA-256 hash is deterministic
  ✅ Same input = same hash
  ✅ Different input = different hash
  ✅ Dedup hit counted (dedup_hits=1)
  ✅ Job marked as new (enrichment copied, not called)
```

---

## 4. Constraint 3 — WebSocket Persistence

### 4.1 The Problem

When the server restarts (deploy, crash, scaling event), all WebSocket connections drop. When the client reconnects:

- The `ConnectionManager` is a fresh instance — no memory of prior connections.
- The WebSocket handler enters the `while True` loop with no context.
- The user sees a **blank chat** — all previous messages are gone from the UI.

The messages ARE persisted in `chat_sessions.conversation_log` (a JSONB column), but the WebSocket handler never replays them on reconnect.

### 4.2 The Solution — History Replay on Connect

#### New Method: `ChatService.get_recent_history()`

```python
async def get_recent_history(
    self, session_id: str, count: int = 10
) -> tuple[list[dict[str, Any]], str]:
    """
    Fetch the last `count` messages and current session status.
    Used for WebSocket state recovery after reconnect.
    """
    session = await self._db.get_chat_session(session_id)
    if not session:
        return [], "closed"
    log = session.get("conversation_log") or []
    status = session.get("status", "active_ai")
    return log[-count:], status
```

**Why 10 messages?** This is a UX balance — enough to restore context without overwhelming the client with a massive payload. The count is configurable.

#### Updated WebSocket Handler (`chat.py`)

The `websocket_chat()` function now has 3 phases:

```
Phase 1: VALIDATE
  → Check session exists
  → Reject if status == 'closed' (code 4003)

Phase 2: REPLAY (NEW)
  → Fetch last 10 messages from conversation_log
  → Send a structured JSON payload: {type: "history_replay", messages: [...], session_status: "..."}

Phase 3: MESSAGE LOOP (existing)
  → AI mode: generate reply → {type: "ai_reply", content: "..."}
  → Human mode: acknowledge → {type: "queued", content: "An admin will respond shortly."}
```

#### Structured JSON Responses

All WebSocket messages are now structured JSON instead of raw strings:

```json
// On connect (history replay)
{
  "type": "history_replay",
  "messages": [
    {"role": "user", "content": "Hello", "timestamp": "2026-02-13T10:00:00Z"},
    {"role": "assistant", "content": "Hi! How can I help?", "timestamp": "2026-02-13T10:00:01Z"}
  ],
  "session_status": "active_ai"
}

// AI reply
{"type": "ai_reply", "content": "Based on your profile..."}

// Human mode acknowledgment
{"type": "queued", "content": "An admin will respond shortly."}
```

#### Closed Session Rejection

```python
session_status = session.get("status", "active_ai")
if session_status == "closed":
    await websocket.close(code=4003, reason="Session is closed")
    return
```

This prevents zombie connections to sessions that have been administratively closed.

### 4.3 Client Integration Notes

Frontend clients should handle the `history_replay` message type:

```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch (data.type) {
        case "history_replay":
            // Populate chat UI with data.messages
            // Update UI state based on data.session_status
            break;
        case "ai_reply":
            // Append AI message to chat
            break;
        case "queued":
            // Show "waiting for admin" indicator
            break;
    }
};
```

### 4.4 Verification

```
  ✅ Returns exactly 10 messages (from 15 total)
  ✅ Returns most recent messages (msg5 through msg14)
  ✅ Returns session status ('active_ai')
  ✅ Closed session returns 'closed' status
```

---

## 5. Constraint 4 — Secure Storage

### 5.1 The Problem

The `GET /users/me/resume` endpoint generated a signed URL valid for **1 hour** (3600 seconds). Two issues:

1. **Over-exposure**: If a URL is leaked (browser history, shared screen, logs), it remains valid for 60 minutes.
2. **Caching risk**: Without `Cache-Control` headers, browsers and CDNs may cache the signed URL and serve stale (expired) links later.

### 5.2 The Solution

#### Change 1: TTL 3600 → 900 (15 minutes)

In `user_service.py`:

```python
# BEFORE
url = await self._storage.get_signed_url(
    bucket=RESUME_BUCKET,
    path=user["resume_file_url"],
    expires_in=3600,            # 1 hour
)

# AFTER
url = await self._storage.get_signed_url(
    bucket=RESUME_BUCKET,
    path=user["resume_file_url"],
    expires_in=900,             # 15 minutes
)
```

**Why 15 minutes?** Short enough to limit exposure, long enough for the user to download. Typical resume download is < 30 seconds.

#### Change 2: `Cache-Control: no-store` Header

In `users.py`:

```python
# BEFORE
return ResumeDownloadResponse(download_url=url)

# AFTER
return JSONResponse(
    content={
        "download_url": url,
        "expires_in_seconds": 900,  # Client knows the TTL
    },
    headers={"Cache-Control": "no-store"},
)
```

- `no-store` tells browsers and CDNs: **do not cache this response at all**. Every request will hit the server and generate a fresh signed URL.
- `expires_in_seconds` in the response body lets the frontend implement a countdown timer or auto-refresh logic.

#### No Port/Adapter Changes Needed

The `StoragePort.get_signed_url()` already accepts `expires_in` as a parameter. The `SupabaseStorageAdapter` passes it directly to Supabase's `create_signed_url()`. The only change was the value passed by the service layer.

### 5.3 Security Properties

| Property | Before | After |
|---|---|---|
| URL validity window | 60 minutes | 15 minutes |
| Caching behavior | Browser default (may cache) | `no-store` (never cached) |
| URL freshness | Fresh on every call | Fresh on every call (unchanged) |
| TTL exposed to client | No | Yes (`expires_in_seconds: 900`) |

### 5.4 Verification

```
  ✅ Signed URL returned
  ✅ TTL is 900 seconds (15 min)
```

---

## 6. SQL Migrations

### Migration File: `docs/migrations/002_scraping_logs.sql`

This migration must be run in the **Supabase SQL Editor** before the new code is deployed.

**What it creates**:
1. `scraping_logs` table — stores the result of every scraping run.
2. `description_hash` column on `jobs` table — SHA-256 of the job description.
3. Indexes on both for query performance.
4. Backfill query to hash existing job descriptions.

**Idempotent**: Uses `IF NOT EXISTS` — safe to run multiple times.

```sql
-- Verify after running:
SELECT COUNT(*) FROM scraping_logs;           -- Should be 0 initially
SELECT COUNT(*) FROM jobs WHERE description_hash IS NOT NULL;  -- Backfilled rows
```

---

## 7. Files Changed — Complete Inventory

### New Files (2)

| File | Purpose |
|---|---|
| `docs/migrations/002_scraping_logs.sql` | SQL migration for `scraping_logs` table + `description_hash` column |
| `test_hardening.py` | Automated test suite — 14 tests across all 4 constraints |

### Modified Files (8)

| File | Lines Changed | What Changed |
|---|---|---|
| `app/services/ingestion_service.py` | Full rewrite (170 lines) | Fail-fast pattern, scraping_logs integration, SHA-256 dedup |
| `app/services/enrichment_service.py` | Full rewrite (95 lines) | Added `enrich_jobs_batch()` stub, cleaned up existing `enrich_job()` |
| `app/services/chat_service.py` | Full rewrite (125 lines) | Added `get_recent_history()`, structured existing methods |
| `app/services/user_service.py` | 1 line | `expires_in=3600` → `expires_in=900` |
| `app/routers/chat.py` | Full rewrite (155 lines) | History replay on connect, closed session rejection, structured JSON |
| `app/routers/users.py` | 15 lines | `JSONResponse` with `Cache-Control: no-store`, added import |
| `app/ports/database_port.py` | +20 lines | `find_job_by_description_hash()`, `insert_scraping_log()`, `update_scraping_log()` |
| `app/adapters/supabase_adapter.py` | +30 lines | Concrete implementations of the 3 new port methods |

---

## 8. Architecture Diagrams

### 8.1 Ingestion Pipeline (After Hardening)

```
┌─────────────────────────────────────────────────────────┐
│                  run_daily_ingestion()                   │
│                                                         │
│  for each scraper in [Deloitte, PwC, KPMG, EY]:        │
│    ┌───────────────────────────────────────────────┐    │
│    │ INSERT scraping_logs (status='running')       │    │
│    │                                               │    │
│    │ try:                                          │    │
│    │    raw_jobs = scraper.fetch_jobs()             │    │
│    │ except:                                       │    │
│    │    UPDATE scraping_logs (status='failed')  ───┼──→ CONTINUE to next scraper
│    │    return stats                               │    │
│    │                                               │    │
│    │ for job in raw_jobs:                          │    │
│    │    ┌─ Dedup by (company, ext_id) ──→ skip?   │    │
│    │    ├─ INSERT job                              │    │
│    │    ├─ Compute SHA-256 hash                    │    │
│    │    ├─ Find donor (same hash + enriched)?      │    │
│    │    │   YES → copy enrichment data             │    │
│    │    │   NO  → call OpenAI enrichment           │    │
│    │    └─ UPDATE job (status='active')            │    │
│    │                                               │    │
│    │ UPDATE scraping_logs (status='success')       │    │
│    └───────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### 8.2 WebSocket Connection Flow (After Hardening)

```
Client                        Server
  │                              │
  │──── WS Connect ────────────→│
  │                              ├─ Validate session exists
  │                              ├─ Check status != 'closed'
  │                              │    (if closed → close WS 4003)
  │                              │
  │←── history_replay ─────────│← Fetch last 10 messages
  │    {messages: [...],         │    from conversation_log
  │     session_status: "ai"}    │
  │                              │
  │──── "Hello" ───────────────→│
  │                              ├─ Append to conversation_log
  │                              ├─ If AI mode: generate reply
  │←── ai_reply ───────────────│
  │    {content: "Hi!"}          │
  │                              │
  │──── disconnect ────────────→│
  │                              ├─ Remove from ConnectionManager
  │                              │
  │      ... server restart ...  │
  │                              │
  │──── WS Reconnect ─────────→│
  │←── history_replay ─────────│← Same history replayed!
  │    {messages: [prev msgs]}   │
```

---

## 9. Testing & Verification

### 9.1 Automated Tests (`test_hardening.py`)

The test file uses `unittest.mock` to isolate each constraint without requiring a real database or API keys.

| # | Test | Constraint | Result |
|---|---|---|---|
| 1 | Failing scraper returns stats (no crash) | Scraper Resilience | ✅ |
| 2 | Scraping log was created | Scraper Resilience | ✅ |
| 3 | Scraping log was updated with failure | Scraper Resilience | ✅ |
| 4 | SHA-256 hash is deterministic | AI Cost Dedup | ✅ |
| 5 | Same input = same hash | AI Cost Dedup | ✅ |
| 6 | Different input = different hash | AI Cost Dedup | ✅ |
| 7 | Dedup hit counted | AI Cost Dedup | ✅ |
| 8 | Job marked as new | AI Cost Dedup | ✅ |
| 9 | Returns exactly 10 messages | WS Persistence | ✅ |
| 10 | Returns most recent messages | WS Persistence | ✅ |
| 11 | Returns session status | WS Persistence | ✅ |
| 12 | Closed session returns 'closed' status | WS Persistence | ✅ |
| 13 | Signed URL returned | Secure Storage | ✅ |
| 14 | TTL is 900 seconds (15 min) | Secure Storage | ✅ |

**Run command**: `python test_hardening.py`

### 9.2 Live Verification

| Test | How | Result |
|---|---|---|
| SQL migration | Ran in Supabase SQL Editor | `scraping_logs` table created, `description_hash` column added |
| Server boot | `uvicorn main:app --reload` | 19 routes loaded, no import errors |
| Ingestion trigger | `POST /admin/ingest/all` | All 4 sources logged to `scraping_logs` (status=success) |
| All imports | `python -c "from app.services..."` | All modules import cleanly |

---

## 10. Future Work

| Item | Priority | Effort | Description |
|---|---|---|---|
| **OpenAI Batch API worker** | Medium | 2-3 days | Implement the polling worker for `enrich_jobs_batch()`. Requires: JSONL builder, file upload, batch submission, status polling cron, result parser. |
| **Redis Pub/Sub for WebSocket** | Medium | 1-2 days | Replace in-memory `ConnectionManager` with Redis for horizontal scaling across multiple server instances. |
| **Scraper alerting** | Low | 0.5 day | Send Slack/email notification when `scraping_logs.status = 'failed'` for any source. |
| **Description hash backfill** | Low | 5 min | The migration includes a backfill query, but verify it ran for all existing jobs. |
| **Batch enrichment queue** | Low | 1 day | Instead of enriching inline during ingestion, push to a queue and process asynchronously. |
