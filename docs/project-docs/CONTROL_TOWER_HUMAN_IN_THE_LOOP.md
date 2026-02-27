# Control Tower — Human-in-the-Loop

> **Ottobon Jobs Network**
> Functional Specification • v2.0 • February 2026

---

## 1. Executive Summary

The **Control Tower** is Ottobon's real-time career coaching and supervision system. It implements a **layered Human-in-the-Loop (HITL)** architecture where artificial intelligence handles seeker interactions at scale, while human experts can **silently observe and take over any conversation at any time** — without the seeker needing to request it.

Think of it like a call center where every customer is initially talking to an intelligent bot, but a human supervisor is always watching the dashboard and can jump into any conversation the moment they feel it's necessary — correcting the AI, adding nuance, or handling an edge case the AI isn't equipped for.

---

## 2. Design Philosophy

| Principle | Description |
|---|---|
| **AI First, Human Anytime** | Every conversation starts with AI. Human experts can take over silently at any point — no button, no permission needed. |
| **Zero Wait for Seekers** | Seekers never wait for a human. AI provides instant responses. If a human takes over, the transition is seamless. |
| **Invisible Handoff** | The seeker doesn't know (or need to know) whether they're talking to AI or a human. The experience feels like one continuous conversation. |
| **Full Conversation Memory** | Every message — whether from AI or a human expert — is persisted in the same conversation log. Nothing is lost, even across disconnections. |
| **Admin Omniscience** | Admins have full visibility into every active session. They see which ones are AI-handled, which ones they've taken over, and can switch between them freely. |

---

## 3. System Actors

### 3.1 Seeker (End User)
The job seeker who uses the platform to get career coaching. They initiate chat sessions from matched job listings, ask questions, take mock interviews, and receive guidance. From their perspective, they are simply "talking to a coach." They don't know — and don't need to care — whether the coach is AI or human at any given moment.

### 3.2 AI Mentor
The default conversational partner. It's an AI model that has been given the seeker's full context: their resume, the job they're interested in, the required skills, and the complete conversation history. It responds instantly, 24/7. It handles coaching questions, mock interview evaluations, and general career advice. It stays in control of the conversation **until a human decides otherwise.**

### 3.3 Human Expert (Admin)
A platform administrator or career coach who monitors active sessions from the Control Tower dashboard. They can:

- **Watch** any conversation in real time.
- **Take over** any session at any moment — the AI steps aside and the human starts responding.
- **Hand back** the session to the AI when they're done — the AI picks up where the human left off.
- **Review mock interviews** and add expert feedback on top of AI-generated scorecards.

The human expert is not summoned by the seeker. They choose to intervene based on their own judgment.

---

## 4. Core Workflows

### 4.1 Real-Time AI Coaching

This is the default interaction loop. Every conversation starts here.

```
  Seeker opens a job they matched with
       │
       ▼
  Clicks "Talk to Coach"
       │
       ▼
  System creates (or reopens) a chat session
  for that specific job
       │
       ▼
  A WebSocket connection is established
       │
       ▼
  Server replays the last 10 messages
  (in case the seeker refreshed or reconnected)
       │
       ▼
  If it's a brand new session,
  the AI sends an opening greeting
       │
       ▼
  ┌─────────────────────────────────┐
  │       CONVERSATION LOOP         │
  │                                 │
  │  Seeker types a message         │
  │       │                         │
  │       ▼                         │
  │  Message is saved to the log    │
  │       │                         │
  │       ▼                         │
  │  AI generates a reply using:    │
  │  • Full conversation history    │
  │  • Seeker's resume & profile    │
  │  • Job description & skills     │
  │       │                         │
  │       ▼                         │
  │  Reply is pushed to the seeker  │
  │  instantly via WebSocket        │
  │       │                         │
  │       ▼                         │
  │  (repeat)                       │
  └─────────────────────────────────┘
```

**Key mechanics:**

