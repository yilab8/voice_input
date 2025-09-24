from voice_input.text_output import TextEmitter
from voice_input.window import ActiveWindow


class DummyClipboard:
    def __init__(self):
        self.copied = []

    def copy(self, text):
        self.copied.append(text)


class DummyKeyboard:
    def __init__(self):
        self.written = []
        self.sent = []

    def write(self, text):
        self.written.append(text)

    def send(self, hotkey):
        self.sent.append(hotkey)


class DummyWindowTracker:
    def __init__(self):
        self.focus_calls = []

    def focus(self, window):
        self.focus_calls.append(window)
        return True


def test_emitter_copies_and_pastes():
    clipboard = DummyClipboard()
    keyboard = DummyKeyboard()
    tracker = DummyWindowTracker()
    emitter = TextEmitter(clipboard_module=clipboard, keyboard_module=keyboard, window_tracker=tracker)
    window = ActiveWindow(handle=1, title="Demo")
    emitter.emit("hello world", target_window=window)
    assert clipboard.copied == ["hello world"]
    assert keyboard.sent == ["ctrl+v"]
    assert tracker.focus_calls == [window]


def test_emitter_write_without_clipboard():
    keyboard = DummyKeyboard()
    emitter = TextEmitter(copy_to_clipboard=False, keyboard_module=keyboard)
    emitter.emit("test")
    assert keyboard.written == ["test"]
