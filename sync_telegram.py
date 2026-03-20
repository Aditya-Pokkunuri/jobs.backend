"""
One-time sync: post all existing active jobs from the website to Telegram.

Usage:
    python sync_telegram.py              # Post ALL active jobs
    python sync_telegram.py --limit 10   # Post only the 10 most recent
"""

import asyncio
import argparse
import sys
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
sys.path.insert(0, os.getcwd())

logger = logging.getLogger(__name__)

# Telegram rate-limit delay (seconds between posts)
POST_DELAY = 1.0


async def main(limit: int | None = None):
    from app.dependencies import get_db, get_telegram_channel_service  # type: ignore

    db = get_db()
    telegram = get_telegram_channel_service()

    if not telegram._enabled:
        logger.error(
            "❌ Telegram is disabled — set TELEGRAM_BOT_TOKEN and "
            "TELEGRAM_CHANNEL_ID in .env first."
        )
        return

    # Fetch all active jobs, newest first
    logger.info("📡 Fetching active jobs from database...")
    result = (
        db._client.table("jobs_jobs")
        .select("*")
        .eq("status", "active")
        .order("created_at", desc=True)
        .execute()
    )
    jobs = result.data or []

    if limit:
        jobs = jobs[:limit]

    total = len(jobs)
    logger.info(f"📦 Found {total} active jobs to post.")

    posted = 0
    failed = 0

    for i, job in enumerate(jobs, start=1):
        logger.info(f"  [{i}/{total}] Posting: {job.get('company_name')} — {job.get('title')}")
        success = await telegram.post_job(job)
        if success:
            posted += 1
        else:
            failed += 1

        # Rate-limit to avoid Telegram throttling
        if i < total:
            await asyncio.sleep(POST_DELAY)

    logger.info(f"\n✅ Sync complete! Posted: {posted}, Failed: {failed}, Total: {total}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync active jobs to Telegram channel")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of jobs to post (most recent first). Omit for all.",
    )
    args = parser.parse_args()
    asyncio.run(main(limit=args.limit))
