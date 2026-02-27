# Ottobon Use Cases — Manual Test Results

**Date**: 13 Feb 2026 | **Tester**: Dave | **Server**: `uvicorn main:app --reload` on `localhost:8000`

---

## Summary

All **5 use cases** were tested manually via localhost API calls and WebSocket connections. Every use case passed successfully with personalized AI responses.

| UC | Name | Status | Key Verification |
|---|---|---|---|
| 1 | Bridge the Gap | ✅ Passed | AI referenced Dave's React/Node skills from resume |
| 2 | Career Pivoter | ✅ Passed | 5 resume tips + 5 interview questions generated |
| 3 | Niche Skill Workshop | ✅ Passed | Personalized C++ → Rust transition advice |
| 4 | Nervous Expert | ✅ Passed | Strategic VP coaching, not coding questions |
| 5 | Passive Browser | ✅ Passed | 10 messages recovered on WebSocket reconnect |

---

## Bug Fix During Testing

**Issue**: UC1's initial AI response was generic (no personalization).

**Root Cause**: `OpenAIAdapter.chat()` used a static system prompt with no user context. `ChatService.handle_message()` never fetched the user's profile.

**Fix Applied** (3 files):
- `app/ports/ai_port.py` — Added `user_context` parameter to `chat()` method
- `app/adapters/openai_adapter.py` — System prompt upgraded to include resume text
- `app/services/chat_service.py` — New `_build_user_context()` fetches user profile from DB and builds a rich context string (resume text, name, skills)

After the fix, all AI responses referenced the user's actual skills and experience.

---

## UC1: Bridge the Gap Candidate

**Steps executed**:
1. `POST /users/resume` — Uploaded `AdityaResume (3).pdf` → extracted text successfully
2. `GET /jobs/feed` — Retrieved active jobs
3. `POST /jobs/{id}/match` — Got similarity score + `gap_detected` flag
4. `POST /chat/sessions` — Created session with `status: active_ai`
5. `ws://127.0.0.1:8000/ws/chat/{session_id}` — Sent: *"I want to apply for this Full Stack role but I only know React."*

**AI Response** (excerpt):
> "Dave, it's great to hear that you're considering applying for a Full Stack role! You already have a solid foundation with your skills in **React.js** and your experience as an AI Engineering Team Lead at **Ottobon**... Practice with **Node.js**... Build projects using **FastAPI**..."

✅ AI referenced Dave's **actual resume**: React.js, Ottobon, Node.js, FastAPI, PostgreSQL, Docker.

---

## UC2: Career Pivoter

**Steps executed**:
1. `POST /jobs` — Created "Client Success Manager" job with skills: Client Management, Relationship Building, SaaS, Retention Strategy
2. Waited 15 seconds for background AI enrichment
3. `GET /jobs/{id}/details` — Retrieved enrichment data

**Result**:
- `resume_guide_generated`: 5 bullet points tailored to pivoting into Client Success
- `prep_guide_generated`: 5 interview questions specific to the role

✅ Both guides were role-specific, not generic.

---

## UC3: Niche Skill Workshop Conversion

**Steps executed**:
1. `POST /jobs` — Created "Rust Systems Developer" with skills: Rust, Systems Programming, Concurrency, Memory Safety
2. `POST /chat/sessions` → WebSocket chat
3. Sent: *"I'm looking at this Rust Systems Developer role but I only know C++ and Python. Is it even worth applying?"*

**AI Response**: Acknowledged the C++ → Rust gap, highlighted transferable knowledge (memory management, concurrency), suggested Rust-specific learning resources.

✅ Personalized transition advice referencing Dave's actual C++/Python background.

---

## UC4: Nervous Expert

**Steps executed**:
1. `POST /jobs` — Created "VP of Engineering" with skills: Engineering Leadership, Technical Strategy, PnL Management, Executive Communication, Organizational Design
2. Checked enrichment → `prep_guide_generated` had strategic/behavioral questions (not coding)
3. `POST /chat/sessions` → WebSocket chat
4. Sent: *"I'm really nervous about the VP of Engineering interview. I haven't interviewed in 10 years."*

**AI Response**: Coaching focused on executive-level preparation, culture fit strategies, and leadership storytelling — not technical coding.

✅ Strategic leadership coaching, appropriate for VP-level role.

---

## UC5: Passive Browser Engagement

**Steps executed**:
1. `POST /jobs` — Created "Junior Data Scientist" with skills: Python, SQL, Statistics, Machine Learning, pandas
2. `POST /jobs/{id}/match` — Got similarity score showing partial skill fit
3. `POST /chat/sessions` → WebSocket chat
4. Sent: *"I'm just browsing Data Science jobs. Not sure if I'm qualified. I know Python but not SQL."*

**AI Response** (excerpt):
> "Hi Dave! ...Your background displays strong qualifications, especially with your skills in **Python**, **AI frameworks**, and your experience as an **AI Engineering Team Lead**... **SQL Knowledge**: this is a skill you can quickly acquire... **Statistics and Data Analysis**: worth studying..."

5. **Disconnected** WebSocket connection
6. **Reconnected** to same session → `HISTORY REPLAY: 10 messages recovered!`

✅ Personalized AI nudge + full state recovery on reconnect.

---

## APIs Tested

| Endpoint | Method | UC | Result |
|---|---|---|---|
| `/users/resume` | POST | 1 | ✅ Resume uploaded and parsed |
| `/jobs/feed` | GET | 1 | ✅ Active jobs listed |
| `/jobs` | POST | 2,3,4,5 | ✅ Jobs created with enrichment |
| `/jobs/{id}/details` | GET | 2,4 | ✅ 4-pillar enrichment returned |
| `/jobs/{id}/match` | POST | 1,5 | ✅ Similarity score + gap detection |
| `/chat/sessions` | POST | 1,3,4,5 | ✅ Sessions created |
| `/ws/chat/{id}` | WS | 1,3,4,5 | ✅ Real-time chat + history replay |

---

## Production Hardening Features Verified

| Feature | How Tested | Status |
|---|---|---|
| Personalized AI Context | Resume text injected into system prompt | ✅ Verified |
| AI Enrichment (4 Pillars) | Created jobs and checked `resume_guide_generated` + `prep_guide_generated` | ✅ Verified |
| WebSocket History Replay | Disconnected and reconnected — 10 messages recovered | ✅ Verified |
| Session Status Management | Created sessions with `active_ai` status | ✅ Verified |
