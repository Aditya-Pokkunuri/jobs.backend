import logging
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot  # type: ignore
from telegram.ext import ContextTypes  # type: ignore
from app.services.job_service import JobService  # type: ignore
from app.config import settings  # type: ignore

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self, job_service: JobService):
        self._job_service = job_service

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a welcome message with a link to the website."""
        welcome_text = (
            "🚀 <b>Welcome to @jobs ottobon!</b>\n\n"
            "I'm your assistant for finding the best entry-level jobs curated from top companies.\n\n"
            "Click the button below to see all active job listings on our website."
        )
        
        keyboard = [
            [InlineKeyboardButton("🌐 View All Jobs", url=f"{settings.frontend_url}/jobs")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')

    async def jobs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Fetch latest jobs and display them in Telegram."""
        try:
            # Fetch latest 5 active jobs
            jobs = await self._job_service.list_feed(skip=0, limit=5)
            
            if not jobs:
                await update.message.reply_text("🔍 No active jobs found at the moment. Check back later!")
                return

            for job in jobs:
                job_id = job.get('id') or job.get('external_id')
                title = job.get('title', 'N/A')
                company = job.get('company_name', 'N/A')
                location = job.get('location') or "India"
                salary = job.get('salary_range') or "Expected Best in Industry"
                qualification = job.get('qualification') or "Any Graduate"
                experience = job.get('experience') or "Freshers/Experienced"
                
                # Format to match the user's reference image
                job_text = (
                    f"<b>{html.escape(company)} is Hiring</b>\n\n"
                    f"Role: {html.escape(title)}\n"
                    f"Qualification: {html.escape(qualification)}\n"
                    f"Experience: {html.escape(experience)}\n"
                    f"Salary: {html.escape(salary)}\n"
                    f"Location: {html.escape(location)}\n\n"
                    f"📌 <b>Apply Now:</b> {settings.frontend_url}/jobs/{job_id}\n\n"
                    f"Join Our WhatsApp: {settings.whatsapp_channel_url}\n"
                    f"Join Our Telegram: {settings.telegram_channel_url}"
                )
                
                # Use a cleaner Button labeled "Apply Now"
                keyboard = [
                    [InlineKeyboardButton("🚀 Apply Now", url=f"{settings.frontend_url}/jobs/{job_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(job_text, reply_markup=reply_markup, parse_mode='HTML', disable_web_page_preview=True)
                
        except Exception as e:
            logger.error(f"Error in jobs_command: {e}")
            await update.message.reply_text("❌ Oops! Something went wrong while fetching jobs.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a list of available commands."""
        help_text = (
            "🤖 <b>Available Commands:</b>\n\n"
            "/start - Welcome and link to website\n"
            "/jobs - Show latest 5 job listings\n"
            "/help - Show this help message"
        )
        await update.message.reply_text(help_text, parse_mode='HTML')

    async def send_job_to_channel(self, job_data: dict):
        """Send a newly ingested job to the Telegram channel."""
        if not settings.telegram_bot_token or not settings.telegram_channel_id:
            logger.warning("Telegram bot token or channel ID not set. Skipping channel post.")
            return

        try:
            bot = Bot(token=settings.telegram_bot_token)
            
            job_id = job_data.get('id')
            title = job_data.get('title', 'N/A')
            company = job_data.get('company_name', 'N/A')
            location = job_data.get('location') or "India"
            salary = job_data.get('salary_range') or "Expected Best in Industry"
            qualification = job_data.get('qualification') or "Any Graduate"
            experience = job_data.get('experience') or "Freshers/Experienced"
            
            # Format according to user's desired template
            job_text = (
                f"<b>{html.escape(company)} is Hiring</b>\n\n"
                f"Role: {html.escape(title)}\n"
                f"Qualification: {html.escape(qualification)}\n"
                f"Experience: {html.escape(experience)}\n"
                f"Salary: {html.escape(salary)}\n"
                f"Location: {html.escape(location)}\n\n"
                f"📌 <b>Apply Now:</b> {settings.frontend_url}/jobs/{job_id}\n\n"
                f"Join Our Telegram: {settings.telegram_channel_url}"
            )
            
            keyboard = [
                [InlineKeyboardButton("🚀 Apply Now", url=f"{settings.frontend_url}/jobs/{job_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await bot.send_message(
                chat_id=settings.telegram_channel_id,
                text=job_text,
                reply_markup=reply_markup,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            logger.info(f"Successfully posted job {job_id} to Telegram channel.")
            
        except Exception as e:
            logger.error(f"Failed to post job to Telegram channel: {e}")
