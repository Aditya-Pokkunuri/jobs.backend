import logging
import datetime
from app.ports.ai_port import AIPort
from app.ports.database_port import DatabasePort
from app.services.market_news_service import MarketNewsService

logger = logging.getLogger(__name__)

class BlogAgent:
    def __init__(self, db: DatabasePort, ai: AIPort):
        self.db = db
        self.ai = ai
        self.news_service = MarketNewsService()

    async def generate_weekly_digest(self) -> dict:
        """
        Generates a blog post about this week's Big 4 market trends using Google News RSS.
        Returns the created blog post dict.
        """
        logger.info("BlogAgent: Starting weekly digest generation (Real-Time Mode)...")

        # 1. Fetch Real-Time News
        articles = self.news_service.fetch_big4_career_news(limit=5)
        
        if not articles:
            logger.warning("BlogAgent: No news found to analyze.")
            return None

        # Format articles for the prompt
        news_context = "\n\n".join([
            f"- Title: {a['title']}\n  Source: {a['source']}\n  Summary: {a['summary']}"
            for a in articles
        ])
        
        # 2. Construct Prompt (Student/Seeker Focused)
        week_str = datetime.datetime.now().strftime("%B %Y")
        prompt = (
            f"Act as a Career Strategist for university students aiming for jobs at the Big 4 (Deloitte, PwC, KPMG, EY). "
            f"Here are the latest news updates from {week_str}:\n\n"
            f"{news_context}\n\n"
            "Task: Write a high-value, actionable blog post for students.\n"
            "DO NOT just summarize the news. Translate every piece of news into a specific 'Student Action'.\n"
            "Example: If PwC invests in AI, tell students to build a specific AI project or get a cert.\n\n"
            "Structure:\n"
            "1. Title (Must be catchy, e.g., 'Big 4 Campus Watch: [Key Trend]')\n"
            "2. Executive Summary (2 sentences)\n"
            "3. The News & The Opportunity (For each key story, have a 'News Snapshot' and a '🎓 Student Takeaway')\n"
            "4. 🚀 Action Plan for this Week (3 bullet points)\n\n"
            "Output strictly valid JSON with keys: 'title', 'slug', 'summary', 'content' (markdown)."
        )

        # 3. Generate Content
        blog_data = await self.ai.generate_blog_post(prompt)
        
        # 4. Save to DB
        if blog_data:
            # Add image URL based on content or random
            blog_data['image_url'] = "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&q=80&w=2070" 
            post = await self.db.create_blog_post(blog_data)
            logger.info(f"BlogAgent: Published new post '{post['title']}'")
            return post
            
        return None
