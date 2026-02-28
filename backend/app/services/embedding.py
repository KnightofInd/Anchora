"""

Embedding Service
-----------------
Generates vector embeddings using Gemini text-embedding-004.
Embeddings are stored in the pgvector column on the documents table.
Used for semantic search and source-linked explainability.
"""

import asyncio
import functools
import logging

from google import genai  # type: ignore[import]
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Lazy-initialized — deferred until first call so the server can start
# even when GEMINI_API_KEY is not yet configured.
_client: "genai.Client | None" = None


def _get_client() -> "genai.Client":
    global _client
    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Add it to backend/.env to enable knowledge embeddings."
            )
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


class EmbeddingService:
    # Only model available on this API key; supports configurable output dims
    MODEL = "gemini-embedding-001"

    def _sync_generate(self, text: str) -> list[float]:
        result = _get_client().models.embed_content(
            model=self.MODEL,
            contents=text,
            config={"output_dimensionality": 768},
        )
        embeddings = result.embeddings
        if not embeddings:
            raise ValueError("Gemini returned no embeddings for the given text.")
        values = embeddings[0].values
        if values is None:
            raise ValueError("Gemini embedding values were None.")
        return list(values)

    async def generate(self, text: str) -> list[float]:
        """
        Generates a 768-dimension embedding vector for the given text.
        Runs the blocking Gemini SDK call in a thread pool to avoid blocking
        the FastAPI event loop.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            functools.partial(self._sync_generate, text),
        )
