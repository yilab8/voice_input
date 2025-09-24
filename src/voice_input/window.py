"""Utilities for querying and restoring the active window on Windows."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from typing import Optional, Protocol


LOGGER = logging.getLogger("voice_input.window")


@dataclass(frozen=True)
class ActiveWindow:
    """Lightweight description of a window that can receive focus."""

    handle: int
    title: str = ""


class WindowBackend(Protocol):
    """Protocol implemented by window system backends."""

    def capture(self) -> Optional[ActiveWindow]:  # pragma: no cover - exercised via tracker tests
        ...

    def focus(self, window: ActiveWindow) -> bool:  # pragma: no cover - exercised via tracker tests
        ...


class _NullWindowBackend:
    """Backend used when active window tracking is not available."""

    def capture(self) -> Optional[ActiveWindow]:
        return None

    def focus(self, window: ActiveWindow) -> bool:
        return False


class ActiveWindowTracker:
    """High-level helper that records and restores the active foreground window."""

    def __init__(self, *, enabled: bool = True, backend: Optional[WindowBackend] = None) -> None:
        self.enabled = enabled
        if backend is not None:
            self._backend = backend
        else:
            self._backend = self._default_backend()

    def _default_backend(self) -> WindowBackend:
        if not self.enabled:
            return _NullWindowBackend()
        if sys.platform.startswith("win"):
            try:
                return _Win32WindowBackend()
            except Exception:  # pragma: no cover - defensive
                LOGGER.debug("Falling back to null backend", exc_info=True)
        return _NullWindowBackend()

    def capture(self) -> Optional[ActiveWindow]:
        """Return the currently focused window, if available."""

        if not self.enabled:
            return None
        try:
            return self._backend.capture()
        except Exception:  # pragma: no cover - backend specific
            LOGGER.debug("Failed to capture active window", exc_info=True)
            return None

    def focus(self, window: Optional[ActiveWindow]) -> bool:
        """Request focus for *window*."""

        if not self.enabled or window is None:
            return False
        try:
            return bool(self._backend.focus(window))
        except Exception:  # pragma: no cover - backend specific
            LOGGER.debug("Failed to focus window %s", window, exc_info=True)
            return False


class _Win32WindowBackend:
    """Implementation backed by the Windows user32 API."""

    def __init__(self) -> None:  # pragma: no cover - requires Windows
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32

        self._ctypes = ctypes
        self._wintypes = wintypes
        self._user32 = user32

    def capture(self) -> Optional[ActiveWindow]:  # pragma: no cover - requires Windows
        hwnd = self._user32.GetForegroundWindow()
        if not hwnd:
            return None
        length = self._user32.GetWindowTextLengthW(hwnd)
        buffer = self._ctypes.create_unicode_buffer(length + 1)
        self._user32.GetWindowTextW(hwnd, buffer, length + 1)
        return ActiveWindow(handle=int(hwnd), title=buffer.value)

    def focus(self, window: ActiveWindow) -> bool:  # pragma: no cover - requires Windows
        hwnd = self._wintypes.HWND(int(window.handle))
        if not hwnd:
            return False

        SW_RESTORE = 9
        if self._user32.IsIconic(hwnd):
            self._user32.ShowWindow(hwnd, SW_RESTORE)

        self._user32.BringWindowToTop(hwnd)
        if not self._user32.SetForegroundWindow(hwnd):
            return False
        self._user32.SetFocus(hwnd)
        return bool(self._user32.GetForegroundWindow() == hwnd)


__all__ = ["ActiveWindow", "ActiveWindowTracker"]
