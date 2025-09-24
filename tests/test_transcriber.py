import pytest

np = pytest.importorskip("numpy")

from voice_input.config import WhisperConfig
from voice_input.transcriber import SpeechRecognizer, _clean_text, _resample_audio


class DummySegment:
    def __init__(self, text, start=None, end=None):
        self.text = text
        self.start = start
        self.end = end


class DummyInfo:
    def __init__(self, language="en", language_probability=0.9, duration=1.2):
        self.language = language
        self.language_probability = language_probability
        self.duration = duration


class DummyModel:
    def __init__(self):
        self.calls = []

    def transcribe(self, audio, **kwargs):
        self.calls.append((audio, kwargs))
        segments = [
            DummySegment(" Hello"),
            DummySegment("world! "),
            DummySegment(""),
        ]
        info = DummyInfo()
        return segments, info


def test_resample_changes_length():
    source = np.linspace(-1.0, 1.0, num=8_000, dtype=np.float32)
    result = _resample_audio(source, 8_000, 16_000)
    assert result.shape[0] == 16_000
    assert np.isclose(result.min(), -1.0, atol=1e-2)
    assert np.isclose(result.max(), 1.0, atol=1e-2)


def test_resample_same_rate_returns_copy():
    source = np.linspace(0.0, 1.0, num=4_000, dtype=np.float32)
    result = _resample_audio(source, 4_000, 4_000)
    assert result.shape == source.shape
    assert result.dtype == np.float32


def test_transcriber_returns_normalised_text():
    config = WhisperConfig(model_size="medium", beam_size=2, language="en")
    dummy_model = DummyModel()
    recogniser = SpeechRecognizer(config, model_loader=lambda: dummy_model)
    audio = np.zeros(16_000, dtype=np.float32)
    result = recogniser.transcribe(audio, sample_rate=16_000)
    assert result.text == "Hello world!"
    assert result.language == "en"
    assert len(result.segments) == 2
    assert dummy_model.calls[0][1]["beam_size"] == 2
    assert dummy_model.calls[0][1]["language"] == "en"
    assert dummy_model.calls[0][1]["vad_filter"] is True


def test_clean_text_removes_extra_spaces():
    assert _clean_text("  Hello   there \n") == "Hello there"
