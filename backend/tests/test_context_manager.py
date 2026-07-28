from app.conversations.context_manager import ContextManager


class TestContextManager:
    def test_init_without_turns(self):
        ctx = ContextManager("networking_event")
        assert ctx.scenario_id == "networking_event"
        assert len(ctx._turns) == 0

    def test_add_turn(self):
        ctx = ContextManager("networking_event")
        ctx.add_turn("user", "Hello")
        ctx.add_turn("ai", "Hi there")
        assert len(ctx._turns) == 2
        assert ctx._turns[0]["speaker"] == "user"
        assert ctx._turns[0]["content"] == "Hello"

    def test_get_transcript(self):
        ctx = ContextManager("networking_event")
        ctx.add_turn("user", "Hello")
        ctx.add_turn("ai", "Hi there")
        transcript = ctx.get_transcript()
        assert "User: Hello" in transcript
        assert "AI: Hi there" in transcript

    def test_get_transcript_empty(self):
        ctx = ContextManager("networking_event")
        assert ctx.get_transcript() == ""

    def test_get_memory_with_turns(self):
        ctx = ContextManager("networking_event")
        ctx.add_turn("user", "How are you?")
        memory = ctx.get_memory()
        assert "Recent context:" in memory
        assert "How are you?" in memory

    def test_get_memory_empty(self):
        ctx = ContextManager("networking_event")
        assert ctx.get_memory() == "No prior conversation."

    def test_get_scenario_goal(self):
        ctx = ContextManager("networking_event")
        goal = ctx.get_scenario_goal()
        assert "Make a memorable impression" in goal

    def test_get_scenario_goal_unknown(self):
        ctx = ContextManager("nonexistent")
        assert ctx.get_scenario_goal() == ""

    def test_get_state(self):
        ctx = ContextManager("networking_event")
        state = ctx.get_state()
        assert state["scenario_id"] == "networking_event"
        assert state["scenario_name"] == "Networking Event"
        assert state["turn_count"] == 0
        assert state["persona_name"] == "Jordan Chen"

    def test_to_dict(self):
        ctx = ContextManager("networking_event")
        ctx.add_turn("user", "Hello")
        data = ctx.to_dict()
        assert data["scenario_id"] == "networking_event"
        assert len(data["turns"]) == 1

    def test_from_dict(self):
        data = {"scenario_id": "job_interview", "turns": [{"speaker": "user", "content": "Hi"}]}
        ctx = ContextManager.from_dict(data)
        assert ctx.scenario_id == "job_interview"
        assert len(ctx._turns) == 1
        assert ctx._turns[0]["content"] == "Hi"
