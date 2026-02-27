"""
Abstract interface for text → vector embedding.
"""

from abc import ABC, abstractmethod


class EmbeddingPort(ABC):
    """Port for generating vector embeddings from text."""

    @abstractmethod
    async def encode(self, text: str) -> list[float]:
        """
        Convert text into a fixed-dimension float vector.
        Expected output dimension: 384.
        """
        ...
