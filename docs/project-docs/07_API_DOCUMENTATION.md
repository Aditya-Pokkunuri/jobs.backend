# Ottobon Jobs — API Documentation

---

## 1. Overview

The Ottobon Jobs backend exposes a RESTful API over HTTP and a WebSocket endpoint for real-time chat. All endpoints are served by FastAPI and documented automatically at `/docs` (Swagger UI) and `/redoc`.

**Base URL:** `http://localhost:8000` (development)

**Authentication:** Most endpoints require a valid Supabase JWT token in the `Authorization: Bearer <token>` header. Endpoints marked as "Public" do not require authentication.

---

## 2. Health Check

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/` | No | Health check |

**Response:**
```json
{
  "status": "ok",
  "service": "jobs.ottobon.cloud"
}
```

---

## 3. Users Endpoints

### 3.1 Get My Profile

| Method | Path | Auth | Role |
|--------|------|------|------|
| `GET` | `/users/me` | Yes | Any |

Returns the authenticated user's profile information.

**Response (200):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "role": "seeker",
  "full_name": "John Doe",
  "resume_text": "Extracted text from resume...",
  "resume_file_url": "resumes/uuid/filename.pdf",
  "resume_file_name": "my_resume.pdf"
}
```

---

### 3.2 Upload Resume

| Method | Path | Auth | Role |
|--------|------|------|------|
| `POST` | `/users/resume` | Yes | Seeker |

Upload a PDF or DOCX resume file. The server extracts text, generates an embedding, and stores the file.

**Request:** `multipart/form-data`
- `file` (required): PDF or DOCX file

**Response (200):**
```json
{
  "message": "Resume processed successfully",
  "characters_extracted": 2847
}
```

**Errors:**
| Code | Reason |
|------|--------|
| 400 | Unsupported file type (not PDF or DOCX) |
| 400 | File appears to be scanned/image-based (< 50 characters extracted) |
| 422 | No file provided |

---

### 3.3 Get Resume Download URL

| Method | Path | Auth | Role |
|--------|------|------|------|
| `GET` | `/users/me/resume` | Yes | Seeker |

Returns a signed URL valid for 15 minutes to download the uploaded resume.

**Response (200):**
```json
{
  "download_url": "https://supabase.co/storage/v1/object/sign/resumes/..."
}
```

**Errors:**
| Code | Reason |
|------|--------|
| 404 | No resume uploaded |

---

## 4. Jobs Endpoints

### 4.1 Create Job

| Method | Path | Auth | Role |
|--------|------|------|------|
| `POST` | `/jobs` | Yes | Provider |

Create a new job listing. AI enrichment runs in the background.

**Request Body:**
```json
{
  "title": "Full Stack Engineer",
  "description_raw": "We are looking for a full stack engineer with...",
  "skills_required": ["React", "Node.js", "PostgreSQL"]
}
```

**Validation:**
- `title`: minimum 3 characters
- `description_raw`: minimum 20 characters
- `skills_required`: list of strings

**Response (202):**
```json
{
  "id": "uuid-of-created-job",
  "message": "Job created. AI enrichment processing in background."
}
```

---

### 4.2 List Provider Jobs

| Method | Path | Auth | Role |
|--------|------|------|------|
| `GET` | `/jobs/provider` | Yes | Provider |

Returns all jobs created by the authenticated provider.

**Response (200):**
```json
[
  {
    "id": "uuid",
    "title": "Full Stack Engineer",
    "description_raw": "...",
    "skills_required": ["React", "Node.js"],
    "resume_guide_generated": { ... },
    "prep_guide_generated": { ... },
    "status": "active",
    "created_at": "2026-02-17T10:00:00Z",
    "company_name": null,
    "external_apply_url": null
  }
]
```

---

### 4.3 Get Job Feed

| Method | Path | Auth | Role |
|--------|------|------|------|
| `GET` | `/jobs/feed` | No | Public |

