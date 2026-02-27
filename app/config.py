"""
Application configuration loaded from environment variables.
Uses pydantic-settings for typed, validated config.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All environment variables required by the application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Supabase ──────────────────────────────────────────────
    supabase_url: str
    supabase_key: str                # anon key (client-facing)
    supabase_service_role_key: str   # service role key (bypasses RLS)
    supabase_jwt_secret: str

    # ── OpenAI ────────────────────────────────────────────────
    openai_api_key: str

    # ── App ───────────────────────────────────────────────────
    app_name: str = "jobs.ottobon.cloud"
    debug: bool = False


# Singleton — import this wherever config is needed
settings = Settings()  # type: ignore[call-arg]
