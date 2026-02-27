"""
Concrete implementation of EmbeddingPort using OpenAI text-embedding-3-small.
"""

from openai import AsyncOpenAI

from app.ports.embedding_port import EmbeddingPort


class OpenAIEmbeddingAdapter(EmbeddingPort):
    """Generates 384-dimension embeddings via OpenAI's embedding API."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimensions: int = 384,
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._dimensions = dimensions

    async def encode(self, text: str) -> list[float]:
        """Encode text into a 384-d float vector."""

        # Truncate extremely long texts to stay within token limits
        truncated = text[:8000]

        response = await self._client.embeddings.create(
            input=truncated,
            model=self._model,
            dimensions=self._dimensions,
        )
        return response.data[0].embedding