Paginated list of active job listings. Returns lightweight items (no descriptions or guides).

**Query Parameters:**
| Parameter | Type | Default | Range |
|-----------|------|---------|-------|
| `skip` | integer | 0 | >= 0 |
| `limit` | integer | 20 | 1-100 |

**Response (200):**
```json
[
  {
    "id": "uuid",
    "title": "Data Analyst Intern",
    "skills_required": ["Python", "SQL"],
    "status": "active",
    "created_at": "2026-02-17T10:00:00Z",
    "company_name": "Deloitte",
    "external_apply_url": "https://careers.deloitte.com/..."
  }
]
```

---

### 4.4 Get Job Details

| Method | Path | Auth | Role |
|--------|------|------|------|
| `GET` | `/jobs/{job_id}/details` | No | Public |

Returns the full 4-pillar job detail including AI-generated content.

**Path Parameters:**
- `job_id` (string): UUID of the job

**Response (200):**
```json
{
  "id": "uuid",
  "title": "Full Stack Engineer",
  "description_raw": "Full description text...",
  "skills_required": ["React", "Node.js", "PostgreSQL"],
  "resume_guide_generated": {
    "resume_guide": [
      "Highlight your React project experience",
      "Add Node.js backend projects to your portfolio",
      "Include PostgreSQL query optimization examples",
      "Mention any full-stack deployment experience",
      "Add relevant certifications or courses"
    ]
  },
  "prep_guide_generated": {
    "prep_questions": [
      "Explain the difference between SSR and CSR in React",
      "How would you design a RESTful API for a CRUD application?",
      "Describe your experience with database indexing",
      "Walk through a recent full-stack project you built",
      "How do you handle authentication in a web application?"
    ]
  },
  "status": "active",
  "created_at": "2026-02-17T10:00:00Z",
  "company_name": "Deloitte",
  "external_apply_url": "https://careers.deloitte.com/..."
}
```

**Errors:**
| Code | Reason |
|------|--------|
| 404 | Job not found |

---

## 5. Matching Endpoint

### 5.1 Match User to Job

| Method | Path | Auth | Role |
|--------|------|------|------|
| `POST` | `/jobs/{job_id}/match` | Yes | Seeker |

Calculate cosine similarity between the user's resume embedding and the job's description embedding.

**Path Parameters:**
- `job_id` (string): UUID of the job

**Response (200):**
```json
{
  "job_id": "uuid",
  "similarity_score": 0.7234,
  "gap_detected": false
}
```

**Gap Detection:** Score below 0.7 = `gap_detected: true`

**Errors:**
| Code | Reason |
|------|--------|
| 422 | User has no resume embedding (upload a resume first) |
| 422 | Job has no embedding (AI enrichment still processing) |
| 500 | Matching calculation failed |

---

## 6. Chat Endpoints

### 6.1 Create Chat Session

| Method | Path | Auth | Role |
|--------|------|------|------|
| `POST` | `/chat/sessions` | Yes | Any |

Creates a new chat session for the authenticated user.

**Response (200):**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "status": "active_ai",
  "created_at": "2026-02-17T10:00:00Z"
}
```

---

### 6.2 Get Chat Session

| Method | Path | Auth | Role |
|--------|------|------|------|
| `GET` | `/chat/sessions/{session_id}` | Yes | Any |

Returns details of a specific chat session.

**Response (200):**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "status": "active_ai",
  "created_at": "2026-02-17T10:00:00Z"
}
```

---

### 6.3 WebSocket Chat

| Protocol | Path | Auth |
|----------|------|------|
| `WS` | `/ws/chat/{session_id}` | No (session validation on connect) |

Real-time bidirectional chat communication.

**Connection Flow:**
1. Client connects to `ws://localhost:8000/ws/chat/{session_id}`
2. Server validates the session exists and is not closed
3. Server sends a `history_replay` message with the last 10 messages

**Server Messages:**

