# 🏗️ Ottobon Jobs — Build & Architecture Documentation

**The Gen Z Recruitment Ecosystem**  
*Outcome-Driven Matching • Neo-Brutalist UI • AI-Powered Upskilling*

---

## 🌟 Project Overview
Ottobon Jobs is a modern recruitment platform designed to disrupt traditional HR software. It connects job seekers with providers using:
1.  **Vibe Check (Matching)**: AI-driven semantic matching between resumes and job descriptions.
2.  **Level Up Zone (Upskill Bridge)**: Automatically identifies skill gaps and provides curated learning resources.
3.  **NPC Chat**: Context-aware AI career coach for instant feedback.
4.  **Loot (Tailoring)**: Generates tailored resumes to improve match scores.

## 🛠️ Technology Stack

### Backend (The Brain)
*   **Framework**: FastAPI (Python 3.10+)
*   **Database**: Supabase (PostgreSQL + pgvector)
*   **AI Engine**: OpenAI (GPT-4o) + `instructor` for structured output
*   **Architecture**: Hexagonal (Ports & Adapters)
    *   `app/domain`: Core business logic & Pydantic models
    *   `app/ports`: Abstract interfaces
    *   `app/adapters`: Concrete implementations (Supabase, OpenAI)
    *   `app/routers`: HTTP endpoints

### Frontend (The Vibe)
*   **Framework**: React 19 + Vite
*   **Styling**: Tailwind CSS v4 (Neo-Brutalist Design System)
*   **Animations**: Framer Motion (Spring physics, entrance effects)
*   **Icons**: Lucide React
*   **State**: React Hooks (Context-free for simplicity)

---

## 🚀 Setup Guide

### 1. Prerequisites
Ensure you have the following installed:
*   [Python 3.10+](https://www.python.org/downloads/)
*   [Node.js 18+](https://nodejs.org/en/download/)
*   [Git](https://git-scm.com/downloads)

### 2. Backend Setup
Navigate to the `backend` directory:
```bash
cd backend
```

**Create Virtual Environment:**
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate
```

**Install Dependencies:**
```bash
pip install -r requirements.txt
```

**Environment Configuration:**
Create a `.env` file in `backend/` with the following keys:
```env
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_KEY="your-anon-key"
SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"  # For RLS bypass
OPENAI_API_KEY="sk-..."
```

**Database Migrations:**
Run the SQL scripts located in `backend/migrations/` in your Supabase SQL Editor.
*   `006_learning_resources.sql` is critical for the Upskill Bridge feature.

**Run the Server:**
```bash
uvicorn main:app --reload
```
*Docs available at: `http://localhost:8000/docs`*

### 3. Frontend Setup
Open a new terminal and navigate to `Frontend`:
```bash
cd Frontend
```

**Install Dependencies:**
```bash
npm install
```

**Environment Configuration:**
Create a `.env` file in `Frontend/` (optional if hardcoded, but recommended):
```env
VITE_API_URL="http://127.0.0.1:8000"
```

**Run the Development Server:**
```bash
npm run dev
```
*App available at: `http://localhost:5173`*

---

## 📂 Key Features & Folder Structure

### 🎨 Neo-Brutalist Design System
*   **Location**: `Frontend/src/index.css`
*   **Fonts**: *Archivo Black* (Headings), *Space Grotesk* (Body)
*   **Tokens**: `--neo-yellow`, `--neo-green`, `--neo-pink`, `--neo-purple`
*   **Shadows**: Hard `6px` black shadows (`box-shadow: 6px 6px 0px #000`)

### 🧠 Upskill Bridge (Level Up Zone)
*   **Backend**: 
    *   `MatchingService.calculate_match` → Triggered when score < 0.7.
    *   `AIPort.extract_missing_skills` → Extracts gaps using OpenAI Structured Outputs.
    *   `DatabasePort.get_learning_resources` → Fetches courses from DB.
*   **Frontend**:
    *   `MatchPage.jsx` → Displays "Level Up Zone" with "Debuff" badges.
    *   Resources link to YouTube (curated) or dynamic search queries.

### 🧩 Hexagonal Pattern (Backend)
*   **Ports** (`backend/app/ports/`): Define *what* the system needs (e.g., `DatabasePort`, `AIPort`).
*   **Adapters** (`backend/app/adapters/`): Define *how* it's done (e.g., `SupabaseAdapter`, `OpenAIAdapter`).
*   **Services** (`backend/app/services/`): Glue logic (e.g., `JobService`, `MatchingService`).

---

## 🧪 Testing & Verification
1.  **Job Feed**: `http://localhost:5173/` should show Neo-Brutalist cards.
2.  **Match Analysis**: Upload a resume to a job.
    *   If score > 70%: See "W Match" & "Shoot Your Shot".
    *   If score < 70%: See "Needs Grinding" & "Level Up Zone".
