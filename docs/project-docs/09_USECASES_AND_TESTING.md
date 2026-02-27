# Ottobon Jobs — Use Cases and Testing

---

## 1. Overview

This document describes the 5 strategic use cases that Ottobon Jobs is designed to handle, followed by detailed testing steps and expected outcomes for each. These use cases demonstrate the platform's AI-powered career guidance capabilities.

---

## 2. Use Cases

### Use Case 1: The "Bridge the Gap" Candidate

**Scenario:** A Junior Developer wants to apply for a Full Stack Engineer role posted by a partner organization.

**The Problem:** The user uploads their resume. The system detects they are strong in React (Frontend) but weak in Node.js (Backend), which is a required skill.

**Platform Solution:**

| Step | Feature | What Happens |
|------|---------|-------------|
| 1 | Skills Analysis | The "Skills Required" pillar highlights the gap in red |
| 2 | AI Coach Chat | AI initiates: "I see you're great with React, but this role requires Node.js. Would you like a quick roadmap?" |
| 3 | Human Tap-In | The user asks a complex question about how deep their knowledge needs to be. A background expert takes over: "For this specific client, they only need Express middleware. Check our Prep tab for a guide." |

**Outcome:** The user studies the specific prep material and applies with confidence.

---

### Use Case 2: The Career Pivoter (Resume Reframing)

**Scenario:** A Customer Support Agent wants to move into a Client Success Manager role.

**The Problem:** Their current resume is full of technical support keywords (tickets, bugs, troubleshooting) which do not match the new job description.

**Platform Solution:**

| Step | Feature | What Happens |
|------|---------|-------------|
| 1 | Resume Guide | The "How to Build the Resume" pillar auto-generates guidance: "Replace 'Resolved Tickets' with 'Managed Client Relationships'" |
| 2 | AI Coach Chat | The user asks: "How do I rephrase my experience with angry customers?" and gets tailored advice |

**Outcome:** The user rebuilds their resume using the system blueprint and passes the initial screening.

---

### Use Case 3: The "Niche Skill" Workshop Conversion

**Scenario:** A company posts a job requiring Rust Programming, a rare skill.

**The Problem:** 95% of developers only know C++ or Python and are about to leave the page.

**Platform Solution:**

| Step | Feature | What Happens |
|------|---------|-------------|
| 1 | Detection | The system detects hesitation on the Skills tab |
| 2 | AI Nudge | "Hey, noticed you're looking at the Rust role. It's tough to find resources for this." |
| 3 | Offer | "We have a 2-day workshop starting Saturday that covers exactly what this company asks for. Interested?" |

**Outcome:** Ottobon monetizes via the workshop and upskills the user.

---

### Use Case 4: The "Nervous Expert" (Interview Prep)

**Scenario:** A Senior Architect applies for a VP-level role.

**The Problem:** They have not interviewed in 10 years and lack confidence.

**Platform Solution:**

| Step | Feature | What Happens |
|------|---------|-------------|
| 1 | Prep Pillar | Behavioral questions tailored to the organization |
| 2 | AI Coach Chat | User says: "I'm really nervous about the culture fit round" |
| 3 | Human Coaching | Expert responds: "For a VP role, focus on Strategic Decision Making over technical depth. Try our Mock Interview module in the Prep tab." |

**Outcome:** The user gains executive-level confidence.

---

### Use Case 5: The "Passive Browser" Engagement

**Scenario:** A user logs in casually with no intention of applying.

**The Problem:** Passive users typically bounce quickly.

**Platform Solution:**

| Step | Feature | What Happens |
|------|---------|-------------|
| 1 | Engagement Hook | A visual graph compares their skills with the job's needs |
| 2 | AI Nudge | "Curious about Data Science? You already have 60% of the skills needed." |
| 3 | Human Validation | "You just need SQL. Check the Prep section for a guide." |

**Outcome:** A passive browser becomes an active learner and future applicant.

---

## 3. Testing Guide

### 3.1 Prerequisites

Before testing, make sure:
- Backend is running: `uvicorn main:app --reload` (port 8000)
- Frontend is running: `npm run dev -- --host` (port 5173)
- Supabase project is set up with schema applied
- `.env` file has all required variables
- At least one scraping run has been completed (or create a test job manually)

