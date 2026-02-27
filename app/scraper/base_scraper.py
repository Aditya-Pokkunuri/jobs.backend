"""
Base scraper with shared logic for all company adapters.

Phase 1: Returns mock data for pipeline testing.
Phase 2: Replace fetch_jobs() with real HTTP scraping logic
         using self.CAREER_PAGE_URL — subclass files stay untouched.
"""

from typing import Any

from app.scraper.scraper_port import ScraperPort


import asyncio
import logging
from typing import Any

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler

from app.scraper.scraper_port import ScraperPort
from app.scraper.experience_filter import is_entry_level

logger = logging.getLogger(__name__)


class BaseScraper(ScraperPort):
    """
    Base scraper with shared logic for all company adapters.
    Uses crawl4ai (Playwright) to fetch JS-rendered pages.
    """

    COMPANY_NAME: str = ""
    CAREER_PAGE_URL: str = ""

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        """
        Fetches jobs from the career page, parses them, and filters for entry-level.
        """
        logger.info(f"🕸️ Scraping {self.COMPANY_NAME} from {self.CAREER_PAGE_URL}...")
        
        try:
            # crawl4ai async context manager handles browser life-cycle
            async with AsyncWebCrawler(verbose=True) as crawler:
                result = await crawler.arun(
                    url=self.CAREER_PAGE_URL,
                )
                
                if not result.html:
                    logger.warning(f"⚠️ No HTML returned for {self.COMPANY_NAME}")
                    return []

                # Parse HTML
                soup = BeautifulSoup(result.html, "html.parser")
                
                # Extract raw job cards (implemented by subclasses)
                raw_jobs = self.parse_jobs(soup)
                logger.info(f"  ↳ Found {len(raw_jobs)} raw jobs for {self.COMPANY_NAME}")

                # Filter and normalize
                valid_jobs = []
                for job in raw_jobs:
                    # Check if entry level
                    if is_entry_level(job["title"], job.get("experience_text", "")):
                        # Normalize keys for our DB
                        normalized = {
                            "external_id": job["external_id"],
                            "title": job["title"],
                            "company_name": self.COMPANY_NAME,
                            "external_apply_url": job["external_apply_url"],
                            "description_raw": job.get("description", ""),
                            "skills_required": [],  # Enrichment will fill this
                            "location": job.get("location", "India"),
                            "salary_range": job.get("salary", None),
                        }
                        valid_jobs.append(normalized)

                logger.info(f"  ✅ Filtered to {len(valid_jobs)} entry-level jobs")
                return valid_jobs

        except Exception as e:
            logger.error(f"❌ Failed to scrape {self.COMPANY_NAME}: {e}")
            return []

    def parse_jobs(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """
        Abstract method: Parse the BeautifulSoup object and return a list of dicts.
        """
        raise NotImplementedError("Subclasses must implement parse_jobs")
