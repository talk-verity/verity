import pytest

from app.conversations.gemini_client import MockAIService
from app.conversations.service import ConversationService
from app.models.turn import Turn


class TestIntegration:
    @pytest.fixture(autouse=True)
    def setup(self, db_session):
        self.db = db_session
        self.service = ConversationService(ai_service=MockAIService())
        self.user_id = "integration-test-user"

    def test_whole_conversation_lifecycle(self):
        session = self.service.create_session(self.db, self.user_id, "job_interview")
        assert session.status == "active"
        assert session.scenario == "job_interview"

        turns = self.service.get_turns(self.db, session.id)
        assert len(turns) == 1
        assert turns[0].speaker == "ai"

        msg1 = self.service.respond(self.db, session.id, self.user_id, "Thanks for having me!")
        assert msg1.speaker == "ai"

        msg2 = self.service.respond(self.db, session.id, self.user_id, "I've been building APIs for 5 years.")
        assert msg2.speaker == "ai"

        all_turns = self.service.get_turns(self.db, session.id)
        assert len(all_turns) == 5
        assert all_turns[0].speaker == "ai"
        assert all_turns[1].speaker == "user"
        assert all_turns[1].content == "Thanks for having me!"
        assert all_turns[2].speaker == "ai"
        assert all_turns[3].speaker == "user"
        assert all_turns[3].content == "I've been building APIs for 5 years."
        assert all_turns[4].speaker == "ai"

    def test_session_restore(self):
        session = self.service.create_session(self.db, self.user_id, "performance_review")
        self.service.respond(self.db, session.id, self.user_id, "I think the quarter went well overall.")
        self.service.respond(self.db, session.id, self.user_id, "The production incident was a setback though.")

        restored_session = self.service.get_session(self.db, session.id, self.user_id)
        assert restored_session.id == session.id
        assert restored_session.scenario == "performance_review"
        assert restored_session.status == "active"

        restored_turns = self.service.get_turns(self.db, session.id)
        assert len(restored_turns) == 5

        ctx = self.service.build_context(restored_session, restored_turns)
        assert ctx.get_transcript() != ""
        assert "production incident" in ctx.get_transcript()
        assert ctx.get_state()["scenario_name"] == "Performance Review"

        msg3 = self.service.respond(self.db, session.id, self.user_id, "I learned from the incident.")
        assert msg3.speaker == "ai"
