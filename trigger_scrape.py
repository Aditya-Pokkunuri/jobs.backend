"""
Delete all jobs and re-scrape directly (no backend needed).
Run from backend folder: python trigger_scrape.py
"""
import asyncio
import sys
import os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.getcwd())


async def main():
    from app.dependencies import _get_supabase_client, get_all_scrapers, get_ai_service, get_embedding_service
    from app.adapters.supabase_adapter import SupabaseAdapter
    from app.services.ingestion_service import IngestionService

    client = _get_supabase_client()

    # 1. Delete old jobs
    print("[1/3] Deleting old jobs...")
    result = client.table("jobs").select("id", count="exact").execute()
    count = result.count if result.count is not None else len(result.data or [])
    print(f"  Found {count} jobs")
    if count > 0:
        # Clear related records first
        try:
            client.table("chat_sessions").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        except Exception:
            pass
        try:
            client.table("scraping_logs").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        except Exception:
            pass
        client.table("jobs").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"  Deleted {count} jobs")

    # 2. Scrape from all sources
    print("\n[2/3] Scraping from all 4 sources...")
    db = SupabaseAdapter(client)
    ai = get_ai_service()
    emb = get_embedding_service()
    service = IngestionService(db, ai, emb)
    scrapers = get_all_scrapers()

    print(f"  Sources: {[s.COMPANY_NAME for s in scrapers]}")

    for scraper in scrapers:
        name = scraper.COMPANY_NAME
        print(f"\n  >> Scraping {name}...")
        try:
            stats = await service.ingest_jobs(scraper)
            print(f"  OK - {name}: {stats}")
        except Exception as e:
            print(f"  FAIL - {name}: {type(e).__name__}: {e}")

    # 3. Final count
    result = client.table("jobs").select("id", count="exact").execute()
    final = result.count if result.count is not None else len(result.data or [])
    print(f"\n[3/3] Done! Total jobs: {final}")


if __name__ == "__main__":
    asyncio.run(main())
