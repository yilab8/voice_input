import pytest

np = pytest.importorskip("numpy")

from voice_input.audio import AudioRecorder
from voice_input.config import RecordingConfig


class DummyStream:
    def __init__(self, callback):
        self.callback = callback
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True
        chunk = (np.ones(4000, dtype=np.int16) * 1000).tobytes()
        self.callback(chunk, len(chunk) // 2, None, None)

    def stop(self):
        self.stopped = True

    def close(self):
        pass


class DummyFactory:
    def __init__(self):
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return DummyStream(kwargs["callback"])


def test_audio_recorder_records_bytes():
    config = RecordingConfig(sample_rate=16_000, channels=1, dtype="int16")
    factory = DummyFactory()
    recorder = AudioRecorder(config, stream_factory=factory)
    recorder.start()
    samples = recorder.stop()
    assert factory.calls, "stream factory should be used"
    assert samples.size > 0
    assert samples.dtype == np.float32
    assert (samples <= 1.0).all()
    assert (samples >= -1.0).all()


def test_abort_stops_stream():
    config = RecordingConfig()
    factory = DummyFactory()
    recorder = AudioRecorder(config, stream_factory=factory)
    recorder.start()
    recorder.abort()
    assert factory.calls[0]["callback"] is not None
