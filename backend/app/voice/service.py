import logging
import os
import tempfile
from time import perf_counter

from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.conversations.service import ConversationService
from app.models.session import Session as SessionModel
from app.voice.stt import STTService, get_stt_service
from app.voice.tts import TTSService, get_tts_service

logger = logging.getLogger(__name__)
from threading import Lock
_tts_lock = Lock()
_stt_lock = Lock()


STT_RETRY_TEXT = "Sorry, I didn't catch that. Could you repeat it?"


class VoiceService:
    def __init__(
        self,
        stt: STTService | None = None,
        tts: TTSService | None = None,
        conversation_service: ConversationService | None = None,
    ):
        self.stt = stt
        self.tts = tts
        self.conversation = conversation_service or ConversationService()

    def transcribe(self, audio_data: bytes, source_format: str | None = None) -> str:
        audio_path_for_stt, wav_path = self._prepare_audio(audio_data, source_format)

        try:
            with _stt_lock:
                text = (self.stt or get_stt_service()).transcribe(audio_path_for_stt)
            return text
        except Exception as e:
            from fastapi import HTTPException
            logger.exception("STT failed")
            raise HTTPException(503, "Transcription unavailable. Please retry.") from e
        finally:
            paths = [audio_path_for_stt]
            if wav_path:
                paths.append(wav_path)
            for p in paths:
                try:
                    os.unlink(p)
                except OSError:
                    pass

    def _prepare_audio(self, audio_data: bytes, source_format: str | None) -> tuple[str, str | None]:
        from app.core.settings import settings
        from fastapi import HTTPException
        import subprocess
        import wave
        if not audio_data or len(audio_data) > settings.MAX_AUDIO_BYTES:
            raise HTTPException(413, "Audio upload exceeds the allowed size")
        if audio_data[:4] == b"RIFF" and audio_data[8:12] == b"WAVE":
            container = "wav"
        elif audio_data[:4] == b"OggS":
            container = "ogg"
        elif audio_data[:4] == b"\x1a\x45\xdf\xa3":
            container = "matroska"
        elif audio_data[4:8] == b"ftyp":
            container = "mov"
        else:
            raise HTTPException(422, "Unsupported recording format")
        source = tempfile.NamedTemporaryFile(suffix=".audio", delete=False)
        audio_path = source.name
        wav_path = audio_path + ".wav"
        try:
            with source:
                source.write(audio_data)
            # Decode every format, including WAV, to a bounded PCM representation.
            # FFmpeg detects the container; user-supplied filenames are never trusted.
            result = subprocess.run([
                self._ffmpeg_binary(), "-nostdin", "-v", "error", "-y", "-protocol_whitelist", "file,pipe",
                "-f", container, "-i", audio_path,
                "-t", str(settings.MAX_AUDIO_SECONDS + 1), "-ar", "16000", "-ac", "1",
                "-sample_fmt", "s16", wav_path,
            ], capture_output=True, timeout=30)
            if result.returncode:
                raise HTTPException(422, "Audio could not be decoded")
            with wave.open(wav_path) as wav:
                duration = wav.getnframes() / wav.getframerate()
            if duration > settings.MAX_AUDIO_SECONDS:
                raise HTTPException(413, "Recording exceeds the duration limit")
            return wav_path, audio_path
        except BaseException:
            for path in (audio_path, wav_path):
                try:
                    os.unlink(path)
                except OSError:
                    pass
            raise

    @staticmethod
    def _ffmpeg_binary():
        from app.core.settings import settings
        if settings.FFMPEG_BINARY == "bundled":
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        return settings.FFMPEG_BINARY

    async def synthesize(self, text: str) -> bytes:
        import asyncio
        def run():
            with _tts_lock:
                return asyncio.run((self.tts or get_tts_service()).synthesize(text))
        return await run_in_threadpool(run)

    async def converse(
        self,
        db: Session,
        user_id: str,
        session_id: str,
        audio_data: bytes,
        source_format: str | None = None,
        request_id: str | None = None,
    ):
        def recognize():
            path, original = self._prepare_audio(audio_data, source_format)
            try:
                with _stt_lock:
                    text = (self.stt or get_stt_service()).transcribe(path)
                return text, self._assess_quality(path, text)
            finally:
                for item in (path, original):
                    if item:
                        try:
                            os.unlink(item)
                        except OSError:
                            pass
        started = perf_counter()
        try:
            text, quality = await run_in_threadpool(recognize)
        except Exception as exc:
            from fastapi import HTTPException
            if isinstance(exc, HTTPException):
                raise
            logger.exception("Transcription failed")
            raise HTTPException(503, "Transcription unavailable. Please retry.") from exc
        if not text or text == STT_RETRY_TEXT:
            from fastapi import HTTPException
            raise HTTPException(422, "No speech recognized. Please try again.")

        stt_finished = perf_counter()
        yield "transcription", text
        yield "mic_quality", quality

        turn = await run_in_threadpool(self.conversation.respond, db, session_id, user_id, text, request_id)
        ai_text = turn.content
        llm_finished = perf_counter()

        yield "ai_response", ai_text

        yield "timing", {"stt_ms": round((stt_finished - started) * 1000),
                         "response_ms": round((llm_finished - stt_finished) * 1000)}

        speech_started = perf_counter()
        try:
            audio = await self.synthesize(ai_text)
            yield "timing", {"tts_ms": round((perf_counter() - speech_started) * 1000)}
            if audio:
                yield "audio", audio
            else:
                logger.warning("TTS produced empty audio")
                yield "warning", "Your response was saved, but speech is unavailable."
        except Exception as e:
            logger.error("TTS failed for response (text delivered, audio skipped): %s", e)
            yield "warning", "Your response was saved, but speech is unavailable."

    def _assess_quality(self, wav_path: str, text: str) -> dict:
        try:
            from app.voice.audio_quality import assess_audio_quality
            quality = assess_audio_quality(wav_path)
        except Exception as e:
            logger.error("Mic quality assessment failed: %s", e)
            quality = {"score": 0, "quality": "unknown", "rms_db": None,
                       "peak_db": None, "silence_ratio": None, "clip_ratio": None}
        quality["recognized"] = text not in (STT_RETRY_TEXT, "", None)
        return quality

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
