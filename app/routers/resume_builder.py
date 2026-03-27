"""
Resume Builder router — new endpoints for the improved resume tailoring
and download workflow.

Endpoints:
  POST /resume-builder/{job_id}/tailor   — AI-tailored resume (auth + anti-fabrication)
  POST /resume-builder/download          — Convert tailored Markdown → downloadable .docx
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.adapters.resume_ai_adapter import ResumeAIAdapter
from app.config import settings
from app.dependencies import get_db
from app.ports.database_port import DatabasePort
from app.services.auth_service import get_current_user
from app.utils.document_utils import generate_docx_from_markdown

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resume-builder", tags=["Resume Builder"])


# ── Request / Response schemas ──────────────────────────────


class ResumeDownloadRequest(BaseModel):
    """Body for the download endpoint."""

    tailored_resume: str = Field(
        ..., min_length=10, description="Markdown text of the tailored resume"
    )
    job_title: str = Field(
        ..., min_length=1, max_length=200, description="Job title for the filename"
    )


# ── Helpers ─────────────────────────────────────────────────


def _get_resume_ai() -> ResumeAIAdapter:
    """Instantiate the enhanced AI adapter."""
    return ResumeAIAdapter(api_key=settings.openai_api_key)


def _sanitize_filename(name: str) -> str:
    """Make a string safe for use in a filename."""
    return "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in name).strip()


# ── Endpoints ───────────────────────────────────────────────


@router.post("/{job_id}/tailor")
async def tailor_resume_secure(
    job_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """
    Rewrite the authenticated user's resume to target a specific job.

    Uses the improved ResumeAIAdapter with:
      - gpt-4o-mini for faster responses
      - 1200-token cap
      - Anti-fabrication guardrails
      - Full JWT signature verification
    """
    # 1. Get user resume
    user = await db.get_user(current_user["id"])
    if not user or not user.get("resume_text"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No resume found. Please upload one first.",
        )

    # 2. Get job description
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    # 3. Call enhanced AI adapter
    ai = _get_resume_ai()
    try:
        tailoring_result = await ai.tailor_resume(
            resume_text=user["resume_text"],
            job_description=job["description_raw"],
            job_title=job.get("title", "the target role"),
            company_name=job.get("company_name", "the target company"),
        )
    except Exception as exc:
        logger.error(f"Resume tailoring failed for job {job_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume tailoring failed: {type(exc).__name__}",
        )

    return tailoring_result


@router.post("/download")
async def download_tailored_resume(body: ResumeDownloadRequest):
    """
    Convert a Markdown resume into a downloadable .docx file.

    Accepts the tailored resume text and job title, returns a Word document
    as a streaming download.
    """
    try:
        docx_buffer = generate_docx_from_markdown(body.tailored_resume)
    except Exception as exc:
        logger.error(f"DOCX generation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document generation failed: {type(exc).__name__}",
        )

    safe_title = _sanitize_filename(body.job_title)
    filename = f"tailored_resume_{safe_title}.docx"

    return StreamingResponse(
        docx_buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
