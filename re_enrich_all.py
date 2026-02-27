import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from app.dependencies import _get_supabase_client, get_ai_service, get_embedding_service
from app.adapters.supabase_adapter import SupabaseAdapter
from app.services.enrichment_service import EnrichmentService

async def re_enrich_all():
    print("Initializing...")
    client = _get_supabase_client()
    db = SupabaseAdapter(client)
    ai = get_ai_service()
    emb = get_embedding_service()
    
    service = EnrichmentService(db, ai, emb)
    
    # Set high limit to cover all current jobs (we have ~27)
    print("Fetching ALL active jobs...")
    jobs = await db.list_active_jobs(limit=1000)
    
    print(f"Found {len(jobs)} active jobs.")
    print("Starting BATCH enrichment (concurrent)...")
    
    sem = asyncio.Semaphore(5) # 5 concurrent requests

    async def enrich_safe(job, idx):
        async with sem:
            print(f"[{idx}/{len(jobs)}] START: {job['title']}...")
            try:
                await service.enrich_job(job['id'])
                print(f"[{idx}/{len(jobs)}] DONE: {job['title']}")
            except Exception as e:
                print(f"[{idx}/{len(jobs)}] FAILED: {job['title']} - {e}")

    tasks = [enrich_safe(job, i) for i, job in enumerate(jobs, 1)]
    await asyncio.gather(*tasks)
    print("ALL DONE.")

if __name__ == "__main__":
    asyncio.run(re_enrich_all())