### 3.2 Test Scenario 1: User Registration and Login

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Open `http://localhost:5173/register` | Registration page loads |
| 2 | Enter email, password, select "Seeker" | All fields accept input |
| 3 | Click "Register" | Success message appears, redirect to login |
| 4 | Enter credentials on login page | All fields accept input |
| 5 | Click "Login" | Dashboard loads with job feed |
| 6 | Check the sidebar | Shows seeker-specific links: Jobs, Profile, Chat |

---

### 3.3 Test Scenario 2: Resume Upload and Processing

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to Profile page | Profile page loads with upload zone |
| 2 | Upload a PDF resume file | File is accepted, upload spinner appears |
| 3 | Wait for processing | Success message: "Resume processed successfully. X characters extracted." |
| 4 | Refresh the page | Resume filename is displayed, resume text is saved |
| 5 | Try uploading a .txt file | Error: "Unsupported file type" |
| 6 | Try uploading a scanned/image PDF | Error: "File appears to be scanned/image-based" |

---

### 3.4 Test Scenario 3: Job Browsing and Match Analysis

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to Jobs page | Job feed displays active job cards |
| 2 | Type in the search bar | Jobs filter in real time by title/company/skills |
| 3 | Click on a job card | Job detail page loads with 4 tabs |
| 4 | View the Prep tab | 5 AI-generated interview questions are displayed |
| 5 | View the Resume Tips tab | 5 AI-generated resume optimization tips are displayed |
| 6 | Click "Check My Fit" | Match page loads |
| 7 | Match score is displayed | Score shows as percentage (0-100%), gap badge if below 70% |

---

### 3.5 Test Scenario 4: AI Career Coach Chat

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to Chat page | Chat interface loads, connection indicator shows "Connected" |
| 2 | Type a message and press Enter | Message appears on the right (user bubble) |
| 3 | Wait for AI response | Response appears on the left (assistant bubble) within a few seconds |
| 4 | Ask about a specific skill gap | AI references your resume context in the response |
| 5 | Wait 30+ seconds idle | No disconnection (heartbeat keeps the connection alive) |
| 6 | Check server logs | Heartbeat pings are received and processed |

---

### 3.6 Test Scenario 5: Provider Job Creation

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Register as a Provider role user | Provider-specific sidebar links appear |
| 2 | Navigate to Create Job page | Job creation form loads |
| 3 | Fill in title, description, and skills | All fields accept input |
| 4 | Click "Create Job" | Success message appears with note about background enrichment |
| 5 | Navigate to My Listings | New job appears with status "processing" |
| 6 | Wait a few seconds, refresh | Status changes to "active" after AI enrichment completes |
| 7 | Click the job to view details | All 4 pillars are populated |

---

### 3.7 Test Scenario 6: Admin Control Tower

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Log in as Admin user | Admin-specific sidebar links appear |
| 2 | Navigate to Control Tower | Dashboard shows active chat sessions |
| 3 | Click "Takeover" on a session | Success message appears |
| 4 | Check the seeker's chat window | A notification appears: "A human agent has joined" |
| 5 | Session mode changes | Status switches from "active_ai" to "active_human" |

---

### 3.8 Test Scenario 7: Job Ingestion

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Log in as Admin user | Admin sidebar links visible |
| 2 | Navigate to Ingestion page | Four scraper cards are displayed |
| 3 | Click "Sync" on one source | Loading spinner appears |
| 4 | Wait for completion | JSON result shows: fetched, new, skipped, errors |
| 5 | Navigate to Jobs feed | Newly scraped jobs appear in the listing |
| 6 | Click "Sync All" | All sources trigger ingestion in background |

---

## 4. Acceptance Criteria

| Criteria | Metric |
|----------|--------|
| All use cases are functionally possible | Users can register, upload resumes, match, chat, and receive AI guidance |
| Match scores are accurate | Cosine similarity computed correctly between resume and job embeddings |
| Chat is responsive | AI responses return within 5 seconds |
| Heartbeat prevents disconnection | WebSocket stays connected for 10+ minutes of idle time |
| Admin takeover works immediately | Session switches from AI to human mode within 1 second |
| Ingestion completes without errors | All 4 scrapers successfully fetch and store jobs |
| Enrichment populates all pillars | Every active job has resume tips, prep questions, and embedding |
