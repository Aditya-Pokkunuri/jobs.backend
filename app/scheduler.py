"""
Scheduler module for periodic background tasks.
Uses APScheduler's AsyncIOScheduler.

Production hardening:
  - Supabase-backed distributed lock prevents duplicate cron runs
    when multiple Uvicorn workers are active.
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.dependencies import get_all_scrapers
from app.services.ingestion_service import IngestionService
# Import dependencies explicitly for manual resolution
from app.dependencies import _get_supabase_client, get_ai_service, get_embedding_service
from app.adapters.supabase_adapter import SupabaseAdapter

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()

# Lock TTL in minutes — if a worker crashes mid-ingestion, the lock
# auto-expires after this duration so another worker can pick it up.
_LOCK_TTL_MINUTES = 30


async def _acquire_cron_lock(lock_name: str) -> bool:
    """
    Attempt to acquire a distributed lock via Supabase `cron_locks` table.

    Uses PostgreSQL's conflict-handling to guarantee exactly one winner:
      - INSERT a new lock row if none exists.
      - ON CONFLICT, UPDATE only if the existing lock has expired
        (locked_until < NOW()).

    Returns True if this worker acquired the lock, False otherwise.
    """
    client = _get_supabase_client()
    try:
        # Use raw SQL via Supabase RPC for atomic upsert with conditional update.
        # This is the only way to atomically check locked_until < NOW() in one shot.
        result = client.rpc("acquire_cron_lock", {
            "p_lock_name": lock_name,
            "p_ttl_minutes": _LOCK_TTL_MINUTES,
        }).execute()

        # The RPC returns true/false indicating whether the lock was acquired
        acquired = result.data if result.data is not None else False
        logger.info(
            "Cron lock '%s': %s",
            lock_name,
            "ACQUIRED ✓" if acquired else "ALREADY HELD ✗",
        )
        return acquired

    except Exception as exc:
        # If the cron_locks table doesn't exist yet (migration not run),
        # fall through and allow execution (single-worker backward compat).
        logger.warning(
            "Cron lock acquisition failed (table may not exist yet): %s. "
            "Proceeding without lock — safe only for single-worker deploys.",
            exc,
        )
        return True


async def _release_cron_lock(lock_name: str) -> None:
    """Release a distributed lock by setting locked_until to the past."""
    client = _get_supabase_client()
    try:
        client.table("cron_locks").update({
            "locked_until": "2000-01-01T00:00:00Z",  # Far past → effectively unlocked
        }).eq("lock_name", lock_name).execute()
        logger.info("Cron lock '%s' released.", lock_name)
    except Exception as exc:
        logger.warning("Failed to release cron lock '%s': %s", lock_name, exc)


async def trigger_ingestion(scraper_name: Optional[str] = None):
    """
    Core ingestion logic. Can be called by scheduler or manual API trigger.
    Args:
        scraper_name: If provided, only run this specific scraper (case-insensitive).
                      If None or 'all', run all scrapers.
    """
    logger.info(f"🕒 Starting ingestion process (target: {scraper_name or 'ALL'})...")

    # Manually resolve dependencies
    client = _get_supabase_client()
    db = SupabaseAdapter(client)
    ai = get_ai_service()
    emb = get_embedding_service()
    
    service = IngestionService(db, ai, emb)
    all_scrapers = get_all_scrapers()
    
    # Filter scrapers if a specific name is requested
    if scraper_name and scraper_name.lower() != "all":
        target = scraper_name.lower()
        scrapers = [s for s in all_scrapers if s.COMPANY_NAME.lower() == target]
        if not scrapers:
            logger.warning(f"⚠️ No scraper found matching '{scraper_name}'")
            return {"error": f"Scraper '{scraper_name}' not found"}
    else:
        scrapers = all_scrapers

    logger.info(f"Scrapers to run: {[s.COMPANY_NAME for s in scrapers]}")

    results = {}
    for scraper in scrapers:
        source_name = scraper.COMPANY_NAME.lower()
        logger.info(f"  ► Triggering scraper: {source_name}")
        try:
            stats = await service.ingest_jobs(scraper)
            results[source_name] = stats
            logger.info(f"  ✓ {source_name}: {stats}")
        except Exception as e:
            logger.error(f"  ✗ {source_name} failed: {e}")
            results[source_name] = {"error": str(e)}
            
    logger.info(f"🕒 Ingestion complete. Stats: {results}")
    return results


async def run_daily_ingestion():
    """
    Task wrapper for scheduled execution with distributed locking.

    Only the worker that acquires the 'daily_ingestion' lock proceeds.
    This prevents N workers from spawning N duplicate scraping runs.
    """
    lock_name = "daily_ingestion"

    if not await _acquire_cron_lock(lock_name):
        logger.info("Another worker holds the ingestion lock — skipping this run.")
        return

    try:
        await trigger_ingestion(scraper_name="all")
    finally:
        # Always release the lock, even if ingestion fails,
        # so the next scheduled run can proceed.
        await _release_cron_lock(lock_name)


def start_scheduler():
    """Start the background scheduler."""
    # Schedule ingest at 10:00 PM IST (Asia/Kolkata)
    trigger = CronTrigger(
        hour=22, 
        minute=0, 
        timezone=ZoneInfo("Asia/Kolkata")
    )
    
    scheduler.add_job(
        run_daily_ingestion, 
        trigger, 
        id="daily_ingestion",
        replace_existing=True,
    )
    
    scheduler.start()
    
    # Log next run time
    job = scheduler.get_job("daily_ingestion")
    if job:
        logger.info(f"📅 Scheduler started. Next ingestion run at: {job.next_run_time}")


def shutdown_scheduler():
    """Stop the scheduler."""
    scheduler.shutdown()
    logger.info("Scheduler shut down.")
