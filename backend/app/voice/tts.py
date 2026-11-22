import io
import logging

from app.core.settings import settings

logger = logging.getLogger(__name__)


class TTSService:
    async def synthesize(self, text: str) -> bytes:
        raise NotImplementedError


class EdgeTTSService(TTSService):
    def __init__(self, voice: str = "en-US-JennyNeural"):
        self.voice = voice

    async def synthesize(self, text: str) -> bytes:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice=self.voice)
        audio = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio.write(chunk["data"])
        result = audio.getvalue()
        logger.info("Synthesized %d bytes", len(result))
        return result


class MockTTSService(TTSService):
    async def synthesize(self, text: str) -> bytes:
        return text.encode("utf-8")


_tts_service = None


def _get_tts_service() -> TTSService:
    global _tts_service
    if _tts_service is None:
        if settings.TTS_PROVIDER == "edge":
            _tts_service = EdgeTTSService(voice=settings.TTS_VOICE)
        elif settings.TTS_PROVIDER == "kokoro":
            from app.voice.tts_kokoro import KokoroTTSService
            _tts_service = KokoroTTSService()
        elif settings.TTS_PROVIDER == "vibevoice":
            from app.voice.tts_vibevoice import VibeVoiceTTSService
            _tts_service = VibeVoiceTTSService(
                model_path=settings.VIBEVOICE_MODEL,
                speaker=settings.VIBEVOICE_SPEAKER,
            )
        elif settings.TTS_PROVIDER == "mock" and settings.DEMO_MODE:
            _tts_service = MockTTSService()
        else:
            from fastapi import HTTPException
            raise HTTPException(503, "Speech provider is not configured")
    return _tts_service


from threading import Lock
_service_lock = Lock()

def get_tts_service() -> TTSService:
    with _service_lock:
        return _get_tts_service()
