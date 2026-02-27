"""Scrape + enrich all Big 4 jobs in one pipeline.

Usage:
    python scrape_and_enrich.py

This script:
1. Fetches jobs from all 4 scrapers (PwC, KPMG, Deloitte, EY)
2. Inserts them into Supabase
3. Runs AI enrichment (resume guide, prep questions, embedding) for each job
"""
import asyncio
import logging
import os
from dotenv import load_dotenv
from supabase import create_client

from app.scraper.deloitte_adapter import DeloitteAdapter
from app.scraper.pwc_adapter import PwCAdapter
from app.scraper.kpmg_adapter import KPMGAdapter
from app.scraper.ey_adapter import EYAdapter
from app.adapters.supabase_adapter import SupabaseAdapter
from app.adapters.openai_adapter import OpenAIAdapter
from app.adapters.openai_embedding import OpenAIEmbeddingAdapter
from app.services.enrichment_service import EnrichmentService

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s │ %(levelname)-8s │ %(message)s")
logger = logging.getLogger(__name__)

INGESTION_PROVIDER_ID = "00000000-0000-4000-a000-000000000001"


async def main():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    openai_key = os.environ["OPENAI_API_KEY"]

    sb = create_client(url, key)
    db = SupabaseAdapter(sb)
    ai = OpenAIAdapter(api_key=openai_key)
    emb = OpenAIEmbeddingAdapter(api_key=openai_key)
    enricher = EnrichmentService(db=db, ai=ai, embeddings=emb)

    scrapers = [
        ("PwC", PwCAdapter()),
        ("KPMG", KPMGAdapter()),
        ("Deloitte", DeloitteAdapter()),
        ("EY", EYAdapter()),
    ]

    total_inserted = 0
    total_enriched = 0

    for company_name, scraper in scrapers:
        print(f"\n{'='*60}")
        print(f"  {company_name}")
        print(f"{'='*60}")

        try:
            jobs = await scraper.fetch_jobs()
            print(f"✅ Fetched {len(jobs)} jobs")
        except Exception as e:
            print(f"❌ Scraper failed: {e}")
            continue

        for job_data in jobs:
            job_data.setdefault("company_name", company_name)
            job_data.setdefault("description_raw", "")
            job_data.setdefault("skills_required", [])
            job_data.setdefault("status", "processing")  # will become 'active' after enrichment
            job_data["provider_id"] = INGESTION_PROVIDER_ID

            # Skip jobs with no real description (can't enrich them clearly)
            desc = job_data.get("description_raw", "")
            
            # Check for bad descriptions
            is_placeholder = (
                not desc 
                or len(desc) < 200 
                or "Visit the official career page" in desc
                or desc.startswith("Posted:")
            )

            if is_placeholder:
                # Insert but mark as 'active' without enrichment data (so frontend shows "Not available" instead of bad AI)
                job_data["status"] = "active"
            
            try:
                # Check if already exists
                existing = sb.table("jobs") \
                    .select("id") \
                    .eq("company_name", job_data["company_name"]) \
                    .eq("external_id", job_data.get("external_id", "")) \
                    .maybe_single() \
                    .execute()

                if existing and existing.data:
                    logger.debug("Skipping duplicate: %s / %s",
                                 company_name, job_data.get("external_id"))
                    continue

                result = sb.table("jobs").insert(job_data).execute()
                created = result.data[0]
                total_inserted += 1

                # Run enrichment ONLY if we have a real description
                if not is_placeholder:
                    try:
                        await enricher.enrich_job(created["id"])
                        await db.update_job(created["id"], {"status": "active"})
                        total_enriched += 1
                        print(f"  ✅ {job_data['title'][:50]} — enriched (Desc len: {len(desc)})")
                    except Exception as e:
                        await db.update_job(created["id"], {"status": "active"})
                        print(f"  ⚠️ {job_data['title'][:50]} — enrichment failed: {e}")
                else:
                    print(f"  ➡️  {job_data['title'][:50]} — skipped enrichment (Low quality desc)")

            except Exception as e:
                print(f"  ❌ Failed: {job_data.get('title', '?')}: {e}")

    print(f"\n{'='*60}")
    print(f"  DONE! Inserted: {total_inserted} | Enriched: {total_enriched}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
