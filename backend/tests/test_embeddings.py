import pytest

from app.embeddings.embedder import MockEmbedder, GeminiEmbedder, create_embedder
from app.embeddings.pinecone import MockPineconeClient, PineconeClient, create_pinecone_client
from app.embeddings.service import EmbeddingService
from app.feedback.rag import RAGService


class TestMockEmbedder:
    @pytest.fixture
    def embedder(self):
        return MockEmbedder(dimension=4)

    def test_embed_returns_vectors(self, embedder):
        result = embedder.embed(["hello world", "test"])
        assert len(result) == 2
        assert len(result[0]) == 4
        assert len(result[1]) == 4

    def test_embed_deterministic(self, embedder):
        a = embedder.embed(["fixed text"])
        b = embedder.embed(["fixed text"])
        assert a == b

    def test_dimension(self, embedder):
        assert embedder.dimension == 4

    def test_is_available(self, embedder):
        assert embedder.is_available is True


class TestMockPineconeClient:
    @pytest.fixture
    def pc(self):
        return MockPineconeClient()

    def test_upsert_and_query(self, pc):
        pc.upsert([
            {"id": "1", "values": [1.0, 0.0, 0.0, 0.0], "metadata": {"text": "hello"}},
            {"id": "2", "values": [0.0, 1.0, 0.0, 0.0], "metadata": {"text": "world"}},
        ])
        results = pc.query([1.0, 0.0, 0.0, 0.0], top_k=2)
        assert len(results) == 2
        assert results[0]["id"] == "1"
        assert results[0]["score"] > results[1]["score"]

    def test_delete_all(self, pc):
        pc.upsert([{"id": "1", "values": [1.0, 0.0, 0.0, 0.0], "metadata": {"text": "a"}}])
        pc.delete(delete_all=True)
        assert pc.describe_index()["total_vector_count"] == 0

    def test_delete_by_ids(self, pc):
        pc.upsert([
            {"id": "1", "values": [1.0, 0.0, 0.0, 0.0], "metadata": {"text": "a"}},
            {"id": "2", "values": [1.0, 0.0, 0.0, 0.0], "metadata": {"text": "b"}},
        ])
        pc.delete(ids=["1"])
        results = pc.query([1.0, 0.0, 0.0, 0.0], top_k=5)
        assert len(results) == 1
        assert results[0]["id"] == "2"

    def test_query_empty(self, pc):
        results = pc.query([1.0, 0.0, 0.0, 0.0])
        assert results == []

    def test_cosine_similarity(self, pc):
        pc.upsert([{"id": "same", "values": [1.0, 0.0, 0.0, 0.0], "metadata": {"text": "x"}}])
        results = pc.query([1.0, 0.0, 0.0, 0.0], top_k=1)
        assert results[0]["score"] == pytest.approx(1.0, abs=1e-6)

    def test_describe_index(self, pc):
        pc.upsert([{"id": "x", "values": [1.0, 0.0, 0.0, 0.0], "metadata": {"text": "x"}}])
        stats = pc.describe_index()
        assert stats["total_vector_count"] == 1


class TestEmbeddingService:
    @pytest.fixture
    def service(self):
        embedder = MockEmbedder(dimension=4)
        vector_db = MockPineconeClient()
        return EmbeddingService(embedder=embedder, vector_db=vector_db)

    def test_embed_texts(self, service):
        vectors = service.embed_texts(["hello", "world"])
        assert len(vectors) == 2
        assert len(vectors[0]) == 4

    def test_index_and_query_roundtrip(self, service):
        chunks = [
            {"id": "c1", "text": "Active listening improves workplace communication", "source": "test.pdf", "page": 1},
            {"id": "c2", "text": "Clear feedback helps teams grow", "source": "test.pdf", "page": 2},
        ]
        count = service.index_chunks(chunks, namespace="test")
        assert count == 2

        results = service.query("active listening in workplace", top_k=2)
        assert len(results) == 2

    def test_retrieve_context_returns_string(self, service):
        chunks = [
            {"id": "c1", "text": "Research shows structured feedback improves outcomes", "source": "paper.pdf", "page": 1},
        ]
        service.index_chunks(chunks)
        context = service.retrieve_context("feedback in workplace", top_k=1)
        assert isinstance(context, str)
        assert "Research shows" in context
        assert "paper.pdf" in context

    def test_retrieve_context_empty_when_no_data(self, service):
        context = service.retrieve_context("anything", top_k=5)
        assert context == ""

    def test_retrieve_context_fallback_on_error(self, service):
        service.vector_db.delete(delete_all=True)
        context = service.retrieve_context("something", top_k=5)
        assert context == ""


class TestRAGService:
    @pytest.fixture
    def rag(self):
        embedder = MockEmbedder(dimension=4)
        vector_db = MockPineconeClient()
        es = EmbeddingService(embedder=embedder, vector_db=vector_db)
        es.index_chunks([
            {"id": "r1", "text": "Use the STAR method for behavioral interviews", "source": "career.pdf", "page": 1},
            {"id": "r2", "text": "Asking open-ended questions builds rapport", "source": "comm.pdf", "page": 2},
        ])
        return RAGService(embedding_service=es)

    def test_retrieve_relevant_context(self, rag):
        context = rag.retrieve_context("job_interview", "I led a team and delivered the project on time")
        assert "STAR method" in context or "rapport" in context

    def test_retrieve_sources_in_context(self, rag):
        context = rag.retrieve_context("networking_event", "asking questions")
        assert "comm.pdf" in context or "career.pdf" in context

    def test_fallback_on_empty_transcript(self, rag):
        context = rag.retrieve_context("networking_event", "")
        assert isinstance(context, str)

    def test_fallback_when_service_unavailable(self):
        class UnavailableEmbeddingService:
            is_available = False

            def retrieve_context(self, transcript, top_k=5):
                raise AssertionError("should not be called when unavailable")

        rag = RAGService(embedding_service=UnavailableEmbeddingService())
        context = rag.retrieve_context("any", "hello")
        assert context == ""


class TestRAGFeedbackIntegration:
    def test_rag_context_includes_references_in_report(self, db_session):
        from app.feedback.service import FeedbackService
        from app.models.user import User
        from app.models.session import Session as SessionModel
        from app.models.report import Report
        from app.models.turn import Turn
        import json

        embedder = MockEmbedder(dimension=4)
        vector_db = MockPineconeClient()
        es = EmbeddingService(embedder=embedder, vector_db=vector_db)
        es.index_chunks([
            {"id": "ref1", "text": "Active listening is key to effective communication", "source": "hbr.pdf", "page": 1},
        ])

        service = FeedbackService()
        service.rag = RAGService(embedding_service=es)

        user = User(id="rag-test-user", clerk_id="rag-clerk", email="rag@test.com")
        db_session.add(user)
        db_session.flush()

        session = SessionModel(user_id="rag-test-user", scenario="networking_event", status="completed")
        db_session.add(session)
        db_session.flush()

        db_session.add(Turn(session_id=session.id, speaker="ai", content="Tell me about yourself"))
        db_session.add(Turn(session_id=session.id, speaker="user", content="I listen carefully to my team members"))

        report = Report(
            user_id="rag-test-user",
            session_id=session.id,
            title="RAG Test",
            status="generating",
        )
        db_session.add(report)
        db_session.commit()

        service.generate_report(db_session, report.id)

        updated = db_session.query(Report).filter(Report.id == report.id).first()
        assert updated.status == "ready"
        data = json.loads(updated.content)
        assert "references" in data
        assert len(data["references"]) >= 1
        assert data["references"][0]["source"] == "hbr.pdf"
