import logging
import os
import time
from pathlib import Path

from app.core.settings import settings

logger = logging.getLogger(__name__)

_PARAKEET_DIR = os.path.join(os.path.dirname(__file__), "parakeet_assets")


def _resample(samples, src_rate: int, dst_rate: int):
    if src_rate == dst_rate:
        return samples
    import numpy as np
    x_old = np.linspace(0.0, 1.0, num=len(samples), endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=int(len(samples) * dst_rate / src_rate), endpoint=False)
    return np.interp(x_new, x_old, samples).astype("float32")


class STTService:
    def transcribe(self, audio_path: str) -> str:
        raise NotImplementedError


class ParakeetSTTService(STTService):
    def __init__(self, model_dir: str = "", num_threads: int = 4):
        self.model_dir = model_dir or _PARAKEET_DIR
        self.num_threads = num_threads
        self._recognizer = None

    def _load(self):
        if self._recognizer is not None:
            return
        logger.info("Loading NVIDIA Parakeet model from: %s", self.model_dir)
        from sherpa_onnx import OfflineRecognizer
        self._recognizer = OfflineRecognizer.from_transducer(
            encoder=os.path.join(self.model_dir, "encoder.int8.onnx"),
            decoder=os.path.join(self.model_dir, "decoder.int8.onnx"),
            joiner=os.path.join(self.model_dir, "joiner.int8.onnx"),
            tokens=os.path.join(self.model_dir, "tokens.txt"),
            num_threads=self.num_threads,
            sample_rate=16000,
            feature_dim=80,
            decoding_method="greedy_search",
            model_type="nemo_transducer",
        )

    def transcribe(self, audio_path: str) -> str:
        self._load()
        import soundfile as sf
        samples, sr = sf.read(audio_path, dtype="float32", always_2d=True)
        samples = samples[:, 0]
        samples = _resample(samples, sr, 16000)

        t0 = time.time()
        stream = self._recognizer.create_stream()
        stream.accept_waveform(16000, samples)
        self._recognizer.decode_stream(stream)
        text = stream.result.text.strip()
        elapsed = time.time() - t0
        logger.info("Parakeet STT completed in %.1fs", elapsed)
        return text

    def warmup(self):
        self._load()


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
        logger.info("Canary-Qwen STT completed in %.1fs", elapsed)
        return text


class GroqSTTService(STTService):
    def __init__(self, model: str = "whisper-large-v3-turbo"):
        from groq import Groq
        self.model = model
        self._client = Groq(api_key=settings.GROQ_API_KEY, timeout=30, max_retries=0)

    def transcribe(self, audio_path: str) -> str:
        with open(audio_path, "rb") as f:
            response = self._client.audio.transcriptions.create(
                file=(Path(audio_path).name, f.read(), "audio/wav"),
                model=self.model,
                response_format="json",
            )
        text = response.text.strip()
        logger.info("Groq STT completed")
        return text


class MockSTTService(STTService):
    def __init__(self, text: str = "Hello, this is a test transcription."):
        self.text = text

    def transcribe(self, audio_path: str) -> str:
        return self.text


_stt_service = None


def _get_stt_service() -> STTService:
    global _stt_service
    if _stt_service is None:
        if settings.STT_PROVIDER == "parakeet":
            _stt_service = ParakeetSTTService(
                model_dir=settings.PARAKEET_MODEL_DIR,
                num_threads=settings.PARAKEET_NUM_THREADS,
            )
        elif settings.STT_PROVIDER == "canary_qwen":
            _stt_service = CanaryQwenSTTService(model_name=settings.CANARY_QWEN_MODEL)
        elif settings.STT_PROVIDER == "groq":
            _stt_service = GroqSTTService(model=settings.GROQ_STT_MODEL)
        elif settings.STT_PROVIDER == "mock" and settings.DEMO_MODE:
            _stt_service = MockSTTService()
        else:
            from fastapi import HTTPException
            raise HTTPException(503, "Speech provider is not configured")
    return _stt_service


from threading import Lock
_service_lock = Lock()

def get_stt_service() -> STTService:
    with _service_lock:
        return _get_stt_service()
