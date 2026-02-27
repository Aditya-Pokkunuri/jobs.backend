# Ottobon Use Cases — Manual Testing Guide

> **Pre-requisites**:
> - Server running: `uvicorn main:app --reload` from `backend/`
> - Supabase SQL migration `002_scraping_logs.sql` executed
> - A user account in Supabase Auth

---

## Step 0 — Get Your Auth Token

Run this in PowerShell (replace email/password with your credentials):

```powershell
$body = '{"email":"dave@ottobon.cloud","password":"TestPass123!"}'
$response = Invoke-RestMethod -Uri "https://angkznyumeoahjnxgxyb.supabase.co/auth/v1/token?grant_type=password" -Method POST -Headers @{ "apikey" = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFuZ2t6bnl1bWVvYWhqbnhneHliIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzA4NzQzMDUsImV4cCI6MjA4NjQ1MDMwNX0.M6QrvhJPIIf90aCnpoBm1cE1juDEQeDdGRswIF0M92s"; "Content-Type" = "application/json" } -Body $body
$TOKEN = $response.access_token
Write-Host "Got token:" $TOKEN.Substring(0,20) "..."
```

**Save the token** — you'll use `$TOKEN` in every command below. If you get `401` errors later, re-run this to get a fresh token.

---

## UC1: The "Bridge the Gap" Candidate

> **Story**: Junior Developer (strong React, weak Node.js) wants to apply for a Full Stack Engineer role.

### Step 1 — Upload Your Resume

Prepare a PDF or DOCX resume file, then:

```powershell
$resumePath = "C:\path\to\your\resume.pdf"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/users/resume" -Method POST -Headers @{"Authorization" = "Bearer $TOKEN"} -Form @{ file = Get-Item $resumePath }
```

**Expected output**:
```json
{"message": "Resume processed successfully", "characters_extracted": 1234}
```

✅ **What to verify**: `characters_extracted` > 0 means your resume was parsed.

---

### Step 2 — Browse the Job Feed

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/jobs/feed?limit=5" -Method GET | ConvertTo-Json -Depth 5
```

**Expected output**: A list of active jobs. Pick a `job_id` from the results for the next step.

---

### Step 3 — Match Yourself Against a Job

Replace `JOB_ID_HERE` with an actual job UUID from the feed:

```powershell
$JOB_ID = "JOB_ID_HERE"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/jobs/$JOB_ID/match" -Method POST -Headers @{"Authorization" = "Bearer $TOKEN"} | ConvertTo-Json
```

**Expected output**:
```json
{
  "job_id": "...",
  "similarity_score": 0.67,
  "gap_detected": true
}
```

✅ **What to verify**:
- `similarity_score` is between 0 and 1
- If `gap_detected` is `true`, it means your resume doesn't fully align with the job (score < 0.7)
- This is the "Bridge the Gap" flag from the use case

---

### Step 4 — Open a Chat Session (Control Tower)

```powershell
$session = Invoke-RestMethod -Uri "http://127.0.0.1:8000/chat/sessions" -Method POST -Headers @{"Authorization" = "Bearer $TOKEN"} -ContentType "application/json"
$SESSION_ID = $session.id
Write-Host "Session ID:" $SESSION_ID
```

**Expected output**:
```json
{"id": "...", "user_id": "...", "status": "active_ai"}
```

---

### Step 5 — Chat via WebSocket (AI Mode)

Open a **second PowerShell window** and run this WebSocket client:

```powershell
# Simple WebSocket test using Python (run from backend/ with venv activated)
python -c "
import asyncio, websockets, json

async def chat():
    uri = 'ws://127.0.0.1:8000/ws/chat/SESSION_ID_HERE'
    async with websockets.connect(uri) as ws:
        # 1. Receive history replay
        history = await ws.recv()
        print('HISTORY REPLAY:', history)
        print()

        # 2. Send a message
        await ws.send('I want to apply for this Full Stack role but I only know React. What should I do?')
        reply = await ws.recv()
        print('AI REPLY:', reply)
        print()

        # 3. Send follow-up
        await ws.send('How deep does my Node.js knowledge need to be?')
        reply2 = await ws.recv()
        print('AI REPLY 2:', reply2)

asyncio.run(chat())
"
```

> **Replace** `SESSION_ID_HERE` with the actual session ID from Step 4.

**Expected output**:
```
HISTORY REPLAY: {"type": "history_replay", "messages": [], "session_status": "active_ai"}

AI REPLY: {"type": "ai_reply", "content": "I see you're great with React..."}

