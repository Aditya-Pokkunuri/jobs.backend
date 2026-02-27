from abc import ABC, abstractmethod
from typing import Any, List

class BlogPort(ABC):
    @abstractmethod
    async def create_blog_post(self, data: dict[str, Any]) -> dict[str, Any]:
        pass

    @abstractmethod
    async def list_blog_posts(self, limit: int = 10) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def get_blog_post(self, slug: str) -> dict[str, Any] | None:
        pass
