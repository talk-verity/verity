import io
import logging
import os
import copy
import torch

from app.core.settings import settings

logger = logging.getLogger(__name__)

_VOICES_DIR = os.path.join(os.path.dirname(__file__), "vibevoice_assets", "voices", "streaming_model")


class VibeVoiceTTSService:
    def __init__(self, model_path: str = "microsoft/VibeVoice-Realtime-0.5B", speaker: str = "en-Carter_man"):
        self.model_path = model_path
        self.speaker = speaker
        self._processor = None
        self._model = None
        self._voice_prompt = None
        self._device = None

    def _get_device(self):
        if self._device is None:
            if torch.cuda.is_available():
                self._device = "cuda"
            elif torch.backends.mps.is_available():
                self._device = "mps"
            else:
                self._device = "cpu"
        return self._device

    def _get_processor(self):
        if self._processor is None:
            from vibevoice.processor.vibevoice_streaming_processor import VibeVoiceStreamingProcessor
            self._processor = VibeVoiceStreamingProcessor.from_pretrained(self.model_path)
            logger.info("VibeVoice processor loaded")
        return self._processor

    def _get_model(self):
        if self._model is None:
            from vibevoice.modular.modeling_vibevoice_streaming_inference import VibeVoiceStreamingForConditionalGenerationInference
            device = self._get_device()
            dtype = torch.float32 if device in ("mps", "cpu") else torch.bfloat16
            attn = "sdpa"
            self._model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
                self.model_path,
                torch_dtype=dtype,
                attn_implementation=attn,
            )
            self._model.to(device)
            self._model.eval()
            self._model.set_ddpm_inference_steps(num_steps=5)
            logger.info("VibeVoice model loaded on %s", device)
        return self._model

    def _get_voice_prompt(self):
        if self._voice_prompt is None:
            voice_path = os.path.join(_VOICES_DIR, f"{self.speaker}.pt")
            if not os.path.exists(voice_path):
                available = [f.replace(".pt", "") for f in os.listdir(_VOICES_DIR) if f.endswith(".pt")]
                fallback = available[0] if available else None
                if not fallback:
                    raise FileNotFoundError(f"No voice prompt files found in {_VOICES_DIR}")
                logger.warning("Speaker '%s' not found, using '%s'", self.speaker, fallback)
                voice_path = os.path.join(_VOICES_DIR, f"{fallback}.pt")
                self.speaker = fallback

            device = self._get_device()
            from transformers.cache_utils import DynamicCache
            from transformers.modeling_outputs import BaseModelOutputWithPast
            try:
                with torch.serialization.safe_globals([BaseModelOutputWithPast, DynamicCache]):
                    self._voice_prompt = torch.load(voice_path, map_location=device, weights_only=True)
            except Exception:
                self._voice_prompt = torch.load(voice_path, map_location=device, weights_only=False)
            logger.info("Voice prompt loaded: %s", self.speaker)
        return self._voice_prompt

    async def synthesize(self, text: str) -> bytes:
        processor = self._get_processor()
        model = self._get_model()
        voice_prompt = self._get_voice_prompt()
        device = self._get_device()

        text = text.replace("’", "'").replace('"', '"').replace('"', '"')

        inputs = processor.process_input_with_cached_prompt(
            text=text,
            cached_prompt=voice_prompt,
            padding=True,
            return_tensors="pt",
            return_attention_mask=True,
        )

        for k, v in inputs.items():
            if torch.is_tensor(v):
                inputs[k] = v.to(device)

        outputs = model.generate(
            **inputs,
            max_new_tokens=None,
            cfg_scale=1.5,
            tokenizer=processor.tokenizer,
            generation_config={"do_sample": False},
            verbose=False,
            all_prefilled_outputs=copy.deepcopy(voice_prompt) if voice_prompt is not None else None,
        )

        if outputs.speech_outputs and outputs.speech_outputs[0] is not None:
            audio = outputs.speech_outputs[0].cpu().numpy().squeeze()
            buf = io.BytesIO()
            import soundfile as sf
            sf.write(buf, audio, 24000, format="WAV")
            result = buf.getvalue()
            logger.info("VibeVoice TTS: %d bytes for: %.100s", len(result), text)
            return result

        logger.warning("VibeVoice generated no audio for: %.100s", text)
        return b""
