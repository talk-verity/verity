from app.conversations.context_manager import ContextManager
from app.conversations.prompt_builder import PromptBuilder


class TestPromptBuilder:
    def setup_method(self):
        self.builder = PromptBuilder()

    def test_build_without_turns(self):
        ctx = ContextManager("networking_event")
        prompt = self.builder.build("networking_event", ctx)
        assert "Jordan Chen" in prompt
        assert "Senior Engineering Manager" in prompt
        assert "TechCorp" in prompt
        assert "Make a memorable impression" in prompt
        assert "CONVERSATION SO FAR" not in prompt

    def test_build_with_turns(self):
        ctx = ContextManager("networking_event")
        ctx.add_turn("user", "Hi Jordan, I'm Alice!")
        ctx.add_turn("ai", "Nice to meet you, Alice!")
        prompt = self.builder.build("networking_event", ctx)
        assert "CONVERSATION SO FAR" in prompt
        assert "User: Hi Jordan" in prompt
        assert "AI: Nice to meet you" in prompt

    def test_build_unknown_scenario(self):
        ctx = ContextManager("nonexistent")
        prompt = self.builder.build("nonexistent", ctx)
        assert prompt == ""

    def test_build_system_prompt(self):
        prompt = self.builder.build_system_prompt("performance_review")
        assert "Sarah Park" in prompt
        assert "Director of Engineering" in prompt
        assert "Stay in character" in prompt
