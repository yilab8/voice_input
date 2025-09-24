import time
from types import SimpleNamespace

from voice_input.window import ActiveWindow

from voice_input.app import VoiceInputApp
from voice_input.config import AppConfig, HotkeyConfig, RecordingConfig


class DummySamples(list):
    @property
    def size(self):
        return len(self)


class DummyRecorder:
    def __init__(self):
        self.started = 0
        self.stopped = 0

    def start(self):
        self.started += 1

    def stop(self):
        self.stopped += 1
        return DummySamples([0.1, 0.2])


class DummyRecognizer:
    def __init__(self):
        self.calls = []

    def transcribe(self, samples, sample_rate):
        self.calls.append((list(samples), sample_rate))
        return SimpleNamespace(text="hello world", segments=(), language="en", language_probability=1.0, duration=0.1)


class DummyEmitter:
    def __init__(self):
        self.emitted = []

    def emit(self, text, *, target_window=None):
        self.emitted.append((text, target_window))


class DummyWindowTracker:
    def __init__(self):
        self.captures = 0
        self.focus_calls = []
        self.window = ActiveWindow(handle=123, title="Dummy")

    def capture(self):
        self.captures += 1
        return self.window

    def focus(self, window):
        self.focus_calls.append(window)
        return True


class DummyKeyboard:
    def __init__(self):
        self.callbacks = {}
        self.next_id = 0

    def add_hotkey(self, hotkey, callback, suppress=False, trigger_on_release=False):
        handle = f"{hotkey}-{self.next_id}"
        self.next_id += 1
        self.callbacks[handle] = {
            "hotkey": hotkey,
            "callback": callback,
            "suppress": suppress,
            "trigger_on_release": trigger_on_release,
        }
        return handle

    def remove_hotkey(self, handle):
        self.callbacks.pop(handle, None)


def test_voice_input_app_toggle_flow():
    config = AppConfig(
        hotkey=HotkeyConfig(hotkey="ctrl+windows"),
        recording=RecordingConfig(sample_rate=16_000),
    )
    recorder = DummyRecorder()
    recognizer = DummyRecognizer()
    emitter = DummyEmitter()
    keyboard = DummyKeyboard()
    window_tracker = DummyWindowTracker()

    app = VoiceInputApp(
        config=config,
        recorder=recorder,
        recogniser=recognizer,
        emitter=emitter,
        keyboard_module=keyboard,
        window_tracker=window_tracker,
    )

    app.start_recording()
    assert recorder.started == 1
    app.stop_recording()
    time.sleep(0.1)
    assert recorder.stopped == 1
    assert recognizer.calls
    assert emitter.emitted == [("hello world", window_tracker.window)]
    assert window_tracker.captures == 1


def test_hotkey_press_release_flow():
    config = AppConfig(
        hotkey=HotkeyConfig(hotkey="ctrl+windows"),
        recording=RecordingConfig(sample_rate=16_000),
    )
    recorder = DummyRecorder()
    recognizer = DummyRecognizer()
    emitter = DummyEmitter()
    keyboard = DummyKeyboard()
    window_tracker = DummyWindowTracker()

    app = VoiceInputApp(
        config=config,
        recorder=recorder,
        recogniser=recognizer,
        emitter=emitter,
        keyboard_module=keyboard,
        window_tracker=window_tracker,
    )

    app._on_hotkey_press()
    assert recorder.started == 1
    app._on_hotkey_release()
    time.sleep(0.1)
    assert recorder.stopped == 1
    assert emitter.emitted == [("hello world", window_tracker.window)]