- **Session Deduplication**: One seeker, one job = one session. Opening the coach for the same job always returns the same conversation. No duplication.
- **Job Context Injection**: The job description and required skills are invisibly injected into the AI's context when the session is created. The seeker doesn't see this, but the AI uses it to give job-specific advice.
- **Heartbeat**: A ping is sent every 30 seconds to keep the connection alive and prevent timeouts.
- **Auto-Reconnect**: If the connection drops (network issue, page refresh), the frontend automatically reconnects and replays the conversation history. The seeker picks up exactly where they left off.

---

### 4.2 Human Takeover (The HITL Moment)

This is the defining feature of the Control Tower. At any point during an AI-handled conversation, a human expert can step in.

```
  Admin opens the Control Tower dashboard
       │
       ▼
  Sees all active sessions in real time
  (auto-refreshes every 10 seconds)
       │
       ▼
  Notices a session they want to monitor
  (maybe the AI gave a weak answer,
   or the seeker seems confused,
   or it's a high-value candidate)
       │
       ▼
  Clicks "Monitor" on that session
       │
       ▼
  Reads the full conversation history
       │
       ▼
  Decides to take over
       │
       ▼
  ┌─────────────────────────────────────────────┐
  │         SESSION STATUS CHANGE                │
  │                                              │
  │  Status flips: active_ai → active_human      │
  │                                              │
  │  From this moment:                           │
  │  • AI stops generating replies               │
  │  • Seeker's messages are queued              │
  │    for the human to respond to               │
  │  • Human types replies directly              │
  │  • Seeker sees them just like AI replies     │
  │    (no visual difference)                    │
  └─────────────────────────────────────────────┘
       │
       ▼
  Human responds for as long as needed
       │
       ▼
  When done, admin hands back to AI
       │
       ▼
  Status flips: active_human → active_ai
       │
       ▼
  AI resumes responding automatically
  (with full context of what the human said)
```

**Why this matters:**

