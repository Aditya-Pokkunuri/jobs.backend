"""
Enrichment service — async AI generation of resume guides + prep questions.
Runs as a FastAPI BackgroundTask after job creation.

Production hardening:
  - Batch API stub for future 50% token cost savings on scraped jobs.
"""

import logging

from app.ports.ai_port import AIPort
from app.ports.database_port import DatabasePort
from app.ports.embedding_port import EmbeddingPort

logger = logging.getLogger(__name__)


class EnrichmentService:
    """Orchestrates the AI enrichment pipeline for a job posting."""

    def __init__(
        self,
        db: DatabasePort,
        ai: AIPort,
        embeddings: EmbeddingPort,
    ) -> None:
        self._db = db
        self._ai = ai
        self._emb = embeddings

    async def enrich_job(self, job_id: str) -> None:
        """
        Synchronous (single-job) enrichment:
        1. Fetches the job record
        2. Calls AI for resume guide + prep questions
        3. Generates a vector embedding of the job description
        4. Updates the job record with all enrichment data
        """
        try:
            job = await self._db.get_job(job_id)
            if not job:
                logger.error("Enrichment failed: job %s not found", job_id)
                return

            description = job["description_raw"]
            skills = job.get("skills_required") or []
            title = job.get("title", "")
            company = job.get("company_name", "")

            # Step 1: AI enrichment (structured output via Instructor)
            enrichment = await self._ai.generate_enrichment(
                description, skills, title=title, company_name=company
            )

            # Step 2: Generate job embedding
            embedding = await self._emb.encode(description)

            # Step 3: Persist results
            # Ensure proper serialization of Pydantic models to list of dicts
            prep_data = [q.model_dump() for q in enrichment.prep_questions]
            
            # Use extracted skills if the job has none (e.g. scraped jobs)
            final_skills = skills if skills else enrichment.extracted_skills

            await self._db.update_job(
                job_id,
                {
                    "resume_guide_generated": enrichment.resume_guide,
                    "prep_guide_generated": prep_data,
                    # "extracted_skills": enrichment.extracted_skills, # Column doesn't exist, so we don't save raw
                    "skills_required": final_skills, # Populate main skills field if empty
                    "embedding": embedding,
                    "salary_range": enrichment.estimated_salary_range,
                },
            )

            logger.info("Enrichment complete for job %s", job_id)

        except Exception:
            logger.exception("Enrichment failed for job %s", job_id)

    async def enrich_jobs_batch(self, job_ids: list[str]) -> str:
        """
        Batch enrichment stub — for future integration with OpenAI Batch API.

        The Batch API offers ~50% cost reduction but has a 24-hour turnaround.
        Use this for scraped jobs where instant availability is not critical.

        TODO: Implement when a polling worker is built:
          1. Build JSONL payloads for each job_id
          2. Submit via openai.batches.create(input_file_id=..., endpoint="/v1/chat/completions")
          3. Store batch_id for the polling worker to check status
          4. On batch completion, parse results and update jobs

        Returns:
            A placeholder batch_id string.
        """
        logger.info(
            "Batch enrichment requested for %d jobs (stub — falling back to sequential)",
            len(job_ids),
        )
        # Fallback: process sequentially until batch worker is implemented
        for job_id in job_ids:
            await self.enrich_job(job_id)

        return "batch_stub_sequential"
