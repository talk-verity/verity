import logging
import math

logger = logging.getLogger(__name__)

_SILENCE_THRESHOLD = 0.005
_CLIP_THRESHOLD = 0.99


def assess_audio_quality(wav_path: str) -> dict:
    import soundfile as sf

    samples, _sr = sf.read(wav_path, dtype="float32", always_2d=True)
    if samples.ndim > 1:
        samples = samples[:, 0]
    samples = samples.ravel()
    if len(samples) == 0:
        return _build(-60.0, -60.0, 1.0, 0.0)

    peak_abs = float(abs(samples).max())
    rms = float(math.sqrt((samples * samples).mean()))
    rms_db = 20.0 * math.log10(rms) if rms > 1e-9 else -60.0
    peak_db = 20.0 * math.log10(peak_abs) if peak_abs > 1e-9 else -60.0
    silence_ratio = float((abs(samples) < _SILENCE_THRESHOLD).mean())
    clip_ratio = float((abs(samples) >= _CLIP_THRESHOLD).mean())

    return _build(rms_db, peak_db, silence_ratio, clip_ratio)


def _build(rms_db: float, peak_db: float, silence_ratio: float, clip_ratio: float) -> dict:
    score = 100.0 - max(0.0, (-28.0 - rms_db)) * 4.0
    score -= silence_ratio * 40.0
    score = max(0.0, min(100.0, round(score, 1)))

    if clip_ratio > 0.01:
        quality = "clipping"
    elif rms_db < -50.0:
        quality = "too_quiet"
    elif score >= 70:
        quality = "good"
    elif score >= 40:
        quality = "low"
    else:
        quality = "poor"

    logger.info(
        "Mic quality: rms=%.1fdB peak=%.1fdB silence=%.0f%% clip=%.1f%% -> %s (%.0f)",
        rms_db, peak_db, silence_ratio * 100, clip_ratio * 100, quality, score,
    )
    return {
        "score": score,
        "quality": quality,
        "rms_db": round(rms_db, 1),
        "peak_db": round(peak_db, 1),
        "silence_ratio": round(silence_ratio, 3),
        "clip_ratio": round(clip_ratio, 4),
    }
