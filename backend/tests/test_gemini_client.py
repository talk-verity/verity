from app.conversations.gemini_client import MockAIService, _categorize


class TestCategorize:
    def test_project(self):
        assert _categorize("I built a project") == "project"

    def test_startup(self):
        assert _categorize("my startup") == "startup"

    def test_question(self):
        assert _categorize("What do you think?") == "question"

    def test_thanks(self):
        assert _categorize("thank you") == "thanks"


class TestMockAIService:
    def test_generate_returns_string(self):
        ai = MockAIService()
        r = ai.generate("You are Jordan Chen\nUser: hello")
        assert isinstance(r, str)
        assert len(r) > 0

    def test_extract_name(self):
        ai = MockAIService()
        assert ai._extract_name("You are Sarah Park") == "Sarah"
        assert ai._extract_name("no match") == ""

    def test_extract_last_message(self):
        ai = MockAIService()
        prompt = "You are Jordan\n\nConversation so far:\nUser: hello\nAI: hi\nUser: how are you"
        assert ai._extract_last_message(prompt) == "how are you"
        assert ai._extract_last_message("no user") == ""

    def test_extract_context(self):
        ai = MockAIService()
        prompt = "Context: You're at a crowded industry mixer.\nGoal: impress"
        assert ai._extract_context(prompt) == "You're at a crowded industry mixer."
        assert ai._extract_context("no context") == ""