```json
// History replay (sent on connect)
{
  "type": "history_replay",
  "messages": [
    { "role": "user", "content": "Hello", "timestamp": "..." },
    { "role": "assistant", "content": "Hi there!", "timestamp": "..." }
  ],
  "session_status": "active_ai"
}

// AI response
{
  "type": "ai_reply",
  "content": "Based on your resume, I recommend..."
}

// Message queued for human agent
{
  "type": "queued",
  "message": "Your message has been forwarded to a human agent"
}

// Admin takeover notification
{
  "event": "admin_takeover",
  "note": "A human agent has joined the chat."
}
```

**Client Messages:**
- Plain text string (the user's message)
- `__ping__` (heartbeat, sent every 30 seconds by the frontend)

---

## 7. Admin Endpoints

### 7.1 Admin Takeover

| Method | Path | Auth | Role |
|--------|------|------|------|
| `POST` | `/admin/takeover` | Yes | Admin |

Switch a chat session from AI mode to human mode.

**Request Body:**
```json
{
  "session_id": "uuid"
}
```

**Response (200):**
```json
{
  "message": "Takeover successful",
  "session_id": "uuid"
}
```

**Errors:**
| Code | Reason |
|------|--------|
| 403 | Not an admin |
| 404 | Session not found |

---

### 7.2 Trigger Ingestion (Manual)

| Method | Path | Auth | Role |
|--------|------|------|------|
| `POST` | `/admin/ingest/trigger` | Yes | Admin or Provider |

Manually trigger job scraping. Runs in the background.

**Query Parameters:**
- `scraper_name` (optional): `deloitte`, `pwc`, `kpmg`, `ey`, or omit for all

**Response (202):**
```json
{
  "message": "Ingestion triggered for ALL scrapers",
  "status": "processing_in_background"
}
```

---

### 7.3 Trigger Ingestion (All Sources)

| Method | Path | Auth | Role |
|--------|------|------|------|
| `POST` | `/admin/ingest/all` | Yes | Admin |

Trigger ingestion for all configured scraper sources.

**Response (200):**
```json
{
  "message": "Global ingestion triggered in background"
}
```

---

### 7.4 Trigger Ingestion (Specific Source)

| Method | Path | Auth | Role |
|--------|------|------|------|
| `POST` | `/admin/ingest/{source_name}` | Yes | Admin |

Trigger ingestion for a specific scraper source.

**Path Parameters:**
- `source_name`: `deloitte`, `pwc`, `kpmg`, or `ey`

**Response (200):**
```json
{
  "source": "deloitte",
  "result": {
    "fetched": 25,
    "new": 10,
    "skipped": 15,
    "errors": 0,
    "dedup_hits": 2
  }
}
```

**Errors:**
| Code | Reason |
|------|--------|
| 403 | Not an admin |
| 404 | Unknown source name |

---

### 7.5 Re-Enrich Jobs

| Method | Path | Auth | Role |
|--------|------|------|------|
| `POST` | `/admin/reenrich` | No | Dev only |

Re-run AI enrichment for all jobs missing prep guides, resume guides, or embeddings. Processes in batches of 3 with 3-second pauses between batches.

**Response (202):**
```json
{
  "message": "Re-enrichment started in background. Check server logs for progress."
}
```

---

## 8. Error Response Format

All error responses follow a consistent format:

```json
{
  "detail": "Human-readable error message"
}
```

### Common HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | Success | Standard successful response |
| 201 | Created | Resource created (rarely used — most use 200) |
| 202 | Accepted | Request accepted, processing in background |
| 400 | Bad Request | Invalid input (wrong file type, etc.) |
| 403 | Forbidden | Insufficient role permissions |
| 404 | Not Found | Resource does not exist |
| 422 | Unprocessable Entity | Validation error (missing required fields, etc.) |
| 500 | Internal Server Error | Unexpected server failure |
| 503 | Service Unavailable | Server overloaded (frontend auto-retries) |
