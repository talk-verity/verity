"""Local Kokoro speech synthesis; inference is offloaded by VoiceService."""
import io
from pathlib import Path

import soundfile as sf

from app.core.settings import settings


class KokoroTTSService:
    def __init__(self):
        self._model = None

    def warmup(self):
        if self._model is None:
            from kokoro_onnx import Kokoro
            assets = Path(__file__).parent / "kokoro_assets"
            self._model = Kokoro(
                str(assets / "kokoro-v1.0.onnx"),
                str(assets / "voices-v1.0.bin"),
            )

    async def synthesize(self, text: str) -> bytes:
        self.warmup()
        samples, rate = self._model.create(text, voice=settings.KOKORO_VOICE, lang="en-us")
        if not len(samples):
            raise RuntimeError("Kokoro produced no audio")
        output = io.BytesIO()
        sf.write(output, samples, rate, format="WAV", subtype="PCM_16")
        return output.getvalue()
