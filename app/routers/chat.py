"""
WebSocket endpoint + REST endpoints for the Control Tower chat system.

Production hardening:
  - History replay on WebSocket connect (last 10 messages)
  - Reject connections to closed sessions
  - Status-aware routing (AI vs human mode)
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status

from app.dependencies import get_ai_service, get_db
from app.domain.models import ChatSessionInfo
from app.ports.ai_port import AIPort
from app.ports.database_port import DatabasePort
from app.services.auth_service import get_current_user
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chat"])


class ConnectionManager:
    """
    Manages active WebSocket connections keyed by session_id.
    In production, replace with Redis Pub/Sub for horizontal scaling.
    """

    def __init__(self) -> None:
        self._active: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._active[session_id] = websocket

    def disconnect(self, session_id: str) -> None:
        self._active.pop(session_id, None)

    async def send_message(self, session_id: str, message: str) -> None:
        ws = self._active.get(session_id)
        if ws:
            await ws.send_text(message)

    def get(self, session_id: str) -> WebSocket | None:
        return self._active.get(session_id)


# Shared instance used by both this router and the admin router
manager = ConnectionManager()


# ── REST endpoints for chat session management ────────────────

from pydantic import BaseModel

class CreateSessionRequest(BaseModel):
    job_id: str | None = None


@router.post(
    "/chat/sessions",
    response_model=ChatSessionInfo,
    status_code=status.HTTP_201_CREATED,
)
async def create_chat_session(
    body: CreateSessionRequest = None,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """
    Create a new chat session or return an existing active one for the same job.
    """
    user_id = current_user["id"]
    job_id = body.job_id if body else None

    # 1. Try to find existing session if job_id provided
    if job_id:
        existing = await db.find_chat_session(user_id, job_id)
        if existing:
            return ChatSessionInfo(**existing)

    # 2. Build initial context to seed the conversation_log
    initial_log = []
    if job_id:
        # Fetch job details so coach has full context
        job = await db.get_job(job_id)
        if job:
            initial_log.append({
                "role": "system",
                "content": f"__job_context__|{job_id}",
                "job_id": job_id,
                "job_title": job.get("title", ""),
                "job_description": (job.get("description_raw") or "")[:3000],
                "skills_required": job.get("skills_required", []),
                "hidden": True,
            })

    # 3. Create new session
    session = await db.create_chat_session(
        user_id=user_id,
        initial_log=initial_log,
        job_id=job_id,
    )
    return ChatSessionInfo(**session)


@router.get("/chat/my-sessions", response_model=list[ChatSessionInfo])
async def list_my_sessions(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """List all chat sessions for the current user."""
    sessions = await db.list_user_sessions(current_user["id"])
    
    # Flatten the Supabase join result: {'jobs': {'title': '...'}} -> job_title
    results = []
    for s in sessions:
        if s.get("jobs"):
            s["job_title"] = s["jobs"].get("title")
        results.append(ChatSessionInfo(**s))
        
    return results


@router.get("/chat/sessions/{session_id}", response_model=ChatSessionInfo)
async def get_chat_session(
    session_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """Retrieve info about an existing chat session."""
    session = await db.get_chat_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )
    return ChatSessionInfo(**session)


# ── WebSocket endpoint ────────────────────────────────────────


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
    db: DatabasePort = Depends(get_db),
    ai: AIPort = Depends(get_ai_service),
):
    """
    Real-time chat endpoint with state recovery.

    On connect:
      1. Validate session exists and is not closed.
      2. Replay last 10 messages from conversation_log (state recovery).
      3. If no messages yet, send an auto-greeting from the coach.
      4. Enter message loop (AI mode or human mode based on status).
    """
    # Validate session exists
    session = await db.get_chat_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    # Reject closed sessions
    session_status = session.get("status", "active_ai")
    if session_status == "closed":
        await websocket.close(code=4003, reason="Session is closed")
        return

    await manager.connect(session_id, websocket)
    chat_svc = ChatService(db=db, ai=ai)

    try:
        # ── History replay for state recovery ─────────────────
        recent_messages, current_status = await chat_svc.get_recent_history(
            session_id, count=10
        )
        await websocket.send_text(json.dumps({
            "type": "history_replay",
            "messages": recent_messages,
            "session_status": current_status,
        }))

        # ── Auto-greeting for new/empty sessions ─────────────
        if not recent_messages and current_status == "active_ai":
            try:
                greeting = await chat_svc.generate_greeting(session_id)
                if greeting:
                    await websocket.send_text(json.dumps({
                        "type": "ai_reply",
                        "content": greeting,
                    }))
            except Exception as e:
                logger.warning("Auto-greeting failed: %s", e)

        # ── Main message loop ─────────────────────────────────
        while True:
            data = await websocket.receive_text()

            # Ignore heartbeat pings
            if data == "__ping__":
                await websocket.send_text("__pong__")
                continue

            # Ignore empty/whitespace messages
            if not data.strip():
                continue

            try:
                reply = await chat_svc.handle_message(
                    session_id=session_id,
                    user_message=data,
                )

                if reply is not None:
                    # AI mode → push reply immediately
                    await websocket.send_text(json.dumps({
                        "type": "ai_reply",
                        "content": reply,
                    }))
                else:
                    # Human mode → acknowledge receipt
                    await websocket.send_text(json.dumps({
                        "type": "queued",
                        "content": "An admin will respond shortly.",
                    }))
            except Exception as e:
                logger.error("Error handling message in session %s: %s", session_id, e)
                await websocket.send_text(json.dumps({
                    "type": "ai_reply",
                    "content": "I'm having a moment — please try again.",
                }))

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        logger.info("WebSocket disconnected for session %s", session_id)
