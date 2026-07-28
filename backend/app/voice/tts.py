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
        logger.info("Synthesized %d bytes for: %.100s", len(result), text)
        return result


class MockTTSService(TTSService):
    async def synthesize(self, text: str) -> bytes:
        return text.encode("utf-8")


def get_tts_service() -> TTSService:
    if settings.TTS_PROVIDER == "edge":
        return EdgeTTSService(voice=settings.TTS_VOICE)
    return MockTTSService()
