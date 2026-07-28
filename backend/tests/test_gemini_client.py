from app.conversations.gemini_client import MockAIService


class TestMockAIService:
    def test_generate_returns_string(self):
        ai = MockAIService()
        response = ai.generate("Hello")
        assert isinstance(response, str)
        assert len(response) > 0

    def test_generate_cycles_through_responses(self):
        ai = MockAIService(responses=["resp1", "resp2"])
        assert ai.generate("msg1") == "resp1"
        assert ai.generate("msg2") == "resp2"
        assert ai.generate("msg3") == "resp1"

    def test_default_responses(self):
        ai = MockAIService()
        r1 = ai.generate("msg")
        r2 = ai.generate("msg")
        assert r1 != r2
