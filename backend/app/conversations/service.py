import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.conversations.context_manager import ContextManager
from app.conversations.gemini_client import AIService, GeminiClient, GroqClient, MockAIService
from app.conversations.prompt_builder import PromptBuilder
from app.conversations.scenarios import get_scenario
from app.core.settings import settings
from app.models.session import Session as SessionModel
from app.models.turn import Turn

logger = logging.getLogger(__name__)


class ConversationService:
    def __init__(self, ai_service: AIService | None = None):
        if ai_service:
            self.ai_service = ai_service
        elif settings.GROQ_API_KEY:
            self.ai_service = GroqClient()
        elif settings.GEMINI_API_KEY:
            self.ai_service = GeminiClient()
        elif settings.DEMO_MODE:
            self.ai_service = MockAIService()
        else:
            self.ai_service = None
        self.prompt_builder = PromptBuilder()

    def create_session(self, db: Session, user_id: str, scenario_id: str) -> SessionModel:
        scenario = get_scenario(scenario_id)
        if not scenario:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown scenario: {scenario_id}")

        session = SessionModel(
            user_id=user_id,
            scenario=scenario_id,
            title=scenario["name"],
            status="active",
        )
        db.add(session)
        db.flush()

        opening = scenario.get("opening_line")
        if opening:
            turn = Turn(session_id=session.id, speaker="ai", content=opening)
            db.add(turn)
        db.commit()
        db.refresh(session)
        return session

    def get_session(self, db: Session, session_id: str, user_id: str) -> SessionModel:
        session = db.query(SessionModel).filter(SessionModel.id == session_id, SessionModel.user_id == user_id).first()
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        return session

    def delete_session(self, db: Session, session_id: str, user_id: str) -> None:
        session = self.get_session(db, session_id, user_id)
        db.delete(session)
        db.commit()

    def get_turns(self, db: Session, session_id: str) -> list[Turn]:
        return db.query(Turn).filter(Turn.session_id == session_id).order_by(Turn.created_at).all()

    def build_context(self, session: SessionModel, turns: list[Turn]) -> ContextManager:
        ctx = ContextManager(session.scenario)
        for turn in turns[-40:]:
            ctx.add_turn(turn.speaker, turn.content)
        return ctx

    def respond(self, db: Session, session_id: str, user_id: str, message: str, request_id: str | None = None) -> Turn:
        try:
            session = (db.query(SessionModel).filter(SessionModel.id == session_id,
                       SessionModel.user_id == user_id).populate_existing().with_for_update().first())
            if not session:
                raise HTTPException(404, "Session not found")
            if request_id:
                previous = db.query(Turn).filter(Turn.request_id == request_id).first()
                if previous:
                    if previous.session_id != session_id:
                        raise HTTPException(409, "Request ID already used")
                    return previous
            if session.status != "active":
                raise HTTPException(400, "Session is not active")
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            created_at = session.created_at if session.created_at.tzinfo else session.created_at.replace(tzinfo=timezone.utc)
            if (now - created_at).total_seconds() >= 300:
                session.status = "timed_out"
                db.commit()
                raise HTTPException(400, "Session time limit expired (5 minutes). Please complete the conversation to view feedback.")
            if not message.strip() or len(message) > 8000:
                raise HTTPException(422, "Message must contain 1–8000 characters")
            if self.ai_service is None:
                raise HTTPException(503, "Conversation provider is not configured")
            turns = self.get_turns(db, session_id)
            if len(turns) >= 201:
                raise HTTPException(422, "Session limit reached. Complete this conversation first.")
            context = self.build_context(session, turns)
            context.add_turn("user", message)
            prompt = self.prompt_builder.build(session.scenario, context)
            try:
                ai_response = self.ai_service.generate(prompt)
                if not ai_response or not ai_response.strip():
                    raise ValueError("Empty provider response")
            except Exception as exc:
                logger.exception("Conversation provider failed")
                raise HTTPException(503, "Response unavailable. Retry your message.") from exc
            db.add(Turn(session_id=session_id, speaker="user", content=message))
            db.flush()
            ai_turn = Turn(session_id=session_id, speaker="ai", content=ai_response, request_id=request_id)
            db.add(ai_turn)
            db.commit()
            db.refresh(ai_turn)
            return ai_turn
        except Exception:
            db.rollback()
            raise
