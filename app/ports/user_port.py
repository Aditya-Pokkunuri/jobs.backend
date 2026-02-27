from abc import ABC, abstractmethod
from typing import Any

class UserPort(ABC):
    @abstractmethod
    async def get_user(self, user_id: str) -> dict[str, Any] | None:
        """Fetch a single user by ID."""
        ...

    @abstractmethod
    async def upsert_user(self, user_id: str, data: dict[str, Any]) -> None:
        """Create or update a user record."""
        ...
