import logging
import re
from typing import Any
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler
from app.scraper.base_scraper import BaseScraper
from app.scraper.experience_filter import is_entry_level

logger = logging.getLogger(__name__)


class EYAdapter(BaseScraper):
    """Scrapes jobs from EY's career page (PhenomPeople platform)."""

    COMPANY_NAME = "EY"
    # EY global search filtered for India
    CAREER_PAGE_URL = "https://careers.ey.com/ey/search/?createNewAlert=false&q=&locationsearch=India&optionsFacetsDD_country=IN"

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        """Fetches jobs + details using crawl4ai."""
        logger.info(f"🕸️ Scraping {self.COMPANY_NAME} from {self.CAREER_PAGE_URL}...")
        
        try:
            async with AsyncWebCrawler(verbose=True) as crawler:
                # 1. Fetch Search Page
                result = await crawler.arun(url=self.CAREER_PAGE_URL)
                if not result.html:
                    return []

                soup = BeautifulSoup(result.html, "html.parser")
                raw_jobs = self.parse_jobs(soup)
                logger.info(f"  ↳ Found {len(raw_jobs)} raw jobs (fetching details for top 15)")

                valid_jobs = []
                count = 0
                
                for job in raw_jobs:
                    if count >= 7:
                        break

                    # Check entry level logic (title-based)
                    if not is_entry_level(job["title"], ""):
                        continue

                    # 2. Fetch Detail Page
                    job_url = job["external_apply_url"]
                    try:
                        # logger.info(f"    Fetching details: {job['title'][:30]}")
                        # Wait for the description container to appear
                        detail_res = await crawler.arun(url=job_url, wait_for="css:span[itemprop='description']")
                        
                        if detail_res.html:
                            d_soup = BeautifulSoup(detail_res.html, "html.parser")
                            # Selectors for PhenomPeople
                            # 1. High precision: Semantic schema tag
                            desc_tag = d_soup.select_one("span[itemprop='description']")
                            
                            # 2. Fallbacks
                            if not desc_tag:
                                 desc_tag = (d_soup.select_one(".job-description") 
                                            or d_soup.select_one(".job-details-content")
                                            or d_soup.select_one(".description")
                                            or d_soup.select_one("#job-description")
                                            or d_soup.select_one("div.job-overview"))

                            if desc_tag:
                                # Clean junk
                                for tag in desc_tag(["script", "style", "iframe", "noscript"]):
                                    tag.decompose()
                                job["description_raw"] = str(desc_tag)
                            else:
                                logger.warning(f"   ⚠️ Desc selectors failed for {job['title']}. USING RAW BODY TEXT.")
                                # Fallback: Get full text, remove huge empty spaces
                                raw_text = d_soup.body.get_text(separator="\n", strip=True)
                                # Limit to first 5000 chars to avoid token limits, but keep enough
                                job["description_raw"] = "RAW_DUMP: " + raw_text[:5000]
                        else:
                            job["description_raw"] = "Posted: Check official site."

                    except Exception as e:
                        logger.warning(f"    Failed detail fetch for {job['title']}: {e}")
                        job["description_raw"] = "Posted: Check official site."

                    normalized = {
                        "external_id": job["external_id"],
                        "title": job["title"],
                        "company_name": self.COMPANY_NAME,
                        "external_apply_url": job["external_apply_url"],
                        "description_raw": job["description_raw"],
                        "skills_required": [],
                        "location": job["location"],
                        "salary_range": None,
                    }
                    
                    valid_jobs.append(normalized)
                    count += 1

                logger.info(f"  ✅ EY: Total {len(valid_jobs)} enriched-ready jobs")
                return valid_jobs

        except Exception as e:
            logger.error(f"❌ Failed to scrape {self.COMPANY_NAME}: {e}")
            return []

    def parse_jobs(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """
        EY uses PhenomPeople platform. Job links follow the pattern:
        /ey/job/<slug>/<job-id>
        """
        results = []
        seen_ids = set()

        # Find all links that match EY job URL pattern
        all_links = soup.find_all("a", href=True)

        for a in all_links:
            href = a.get("href", "")
            text = a.get_text(strip=True)

            # Match EY job detail links: /ey/job/<slug>/<id>
            # or full URLs like https://careers.ey.com/ey/job/<slug>/<id>
            match = re.search(r'/ey/job/([^/]+)/(\d+)', href)
            if not match:
                continue

            slug = match.group(1)
            job_id = match.group(2)

            # Deduplicate
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            # Title from link text, or derive from slug
            title = text if len(text) > 3 else slug.replace("-", " ").title()

            # Build full URL
            if href.startswith("http"):
                full_url = href
            else:
                full_url = f"https://careers.ey.com{href}"

            # Try to extract location from surrounding context
            location = "India"  # Default since we filter for India
            parent = a.parent
            if parent:
                parent_text = parent.get_text(" ", strip=True)
                for city in ["Bangalore", "Bengaluru", "Mumbai", "Delhi", "Gurgaon", "Gurugram",
                             "Hyderabad", "Chennai", "Kolkata", "Pune", "Noida", "Kochi", "Ahmedabad"]:
                    if city.lower() in parent_text.lower():
                        location = f"{city}, India"
                        break

            results.append({
                "external_id": job_id,
                "title": title,
                "external_apply_url": full_url,
                "location": location,
                # description_raw filled later
            })

        return results
