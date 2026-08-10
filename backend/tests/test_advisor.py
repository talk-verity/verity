import json

import pytest

from app.embeddings.embedder import MockEmbedder
from app.embeddings.pinecone import MockPineconeClient
from app.embeddings.service import EmbeddingService
from app.feedback.advisor import ResearchAdvisor
from app.feedback.generator import FeedbackGenerator
from app.feedback.rag import RAGService


def make_rag_service(chunks: list[dict]) -> RAGService:
    embedder = MockEmbedder(dimension=4)
    vector_db = MockPineconeClient()
    es = EmbeddingService(embedder=embedder, vector_db=vector_db)
    es.index_chunks(chunks)
    return RAGService(embedding_service=es)


class TestScenarioAwareRAG:
    def test_prioritizes_scenario_relevant_sources(self):
        rag = make_rag_service([
            {"id": "s1", "text": "Prepare a two minute pitch and exchange contact details", "source": "HBR Guide to Networking.pdf", "page": 1},
            {"id": "s2", "text": "Use the STAR method to structure your interview stories", "source": "STAR Method.pdf", "page": 1},
        ])
        context = rag.retrieve_context("networking_event", "I introduced myself to several people", top_k=1)
        assert "HBR Guide to Networking.pdf" in context

    def test_scenario_sources_in_chunks(self):
        rag = make_rag_service([
            {"id": "s1", "text": "Networking tips for introverts", "source": "networking.pdf", "page": 1},
            {"id": "s2", "text": "Unrelated content about tax law", "source": "other.pdf", "page": 1},
        ])
        chunks = rag.retrieve_chunks("how to network at a conference", top_k=4, scenario_id="networking_event")
        sources = [c["source"] for c in chunks]
        assert "networking.pdf" in sources

    def test_fallback_when_no_scenario_match(self):
        rag = make_rag_service([
            {"id": "s1", "text": "Say the following sentence in your next interview", "source": "career.pdf", "page": 1},
        ])
        context = rag.retrieve_context("job_interview", "hello")
        assert "career.pdf" in context


class TestResearchAdvisor:
    def test_extractive_suggestions(self):
        advisor = ResearchAdvisor(
            rag=make_rag_service([
                {"id": "s1", "text": "Quantify your impact in numbers and metrics.", "source": "promo.pdf", "page": 1},
            ]),
        )
        result = advisor.suggest(
            {"name": "Promotion Discussion"},
            {"weaknesses": ["Vague about impact"], "strengths": []},
            "[Source: promo.pdf]\nQuantify your impact in numbers and metrics.",
        )
        assert result is not None
        assert result["recommendations"]
        assert result["suggested_responses"][0]["weakness"] == "Vague about impact"
        assert "source" not in result["suggested_responses"][0]
        assert "Research note" not in result["recommendations"][0]

    def test_suggest_none_without_chunks(self):
        advisor = ResearchAdvisor(rag=make_rag_service([]))
        result = advisor.suggest({"name": "X"}, {"weaknesses": []}, "")
        assert result is None

    def test_scenario_tips_extractive(self):
        advisor = ResearchAdvisor(
            rag=make_rag_service([
                {"id": "s1", "text": "Practice your elevator pitch until it feels natural.", "source": "networking.pdf", "page": 1},
            ]),
        )
        tips = advisor.scenario_tips("networking_event", top_k=2)
        assert tips
        assert any("elevator pitch" in t for t in tips)

    def test_llm_suggestions_path(self):
        class FakeAI:
            def generate(self, prompt: str) -> str:
                return json.dumps({
                    "recommendations": ["Lead with your strongest metric."],
                    "suggested_responses": [
                        {"weakness": "Vague", "response": "I cut deployment time by 30%."}
                    ],
                })

        advisor = ResearchAdvisor(ai_service=FakeAI(), rag=make_rag_service([]))
        result = advisor.suggest(
            {"name": "Promotion Discussion"},
            {"weaknesses": ["Vague about impact"]},
            "[Source: promo.pdf]\nQuantify your impact.",
        )
        assert result["recommendations"] == ["Lead with your strongest metric."]
        assert result["suggested_responses"][0]["response"] == "I cut deployment time by 30%."
        assert "source" not in result["suggested_responses"][0]

    def test_llm_suggestions_strips_source_field(self):
        class FakeAI:
            def generate(self, prompt: str) -> str:
                return json.dumps({
                    "recommendations": ["Lead with your strongest metric."],
                    "suggested_responses": [
                        {"weakness": "Vague", "response": "I cut deployment time by 30%.", "source": "promo.pdf"}
                    ],
                })

        advisor = ResearchAdvisor(ai_service=FakeAI(), rag=make_rag_service([]))
        result = advisor.suggest(
            {"name": "Promotion Discussion"},
            {"weaknesses": ["Vague about impact"]},
            "[Source: promo.pdf]\nQuantify your impact.",
        )
        assert "source" not in result["suggested_responses"][0]

    def test_llm_tips_path(self):
        class FakeAI:
            def generate(self, prompt: str) -> str:
                return '```json\n["Ask about team priorities first.", "Lead with quantified wins."]\n```'

        advisor = ResearchAdvisor(
            ai_service=FakeAI(),
            rag=make_rag_service([
                {"id": "s1", "text": "Prepare for the review with data.", "source": "reviews.pdf", "page": 1},
            ]),
        )
        tips = advisor.scenario_tips("performance_review", top_k=2)
        assert tips == ["Ask about team priorities first.", "Lead with quantified wins."]


class TestFeedbackGeneratorSuggestions:
    def test_generate_uses_research_recommendations(self):
        analysis = {
            "overall_score": 70.0,
            "strengths": [],
            "weaknesses": ["Vague about impact"],
            "confidence_score": 60.0,
            "clarity_score": 70.0,
            "filler_word_count": 1,
            "filler_words": ["um"],
            "interruption_count": 0,
            "goal_completion": "partially addressed",
            "total_turns": 2,
            "total_user_words": 50,
            "avg_response_length": 25.0,
        }
        suggestions = {
            "recommendations": ["Ground your case in metrics."],
            "suggested_responses": [
                {"weakness": "Vague", "response": "I reduced latency by 40%.", "source": "promo.pdf"}
            ],
        }
        content = json.loads(FeedbackGenerator().generate(analysis, "Promo", "Marcus", suggestions=suggestions))
        assert content["recommendations"] == ["Ground your case in metrics."]
        assert content["suggested_responses"][0]["response"] == "I reduced latency by 40%."

    def test_generate_keeps_template_without_suggestions(self):
        analysis = {
            "overall_score": 70.0,
            "strengths": [],
            "weaknesses": [],
            "confidence_score": 60.0,
            "clarity_score": 70.0,
            "filler_word_count": 5,
            "filler_words": ["um"],
            "interruption_count": 0,
            "goal_completion": "partially addressed",
            "total_turns": 2,
            "total_user_words": 50,
            "avg_response_length": 25.0,
        }
        content = json.loads(FeedbackGenerator().generate(analysis, "Promo", "Marcus"))
        assert "suggested_responses" not in content
        assert content["recommendations"]
