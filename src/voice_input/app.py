"""Entry point for the voice input desktop utility."""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from .audio import AudioRecorder
from .config import AppConfig
from .text_output import TextEmitter
from .window import ActiveWindow, ActiveWindowTracker
from .transcriber import SpeechRecognizer

try:  # pragma: no cover - optional dependency
    import keyboard  # type: ignore
except Exception as exc:  # pragma: no cover
    keyboard = None  # type: ignore
    _KEYBOARD_IMPORT_ERROR = exc
else:  # pragma: no cover
    _KEYBOARD_IMPORT_ERROR = None

LOGGER = logging.getLogger("voice_input")


class VoiceInputApp:
    """Coordinates keyboard events, audio capture and speech recognition."""

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        *,
        recorder: Optional[AudioRecorder] = None,
        recogniser: Optional[SpeechRecognizer] = None,
        emitter: Optional[TextEmitter] = None,
        keyboard_module: Optional[object] = None,
        window_tracker: Optional[ActiveWindowTracker] = None,
    ) -> None:
        self.config = config or AppConfig.default()
        self.recorder = recorder or AudioRecorder(self.config.recording)
        self.recogniser = recogniser or SpeechRecognizer(self.config.whisper)
        self.window_tracker = window_tracker or ActiveWindowTracker(
            enabled=self.config.focus_active_window
        )
        self.emitter = emitter or TextEmitter(
            insert_text=self.config.insert_text,
            copy_to_clipboard=self.config.copy_to_clipboard,
            window_tracker=self.window_tracker,
        )
        if (
            emitter is not None
            and hasattr(self.emitter, "window_tracker")
            and getattr(self.emitter, "window_tracker", None) is None
        ):
            try:
                self.emitter.window_tracker = self.window_tracker  # type: ignore[attr-defined]
            except Exception:  # pragma: no cover - best effort for external emitters
                LOGGER.debug("Unable to attach window tracker to emitter", exc_info=True)
        self.keyboard = keyboard_module or keyboard
        if self.keyboard is None:
            raise RuntimeError("keyboard module is required to register the global hotkey") from _KEYBOARD_IMPORT_ERROR
        self._state_lock = threading.RLock()
        self._is_recording = False
        self._last_release_at = 0.0
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="transcription")
        self._hotkey_handles: list[object] = []
        self._active_window: Optional[ActiveWindow] = None

    def run(self) -> None:
        """Start the application event loop."""

        hotkey = self.config.hotkey.hotkey
        LOGGER.info("Hold %s to record speech. Release to transcribe. Press Ctrl+C to exit.", hotkey)
        press_handle = self.keyboard.add_hotkey(
            hotkey,
            self._on_hotkey_press,
            suppress=getattr(self.config.hotkey, "suppress", False),
        )
        release_handle = self.keyboard.add_hotkey(
            hotkey,
            self._on_hotkey_release,
            suppress=getattr(self.config.hotkey, "suppress", False),
            trigger_on_release=True,
        )
        self._hotkey_handles = [press_handle, release_handle]
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            LOGGER.info("Shutting down")
        finally:
            for handle in self._hotkey_handles:
                try:
                    self.keyboard.remove_hotkey(handle)
                except Exception:  # pragma: no cover - defensive
                    LOGGER.debug("Failed to remove hotkey handle %r", handle)
            if self._is_recording:
                try:
                    self.recorder.abort()
                except Exception:  # pragma: no cover - device specific cleanup
                    LOGGER.debug("Recorder abort failed during shutdown", exc_info=True)
            self._executor.shutdown(wait=True)

    def toggle_recording(self) -> None:
        """Toggle recording state. Retained for compatibility and testing."""

        if not self.stop_recording():
            self.start_recording()

    def start_recording(self) -> bool:
        """Begin a new recording session if not already active."""

        with self._state_lock:
            if self._is_recording:
                LOGGER.debug("Start request ignored; recorder already active")
                return False
            self._is_recording = True
        self._active_window = self.window_tracker.capture()
        try:
            self.recorder.start()
            LOGGER.info("Recording... release %s to stop.", self.config.hotkey.hotkey)
            return True
        except Exception as exc:  # pragma: no cover - device specific
            LOGGER.exception("Failed to start recording: %s", exc)
            with self._state_lock:
                self._is_recording = False
                self._active_window = None
            raise

    def stop_recording(self) -> bool:
        """Stop the current recording and trigger transcription."""

        with self._state_lock:
            if not self._is_recording:
                LOGGER.debug("Stop request ignored; recorder not active")
                return False
            self._is_recording = False
            self._last_release_at = time.monotonic()
        threading.Thread(target=self._stop_and_transcribe, daemon=True).start()
        return True

    def _on_hotkey_press(self) -> None:
        """Callback when the push-to-talk hotkey is pressed."""

        self.start_recording()

    def _on_hotkey_release(self) -> None:
        """Callback when the push-to-talk hotkey is released."""

        now = time.monotonic()
        with self._state_lock:
            if not self._is_recording:
                if (now - self._last_release_at) < self.config.hotkey.release_timeout_s:
                    LOGGER.debug("Ignoring duplicate release event")
                else:
                    self._last_release_at = now
                return
        self.stop_recording()

    def _stop_and_transcribe(self) -> None:
        active_window = self._active_window
        self._active_window = None
        try:
            samples = self.recorder.stop()
        except Exception as exc:  # pragma: no cover - device specific
            LOGGER.exception("Failed to stop recording: %s", exc)
            return
        if getattr(samples, "size", 0) == 0:
            LOGGER.info("No audio captured")
            return
        LOGGER.info("Transcribing %d samples", getattr(samples, "size", 0))
        self._executor.submit(self._transcribe_and_emit, samples, active_window)

    def _transcribe_and_emit(self, samples, active_window: Optional[ActiveWindow]) -> None:
        try:
            result = self.recogniser.transcribe(samples, sample_rate=self.config.recording.sample_rate)
            if result.text:
                LOGGER.info("Recognised: %s", result.text)
                self.emitter.emit(result.text, target_window=active_window)
            else:
                LOGGER.info("No speech detected")
        except Exception as exc:  # pragma: no cover - backend specific
            LOGGER.exception("Transcription failed: %s", exc)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
    app = VoiceInputApp()
    app.run()


__all__ = ["VoiceInputApp", "main"]
