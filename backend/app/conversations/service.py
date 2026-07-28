import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.conversations.context_manager import ContextManager
from app.conversations.gemini_client import AIService, GeminiClient
from app.conversations.prompt_builder import PromptBuilder
from app.conversations.scenarios import get_scenario
from app.models.session import Session as SessionModel
from app.models.turn import Turn

logger = logging.getLogger(__name__)


class ConversationService:
    def __init__(self, ai_service: AIService | None = None):
        self.ai_service = ai_service or GeminiClient()
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
        for turn in turns:
            ctx.add_turn(turn.speaker, turn.content)
        return ctx

    def respond(self, db: Session, session_id: str, user_id: str, message: str) -> Turn:
        session = self.get_session(db, session_id, user_id)

        if session.status != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session is not active")

        user_turn = Turn(session_id=session_id, speaker="user", content=message)
        db.add(user_turn)
        db.commit()
        db.refresh(user_turn)

        turns = self.get_turns(db, session_id)
        context = self.build_context(session, turns)

        prompt = self.prompt_builder.build(session.scenario, context)
        logger.info("Sending prompt to AI service: %.200s", prompt)

        try:
            ai_response = self.ai_service.generate(prompt)
        except Exception as e:
            logger.error("AI generation failed: %s", e)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI service unavailable")

        ai_turn = Turn(session_id=session_id, speaker="ai", content=ai_response)
        db.add(ai_turn)
        db.commit()
        db.refresh(ai_turn)

        return ai_turn
