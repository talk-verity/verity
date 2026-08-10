import logging
from typing import Sequence

from app.core.settings import settings

logger = logging.getLogger(__name__)


class Embedder:
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        raise NotImplementedError

    @property
    def dimension(self) -> int:
        raise NotImplementedError

    @property
    def is_available(self) -> bool:
        return False


class GeminiEmbedder(Embedder):
    MODEL = "models/gemini-embedding-001"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        client = self._get_client()
        try:
            result = client.models.embed_content(
                model=self.MODEL,
                contents=list(texts),
            )
            return [e.values for e in result.embeddings]
        except Exception as e:
            logger.warning("Gemini embedding failed: %s", e)
            raise

    @property
    def dimension(self) -> int:
        return 768

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)


class MockEmbedder(Embedder):
    def __init__(self, dimension: int = settings.EMBEDDING_DIMENSION):
        self._dimension = dimension

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        import random
        rng = random.Random(42)
        return [
            [rng.random() for _ in range(self._dimension)]
            for _ in texts
        ]

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def is_available(self) -> bool:
        return True


class LocalEmbedder(Embedder):
    def __init__(self, model_name: str = settings.EMBEDDING_MODEL):
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading local embedding model %s...", self.model_name)
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._get_model()
        vectors = model.encode(list(texts), normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    @property
    def dimension(self) -> int:
        return settings.EMBEDDING_DIMENSION

    @property
    def is_available(self) -> bool:
        return True


def create_embedder() -> Embedder:
    provider = settings.EMBEDDING_PROVIDER
    if provider == "gemini":
        return GeminiEmbedder()
    if provider == "mock":
        return MockEmbedder()
    logger.info("Using local embedder (%s)", settings.EMBEDDING_MODEL)
    return LocalEmbedder()