AI REPLY 2: {"type": "ai_reply", "content": "For most full-stack roles..."}
```

✅ **What to verify**:
- First message is `history_replay` with empty messages (new session)
- AI replies are relevant to the skill gap
- Messages are JSON with `type` field

---

### Step 6 — (Optional) Admin Takeover

If your user has `role: "admin"`:

```powershell
$body = '{"session_id": "SESSION_ID_HERE"}'
Invoke-RestMethod -Uri "http://127.0.0.1:8000/admin/chat/takeover" -Method POST -Headers @{"Authorization" = "Bearer $TOKEN"; "Content-Type" = "application/json"} -Body $body
```

After takeover, the session status changes to `active_human`. User messages will no longer get AI replies.

---

## UC2: The Career Pivoter (Resume Reframing)

> **Story**: The system generates a resume guide that helps a support agent reframe their experience for a Client Success role.

### Step 1 — Create a Job with a Description

```powershell
$jobBody = @{
    title = "Client Success Manager"
    description_raw = "We are looking for a Client Success Manager to build relationships with enterprise clients, drive retention, and identify upsell opportunities. The ideal candidate has experience in customer-facing roles and can translate technical concepts into business value."
    skills_required = @("Client Management", "Relationship Building", "SaaS", "Retention Strategy")
} | ConvertTo-Json

$job = Invoke-RestMethod -Uri "http://127.0.0.1:8000/jobs" -Method POST -Headers @{"Authorization" = "Bearer $TOKEN"; "Content-Type" = "application/json"} -Body $jobBody
$NEW_JOB_ID = $job.id
Write-Host "Created job:" $NEW_JOB_ID
```

**Expected output**:
```json
{"id": "...", "message": "Job created. AI enrichment is processing in the background."}
```

---

### Step 2 — Wait 10-15 Seconds, Then Check the 4 Pillars

```powershell
Start-Sleep -Seconds 15
Invoke-RestMethod -Uri "http://127.0.0.1:8000/jobs/$NEW_JOB_ID/details" -Method GET | ConvertTo-Json -Depth 5
```

**Expected output**:
```json
{
  "id": "...",
  "title": "Client Success Manager",
  "resume_guide_generated": [
    "Replace support terminology with client success language",
    "Highlight retention metrics you've influenced",
    ...
  ],
  "prep_guide_generated": [
    "How would you handle a client threatening to churn?",
    "Describe your approach to identifying upsell opportunities",
    ...
  ]
}
```

✅ **What to verify**:
- `resume_guide_generated` has 5 actionable bullet points
- `prep_guide_generated` has 5 interview questions
- The guides are **specific** to the Client Success role, not generic

---

## UC3: The "Niche Skill" Workshop Conversion

> **Story**: User views a Rust developer role and the AI proactively engages them about learning resources.

### Step 1 — Create a Niche Skill Job

```powershell
$rustJob = @{
    title = "Rust Systems Developer"
    description_raw = "We need a systems developer proficient in Rust to build high-performance backend services. Experience with memory safety, concurrency patterns, and systems programming required. You will work on performance-critical infrastructure serving millions of requests."
    skills_required = @("Rust", "Systems Programming", "Concurrency", "Memory Safety")
} | ConvertTo-Json

$rjob = Invoke-RestMethod -Uri "http://127.0.0.1:8000/jobs" -Method POST -Headers @{"Authorization" = "Bearer $TOKEN"; "Content-Type" = "application/json"} -Body $rustJob
Write-Host "Rust job created:" $rjob.id
```

---

### Step 2 — Open Chat and Ask About the Niche Skill

Create a new session and connect via WebSocket (same Python script as UC1 Step 5), but send:

```
I'm looking at this Rust developer role but I only know C++. Is it worth applying?
```

✅ **What to verify**:
- AI acknowledges the C++ → Rust gap
- AI might suggest learning resources or a transition path
- The conversation is encouraging, not dismissive

---

## UC4: The "Nervous Expert" (Interview Prep)

> **Story**: Senior Architect applies for VP role, hasn't interviewed in 10 years.

### Step 1 — Create a VP-Level Job

```powershell
$vpJob = @{
    title = "VP of Engineering"
    description_raw = "We are seeking a VP of Engineering to lead our 200-person engineering organization. Responsibilities include setting technical strategy, managing P&L, driving hiring and retention, and representing engineering at the executive level. The ideal candidate has 15+ years of experience and has led organizations through hyper-growth."
    skills_required = @("Engineering Leadership", "Technical Strategy", "P&L Management", "Executive Communication", "Organizational Design")
} | ConvertTo-Json

