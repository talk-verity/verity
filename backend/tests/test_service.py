import pytest

from app.conversations.gemini_client import MockAIService
from app.conversations.service import ConversationService
from app.models.session import Session as SessionModel
from app.models.turn import Turn


@pytest.fixture
def service():
    return ConversationService(ai_service=MockAIService())


@pytest.fixture
def user_id():
    return "test-user-id"


class TestConversationService:
    def test_create_session(self, db_session, service, user_id):
        session = service.create_session(db_session, user_id, "networking_event")
        assert session.id is not None
        assert session.scenario == "networking_event"
        assert session.user_id == user_id
        assert session.status == "active"
        assert session.title == "Networking Event"

    def test_create_session_invalid_scenario(self, db_session, service, user_id):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            service.create_session(db_session, user_id, "nonexistent")
        assert exc.value.status_code == 400

    def test_get_session(self, db_session, service, user_id):
        session = service.create_session(db_session, user_id, "networking_event")
        retrieved = service.get_session(db_session, session.id, user_id)
        assert retrieved.id == session.id
        assert retrieved.user_id == user_id

    def test_get_session_not_found(self, db_session, service, user_id):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            service.get_session(db_session, "nonexistent-id", user_id)
        assert exc.value.status_code == 404

    def test_get_session_wrong_user(self, db_session, service, user_id):
        session = service.create_session(db_session, user_id, "networking_event")
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            service.get_session(db_session, session.id, "different-user")
        assert exc.value.status_code == 404

    def test_delete_session(self, db_session, service, user_id):
        session = service.create_session(db_session, user_id, "networking_event")
        service.delete_session(db_session, session.id, user_id)
        assert db_session.query(SessionModel).count() == 0

    def test_get_turns_empty(self, db_session, service, user_id):
        session = service.create_session(db_session, user_id, "networking_event")
        turns = service.get_turns(db_session, session.id)
        assert turns == []

    def test_respond_creates_turns(self, db_session, service, user_id):
        session = service.create_session(db_session, user_id, "networking_event")
        ai_turn = service.respond(db_session, session.id, user_id, "Hello there!")
        assert ai_turn.speaker == "ai"
        assert ai_turn.content != ""
        assert ai_turn.session_id == session.id

        turns = db_session.query(Turn).filter(Turn.session_id == session.id).order_by(Turn.created_at).all()
        assert len(turns) == 2
        assert turns[0].speaker == "user"
        assert turns[0].content == "Hello there!"
        assert turns[1].speaker == "ai"
        assert turns[1].id == ai_turn.id

    def test_respond_inactive_session(self, db_session, service, user_id):
        session = service.create_session(db_session, user_id, "networking_event")
        session.status = "completed"
        db_session.commit()

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            service.respond(db_session, session.id, user_id, "Hello")
        assert exc.value.status_code == 400
