"""
Concrete implementation of DatabasePort using the Supabase Python client.
"""

from typing import Any

from supabase import Client

from app.ports.database_port import DatabasePort


class SupabaseAdapter(DatabasePort):
    """All database I/O goes through the Supabase REST client."""

    def __init__(self, client: Client) -> None:
        self._client = client

    # ── Users ─────────────────────────────────────────────────

    async def get_user(self, user_id: str) -> dict[str, Any] | None:
        result = (
            self._client.table("users")
            .select("*")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    async def upsert_user(self, user_id: str, data: dict[str, Any]) -> None:
        # Try update first (preserves existing columns like email)
        result = (
            self._client.table("users")
            .update(data)
            .eq("id", user_id)
            .execute()
        )
        # If no rows were updated, the user doesn't exist yet — insert
        if not result.data:
            data["id"] = user_id
            self._client.table("users").insert(data).execute()

    # ── Jobs ──────────────────────────────────────────────────

    async def create_job(self, data: dict[str, Any]) -> dict[str, Any]:
        result = self._client.table("jobs").insert(data).execute()
        return result.data[0]

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        result = (
            self._client.table("jobs")
            .select("*")
            .eq("id", job_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    async def update_job(self, job_id: str, data: dict[str, Any]) -> None:
        self._client.table("jobs").update(data).eq("id", job_id).execute()

    async def list_jobs_by_provider(self, provider_id: str) -> list[dict[str, Any]]:
        result = (
            self._client.table("jobs")
            .select("*")
            .eq("provider_id", provider_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    async def find_job_by_external_id(
        self, company_name: str, external_id: str
    ) -> dict[str, Any] | None:
        result = (
            self._client.table("jobs")
            .select("*")
            .eq("company_name", company_name)
            .eq("external_id", external_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    async def list_active_jobs(self, skip: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        # Only valid jobs = active status + not archived
        result = (
            self._client.table("jobs")
            .select("*")
            .eq("status", "active")
            # .filter("archived_at", "is", "null")
            .order("created_at", desc=True)
            .range(skip, skip + limit - 1)
            .execute()
        )
        return result.data or []

    async def get_all_jobs_for_analytics(self) -> list[dict[str, Any]]:
        """
        Fetches a lightweight subset of fields for ALL active jobs.
        Used for in-memory aggregation of market stats.
        """
        result = (
            self._client.table("jobs")
            .select("title, company_name, location, salary_range, skills_required, created_at")
            .eq("status", "active")
            # .filter("archived_at", "is", "null")
            .execute()
        )
        return result.data or []

    # ── Chat Sessions ─────────────────────────────────────────

    async def get_chat_session(self, session_id: str) -> dict[str, Any] | None:
        result = (
            self._client.table("chat_sessions")
            .select("*")
            .eq("id", session_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    async def update_chat_session(
        self, session_id: str, data: dict[str, Any]
    ) -> None:
        self._client.table("chat_sessions").update(data).eq("id", session_id).execute()



    async def get_all_chat_sessions(self) -> list[dict[str, Any]]:
        """Fetch all chat sessions for admin dashboard (bypasses RLS via service role)."""
        result = (
            self._client.table("chat_sessions")
            .select("id, created_at, status, user_id, users(id, email, full_name)")
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    async def list_user_sessions(self, user_id: str) -> list[dict[str, Any]]:
        """Fetch all chat sessions for a specific seeker, including job details."""
        # Using service role key bypasses RLS, so manually filter by user_id
        result = (
            self._client.table("chat_sessions")
            .select("id, created_at, status, job_id, jobs(title)")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    async def find_chat_session(self, user_id: str, job_id: str) -> dict[str, Any] | None:
        """Find an active chat session for a user and job."""
        # Check for non-closed sessions
        result = (
            self._client.table("chat_sessions")
            .select("*")
            .eq("user_id", user_id)
            .eq("job_id", job_id)
            .neq("status", "closed")
            .limit(1)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    async def create_chat_session(
        self, user_id: str, initial_log: list | None = None, job_id: str | None = None
    ) -> dict[str, Any]:
        insert_data = {"user_id": user_id}
        if initial_log is not None:
            insert_data["conversation_log"] = initial_log
        if job_id:
            insert_data["job_id"] = job_id
            
        result = (
            self._client.table("chat_sessions")
            .insert(insert_data)
            .execute()
        )
        return result.data[0]

    # ── Mock Interviews ───────────────────────────────────────

    async def create_mock_interview(self, data: dict[str, Any]) -> dict[str, Any]:
        result = self._client.table("mock_interviews").insert(data).execute()
        return result.data[0]

    async def get_mock_interview(self, interview_id: str) -> dict[str, Any] | None:
        result = (
            self._client.table("mock_interviews")
            .select("*")
            .eq("id", interview_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    async def update_mock_interview(self, interview_id: str, data: dict[str, Any]) -> None:
        self._client.table("mock_interviews").update(data).eq("id", interview_id).execute()

    async def list_user_mock_interviews(self, user_id: str) -> list[dict[str, Any]]:
        result = (
            self._client.table("mock_interviews")
            .select("*, jobs(title)")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    async def list_pending_reviews(self) -> list[dict[str, Any]]:
        result = (
            self._client.table("mock_interviews")
            .select("*, jobs(title), users(full_name, email)")
            .eq("status", "pending_review")
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    # ── Job Description Hash ───────────────────────────────────

    async def find_job_by_description_hash(
        self, description_hash: str
    ) -> dict[str, Any] | None:
        result = (
            self._client.table("jobs")
            .select("*")
            .eq("description_hash", description_hash)
            .not_.is_("embedding", "null")
            .limit(1)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    # ── Scraping Logs ──────────────────────────────────────────

    async def insert_scraping_log(self, data: dict[str, Any]) -> dict[str, Any]:
        result = self._client.table("scraping_logs").insert(data).execute()
        return result.data[0]

    async def update_scraping_log(
        self, log_id: str, data: dict[str, Any]
    ) -> None:
        self._client.table("scraping_logs").update(data).eq("id", log_id).execute()

    # ── Blog Posts ─────────────────────────────────────────────

    async def create_blog_post(self, data: dict[str, Any]) -> dict[str, Any]:
        result = self._client.table("blog_posts").insert(data).execute()
        return result.data[0]

    async def list_blog_posts(self, limit: int = 10) -> list[dict[str, Any]]:
        result = (
            self._client.table("blog_posts")
            .select("id, title, slug, summary, published_at, image_url")
            .order("published_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    async def get_blog_post(self, slug: str) -> dict[str, Any] | None:
        result = (
            self._client.table("blog_posts")
            .select("*")
            .eq("slug", slug)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    # ── Learning Resources ─────────────────────────────────────

    async def get_learning_resources(self, skills: list[str]) -> list[dict[str, Any]]:
        if not skills:
            return []
            
        result = (
            self._client.table("learning_resources")
            .select("*")
            .in_("skill_name", skills)
            .execute()
        )
        return result.data or []

