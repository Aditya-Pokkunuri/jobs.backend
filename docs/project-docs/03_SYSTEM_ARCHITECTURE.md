# Ottobon Jobs — System Architecture

---

## 1. Architectural Pattern

Ottobon Jobs follows the **Hexagonal Architecture** (also called Ports and Adapters). This pattern separates business logic from external systems, making the codebase testable, maintainable, and easy to extend.

### Core Principle

Business logic (Services) never directly calls external systems. Instead, it depends on abstract interfaces (Ports). Concrete implementations (Adapters) are injected at runtime through a Dependency Injection container.

```
┌─────────────────────────────────────────────────────────────┐
│                    HTTP / WebSocket Layer                    │
│                       (Routers)                             │
├─────────────────────────────────────────────────────────────┤
│                     Business Logic                          │
│                      (Services)                             │
│    AuthService · JobService · ChatService · MatchingService │
│    EnrichmentService · IngestionService · UserService       │
├─────────────────────────────────────────────────────────────┤
│                   Abstract Interfaces                       │
│                       (Ports)                               │
│   DatabasePort · AIPort · EmbeddingPort · StoragePort       │
│   DocumentPort · ScraperPort                                │
├─────────────────────────────────────────────────────────────┤
│                 Concrete Implementations                    │
│                      (Adapters)                             │
│  SupabaseAdapter · OpenAIAdapter · DocumentAdapter · ...    │
└─────────────────────────────────────────────────────────────┘
```

### Why This Matters

- **Swappable Providers** — To switch from OpenAI to a different AI provider, you change one adapter file and one line in the DI container. No service code changes.
- **Testability** — Services can be tested with mock adapters without needing real database or API connections.
- **Single Responsibility** — Each layer has a clear job. Routers handle HTTP concerns. Services handle business rules. Adapters handle external I/O.

---

## 2. System Components

### 2.1 Backend (FastAPI)

The backend is a Python FastAPI application that handles all business logic, API endpoints, and background processing.

**Key responsibilities:**
- REST API for user management, job operations, matching, and chat
- WebSocket server for real-time chat communication
- Background task scheduler for automated job scraping
- AI pipeline for job enrichment and resume processing

### 2.2 Frontend (React + Vite)

The frontend is a single-page React application that provides the user interface.

**Key responsibilities:**
- User authentication (login, registration)
- Job browsing, searching, and detail viewing
- Resume upload and match analysis
- Real-time chat interface
- Admin dashboards (Control Tower, Ingestion)

### 2.3 Database (Supabase / PostgreSQL)

Supabase provides a managed PostgreSQL database with built-in authentication, file storage, and real-time capabilities.

**Key responsibilities:**
- User profiles and credentials
- Job listings with AI-generated enrichment data
- Vector embeddings for semantic matching (via pgvector extension)
- Chat session state and conversation history
- Scraping logs and cron lock state

### 2.4 External Services

| Service | Purpose |
|---------|---------|
| **OpenAI GPT-4o-mini** | Generates interview prep questions and resume tips (structured output via Instructor library) |
| **OpenAI Embeddings** | Creates 1536-dimension vector representations of job descriptions and resumes |
| **Supabase Auth** | Handles user registration, login, and JWT token management |
| **Supabase Storage** | Stores uploaded resume files (PDF, DOCX) |
| **Career Sites** | Deloitte, PwC, KPMG, EY career pages are scraped for job listings |

---

## 3. Data Flow Diagram

### 3.1 Overall System Flow

```
┌──────────────┐     REST / WS      ┌──────────────┐
│              │ ────────────────►   │              │
│   Frontend   │                    │   Backend    │
│   (React)    │ ◄────────────────  │   (FastAPI)  │
│              │     JSON / WS      │              │
└──────┬───────┘                    └──────┬───────┘
       │                                   │
       │ Supabase Auth SDK                 │ Service Role Key
       │                                   │
       ▼                                   ▼
┌──────────────────────────────────────────────┐
│              Supabase Platform               │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Auth     │  │ Database │  │ Storage   │  │
│  │ (JWT)    │  │ (PG+vec) │  │ (Files)   │  │
│  └──────────┘  └──────────┘  └───────────┘  │
└──────────────────────────────────────────────┘
                                   │
                                   │ API calls
                                   ▼
                     ┌──────────────────────┐
                     │   OpenAI Platform    │
                     │  GPT-4o  Embeddings  │
                     └──────────────────────┘
```

### 3.2 Request Authentication Flow

