import logging
import time
from pathlib import Path

from app.core.settings import settings

logger = logging.getLogger(__name__)


class STTService:
    def transcribe(self, audio_path: str) -> str:
        raise NotImplementedError


class CanaryQwenSTTService(STTService):
    def __init__(self, model_name: str = "nvidia/canary-qwen-2.5b"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return
        logger.info("Loading Canary-Qwen model: %s", self.model_name)
        from nemo.collections.speechlm2.models import SALM
        model = SALM.from_pretrained(self.model_name)
        model.eval()
        self._model = model

    def transcribe(self, audio_path: str) -> str:
        self._load_model()
        model = self._model
        t0 = time.time()
        prompts = [[
            {
                "role": "user",
                "content": f"Transcribe the following: {model.audio_locator_tag}",
                "audio": [audio_path],
            }
        ]]
        answer_ids = model.generate(prompts=prompts, max_new_tokens=128)
        text = model.tokenizer.ids_to_text(answer_ids[0].cpu()).strip()
        elapsed = time.time() - t0
        logger.info("Canary-Qwen STT (%.1fs): %.100s", elapsed, text)
        return text


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
    if settings.STT_PROVIDER == "canary_qwen":
        return CanaryQwenSTTService(model_name=settings.CANARY_QWEN_MODEL)
    if settings.STT_PROVIDER == "groq":
        return GroqSTTService(model=settings.GROQ_STT_MODEL)
    return MockSTTService()
