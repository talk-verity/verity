import logging
import os
import tempfile
from pathlib import Path

from app.core.settings import settings

logger = logging.getLogger(__name__)


class STTService:
    def transcribe(self, audio_path: str) -> str:
        raise NotImplementedError


class FasterWhisperSTT(STTService):
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",
                download_root=settings.WHISPER_MODEL_DIR or None,
            )
        return self._model

    def transcribe(self, audio_path: str) -> str:
        model = self._get_model()
        segments, info = model.transcribe(audio_path, beam_size=5)
        text = "".join(seg.text for seg in segments)
        logger.info("Transcribed %s: %.100s", audio_path, text)
        return text.strip()


class GroqSTTService(STTService):
    def __init__(self, model: str = "whisper-large-v3-turbo"):
        from groq import Groq
        self.model = model
        self._client = Groq(api_key=settings.GROQ_API_KEY)

    def transcribe(self, audio_path: str) -> str:
        with open(audio_path, "rb") as f:
            response = self._client.audio.transcriptions.create(
                file=(Path(audio_path).name, f.read(), "audio/wav"),
                model=self.model,
                response_format="json",
            )
        text = response.text.strip()
        logger.info("Groq STT: %.100s", text)
        return text


class MockSTTService(STTService):
    def __init__(self, text: str = "Hello, this is a test transcription."):
        self.text = text

    def transcribe(self, audio_path: str) -> str:
        return self.text


def get_stt_service() -> STTService:
    if settings.STT_PROVIDER == "faster_whisper":
        return FasterWhisperSTT(model_size=settings.WHISPER_MODEL_SIZE)
    if settings.STT_PROVIDER == "groq":
        return GroqSTTService(model=settings.GROQ_STT_MODEL)
    return MockSTTService()