$vjob = Invoke-RestMethod -Uri "http://127.0.0.1:8000/jobs" -Method POST -Headers @{"Authorization" = "Bearer $TOKEN"; "Content-Type" = "application/json"} -Body $vpJob
Write-Host "VP job created:" $vjob.id
```

---

### Step 2 — Check the Prep Pillar

```powershell
Start-Sleep -Seconds 15
$VP_JOB_ID = $vjob.id
Invoke-RestMethod -Uri "http://127.0.0.1:8000/jobs/$VP_JOB_ID/details" -Method GET | ConvertTo-Json -Depth 5
```

✅ **What to verify**:
- `prep_guide_generated` has behavioral/strategic questions (not coding questions)
- `resume_guide_generated` focuses on leadership impact, not technical skills

---

### Step 3 — Chat About Interview Nerves

Open a new chat session and send:

```
I'm really nervous about the culture fit round. I haven't interviewed in 10 years.
```

✅ **What to verify**:
- AI provides coaching focused on strategic leadership, not technical depth
- AI might reference the Prep tab/pillar

---

## UC5: The "Passive Browser" Engagement

> **Story**: Casual user browses Data Science jobs, gets nudged by AI showing they already have 60% of needed skills.

### Step 1 — Create a Data Science Job

```powershell
$dsJob = @{
    title = "Junior Data Scientist"
    description_raw = "Join our analytics team as a Junior Data Scientist. You will analyze large datasets, build predictive models, and create data visualizations. Required skills include Python, SQL, Statistics, and basic Machine Learning. Experience with pandas, scikit-learn, and Jupyter preferred."
    skills_required = @("Python", "SQL", "Statistics", "Machine Learning", "pandas")
} | ConvertTo-Json

$dsjob = Invoke-RestMethod -Uri "http://127.0.0.1:8000/jobs" -Method POST -Headers @{"Authorization" = "Bearer $TOKEN"; "Content-Type" = "application/json"} -Body $dsJob
Write-Host "DS job created:" $dsjob.id
```

---

### Step 2 — Match (See Your Skill Percentage)

```powershell
Start-Sleep -Seconds 15
$DS_JOB_ID = $dsjob.id
Invoke-RestMethod -Uri "http://127.0.0.1:8000/jobs/$DS_JOB_ID/match" -Method POST -Headers @{"Authorization" = "Bearer $TOKEN"} | ConvertTo-Json
```

✅ **What to verify**:
- `similarity_score` gives you a sense of fit (e.g., 0.6 = 60% match)
- `gap_detected` tells you if you need to upskill

---

### Step 3 — Chat as a Passive Browser

Open a new chat session and send:

```
I'm just browsing Data Science jobs. Not sure if I'm qualified. I know Python but not SQL.
```

✅ **What to verify**:
- AI is encouraging, not dismissive
- AI mentions which skills you already have
- AI directs you to learning resources or the Prep section

---

### Step 4 — Disconnect and Reconnect (State Recovery)

1. Close the WebSocket connection (Ctrl+C on the Python script)
2. Re-run the same Python script with the **same session ID**
3. The first message you receive should be `history_replay` with your previous messages

✅ **What to verify**:
- `history_replay` contains all messages from the previous session
- You don't see a blank chat

---

## Quick Reference — All API Endpoints

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/users/resume` | POST | ✅ | Upload resume (PDF/DOCX) |
| `/users/me` | GET | ✅ | Get your profile |
| `/users/me/resume` | GET | ✅ | Get signed download URL (15-min TTL) |
| `/jobs/feed` | GET | ❌ | Browse active jobs |
| `/jobs` | POST | ✅ | Create a job posting |
| `/jobs/{id}/details` | GET | ❌ | Get 4-pillar job details |
| `/jobs/{id}/match` | POST | ✅ | Match your resume against a job |
| `/chat/sessions` | POST | ✅ | Create a new chat session |
| `/ws/chat/{session_id}` | WS | ❌ | WebSocket chat connection |
| `/admin/ingest/all` | POST | ✅ Admin | Trigger scraping pipeline |
| `/admin/chat/takeover` | POST | ✅ Admin | Switch chat to human mode |

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `401 Unauthorized` | Token expired. Re-run Step 0 to get a fresh token. |
| `422 Unprocessable Entity` on match | Your resume has no embedding. Upload a resume first (UC1 Step 1). |
| `404` on job details | Job ID doesn't exist. Check `/jobs/feed` for valid IDs. |
| AI enrichment fields are `null` | Enrichment runs in background. Wait 15 seconds and retry. |
| WebSocket closes immediately | Check the session ID is valid. `4003` = session is closed, `4004` = session not found. |
| `websockets` not installed | Run `pip install websockets` in your venv. |
