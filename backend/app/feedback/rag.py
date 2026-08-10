import logging

from app.conversations.scenarios import get_scenario
from app.embeddings.service import EmbeddingService

logger = logging.getLogger(__name__)

SCENARIO_SOURCES = {
    "networking_event": ["networking"],
    "performance_review": ["performance review", "manager handbook", "feedback"],
    "promotion_discussion": ["promotion", "raise", "negotiate"],
    "job_interview": ["interview", "star", "questions", "negotiating"],
    "workplace_conflict": ["conflict", "feedback", "manager handbook"],
}


class RAGService:
    def __init__(self, embedding_service: EmbeddingService | None = None):
        self.embedding_service = embedding_service or EmbeddingService()

    def retrieve_context(self, scenario_id: str, transcript: str, top_k: int = 5) -> str:
        if not self.embedding_service.is_available:
            logger.warning("EmbeddingService not available — skipping RAG")
            return ""
        scenario = get_scenario(scenario_id) or {}
        query = self._build_query(scenario, transcript)
        results = self.embedding_service.query(query, top_k=max(top_k * 2, 8))
        results = self._prioritize(results, scenario_id)[:top_k]
        if not results:
            return ""
        return "\n\n---\n\n".join(
            f"[Source: {r.get('metadata', {}).get('source', 'unknown')}]\n{r.get('text', '')}"
            for r in results
        )

    def retrieve_chunks(self, query: str, top_k: int = 5, scenario_id: str | None = None) -> list[dict]:
        if not self.embedding_service.is_available:
            return []
        results = self.embedding_service.query(query, top_k=top_k)
        if scenario_id:
            results = self._prioritize(results, scenario_id)
        return [
            {
                "source": r.get("metadata", {}).get("source", "unknown"),
                "text": r.get("text", ""),
                "score": r.get("score", 0.0),
            }
            for r in results
        ]

    def _build_query(self, scenario: dict, transcript: str) -> str:
        parts = [scenario.get("name", ""), scenario.get("goal", ""), scenario.get("context", "")]
        query = " ".join(p for p in parts if p).strip()
        tail = (transcript or "").strip()
        if query and tail:
            return f"{query}\n{tail[:1500]}"
        return query or tail or "communication best practices"

    def _prioritize(self, results: list[dict], scenario_id: str) -> list[dict]:
        keywords = SCENARIO_SOURCES.get(scenario_id, [])
        if not keywords:
            return results

        def key(r: dict) -> tuple[bool, float]:
            source = (r.get("metadata", {}).get("source", "") or "").lower()
            matched = any(k in source for k in keywords)
            return (matched, r.get("score", 0.0))

        return sorted(results, key=key, reverse=True)
