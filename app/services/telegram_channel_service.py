"""
Telegram Channel Broadcast Service.

One-way push: formats each ingested job as a rich HTML message and
sends it to the configured Telegram channel.  If the bot token or
channel ID is not set, the service is silently disabled.
"""

import logging
from html import escape

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup  # type: ignore

from app.config import settings  # type: ignore

logger = logging.getLogger(__name__)


class TelegramChannelService:
    """Broadcasts job postings to a Telegram channel."""

    def __init__(self) -> None:
        self._token = settings.telegram_bot_token
        self._channel = settings.telegram_channel_id
        self._frontend_url = settings.frontend_url.rstrip("/")
        self._enabled = bool(self._token and self._channel)

        if not self._enabled:
            logger.info(
                "TelegramChannelService disabled — "
                "TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID not set."
            )

    # ── Public API ────────────────────────────────────────────

    async def post_job(self, job: dict) -> bool:
        """
        Format and send a single job card to the Telegram channel.

        Returns True on success, False if disabled or on error.
        Never raises — failures are logged and swallowed so that
        the ingestion pipeline is never interrupted.
        """
        if not self._enabled:
            return False

        try:
            job_id = job.get("id", "")
            apply_url = f"{self._frontend_url}/jobs/{job_id}"
            text = self._format_message(job)

            # Clickable "Apply Now" button below the message
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("👉 Apply on JobsOttobon", url=apply_url)]
            ])

            bot = Bot(token=self._token)
            await bot.send_message(
                chat_id=self._channel,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=keyboard,
            )
            logger.info(
                "Posted to Telegram channel: %s — %s",
                job.get("company_name"),
                job.get("title"),
            )
            return True
        except Exception as exc:
            logger.warning(
                "Failed to post job %s to Telegram: %s",
                job.get("id", "?"),
                exc,
            )
            return False

    # ── Internals ─────────────────────────────────────────────

    def _format_message(self, job: dict) -> str:
        """Build a rich HTML message for the Telegram channel."""
        company = escape(job.get("company_name") or "Unknown Company")
        title = escape(job.get("title") or "Untitled Position")
        location = escape(job.get("location") or "India")
        skills = job.get("skills_required") or []
        experience = job.get("experience") or None
        qualification = job.get("qualification") or None
        salary = job.get("salary_range") or None

        lines = [
            f"🏢 <b>{company}</b>",
            f"💼 <b>{title}</b>",
            f"📍 {location}",
        ]

        if experience:
            lines.append(f"🎓 Experience: {escape(experience)}")

        if qualification:
            lines.append(f"📜 Qualification: {escape(qualification)}")

        if salary:
            lines.append(f"💰 Salary: {escape(salary)}")

        if skills:
            skills_text = ", ".join(escape(s) for s in skills[:10])
            lines.append(f"🔗 Skills: {skills_text}")

        return "\n".join(lines)
