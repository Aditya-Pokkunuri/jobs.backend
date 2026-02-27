# Scraper Implementation Guide

This document details the architecture and usage of the scraping system implemented for the Big 4 job ingestion pipeline.

## Architecture

The system uses a **Hybrid Scraping Approach**:
1.  **Rendering**: `crawl4ai` (wrapping Playwright) handles JavaScript resizing and loads dynamic content.
2.  **Parsing**: `BeautifulSoup` parses the rendered HTML for job cards.
3.  **Filtering**: A dedicated `experience_filter.py` module filters jobs for 0-2 years of experience.
4.  **Scheduling**: `APScheduler` runs the ingestion daily at 10:00 PM IST.

### Component Diagram

```mermaid
graph TD
    Scheduler[APScheduler (Daily 10 PM)] -->|Trigger| IngestionService
    AdminAPI[POST /admin/ingest/all] -->|Trigger| IngestionService
    IngestionService -->|Iterate| Scrapers{Scraper Registry}
    Scrapers -->|Fetch| Deloitte[DeloitteAdapter]
    Scrapers -->|Fetch| PwC[PwCAdapter]
    Scrapers -->|Fetch| KPMG[KPMGAdapter]
    Scrapers -->|Fetch| EY[EYAdapter]
    
    subgraph "BaseScraper"
        Deloitte -->|Inherits| Base[base_scraper.py]
        Base -->|Render| Crawl4AI[crawl4ai / Playwright]
        Base -->|Parse| BS4[BeautifulSoup]
        Base -->|Filter| ExpFilter[experience_filter.py]
    end
```

## Scheduler Configuration

The scheduler is initialized in `app.scheduler.py` and started via `main.py` lifespan events.

- **Timezone**: Asia/Kolkata
- **Schedule**: Every day at 22:00 (10:00 PM)
- **Job ID**: `daily_ingestion`

## Adding New Scrapers

1.  Create a new adapter in `app/scraper/` (e.g., `accenture_adapter.py`).
2.  Inherit from `BaseScraper`.
3.  Define `COMPANY_NAME` and `CAREER_PAGE_URL`.
4.  Implement `parse_jobs(self, soup)` to return a list of dicts with `external_id`, `title`, and `external_apply_url`.
5.  Register the adapter in `app/dependencies.py` inside `_SCRAPER_REGISTRY`.

## Manual Trigger

You can manually trigger the ingestion process for all sources via the admin API:

```bash
curl -X POST "http://localhost:8000/admin/ingest/all" \
     -H "Authorization: Bearer <ADMIN_TOKEN>"
```

## Troubleshooting

- **Browser Issues**: If `crawl4ai` fails to launch, ensure playwright browsers are installed: `playwright install`.
- **Selectors Changing**: Career pages change often. Update the CSS selectors in the specific adapter file (e.g., `deloitte_adapter.py`).
