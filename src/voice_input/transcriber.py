"""Speech recognition helpers built on top of faster-whisper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional, Sequence

try:  # pragma: no cover - import guard exercised in tests
    import numpy as np  # type: ignore
except Exception as exc:  # pragma: no cover - handled explicitly
    np = None  # type: ignore
    _NUMPY_IMPORT_ERROR = exc
else:  # pragma: no cover - executed when numpy available
    _NUMPY_IMPORT_ERROR = None

from .config import WhisperConfig


@dataclass
class Segment:
    """Container representing a recognised speech segment."""

    text: str
    start: Optional[float] = None
    end: Optional[float] = None


@dataclass
class TranscriptionResult:
    """Normalised transcription result."""

    text: str
    segments: Sequence[Segment]
    language: Optional[str]
    language_probability: Optional[float]
    duration: Optional[float]


ModelLoader = Callable[[], object]


def _require_numpy() -> None:
    if np is None:  # pragma: no cover - depends on environment
        raise RuntimeError("numpy is required for speech recognition") from _NUMPY_IMPORT_ERROR


def _resample_audio(audio, orig_rate: int, target_rate: int):
    """Resample *audio* to *target_rate* using simple linear interpolation."""

    _require_numpy()
    if orig_rate == target_rate:
        return np.asarray(audio, dtype=np.float32)

    audio_arr = np.asarray(audio, dtype=np.float32)
    if audio_arr.ndim != 1:
        raise ValueError("Audio must be mono for resampling")

    ratio = target_rate / float(orig_rate)
    new_length = max(int(round(audio_arr.shape[0] * ratio)), 1)
    base_positions = np.linspace(0, audio_arr.shape[0] - 1, num=audio_arr.shape[0], dtype=np.float64)
    target_positions = np.linspace(0, audio_arr.shape[0] - 1, num=new_length, dtype=np.float64)
    resampled = np.interp(target_positions, base_positions, audio_arr.astype(np.float64))
    return resampled.astype(np.float32)


class SpeechRecognizer:
    """Wrapper that exposes a light-weight interface around faster-whisper."""

    def __init__(self, config: WhisperConfig, *, model_loader: Optional[ModelLoader] = None) -> None:
        self.config = config
        self._model_loader = model_loader or self._default_model_loader
        self._model: Optional[object] = None

    def _default_model_loader(self) -> object:
        from faster_whisper import WhisperModel

        kwargs = {
            "compute_type": self.config.compute_type,
        }
        if self.config.download_root is not None:
            kwargs["download_root"] = str(self.config.download_root)
        return WhisperModel(self.config.model_size, **kwargs)

    def _ensure_model(self) -> object:
        if self._model is None:
            self._model = self._model_loader()
        return self._model

    def transcribe(self, audio, sample_rate: int) -> TranscriptionResult:
        """Transcribe *audio* sampled at *sample_rate* Hz."""

        _require_numpy()
        audio_arr = np.asarray(audio)
        if audio_arr.ndim != 1:
            raise ValueError("SpeechRecognizer expects mono audio input")

        normalised_audio = _resample_audio(audio_arr, sample_rate, 16_000)
        model = self._ensure_model()
        segments, info = self._call_transcribe(model, normalised_audio)
        normalised_segments = [
            Segment(text=_clean_text(seg.text), start=getattr(seg, "start", None), end=getattr(seg, "end", None))
            for seg in segments
            if getattr(seg, "text", "").strip()
        ]
        text = " ".join(segment.text for segment in normalised_segments).strip()
        language = getattr(info, "language", None)
        language_probability = getattr(info, "language_probability", None)
        duration = getattr(info, "duration", None)
        return TranscriptionResult(
            text=text,
            segments=normalised_segments,
            language=language,
            language_probability=language_probability,
            duration=duration,
        )

    def _call_transcribe(self, model: object, audio) -> tuple[Iterable[object], object]:
        kwargs = {
            "beam_size": self.config.beam_size,
            "language": self.config.language,
            "vad_filter": True,
            "vad_parameters": {"min_silence_duration_ms": 500},
        }
        return model.transcribe(audio, **kwargs)


def _clean_text(text: str) -> str:
    return " ".join(text.strip().split())


__all__ = [
    "SpeechRecognizer",
    "TranscriptionResult",
    "Segment",
]