- The seeker never has to ask for help. They don't even know the switch happened.
- The human expert jumps in based on their own judgment — they might spot a situation where the AI is giving generic advice for a very specific question, or where the seeker is clearly frustrated.
- When the human hands back, the AI has the complete conversation (including the human's messages) in its context. So it doesn't lose continuity — it knows exactly what the human told the seeker and continues from there.

---

### 4.3 Mock Interview Flow

Mock interviews add another layer of HITL. Here, the AI evaluates the seeker's performance first, and the human expert adds their perspective on top.

```
  Seeker matches with a job (≥ 70% score)
       │
       ▼
  "Start Mock Interview" option appears
       │
       ▼
  System pulls 5 prep questions
  (generated during job enrichment by AI)
       │
       ▼
  Seeker answers all 5 questions
       │
       ▼
  AI evaluates the full transcript:
  ┌──────────────────────────────┐
  │  AI SCORECARD                │
  │  • Technical Accuracy: X/10  │
  │  • Clarity: X/10             │
  │  • Confidence: X/10          │
  │  • Summary Notes: "..."      │
  └──────────────────────────────┘
       │
       ▼
  Scorecard shown to seeker immediately
       │
       ▼
  ════════════════════════════════════
  Meanwhile, on the Admin side...
  ════════════════════════════════════
       │
       ▼
  Completed interviews appear in the
  admin's Review Desk automatically
       │
       ▼
  Admin opens the interview:
  • Reads the full Q&A transcript
  • Reviews the AI's scorecard
       │
       ▼
  Admin writes expert feedback:
  "Your answer on system design was
   technically correct but lacked the
   business impact framing that Big 4
   firms specifically look for..."
       │
       ▼
  Expert feedback is attached to the
  interview record
       │
       ▼
  Seeker sees both: AI scorecard
  + human expert feedback side by side
```

**The key difference from the chat takeover**: In mock interviews, the human review happens **asynchronously**. The admin reviews at their own pace. The seeker gets the AI scorecard instantly and the human feedback later — but both end up on the same scorecard view.

---

### 4.4 Admin Dashboard (Bird's-Eye View)

The Control Tower dashboard is the nerve center for all human oversight.

```
┌─────────────────────────────────────────────────────┐
│              CONTROL TOWER DASHBOARD                 │
│                                                      │
│  ┌──────────────────┐  ┌──────────────────┐         │
│  │  AI Sessions: 47  │  │ Human Active: 3  │         │
│  └──────────────────┘  └──────────────────┘         │
│                                                      │
│  Direct Intercept: [________UUID________] [GO]      │
│                                                      │
│  ─── Live Sessions ─────────────────────────────    │
│                                                      │
│  ● John Doe        session-abc123    14:02   [MON]  │
│  ○ Jane Smith      session-def456    13:58   [MON]  │
│  ● Raj Patel       session-ghi789    13:45   [MON]  │
│  ○ Maria Lopez     session-jkl012    13:30   [MON]  │
│                                                      │
│  ● = Human intervened    ○ = AI handling             │
│                                                      │
│  ─── Review Desk ───────────────────────────────    │
│                                                      │
│  Pending mock interview reviews:                     │
│  • Interview #a1b2  —  Jane Smith  —  PENDING       │
│  • Interview #c3d4  —  Raj Patel   —  PENDING       │
│                                                      │
└─────────────────────────────────────────────────────┘
```

The admin can:
- See all sessions at a glance and know which are AI-handled vs. human-intervened.
- Jump into any session by clicking "Monitor" or entering a UUID directly.
- See pending mock interview reviews and action them from the Review Desk.
- All lists auto-refresh, so the dashboard stays current without manual polling.

---

## 5. Session State Machine

Every chat session has three possible states:

```
                  ┌─────────────┐
    Session ────► │  active_ai  │ ◄─── Default state
    Created       └──────┬──────┘      AI is responding
                         │
                   Admin takes over
                         │
                         ▼
                  ┌──────────────┐
                  │ active_human │ ◄─── Human is responding
                  └──────┬───────┘      AI is paused
                         │
              ┌──────────┴──────────┐
              │                     │
        Admin hands back       Session closed
              │                     │
              ▼                     ▼
       ┌─────────────┐      ┌─────────────┐
       │  active_ai  │      │   closed    │
       └─────────────┘      └─────────────┘
                              Terminal state
```

- **`active_ai`**: The AI mentor is responding. All seeker messages are processed by AI and a reply is generated instantly. This is the default.
- **`active_human`**: A human expert has taken over. The AI stops generating replies. The seeker's messages are presented to the admin, who responds manually. The seeker sees these replies exactly the same way — no visual change.
- **`closed`**: The session is archived. No more messages can be sent. WebSocket connections are rejected.

**The key transitions:**
- `active_ai` → `active_human`: Admin clicks "Take Over" from the dashboard. Instant. Silent.
- `active_human` → `active_ai`: Admin clicks "Hand Back." AI resumes with full conversation context.
- Any state → `closed`: Admin or system closes the session.

---

## 6. Mock Interview Status Machine

```
┌───────────────┐     All answers      ┌───────────────┐
│  in_progress  │ ───────────────────► │   completed   │
│  (answering)  │     submitted        │ (AI scorecard) │
└───────────────┘     + AI evaluates   └───────┬───────┘
                                               │
                                        Appears in admin
                                        Review Desk auto-
                                        matically
                                               │
                                               ▼
                                       ┌───────────────┐
                                       │pending_review  │
                                       │ (in admin queue)│
                                       └───────┬───────┘
                                               │
                                         Admin writes
                                        expert feedback
                                               │
                                               ▼
                                       ┌───────────────┐
                                       │   reviewed    │
                                       │(AI + human fb) │
                                       └───────────────┘
```

| State | Who acts | What happens |
|---|---|---|
| `in_progress` | Seeker | Answering 5 interview questions |
| `completed` | AI | AI generates a structured scorecard |
| `pending_review` | Admin (queued) | Interview appears in the Review Desk |
| `reviewed` | Admin (done) | Expert feedback is attached alongside the AI scorecard |

---

## 7. Data Flow Architecture

```
 ┌─────────────┐          ┌──────────────┐          ┌───────────────┐
 │   Frontend   │ ◄─WS──► │   Backend    │ ◄──────► │   Database    │
 │   (Browser)  │          │   (Server)   │          │  (PostgreSQL) │
 └──────┬──────┘          └──────┬───────┘          └───────────────┘
        │                        │
        │   REST API             │   Async calls
        │ ◄────────────────────► │ ◄─────────────►  ┌───────────────┐
        │                        │                   │    AI Model   │
        │                        │                   │  (GPT-4o-mini)│
        └────────────────────────┘                   └───────────────┘
```

**How data flows for a single message:**

1. Seeker types a message in the browser.
2. Message travels over the WebSocket to the backend.
3. Backend appends it to the conversation log in the database.
4. Backend checks the session status:
   - **`active_ai`** → sends conversation history + user context to the AI model → AI generates a reply → reply is saved to the log → reply is pushed back to the seeker via WebSocket.
   - **`active_human`** → message is saved and presented to the admin on the HelpDesk → admin types a reply → reply is saved to the log → reply is pushed back to the seeker via WebSocket.
5. The seeker receives the reply. It looks identical regardless of who sent it.

---

## 8. The Human-in-the-Loop Value Proposition

### What the AI does well
- **Instant availability**: Coaching at 2 AM on a Sunday? No problem. AI is always on.
- **Perfect memory**: It never forgets the job description, the seeker's resume, or what was discussed three messages ago. Every response is contextually grounded.
- **Consistent evaluation**: Every mock interview is graded against the same rubric. No mood swings, no bias, no bad days.
- **Scale**: Can handle hundreds of simultaneous coaching conversations without any degradation in quality or speed.

### What the human expert adds
- **Real-world judgment**: "This answer is technically right, but in an actual Big 4 interview, they'd want you to lead with the business impact, not the implementation detail." — this kind of nuance requires lived experience.
- **Emotional intelligence**: Spotting when a seeker is frustrated, anxious, or losing confidence — and adjusting the tone accordingly — is something humans do naturally.
- **Error correction**: Catching moments where the AI was too generous ("you scored 9/10 for confidence" on a rambling answer) or too harsh (penalizing unconventional but valid approaches).
- **Strategic direction**: "You don't need another certification. What you need is a portfolio project that demonstrates this specific skill gap." — targeted, personalized guidance that requires understanding the hiring landscape.

### Why both together are more powerful than either alone

| Scenario | AI Only | Human Only | AI + Human (HITL) |
|---|---|---|---|
| Seeker asks at 3 AM | ✅ Instant reply | ❌ No one online | ✅ AI handles it |
| 500 seekers active at once | ✅ Handles all | ❌ Impossible | ✅ AI handles bulk, human picks key ones |
| Seeker needs behavioral coaching | ⚠️ Generic advice | ✅ Nuanced, personal | ✅ AI gives base, human refines |
| AI gives bad advice | ❌ No one catches it | N/A | ✅ Human spots it and corrects |
| Mock interview evaluation | ⚠️ Technically accurate but may miss soft signals | ✅ Holistic assessment | ✅ AI scores first, human validates |
| Scaling from 100 to 10,000 users | ✅ No change needed | ❌ Need to hire 100x more coaches | ✅ AI absorbs growth, humans focus on high-impact |

The HITL model is not about replacing humans with AI or vice versa. It's about putting each where they're most effective: **AI for speed and scale, humans for judgment and depth** — with seamless, invisible transitions between the two.

---

> **Document Owner**: Ottobon Engineering
> **Last Updated**: 25 February 2026
