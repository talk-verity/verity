import logging
from typing import Sequence

from app.embeddings.embedder import Embedder, create_embedder
from app.embeddings.pinecone import PineconeClient, MockPineconeClient, create_pinecone_client

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(
        self,
        embedder: Embedder | None = None,
        vector_db: PineconeClient | MockPineconeClient | None = None,
    ):
        self.embedder = embedder or create_embedder()
        self.vector_db = vector_db or create_pinecone_client()

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return self.embedder.embed(texts)

    def index_chunks(self, chunks: list[dict], namespace: str = "default") -> int:
        texts = [c["text"] for c in chunks]
        vectors = self.embed_texts(texts)
        pinecone_vectors = []
        for chunk, vec in zip(chunks, vectors):
            pinecone_vectors.append({
                "id": chunk["id"],
                "values": vec,
                "metadata": {
                    "text": chunk["text"],
                    "source": chunk.get("source", ""),
                    "page": chunk.get("page", 0),
                    "namespace": namespace,
                },
            })
        return self.vector_db.upsert(pinecone_vectors)

    def query(self, text: str, top_k: int = 5) -> list[dict]:
        vector = self.embed_texts([text])[0]
        return self.vector_db.query(vector, top_k=top_k)

    def retrieve_context(self, transcript: str, top_k: int = 5) -> str:
        try:
            results = self.query(transcript, top_k=top_k)
            if not results:
                return ""
            chunks = []
            for r in results:
                source = r.get("metadata", {}).get("source", "unknown")
                text = r.get("text", "")
                chunks.append(f"[Source: {source}]\n{text}")
            return "\n\n---\n\n".join(chunks)
        except Exception as e:
            logger.warning("RAG retrieval failed: %s", e)
            return ""

    def delete_all(self, namespace: str | None = None):
        self.vector_db.delete(delete_all=True, namespace=namespace)

    @property
    def is_available(self) -> bool:
        return self.embedder.is_available and self.vector_db.is_available
