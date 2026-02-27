# Ottobon Jobs — High-Level Design

---

## 1. Component Diagram

The platform consists of three main systems: Frontend, Backend, and External Services. Below is a breakdown of every component and how they interact.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React 18)                      │
│                                                                 │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ Auth    │  │ API      │  │ Pages    │  │ Components     │  │
│  │ Context │──│ Layer    │──│ (12)     │──│ (Layout + UI)  │  │
│  │         │  │ (Axios)  │  │          │  │                │  │
│  └────┬────┘  └────┬─────┘  └──────────┘  └────────────────┘  │
│       │            │                                            │
│       │            │        ┌──────────────┐                   │
│       │            │        │ useWebSocket │                   │
│       │            │        │ (Heartbeat)  │                   │
│       │            │        └──────┬───────┘                   │
└───────┼────────────┼───────────────┼───────────────────────────┘
        │            │               │
   Supabase     REST API        WebSocket
     Auth        (JWT)          Connection
        │            │               │
┌───────┼────────────┼───────────────┼───────────────────────────┐
│       ▼            ▼               ▼                            │
│                     BACKEND (FastAPI)                           │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    ROUTERS (6)                            │  │
│  │  users · jobs · matching · chat · admin · ingestion      │  │
│  └─────────────────────────┬────────────────────────────────┘  │
│                            │                                    │
│  ┌─────────────────────────▼────────────────────────────────┐  │
│  │                   SERVICES (7)                            │  │
│  │  AuthService · JobService · ChatService · MatchingService│  │
│  │  EnrichmentService · IngestionService · UserService      │  │
│  └─────────────────────────┬────────────────────────────────┘  │
│                            │                                    │
│  ┌─────────────────────────▼────────────────────────────────┐  │
│  │                    PORTS (6)                              │  │
│  │  DatabasePort · AIPort · EmbeddingPort · StoragePort     │  │
│  │  DocumentPort · ScraperPort                              │  │
│  └─────────────────────────┬────────────────────────────────┘  │
│                            │                                    │
│  ┌─────────────────────────▼────────────────────────────────┐  │
│  │                  ADAPTERS (8+)                            │  │
│  │  SupabaseAdapter · OpenAIAdapter · OpenAIEmbeddingAdapter│  │
│  │  SupabaseStorageAdapter · DocumentAdapter                │  │
│  │  DeloitteAdapter · PwCAdapter · KPMGAdapter · EYAdapter  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  SCHEDULER                               │  │
│  │  APScheduler + Distributed Cron Lock (Supabase)         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Service Interaction Map

This table shows which service depends on which port, and what adapter fulfills it.

| Service | Depends On (Ports) | Fulfilled By (Adapters) |
|---------|-------------------|-------------------------|
| AuthService | DatabasePort | SupabaseAdapter |
| JobService | DatabasePort | SupabaseAdapter |
| EnrichmentService | DatabasePort, AIPort, EmbeddingPort | SupabaseAdapter, OpenAIAdapter, OpenAIEmbeddingAdapter |
| MatchingService | DatabasePort | SupabaseAdapter |
| ChatService | DatabasePort, AIPort | SupabaseAdapter, OpenAIAdapter |
| UserService | DatabasePort, StoragePort, DocumentPort, EmbeddingPort | SupabaseAdapter, SupabaseStorageAdapter, DocumentAdapter, OpenAIEmbeddingAdapter |
| IngestionService | DatabasePort, AIPort, EmbeddingPort, ScraperPort | SupabaseAdapter, OpenAIAdapter, OpenAIEmbeddingAdapter, *Adapter |

---

## 3. Core Workflows

### 3.1 User Registration and Login

```
Step 1: User fills registration form (email, password, role)
Step 2: Frontend calls Supabase Auth SDK → signUp()
Step 3: Supabase creates the auth user and returns a JWT
Step 4: On first API call, backend's AuthService:
        a. Verifies the JWT
        b. Checks if a user record exists in the users table
        c. If not, creates one with the auth user's email and ID
Step 5: User is now authenticated and can access protected routes
```

### 3.2 Resume Upload and Processing

```
Step 1: Seeker selects a PDF or DOCX file on the Profile page
Step 2: Frontend sends the file to POST /users/resume
Step 3: Backend's UserService processes the file:
        a. Validates the file extension (pdf or docx)
        b. Sanitizes the filename and generates a unique storage path
        c. Uploads the file to Supabase Storage ("resumes" bucket)
        d. Extracts text from the file (offloaded to a threadpool)
        e. Generates a 1536-dimension embedding using OpenAI
        f. Saves the file URL, extracted text, and embedding to the user record
Step 4: Frontend shows success message with character count
```

