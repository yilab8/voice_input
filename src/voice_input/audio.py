"""Audio recording utilities built on top of sounddevice."""

from __future__ import annotations

import queue
from typing import Callable, Optional

try:  # pragma: no cover - environment dependent
    import sounddevice as sd  # type: ignore
except Exception as exc:  # pragma: no cover
    sd = None  # type: ignore
    _SD_IMPORT_ERROR = exc
else:  # pragma: no cover
    _SD_IMPORT_ERROR = None

try:  # pragma: no cover
    import numpy as np  # type: ignore
except Exception as exc:  # pragma: no cover
    np = None  # type: ignore
    _NUMPY_IMPORT_ERROR = exc
else:  # pragma: no cover
    _NUMPY_IMPORT_ERROR = None

from .config import RecordingConfig

StreamFactory = Callable[..., object]


def _require_sounddevice() -> None:
    if sd is None:  # pragma: no cover - depends on runtime environment
        raise RuntimeError("sounddevice is required for audio recording") from _SD_IMPORT_ERROR


def _require_numpy() -> None:
    if np is None:  # pragma: no cover
        raise RuntimeError("numpy is required for audio recording") from _NUMPY_IMPORT_ERROR


class AudioRecorder:
    """Record raw audio from the system microphone."""

    def __init__(self, config: RecordingConfig, *, stream_factory: Optional[StreamFactory] = None) -> None:
        self.config = config
        self._stream_factory = stream_factory or self._default_stream_factory
        self._queue: queue.Queue[bytes] = queue.Queue()
        self._stream: Optional[object] = None

    def _default_stream_factory(self, **kwargs) -> object:
        _require_sounddevice()
        return sd.RawInputStream(**kwargs)

    def start(self) -> None:
        """Begin recording audio."""

        _require_numpy()
        self._queue = queue.Queue()
        stream = self._stream_factory(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            blocksize=self.config.block_size,
            dtype=self.config.dtype,
            callback=self._callback,
        )
        self._stream = stream
        if hasattr(stream, "start"):
            stream.start()

    def _callback(self, indata, frames, time, status) -> None:  # pragma: no cover - exercised indirectly
        if indata is None:
            return
        if isinstance(indata, (bytes, bytearray, memoryview)):
            chunk = bytes(indata)
        else:
            chunk = bytes(getattr(indata, "tobytes")())
        self._queue.put(chunk)

    def stop(self):
        """Stop recording and return the captured audio as float32 samples."""

        _require_numpy()
        if self._stream is not None and hasattr(self._stream, "stop"):
            self._stream.stop()
        if self._stream is not None and hasattr(self._stream, "close"):
            self._stream.close()
        raw_frames: list[bytes] = []
        while not self._queue.empty():
            raw_frames.append(self._queue.get())
        raw_audio = b"".join(raw_frames)
        if not raw_audio:
            return np.zeros(0, dtype=np.float32)
        dtype = np.dtype(self.config.dtype)
        int_samples = np.frombuffer(raw_audio, dtype=dtype)
        max_value = float(np.iinfo(dtype).max)
        float_samples = int_samples.astype(np.float32) / max_value
        return float_samples

    def abort(self) -> None:
        """Abort recording without returning audio."""

        if self._stream is not None and hasattr(self._stream, "stop"):
            self._stream.stop()
        if self._stream is not None and hasattr(self._stream, "close"):
            self._stream.close()
        self._stream = None
        with self._queue.mutex:
            self._queue.queue.clear()


__all__ = ["AudioRecorder"]
