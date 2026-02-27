import feedparser
import urllib.parse
from datetime import datetime
from typing import List, Dict

class MarketNewsService:
    """
    Ingests real-time market news for Big 4 companies with a focus on 
    Early Careers, Internships, and Campus Recruitment.
    """

    GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

    # Targeted Companies
    TARGET_COMPANIES = ["Deloitte", "PwC", "KPMG", "EY"]

    # Keywords for student relevance
    CAREER_KEYWORDS = [
        "intern", "internship", "graduate", "early career", 
        "campus", "hiring", "recruitment", "bootcamp", 
        "apprenticeship", "entry level", "university", 
        "scholarship", "hackathon", "innovation challenge"
    ]

    # Keywords to exclude
    EXCLUDE_KEYWORDS = [
        "stock", "share price", "dividend", "revenue", "quarterly result",
        "tax audit", "lawsuit", "scandal", "merger", "acquisition"
    ]

    def fetch_big4_career_news(self, limit: int = 5) -> List[Dict]:
        """
        Fetches, filters, and standardizes news items.
        Returns a list of dicts with title, link, published, summary, source.
        """
        # Construct Query: (Deloitte OR PwC ...) AND (intern OR graduate ...)
        companies_part = " OR ".join(self.TARGET_COMPANIES)
        keywords_part = " OR ".join([f'"{k}"' for k in self.CAREER_KEYWORDS])
        
        # URL encode the query
        raw_query = f"({companies_part}) AND ({keywords_part})"
        encoded_query = urllib.parse.quote(raw_query)
        
        feed_url = self.GOOGLE_NEWS_RSS_URL.format(query=encoded_query)
        
        print(f"Fetching RSS feed from: {feed_url}")
        feed = feedparser.parse(feed_url)
        
        if feed.bozo:
            print(f"Warning: Feed parsing error: {feed.bozo_exception}")

        articles = []
        seen_titles = set()

        for entry in feed.entries:
            title = entry.title
            link = entry.link
            summary = getattr(entry, "summary", "")
            published = getattr(entry, "published", str(datetime.now()))
            source = entry.source.title if hasattr(entry, "source") else "Google News"

            # Deduping
            if title in seen_titles:
                continue
            seen_titles.add(title)

            # Filtering
            if self._is_relevant(title, summary):
                articles.append({
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "published": published,
                    "source": source
                })

            if len(articles) >= limit:
                break
        
        return articles

    def _is_relevant(self, title: str, summary: str) -> bool:
        """
        Returns True if the article contains positive keywords and avoids negative ones.
        """
        text = (title + " " + summary).lower()

        # 1. Must mention at least one Big 4 company (sanity check)
        if not any(c.lower() in text for c in self.TARGET_COMPANIES):
            return False

        # 2. Must NOT contain exclude keywords
        if any(bad in text for bad in self.EXCLUDE_KEYWORDS):
            return False

        # 3. (Optional) Could enforce career keywords again, but the search query does that.
        # We trust the search query for inclusion, but double check here.
        if not any(k.lower() in text for k in self.CAREER_KEYWORDS):
            return False

        return True