### 3.3 Job Creation and Enrichment

```
Step 1: Provider fills the job creation form (title, description, skills)
Step 2: Frontend sends the data to POST /jobs
Step 3: Backend inserts the job with status "processing"
Step 4: Backend kicks off a background task:
        a. OpenAI generates 5 resume tips and 5 interview questions
        b. OpenAI generates a 1536-dimension embedding of the description
        c. Both are saved to the job record
        d. Job status is updated to "active"
Step 5: Job now appears in the feed with full 4-pillar detail
```

### 3.4 Match Analysis

```
Step 1: Seeker clicks "Check My Fit" on a job detail page
Step 2: Frontend sends a request to POST /jobs/{id}/match
Step 3: Backend's MatchingService:
        a. Fetches the user's resume embedding
        b. Fetches the job's description embedding
        c. Computes cosine similarity between the two vectors
        d. Flags a gap if the score is below 0.7
Step 4: Frontend displays the match score as a percentage gauge
        with a gap detection badge if applicable
```

### 3.5 Chat Session Lifecycle

```
Step 1: Seeker opens the Chat page
Step 2: Frontend creates a session via POST /chat/sessions
Step 3: Frontend connects to WebSocket at /ws/chat/{session_id}
Step 4: Server replays the last 10 messages (history recovery)
Step 5: Chat operates in AI mode:
        - User sends a message
        - Server builds context from user's resume
        - OpenAI generates a personalized response
        - Response is sent back via WebSocket
Step 6: (Optional) Admin takes over via POST /admin/takeover
        - Session switches to human mode
        - WebSocket broadcasts a notification to the seeker
        - Subsequent messages are queued for admin response
Step 7: Frontend sends a heartbeat ping every 30 seconds
```

### 3.6 Job Ingestion Pipeline

```
Step 1: Scheduler fires at 10:00 PM IST (or admin triggers manually)
Step 2: Worker acquires distributed lock (cron_locks table)
Step 3: For each scraper (Deloitte, PwC, KPMG, EY):
        a. Create a scraping log entry (status: "running")
        b. Fetch job data from the external career site
        c. For each job:
           - Check if it already exists (by company + external ID)
           - If new: insert into database
           - Check SHA-256 hash of description
           - If hash matches existing enriched job: copy AI data (cost savings)
           - If no match: run full AI enrichment pipeline
           - Set status to "active"
        d. Finalize scraping log with statistics
Step 4: Release distributed lock
```

---

## 4. Design Decisions

### 4.1 Why Hexagonal Architecture?

The platform integrates multiple external services (Supabase, OpenAI, career site scrapers). Each could change independently. By abstracting them behind ports, we can:
- Switch from OpenAI to another LLM provider without touching business logic
- Replace Supabase with a different database without changing services
- Add new scraper sources by creating one new adapter class

### 4.2 Why Cosine Similarity in Python (Not PostgreSQL)?

Currently, match calculations happen in Python rather than via PostgreSQL's built-in `<=>` operator. This is because:
- The matching is done for a single user-job pair (not a batch search)
- It gives us full control over error handling and score formatting
- The `match_jobs()` database function exists for future batch use cases

### 4.3 Why In-Memory WebSocket Manager?

The current ConnectionManager stores active WebSocket connections in a Python dictionary. This works for single-server deployments. For horizontal scaling, this would be replaced with Redis Pub/Sub to broadcast messages across multiple server instances.

### 4.4 Why SHA-256 Description Hashing?

When different companies post identical job descriptions, the AI enrichment would produce nearly identical output. By hashing the description and checking for existing enriched jobs with the same hash, we skip the OpenAI API call entirely and copy the existing data. This can save significant AI costs.

### 4.5 Why Distributed Cron Locks?

APScheduler runs inside each Uvicorn worker process. With multiple workers, the daily ingestion would run multiple times simultaneously. The Supabase-backed lock ensures exactly one worker executes the task, while others skip gracefully.

---

## 5. Error Handling Strategy

| Layer | Strategy |
|-------|----------|
| **Routers** | Raise HTTPException with appropriate status codes (400, 403, 404, 422, 500) |
| **Services** | Raise ValueError for business rule violations; let unexpected errors bubble up |
| **Adapters** | Log errors with full context; re-raise for services to handle |
| **Scheduler** | Catch and log all exceptions; never crash the scheduler itself |
| **Frontend** | Axios interceptors retry 503 errors; display user-friendly error messages |
| **WebSocket** | Reconnection is handled by the client; heartbeat prevents silent drops |
