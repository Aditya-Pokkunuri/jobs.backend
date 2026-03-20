"""
Trigger Generic Ingestion safely (non-destructive).
"""
import asyncio
import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore
sys.path.insert(0, os.getcwd())

async def main():
    from app.dependencies import (
        get_db, 
        get_ai_service, 
        get_embedding_service, 
        get_job_service,
        get_telegram_channel_service
    )  # type: ignore
    from app.scraper.generic_adapter import GenericAdapter  # type: ignore

    db = get_db()
    ai = get_ai_service()
    emb = get_embedding_service()
    job_svc = get_job_service(db)
    telegram_svc = get_telegram_channel_service()
    
    from app.services.ingestion_service import IngestionService # type: ignore
    service = IngestionService(db, ai, emb, telegram_svc)
    
    scraper = GenericAdapter()
    
    # Optional: Limiting to a few URLs for the very first live test if you want to be quick
    # scraper.target_urls = scraper.target_urls[:5] 

    print(f"🚀 Starting Generic Scraper for {len(scraper.target_urls)} sites...")
    try:
        stats = await service.ingest_jobs(scraper)
        print(f"\n✅ Stats: {stats}")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
