"""
Ingestion endpoints — admin-triggered external job scraping.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from app.dependencies import get_ai_service, get_db, get_embedding_service, get_scraper
from app.ports.ai_port import AIPort
from app.ports.database_port import DatabasePort
from app.ports.embedding_port import EmbeddingPort
from app.services.auth_service import get_current_user
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/ingest/all", status_code=status.HTTP_200_OK)
async def ingest_all_sources(
    background_tasks: BackgroundTasks,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Trigger ingestion for ALL configured sources (background task)."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can trigger ingestion",
        )

    # We run this in background because it takes a while
    from app.scheduler import run_daily_ingestion
    background_tasks.add_task(run_daily_ingestion)

    return {"message": "Global ingestion triggered in background"}


@router.post("/ingest/{source_name}", status_code=status.HTTP_200_OK)
async def trigger_ingestion(
    source_name: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
    ai: AIPort = Depends(get_ai_service),
    emb: EmbeddingPort = Depends(get_embedding_service),
):
    """
    Admin-only: trigger external job ingestion from a named source.

    Supported sources: deloitte, pwc, kpmg, ey
    """
    # Admin role check
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can trigger ingestion",
        )

    # Resolve source name → scraper adapter
    try:
        scraper = get_scraper(source_name)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown source: '{source_name}'. "
            f"Available: deloitte, pwc, kpmg, ey",
        )

    svc = IngestionService(db=db, ai=ai, embeddings=emb)
    stats = await svc.ingest_jobs(scraper)

    return {
        "source": source_name,
        "result": stats,
    }
