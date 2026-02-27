"""PwC career page scraper (Workday JSON API)."""
import logging
import requests
from typing import Any
from app.scraper.scraper_port import ScraperPort
from app.scraper.experience_filter import is_entry_level

logger = logging.getLogger(__name__)


class PwCAdapter(ScraperPort):
    """Scrapes jobs from PwC via Workday JSON API (no browser needed)."""

    COMPANY_NAME = "PwC"
    # Workday external API endpoint
    API_URL = "https://pwc.wd3.myworkdayjobs.com/wday/cxs/pwc/Global_Experienced_Careers/jobs"
    BASE_URL = "https://pwc.wd3.myworkdayjobs.com/en-US/Global_Experienced_Careers"

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        """Fetches jobs directly from the Workday API — no Playwright needed."""
        logger.info(f"🕸️ Fetching {self.COMPANY_NAME} jobs from Workday API...")

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        all_jobs = []
        offset = 0
        limit = 20  # Workday default page size

        try:
            # Fetch up to 100 jobs (5 pages) but stop after 15 enriched entry-level jobs for speed
            desired_count = 7

            for page in range(5):
                if len(all_jobs) >= desired_count:
                    break

                payload = {
                    "appliedFacets": {},
                    "limit": limit,
                    "offset": offset,
                    "searchText": "",
                }

                resp = requests.post(self.API_URL, json=payload, headers=headers, timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"⚠️ PwC API returned {resp.status_code}")
                    break

                data = resp.json()
                job_postings = data.get("jobPostings", [])

                if not job_postings:
                    break

                for job in job_postings:
                    if len(all_jobs) >= desired_count:
                        break

                    title = job.get("title", "")
                    ext_path = job.get("externalPath", "")
                    location = job.get("locationsText", "India")
                    posted = job.get("postedOn", "")
                    bullet_fields = job.get("bulletFields", [])

                    # ID for detail fetch: "job/..." -> "job/..." (slug)
                    slug = ext_path.split("/")[-1] if ext_path else "" 
                    if not slug:
                        continue

                    job_req_id = job.get("bulletFields", [""])[0] # Often the first bullet is the ID e.g. "366367WD"

                    full_url = f"{self.BASE_URL}{ext_path}"
                    external_id = slug

                    # Check entry level
                    experience_text = " ".join(bullet_fields) if bullet_fields else ""
                    if not is_entry_level(title, experience_text):
                         continue

                    # --- Fetch Full Description ---
                    # Detail API: https://pwc.wd3.myworkdayjobs.com/wday/cxs/pwc/Global_Experienced_Careers/job/{slug}
                    detail_url = f"https://pwc.wd3.myworkdayjobs.com/wday/cxs/pwc/Global_Experienced_Careers/job/{slug}"
                    
                    try:
                        desc_resp = requests.get(detail_url, headers=headers, timeout=10)
                        if desc_resp.status_code == 200:
                            desc_data = desc_resp.json()
                            description = desc_data.get("jobPostingInfo", {}).get("jobDescription", "")
                            # If we got a real description, use it (it's HTML, but AI handles HTML fine)
                            # If empty, fallback to summary
                            description_raw = description if description else f"Posted: {posted}. {' | '.join(bullet_fields)}"
                        else:
                             description_raw = f"Posted: {posted}. {' | '.join(bullet_fields)}"
                    except Exception:
                        description_raw = f"Posted: {posted}. {' | '.join(bullet_fields)}"

                    all_jobs.append({
                        "external_id": external_id,
                        "title": self._clean_title(title),
                        "company_name": self.COMPANY_NAME,
                        "external_apply_url": full_url,
                        "description_raw": description_raw,
                        "skills_required": [],
                        "location": location,
                        "salary_range": None,
                    })

                offset += limit
                logger.info(f"  ↳ Page {page+1}: fetched {len(job_postings)} postings, {len(all_jobs)} entry-level so far")

            logger.info(f"  ✅ PwC: Total {len(all_jobs)} entry-level jobs with full details")
            return all_jobs

        except Exception as e:
            logger.error(f"❌ Failed to fetch PwC jobs: {e}")
            return []

    @staticmethod
    def _clean_title(raw: str) -> str:
        """
        Convert slug-format titles like
        'IN_ASSOCIATE_JAVA_DEVELOPER_DATA_&_ANALYTICS_ADVISORY_KOLKATA'
        into readable titles like
        'Associate Java Developer - Data & Analytics Advisory'.
        """
        import re
        # Strip leading country code prefix (e.g. "IN_", "US_")
        cleaned = re.sub(r'^[A-Z]{2}_', '', raw)
        # Strip trailing city name (uppercase word at end after last underscore block)
        # Common Indian cities
        cities = ['KOLKATA', 'MUMBAI', 'DELHI', 'BANGALORE', 'BENGALURU', 'HYDERABAD',
                  'CHENNAI', 'PUNE', 'GURGAON', 'GURUGRAM', 'NOIDA', 'AHMEDABAD', 'KOCHI',
                  'JAIPUR', 'LUCKNOW', 'CHANDIGARH', 'INDORE', 'BHOPAL', 'NEW DELHI']
        for city in cities:
            if cleaned.upper().endswith('_' + city.replace(' ', '_')):
                cleaned = cleaned[:-(len(city) + 1)]
                break
        # Replace underscores with spaces
        cleaned = cleaned.replace('_', ' ')
        # Title case
        cleaned = cleaned.title()
        # Fix common abbreviations
        cleaned = cleaned.replace(' & ', ' & ')
        return cleaned.strip()
