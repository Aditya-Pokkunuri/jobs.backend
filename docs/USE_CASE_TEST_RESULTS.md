# Ottobon Use Cases — Detailed Test Results & Walkthrough

> **Date**: February 13, 2026  
> **Test Runner**: `test_use_cases.py`  
> **Result**: **30/30 passed** ✅

---

## Table of Contents

1. [UC1: The "Bridge the Gap" Candidate](#uc1-the-bridge-the-gap-candidate)
2. [UC2: The Career Pivoter (Resume Reframing)](#uc2-the-career-pivoter-resume-reframing)
3. [UC3: The "Niche Skill" Workshop Conversion](#uc3-the-niche-skill-workshop-conversion)
4. [UC4: The "Nervous Expert" (Interview Prep)](#uc4-the-nervous-expert-interview-prep)
5. [UC5: The "Passive Browser" Engagement](#uc5-the-passive-browser-engagement)

---

## UC1: The "Bridge the Gap" Candidate

**Scenario**: A Junior Developer wants to apply for a Full Stack Engineer role. They're strong in React but weak in Node.js.

### Step 1 — Resume Upload

**API**: `POST /users/resume`

The user uploads their PDF resume. The system processes it through the full pipeline:

```
Upload → Storage → Text Extraction → Embedding → DB Persist
```

**Simulated Resume Text**:
```
Experienced React developer with 3 years of frontend work.
Built SPAs with React, Redux, TypeScript. Limited backend exposure.
```

**Generated Embedding**: `[0.8, 0.9, 0.2, 0.1]`  
→ High values for frontend dimensions (0.8, 0.9), low values for backend (0.2, 0.1).

**What was verified**:
| Check | Result |
|---|---|
| Text extracted from PDF | ✅ 119 characters |
| Embedding generated | ✅ Called `EmbeddingPort.encode()` |
| User record updated in DB | ✅ `upsert_user()` called with resume_text, resume_embedding, resume_file_url |

---

### Step 2 — Matching Against Full Stack Job

**API**: `POST /jobs/{job_id}/match`

The system computes cosine similarity between the user's resume embedding and the job's embedding.

**Job**: Full Stack Engineer  
**Required Skills**: React, Node.js, Express, PostgreSQL  
**Job Embedding**: `[0.5, 0.5, 0.8, 0.8]` — balanced frontend + backend

**Match Calculation**:
```
User Vector:  [0.8, 0.9, 0.2, 0.1]   ← Strong frontend, weak backend
Job Vector:   [0.5, 0.5, 0.8, 0.8]   ← Needs both frontend + backend

Cosine Similarity = dot(u, j) / (||u|| × ||j||)
dot product    = (0.8×0.5) + (0.9×0.5) + (0.2×0.8) + (0.1×0.8) = 0.4 + 0.45 + 0.16 + 0.08 = 1.09
||user||       = √(0.64 + 0.81 + 0.04 + 0.01) = √1.50 = 1.2247
||job||        = √(0.25 + 0.25 + 0.64 + 0.64) = √1.78 = 1.3342

Score = 1.09 / (1.2247 × 1.3342) = 0.6672 (66.7%)
```

**Gap Detection**: Score `0.6672` < threshold `0.7` → **Gap Detected** ✅

**What was verified**:
| Check | Result |
|---|---|
| Similarity score in [0, 1] range | ✅ 0.6672 |
| Gap detected (frontend vs full-stack) | ✅ `gap_detected = True` |

---

### Step 3 — AI Chat Initiates Skill Gap Conversation

**API**: `WebSocket /ws/chat/{session_id}`

The user opens the Control Tower chat. The AI sees their resume context and the job they're viewing.

**User Message**:
```
I want to apply for this Full Stack role but I only know React
```

**AI Reply**:
```
I see you're great with React, but this role requires Node.js.
Would you like a quick roadmap? The Prep tab has a middleware guide.
```

**What happens behind the scenes**:
1. User message appended to `conversation_log` JSONB column
2. AI response generated via `AIPort.chat(history)`
3. AI reply appended to `conversation_log`
4. Full log persisted to DB via `update_chat_session()`

**What was verified**:
| Check | Result |
|---|---|
| AI generates a reply | ✅ Non-null response |
| Reply mentions the skill gap (Node.js) | ✅ Contains "Node.js" |

---

### Step 4 — Admin Takeover (Human Expert)

**API**: `POST /admin/takeover`

The AI is good, but the user asks a nuanced question. A background expert takes over the chat.

**Conversation Flow**:
```
┌─────────┐        ┌──────────────────┐       ┌─────────────┐
│  User   │───→    │  AI (active_ai)  │───→   │ Admin takes  │
│  asks   │        │  gives roadmap   │       │ over session │
└─────────┘        └──────────────────┘       └─────────────┘
                                                     │
                   Session status changes:           │
                   active_ai → active_human  ←───────┘
```

**What was verified**:
| Check | Result |
|---|---|
| Admin takeover executed | ✅ `update_chat_session()` called |
| Session switched to `active_human` | ✅ Status = "active_human" |

---

## UC2: The Career Pivoter (Resume Reframing)

**Scenario**: A Customer Support Agent wants to move into a Client Success Manager role. Their resume is full of support keywords that don't match.

### Step 1 — AI Enrichment Generates Career Pivot Guides

**API**: `POST /jobs` → Background Task: `EnrichmentService.enrich_job()`

When the Client Success Manager job is posted, the AI generates tailored resume and prep guides.

**Job Description**:
```
We are looking for a Client Success Manager to build relationships
with enterprise clients, drive retention, and identify upsell opportunities.
```

**AI-Generated Resume Guide (5 actionable tips)**:
```
1. "Replace 'Resolved Tickets' with 'Managed Client Relationships'"
2. "Reframe 'Bug Reports' as 'Identified Client Pain Points'"
3. "Highlight customer retention metrics you've influenced"
4. "Add examples of cross-functional collaboration"
5. "Include any client-facing communication achievements"
```

↑ This is the **reframing** advice the use case describes — translating support terminology into client success language.

**AI-Generated Prep Questions (5 interview questions)**:
```
1. "How would you handle a client threatening to churn?"
2. "Describe a time you turned a dissatisfied customer into an advocate"
3. "What metrics would you track for client success?"
4. "How do you prioritize between multiple enterprise accounts?"
5. "What's your approach to identifying upsell opportunities?"
```

**Embedding**: Generated using `EmbeddingPort.encode()` for future matching.

**What was verified**:
| Check | Result |
|---|---|
| AI enrichment called | ✅ `generate_enrichment()` invoked |
| Job record updated with guides | ✅ `update_job()` called |
| Resume guide has 5 tips | ✅ Length = 5 |
| Prep guide has 5 questions | ✅ Length = 5 |
| Resume guide includes reframing advice | ✅ Contains "Replace" and "Reframe" |
| Embedding generated | ✅ Non-null vector stored |

---

## UC3: The "Niche Skill" Workshop Conversion

**Scenario**: A company posts a job requiring Rust Programming. 95% of developers only know C++ or Python and are about to leave the page.

### Step 1 — User Expresses Hesitation in Chat

**API**: `WebSocket /ws/chat/{session_id}`

The user opens the Control Tower while viewing the Rust role.

**User Message**:
```
I'm looking at this Rust developer role but I only know C++
```

**AI Reply**:
```
Hey, noticed you're looking at the Rust role. It's tough to find
resources for this. We have a 2-day workshop starting Saturday
that covers exactly what this company asks for. Interested?
```

**What happens behind the scenes**:
1. Message appended to `conversation_log`
2. AI generates a proactive engagement response
3. Response references a learning opportunity (workshop)
4. Full conversation persisted to DB

**The Control Tower strategy**: Instead of letting the user bounce, the AI:
- Acknowledges the skill gap
- Offers a concrete solution (workshop)
- Keeps the user engaged and monetizes via upskilling

**What was verified**:
| Check | Result |
|---|---|
| AI responds about the niche skill | ✅ Non-null reply |
| Reply mentions workshop/learning opportunity | ✅ Contains "workshop" |
| Conversation persisted to log | ✅ `update_chat_session()` called |

---

## UC4: The "Nervous Expert" (Interview Prep)

**Scenario**: A Senior Architect applies for a VP-level role. They haven't interviewed in 10 years and lack confidence.

### Step 1 — Viewing the Prep Pillar

**API**: `GET /jobs/{job_id}/details`

The user opens the VP of Engineering job and sees the 4-Pillar view.

**Job**: VP of Engineering  
**Required Skills**: Architecture, Leadership, Strategy

**Resume Guide (Pillar 3)**:
```
1. "Lead with strategic impact, not technical depth"
2. "Quantify team growth and retention metrics"
3. "Show P&L or budget management experience"
4. "Include cross-org collaboration examples"
5. "Highlight culture-building initiatives"
```

**Prep Guide (Pillar 4)**:
```
1. "How would you restructure an underperforming engineering org?"
2. "Describe your approach to technical debt at scale"
3. "What's your philosophy on build vs buy decisions?"
4. "How do you handle conflicts between PMs and engineers?"
5. "Tell us about a time you influenced C-level strategy"
```

**What was verified**:
| Check | Result |
|---|---|
| Job details fetched | ✅ Non-null response |
| Prep guide has 5 questions | ✅ Length = 5 |
| Resume guide has 5 tips | ✅ Length = 5 |

---

### Step 2 — User Asks for Help in Control Tower

**User Message**:
```
I'm really nervous about the culture fit round
```

**AI Reply**:
```
For a VP role, focus on Strategic Decision Making over technical depth.
Try our Mock Interview module in the Prep tab.
```

**What was verified**:
| Check | Result |
|---|---|
| AI provides interview coaching | ✅ Non-null reply |
| Reply mentions strategy/prep | ✅ Contains "strategic" and "prep" |

---

### Step 3 — Admin Provides Expert Coaching

**API**: `POST /admin/chat/reply`

The AI response is good, but the admin (a background career expert) adds nuanced advice:

**Admin Reply**:
```
For a VP role, focus on Strategic Decision Making over technical depth.
```

**Session Flow**:
```
User → AI (active_ai) → Admin takeover (active_human) → Admin reply
```

**What was verified**:
| Check | Result |
|---|---|
| Admin reply persisted to conversation log | ✅ `update_chat_session()` called |

---

## UC5: The "Passive Browser" Engagement

**Scenario**: A user logs in casually with no intention of applying. They're just browsing Data Science jobs.

### Step 1 — Matching Shows Partial Fit

**API**: `POST /jobs/{job_id}/match`

**User Profile**: Knows Python and Statistics, but NOT SQL  
**User Embedding**: `[0.7, 0.8, 0.6, 0.3, 0.1]`

**Job**: Data Scientist  
**Required Skills**: Python, SQL, Statistics, Machine Learning  
**Job Embedding**: `[0.7, 0.7, 0.7, 0.7, 0.7]`

**Match Calculation**:
```
User Vector:  [0.7, 0.8, 0.6, 0.3, 0.1]   ← Strong Python/Stats, weak SQL/ML
Job Vector:   [0.7, 0.7, 0.7, 0.7, 0.7]   ← Needs all skills equally

Cosine Similarity = 88.7%
```

→ The user already has ~60% of the skills (Python, Stats), just needs SQL and ML.

**What was verified**:
| Check | Result |
|---|---|
| Match score computed | ✅ 88.7% similarity |

---

### Step 2 — AI Nudge to Convert Passive User

**API**: `WebSocket /ws/chat/{session_id}`

**User Message** (casual/hesitant):
```
I'm just browsing Data Science jobs, not sure if I'm qualified
```

**AI Reply** (encouraging nudge):
```
Curious about Data Science? You already have 60% of the skills needed.
You just need SQL. Check the Prep section for a guide.
```

**The Engagement Strategy**:
```
Passive Browse → Match Score (visual graph) → AI Nudge → Prep Section → Active Learner
```

**What was verified**:
| Check | Result |
|---|---|
| AI provides encouraging nudge | ✅ Non-null reply |
| Reply mentions skills percentage | ✅ Contains "60%" |
| Reply directs to Prep section | ✅ Contains "Prep" and "guide" |

---

### Step 3 — User Returns Later (WebSocket Recovery)

The passive user comes back the next day. Thanks to the **WebSocket persistence** feature (Constraint 3 from Production Hardening), their previous conversation is replayed on reconnect.

**API**: `WebSocket /ws/chat/{session_id}` → `history_replay`

**Stored Conversation Log**:
```json
[
  {"role": "user", "content": "I'm just browsing...", "timestamp": "2026-02-13T10:00:00Z"},
  {"role": "assistant", "content": "Curious about Data Science?...", "timestamp": "2026-02-13T10:00:01Z"}
]
```

**On Reconnect, Client Receives**:
```json
{
  "type": "history_replay",
  "messages": [
    {"role": "user", "content": "I'm just browsing..."},
    {"role": "assistant", "content": "Curious about Data Science?..."}
  ],
  "session_status": "active_ai"
}
```

The user sees their previous conversation — no blank chat. They pick up where they left off.

**What was verified**:
| Check | Result |
|---|---|
| History replayed on reconnect | ✅ 2 messages returned |
| Session still active | ✅ Status = "active_ai" |

---

## Summary — API Coverage per Use Case

| Use Case | APIs Exercised | Tests |
|---|---|---|
| UC1: Bridge the Gap | `POST /users/resume` → `POST /jobs/{id}/match` → `WS /ws/chat` → `POST /admin/takeover` | **9/9** ✅ |
| UC2: Career Pivoter | `POST /jobs` → `EnrichmentService.enrich_job()` | **6/6** ✅ |
| UC3: Niche Skill | `WS /ws/chat` (proactive AI engagement) | **3/3** ✅ |
| UC4: Nervous Expert | `GET /jobs/{id}/details` → `WS /ws/chat` → `POST /admin/takeover` → `admin_reply()` | **6/6** ✅ |
| UC5: Passive Browser | `POST /jobs/{id}/match` → `WS /ws/chat` → Reconnect `history_replay` | **6/6** ✅ |
| **TOTAL** | | **30/30** ✅ |
