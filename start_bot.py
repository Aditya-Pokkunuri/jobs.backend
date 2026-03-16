import asyncio
import logging
from telegram.ext import ApplicationBuilder, CommandHandler # type: ignore
from app.config import settings # type: ignore
from app.dependencies import get_db, get_job_service # type: ignore
from app.services.telegram_service import TelegramService # type: ignore

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    if not settings.telegram_bot_token or settings.telegram_bot_token == "your_telegram_bot_token_here":
        logger.error("TELEGRAM_BOT_TOKEN not set in .env file!")
        return

    # Initialize dependencies manually
    db = get_db()
    job_service = get_job_service(db=db)
    telegram_service = TelegramService(job_service=job_service)

    # Build the application
    application = ApplicationBuilder().token(settings.telegram_bot_token).build()

    # Add command handlers
    start_handler = CommandHandler('start', telegram_service.start_command)
    jobs_handler = CommandHandler('jobs', telegram_service.jobs_command)
    help_handler = CommandHandler('help', telegram_service.help_command)

    application.add_handler(start_handler)
    application.add_handler(jobs_handler)
    application.add_handler(help_handler)

    logger.info("Starting Telegram bot: @jobs ottobon")
    # Run the bot in polling mode
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Keep the bot running
    while True:
        await asyncio.sleep(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
