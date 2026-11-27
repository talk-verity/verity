import logging
from typing import Any

from app.core.settings import settings

logger = logging.getLogger(__name__)


class PineconeClient:
    INDEX_NAME = "delphi"

    def __init__(self, api_key: str | None = None, environment: str | None = None):
        self.api_key = api_key or settings.PINECONE_API_KEY
        self.environment = environment or settings.PINECONE_ENVIRONMENT
        self._index = None

    def _connect(self):
        if self._index is not None:
            return
        if not self.api_key:
            raise RuntimeError("Pinecone API key not configured")
        from pinecone import Pinecone, ServerlessSpec
        pc = Pinecone(api_key=self.api_key)
        existing = [i.name for i in pc.list_indexes()]
        if self.INDEX_NAME not in existing:
            logger.warning("Index '%s' does not exist — creating", self.INDEX_NAME)
            pc.create_index(
                name=self.INDEX_NAME,
                dimension=settings.EMBEDDING_DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region=self.environment),
            )
        self._index = pc.Index(self.INDEX_NAME)

    def upsert(self, vectors: list[dict[str, Any]], batch_size: int = 100) -> int:
        self._connect()
        total = 0
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self._index.upsert(vectors=batch)
            total += len(batch)
        return total

    def query(self, vector: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        self._connect()
        result = self._index.query(
            top_k=top_k,
            vector=vector,
            include_metadata=True,
        )
        return [
            {
                "id": m.id,
                "score": m.score,
                "metadata": m.metadata or {},
                "text": (m.metadata or {}).get("text", ""),
            }
            for m in result.matches
        ]

    def delete(self, ids: list[str] | None = None, namespace: str | None = None, delete_all: bool = False):
        self._connect()
        self._index.delete(ids=ids, namespace=namespace or "", delete_all=delete_all)

    def describe_index(self) -> dict:
        self._connect()
        stats = self._index.describe_index_stats()
        return {"total_vector_count": stats.total_vector_count}

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)


class MockPineconeClient:
    INDEX_NAME = "delphi"

    def __init__(self):
        self._vectors: list[dict[str, Any]] = []

    def _cosine_sim(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        if not na or not nb:
            return 0.0
        return dot / (na * nb)

    def upsert(self, vectors: list[dict[str, Any]]) -> int:
        count = 0
        for v in vectors:
            existing = [x for x in self._vectors if x["id"] == v["id"]]
            if existing:
                self._vectors.remove(existing[0])
            self._vectors.append(v)
            count += 1
        return count

    def query(self, vector: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        scored = []
        for v in self._vectors:
            sim = self._cosine_sim(vector, v["values"])
            scored.append({
                "id": v["id"],
                "score": sim,
                "metadata": v.get("metadata", {}),
                "text": v.get("metadata", {}).get("text", ""),
            })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def delete(self, ids: list[str] | None = None, namespace: str | None = None, delete_all: bool = False):
        if delete_all:
            self._vectors.clear()
        elif ids:
            self._vectors = [v for v in self._vectors if v["id"] not in ids]

    def describe_index(self) -> dict:
        return {"total_vector_count": len(self._vectors)}

    @property
    def is_available(self) -> bool:
        return True


def create_pinecone_client() -> PineconeClient | MockPineconeClient:
    if settings.PINECONE_API_KEY:
        return PineconeClient()
    logger.warning("No PINECONE_API_KEY set — using MockPineconeClient")
    return MockPineconeClient()
