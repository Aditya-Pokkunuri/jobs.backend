from abc import ABC, abstractmethod
from typing import Any, List

class ChatPort(ABC):
    @abstractmethod
    async def get_chat_session(self, session_id: str) -> dict[str, Any] | None:
        """Fetch a chat session by ID."""
        pass

    @abstractmethod
    async def update_chat_session(self, session_id: str, data: dict[str, Any]) -> None:
        """Update a chat session (status, conversation_log, etc.)."""
        pass

    @abstractmethod
    async def get_all_chat_sessions(self) -> list[dict[str, Any]]:
        """Fetch all chat sessions."""
        pass
    
    @abstractmethod
    async def list_user_sessions(self, user_id: str) -> list[dict[str, Any]]:
        """List all chat sessions for a given user."""
        pass

    @abstractmethod
    async def find_chat_session(self, user_id: str, job_id: str) -> dict[str, Any] | None:
        """Find a chat session by user ID and job ID."""
        pass

    @abstractmethod
    async def create_chat_session(
        self, user_id: str, initial_log: list | None = None, job_id: str | None = None
    ) -> dict[str, Any]:
        """Create a new chat session for a user, optionally with initial context and associated job."""
        pass
