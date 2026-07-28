import logging
import os
import tempfile
import uuid

from sqlalchemy.orm import Session

from app.conversations.gemini_client import AIService, GeminiClient
from app.conversations.prompt_builder import PromptBuilder
from app.conversations.scenarios import get_scenario
from app.conversations.service import ConversationService
from app.models.session import Session as SessionModel
from app.models.turn import Turn
from app.voice.stt import STTService, get_stt_service
from app.voice.tts import TTSService, get_tts_service

logger = logging.getLogger(__name__)


STT_RETRY_TEXT = "Sorry, I didn't catch that. Could you repeat it?"


class VoiceService:
    def __init__(
        self,
        stt: STTService | None = None,
        tts: TTSService | None = None,
        conversation_service: ConversationService | None = None,
    ):
        self.stt = stt or get_stt_service()
        self.tts = tts or get_tts_service()
        self.conversation = conversation_service or ConversationService()

    def transcribe(self, audio_data: bytes) -> str:
        suffix = ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_data)
            audio_path = f.name
        try:
            text = self.stt.transcribe(audio_path)
            return text
        except Exception as e:
            logger.error("STT failed: %s", e)
            return STT_RETRY_TEXT
        finally:
            try:
                os.unlink(audio_path)
            except OSError:
                pass

    async def synthesize(self, text: str) -> bytes:
        return await self.tts.synthesize(text)

    async def converse(
        self,
        db: Session,
        user_id: str,
        session_id: str,
        audio_data: bytes,
    ):
        text = self.transcribe(audio_data)
        yield "transcription", text

        if text == STT_RETRY_TEXT:
            ai_text = text
        else:
            turn = self.conversation.respond(db, session_id, user_id, text)
            ai_text = turn.content

        yield "ai_response", ai_text

        audio = await self.synthesize(ai_text)
        yield "audio", audio

    def get_or_create_session(self, db: Session, user_id: str) -> str:
        active = (
            db.query(SessionModel)
            .filter(SessionModel.user_id == user_id, SessionModel.status == "active")
            .order_by(SessionModel.created_at.desc())
            .first()
        )
        if active:
            return active.id

        default_scenario = "networking_event"
        session = self.conversation.create_session(db, user_id, default_scenario)
        return session.id
