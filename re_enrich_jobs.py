import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from app.dependencies import _get_supabase_client, get_ai_port, get_embedding_port
from app.adapters.supabase_adapter import SupabaseAdapter
from app.services.enrichment_service import EnrichmentService

async def re_enrich():
    print("Initializing...")
    client = _get_supabase_client()
    db = SupabaseAdapter(client)
    ai = get_ai_port()
    emb = get_embedding_port()
    
    service = EnrichmentService(db, ai, emb)
    
    print("Fetching top 5 active jobs...")
    jobs = await db.list_active_jobs(limit=5)
    
    print(f"Re-enriching {len(jobs)} jobs...")
    for job in jobs:
        print(f"Enriching: {job['title']} ({job['id']})")
        await service.enrich_job(job['id'])
        print("Done.")

if __name__ == "__main__":
    asyncio.run(re_enrich())
