"""
Ingestion service — orchestrates the scrape → dedup → insert → enrich pipeline.
Single Responsibility: only handles external job ingestion logic.

Production hardening:
  - Fail-fast per-scraper: if fetch_jobs() throws, log to scraping_logs and move on.
  - SHA-256 dedup: skip AI enrichment for duplicate job descriptions.
"""

import hashlib
import logging
import traceback
from datetime import datetime, timezone
from typing import Any

from app.ports.ai_port import AIPort
from app.ports.database_port import DatabasePort
from app.ports.embedding_port import EmbeddingPort
from app.scraper.scraper_port import ScraperPort
from app.services.enrichment_service import EnrichmentService

logger = logging.getLogger(__name__)

# System user UUID that "owns" all scraped/ingested jobs.
# Must match the UUID inserted by external_ingestion_migration.sql.
INGESTION_PROVIDER_ID = "00000000-0000-4000-a000-000000000001"


class IngestionService:
    """
    Fetches jobs from a scraper, deduplicates against existing records,
    inserts new ones, and triggers AI enrichment for each.
    """

    def __init__(
        self,
        db: DatabasePort,
        ai: AIPort,
        embeddings: EmbeddingPort,
    ) -> None:
        self._db = db
        self._ai = ai
        self._emb = embeddings

    async def ingest_jobs(self, scraper: ScraperPort) -> dict[str, Any]:
        """
        Full ingestion pipeline with resilience:
        1. Create a scraping_log entry (status='running')
        2. Fetch jobs from the external scraper (fail-fast on error)
        3. Deduplicate by (company_name, external_id)
        4. SHA-256 hash dedup for AI enrichment cost savings
        5. Insert new jobs and trigger enrichment
        6. Finalize scraping_log with results

        Returns a stats dict: {fetched, new, skipped, errors, dedup_hits}
        """
        source_name = scraper.COMPANY_NAME.lower()
        started_at = datetime.now(timezone.utc).isoformat()

        # Create log entry at the start of the run
        log_entry = await self._db.insert_scraping_log({
            "source_name": source_name,
            "status": "running",
            "started_at": started_at,
        })
        log_id = log_entry["id"]

        stats: dict[str, Any] = {
            "fetched": 0, "new": 0, "skipped": 0,
            "errors": 0, "dedup_hits": 0,
        }

        # ── Step 1: Fetch (fail-fast on scraper failure) ──────
        try:
            raw_jobs = await scraper.fetch_jobs()
            stats["fetched"] = len(raw_jobs)
        except Exception as exc:
            tb = traceback.format_exc()
            logger.error(
                "Scraper %s failed during fetch: %s", source_name, exc
            )
            await self._db.update_scraping_log(log_id, {
                "status": "failed",
                "error_message": str(exc),
                "traceback": tb,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            })
            # Return stats — don't crash the global run
            return {**stats, "error": str(exc)}

        # ── Step 2: Process each job ──────────────────────────
        for job_data in raw_jobs:
            company = job_data["company_name"]
            ext_id = job_data["external_id"]

            try:
                # Dedup check by external ID
                existing = await self._db.find_job_by_external_id(company, ext_id)
                if existing:
                    logger.debug("Skipping duplicate: %s / %s", company, ext_id)
                    stats["skipped"] += 1
                    continue

                # Compute description hash for AI cost dedup
                desc_raw = job_data.get("description_raw", "")
                desc_hash = (
                    hashlib.sha256(desc_raw.encode()).hexdigest()
                    if desc_raw else None
                )

                # Insert the job
                created = await self._db.create_job({
                    "provider_id": INGESTION_PROVIDER_ID,
                    "title": job_data["title"],
                    "description_raw": desc_raw,
                    "skills_required": job_data.get("skills_required", []),
                    "external_id": ext_id,
                    "external_apply_url": job_data.get("external_apply_url"),
                    "company_name": company,
                    "description_hash": desc_hash,
                    "status": "processing",
                })

                # SHA-256 dedup: check if an enriched job with same hash exists
                if desc_hash:
                    donor = await self._db.find_job_by_description_hash(desc_hash)
                    if donor:
                        # Copy enrichment data — skip AI call entirely
                        await self._db.update_job(created["id"], {
                            "resume_guide_generated": donor["resume_guide_generated"],
                            "prep_guide_generated": donor["prep_guide_generated"],
                            "embedding": donor["embedding"],
                            "status": "active",
                        })
                        stats["new"] += 1
                        stats["dedup_hits"] += 1
                        logger.info(
                            "Dedup hit — copied enrichment for %s / %s",
                            company, ext_id,
                        )
                        continue

                # No dedup hit — run full enrichment
                enricher = EnrichmentService(
                    db=self._db, ai=self._ai, embeddings=self._emb
                )
                await enricher.enrich_job(created["id"])
                await self._db.update_job(created["id"], {"status": "active"})

                stats["new"] += 1
                logger.info("Ingested & enriched: %s / %s", company, ext_id)

            except Exception:
                logger.exception(
                    "Failed to ingest job: %s / %s", company, ext_id
                )
                stats["errors"] += 1

        # ── Step 3: Finalize log ──────────────────────────────
        final_status = "success"
        if stats["errors"] > 0 and stats["new"] > 0:
            final_status = "partial"
        elif stats["errors"] > 0 and stats["new"] == 0:
            final_status = "failed"

        await self._db.update_scraping_log(log_id, {
            "status": final_status,
            "jobs_found": stats["fetched"],
            "jobs_new": stats["new"],
            "jobs_skipped": stats["skipped"],
            "error_count": stats["errors"],
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })

        logger.info("Ingestion complete for %s: %s", source_name, stats)
        return stats
