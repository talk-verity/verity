import io
import struct
import wave

import pytest

from app.voice.service import STT_RETRY_TEXT, VoiceService
from app.voice.stt import MockSTTService
from app.voice.tts import MockTTSService
from app.conversations.service import ConversationService
from app.conversations.gemini_client import MockAIService


def _wav_bytes() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        for _ in range(1600):
            wf.writeframes(struct.pack("<h", 0))
    return buf.getvalue()


@pytest.fixture
def voice_service():
    return VoiceService(
        stt=MockSTTService(),
        tts=MockTTSService(),
        conversation_service=ConversationService(ai_service=MockAIService()),
    )


class TestSTT:
    def test_stt_interface(self):
        service = MockSTTService(text="hello world")
        result = service.transcribe("/fake/path.wav")
        assert result == "hello world"


class TestTTS:
    @pytest.mark.asyncio
    async def test_tts_interface(self):
        service = MockTTSService()
        result = await service.synthesize("hello")
        assert result == b"hello"


class TestVoiceService:
    def test_transcribe(self, voice_service):
        result = voice_service.transcribe(_wav_bytes())
        assert result == "Hello, this is a test transcription."

    @pytest.mark.asyncio
    async def test_synthesize(self, voice_service):
        result = await voice_service.synthesize("test")
        assert result == b"test"

    def test_transcribe_fallback_on_error(self):
        class FailingSTT(MockSTTService):
            def transcribe(self, audio_path):
                raise RuntimeError("STT failed")

        service = VoiceService(stt=FailingSTT(), tts=MockTTSService())
        result = service.transcribe(_wav_bytes())
        assert result == STT_RETRY_TEXT

    @pytest.mark.asyncio
    async def test_converse_returns_events(self, voice_service, db_session, user_id):
        session = voice_service.conversation.create_session(
            db_session, user_id, "networking_event"
        )
        events = []
        async for event in voice_service.converse(db_session, user_id, session.id, _wav_bytes()):
            events.append(event)
        assert len(events) >= 2
        assert events[0][0] == "transcription"
        assert events[1][0] == "ai_response"
        assert "Sorry" not in events[1][1]

    def test_get_or_create_session_creates_new(self, voice_service, db_session, user_id):
        sid = voice_service.get_or_create_session(db_session, user_id)
        assert sid is not None
        from app.models.session import Session as SessionModel
        session = db_session.query(SessionModel).filter(SessionModel.id == sid).first()
        assert session is not None
        assert session.user_id == user_id

    def test_get_or_create_session_reuses_active(self, voice_service, db_session, user_id):
        sid1 = voice_service.get_or_create_session(db_session, user_id)
        sid2 = voice_service.get_or_create_session(db_session, user_id)
        assert sid1 == sid2
