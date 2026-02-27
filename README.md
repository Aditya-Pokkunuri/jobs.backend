# Ottobon Jobs Platform

A comprehensive job matching platform connecting seekers with providers using AI-driven matching and real-time chat.

## Project Structure
- **Backend**: FastAPI (Python) server handling API, database interactions, and AI logic.
- **Frontend**: React + Vite application for the user interface.

## Quick Start Guide

### Prerequisites
- Python 3.10+
- Node.js 18+
- Supabase Project (URL & Anon Key)
- OpenAI API Key

### 1. Backend Setup
Navigate to the `backend` directory:
```bash
cd backend
```

Create and activate a virtual environment:
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Configure Environment Variables (`backend/.env`):
Create a `.env` file with your credentials:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_service_role_key
OPENAI_API_KEY=your_openai_api_key
```

Run the Server:
```bash
uvicorn main:app --reload
```
The API will be available at `http://localhost:8000`. API documentation is at `http://localhost:8000/docs`.

### 2. Frontend Setup
Open a new terminal and navigate to the `Frontend` directory:
```bash
cd Frontend
```

Install Node dependencies:
```bash
npm install
```

Configure Environment Variables (`Frontend/.env`):
Create a `.env` file with your public keys:
```env
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_KEY=your_supabase_anon_key
VITE_API_URL=http://localhost:8000
```

Run the Application:
```bash
npm run dev
```
The frontend will launch at `http://localhost:5173`.

## Features
- **Job Seeker**: Browse jobs, upload resume, view AI-matched scores, and chat with career coaches.
- **Provider**: Post jobs and manage listings.
- **Admin**: Control Tower for monitoring chats and triggering job ingestion scrapers.
- **Real-time Chat**: WebSocket-powered messaging between users and support agents/AI.