```
1. User logs in via Supabase Auth SDK (frontend)
2. Supabase returns a JWT access token
3. Frontend stores the token and attaches it to every API request
4. Backend extracts the JWT from the Authorization header
5. Backend verifies the JWT signature using the Supabase JWT secret
6. Backend fetches/creates the user record in the database
7. The authenticated user object is passed to the route handler
```

### 3.3 Job Ingestion Flow

```
1. Scheduler triggers at 10:00 PM IST (or admin triggers manually)
2. Distributed lock check — only one worker proceeds
3. Each scraper fetches job listings from its target website
4. Deduplication check — skip jobs that already exist (by external ID)
5. SHA-256 hash check — if description matches an existing enriched job, copy the AI data
6. New unique jobs are inserted into the database
7. Each new job is sent through the AI enrichment pipeline
8. Job status changes from "processing" to "active"
9. Scraping log records the run statistics
10. Lock is released
```

### 3.4 Real-Time Chat Flow

```
1. Seeker opens the chat page
2. Frontend creates a chat session via REST API
3. Frontend opens a WebSocket connection to /ws/chat/{session_id}
4. Server replays the last 10 messages (state recovery)
5. Seeker sends a message via WebSocket
6. In AI mode: Server builds user context from resume, calls OpenAI, returns response
7. In Human mode: Server queues the message for admin response
8. Every 30 seconds, frontend sends a heartbeat ping to prevent idle disconnection
9. Admin can take over the session via POST /admin/takeover
10. WebSocket broadcasts the takeover event to the connected seeker
```

---

## 4. Technology Stack

### Backend Technologies

| Technology | Version | Purpose |
|-----------|---------|---------|
| Python | 3.12+ | Programming language |
| FastAPI | Latest | Web framework (async) |
| Uvicorn | Latest | ASGI server |
| Supabase Python | Latest | Database and storage client |
| OpenAI Python | Latest | AI API client |
| Instructor | Latest | Structured AI output (Pydantic models via LLM) |
| APScheduler | Latest | Background task scheduling |
| pypdf | Latest | PDF text extraction |
| python-docx | Latest | DOCX text extraction |
| aiohttp | Latest | Async HTTP client for web scraping |
| pydantic-settings | Latest | Environment variable management |
| PyJWT | Latest | JWT token verification |

### Frontend Technologies

| Technology | Version | Purpose |
|-----------|---------|---------|
| React | 18 | UI framework |
| Vite | Latest | Build tool and dev server |
| React Router | v6 | Client-side routing |
| Axios | Latest | HTTP client with interceptors |
| Supabase JS | Latest | Auth SDK |
| Lucide React | Latest | Icon library |
| Tailwind CSS | v4 | Utility-first CSS framework |

### Database and Infrastructure

| Technology | Purpose |
|-----------|---------|
| PostgreSQL (via Supabase) | Primary data store |
| pgvector extension | Vector similarity search |
| HNSW indexes | Fast approximate nearest-neighbor lookup |
| Row Level Security (RLS) | Database-level access control |
| Supabase Auth | User authentication and JWT issuing |
| Supabase Storage | File storage for resumes |

---

## 5. Security Architecture

### Authentication
- Supabase Auth handles registration and login
- JWT tokens are issued by Supabase and verified by the backend using the JWT secret
- Every protected endpoint requires a valid JWT in the Authorization header

### Authorization
- Role-based access control (Seeker, Provider, Admin)
- Frontend routes are guarded by ProtectedRoute component
- Backend endpoints check user role before executing privileged operations

### Database Security
- Row Level Security (RLS) policies enforce access rules at the PostgreSQL level
- Seekers can only read jobs with status "active"
- Providers can only modify their own jobs
- The backend connects with a service role key that bypasses RLS (trusted server-side code)

### API Security
- CORS is configured on the backend
- Axios interceptors auto-retry on 503 errors (up to 3 times)
- File uploads are validated for extension and content

---

## 6. Scalability Considerations

| Area | Current Design | Scale Strategy |
|------|----------------|----------------|
| API Server | Single Uvicorn worker with hot-reload | Multiple Uvicorn workers behind a load balancer |
| Database Queries | HNSW vector indexes for embedding queries | Indexes handle millions of rows with sub-ms latency |
| Cron Jobs | Distributed lock prevents duplicate runs | Works with any number of workers |
| WebSocket | In-memory connection manager | Replace with Redis Pub/Sub for multi-server support |
| AI Costs | SHA-256 hash dedup avoids redundant calls | OpenAI Batch API for 50% cost reduction |
| File Storage | Supabase Storage with signed URLs | CDN integration for global distribution |
