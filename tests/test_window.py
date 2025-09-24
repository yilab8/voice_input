from voice_input.window import ActiveWindow, ActiveWindowTracker


class DummyBackend:
    def __init__(self):
        self.capture_calls = 0
        self.focus_calls = []
        self.window = ActiveWindow(handle=99, title="Dummy")

    def capture(self):
        self.capture_calls += 1
        return self.window

    def focus(self, window):
        self.focus_calls.append(window)
        return True


def test_tracker_uses_backend_for_capture_and_focus():
    backend = DummyBackend()
    tracker = ActiveWindowTracker(enabled=True, backend=backend)

    window = tracker.capture()
    assert window == backend.window
    assert backend.capture_calls == 1

    assert tracker.focus(window) is True
    assert backend.focus_calls == [backend.window]


def test_tracker_disabled_skips_backend_calls():
    backend = DummyBackend()
    tracker = ActiveWindowTracker(enabled=False, backend=backend)

    assert tracker.capture() is None
    assert backend.capture_calls == 0
    assert tracker.focus(backend.window) is False
    assert backend.focus_calls == []
